import tempfile
import unittest
from pathlib import Path

from aurora.core import AccessDenied, AuroraCore


class AuroraCoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.core = AuroraCore(Path(self.directory.name) / "aurora.json")

    def tearDown(self):
        self.directory.cleanup()

    def test_personal_notes_are_isolated(self):
        self.core.add_note("dmitry", "dmitry", "private idea")
        with self.assertRaises(AccessDenied):
            self.core.find_notes("eva", "dmitry", "idea")

    def test_family_note_is_visible_to_both_users(self):
        self.core.add_note("dmitry", "family", "buy groceries")
        found = self.core.find_notes("eva", "family", "groceries")
        self.assertEqual(found[0]["text"], "buy groceries")

    def test_personal_and_family_messages_are_isolated(self):
        self.core.remember_message("dmitry", "dmitry", "personal thought")
        self.core.remember_message("dmitry", "family", "shared conversation")
        self.assertEqual(self.core.find_messages("dmitry", "dmitry")[0]["text"], "personal thought")
        self.assertEqual(self.core.find_messages("eva", "family")[0]["text"], "shared conversation")
        with self.assertRaises(AccessDenied):
            self.core.find_messages("eva", "dmitry")

    def test_task_status_change_is_audited(self):
        task = self.core.create_task("dmitry", "dmitry", "write MVP")
        self.core.update_task_status("dmitry", task["id"], "done")
        self.assertEqual(self.core.list_tasks("dmitry", "dmitry")[0]["status"], "done")
        self.assertIn("task.status_changed", [event["action"] for event in self.core.audit_log("dmitry")])

    def test_only_requester_can_confirm_critical_action(self):
        request = self.core.request_critical_action("eva", "connect calendar")
        with self.assertRaises(AccessDenied):
            self.core.confirm_critical_action("dmitry", request["id"])
        self.assertEqual(self.core.confirm_critical_action("eva", request["id"])["status"], "confirmed")

    def test_export_contains_only_allowed_space(self):
        self.core.add_note("dmitry", "dmitry", "private plan")
        self.core.add_note("dmitry", "family", "shared plan")
        destination = Path(self.directory.name) / "dmitry-export.json"
        self.core.export_space("dmitry", "dmitry", destination)
        content = destination.read_text(encoding="utf-8")
        self.assertIn("private plan", content)
        self.assertNotIn("shared plan", content)

    def test_export_rejects_unpermitted_space_and_overwrite(self):
        destination = Path(self.directory.name) / "export.json"
        with self.assertRaises(AccessDenied):
            self.core.export_space("eva", "dmitry", destination)
        self.core.export_space("dmitry", "dmitry", destination)
        with self.assertRaises(FileExistsError):
            self.core.export_space("dmitry", "dmitry", destination)


if __name__ == "__main__":
    unittest.main()
