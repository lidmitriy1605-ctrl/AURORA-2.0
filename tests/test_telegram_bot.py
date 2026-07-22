import tempfile
import unittest
from pathlib import Path

from aurora.core import AuroraCore
from aurora.telegram_bot import AuroraTelegramBot


class FakeTelegramClient:
    def __init__(self):
        self.messages = []

    def send_message(self, chat_id, text):
        self.messages.append((chat_id, text))


class AuroraTelegramBotTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        core = AuroraCore(Path(self.directory.name) / "aurora.json")
        self.client = FakeTelegramClient()
        self.bot = AuroraTelegramBot(self.client, core, owner_chat_id=12345)

    def tearDown(self):
        self.directory.cleanup()

    def test_pairing_mode_reveals_only_the_callers_chat_id(self):
        pairing = AuroraTelegramBot(self.client, self.bot.core)
        reply = pairing.handle_message(777, "/start")
        self.assertIn("777", reply)
        self.assertIn("pairing", reply)

    def test_non_owner_cannot_read_or_write_personal_data(self):
        reply = self.bot.handle_message(999, "/note secret")
        self.assertEqual(reply, "Access denied. This AURORA bot is private.")
        self.assertEqual(self.bot.core.find_notes("dmitry", "dmitry"), [])

    def test_owner_can_create_and_complete_task(self):
        created = self.bot.handle_message(12345, "/task Prepare Telegram")
        task_id = created.split("ID: ", 1)[1]
        completed = self.bot.handle_message(12345, f"/done {task_id}")
        self.assertIn("Task completed", completed)

    def test_process_update_replies_to_message(self):
        self.bot.process_update({"message": {"chat": {"id": 12345}, "text": "/help"}})
        self.assertEqual(self.client.messages[0][0], 12345)
        self.assertIn("/note", self.client.messages[0][1])
