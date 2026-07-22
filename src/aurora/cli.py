"""A small local command line interface for AURORA MVP."""

from __future__ import annotations

import argparse
import json
from .core import AuroraCore


def main() -> None:
    parser = argparse.ArgumentParser(description="AURORA 2.0 local MVP")
    parser.add_argument("--data", default="data/aurora.json", help="path to local data file")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("note-add", "note-find", "task-add", "task-list"):
        child = commands.add_parser(name)
        child.add_argument("actor", choices=["dmitry", "eva"])
        child.add_argument("space", choices=["dmitry", "eva", "family"])
        child.add_argument("text", nargs="?", default="")
    export = commands.add_parser("export", help="export one allowed data space")
    export.add_argument("actor", choices=["dmitry", "eva"])
    export.add_argument("space", choices=["dmitry", "eva", "family"])
    export.add_argument("destination", help="new JSON file to create")
    args = parser.parse_args()
    core = AuroraCore(args.data)
    if args.command == "note-add":
        result = core.add_note(args.actor, args.space, args.text)
    elif args.command == "note-find":
        result = core.find_notes(args.actor, args.space, args.text)
    elif args.command == "task-add":
        result = core.create_task(args.actor, args.space, args.text)
    elif args.command == "task-list":
        result = core.list_tasks(args.actor, args.space)
    else:
        result = {"exported_to": str(core.export_space(args.actor, args.space, args.destination))}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
