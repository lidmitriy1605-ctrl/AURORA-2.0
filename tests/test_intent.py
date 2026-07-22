import unittest
from datetime import date

from aurora.intent import classify_message


class IntentTests(unittest.TestCase):
    def test_classifies_personal_note_without_external_service(self):
        intent = classify_message("Запомни идею для проекта", "dmitry")
        self.assertEqual(intent.kind, "note")
        self.assertEqual(intent.text, "идею для проекта")

    def test_classifies_task_for_eva_with_due_date(self):
        intent = classify_message("Ева, нужно оплатить кружок до пятницы", "dmitry")
        self.assertEqual(intent.kind, "task")
        self.assertEqual(intent.assignee, "eva")
        self.assertTrue(intent.due_at)
        self.assertIn("оплатить кружок", intent.text)

    def test_question_is_sent_to_research_route(self):
        intent = classify_message("Что такое квантовые вычисления?", "dmitry")
        self.assertEqual(intent.kind, "research")

    def test_weather_is_detected(self):
        self.assertEqual(classify_message("Какая погода завтра?", "dmitry").kind, "weather")
