## MODIFIED Requirements

### Requirement: The effect-resolution registry is open, prefix-keyed, and every handler declares its
mutation surfaces
`world/rules/action.py` SHALL expose `register_effect_handler(prefix, handler, surfaces)` as the only
sanctioned way to add an effect-ID handler, where `surfaces` is the exact set of entity-state surfaces
that handler's staged effects mutate. Step 5 SHALL dispatch purely by looking up an effect ID's prefix
(the substring before its first `:`) in the registry, with no other conditional distinguishing one
effect kind from another. Registration SHALL fail immediately if `surfaces` is not a subset of the
surfaces `_commit()`'s snapshot/restore mechanism covers, and `_commit()` SHALL independently refuse to
run any action whose staged effects declare a surface outside that same set.

#### Scenario: A newly registered handler resolves a previously-unknown prefix

- **WHEN** a test registers a handler for a synthetic prefix not built into this change, declaring
  `surfaces=frozenset({"traits"})`, then resolves a skill whose `effects` list contains an ID with that
  prefix
- **THEN** `resolve()` succeeds and the registered handler's staged effect is committed

#### Scenario: Registering a handler with an unsupported surface fails immediately

- **WHEN** `register_effect_handler()` is called with a `surfaces` value containing a surface outside
  `_commit()`'s snapshot/restore coverage (e.g. `"inventory"`)
- **THEN** it raises `UnsnapshottedSurfaceError` immediately, naming the unsupported surface, before any
  skill can ever reference that prefix

#### Scenario: A handler bypassing registration is still caught at commit time

- **WHEN** a test injects an entry directly into the internal handler-surface mapping (bypassing
  `register_effect_handler()`'s own check) declaring an unsupported surface, then resolves a skill using
  that prefix
- **THEN** `_commit()`'s own independent assertion rejects the action with
  `RejectReason.UNSNAPSHOTTED_EFFECT_SURFACE` before touching any entity, proving the commit-time check
  is not merely decorative alongside the registration-time one

#### Scenario: 統御術's cast-time conferral commits atomically with its own resource cost

- **WHEN** `resolve()` is called for 統御術 (`dominion_art`) targeting a single ally, with an
  `event_context` carrying no conferral keys, by a caster who directly owns conferrable passives
  declared at the node's coefficient
- **THEN** the target's `entity.db.skill_grants` gains one `ConferredSkillGrant` per derived skill at
  the node's declared scale, and the actor's declared `cost` resources are deducted, in the same
  successful `resolve()` call

#### Scenario: A sexual-magic effect ID rejects cleanly before change 7b exists, and self-arms after

- **WHEN** `resolve()` is called for a skill whose `effects` include a `sexual_event:`-prefixed ID,
  while `world.rules.sexual_transitions` is not importable
- **THEN** it returns `ActionResult(outcome="rejected", reason=RejectReason.EFFECT_RESOLUTION_FAILED)`
  with no exception escaping and no state mutated

#### Scenario: A sexual-magic effect ID resolves once change 7b's module exists (self-arming)

- **WHEN** `resolve()` is called for the same skill, guarded by
  `pytest.importorskip("world.rules.sexual_transitions")`, once that module is importable
- **THEN** `resolve()` succeeds and the target's `entity.sexual` reflects `apply_event()`'s effect

### Requirement: Preflight rejects missing handler context before any round cost

`ActionResolver.preflight()` and the combat-session revalidation SHALL verify that every effect handler's declared context keys are present in the submitted `event_context`; a missing key SHALL reject the action before initiative, round count, upkeep, or world time changes.

#### Scenario: Missing disguise context rejects before initiative

- **WHEN** a player submits `status_disguise` in combat without `event_context.disguise`
- **THEN** the action is rejected at preflight, no round is consumed, and the enemy does not act

#### Scenario: Missing dominion context rejects before initiative

- **WHEN** a player submits `dominion_art` in combat while owning no skill that passes the
  conferrability shape validation, with an `event_context` carrying no conferral keys (the scale and
  the conferred set are now derived from the caster's own ownership and the node's policy, so the
  old required-context keys no longer exist)
- **THEN** the action is rejected at preflight with `EFFECT_RESOLUTION_FAILED`, no round is consumed,
  and the enemy does not act

#### Scenario: Out-of-combat casts with supplied context still work

- **WHEN** a player casts `status_disguise` out of combat with the disguise context supplied by the command
- **THEN** the cast resolves normally