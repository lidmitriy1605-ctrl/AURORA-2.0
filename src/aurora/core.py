"""Small, dependency-free core for AURORA's first local MVP."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


SPACES = {"dmitry": {"dmitry"}, "eva": {"eva"}, "family": {"dmitry", "eva"}}
TASK_STATUSES = {"open", "in_progress", "done"}


class AccessDenied(PermissionError):
    """Raised when an actor is not permitted to use a data space."""


class ConfirmationRequired(RuntimeError):
    """Raised when an action must be explicitly confirmed before execution."""


class AuroraCore:
    """Local storage and policy boundary for notes, tasks and confirmations."""

    def __init__(self, data_path: str | Path = "data/aurora.json") -> None:
        self.path = Path(data_path)
        self.data = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            return {"notes": [], "tasks": [], "audit": [], "confirmations": []}
        with self.path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        for collection in ("notes", "tasks", "audit", "confirmations"):
            data.setdefault(collection, [])
        return data

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(self.data, file, ensure_ascii=False, indent=2)
        temporary.replace(self.path)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _require_access(actor: str, space: str) -> None:
        if space not in SPACES:
            raise ValueError(f"Unknown data space: {space}")
        if actor not in SPACES[space]:
            raise AccessDenied(f"{actor} cannot access {space}")

    def _audit(self, actor: str, action: str, target: str, result: str = "ok") -> None:
        self.data["audit"].append({
            "id": str(uuid4()), "at": self._now(), "actor": actor,
            "action": action, "target": target, "result": result,
        })

    def add_note(self, actor: str, space: str, text: str, source: str = "manual") -> dict:
        self._require_access(actor, space)
        if not text.strip():
            raise ValueError("Note text cannot be empty")
        note = {"id": str(uuid4()), "space": space, "author": actor, "text": text.strip(),
                "source": source, "created_at": self._now()}
        self.data["notes"].append(note)
        self._audit(actor, "note.created", note["id"])
        self._save()
        return note

    def find_notes(self, actor: str, space: str, query: str = "") -> list[dict]:
        self._require_access(actor, space)
        query = query.casefold().strip()
        records = [note for note in self.data["notes"] if note["space"] == space]
        if query:
            records = [note for note in records if query in note["text"].casefold()]
        self._audit(actor, "note.searched", space)
        self._save()
        return records

    def create_task(self, actor: str, space: str, title: str) -> dict:
        self._require_access(actor, space)
        if not title.strip():
            raise ValueError("Task title cannot be empty")
        now = self._now()
        task = {"id": str(uuid4()), "space": space, "author": actor, "title": title.strip(),
                "status": "open", "created_at": now, "updated_at": now}
        self.data["tasks"].append(task)
        self._audit(actor, "task.created", task["id"])
        self._save()
        return task

    def list_tasks(self, actor: str, space: str, status: str | None = None) -> list[dict]:
        self._require_access(actor, space)
        tasks = [task for task in self.data["tasks"] if task["space"] == space]
        if status:
            if status not in TASK_STATUSES:
                raise ValueError(f"Unknown task status: {status}")
            tasks = [task for task in tasks if task["status"] == status]
        return tasks

    def update_task_status(self, actor: str, task_id: str, status: str) -> dict:
        if status not in TASK_STATUSES:
            raise ValueError(f"Unknown task status: {status}")
        task = next((item for item in self.data["tasks"] if item["id"] == task_id), None)
        if task is None:
            raise KeyError(f"Task not found: {task_id}")
        self._require_access(actor, task["space"])
        task["status"] = status
        task["updated_at"] = self._now()
        self._audit(actor, "task.status_changed", task_id)
        self._save()
        return task

    def request_critical_action(self, actor: str, description: str) -> dict:
        if actor not in {"dmitry", "eva"}:
            raise AccessDenied(f"Unknown actor: {actor}")
        if not description.strip():
            raise ValueError("Action description cannot be empty")
        request = {"id": str(uuid4()), "actor": actor, "description": description.strip(),
                   "status": "pending", "created_at": self._now(), "confirmed_at": None}
        self.data["confirmations"].append(request)
        self._audit(actor, "confirmation.requested", request["id"])
        self._save()
        return request

    def confirm_critical_action(self, actor: str, request_id: str) -> dict:
        request = next((item for item in self.data["confirmations"] if item["id"] == request_id), None)
        if request is None:
            raise KeyError(f"Confirmation not found: {request_id}")
        if request["actor"] != actor:
            raise AccessDenied("Only the requesting owner may confirm this action")
        if request["status"] != "pending":
            raise ConfirmationRequired("Action was already confirmed")
        request["status"] = "confirmed"
        request["confirmed_at"] = self._now()
        self._audit(actor, "confirmation.confirmed", request_id)
        self._save()
        return request

    def audit_log(self, actor: str) -> list[dict]:
        if actor != "dmitry":
            raise AccessDenied("Audit log is available to the system owner")
        return list(self.data["audit"])
