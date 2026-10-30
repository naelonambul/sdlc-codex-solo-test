# Specification

## Summary

Daylist is a local, single-user task checklist invoked from the terminal with Python 3.9 or newer. It stores tasks in a JSON file and supports adding, listing, completing, and removing tasks.

## Requirements

### Functional

- Support these commands:
  - `python3 daylist.py add TEXT`
  - `python3 daylist.py list`
  - `python3 daylist.py done ID`
  - `python3 daylist.py remove ID`
- Accept an optional `--data-file PATH` before the command. Expand `~` in the path; interpret a relative path from the current working directory.
- Use `~/.daylist/tasks.json` when `--data-file` is omitted.
- For `add`, trim whitespace from the beginning and end of `TEXT`, reject an empty result, allocate a positive integer ID, and save the task as incomplete. IDs increase monotonically and are never reused after removal.
- For `list`, show all tasks in ascending ID order, including completed tasks. Show each ID, a clear incomplete or complete marker, and the task text. If no data file exists or the list is empty, print `No tasks.` without creating a file.
- For `done ID`, mark the matching task complete. Repeating the command for an already completed task succeeds without changing its state. An unknown ID is an error and does not change the file.
- For `remove ID`, remove the matching task. An unknown ID is an error and does not change the file.
- Create the default data directory and file when the first task is added. Do not create the data file for read-only commands or failed mutations.
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
- `list` uses `[ ]` for incomplete tasks and `[x]` for completed tasks, preserving the task text as entered apart from trimming its outer whitespace.
- Invalid command syntax uses the argument parser's help and error behavior. Invalid IDs, unknown tasks, inaccessible paths, malformed JSON, and unsupported data versions produce a concise error.

## Architecture and design

- Keep the first version as a single `daylist.py` module that can be run directly with `python3 daylist.py`; installation as a package is not required.
- Use the standard-library argument parser for the command interface and JSON for persistence.
- Treat a missing data file as an empty list. Validate the JSON version and task records when loading an existing file. Never silently replace malformed or unsupported data with an empty list.
- Write updated data to a temporary file in the destination directory, then replace the destination so an interrupted write does not truncate the previous file. Remove the temporary file after a failed write when possible.
- Support one process at a time writing a given data file. Concurrent writers and conflict resolution are out of scope.

## Interfaces, data, and dependencies

CLI grammar:

```text
python3 daylist.py [--data-file PATH] {add,list,done,remove} ...
```

The version 1 JSON document contains `version`, `next_id`, and `tasks`. Each task contains a unique positive integer `id`, non-empty string `text`, and boolean `completed`. `next_id` is greater than every ID already allocated. The stored task list is ordered by ID. For example:

```json
{
  "version": 1,
  "next_id": 3,
  "tasks": [
    {"id": 1, "text": "Buy tea", "completed": false},
    {"id": 2, "text": "Call the dentist", "completed": true}
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
- Concurrent writes can overwrite one another; the first version explicitly supports one writer at a time.
- The default hidden directory may not match every user's backup preferences; `--data-file` provides a way to choose a path.

## Acceptance criteria

- Help shows the four commands and the data-file option without reading or creating a data file.
- With an isolated data-file path, a user can add two tasks, list both with stable IDs and correct states, complete one, and remove the other.
- Re-running the CLI preserves task state and does not reuse an ID after removal.
- Listing a missing file prints `No tasks.` and leaves the path absent; the first successful add creates its parent directory and valid JSON data.
- Blank task text, invalid or unknown IDs, malformed JSON, unsupported versions, and file permission errors fail clearly without destroying existing data.
- The CLI runs without network access and without third-party runtime packages on Python 3.9 or newer.

## Open questions

None. The first version is intentionally local, single-user, and limited to basic task management.
