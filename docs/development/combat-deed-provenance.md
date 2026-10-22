# Combat Deed Provenance and the Encounter Join Contract

Committed combat actions, upkeep milestones and terminal encounter outcomes are
durable narrative evidence. This document states the one identity each of them
carries and the one key consumers join on.

## Provenance value

`world.rules.combat.decision_scope.CombatProvenance` is a frozen value:

| Field | Meaning |
| --- | --- |
| `engagement_id` | The encounter's authoritative occurrence identity. Allocated once per engagement by the combat owner. |
| `round_ordinal` | The engagement's real round number this occurrence was resolved in. |
| `slot_ordinal` | The acting combatant's action-slot ordinal; `None` for a round-owned boundary such as end-of-round upkeep. |
| `session_id` | The reusable transport token. Diagnostic metadata only. |

The combat owner constructs it. `ExecutionScopeBase` carries `engagement_id`,
`round_index` and `session_id`; `world.rules.combat.rounds._resolve_round`
installs `combat_provenance(...)` for the round and narrows it with
`at_slot(slot_index)` around each action slot, so both the source identity and
the post-commit evidence inherit the occurrence actually being resolved.

Composition points:

- Interactive sessions: `world.rules.combat_session.battlefield.execution_scope_base(record)`
  reads the durable `CombatSessionRecord`. Ordinary, opening and failed-retreat
  rounds all use it. A durable record without an engagement identity is
  malformed and fails closed before anything is provisioned.
- Compressed (overwhelm) execution reuses the same base and re-specifies only
  the round ordinal, so every internal round keeps the encounter's identity.
- Guild examinations allocate their engagement identity from the same
  `combat_encounter_seq` counter as hostile engagements, so an examination and
  a hostile engagement at the same tick with the same participants keep
  distinct identities.
- A bounded `run_battle(...)` encounter declares its own identity through
  `engagement_id=`; it is not a durable session and never inherits one.

## Source identities

Committed combat action:

```text
action:combat:<engagement_id>:r<round_ordinal>:s<slot_ordinal>:<actor_pk>:<skill_key>
```

End-of-round upkeep milestone (the recorder appends
`:milestone:<entity_pk>:<milestone_kind>:<identifier>`):

```text
combat:<engagement_id>:round:<round_ordinal>:upkeep:<entity_pk>
```

Terminal encounter:

```text
encounter:<engagement_id>:terminal:1
```

No world tick, display string, narration scope or transport session token takes
part in any of them. Consequently:

- the same skill in distinct slots or rounds of one engagement produces
  distinct sources even when world time did not advance and both occurrences
  render identical prose;
- repeated upkeeps in one round produce distinct sources per transition, and
  distinct rounds never share one;
- two actual engagements that reuse one session token and one world tick keep
  distinct action, milestone and terminal sources.

## Evidence payloads

`skill_use` and `adult_action` content carries `encounter_context`:

```json
{
  "encounter_id": "<engagement_id>",
  "session_id": "<transport token, diagnostics only>",
  "round_number": 3,
  "slot_ordinal": 1
}
```

`adult_milestone` content carries the same `encounter_context` when the
milestone was committed under a combat occurrence (upkeep boundaries included).

`combat_encounter` (terminal) content carries `encounter_id` plus the transport
`session_id` as diagnostic metadata.

Every supported deed payload also carries the settlement-time location
reference `"location": {"id": <durable room identity>, "label": <readable room
label>}`. Combat evidence snapshots the durable session room and its label;
both fields are empty when the settlement held no authoritative location.
`world.narrative.recent_deeds` reads only this snapshot (never a live room),
renders each fact's own `tick` and `location`, and keeps one source-linked
`occurrences` reference per occurrence when consecutive actions compress.

## Selection join

`world.narrative.recent_deeds` joins only on `encounter_id`:

- the terminal index is keyed by `combat_encounter.encounter_id`;
- action runs compress and associate by `encounter_context.encounter_id`;
- an upkeep milestone that names no admitted action still joins its own
  encounter through `encounter_context.encounter_id` and contributes its own
  source and facts to that group;
- `session_id` is projected as diagnostic data and never keys a dictionary,
  never merges two encounters and never groups two action runs together.

Rolling-window filtering happens in the durable query, before any of this
grouping: an occurrence outside the window contributes no fact, no source
reference and no repetition count.

## Fail-closed rules

Each of these is malformed required evidence and raises instead of inventing an
identity:

- a combat action context with no installed combat provenance
  (`build_action_source_id`), which is never relabeled as an out-of-combat
  `action:cast:...` occurrence;
- an explicit `source_id` on a request that disagrees with the provenance being
  resolved;
- a combat provenance with an empty `engagement_id`, or an action occurrence
  with no slot ordinal;
- an upkeep milestone with no combat provenance;
- a durable session (or its terminal settlement) without an engagement
  identity;
- a `combat_encounter` record without `encounter_id` in selection.

Out-of-combat casts keep their existing accepted identity,
`action:cast:<actor_pk>:<skill_key>:<tick>`, owned by
`world.rules.cast_settlement.settle_out_of_combat_cast`.
