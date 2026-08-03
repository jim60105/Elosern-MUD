## ADDED Requirements

### Requirement: ActionResolver exposes shared side-effect-free action preview
The deterministic rules layer SHALL expose a frozen preview query factored from the same pure checks used by `ActionResolver.preflight()`. Given an actor, skill, context, and optional candidate, it SHALL report enabled state, the exact stable rejection reason and resource detail when disabled, and valid targets or applicable AREA shorthands. It SHALL cover ownership and active kind, current resources, exact target shape, presence, alive state, range, faction, action-blocking buffs, `actions_per_turn == 0`, registered effect prefixes, and time metadata. Modifier evaluation SHALL read a no-create context from existing stored buff and sexual-state data and SHALL NOT materialize a lazy handler or default. Preview SHALL NOT roll randomness, stage or apply effects, construct EventLogs, invoke event-effect planners, mutate any persistent or nonpersistent game state, or advance world time. `preflight()` and final `resolve()` SHALL remain authoritative and SHALL rerun their required checks.

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
