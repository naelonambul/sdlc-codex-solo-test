# Intent

## Problem

People who spend time in a terminal need a quick way to remember and manage a short personal task list without switching to a larger app or maintaining ad hoc notes.

## Proposed outcome

Daylist is a small command-line checklist for one person. It lets someone add tasks, review their status, mark tasks complete, and remove tasks. A task may have an optional due date that appears in the list. The list persists between runs in a local file, with a simple way to select another file for backup or a separate list.

## Affected users and systems

- A person using a command line on a computer with Python 3.9 or newer.
- The user's local filesystem, where Daylist keeps its task data.

## Constraints

- The tool works offline and does not send task text or other data anywhere.
- Runtime behavior uses Python's standard library and requires no account, service, or background process.
- Task data stays in a user-controlled local file.
- Adding, completing, and removing tasks are explicit user actions.

## Out of scope

- Multi-user lists, synchronization, accounts, or network services.
- Reminders, recurring tasks, priorities, or project management features.
- A graphical interface.

## Success criteria

- A user can add a task, list tasks with clear identifiers and completion status, mark a task complete, and remove a task from the terminal.
- A user can give a task an optional due date and see it when listing tasks.
- Task identifiers remain usable across runs, and saved tasks persist between invocations.
- A user can choose an alternate data file without changing the default list.
- The tool explains its commands through built-in help and gives clear errors for invalid input or unknown task identifiers.
- The tool works without network access or third-party runtime packages.

## Open questions

None for this deliberately small, local, single-user first version.
