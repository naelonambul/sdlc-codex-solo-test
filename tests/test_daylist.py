"""Behavioral tests for the Daylist command line."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import daylist


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "daylist.py"


class DaylistCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.directory = Path(self.temporary_directory.name)
        self.data_file = self.directory / "nested" / "tasks.json"

    def invoke(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--data-file",
                str(self.data_file),
                *arguments,
            ],
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
        )

    def invoke_default(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["HOME"] = str(self.directory)
        return subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            cwd=ROOT,
            capture_output=True,
            check=False,
            env=environment,
            text=True,
        )

    def write_v1_file(self) -> bytes:
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        document = {
            "version": 1,
            "next_id": 3,
            "tasks": [
                {"id": 1, "text": "Legacy open", "completed": False},
                {"id": 2, "text": "Legacy done", "completed": True},
            ],
        }
        content = (json.dumps(document, indent=2) + "\n").encode("utf-8")
        self.data_file.write_bytes(content)
        return content

    def test_help_lists_commands_without_creating_data(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--data-file", str(self.data_file), "--help"],
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("add", result.stdout)
        self.assertIn("list", result.stdout)
        self.assertIn("done", result.stdout)
        self.assertIn("remove", result.stdout)
        self.assertIn("--data-file", result.stdout)
        self.assertFalse(self.data_file.exists())

    def test_add_help_shows_due_option_without_creating_data(self) -> None:
        result = self.invoke("add", "--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--due YYYY-MM-DD", result.stdout)
        self.assertFalse(self.data_file.exists())

    def test_list_of_missing_file_does_not_create_it(self) -> None:
        result = self.invoke("list")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "No tasks.\n")
        self.assertFalse(self.data_file.exists())

    def test_default_file_is_created_on_first_add(self) -> None:
        result = self.invoke_default("add", "Default list")
        default_file = self.directory / ".daylist" / "tasks.json"
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "Added task 1.\n")
        self.assertTrue(default_file.is_file())
        self.assertEqual(self.invoke_default("list").stdout, "[ ] 1 Default list\n")

    def test_add_list_complete_remove_and_never_reuse_ids(self) -> None:
        first = self.invoke("add", "  Buy tea  ")
        second = self.invoke("add", "Call the dentist")
        self.assertEqual((first.returncode, first.stdout), (0, "Added task 1.\n"))
        self.assertEqual((second.returncode, second.stdout), (0, "Added task 2.\n"))

        listed = self.invoke("list")
        self.assertEqual(listed.stdout, "[ ] 1 Buy tea\n[ ] 2 Call the dentist\n")

        completed = self.invoke("done", "2")
        repeated = self.invoke("done", "2")
        self.assertEqual(completed.stdout, "Completed task 2.\n")
        self.assertEqual(repeated.stdout, "Task 2 is already complete.\n")
        self.assertEqual(self.invoke("remove", "1").stdout, "Removed task 1.\n")
        self.assertEqual(self.invoke("add", "Write a note").stdout, "Added task 3.\n")
        self.assertEqual(
            self.invoke("list").stdout,
            "[x] 2 Call the dentist\n[ ] 3 Write a note\n",
        )

        document = json.loads(self.data_file.read_text(encoding="utf-8"))
        self.assertEqual(document["version"], 2)
        self.assertEqual(document["next_id"], 4)
        self.assertEqual([task["due_date"] for task in document["tasks"]], [None, None])

    def test_add_due_date_is_persisted_and_listed(self) -> None:
        dated = self.invoke("add", "Submit report", "--due", "2026-11-05")
        undated = self.invoke("add", "Buy tea")

        self.assertEqual(dated.returncode, 0)
        self.assertEqual(undated.returncode, 0)
        self.assertEqual(
            self.invoke("list").stdout,
            "[ ] 1 Submit report (due 2026-11-05)\n[ ] 2 Buy tea\n",
        )
        document = json.loads(self.data_file.read_text(encoding="utf-8"))
        self.assertEqual(document["version"], 2)
        self.assertEqual(
            [task["due_date"] for task in document["tasks"]],
            ["2026-11-05", None],
        )
        self.assertEqual(self.invoke("done", "1").returncode, 0)
        self.assertEqual(
            self.invoke("list").stdout,
            "[x] 1 Submit report (due 2026-11-05)\n[ ] 2 Buy tea\n",
        )
        self.assertEqual(self.invoke("remove", "2").returncode, 0)
        document = json.loads(self.data_file.read_text(encoding="utf-8"))
        self.assertEqual(document["tasks"][0]["due_date"], "2026-11-05")

    def test_due_date_requires_a_real_canonical_calendar_date(self) -> None:
        valid_leap_day = self.invoke("add", "Leap day", "--due", "2024-02-29")
        self.assertEqual(valid_leap_day.returncode, 0)
        original = self.data_file.read_bytes()

        for value in ("2023-02-29", "2026-13-01", "2026-1-01", "not-a-date"):
            with self.subTest(value=value):
                result = self.invoke("add", "Invalid date", "--due", value)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("YYYY-MM-DD", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(self.data_file.read_bytes(), original)

    def test_version_one_list_does_not_rewrite_file(self) -> None:
        original = self.write_v1_file()

        result = self.invoke("list")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            result.stdout,
            "[ ] 1 Legacy open\n[x] 2 Legacy done\n",
        )
        self.assertEqual(self.data_file.read_bytes(), original)

    def test_state_changing_commands_migrate_version_one_to_version_two(self) -> None:
        operations = (
            (
                ("add", "New task"),
                4,
                [1, 2, 3],
                ["Legacy open", "Legacy done", "New task"],
                [False, True, False],
            ),
            (
                ("done", "1"),
                3,
                [1, 2],
                ["Legacy open", "Legacy done"],
                [True, True],
            ),
            (
                ("remove", "1"),
                3,
                [2],
                ["Legacy done"],
                [True],
            ),
        )
        for arguments, next_id, task_ids, texts, completed in operations:
            with self.subTest(arguments=arguments):
                self.write_v1_file()

                result = self.invoke(*arguments)

                self.assertEqual(result.returncode, 0, result.stderr)
                document = json.loads(self.data_file.read_text(encoding="utf-8"))
                self.assertEqual(document["version"], 2)
                self.assertEqual(document["next_id"], next_id)
                self.assertEqual([task["id"] for task in document["tasks"]], task_ids)
                self.assertEqual([task["text"] for task in document["tasks"]], texts)
                self.assertEqual(
                    [task["completed"] for task in document["tasks"]], completed
                )
                self.assertTrue(all("due_date" in task for task in document["tasks"]))
                self.assertEqual(
                    [task["due_date"] for task in document["tasks"]],
                    [None] * len(task_ids),
                )

    def test_repeated_done_does_not_migrate_version_one_file(self) -> None:
        original = self.write_v1_file()

        result = self.invoke("done", "2")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "Task 2 is already complete.\n")
        self.assertEqual(self.data_file.read_bytes(), original)

    def test_invalid_version_two_due_dates_are_preserved(self) -> None:
        invalid_documents = [
            {
                "version": 2,
                "next_id": 2,
                "tasks": [
                    {
                        "id": 1,
                        "text": "Invalid date",
                        "completed": False,
                        "due_date": invalid_due_date,
                    }
                ],
            }
            for invalid_due_date in ("2023-02-29", "2026-1-01", 1, True)
        ]
        invalid_documents.append(
            {
                "version": 2,
                "next_id": 2,
                "tasks": [{"id": 1, "text": "Missing date", "completed": False}],
            }
        )
        for document in invalid_documents:
            with self.subTest(document=document):
                self.data_file.parent.mkdir(parents=True, exist_ok=True)
                content = (json.dumps(document, indent=2) + "\n").encode("utf-8")
                self.data_file.write_bytes(content)

                result = self.invoke("list")

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(str(self.data_file), result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(self.data_file.read_bytes(), content)

    def test_data_file_override_keeps_lists_separate(self) -> None:
        alternate = self.directory / "alternate.json"
        self.assertEqual(self.invoke("add", "Primary").returncode, 0)
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--data-file",
                str(alternate),
                "add",
                "Alternate",
            ],
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.invoke("list").stdout, "[ ] 1 Primary\n")
        self.assertEqual(
            subprocess.run(
                [sys.executable, str(SCRIPT), "--data-file", str(alternate), "list"],
                cwd=ROOT,
                capture_output=True,
                check=False,
                text=True,
            ).stdout,
            "[ ] 1 Alternate\n",
        )

    def test_empty_task_text_and_invalid_ids_fail_without_writing(self) -> None:
        blank = self.invoke("add", "   ")
        invalid = self.invoke("done", "0")
        self.assertNotEqual(blank.returncode, 0)
        self.assertIn("must not be empty", blank.stderr)
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn("positive integer", invalid.stderr)
        self.assertFalse(self.data_file.exists())

    def test_unknown_ids_leave_data_unchanged(self) -> None:
        self.assertEqual(self.invoke("add", "Keep").returncode, 0)
        original = self.data_file.read_bytes()
        for command in ("done", "remove"):
            result = self.invoke(command, "99")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unknown task ID", result.stderr)
            self.assertEqual(self.data_file.read_bytes(), original)

    def test_malformed_or_unsupported_data_is_preserved(self) -> None:
        for content in (b"{broken", b'{"version": 3, "next_id": 1, "tasks": []}'):
            with self.subTest(content=content):
                self.data_file.parent.mkdir(parents=True, exist_ok=True)
                self.data_file.write_bytes(content)
                result = self.invoke("add", "Do not overwrite")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(str(self.data_file), result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(self.data_file.read_bytes(), content)

    def test_write_failure_keeps_existing_file_and_removes_temporary_file(self) -> None:
        original = self.write_v1_file()
        store = daylist.load_store(self.data_file)
        store.tasks[0].completed = True
        with patch(
            "daylist.os.replace", side_effect=OSError("simulated replace failure")
        ):
            with self.assertRaises(OSError):
                daylist.save_store(self.data_file, store)
        self.assertEqual(self.data_file.read_bytes(), original)
        self.assertEqual(list(self.data_file.parent.glob(".tasks.json.*.tmp")), [])

    def test_file_error_is_concise_and_does_not_show_traceback(self) -> None:
        blocker = self.directory / "not-a-directory"
        blocker.write_text("file", encoding="utf-8")
        self.data_file = blocker / "tasks.json"
        result = self.invoke("add", "Cannot save")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("daylist:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
