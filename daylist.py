"""A small, local task list for the command line."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn


@dataclass
class Task:
    id: int
    text: str
    completed: bool


@dataclass
class Store:
    next_id: int
    tasks: list[Task]


class DaylistError(Exception):
    """An expected command or stored-data error."""


def positive_id(value: str) -> int:
    """Parse a positive task ID for argparse."""
    try:
        task_id = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("ID must be a positive integer") from exc
    if task_id < 1:
        raise argparse.ArgumentTypeError("ID must be a positive integer")
    return task_id


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Manage a local task list.")
    result.add_argument(
        "--data-file",
        metavar="PATH",
        help="use PATH instead of ~/.daylist/tasks.json",
    )
    commands = result.add_subparsers(dest="command", required=True)

    add_command = commands.add_parser("add", help="add a task")
    add_command.add_argument("text", metavar="TEXT", help="task text")
    commands.add_parser("list", help="list all tasks")

    done_command = commands.add_parser("done", help="mark a task complete")
    done_command.add_argument("id", metavar="ID", type=positive_id)

    remove_command = commands.add_parser("remove", help="remove a task")
    remove_command.add_argument("id", metavar="ID", type=positive_id)
    return result


def fail(message: str) -> NoReturn:
    raise DaylistError(message)


def load_store(path: Path) -> Store:
    try:
        with path.open("r", encoding="utf-8") as handle:
            document = json.load(handle)
    except FileNotFoundError:
        return Store(next_id=1, tasks=[])
    except json.JSONDecodeError:
        fail(f"invalid JSON in data file {path}")
    except UnicodeDecodeError:
        fail(f"data file is not valid UTF-8: {path}")

    if not isinstance(document, dict):
        fail(f"invalid data in {path}: expected a JSON object")
    version = document.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version != 1:
        fail(f"unsupported data version in {path}: {version!r}")

    next_id = document.get("next_id")
    if isinstance(next_id, bool) or not isinstance(next_id, int) or next_id < 1:
        fail(f"invalid data in {path}: next_id must be a positive integer")

    records = document.get("tasks")
    if not isinstance(records, list):
        fail(f"invalid data in {path}: tasks must be a list")

    tasks: list[Task] = []
    seen_ids: set[int] = set()
    previous_id = 0
    for record in records:
        if not isinstance(record, dict):
            fail(f"invalid data in {path}: each task must be an object")
        task_id = record.get("id")
        text = record.get("text")
        completed = record.get("completed")
        if isinstance(task_id, bool) or not isinstance(task_id, int) or task_id < 1:
            fail(f"invalid data in {path}: task IDs must be positive integers")
        if task_id in seen_ids:
            fail(f"invalid data in {path}: duplicate task ID {task_id}")
        if task_id <= previous_id:
            fail(f"invalid data in {path}: tasks must be ordered by ID")
        if not isinstance(text, str) or not text.strip():
            fail(f"invalid data in {path}: task text must be non-empty")
        if not isinstance(completed, bool):
            fail(f"invalid data in {path}: completed must be a boolean")
        tasks.append(Task(id=task_id, text=text, completed=completed))
        seen_ids.add(task_id)
        previous_id = task_id

    if next_id <= previous_id:
        fail(f"invalid data in {path}: next_id must exceed every task ID")
    return Store(next_id=next_id, tasks=tasks)


def save_store(path: Path, store: Store) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "version": 1,
        "next_id": store.next_id,
        "tasks": [
            {"id": task.id, "text": task.text, "completed": task.completed}
            for task in store.tasks
        ],
    }
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            json.dump(document, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except OSError:
                pass


def find_task(store: Store, task_id: int) -> Task:
    for task in store.tasks:
        if task.id == task_id:
            return task
    raise DaylistError(f"unknown task ID: {task_id}")


def run(args: argparse.Namespace) -> int:
    if args.data_file is None:
        path = Path("~/.daylist/tasks.json").expanduser()
    else:
        path = Path(args.data_file).expanduser()

    store = load_store(path)
    if args.command == "list":
        if not store.tasks:
            print("No tasks.")
            return 0
        for task in store.tasks:
            marker = "x" if task.completed else " "
            print(f"[{marker}] {task.id} {task.text}")
        return 0

    if args.command == "add":
        text = args.text.strip()
        if not text:
            raise DaylistError("task text must not be empty")
        task = Task(id=store.next_id, text=text, completed=False)
        store.tasks.append(task)
        store.next_id += 1
        save_store(path, store)
        print(f"Added task {task.id}.")
        return 0

    task = find_task(store, args.id)
    if args.command == "done":
        if task.completed:
            print(f"Task {task.id} is already complete.")
            return 0
        task.completed = True
        save_store(path, store)
        print(f"Completed task {task.id}.")
        return 0

    if args.command == "remove":
        store.tasks.remove(task)
        save_store(path, store)
        print(f"Removed task {task.id}.")
        return 0

    raise DaylistError(f"unsupported command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return run(args)
    except DaylistError as exc:
        print(f"daylist: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        detail = exc.strerror or str(exc)
        path = args.data_file or "~/.daylist/tasks.json"
        print(f"daylist: cannot access data file {path}: {detail}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
