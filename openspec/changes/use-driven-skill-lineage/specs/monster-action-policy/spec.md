## RENAMED Requirements

- FROM: `### Requirement: A delegated non-Monster entity proposes the first affordable resolver-backed damage skill`

- TO: `### Requirement: A delegated non-Monster entity proposes the first usable resolver-backed damage skill`

## MODIFIED Requirements

### Requirement: A delegated non-Monster entity proposes the first usable resolver-backed damage skill
`world/rules/combat.py`'s `default_attack_policy(entity, battlefield)` SHALL consider every owned
`ACTIVE` skill with a `damage:`-prefixed effect and select the first one `ActionResolver` can
resolve — ownership and MP affordability are the only eligibility gates until
consume. A skill the resolver would reject (prerequisite-unsatisfied per `can_use_skill`,
unowned, or MP-unaffordable for the current gauge) SHALL be skipped in favor of the next candidate — in practice the innate `basic_attack`, which is
always affordable — and SHALL never be proposed in an `ActionRequest` that `ActionResolver` rejects.
The policy SHALL NOT raise on a malformed spell.

#### Scenario: A prerequisite-unsatisfied spell falls back to the innate basic_attack
- **WHEN** `default_attack_policy` runs for a non-Monster entity (e.g. a party NPC) that owns an
  affordable `firestorm` whose `scorching_wave` prerequisite is below the edge threshold — and a
  living enemy is present
- **THEN** the returned `ActionRequest` names `"basic_attack"` targeting that enemy, never the
  gated spell, and `ActionResolver` accepts the request

#### Scenario: An unaffordable spell falls back to the innate basic_attack
- **WHEN** `default_attack_policy` runs for a non-Monster entity (e.g. a party NPC) that owns an
  elemental spell it cannot afford — `skills=["firestorm"]`, `mp < 30` — and a living enemy
  is present
- **THEN** the returned `ActionRequest` names `"basic_attack"` targeting that enemy, never the
  unaffordable spell, and `ActionResolver` accepts the request

#### Scenario: A usable owned spell is chosen ahead of the innate
- **WHEN** the entity owns an affordable damage spell earlier in `owned_keys()` order than the innate
  skills, and its prerequisites are satisfied
- **THEN** `default_attack_policy` returns an `ActionRequest` naming that spell, because it passes
  `can_use_skill` and affordability

#### Scenario: A companion with only an unaffordable spell still acts every round
- **WHEN** a party NPC owning only the unaffordable `firestorm` (plus the innate skills) fights
  through `combat.run_round` against a living enemy
- **THEN** every round the NPC's resolved `basic_attack` action produces an `EventLog` entry — no
  round silently discards a rejected request and no `action_skipped` entry is emitted for a castable
  entity
