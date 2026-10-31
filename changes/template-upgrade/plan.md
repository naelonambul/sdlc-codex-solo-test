# Implementation Plan

## Summary

Update the control plane, skills and docs from the template at commit 184b5ef, so later changes use the current gates.

## Files and components that change

The files listed in `write_scope`, copied unchanged from the template. The product `README.md` stays as it is.

## Order of work

1. Copy the files.
2. Run `python3 scripts/repo.py verify --change template-upgrade --full`.

## Tests and proof

The full registered check run passes.

## Risks and rollback

The frozen `daylist-cli` closure has no `tree_sha256`, which stays valid. To undo, open a new change.
