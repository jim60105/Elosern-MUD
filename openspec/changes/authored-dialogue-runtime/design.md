# Design

## Context

Observed run_scripted_talk grants +1 talk affinity inside an atomic with relations snapshots, except guild 回報 and declared generated story effects. Current session stores one npc_id/line/tick. Presenter and UMD accept exact version 2 and first four choices. Generated quest dialogue lives in world/quests/story_dialogue.py; preserve it.

## Goals / Non-Goals

**Goals:** Cut over all authored backend/text delivery and version-3 protocol. Deliver this runnable slice and its acceptance within one engineer-day.

**Non-Goals:** Unowned runtime/content work, compatibility migrations, new game effects and per-line server stepping.

## Decisions

Implement Shared contract v2 from ../authored-dialogue-contracts/design.md. Own source-neutral selection/provider dispatch, native freeform/opening/service versus scene session forms and all protocol mirrors. Static provider reads the loader snapshot; generated-packages later replaces its package provider. Common features never require static-registry membership. Until the scene player lands, MessageWindow receives complete attributed scenes as ordinary text, usable on both transports.

Migrate all 25 Python tables directly to `world/lore/dialogue/content/<NpcProfile.key>.yaml`, preserving existing dialogue-key topic_01..topic_04 IDs and localized aliases. Derive lookup from canonical profile/service bindings, including guild_staff -> altoria_guild_master, never file registration/dbids/display names. No duplicate owner field. Temporary explicit actor-question/old-host-response scenes are replaced by content slices; runtime never synthesizes actor prose. Delete obsolete guild/altoria_lower/altoria_middle/altoria_upper/ciaran Python dialogue modules, old class re-exports and all importers after migration. Generated-packages removes PhaseTopic.response and supplies common actor-first scenes; generated content has no permanent one-host-line exemption.

Keep greeting override precedence/escaping and componentless/unknown fallbacks. Guild 回報 remains read-only listing/explicit quest-id settlement as native service delivery, without invented rewards or affinity. Move static callers to select_authored_topic and expose ResolvedDialogueSource for generated-packages, which later removes every old generated run_scripted_talk branch/caller. Preserve freeform observers and phase invalidation through the sole session writer. Text emits all attributed lines; reading-server wires successful-emission completion. Never label unsaved completion as saved.

Use existing request-envelope generation/epoch/revision rejection before selection. Persist bounded per-topic last selection receipt plus current delivery in the context. A transport duplicate of current request returns committed delivery; an older envelope is rejected before a fresh selection even if its request receipt was replaced. Text invocations allocate a fresh selection identity; replay directly reads delivery and never calls selection. Tests must cover duplicate request after an intervening different topic and prove rejection/no second affinity. Transaction covers effect and session writes; injected session failure restores relations and session cache snapshots. No content is returned before success.

Panel v3 replaces the whole panel requirement, preserving portrait/privacy/unavailable invariants and unrelated scenarios. All <=16 static/generated topics remain reachable; command aliases stay vocabulary, with generated keyword action payload removed at generated cutover. Python action/panel/session validators, UMD misc.js/constants.js/core.js/store.js, Vue view admission and completion validators accept static <=96 or canonical generated <=2048 topic/scene IDs in all predecessor/completed/receipt fields. Scope exceptions to these fields; preserve aggregate UTF-8 budgets. Test worst valid Unicode binding IDs across selection/completion/replay/reconnect. Oversized actual payload rejects before effects without truncation. Empty definition stays empty.

`SceneDelivery` keeps its Shared contract v2 fields and adds one defaulted,
server-only flag, `affinity_budget_capped`. A talk-affinity gain blocked by the
daily interaction budget is the only writer; `delivery_to_wire` omits it, so the
panel, stored session and client never carry it, and a replay reconstructs the
delivery without the flag and re-sends no hint. It exists because the text
surface must keep presenting the fixed non-numeric capped-relationship hint that
the previous native talk writer reported.

## Implementation handoff constraints

