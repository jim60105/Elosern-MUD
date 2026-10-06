## MODIFIED Requirements

### Requirement: DEFEAT progress is planned automatically from committed player action events
The quest event-effect planner SHALL inspect `target_defeated` entries produced by an
`ActionResolver` request or by the combat upkeep settlement. It SHALL advance only active DEFEAT
stages owned by the acting entity when that entity is a `PlayerCharacter`, and SHALL additionally
advance the owner's matching stage when the acting entity is a bound companion of the owner (per the
party binding) and is not knocked out; a companion's entries SHALL follow the same aggregation, cap,
and one-transition rules as the owner's own. A
bound-target objective SHALL match `data["target_id"]` against the record's `objective_target_ids`; an
unbound tier objective SHALL match its declared `monster_tier`; a regional species-hunt objective SHALL
match by the species-hunt rules below. Display
keys SHALL NOT be used as entity identity. Counting SHALL key on the defeated individual's persistent
identity, and each record SHALL keep the set of individual identities already counted for its current
objective: a duplicate or redelivered `target_defeated` entry for an identity this record has already
counted SHALL advance nothing. The resulting quest mutation SHALL commit in the same
action or combat-round transaction as the lethal damage. The planner SHALL aggregate every matching
defeat entry in one EventLog per quest, cap progress at the current objective quantity, perform at
most one stage transition, and discard surplus kills rather than applying them to the next stage.
Simulated defeats (guild examinations) and unattributed upkeep ticks SHALL advance no quest and SHALL
not fail a protected entity.

#### Scenario: Player defeat advances a matching tier objective automatically
- **WHEN** a player action lethally damages a monster whose tier matches the player's active DEFEAT stage
- **THEN** `ActionResolver.resolve()` commits the damage and increments quest progress without any caller
  invoking a separate observer

#### Scenario: Bound objective matches exact dbref
- **WHEN** two monsters share a display key but only one dbref is in `objective_target_ids`
- **THEN** defeating the unbound monster does not advance the quest and defeating the bound monster does

#### Scenario: A duplicate defeat event for one individual counts once
- **WHEN** the planner is presented twice with the same defeat entry for one individual against the same active record
- **THEN** the objective's progress advances once across both presentations

#### Scenario: A bound companion's kill advances the owner's objective
- **WHEN** a bound, non-knocked-out companion defeats a monster matching the owner's active DEFEAT stage
- **THEN** the owner's quest progress advances in the same action transaction with the same cap and
  one-transition rules

#### Scenario: A knocked-out companion's kill grants no credit
- **WHEN** a knocked-out companion defeats a matching-tier monster
- **THEN** the owner's quest progress is unchanged

#### Scenario: Another character's action grants no ordinary kill credit
- **WHEN** an NPC that is not a bound companion, a different `PlayerCharacter`, or a monster defeats a matching-tier monster
- **THEN** the quest owner's ordinary DEFEAT progress is unchanged

#### Scenario: Quest planner failure rejects the complete action
- **WHEN** the quest planner cannot stage a valid transition because the actor's active record is
  malformed
- **THEN** the action rejects before commit and target HP, resources, progression, quest log, and pins
  all remain unchanged

#### Scenario: AREA defeat entries aggregate without skipping stages
- **WHEN** one AREA action defeats three matching targets while the current objective needs two
- **THEN** progress reaches two, the current stage transitions exactly once, and the surplus kill is not
  applied to the next stage

#### Scenario: An attributed upkeep kill advances the matching objective
- **WHEN** the player's damaging rate tick causes the lethal HP crossing of a monster matching the player's active DEFEAT stage
- **THEN** the quest log advances in the same combat-round transaction with the same cap and one-transition rules

#### Scenario: A simulated or unattributed upkeep kill grants no quest progress
- **WHEN** a lethal rate tick fires inside a guild examination, or an upkeep tick has no resolvable source
- **THEN** no quest DEFEAT stage advances and no protected-entity failure occurs

## ADDED Requirements

### Requirement: Species-hunt objectives match by variant membership, region, and persistent identity
The quest planner SHALL evaluate a regional species-hunt DEFEAT objective against the `target_defeated`
entry's species/variant identity fields: an entry counts only when its species key equals the
objective's species key, its variant key is one of the objective's countable variant keys, and the
defeated individual's location resolved inside the objective's declared region at defeat time. Each
distinct persistent individual identity counts at most once per record (composing with the
already-counted-identity dedupe), including stronger same-species variants in a general hunt — one
stronger individual never counts twice and is never required when ordinary-eligible targets suffice. An
entry with no species identity (tier-only individual) SHALL never satisfy a species hunt, and a hunt
whose countable variants name specific variants SHALL count only those. Matching SHALL NOT consult
display names, guild rank, or a single stat.

#### Scenario: A countable stronger variant counts once
- **WHEN** a general hunt counts eligible variants and a stronger same-species individual inside the region is defeated
- **THEN** progress advances by one for that identity, and a duplicate event for it advances nothing

#### Scenario: An unlisted variant does not count
- **WHEN** a defeated individual's variant is a registered variant of the species but not among the objective's countable variants
- **THEN** progress does not advance

#### Scenario: Outside the region does not count
- **WHEN** an individual of the right species and a countable variant is defeated outside the declared region
- **THEN** progress does not advance

#### Scenario: Ordinary targets alone always suffice
- **WHEN** a hunt's ordinary-eligible targets were guaranteed at acceptance and all counted defeats are ordinary variants
- **THEN** the objective completes without requiring any stronger variant

#### Scenario: Tier-only kills never satisfy a species hunt
- **WHEN** a tier-only monster without species identity is defeated inside the region
- **THEN** the species-hunt objective's progress is unchanged
