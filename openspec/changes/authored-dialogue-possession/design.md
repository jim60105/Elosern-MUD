# Design

## Context

Observed talk_open, talk_scripted and dialogue_leave reject is_possessed_actor. Existing party_scope.resolve_commander checks mirrored possession and live owner-account control; is_companion validates both membership directions. Current _trade_member already resolves the commander and uses member inventory. Existing possession-core only forbids addressing the possessed self and silences autonomy; preserve those rules.

## Goals / Non-Goals

**Goals:** Lawful possessed authored conversations with owner-correct relationships. Deliver this runnable slice and its acceptance within one engineer-day.

**Non-Goals:** Unowned runtime/content work, compatibility migrations, new game effects and per-line server stepping.

## Decisions

Extend Shared contract v1 resolver through world.rules.party_scope.resolve_commander(actor), then is_companion(actor, owner), same actual room, account/session puppet and both possession mirrors. Do not use encounter_dispatch.resolve_exploring_owner as an authorization check: observed implementation resolves possessed_by without these complete gates. Reject forged ownership, unrelated NPC actors, remote host, host==actor, unavailable actor, stale phase and schedule-blocked host before effects/delivery.

Remove only authored talk-open/scripted/leave prohibitions and their affordance suppression. Keep freeform possession availability unchanged, including possessed-self rejection. Keep combat/other possession restrictions unchanged. Host-to-owner RelationHandler reads and apply_affinity_change use owner, never actor; variants use actor race/portrait. Guild 回報 listing/explicit claim while possessed uses owner ledger but checks host at actor's actual local room through the existing local-host authority; introduce no commander teleport, duplicate reward service or remote counter bypass. If the guild service requires local owner, retain that service's existing refusal rather than bypass its authority. Shopping is explicitly unchanged: commander purse, selected member bag, existing lawful trading gates. Historical spec prohibition of possessed shopping must not be revived.

Session stays on actor. Starting possession already requires no conflicting dialogue; release/control switch clears possessed actor dialogue through the sole writer and republishes current body mode. Reading is later stored owner-side so no per-body reading copy is needed. Existing owner-only scene replay cannot appear on companion control, or vice versa. Add synthetic owner/actor race differences and a host with owner and companion relationship records; verify only owner record changes. Browser method actually enters lawful possession and selects a race-qualified synthetic variant once conditions land; this slice independently verifies a two-line possessed scene and actor portrait. The physical-condition slice extends that method for race qualification.

## Implementation handoff constraints

This proposed slice is capped at one engineer-day. Each numbered task is intended as a 45-120 minute implementation-and-focused-test unit; tests/docs land with their owning behavior. Use a local untracked `.env.test` containing `MUD_TEST_SETTINGS=1` for the commands below (create that environment file only at apply time). Run focused commands from the repository root; new test labels are explicitly proposed, existing labels are regression targets. Also run `uv run --locked python -m tools.contract_gate` before implementation handoff, with test ownership updates in the same feature commit. No live external model/image requests. Planning created no production code or test results.

Boundary events use the existing world.observability facade with available owner/actor/npc/topic/context identifiers; exceptions rethrow or log once with exc. No new telemetry subsystem. No compatibility shim, legacy aliases, data backfill or migration. No executable dialogue scripts, mid-scene choice tree, per-line server stepping/persistence or new gameplay effects.


## Exact target files

- `world/rules/dialogue_context.py`
- `world/rules/dialogue.py`
- `web/webclient/actions/exploration_actions.py`
- `web/webclient/presentation/affordances.py`
- `web/webclient/presentation/exploration.py`
- `world/rules/possession.py`
- `commands/talk.py`
- `web/webclient/presentation/dialogue.py`

## Risks / Trade-offs

Touches shared backend context/adapters and browser fixture with condition/reading changes; sequence accordingly. No economy.py modification permitted. Keep authored source validation separate from runtime eligibility. A failed post-commit push recovers on the next canonical sync, without reversing a successful owning commit. Read the approved design and dependency artifacts before edits; no interface decision is left open.

## Focused verification at implementation time

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb world.rules.tests.test_authored_dialogue_possession web.webclient.presentation.tests.test_possession_presentation
pnpm exec vitest run web/webclient-app/tests/dialogue_view_model.test.js
uv run --locked python -m tools.contract_gate
```

Run only focused test labels/methods within the repository time limits. Full managed browser and evidence suites remain CI-owned. These commands are planned acceptance, not results from proposal creation.
