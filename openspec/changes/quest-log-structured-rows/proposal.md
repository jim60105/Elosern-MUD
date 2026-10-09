# Proposal

## Why

The `quest_log` panel ships each quest's whole description as one pre-rendered `detail` blob and its reward as a prefixed `reward_line` string. The approved quest drawer redesign (`docs/superpowers/specs/2026-10-09-quest-drawer-redesign-design.md`, §4.1) needs structured fields it can lay out: category, grade, objective note, rating rationale, background flavor, a structured reward, and claim state. In the live client the blob repeats every other field as a run-on paragraph and the reward renders as 獎勵：獎勵：.

## What Changes

- **BREAKING** `quest_log` moves to schema version 2. Each row drops `detail` and `reward_line` and gains `category`, `grade`, `objective_note`, `rationale`, `flavor`, `reward`, and `reward_claimed`. `objective_line` no longer carries the species-hunt variant clause; that clause moves to `objective_note`.
- The commission-coherence rule moves from `reward_line` to `reward`: `settlement` and `reward` are null together or present together.
- New describe seams split an objective into its line and its optional note and build a structured reward. The existing `describe_objective()` and `describe_reward()` text output stays byte-identical, so `guild show`, the objective tracker, and the `services` counter rows are unchanged.
- The Python validator, the JS mirror, the schema-version parity contract, and the protocol and story fixtures move to v2 together. Story fixtures switch to realistic content: real catalog prose, the full branch name, item rewards, and a deadline.
- The current `QuestLog.vue` is adapted only enough to keep rendering from v2 (reward from the structured object, flavor in place of the dropped detail). The drawer redesign replaces it in `quest-drawer-book-tab`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-quest-log-panel`: version-2 row field set; prose and reward sources; null pairing moves to `reward`; claim-state disclosure.
- `webclient-service-menus`: the quest book's reward disclosure renders the structured reward instead of `reward_line`.

## Impact

`world/quests/describe.py`; `web/webclient/presentation/quest_log.py` and its tests; `web/static/webclient/js/elosern/protocol/panels/quest_log.js` and `constants.js`; `web/static/webclient/js/tests/` protocol fixtures and quest-log tests; `tests/test_quest_log_parity_contract.py`; `tests/test_panel_schema_version_parity_contract.py`; `web/webclient-app/stories/fixtures/quest_log_panels.js`; `web/webclient-app/components/QuestLog.vue` and `tests/world/quest_log.test.js`.

## Non-goals

No drawer redesign UI (later changes). No change to the `services` panel, the `objectives` panel, `guild show`, quest rules, issuance registration, or reward settlement. No compatibility shim for v1: the project is unreleased.

## Batch:

```text
depends-on: (none)
code-conflicts: guild-board-structured-offers (describe.py, protocol fixtures, constants.js), quest-drawer-book-tab (QuestLog.vue, quest_log story fixtures)
```

First in the quest drawer redesign set. It can run in parallel with `quest-drawer-ui-primitives`. `guild-board-structured-offers` and `quest-drawer-book-tab` start after this change is merged.

Archive strictly in this order: `quest-log-structured-rows` → `guild-board-structured-offers` → `quest-drawer-book-tab` → `quest-drawer-guild-board-tab`. `quest-drawer-ui-primitives` has no deltas and can archive any time after it merges. Any other order fails `openspec archive`: `quest-drawer-book-tab` REMOVES a requirement that `quest-log-structured-rows` MODIFIES, and `quest-drawer-guild-board-tab` adds to the capability that `quest-drawer-book-tab` creates and REMOVES a requirement that `guild-board-structured-offers` adds.

## Worker profile

**Logic.** Server presenters, validators, JS protocol mirrors, and contract tests. The interim Vue edit is a field swap with no aesthetic judgment, so any capable worker can take this; visual ability is not needed.

## Size and standalone delivery

About 7 hours: describe seams and their byte-identity tests (1.5h), the presenter and validator at v2 (2h), the JS mirror, constants, and parity contracts (1.5h), fixtures (1h), and the minimal `QuestLog.vue` adaptation with its Vitest update (1h). It is deployable alone: the live quest book keeps working on v2.
