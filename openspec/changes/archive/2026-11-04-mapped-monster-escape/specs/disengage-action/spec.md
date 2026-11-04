# Spec Delta

## MODIFIED Requirements

### Requirement: A successful flee adds the fleeing entity's key to Battlefield.fled; a failed attempt
Individual flee SHALL preserve the existing agility contest and stable fled identity, require a committed legal affordable journey in mapped combat, and use explicit abstract context in standalone combat; allied interactive escape SHALL retain confirmed party retreat.

#### Scenario: A successful flee is reflected in Battlefield.fled after commit
- **WHEN** a `flee` request resolves successfully with the underlying attempt succeeding
- **THEN** the actor's stable individual identity is present in `battlefield.fled` after `resolve()` returns

#### Scenario: A failed flee attempt leaves Battlefield.fled unchanged
- **WHEN** a `flee` request resolves with the underlying attempt failing
- **THEN** the actor's stable individual identity is absent from `battlefield.fled` after `resolve()` returns, and no entity's
  `traits`, `sexual`, `buffs`, or `skill_grants` values differ from their pre-call state

#### Scenario: Both outcomes still produce a real EventLog
- **WHEN** a `flee` request resolves, whether the underlying attempt succeeds or fails
- **THEN** `ActionResult.success()` returns a non-`None` `event_log` containing an entry describing the
  attempt's outcome, and the standard flat time cost is reported in both cases

#### Scenario: Allied interactive escape uses party confirmation
- **WHEN** an allied actor in an interactive player session requests this innate flee mechanism
- **THEN** the request is routed to confirmed party retreat before any individual effect mutates the battlefield; enemy individual flee keeps the mechanism above unchanged

#### Scenario: Mapped flee departure
- **WHEN** a mapped enemy succeeds through the resolver
- **THEN** fled state and actual source departure commit together; failure preserves position/group and no abstract world fallback is selected

### Requirement: The disengage effect handler computes flee success from the same agility-difference
The individual flee agility contest SHALL use d100 plus actor adjusted agility against the shared combat defender constant plus fastest eligible pursuer agility; no pursuer SHALL skip that contest only, while mapped escape SHALL still require a legal affordable route and declared atomic effect surfaces.

#### Scenario: Exact agility parity yields a 50% escape rate
- **WHEN** a flee attempt is evaluated where the fleeing entity's adjusted agility exactly equals the
  fastest living opposing combatant's adjusted agility, over 10,000 fixed-seed trials
- **THEN** the observed success rate is within a small statistical tolerance of 50%

#### Scenario: A cross-race agility gap saturates flight to a guaranteed outcome, with no special case
- **WHEN** a flee attempt is evaluated where the fleeing entity's adjusted agility differs from the
  fastest living opposing combatant's adjusted agility by 50 or more, in either direction
- **THEN** the success rate is exactly 0% (fleeing entity's deficit) or exactly 100% (fleeing entity's
  surplus), with no roll capable of changing the outcome, and no conditional in `world/rules/
  disengage.py` branches on an overwhelm ratio, an `effective_power()` value, or any
  `classify_overwhelm()`-related concept to produce this result

#### Scenario: A human cannot escape a pursuing elf
- **WHEN** a flee attempt is evaluated for a human-elite-tier fleeing entity (effective agility in
  `STATIC_TIER_REGISTRY`'s human elite band, e.g. 9) against an elf-tier pursuer (effective agility in
  that registry's elf band, e.g. 92)
- **THEN** the escape rate is exactly 0% , the same agility-difference saturation that makes the human
  unable to land a to-hit roll against that elf also makes escape from them impossible

#### Scenario: An elf can always escape a pursuing human
- **WHEN** a flee attempt is evaluated for an elf-tier fleeing entity (effective agility 92) against a
  human-elite-tier pursuer (effective agility 9)
- **THEN** the escape rate is exactly 100%

#### Scenario: The comparison uses the fastest living opposing combatant, not an average or a
player-chosen target
- **WHEN** a flee attempt is evaluated against an opposing team with multiple living, non-fled members
  of differing adjusted agility
- **THEN** the comparison uses the single greatest adjusted-agility value among them, not an average or
  any other aggregate

#### Scenario: accuracy modifiers are never read by the flee success check
- **WHEN** `_adjusted_agility()`'s implementation is inspected
- **THEN** it reads only the `agility` key of `evaluate_combat_modifiers()`'s returned bundle, never the
  `accuracy` key

#### Scenario: No living, non-fled opposing combatant makes escape automatic
- **WHEN** a flee attempt is evaluated and every member of the opposing team is dead or already fled
- **THEN** the agility contest succeeds without calling `roll_d100()`; mapped escape still fails when no legal affordable route exists

#### Scenario: The threshold constant is combat's own, reused verbatim
- **WHEN** the success check's `defender_constant` is sourced
- **THEN** it uses `world.rules.combat.COMBAT_YAML`'s existing constant verbatim , no new constant
  is declared for this check

#### Scenario: Agility adjustment uses the agility percentage only
- **WHEN** the adjusted-agility inputs to the success check are computed
- **THEN** they are adjusted by `evaluate_combat_modifiers()`'s `agility` percentage, never its
  `accuracy` value

#### Scenario: The pursuer term is the greatest effective_value("agility")
- **WHEN** `fastest_pursuer_adjusted_agility` is computed
- **THEN** it is the greatest `effective_value("agility")` among every living, non-fled member of
  the opposing team

#### Scenario: Allied interactive escape uses party confirmation
- **WHEN** an allied actor in an interactive player session requests this innate flee mechanism
- **THEN** the request is routed to confirmed party retreat before any individual effect mutates the battlefield; enemy individual flee keeps the mechanism above unchanged
