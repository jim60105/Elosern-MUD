## ADDED Requirements

### Requirement: A positional-marker buff row makes holding it the canonical out-of-position fact
A buff definition MAY declare the closed-vocabulary `marker: positional` clause at definition load — the second value of the shipped closed marker vocabulary beside `ground`. A row that declares it SHALL be a positional marker whose canonical「失去位置／被擊退出位」fact is exactly the holder carrying a live (unexpired, non-paused) instance of that definition — there is no separate position, tile, or room state, and no generic code SHALL read an element, skill or definition-key identity to honor the clause. Positional rows compose with the shipped definition vocabulary without restriction (a positional row may additionally carry `rate`, `bounds` or an empty `modifiers` mapping); a row without the clause SHALL load, apply, tick and expire bit-identically to its pre-clause behavior. The clause value SHALL stay validated fail-closed at load — a value outside the two-member closed vocabulary, a non-string, or a boolean SHALL name the offending definition key and fail the load.

#### Scenario: A synthetic positional row loads, applies, refreshes and expires on the ordinary clock
- **WHEN** a synthetic `marker: positional` row with an authored world-second duration is applied by a living caster, reapplied before expiry, and then the clock advances past expiry
- **THEN** the out-of-position fact is true from application through the refreshed duration and false after expiry, refresh replaces rather than stacks the instance, and no other entity changes

#### Scenario: Every malformed marker value still fails the load closed
- **WHEN** a synthetic buffs table declares `marker: positional`, and separately `marker: ground`, `marker: knockback`, `marker: true`, or `marker: 3`
- **THEN** the two closed vocabulary values load carrying the validated clause and each malformed value raises at load time naming the offending definition key, with no partially-loaded definition set observable

### Requirement: A displaced holder is unreachable to single-target physical strikes in both directions
While an entity holds a live positional-marker instance, the single-target physical-strike pairing between that holder and other entities SHALL be unreachable in both directions: the holder SHALL be rejected as the target of another entity's single-target physical strike, and the holder SHALL be rejected when selecting another entity as the target of its own single-target physical strike. The gate SHALL classify strike-class actions over shipped vocabulary only — `TargetSpec.SINGLE` with at least one physical-school `damage:` effect and no magic-school damage effect — consulted at the existing post-targeting condition stage of action resolution, rejecting with the existing condition-unmet reason. Area-targeted actions, magic-school single-target actions, self/none actions, item use, movement, and every capability and turn mechanic SHALL be untouched: the holder keeps full agency over everything that is not a melee-reach strike (the marker is neither the stillness ladder nor turn denial). One ratified exception exists: the holder's OWN single-target physical strike action is the self-return act (see the self-return requirement) — every other path stays gated while the instance is live.

#### Scenario: A displaced target cannot be selected for a melee strike but can be blasted
- **WHEN** an attacker selects a displaced holder for a registered single-target physical strike, and separately casts a magic-school single-target spell and an area spell at the same holder
- **THEN** the strike rejects with the condition-unmet reason naming the target before any effect stages, no resource is spent, and both magic paths resolve normally dealing their authored effects

#### Scenario: A displaced holder cannot reach out — and its agency otherwise survives intact
- **WHEN** a displaced holder selects another entity for a single-target physical strike, and separately casts a magic spell, casts an area spell, uses an item, and resolves its turn with the marker live
- **THEN** the strike is the one gated path (subject to the self-return exception), while the magic/area/item/turn paths resolve exactly as an undisplaced entity's, and no action-per-turn, action-blocking, or turn-skipping mechanic ever reads the positional clause

#### Scenario: Two displaced holders cannot strike each other and neither marker is consumed
- **WHEN** two displaced entities select each other for single-target physical strikes
- **THEN** each strike rejects at the target-side gate before any self-return clear, neither pairing lands a strike while both markers are live, and both positional instances remain live with their original remaining durations (a failed climb-back toward an unreachable target consumes nothing)

### Requirement: The holder's own single-target strike is the self-return act
When the actor of a strike-class action holds a live positional-marker instance, that action SHALL clear the ACTOR's own live positional instances immediately before the action resolves, and the strike SHALL then resolve normally (climbing back into position is priced as the one re-entry action, never denied). The clear SHALL be staged inside the action's existing atomic transaction so a failed settlement restores the marker; a magic, area, item, movement, or turn-passage action SHALL NEVER clear the instance; the clear SHALL touch only the actor's own positional instances and no other entity's state. After the clear the holder is in position: subsequent strikes resolve ordinarily.

