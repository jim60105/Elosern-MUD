# Design

## Context

Observed dialogue choices, exploration keyword affordances and adapters have separate projections over the shared definition; all must consume one qualified view. Existing pusher rerenders CURRENT state with epoch guards and does not persist. Phase/movement/combat/NPC cleanup already owns invalidation.

## Goals / Non-Goals

**Goals:** Server-qualified topic disclosure and committed-state refresh. Deliver this runnable slice and its acceptance within one engineer-day.

**Non-Goals:** Unowned runtime/content work, compatibility migrations, new game effects and per-line server stepping.

## Decisions

Shared contract v2 makes trusted source resolution the sole common projection input. Static YAML/generated DB phases share requires/predecessors, hidden/locked/open, hints, refusal and variants. No static membership feature predicate. Resolve published noncancelled package, role binding and permitted selected phase first; private package/other-phase bodies never enter panels, affordances, hints, chain bundles or freeform context. Effect topics require common qualification plus existing domain authority before formal success delivery.

Implement project_topics(context) as the sole pure availability/disclosure projection and use it from panel, exploration targets, action validator and text topic listing. None of these presenters writes reading or session state. For each qualified topic, requires and saved formal predecessors must pass; false gives hidden or locked according to unavailable. Locked rows contain only ID/label/lock/hint/action descriptor; selection delivers the permitted refusal, never fallback/variant formal body. Open qualified rows expose descriptors only; protected body appears only after server selection recheck. Remove every convenience field or exploration option that copies a full formal response. Never use a client-supplied availability flag.

Before reading persistence lands, qualified predecessors cannot be satisfied and therefore fail closed; this does not pretend a runtime reading implementation exists. Pure-chain definitions remain complete public data, but actual delivery/reveal/receipt synchronization belongs to reading-server. An unmet pure-chain predecessor never becomes a quest/reward authorization primitive. Keep locked refusal effects zero and fixed variant during live playback. Text selecting a locked localized keyword plays the same refusal; hidden/unrecognized behaves as unknown without leaking identity or hint.

Implement `refresh_dialogue_availability(owner, *, cause)` as a complete deterministic API that re-resolves current owner/actor context and invokes current-state fan-out after commit; test it explicitly through this callable. Do not install generic command-observer hooks or claim they cover Telnet/no-session writes. Exact production mutation hooks and owner-discovery behavior are owned by authored-dialogue-refresh-physical and authored-dialogue-refresh-lifecycle, with source-family matrices in those designs. This split preserves one-day scope. Snapshot/selection always recheck canonical readers. Ordinary eligibility refresh preserves the delivered variant; phase invalidation retires obsolete delivery. No presenter writes sessions or reading state.

Use the whole modified webclient-dialogue-session panel requirement from runtime as baseline if additional fields change. This slice changes projection behavior, not v3 field vocabulary. Focused synthetic fixtures establish private body absence recursively across panel/action/affordance payloads and verify forged/stale selection after a committed equipment change. Existing logging facade emits dialogue_selection_rejected/dialogue_availability_refreshed with char/actor/npc/context/cause, no private prose or affinity values.

## Implementation handoff constraints

This proposed slice is capped at one engineer-day. Each numbered task is intended as a 45-120 minute implementation-and-focused-test unit; tests/docs land with their owning behavior. Use a local untracked `.env.test` containing `MUD_TEST_SETTINGS=1` for the commands below (create that environment file only at apply time). Run focused commands from the repository root; new test labels are explicitly proposed, existing labels are regression targets. Also run `uv run --locked python -m tools.contract_gate` before implementation handoff, with test ownership updates in the same feature commit. No live external model/image requests. Planning created no production code or test results.

Boundary events use the existing world.observability facade with available owner/actor/npc/topic/context identifiers; exceptions rethrow or log once with exc. No new telemetry subsystem. No compatibility shim, legacy aliases, data backfill or migration. No executable dialogue scripts, mid-scene choice tree, per-line server stepping/persistence or new gameplay effects.


## Exact target files

- `world/rules/dialogue_availability.py (new)`
- `world/rules/dialogue.py`
- `web/webclient/presentation/dialogue.py`
- `web/webclient/presentation/affordances.py`
- `web/webclient/actions/exploration_actions.py`
- `web/webclient/presentation/dialogue_push.py`
- `world/rules/dialogue_availability.py::refresh_dialogue_availability`

Every successful open or selection re-projects and calls `refresh_dialogue_availability(owner, cause="open")`; the first call for a host carries `initial=True` into `observe_availability`, so a host's first-ever visit initializes every declared topic ID and later unlock batches are classified correctly. This is the only non-mutation refresh cause this slice adds, and it is distinct from the committed-state causes owned by the two refresh slices.

## Risks / Trade-offs

Shared backend projection, action/command ingress and pusher conflict with reading/notification hooks. Reading server follows this; UI availability can run independently once server projection and playback exist. Keep authored source validation separate from runtime eligibility. A failed post-commit push recovers on the next canonical sync, without reversing a successful owning commit. Read the approved design and dependency artifacts before edits; no interface decision is left open.

## Focused verification at implementation time

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb world.rules.tests.test_dialogue_availability web.webclient.presentation.tests.test_dialogue_panel
uv run --locked python -m tools.contract_gate
```

Run only focused test labels/methods within the repository time limits. Full managed browser and evidence suites remain CI-owned. These commands are planned acceptance, not results from proposal creation.
