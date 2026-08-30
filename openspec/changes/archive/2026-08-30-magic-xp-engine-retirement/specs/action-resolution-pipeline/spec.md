## MODIFIED Requirements

### Requirement: ActionResolver exposes shared side-effect-free action preview
The deterministic rules layer SHALL expose a frozen preview query factored from the same pure checks used by `ActionResolver.preflight()`. Given an actor, skill, context, and optional candidate, it SHALL report enabled state, the exact stable rejection reason and resource detail when disabled, and valid targets or applicable AREA shorthands. It SHALL cover ownership and active kind, current resources, exact target shape, presence, alive state, range, faction, action-blocking buffs, `actions_per_turn == 0`, registered effect prefixes, and time metadata. The same checks SHALL apply to the combat-session submission revalidation path, so a rejected submission stops before initiative. Modifier evaluation SHALL read a no-create context from existing stored buff and sexual-state data and SHALL NOT materialize a lazy handler or default. Preview SHALL NOT roll randomness, stage or apply effects, construct EventLogs, invoke event-effect planners, mutate any persistent or nonpersistent game state, or advance world time. `preflight()` and final `resolve()` SHALL remain authoritative and SHALL rerun their required checks.

#### Scenario: Preview has no side effects
- **WHEN** previews are built for every owned active skill and every current combat participant
- **THEN** traits, resources, buffs, sexual state, battlefield state, session record, quest state, random source, EventLogs, and world clock are unchanged

#### Scenario: Preview reuses a named resolver rejection
- **WHEN** an active skill costs more MP than the actor currently has
- **THEN** preview reports disabled with `RejectReason.INSUFFICIENT_RESOURCE` and MP detail, matching preflight without executing an effect

#### Scenario: Zero-action state is authoritative before initiative
- **WHEN** deterministic combat modifiers set the player actor's `actions_per_turn` to zero
- **THEN** preview and player-session submission report `RejectReason.ACTION_FORBIDDEN` before initiative while `run_round()` retains its existing skip behavior for an NPC or a post-preflight state change

#### Scenario: Preview does not materialize sexual state
- **WHEN** an actor has a stored sexual baseline but no materialized sexual trait handler and combat preview is built
- **THEN** modifier matching is interpreted in memory and no sexual trait Attribute or default handler state is created

#### Scenario: Target previews use ordinary ordered validation
- **WHEN** candidate previews are requested for a SINGLE or AREA skill
- **THEN** candidate acceptance and rejection use the same presence, alive, range, and faction functions and ordering as final target resolution

#### Scenario: The shared combat view marks an unaffordable spell disabled
- **WHEN** the combat view (`build_combat_view`) is built for an actor who owns a spell whose MP cost exceeds their current MP
- **THEN** the spell's descriptor carries `enabled == False` and the MP resource reason code, so both the Telnet `combat actions` command and the WebClient combat panel render it unavailable

### Requirement: Neither ActionResolver nor targeting branches on combat state
`world/rules/action.py` and `world/rules/targeting.py` SHALL contain no conditional that distinguishes
combat from non-combat behavior other than the single, explicitly marked `usable_out_of_combat` gate. All other
combat-vs-non-combat behavior SHALL be expressed entirely through which concrete `ActionContext`
implementation the caller supplies.

#### Scenario: A source scan finds no undeclared combat-state branch
- **WHEN** `world/rules/action.py`, `world/rules/targeting.py`, and `world/rules/event_log.py` are
  scanned for the literal tokens `in_combat`, `is_combat`, `combat_state`, and
  `isinstance(context, Battlefield`
- **THEN** none of the tokens appear anywhere in these three files

#### Scenario: A battlefield defeat stages events and planners only
- **WHEN** a battlefield-backed action reduces a resolved `Monster` with a known `threat_tier` from
  positive HP to zero
- **THEN** the action stages the defeat EventLog entry (carrying `monster_tier`) and the
  event-effect planners derived from it, and no progression effect of any kind

#### Scenario: No public callable takes a combat-shaped parameter
- **WHEN** every public callable in `action.py`, `targeting.py`, and `event_log.py` has its signature
  inspected
- **THEN** no parameter is named `in_combat`, `combat_state`, `turn`, or `is_combat`

#### Scenario: Identical code, different ActionContext, different faction outcome
- **WHEN** `ActionResolver.resolve()` is called twice with byte-identical `ActionRequest`s (same actor,
  same `skill_key` whose `SkillDef.faction_constraint` is `FactionConstraint.SELF_ONLY`) differing only in
  which `ActionContext` is supplied — once with `RoomActionContext`, once with a test double whose
  `relation_to()` reports `Relation.SELF` for the same target
- **THEN** the `RoomActionContext` call rejects with `RejectReason.TARGET_FACTION_FORBIDDEN` and the
  test-double call succeeds, with no difference in `action.py`'s or `targeting.py`'s executed source
  between the two calls

### Requirement: Nonlethal policy transforms lethal projection before EventLog planners
A validated BattlefieldActionContext MAY carry a deterministic `nonlethal` policy as a
session-wide flag and/or per-entity `nonlethal_keys` (entity keys protected by the policy; in a
hostile session these are the allied companions). During damage
projection, a positive-to-non-positive crossing under the policy SHALL stage HP at 1 and mark the exact
target knocked out; the per-entity key set SHALL apply to the damaged target's key and the
session-wide flag SHALL apply to every target, with the flag unchanged in its existing exam
semantics. Step 7 SHALL emit `target_knocked_out` and SHALL NOT emit `target_defeated`. This
transformation SHALL occur before event-effect planners, so DEFEAT progress,
protected-entity failure, and loot consumers receive no defeat entry. Contexts without the policy SHALL
retain existing lethal behavior.

#### Scenario: Nonlethal projection emits knockout only
- **WHEN** exam damage would cross a target from positive HP to zero or lower
- **THEN** projected and committed HP is 1, knockout identity is staged, `target_knocked_out` is emitted,
  and no `target_defeated` entry exists

#### Scenario: A companion key under the per-entity policy is knocked out
- **WHEN** hostile-session damage would cross a companion from positive HP to zero or lower
- **THEN** the companion's projected and committed HP is 1, `target_knocked_out` is emitted, and no
  `target_defeated` entry exists for the companion

#### Scenario: Hostile targets outside the key set stay lethal
- **WHEN** identical damage in the same hostile session would cross a monster from positive HP to
  zero or lower
- **THEN** the ordinary lethal crossing and `target_defeated` behavior apply to the monster

#### Scenario: Quest and XP planners cannot observe exam defeat
- **WHEN** event-effect planners inspect the completed nonlethal EventLog
- **THEN** none can match ordinary defeat because the log contains only knockout identity

#### Scenario: Ordinary hostile damage is unchanged
- **WHEN** identical damage resolves without a nonlethal policy
- **THEN** the existing lethal HP crossing and target-defeated planner behavior apply

## REMOVED Requirements

### Requirement: Casting an elemental spell above the caster's tier without mastery is rejected
**Reason**: the elemental tier gate is a construct of the deleted magic-XP ladder (design D3/D5).
**Migration**: interim preflight/resolve reject casts the actor does not own or cannot afford (existing ownership and MP checks); `use-driven-skill-lineage` restores an authoritative lineage-based gate through `can_use_skill`.
