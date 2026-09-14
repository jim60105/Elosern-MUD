# damage-state-feedback Specification

## Purpose
Define reusable passive reactions to actual damage and new negative buffs, and state-dependent recovery benefits independent of equipment or profession names.

## Requirements

### Requirement: Damage feedback follows actual loss and newly accepted negative instances
A qualified passive SHALL react once to each positive actual HP loss and each newly accepted negative buff instance, using its authored source-tier gain through the canonical state writer. Spell, item, rulebook and periodic-damage sources SHALL share this behavior. Source tier SHALL be captured at application for periodic effects; nonspell sources SHALL use the configured first-tier fallback. Misses, zero loss, healing, resource costs, immunity and instance refresh SHALL not trigger.

#### Scenario: Different damage sources share the reaction
- **WHEN** a synthetic passive owner suffers direct spell, item and periodic damage
- **THEN** each actual loss causes the configured gain once and uses its captured source tier

#### Scenario: Immune and refresh outcomes do not count
- **WHEN** a negative buff is refused by immunity or only refreshes an existing instance
- **THEN** there is no new-instance feedback

#### Scenario: New debuff and its ticks are distinct
- **WHEN** a new damaging debuff is accepted and later ticks twice
- **THEN** the new-instance event and each positive-loss tick independently trigger once

### Requirement: Feedback cascades remain within the initiating transaction
Feedback that changes arousal or phase SHALL use canonical transitions and phase reactions without recursive damage-event loops. The initiating action, item or world-clock transaction SHALL capture and restore every transitive state surface. A failed settlement SHALL leave neither the triggering loss/buff nor resulting pleasure/phase/marker changes.

#### Scenario: Feedback can enter the normal lock phase
- **WHEN** a configured damage gain crosses the recipient into in-progress
- **THEN** normal phase reactions and action locking occur without inventing a second state system

#### Scenario: Late failure restores the complete cascade
- **WHEN** an item or clock settlement fails after feedback activates a phase marker
- **THEN** HP, negative buff state, pleasure, phase, counters and marker all restore

### Requirement: Recovery-only passive adjustment composes once and is snapshotted
A configured passive SHALL provide a state-derived recovery-only modifier independent of equipment. Recovery profiles SHALL capture it on application, while ordinary direct heals and already state-scaled sacramental effects SHALL not receive it again. Existing equipment healing modifiers SHALL compose once through their own stage. Numeric conferred adjustments SHALL retain existing fractional semantics without granting binary event reactions.

#### Scenario: Equipment-independent recovery
- **WHEN** a synthetic passive owner with no equipment applies a recovery profile at a nonzero state ordinal
- **THEN** ticks include the configured captured benefit even after source state changes

#### Scenario: No duplicate sacramental multiplier
- **WHEN** the same owner uses a direct state-scaled heal and a periodic recovery profile
- **THEN** only the configured recovery profile receives the extra recovery-only modifier
