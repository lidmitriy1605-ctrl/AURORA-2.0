import tempfile
import unittest
from pathlib import Path

from aurora.cli import run


class AuroraCliTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.data = str(Path(self.directory.name) / "aurora.json")

    def tearDown(self):
        self.directory.cleanup()

    def _run(self, *arguments):
        return run(["--data", self.data, *arguments])

    def test_task_can_be_created_and_updated_from_cli(self):
        task = self._run("task-add", "dmitry", "dmitry", "Prepare MVP")
        updated = self._run("task-status", "dmitry", task["id"], "in_progress")
        listed = self._run("task-list", "dmitry", "dmitry", "--status", "in_progress")
        self.assertEqual(updated["status"], "in_progress")
        self.assertEqual(listed[0]["id"], task["id"])

    def test_confirmation_can_be_requested_and_confirmed_from_cli(self):
        request = self._run("confirmation-request", "eva", "connect calendar")
        confirmed = self._run("confirmation-confirm", "eva", request["id"])
        self.assertEqual(confirmed["status"], "confirmed")
