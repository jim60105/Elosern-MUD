## Why

The approved design (`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §11.1 case 10) requires real-browser coverage of the editor's hard cases — stale-result correlation, target departure, session/puppet changes, and cross-tab conflicts — not only component tests. `npc-persona-editor-window` already specifies these behaviors and proves them with Vitest plus the core browser journeys; this change adds the slower multi-page and multi-entity browser evidence separately so the window change stays one workday and each browser file stays under the five-minute CI bound.

## What Changes

- Add `web/tests/browser/test_browser_npc_persona_editor_edges.py` with focused methods: a late read for a closed editor does not seed the next editor for another NPC; the bound NPC leaving the room keeps the dirty draft with save disabled and recovers when it returns; switching the puppet closes the editor and leaves no card text in the store or browser storage; two pages edit the same NPC, the second save shows the conflict with its draft intact, and reload shows the first page's card at the new version.
- Extend the editor seed fixture only as needed (second NPC, movement hook, second character for the puppet switch).
- Register every method in `.github/browser-shards.json`.

No production code or spec requirement changes (`skip_specs: true`); behavior is owned by `webclient-npc-persona-editor`, and these tests are annotated with its requirement IDs.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None (test evidence only).

## Impact

- Tests: one new browser module, seed fixture additions under `web/tests/browser/seed/`, `.github/browser-shards.json`.

## Batch:

depends-on: npc-persona-editor-window

Code-conflict notes: touches only browser test files and `.github/browser-shards.json` (append-only; adjacent-line rebase conflicts only). If a test exposes a defect in the window change's code, fix it here in the same change and note it, keeping the window's spec unchanged unless the defect is in the spec.
