# Design

## Context

Observed MessageWindow already measures pages, supports typewriter, surface click, Space/Enter and focusHome, plus combat beat timers. use-dialogue-choices currently treats reconnect as reading complete; this conflicts with scene replay. elosern/view.js currently infers speaker from in-flight speech actions.

## Goals / Non-Goals

**Goals:** Shared manual Vue scene player and synchronized stage attribution. Deliver this runnable slice and its acceptance within one engineer-day.

**Non-Goals:** Unowned runtime/content work, compatibility migrations, new game effects and per-line server stepping.

## Decisions

Use Shared contract v2 for both static and generated SceneDelivery. No source-based single-line conversion, static-profile predicate or separate generated player. Canonical generated topic/scene IDs <=2048 bytes stay opaque through view admission, replay and transcript dedup; aggregate byte budgets apply unchanged. The shared player rules below apply to both sources.

Reuse MessageWindow pagination/typewriter and portrait catalog/artwork lifecycle. Add useAuthoredScene(delivery, context) exposing lineIndex, line, speaker, readingComplete, advance(), retire(), and a single scene-finished event. The composable is presentation-only, has no store dispatch/effect imports, and never changes the server clock. AppClient binds active line text/name and stage speaker synchronously. Actor portrait/name come from panel.actor, so possession needs no second renderer.

While typing, activation finishes the current page; next activation advances page then line. The last fully visible page still requires a further activation to finish. Long-line pages keep speaker. Narration has no name and neither portrait emphasized. Two consecutive same-speaker lines remain separate reading steps. Never arm combat beat auto-page timers for authored scenes. Reuse text speed/reduced motion; reduced motion may reveal text at once but must not auto-advance. Keyboard only consumes unmodified nonrepeated Space/Enter on the focused message surface; selection, links, buttons, command entry and overlays keep existing behavior.

New delivery_id or mounted reconnect starts at line one regardless of saved reading. Same delivery_id on availability-only refresh retains local page/line and chosen variant. Changed context/phase/mode or unavailable panel retires the player without a finished event. Keep full attributed transcript once per delivered scene, with speaker names stored as displayed at delivery; page advances do not append duplicate history. Reconnect replay keeps historic transcript and does not create a second selection/effect. Choices hide until the explicit finish action and restore focus only if it was in message/list/body; drawers/command field never lose focus. The finish event is locally usable before persistence lands and is wired by the reading-client slice.

Browser acceptance belongs here, not a final catch-all. Add a deterministic multi-line fixture with actor, same-host consecutive lines, narration and one long line; exercise real AppClient portraits in the browser (art placeholders count as real catalog entries). Preserve combat beat choreography and normal message behavior with their existing tests. The target remains desktop 16:9 with existing --ui-scale and --text/--motion tokens; no mobile/gamepad redesign.

## Implementation handoff constraints

This proposed slice is capped at one engineer-day. Each numbered task is intended as a 45-120 minute implementation-and-focused-test unit; tests/docs land with their owning behavior. Use a local untracked `.env.test` containing `MUD_TEST_SETTINGS=1` for the commands below (create that environment file only at apply time). Run focused commands from the repository root; new test labels are explicitly proposed, existing labels are regression targets. Also run `uv run --locked python -m tools.contract_gate` before implementation handoff, with test ownership updates in the same feature commit. No live external model/image requests. Planning created no production code or test results.

Boundary events use the existing world.observability facade with available owner/actor/npc/topic/context identifiers; exceptions rethrow or log once with exc. No new telemetry subsystem. No compatibility shim, legacy aliases, data backfill or migration. No executable dialogue scripts, mid-scene choice tree, per-line server stepping/persistence or new gameplay effects.


## Exact target files

- `web/webclient-app/composables/use-authored-scene.js (new)`
- `web/webclient-app/components/MessageWindow.vue`
- `web/webclient-app/composables/use-dialogue-choices.js`
- `web/webclient-app/stores/dialogue-view.js`
- `web/webclient-app/stores/elosern/view.js`
- `web/webclient-app/AppClient.vue`
- `web/webclient-app/components/StageActor.vue`

## Risks / Trade-offs

Conflicts with reading-client and availability UI in AppClient, use-dialogue-choices and dialogue-view; those depend on this slice. Combat behavior must remain unchanged. Keep authored source validation separate from runtime eligibility. A failed post-commit push recovers on the next canonical sync, without reversing a successful owning commit. Read the approved design and dependency artifacts before edits; no interface decision is left open.

## Focused verification at implementation time

```text
pnpm exec vitest run web/webclient-app/tests/message_window_dialogue.test.js web/webclient-app/tests/app_client_dialogue_choices.test.js
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_exploration_dialogue
uv run --locked python -m tools.contract_gate
```

Run only focused test labels/methods within the repository time limits. Full managed browser and evidence suites remain CI-owned. These commands are planned acceptance, not results from proposal creation.
