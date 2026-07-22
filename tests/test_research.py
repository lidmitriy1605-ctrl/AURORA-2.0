import unittest

from aurora.research import GeminiAssistant, SearchResult, TavilySearch


class ResearchTests(unittest.TestCase):
    def test_tavily_formats_sources(self):
        service = TavilySearch("key", "https://example.test/search")
        import aurora.research as research
        original = research._post_json
        research._post_json = lambda *_: {"answer": "summary", "results": [{"title": "Source", "url": "https://example.test"}]}
        try:
            result = service.search("question")
        finally:
            research._post_json = original
        self.assertEqual(result.answer, "summary")
        self.assertEqual(result.sources[0][1], "https://example.test")

    def test_gemini_extracts_text(self):
        service = GeminiAssistant("key", "model")
        import aurora.research as research
        original = research._post_json
        research._post_json = lambda *_: {"candidates": [{"content": {"parts": [{"text": "answer"}]}}]}
        try:
            answer = service.answer("question", SearchResult("summary", ()))
        finally:
            research._post_json = original
        self.assertEqual(answer, "answer")
