"""Web search and LLM adapters used only for explicit information requests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.request import Request, urlopen


class ResearchError(RuntimeError):
    pass


def _post_json(url: str, payload: dict, headers: dict[str, str] | None = None) -> dict:
    request = Request(url, data=json.dumps(payload).encode("utf-8"), method="POST")
    request.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as error:
        raise ResearchError("Не удалось получить ответ внешнего информационного сервиса.") from error


@dataclass(frozen=True)
class SearchResult:
    answer: str
    sources: tuple[tuple[str, str], ...]


class TavilySearch:
    def __init__(self, api_key: str, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url

    def search(self, query: str) -> SearchResult:
        data = _post_json(
            self.base_url,
            {"query": query, "search_depth": "basic", "max_results": 5, "include_answer": "basic"},
            {"Authorization": f"Bearer {self.api_key}"},
        )
        sources = tuple((item.get("title", "Источник"), item["url"]) for item in data.get("results", []) if item.get("url"))
        return SearchResult(data.get("answer", "Поиск не дал краткого ответа."), sources)


class GeminiAssistant:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def answer(self, question: str, search: SearchResult | None = None) -> str:
        evidence = ""
        if search:
            evidence = "\n\nМатериалы поиска:\n" + "\n".join(f"- {title}: {url}" for title, url in search.sources)
            evidence += "\nКраткий результат поиска: " + search.answer
        prompt = (
            "Ты AURORA — личный помощник. Ответь по-русски кратко и практично. "
            "Не придумывай факты; если использованы материалы поиска, опирайся на них и не скрывай неопределённость.\n\n"
            f"Вопрос пользователя: {question}{evidence}"
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        data = _post_json(url, {"contents": [{"parts": [{"text": prompt}]}]})
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError, TypeError) as error:
            raise ResearchError("LLM не вернула пригодный текстовый ответ.") from error