#### Scenario: The first melee strike after knockback climbs back and lands
- **WHEN** a displaced entity resolves a single-target physical strike against a non-displaced target
- **THEN** the positional instance is gone immediately before the strike resolves, the strike's roll and damage settle ordinarily, resources and practice accrue once, and the entity's remaining buffs are untouched

#### Scenario: Casting never climbs back
- **WHEN** a displaced entity casts a magic-school single-target spell, casts an area spell, uses an item, and simply passes into the next round
- **THEN** the positional instance stays live with its original remaining duration after every one of those paths

#### Scenario: A failed settlement restores the marker
- **WHEN** a self-returning strike's settlement fails at a later commit step after the staged clear
- **THEN** the atomic restore returns the positional instance and every other touched state, exactly like the surrounding effect rollback

### Requirement: Mounting a positional marker sweeps the holder's ground markers and refuses impossible mounts
Applying a positional-marker definition to an entity SHALL first remove that entity's live ground-marker instances through the existing scoped removal path (blown off the hazard), with zero damage or revive side effects and non-marker instances untouched, before the positional instance mounts — the order observable as sweep-then-mount. The public buff-application entry point SHALL additionally refuse to mount a positional instance on an entity that is defeated (hp ≤ 0) or recorded fled or knocked-out in its active combat session, leaving all existing state unchanged; the refusal SHALL consult only the positional clause (a ground row's mounted-anyway-then-swept behavior stays bit-identical) and SHALL never apply to non-positional rows.

#### Scenario: Knockback blows the holder off the fissure
- **WHEN** a synthetic entity holding a live ground-marker hazard instance plus an ordinary timed buff receives a positional-marker application
- **THEN** the ground instance is gone at mount time with no further ticks, the ordinary buff persists unchanged, and the positional instance is live

#### Scenario: Impossible mounts refuse without writes
- **WHEN** a positional row is applied to a defeated entity, to a fled combatant, and to a knocked-out combatant
- **THEN** each application writes nothing, the entity's active buff set is unchanged, and the same calls against a living still-fighting entity mount normally

### Requirement: A positional marker extinguishes when its holder leaves the battlefield
A live positional-marker instance SHALL end — through the existing buff-removal path, with zero further ticks or side effects — when its holder flees the combat session, is knocked out, or the combat session ends, without waiting for its authored duration, exactly like the shipped ground-marker exit extinguishment (which SHALL stay bit-identical). Ordinary buffs SHALL keep their cross-combat persistence unchanged, and out-of-combat positional holders SHALL keep the instance on its own duration clock (the sweep is battlefield-exit scoped, not an out-of-combat expiry special case).

#### Scenario: Flee, knockout, and session end sweep both marker classes
- **WHEN** a session flees, knocks out, or ends with participants holding synthetic ground markers, synthetic positional markers, and ordinary timed buffs of equal remaining duration
- **THEN** every marker instance of both classes held by exiting or ended participants is removed at the transition, no ordinary buff is touched, and neither entity's HP changes from the sweep

#### Scenario: An active holder keeps the positional marker across rounds
- **WHEN** a displaced holder stays in the fight for several rounds before expiry
- **THEN** the positional fact stays true every round until its own duration elapses or a self-return strike clears it

### Requirement: Deterministic single-target attackers skip displaced candidates
The deterministic strike-candidate selections that build scripted combat actions — the session basic-attack target picker, the delegated default attack policy's strike-class candidate selection, and the monster single-target selection path — SHALL exclude positional-marker holders from their candidate sets, falling back to no-target/no-action when every living enemy is displaced (that combatant skips its attack exactly like the every-enemy-fled case). The AREA shorthand candidate set SHALL keep displaced candidates. The exclusion SHALL be state-only and dice-free (fixed-seed reproducibility preserved), SHALL be selection hygiene rather than permission (resolution-time gating stays the single authority), and SHALL not alter any other selection metric or tie-break.

#### Scenario: A basic-attacker with one displaced enemy holds its swing
- **WHEN** a session combatant whose only living enemy is displaced reaches its basic-attack step
- **THEN** no strike request is proposed and the round proceeds with that combatant silent, deterministically under a fixed seed

#### Scenario: A monster with mixed enemies picks the reachable one
- **WHEN** a monster targeting by its configured strategy faces one displaced and one undisplaced living enemy of equal metric value
- **THEN** the undisplaced enemy is selected without any additional dice draw, and replaying the same seed and state reproduces the identical request

#### Scenario: Area actions still see displaced enemies
- **WHEN** a monster with the area preference and multiple living enemies (one displaced) chooses its area action
- **THEN** the all-enemies shorthand still includes the displaced combatant and the area resolution strikes it normally
