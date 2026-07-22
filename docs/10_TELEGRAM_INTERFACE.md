# 10. Telegram interface

## Security model

The token is stored only in local `.env`, which is ignored by Git. The bot starts in pairing mode and exposes no AURORA data. Send `/start` to the bot; it replies with your Telegram chat ID. Add that number to `TELEGRAM_OWNER_CHAT_ID` in `.env`, then restart the adapter.

Only the configured owner chat can use AURORA commands. Other chats receive no project data.

## Start

```powershell
.\tools\telegram-bot.ps1
```

Keep this PowerShell window open while the bot is used. Stop it with `Ctrl+C`.

## Commands

- `/note text` — save a personal note;
- `/find text` — search personal notes;
- `/task text` — create a personal task;
- `/tasks` — list open tasks;
- `/done task-id` — complete a task;
- `/backup` — create a local export;
- `/help` — display command help.

The first release deliberately provides only Dmitry's personal area. Family access and external actions require separate user and confirmation flows.

## Natural dialogue and family tasks

Commands are optional. The bot recognises common Russian phrases locally:

- `Запомни идею для проекта` saves a personal note.
- `Нужно подготовить отчёт до пятницы` creates a personal task with a due date.
- `Ева, нужно оплатить кружок до пятницы` creates a family task for Eva and notifies her after her chat is paired.
- `Какая погода завтра?` returns current conditions and tomorrow's forecast for the configured city through Open-Meteo.
- Internet questions are processed through Tavily search and Gemini. The bot returns a concise answer together with source links.

The bottom Telegram keyboard provides **Today**, **Tasks**, **Calendar**, **Weather**, and **Summary**. It is an overview, not a replacement for natural conversation.

To pair Eva, she sends `/start` to the bot. Add her returned chat ID locally as `TELEGRAM_EVA_CHAT_ID` in `.env`, then restart the adapter. This permits task notifications, but does not expose either user's personal notes.
