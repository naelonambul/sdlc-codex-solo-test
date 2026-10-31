# Specification

## Summary

Daylist is a local, single-user task checklist invoked from the terminal with Python 3.9 or newer. It stores tasks in a JSON file and supports adding, listing, completing, and removing tasks. A task may have an optional calendar due date. The data format is version 2, and valid version 1 files remain usable and migrate on their next successful write.

## Requirements

### Functional

- Support these commands:
  - `python3 daylist.py add TEXT [--due YYYY-MM-DD]`
  - `python3 daylist.py list`
  - `python3 daylist.py done ID`
  - `python3 daylist.py remove ID`
- Accept an optional `--data-file PATH` before the command. Expand `~` in the path; interpret a relative path from the current working directory.
- Use `~/.daylist/tasks.json` when `--data-file` is omitted.
- For `add`, trim whitespace from the beginning and end of `TEXT`, reject an empty result, allocate a positive integer ID, and save the task as incomplete. IDs increase monotonically and are never reused after removal.
- For `add`, accept an optional `--due` after `TEXT`. Its value must be a real calendar date in exactly `YYYY-MM-DD` form. Reject malformed or impossible dates without changing the data file. If omitted, the task has no due date.
- For `list`, show all tasks in ascending ID order, including completed tasks. Show each ID, a clear incomplete or complete marker, and the task text. If a task has a due date, append ` (due YYYY-MM-DD)` to its line. If it has no due date, keep the existing line format. If no data file exists or the list is empty, print `No tasks.` without creating a file.
- For `done ID`, mark the matching task complete. Repeating the command for an already completed task succeeds without changing its state or writing the file. An unknown ID is an error and does not change the file.
- For `remove ID`, remove the matching task. An unknown ID is an error and does not change the file.
- Create the default data directory and file when the first task is added. Do not create or rewrite the data file for read-only commands or failed mutations.
- Show built-in command help. Do not prompt interactively.

### Non-functional

- Support Python 3.9 and newer using only the Python standard library at runtime.
- Operate offline; task content never leaves the selected local data file.
- Keep successful command output concise and deterministic. Send errors to standard error, return a nonzero exit status for invalid input, invalid stored data, unknown IDs, and file errors, and do not show a traceback for expected errors.
- Preserve an existing valid data file if a write fails partway through.

## User experience and behavior

- `TEXT` is one shell argument; users quote text containing spaces, for example `python3 daylist.py add "Buy tea"`.
- `--data-file` is a global option and appears before the command, for example `python3 daylist.py --data-file ./work.json list`.
- Successful `add`, `done`, and `remove` commands report the affected ID. `done` on an already completed task reports that it is already complete and exits successfully.
- `list` uses `[ ]` for incomplete tasks and `[x]` for completed tasks, preserving task text as entered apart from trimming its outer whitespace. For example, a task with a due date is displayed as `[ ] 1 Submit report (due 2026-11-05)`.
- Invalid command syntax uses the argument parser's help and error behavior. Invalid IDs, unknown tasks, inaccessible paths, malformed JSON, invalid due dates, and unsupported data versions produce a concise error.

## Architecture and design

- Keep the CLI in the single `daylist.py` module, runnable with `python3 daylist.py`; installation as a package is not required.
- Use the standard-library argument parser for the command interface and JSON for persistence.
- Treat a missing data file as an empty list. Validate the JSON version and task records when loading an existing file. Never silently replace malformed or unsupported data with an empty list.
- Read version 1 and version 2 data files. A version 1 task has no due date and loads with an in-memory due date of `None`.
- Write all newly created data and all successful state-changing mutations as version 2. This includes adding, completing an incomplete task, and removing a task. A repeated `done ID` on an already completed task performs no write, so it does not migrate a version 1 file. Read-only commands and failed mutations do not migrate a file.
- Write updated data to a temporary file in the destination directory, then replace the destination so an interrupted write does not truncate the previous file. Remove the temporary file after a failed write when possible.
- Support one process at a time writing a given data file. Concurrent writers and conflict resolution are out of scope.

## Interfaces, data, and dependencies

CLI grammar:

```text
python3 daylist.py [--data-file PATH] add TEXT [--due YYYY-MM-DD]
python3 daylist.py [--data-file PATH] {list|done ID|remove ID}
```

Version 1 documents keep their existing shape: the top-level object contains `version`, `next_id`, and `tasks`; each task contains a unique positive integer `id`, non-empty string `text`, and boolean `completed`. `next_id` is greater than every ID already allocated, and tasks are ordered by ID. Version 1 task records are interpreted as having no due date.

Every version 2 task contains `id`, `text`, `completed`, and `due_date`. `due_date` is either `null` or a valid calendar date in canonical `YYYY-MM-DD` form. Version 2 documents retain the top-level `version`, `next_id`, and `tasks` fields. For example:

```json
{
  "version": 2,
  "next_id": 3,
  "tasks": [
    {"id": 1, "text": "Submit report", "completed": false, "due_date": "2026-11-05"},
    {"id": 2, "text": "Buy tea", "completed": false, "due_date": null}
  ]
}
```

There are no runtime dependencies outside Python's standard library. Development and CI tools are specified separately in the implementation plan.

## Security, privacy, and policy constraints

- Daylist reads and writes only the selected local data file and does not make network requests, launch subprocesses, or collect telemetry.
- Treat task text as plain text; never evaluate or execute content loaded from JSON.
- File paths and task data belong to the invoking user. Do not log task text on errors unrelated to displaying the list.

## Risks and concerns

- Manual edits or storage failures can leave invalid JSON. Detect this, report the selected file path, and leave the file untouched rather than discarding user data.
- Version 1 migration replaces a file on its next successful mutation. Use the existing atomic-write approach so a failed migration write preserves the original version 1 file.
- Concurrent writes can overwrite one another; Daylist supports one writer at a time.
- The default hidden directory may not match every user's backup preferences; `--data-file` provides a way to choose a path.

## Acceptance criteria

- Help shows the four commands, the global data-file option, and the add command's due-date option without reading or creating a data file.
- With an isolated data-file path, a user can add tasks with and without due dates, list them with stable IDs and correct states, complete one, and remove another. Listing shows each due date and leaves lines for undated tasks in the existing format.
- Valid dates are accepted, including leap-day dates when valid for that year. Malformed dates and impossible calendar dates fail without changing or creating the data file.
- A valid version 1 file can be listed without modification. Its tasks show no due date. The next successful state-changing mutation writes version 2, preserves IDs, text, completion state, and `next_id`, and gives undated tasks `due_date: null`.
- Repeating `done ID` for an already completed task succeeds without modifying a version 1 file. A later successful mutation migrates it to version 2.
- Version 2 data round-trips due dates through add, list, done, and remove operations. Invalid version 2 due-date values or missing `due_date` fields fail clearly without destroying the file.
- Re-running the CLI preserves task state and does not reuse an ID after removal.
- Listing a missing file prints `No tasks.` and leaves the path absent; the first successful add creates its parent directory and valid version 2 JSON data.
- Blank task text, invalid or unknown IDs, malformed JSON, unsupported versions, and file errors fail clearly without destroying existing data.
- The CLI runs without network access and without third-party runtime packages on Python 3.9 or newer.

## Open questions

None. The due-date field, output format, and version 1 migration behavior are specified above.
