# Implementation Plan

## Summary

Add optional calendar due dates to Daylist, store them in version 2 JSON, and keep valid version 1 files usable until a successful state-changing command rewrites them as version 2.

## Files and components that change

- `daylist.py`: add and validate the `add --due` argument, display due dates, load versions 1 and 2, and write all newly created or mutated data as version 2.
- `tests/test_daylist.py`: cover due-date parsing and display, version 1 read and migration behavior, version 2 validation and round-tripping, and preservation of files on failures.
- `README.md`: document the due-date option, its list display, and version 1 migration behavior.
- `changes/due-dates/intent.md` and `changes/due-dates/spec.md`: approved copies to promote to the root baseline during closure.

## Order of work

1. Update `daylist.py` and `tests/test_daylist.py`. Add the nullable task due-date field; strictly validate command-line and stored dates; load version 1 tasks with no due date; write version 2 on actual mutations; and preserve atomic writes. Add regression coverage for the accepted spec, including read-only version 1 listing, migration through add/done/remove, no-op `done`, invalid dates, and failed writes. Prove the step with `python3 -m unittest discover -s tests -v`.
2. Update `README.md` with an `add --due` example, the list output form, and the version 1 migration note. Prove the documented details are present with `python3 -c 'from pathlib import Path; text = Path("README.md").read_text(); assert "--due" in text and "due date" in text and "version 1" in text'`.

## Tests and proof

- During implementation, run the focused Daylist suite with `python3 -m unittest discover -s tests -v`.
- Before closure, run `python3 scripts/repo.py status --change due-dates` and `python3 scripts/repo.py verify --change due-dates --full`. The full verification must pass every registered check and produce complete evidence; cite that evidence when closing.
- Review the final diff against `REVIEW.md`, with particular attention to migration preserving task IDs, text, completion state, and `next_id`, and to keeping the original file intact when a write fails.
- No `checks.json` change is planned: existing registered checks cover `daylist.py` and `tests/**`, and the required full verification also runs the repository quality checks.

## Risks and mitigations

- A migration bug could damage an existing list. Validate the complete input before mutation, retain the existing same-directory temporary-file and atomic-replace write, and test failed replacement against a version 1 file.
- After a successful version 2 write, the previous application version will reject that file as unsupported. Do not add an unrequested backup format; users who need rollback must retain or restore their own copy, while the new version continues to read both formats.
- Strict date validation can accidentally accept noncanonical or impossible dates. Test exact `YYYY-MM-DD` formatting and calendar validity, including valid and invalid leap days.

## Rollback or recovery

- If implementation or verification fails before merge, keep the change open and correct it within this packet; version 1 files remain untouched until a successful mutation under the new code.
- Once a version 2 file has been written, recover with a version 2-capable Daylist or restore a user-held backup before using the previous application version. The atomic write protects against partial replacement, not application-version rollback.
- Any post-merge reversal follows the repository's new-change process; do not rewrite or remove the frozen packet.

## Open questions

None beyond the approved specification.
