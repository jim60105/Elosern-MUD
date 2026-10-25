# Design

## Context

Observed DialogueChoices maps passive pick rows into ChoiceCard and dispatches through the single store entry. A locked topic must remain selectable for refusal, unlike an operationally disabled action row. UI must render server facts rather than reevaluate conditions.

## Goals / Non-Goals

**Goals:** Visible locked topic refusal and accessible canonical hints. Deliver this runnable slice and its acceptance within one engineer-day.

**Non-Goals:** Unowned runtime/content work, compatibility migrations, new game effects and per-line server stepping.

## Decisions

Use panel.choice.availability and requirement_hint verbatim. Hidden rows never exist client-side. A locked formal topic remains an enabled pick with a lock glyph and text accessible name; activation uses its server action payload to play the refusal. Do not put aria-disabled on a row that intentionally dispatches refusal, or convert the topic into an unselectable tooltip. Operational in-flight/action-unavailable states still use the existing disabled convention and emit nothing. Add pointer hover and keyboard focus hints associated with aria-describedby, no focusable tooltip or modal, no numeric relationship details. Empty hints do not produce empty tooltip containers.

Use Shared contract v1 and manual player; distinguish selection outcomes by delivered kind. Refusal final activation returns to choices, emits no formal completion and reveals no successor. Keep all <=16 ordered rows reachable through the existing list/scroll/keyboard navigation, with no four-row clipping. Dynamically changed state retains active topic by stable topic_id if present, otherwise nearest remaining row; hiding current topic must not strand focus. Choices remain hidden during scene playback. An availability refresh changes the next choice projection without switching current lines/portrait. No client condition arithmetic or local unlock guesses for qualified content.

Add component/story fixtures containing open/locked/hidden-absent rows and long requirement hints under desktop token scaling. Inspect app-shell.css overrides for the classes edited; reuse ChoiceCard semantics rather than a second list. Actual browser method verifies keyboard focus hint, pointer hint, selectable refusal and absence of formal completion/body. No notification/read marker work here except preserving declared unread field for later owner.

## Implementation handoff constraints

This proposed slice is capped at one engineer-day. Each numbered task is intended as a 45-120 minute implementation-and-focused-test unit; tests/docs land with their owning behavior. Use a local untracked `.env.test` containing `MUD_TEST_SETTINGS=1` for the commands below (create that environment file only at apply time). Run focused commands from the repository root; new test labels are explicitly proposed, existing labels are regression targets. Also run `uv run --locked python -m tools.contract_gate` before implementation handoff, with test ownership updates in the same feature commit. No live external model/image requests. Planning created no production code or test results.

Boundary events use the existing world.observability facade with available owner/actor/npc/topic/context identifiers; exceptions rethrow or log once with exc. No new telemetry subsystem. No compatibility shim, legacy aliases, data backfill or migration. No executable dialogue scripts, mid-scene choice tree, per-line server stepping/persistence or new gameplay effects.


## Exact target files

- `web/webclient-app/components/DialogueChoices.vue`
- `web/webclient-app/components/ChoiceCard.vue`
- `web/webclient-app/stores/dialogue-view.js`
- `web/webclient-app/composables/use-dialogue-choices.js`
- `web/webclient-app/styles/app-shell.css`

## Risks / Trade-offs

Frontend overlap with reading-client/notices in choices/composable/view model requires scheduling after this UI change for those slices. Keep authored source validation separate from runtime eligibility. A failed post-commit push recovers on the next canonical sync, without reversing a successful owning commit. Read the approved design and dependency artifacts before edits; no interface decision is left open.

## Focused verification at implementation time

```text
pnpm exec vitest run web/webclient-app/tests/dialogue_choices.test.js web/webclient-app/tests/app_client_dialogue_choices.test.js
uv run --locked python -m tools.contract_gate
```

Run only focused test labels/methods within the repository time limits. Full managed browser and evidence suites remain CI-owned. These commands are planned acceptance, not results from proposal creation.
