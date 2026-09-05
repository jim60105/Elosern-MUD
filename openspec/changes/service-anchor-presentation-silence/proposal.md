# Proposal: service-anchor-presentation-silence

## Why

The anchoring gate answers `off_anchor`, but nothing shows it and nothing keeps a traveling
clerk's authored shift from dragging him back to the storefront mid-adventure. Two consumer
surfaces complete the anchor story: the exploration affordances must render the verdict honestly
(disabled entry beside the traveler, no ghost entry in the darkened anchor room — the latter
already holds because navigation entries emit only for the exact local host), and schedule
settlement must fall silent for off-anchor traveling place-bound companions.
Source design: `docs/superpowers/specs/2026-09-05-service-anchoring-design.md` (§4, §5, D5–D6).

## What Changes

- `exploration-affordances`: a co-located service host whose component is `place`-bound and
  off-anchor SHALL emit its guild/shop navigation entry **disabled** with the gate's fixed
  registry `disabled_reason` message (same `disabled_reason.message` pattern as `target_dead`);
  anchor-room darkness needs no change (absence already yields no entry — pinned by test, not
  code).
- `npc-schedule-runtime`: settlement skips an NPC that is simultaneously (a) a bound party
  companion, (b) carries a `place`-bound service component, and (c) is not in its anchor room —
  one shared silence predicate (`world/rules/service_gate.py` grows
  `schedule_silenced(npc) -> bool`), the same gate slot the possession change extends for
  possessed NPCs. A silenced NPC settles no entries, emits no events, and changes no state;
  every other NPC settles byte-identically.
- Silence is read-only presentation/settlement policy: it never writes binding/anchor data and
  never touches the interaction-gate vocabulary (`interaction_reason` unchanged).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `exploration-affordances`: navigation-entry emission gains the `off_anchor` disabled state.
- `npc-schedule-runtime`: `settle_npc_schedules` gains the traveling-place-bound silence skip.

## Impact

- `web/webclient/presentation/affordances.py` (navigation entry emission consults the resolver),
  `web/webclient/presentation/tests/` affordance cases; `world/rules/service_gate.py`
  (`schedule_silenced`), `world/rules/npc_schedules.py::settle_npc_schedules` (skip call),
  `npc-schedule` settlement tests.
- Depends on: `service-anchoring-gate`. Code conflicts: the affordance module is also touched by
  `companion-possession-webclient` (new action ids) — that change lands later, no file-level
  overlap in tasks. Dependents: possession (reuses `schedule_silenced`'s second trigger).
- No new player commands.
