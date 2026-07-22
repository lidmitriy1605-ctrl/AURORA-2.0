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

    def send_message(self, chat_id: int, text: str) -> None:
        self.call("sendMessage", chat_id=chat_id, text=text)


class AuroraTelegramBot:
    def __init__(self, client: TelegramClient, core: AuroraCore, owner_chat_id: int | None = None) -> None:
        self.client = client
        self.core = core
        self.owner_chat_id = owner_chat_id

    @staticmethod
    def _help() -> str:
        return (
            "AURORA MVP commands:\n"
            "/note <text> — save a personal note\n"
            "/find <text> — search personal notes\n"
            "/task <text> — create a personal task\n"
            "/tasks — list open personal tasks\n"
            "/done <task-id> — complete a task\n"
            "/backup — create a local personal export\n"
            "/help — show this help"
        )

    def handle_message(self, chat_id: int, text: str) -> str:
        if self.owner_chat_id is None:
            return (
                f"AURORA is waiting for secure pairing. Your Telegram chat ID: {chat_id}.\n"
                "Add this number as TELEGRAM_OWNER_CHAT_ID in the local .env file, then restart the bot."
            )
        if chat_id != self.owner_chat_id:
            return "Access denied. This AURORA bot is private."

        command, _, argument = text.strip().partition(" ")
        command = command.split("@", 1)[0].lower()
        if command in {"/start", "/help"}:
            return self._help()
        if command == "/note":
            if not argument.strip():
                return "Usage: /note <text>"
            note = self.core.add_note("dmitry", "dmitry", argument)
            return f"Note saved: {note['id']}"
        if command == "/find":
            notes = self.core.find_notes("dmitry", "dmitry", argument)
            if not notes:
                return "No matching personal notes found."
            return "\n\n".join(f"• {note['text']}\n{note['created_at']}" for note in notes[:10])
        if command == "/task":
            if not argument.strip():
                return "Usage: /task <text>"
            task = self.core.create_task("dmitry", "dmitry", argument)
            return f"Task created: {task['title']}\nID: {task['id']}"
        if command == "/tasks":
            tasks = self.core.list_tasks("dmitry", "dmitry", "open")
            if not tasks:
                return "No open personal tasks."
            return "\n".join(f"• {task['title']}\n  ID: {task['id']}" for task in tasks[:20])
        if command == "/done":
            if not argument.strip():
                return "Usage: /done <task-id>"
            task = self.core.update_task_status("dmitry", argument.strip(), "done")
            return f"Task completed: {task['title']}"
        if command == "/backup":
            destination = Path("exports") / f"telegram-dmitry-{int(time.time())}.json"
            exported = self.core.export_space("dmitry", "dmitry", destination)
            return f"Local backup created: {exported}"
        return "Unknown command. Send /help."

    def process_update(self, update: dict) -> None:
        message = update.get("message")
        if not message or "text" not in message:
            return
        chat_id = message["chat"]["id"]
        self.client.send_message(chat_id, self.handle_message(chat_id, message["text"]))


def run_polling(data_path: str | Path = "data/aurora.json", env_path: str | Path = ".env") -> None:
    load_dotenv(env_path)
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    owner_value = os.environ.get("TELEGRAM_OWNER_CHAT_ID", "").strip()
    owner_chat_id = int(owner_value) if owner_value else None
    client = TelegramClient(token)
    bot = AuroraTelegramBot(client, AuroraCore(data_path), owner_chat_id)
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
