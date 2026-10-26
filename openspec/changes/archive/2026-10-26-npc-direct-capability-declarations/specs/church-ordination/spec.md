# Spec Delta

## MODIFIED Requirements

### Requirement: Church venues and clergy hosts exist as authored content
Places whose explicit venue metadata carries the `church` flag SHALL form the derived church-place set in `world/lore/church/` (the `shop_key` derivation pattern), and the derivation SHALL fail closed on a duplicate-flagged authoring conflict. The `ChurchHost` typeclass component (sibling of `GuildStaff`, a zero-state capability adapter) SHALL be authored on the one registered clergy NPC roster row (艾莉安娜‧寒水 high celebrant) through her direct component declaration.

#### Scenario: The derived church set is complete and fail-closed
- **WHEN** the lore package derives the church-place set from authored kwargs
- **THEN** every `church`-flagged place appears exactly once, and a duplicate/conflicting church kwarg authoring raises at derivation instead of silently winning

#### Scenario: The clergy host is authored and sync-idempotent
- **WHEN** the direct-capability roster derivation and `place-driven-service-sync` converge with `ChurchHost` attached to the celebrant NPC
- **THEN** she resolves through the local-service-host lookup, her spawn data carries the raised initial arousal, the sanctum steward resolves as a plain merchant without the component, and a second sync pass changes nothing

#### Scenario: The clergy row carries the raised initial arousal
- **WHEN** the clergy roster row is authored
- **THEN** that row carries the small raised-initial-arousal authoring kwarg on its spawn data

#### Scenario: The sanctum steward stays a plain merchant
- **WHEN** the roster is authored per owner decision
- **THEN** the sanctum steward 羅海西亞‧芬威克 stays a plain merchant selling the sanctum's wares and carries neither the component nor the arousal seed

#### Scenario: No consumer arrives with this change
- **WHEN** this stage ships
- **THEN** no gameplay mechanic consumes the venue set or the host — the enrollment and accrual changes do — but `place-driven-service-sync` convergence stays idempotent with the new component attached and the derived set is non-empty