This proposed slice is capped at one engineer-day. Each numbered task is intended as a 45-120 minute implementation-and-focused-test unit; tests/docs land with their owning behavior. Use a local untracked `.env.test` containing `MUD_TEST_SETTINGS=1` for the commands below (create that environment file only at apply time). Run focused commands from the repository root; new test labels are explicitly proposed, existing labels are regression targets. Also run `uv run --locked python -m tools.contract_gate` before implementation handoff, with test ownership updates in the same feature commit. No live external model/image requests. Planning created no production code or test results.

Boundary events use the existing world.observability facade with available owner/actor/npc/topic/context identifiers; exceptions rethrow or log once with exc. No new telemetry subsystem. No compatibility shim, legacy aliases, data backfill or migration. No executable dialogue scripts, mid-scene choice tree, per-line server stepping/persistence or new gameplay effects.


## Exact target files

- `world/rules/dialogue.py`
- `world/rules/dialogue_context.py (new)`
- `commands/talk.py`
- `world/lore/dialogue/__init__.py`
- `world/lore/dialogue/{guild,altoria_lower,altoria_middle,altoria_upper,ciaran}.py (delete after cutover)`
- `world/lore/dialogue/content/<existing NpcProfile.key>.yaml (25 migrated files)`
- `world/rules/dialogue_sources.py (new)`
- `web/webclient/actions/exploration_actions.py`
- `web/webclient/presentation/dialogue.py`
- `web/webclient/presentation/affordances.py::_scripted_keyword_descriptors (composed talk_scripted params producer)`
- `web/static/webclient/js/elosern/protocol/panels/skill_descriptor.js (client exact-field mirror of the composed params)`
- `web/static/webclient/js/elosern/protocol/panels/misc.js::validateDialoguePanel`
- `web/static/webclient/js/elosern/protocol/constants.js`
- `web/static/webclient/js/elosern/protocol/core.js`
- `web/static/webclient/js/elosern/protocol/store.js`
- `web/webclient/presentation/protocol.py`
- `web/webclient/presentation/coordinator.py`
- `web/webclient/actions/dispatcher.py::handle_ui_action`
- `web/webclient-app/stores/elosern/transport.js::dispatchAction`
- `web/webclient-app/stores/dialogue-view.js`

## Risks / Trade-offs

The complete review-resolved schemas and UTF-8 publication budgets in the shared contract are mandatory in this slice. The production client validator is misc.js, not exotic.js or dialogue-view.js. Protocol adoption tests belong to web/static/webclient/js/tests/protocol_dialogue.test.js and the production protocol-store tests, plus Python protocol/coordinator tests. Request identity injection occurs in handle_ui_action before full action payload validation, after duplicate/stale admission. Projection validates only the identity-free descriptor. Test two deliberate picks versus a retry, null-context direct entry and opening reconnect. No presenter creates context or receipt IDs.

The `explore.talk_scripted` composed payload is exactly `{npc_id,topic_id,context_id}` with `context_id` null only for a no-live-context direct entry; `selection_id` is injected by `handle_ui_action`, never projected. The producer (`presentation/affordances.py`), the exact-field validator (`actions/exploration_actions.py::validate_talk_scripted_payload`), the registered `ActionSpec`, the `presentation/options.py::_ACTION_PAYLOAD_VALIDATORS` entry that keeps projections byte-identical to dispatch, and the UMD `skill_descriptor.js` mirror change in this one slice; the existing lockstep validator test (`web.webclient.presentation.tests.test_combat_panel.test_options_and_validators`) must stay green, and `constants.js` bounds for the new topic/context params stay within the existing per-param and param-count limits.

Highest backend blast radius. Conflicts with possession, availability, reading in dialogue.py, exploration_actions.py, protocol and presenter; dependent order is mandatory. Registry mechanical conversion precedes every prose slice. Keep authored source validation separate from runtime eligibility. A failed post-commit push recovers on the next canonical sync, without reversing a successful owning commit. Read the approved design and dependency artifacts before edits; no interface decision is left open.

## Focused verification at implementation time

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb world.rules.tests.test_authored_dialogue_runtime world.rules.tests.test_dialogue_session commands.tests.test_talk_turnin_commands
node --test web/static/webclient/js/tests/protocol_dialogue.test.js
uv run --locked python -m tools.contract_gate
```

Run only focused test labels/methods within the repository time limits. Full managed browser and evidence suites remain CI-owned. These commands are planned acceptance, not results from proposal creation.
