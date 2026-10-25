# Design

## Context

Observed run_scripted_talk grants +1 talk affinity inside an atomic with relations snapshots, except guild 回報 and declared generated story effects. Current session stores one npc_id/line/tick. Presenter and UMD accept exact version 2 and first four choices. Generated quest dialogue lives in world/quests/story_dialogue.py; preserve it.

## Goals / Non-Goals

**Goals:** Cut over all authored backend/text delivery and version-3 protocol. Deliver this runnable slice and its acceptance within one engineer-day.

**Non-Goals:** Unowned runtime/content work, compatibility migrations, new game effects and per-line server stepping.

## Decisions

Implement Shared contract v1 from ../authored-dialogue-contracts/design.md. This slice owns backend selection, native line versus scene session forms, server protocol and both client schema mirrors. Until the dedicated scene player lands, the current MessageWindow receives the complete attributed scene as ordinary message text, so a real multi-line authored fixture is usable on both transports; do not add a stub player, duplicated per-line effects or version-2 protocol shim.

Mechanically convert all 25 registry tables to the new declarations with stable ASCII suffixes derived once from the existing ordered topics (`topic_01`..`topic_04`), preserving localized keyword lookup. Each temporary formal scene is [actor Speech containing the topic question, host Speech containing old response]; this explicit dependency-stage representation is removed by every content slice. Topic IDs stay fixed across rewrite. Do not synthesize permanent actor text from menu labels in runtime. Remove KeywordResponse/DialogueDefinition and their rules re-exports once all imports/tests/generated resolver consumers are moved to their own native data shape. Generated phase declarations keep their existing package schema and authority; a presentation conversion emits a single host speech without claiming authored actor-first validation applies.

Keep greeting override precedence, literal escaping and componentless/unknown fallbacks. Guild 回報 dispatches the existing read-only listing and explicit quest-id settlement as native service delivery; no invented reward effect or affinity. Existing `run_scripted_talk` becomes the generated/native service dispatch function, with every authored caller moved to select_authored_topic. Preserve freeform observer session calls and generated refresh/phase invalidation through open_or_refresh_dialogue. Text emits all attributed lines once; this slice has no reading persistence yet (reading owner later wires the successful-emission callback). Never label unsaved completion as saved.

Use existing request-envelope generation/epoch/revision rejection before selection. Persist bounded per-topic last selection receipt plus current delivery in the context. A transport duplicate of current request returns committed delivery; an older envelope is rejected before a fresh selection even if its request receipt was replaced. Text invocations allocate a fresh selection identity; replay directly reads delivery and never calls selection. Tests must cover duplicate request after an intervening different topic and prove rejection/no second affinity. Transaction covers effect and session writes; injected session failure restores relations and session cache snapshots. No content is returned before success.

Panel v3 removes version-2 exact-field/four-choice rules in webclient-dialogue-session, replacing its WHOLE panel requirement while retaining every portrait/privacy/unavailable/validation invariant. Modify its session requirement in full to cover both native lines and scene snapshots. Modify scripted-dialogue's complete table requirement to immutable stable topics and generated native definitions; keep all old greeting, fallback, guild and schedule scenarios, adjusting only single-response claims. All <=16 authored topics must remain reachable on scroll; preserve existing generated keyword vocabulary. Empty definition remains empty, no action-options replacement.

## Implementation handoff constraints

This proposed slice is capped at one engineer-day. Each numbered task is intended as a 45-120 minute implementation-and-focused-test unit; tests/docs land with their owning behavior. Use a local untracked `.env.test` containing `MUD_TEST_SETTINGS=1` for the commands below (create that environment file only at apply time). Run focused commands from the repository root; new test labels are explicitly proposed, existing labels are regression targets. Also run `uv run --locked python -m tools.contract_gate` before implementation handoff, with test ownership updates in the same feature commit. No live external model/image requests. Planning created no production code or test results.

Boundary events use the existing world.observability facade with available owner/actor/npc/topic/context identifiers; exceptions rethrow or log once with exc. No new telemetry subsystem. No compatibility shim, legacy aliases, data backfill or migration. No executable dialogue scripts, mid-scene choice tree, per-line server stepping/persistence or new gameplay effects.


## Exact target files

- `world/rules/dialogue.py`
- `world/rules/dialogue_context.py (new)`
- `commands/talk.py`
- `world/lore/dialogue/{__init__,guild,altoria_lower,altoria_middle,altoria_upper,ciaran}.py`
- `web/webclient/actions/exploration_actions.py`
- `web/webclient/presentation/dialogue.py`
- `web/static/webclient/js/elosern/protocol/panels/exotic.js`
- `web/webclient-app/stores/dialogue-view.js`

## Risks / Trade-offs

Highest backend blast radius. Conflicts with possession, availability, reading in dialogue.py, exploration_actions.py, protocol and presenter; dependent order is mandatory. Registry mechanical conversion precedes every prose slice. Keep authored source validation separate from runtime eligibility. A failed post-commit push recovers on the next canonical sync, without reversing a successful owning commit. Read the approved design and dependency artifacts before edits; no interface decision is left open.

## Focused verification at implementation time

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb world.rules.tests.test_authored_dialogue_runtime world.rules.tests.test_dialogue_session commands.tests.test_talk_turnin_commands
node --test web/static/webclient/js/tests/protocol_dialogue.test.js
uv run --locked python -m tools.contract_gate
```

Run only focused test labels/methods within the repository time limits. Full managed browser and evidence suites remain CI-owned. These commands are planned acceptance, not results from proposal creation.
