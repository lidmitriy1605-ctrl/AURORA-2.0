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
