"""Conservative interpretation of common Russian Telegram messages.

This is a transparent local fallback. A future LLM adapter can replace it,
but no text is sent to an external provider by this module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class Intent:
    kind: str
    text: str = ""
    assignee: str | None = None
    due_at: str | None = None


WEEKDAYS = {
    "понедельник": 0, "понедельника": 0,
    "вторник": 1, "вторника": 1,
    "среда": 2, "среды": 2,
    "четверг": 3, "четверга": 3,
    "пятница": 4, "пятницы": 4,
    "суббота": 5, "субботы": 5,
    "воскресенье": 6, "воскресенья": 6,
}


def _extract_due(text: str, today: date | None = None) -> tuple[str, str | None]:
    today = today or date.today()
    result = text
    due = None
    if re.search(r"\bзавтра\b", result, flags=re.IGNORECASE):
        due = today + timedelta(days=1)
        result = re.sub(r"\bзавтра\b", "", result, flags=re.IGNORECASE)
    else:
        match = re.search(r"\b(?:до|в)\s+(" + "|".join(WEEKDAYS) + r")\b", result, flags=re.IGNORECASE)
        if match:
            weekday = WEEKDAYS[match.group(1).lower()]
            days = (weekday - today.weekday()) % 7
            due = today + timedelta(days=days or 7)
            result = result[:match.start()] + result[match.end():]
    time_match = re.search(r"\b(?:в\s+)?([01]?\d|2[0-3]):([0-5]\d)\b", text)
    if due and time_match:
        due_value = f"{due.isoformat()}T{time_match.group(1).zfill(2)}:{time_match.group(2)}"
    else:
        due_value = due.isoformat() if due else None
    return re.sub(r"\s+", " ", result).strip(" ,.-"), due_value


def classify_message(text: str, actor: str) -> Intent:
    clean = text.strip()
    lower = clean.casefold()
    if lower in {"сегодня", "🗓 сегодня"}:
        return Intent("today")
    if lower in {"задачи", "✅ задачи"}:
        return Intent("tasks")
    if lower in {"календарь", "📅 календарь"} or "встреч" in lower or "событи" in lower:
        return Intent("calendar", clean)
    if lower in {"погода", "🌦 погода"} or "погод" in lower:
        return Intent("weather", clean)
    if lower in {"сводка", "📰 сводка"}:
        return Intent("summary")
    if lower.startswith(("запомни", "сохрани", "заметка", "запиши")):
        note = re.sub(r"^(запомни|сохрани|заметка|запиши)\s*[:,.-]?\s*", "", clean, flags=re.IGNORECASE)
        return Intent("note", note)
    task_signals = ("задача", "надо", "нужно", "напомни", "сделай", "сделать", "должен", "должна")
    if any(signal in lower for signal in task_signals):
        assignee = actor
        if re.search(r"\bев[аеы]\b", lower):
            assignee = "eva"
        elif re.search(r"\bдмитри[йюя]\b", lower):
            assignee = "dmitry"
        title = re.sub(r"^(?:задача\s*[:,-]?\s*)", "", clean, flags=re.IGNORECASE)
        title = re.sub(r"^(?:ева|еве|дмитрий|дмитрию)\s*[,!:—-]*\s*", "", title, flags=re.IGNORECASE)
        title, due_at = _extract_due(title)
        return Intent("task", title or clean, assignee, due_at)
    if clean.endswith("?") or any(signal in lower for signal in ("найди", "поищи", "расскажи", "что такое", "почему", "как ")):
        return Intent("research", clean)
    return Intent("clarify", clean)
