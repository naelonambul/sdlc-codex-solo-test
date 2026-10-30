# Implementation Plan

## Summary

Implement the approved Daylist specification as a standard-library Python CLI, register reproducible build, test, lint, format, and type checks, and establish the approved intent and specification as the root product baseline before closing the change.

## Files and components that change

- `daylist.py`: command parsing, JSON storage, task operations, and user-facing errors.
- `tests/test_daylist.py`: standard-library tests using temporary data files and isolated CLI invocations.
- `README.md`: Python requirement, usage examples, data-file override, and development check commands.
- `pyproject.toml`: Ruff and mypy configuration targeting Python 3.9.
- `requirements-dev.txt`: pinned Ruff and mypy development dependencies.
- `checks.json`: register the CLI build and unit checks in `core`, and Ruff and mypy checks in a separate `python-quality` group. Keep `core` dependent only on Python and Git.
- `.github/workflows/repository.yml`: install the development dependencies, run `repo.py verify --group python-quality`, upload its evidence, and add the job to `summary.needs`.
- Root `intent.md` and `spec.md`: replace the unestablished baseline with the approved packet copies after implementation and verification.
- `changes/daylist-cli/closure.json`: generated from the final full verification evidence.

## Order of work

1. **Implement and document the CLI.** Change `daylist.py`, `tests/test_daylist.py`, and `README.md`. Implement the approved commands and JSON behavior, atomic file replacement, and expected error handling. Cover the acceptance criteria with standard-library tests that use temporary files and do not touch the user's default task file. Proof: `python3 -m unittest discover -s tests -v`.

2. **Register and wire the Python quality gates.** Change `pyproject.toml`, `requirements-dev.txt`, `checks.json`, and `.github/workflows/repository.yml`. Pin Ruff and mypy; register `py_compile` and unit tests in `core`, and Ruff lint, Ruff format check, and strict mypy in `python-quality`. The workflow job installs the pinned tools, runs the quality group, uploads evidence, and is included in the required `summary` job. Proof: `python3 scripts/repo.py status --change daylist-cli` confirms the check groups and workflow jobs agree. **Owner handoff:** the GitHub App cannot push workflow files. Once the workflow change is reviewable, stop and have the owner push it to this branch; then make a real source or documentation follow-up commit as the App so the App is the last pusher, and rerun the affected checks.

3. **Run the complete check set before baseline replacement.** No source files change; `repo.py verify` writes evidence under `.evidence/`. Run the full registered suite after the workflow handoff and App follow-up. Proof: `python3 scripts/repo.py verify --change daylist-cli --full` reports a complete run with every check passed.

4. **Establish the product baseline.** Replace root `intent.md` and `spec.md` with the approved copies from `changes/daylist-cli/`. Proof: `cmp -s changes/daylist-cli/intent.md intent.md && cmp -s changes/daylist-cli/spec.md spec.md`.

5. **Verify and close.** After baseline replacement, run `python3 scripts/repo.py verify --change daylist-cli --full` again. Use that complete evidence file with `python3 scripts/repo.py close daylist-cli --evidence .evidence/<full-run>/evidence.json` to create `changes/daylist-cli/closure.json`. Proof: `python3 scripts/repo.py status --change daylist-cli` reports a current candidate closure and readiness ready. Commit and push the closure, then open one pull request with `Change-ID: daylist-cli`; record the CI `summary` result in the pull request and review the change against `REVIEW.md`.

## Tests and proof

- During CLI work: `python3 -m unittest discover -s tests -v`.
- Canonical registered checks: Python compilation, unit tests, `ruff check daylist.py tests`, `ruff format --check daylist.py tests`, and `mypy --strict daylist.py`.
- Before and after replacing the root baseline: `python3 scripts/repo.py verify --change daylist-cli --full`. Only the post-replacement complete evidence is cited by the closure.
- Before closure: `python3 scripts/repo.py status --change daylist-cli`, followed by review against `REVIEW.md`.

## Risks and mitigations

- A malformed or partially written JSON file could lose task data. Validate the complete schema, preserve malformed files, write to a same-directory temporary file, and replace atomically; test these failure paths.
- Concurrent writers can overwrite one another. The specification limits support to one writer per data file; document this limitation.
- The GitHub App cannot push `.github/workflows/**`. Treat the workflow push as an owner handoff, then make an App-authored follow-up change and rerun full verification before closure.
- Ruff and mypy require installation. Pin them in `requirements-dev.txt` and install that file in the dedicated CI job rather than relying on globally installed tools.

## Rollback or recovery

Before merge, abandon the change branch if the product is rejected; the approved root baseline remains unchanged until the baseline-replacement step. After merge, treat the packet as frozen and use a new change to revise or remove the product. Daylist tests always use temporary data files and must not modify a developer's real task list.

## Open questions

None.
