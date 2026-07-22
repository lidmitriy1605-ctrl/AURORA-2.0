"""Local Google Calendar OAuth and read-only schedule adapter."""

from __future__ import annotations

import json
import secrets
import threading
import time
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen


SCOPE = "https://www.googleapis.com/auth/calendar.events"


class CalendarError(RuntimeError):
    pass


def _post(url: str, payload: dict) -> dict:
    request = Request(url, data=urlencode(payload).encode("utf-8"), method="POST")
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as error:
        raise CalendarError("Google Calendar authorization request failed.") from error


class GoogleCalendar:
    def __init__(self, client_path: str | Path = "secrets/google-calendar-client.json", token_path: str | Path = "data/google-calendar-token.json") -> None:
        self.client_path = Path(client_path)
        self.token_path = Path(token_path)

    def _client(self) -> dict:
        try:
            data = json.loads(self.client_path.read_text(encoding="utf-8"))
            return data["installed"]
        except Exception as error:
            raise CalendarError("Google Calendar OAuth client file is unavailable.") from error

    def _token(self) -> dict:
        try:
            return json.loads(self.token_path.read_text(encoding="utf-8"))
        except Exception as error:
            raise CalendarError("Google Calendar is not authorised yet.") from error

    def _save_token(self, token: dict) -> None:
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_path.write_text(json.dumps(token, ensure_ascii=False, indent=2), encoding="utf-8")

    def authorize(self, port: int = 8765) -> None:
        client = self._client()
        redirect_uri = f"http://localhost:{port}/callback"
        state = secrets.token_urlsafe(24)
        query = urlencode({"client_id": client["client_id"], "redirect_uri": redirect_uri, "response_type": "code", "scope": SCOPE, "access_type": "offline", "prompt": "consent", "state": state})
        result: dict[str, str] = {}
        callback_received = threading.Event()

        class Callback(BaseHTTPRequestHandler):
            def do_GET(self):
                values = parse_qs(urlparse(self.path).query)
                result.update({key: value[0] for key, value in values.items() if value})
                callback_received.set()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write("<h2>AURORA Calendar connected. You may close this tab.</h2>".encode("utf-8"))

            def log_message(self, *_):
                return

        server = HTTPServer(("localhost", port), Callback)
        webbrowser.open("https://accounts.google.com/o/oauth2/v2/auth?" + query)
        server.timeout = 300
        while not callback_received.is_set():
            server.handle_request()
        server.server_close()
        if result.get("state") != state or "code" not in result:
            raise CalendarError("Google Calendar authorisation was not completed.")
        token = _post("https://oauth2.googleapis.com/token", {"code": result["code"], "client_id": client["client_id"], "client_secret": client["client_secret"], "redirect_uri": redirect_uri, "grant_type": "authorization_code"})
        token["expires_at"] = time.time() + int(token.get("expires_in", 3600))
        self._save_token(token)

    def _access_token(self) -> str:
        token = self._token()
        if token.get("expires_at", 0) > time.time() + 60:
            return token["access_token"]
        if not token.get("refresh_token"):
            raise CalendarError("Google Calendar token cannot be refreshed; reconnect it.")
        client = self._client()
        refreshed = _post("https://oauth2.googleapis.com/token", {"client_id": client["client_id"], "client_secret": client["client_secret"], "refresh_token": token["refresh_token"], "grant_type": "refresh_token"})
        token.update(refreshed)
        token["expires_at"] = time.time() + int(token.get("expires_in", 3600))
        self._save_token(token)
        return token["access_token"]

    def upcoming(self) -> str:
        params = urlencode({"timeMin": datetime.now(timezone.utc).isoformat(), "maxResults": 5, "singleEvents": "true", "orderBy": "startTime"})
        request = Request("https://www.googleapis.com/calendar/v3/calendars/primary/events?" + params)
        request.add_header("Authorization", f"Bearer {self._access_token()}")
        try:
            with urlopen(request, timeout=30) as response:
                items = json.loads(response.read().decode("utf-8")).get("items", [])
        except Exception as error:
            raise CalendarError("Не удалось прочитать Google Calendar.") from error
        if not items:
            return "В ближайших событиях Google Calendar пусто."
        lines = ["Ближайшие события:"]
        for event in items:
            start = event.get("start", {}).get("dateTime", event.get("start", {}).get("date", ""))
            lines.append(f"• {start} — {event.get('summary', 'Без названия')}")
        return "\n".join(lines)
