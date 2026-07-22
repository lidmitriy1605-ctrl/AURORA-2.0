"""A human-oriented local command line interface for AURORA MVP."""

from __future__ import annotations

import argparse
import json
from typing import Sequence

from .core import AccessDenied, AuroraCore, ConfirmationRequired

ACTORS = ("dmitry", "eva")
SPACES = ("dmitry", "eva", "family")


def _actor_and_space(command: argparse.ArgumentParser) -> None:
    command.add_argument("actor", choices=ACTORS, help="who performs the action")
    command.add_argument("space", choices=SPACES, help="personal or family data space")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AURORA 2.0 — local personal assistant MVP")
    parser.add_argument("--data", default="data/aurora.json", help="path to local data file")
    commands = parser.add_subparsers(dest="command", required=True, title="commands")

    note_add = commands.add_parser("note-add", help="save a note")
    _actor_and_space(note_add)
    note_add.add_argument("text", help="note text")
    note_find = commands.add_parser("note-find", help="find notes in one space")
    _actor_and_space(note_find)
    note_find.add_argument("query", nargs="?", default="", help="text to find")

    task_add = commands.add_parser("task-add", help="create a task")
    _actor_and_space(task_add)
    task_add.add_argument("title", help="task title")
    task_list = commands.add_parser("task-list", help="list tasks in one space")
    _actor_and_space(task_list)
    task_list.add_argument("--status", choices=("open", "in_progress", "done"), help="optional status filter")
    task_status = commands.add_parser("task-status", help="change task status")
    task_status.add_argument("actor", choices=ACTORS)
    task_status.add_argument("task_id", help="task identifier")
    task_status.add_argument("status", choices=("open", "in_progress", "done"))

    export = commands.add_parser("export", help="export one allowed data space")
    _actor_and_space(export)
    export.add_argument("destination", help="new JSON file to create")

    request = commands.add_parser("confirmation-request", help="prepare a critical action for approval")
    request.add_argument("actor", choices=ACTORS)
    request.add_argument("description", help="what will be done after approval")
    confirm = commands.add_parser("confirmation-confirm", help="confirm a previously requested action")
    confirm.add_argument("actor", choices=ACTORS)
    confirm.add_argument("request_id", help="confirmation identifier")
    audit = commands.add_parser("audit", help="view system audit log (owner only)")
    audit.add_argument("actor", choices=ACTORS)
    return parser


def run(arguments: Sequence[str] | None = None) -> object:
    parser = build_parser()
    args = parser.parse_args(arguments)
    core = AuroraCore(args.data)
    try:
        if args.command == "note-add":
            return core.add_note(args.actor, args.space, args.text)
        if args.command == "note-find":
            return core.find_notes(args.actor, args.space, args.query)
        if args.command == "task-add":
            return core.create_task(args.actor, args.space, args.title)
        if args.command == "task-list":
            return core.list_tasks(args.actor, args.space, args.status)
        if args.command == "task-status":
            return core.update_task_status(args.actor, args.task_id, args.status)
        if args.command == "export":
            return {"exported_to": str(core.export_space(args.actor, args.space, args.destination))}
        if args.command == "confirmation-request":
            return core.request_critical_action(args.actor, args.description)
        if args.command == "confirmation-confirm":
            return core.confirm_critical_action(args.actor, args.request_id)
        return core.audit_log(args.actor)
    except (AccessDenied, ConfirmationRequired, FileExistsError, KeyError, ValueError) as error:
        parser.exit(2, f"AURORA: {error}\n")


def main() -> None:
    print(json.dumps(run(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
