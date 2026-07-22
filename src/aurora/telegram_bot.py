"""Telegram adapter for the local AURORA MVP.

The adapter uses only the Telegram Bot HTTP API and Python's standard library.
It never stores the bot token in project data or source control.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .core import AuroraCore
from .intent import Intent, classify_message
from .calendar import CalendarError, GoogleCalendar
from .research import GeminiAssistant, ResearchError, TavilySearch
from .weather import OpenMeteoWeather, WeatherError


def load_dotenv(path: str | Path = ".env") -> None:
    """Load simple KEY=VALUE pairs without replacing existing environment values."""
    file_path = Path(path)
    if not file_path.exists():
        return
    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


class TelegramApiError(RuntimeError):
    """A Telegram request failed without exposing the authentication token."""


class TelegramClient:
    def __init__(self, token: str) -> None:
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN is not configured")
        self.base_url = f"https://api.telegram.org/bot{token}/"

    def call(self, method: str, **parameters):
        body = urlencode({key: value for key, value in parameters.items() if value is not None}).encode("utf-8")
        request = Request(self.base_url + method, data=body, method="POST")
        try:
            with urlopen(request, timeout=45) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as error:
            raise TelegramApiError(f"Telegram API request failed: {error}") from error
        if not payload.get("ok"):
            raise TelegramApiError(payload.get("description", "Unknown Telegram API error"))
        return payload["result"]

    def get_updates(self, offset: int | None = None):
        return self.call("getUpdates", offset=offset, timeout=30, allowed_updates=json.dumps(["message"]))

    def send_message(self, chat_id: int, text: str, reply_markup: dict | None = None) -> None:
        markup = json.dumps(reply_markup, ensure_ascii=False) if reply_markup else None
        self.call("sendMessage", chat_id=chat_id, text=text, reply_markup=markup)


class AuroraTelegramBot:
    MENU = {
        "keyboard": [["🗓 Сегодня", "✅ Задачи"], ["📅 Календарь", "🌦 Погода"], ["📰 Сводка"]],
        "resize_keyboard": True,
    }

    def __init__(
        self,
        client: TelegramClient,
        core: AuroraCore,
        owner_chat_id: int | None = None,
        eva_chat_id: int | None = None,
        weather: OpenMeteoWeather | None = None,
        search: TavilySearch | None = None,
        assistant: GeminiAssistant | None = None,
        calendar: GoogleCalendar | None = None,
        family_chat_id: int | None = None,
    ) -> None:
        self.client = client
        self.core = core
        self.owner_chat_id = owner_chat_id
        self.eva_chat_id = eva_chat_id
        self.weather = weather
        self.search = search
        self.assistant = assistant
        self.calendar = calendar
        self.family_chat_id = family_chat_id

    @staticmethod
    def _help() -> str:
        return (
            "Пишите обычными словами — AURORA поймёт заметку, задачу или вопрос.\n"
            "Например: «Ева, нужно оплатить кружок до пятницы» или «Запомни идею для проекта».\n\n"
            "Кнопки снизу показывают главное. Команды остаются как резервный вариант: /note, /task, /tasks, /done, /backup."
        )

    def _user_for_chat(self, chat_id: int) -> str | None:
        if chat_id == self.owner_chat_id:
            return "dmitry"
        if chat_id == self.eva_chat_id:
            return "eva"
        return None

    @staticmethod
    def _task_line(task: dict) -> str:
        due = f" · до {task['due_at']}" if task.get("due_at") else ""
        return f"• {task['title']}{due}\n  ID: {task['id']}"

    def _today(self, actor: str) -> str:
        tasks = self.core.list_tasks_for_assignee(actor, actor, "open")
        if not tasks:
            return "На сегодня нет открытых задач."
        return "Ваши открытые задачи:\n" + "\n".join(self._task_line(task) for task in tasks[:10])

    def _create_task(self, actor: str, intent: Intent) -> str:
        assignee = intent.assignee or actor
        space = "family" if assignee != actor else actor
        task = self.core.create_task(actor, space, intent.text, assignee=assignee, due_at=intent.due_at)
        recipient_chat = self.eva_chat_id if assignee == "eva" else self.owner_chat_id
        if recipient_chat and assignee != actor:
            try:
                self.client.send_message(
                    recipient_chat,
                    f"AURORA: новая семейная задача для вас\n{self._task_line(task)}",
                    self.MENU,
                )
                notified = " Исполнителю отправлено уведомление."
            except TelegramApiError:
                notified = " Задача сохранена, но уведомление пока не доставлено; попросите исполнителя открыть этого бота."
        elif assignee != actor:
            notified = " Уведомление будет отправлено после привязки Telegram-чата исполнителя."
        else:
            notified = ""
        return f"Задача создана:\n{self._task_line(task)}{notified}"

    def _handle_natural(self, actor: str, text: str) -> str:
        intent = classify_message(text, actor)
        if intent.kind == "today":
            return self._today(actor)
        if intent.kind == "tasks":
            return self._today(actor)
        if intent.kind == "note":
            if not intent.text:
                return "Напишите текст заметки после слова «запомни» или «сохрани»."
            note = self.core.add_note(actor, actor, intent.text)
            return f"Запомнила. Заметка сохранена: {note['id']}"
        if intent.kind == "task":
            return self._create_task(actor, intent)
        if intent.kind == "calendar":
            if not self.calendar:
                return "Google Calendar пока не подключён."
            try:
                return self.calendar.upcoming()
            except CalendarError as error:
                return str(error)
        if intent.kind == "weather":
            if not self.weather:
                return "Погодный сервис пока не настроен."
            try:
                return self.weather.forecast()
            except WeatherError as error:
                return str(error)
        if intent.kind == "research":
            try:
                result = self.search.search(intent.text) if self.search else None
                answer = self.assistant.answer(intent.text, result) if self.assistant else (result.answer if result else None)
                if not answer:
                    return "Информационный контур пока не настроен."
                sources = ""
                if result and result.sources:
                    sources = "\n\nИсточники:\n" + "\n".join(f"• {title} — {url}" for title, url in result.sources[:5])
                return answer + sources
            except ResearchError as error:
                return str(error)
        return "Я не хочу неверно угадать. Напишите, например: «Запомни ...», «Нужно ...», «Ева, нужно ...» или задайте вопрос с вопросительным знаком."

    def handle_message(self, chat_id: int, text: str) -> str:
        if self.owner_chat_id is None:
            return (
                f"AURORA is waiting for secure pairing. Your Telegram chat ID: {chat_id}.\n"
                "Add this number as TELEGRAM_OWNER_CHAT_ID in the local .env file, then restart the bot."
            )
        actor = self._user_for_chat(chat_id)
        if actor is None:
            return "Access denied. This AURORA bot is private."

        command, _, argument = text.strip().partition(" ")
        command = command.split("@", 1)[0].lower()
        if command in {"/start", "/help"}:
            return self._help()
        if command == "/note":
            if not argument.strip():
                return "Usage: /note <text>"
            note = self.core.add_note(actor, actor, argument)
            return f"Note saved: {note['id']}"
        if command == "/find":
            notes = self.core.find_notes(actor, actor, argument)
            if not notes:
                return "No matching personal notes found."
            return "\n\n".join(f"• {note['text']}\n{note['created_at']}" for note in notes[:10])
        if command == "/task":
            if not argument.strip():
                return "Usage: /task <text>"
            task = self.core.create_task(actor, actor, argument)
            return f"Task created: {task['title']}\nID: {task['id']}"
        if command == "/tasks":
            tasks = self.core.list_tasks_for_assignee(actor, actor, "open")
            if not tasks:
                return "No open personal tasks."
            return "\n".join(self._task_line(task) for task in tasks[:20])
        if command == "/done":
            if not argument.strip():
                return "Usage: /done <task-id>"
            task = self.core.update_task_status(actor, argument.strip(), "done")
            return f"Task completed: {task['title']}"
        if command == "/backup":
            destination = Path("exports") / f"telegram-{actor}-{int(time.time())}.json"
            exported = self.core.export_space(actor, actor, destination)
            return f"Local backup created: {exported}"
        if command.startswith("/"):
            return "Unknown command. Send /help."
        return self._handle_natural(actor, text)

    def _handle_family_message(self, actor: str, text: str) -> str | None:
        """Answer only actionable group messages; ordinary discussion remains quiet."""
        intent = classify_message(text, actor)
        if intent.kind in {"task", "note", "calendar", "weather", "research", "today", "tasks"}:
            return self._handle_natural(actor, text)
        return None

    def process_update(self, update: dict) -> None:
        message = update.get("message")
        if not message or "text" not in message:
            return
        chat_id = message["chat"]["id"]
        text = message["text"]
        chat_type = message.get("chat", {}).get("type")
        if self.family_chat_id is not None and chat_id == self.family_chat_id:
            sender_id = message.get("from", {}).get("id")
            actor = self._user_for_chat(sender_id)
            if actor is None:
                return
            self.core.remember_message(actor, "family", text, chat_id, message.get("message_id"), "telegram-group")
            reply = self._handle_family_message(actor, text)
            if reply:
                self.client.send_message(chat_id, reply, self.MENU)
            return
        if chat_type in {"group", "supergroup"}:
            sender_id = message.get("from", {}).get("id")
            if self.family_chat_id is None and self._user_for_chat(sender_id) is not None:
                self.client.send_message(
                    chat_id,
                    f"AURORA is waiting for family-group pairing. Group chat ID: {chat_id}.\n"
                    "Add it as TELEGRAM_FAMILY_CHAT_ID in the local .env file, then restart the bot.",
                )
            return
        actor = self._user_for_chat(chat_id)
        if actor is not None:
            self.core.remember_message(actor, actor, text, chat_id, message.get("message_id"))
        self.client.send_message(chat_id, self.handle_message(chat_id, text), self.MENU)


def run_polling(data_path: str | Path = "data/aurora.json", env_path: str | Path = ".env") -> None:
    load_dotenv(env_path)
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    owner_value = os.environ.get("TELEGRAM_OWNER_CHAT_ID", "").strip()
    eva_value = os.environ.get("TELEGRAM_EVA_CHAT_ID", "").strip()
    family_value = os.environ.get("TELEGRAM_FAMILY_CHAT_ID", "").strip()
    owner_chat_id = int(owner_value) if owner_value else None
    eva_chat_id = int(eva_value) if eva_value else None
    family_chat_id = int(family_value) if family_value else None
    client = TelegramClient(token)
    weather = OpenMeteoWeather(
        os.environ.get("WEATHER_DEFAULT_CITY", "Saint Petersburg"),
        os.environ.get("WEATHER_DEFAULT_COUNTRY", ""),
    )
    search = None
    if os.environ.get("WEB_SEARCH_API_KEY") and os.environ.get("WEB_SEARCH_BASE_URL"):
        search = TavilySearch(os.environ["WEB_SEARCH_API_KEY"], os.environ["WEB_SEARCH_BASE_URL"])
    assistant = None
    if os.environ.get("GEMINI_API_KEY") and os.environ.get("GEMINI_MODEL"):
        assistant = GeminiAssistant(os.environ["GEMINI_API_KEY"], os.environ["GEMINI_MODEL"])
    calendar = GoogleCalendar() if Path("secrets/google-calendar-client.json").exists() else None
    bot = AuroraTelegramBot(client, AuroraCore(data_path), owner_chat_id, eva_chat_id, weather, search, assistant, calendar, family_chat_id)
    offset = None
    print("AURORA Telegram adapter started. Press Ctrl+C to stop.")
    while True:
        for update in client.get_updates(offset):
            offset = update["update_id"] + 1
            try:
                bot.process_update(update)
            except Exception as error:  # Keep polling when one user request fails.
                print(f"AURORA Telegram update error: {error}")


if __name__ == "__main__":
    run_polling()
