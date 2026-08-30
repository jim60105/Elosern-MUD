## MODIFIED Requirements

### Requirement: A delegated non-Monster entity is never proposed a tier-blocked elemental spell
`world/rules/combat.py`'s `default_attack_policy(entity, battlefield)` SHALL apply the shared
cast-eligibility predicate (`world.rules.progression.can_cast_skill`) to every owned `ACTIVE` skill
with a `damage:`-prefixed effect it considers, so the first affordable, resolver-ready damage skill
in `entity.skills.owned_keys()` order is selected. A tier-blocked elemental spell SHALL be skipped in
favor of the next legal candidate — in practice the innate `basic_attack`, which always passes the
gate — and SHALL never be proposed in an `ActionRequest` that `ActionResolver` rejects. The predicate
SHALL be the only tier-gate applied by this policy; the policy SHALL NOT raise on a malformed spell
(the predicate fails closed).

#### Scenario: An over-tier affordable spell falls back to the innate basic_attack
- **WHEN** `default_attack_policy` runs for a non-Monster entity (e.g. a party NPC) that owns an
  affordable elemental spell above its element-effective tier — `skills=["firestorm"]`,
  `magic_power == 15`, `mp >= 30`, `affinity_elements == []`, no `fire_mastery` — and a living enemy
  is present
- **THEN** the returned `ActionRequest` names `"basic_attack"` targeting that enemy, never the
  tier-blocked spell, and `ActionResolver` accepts the request

#### Scenario: A mastery-owned spell is still chosen by the delegated policy
- **WHEN** the same over-tier-skill entity additionally owns `"fire_mastery"` in `owned_keys()`
- **THEN** `default_attack_policy` returns an `ActionRequest` naming the elemental spell, because the
  shared predicate honors the direct-mastery override

#### Scenario: A companion with only a blocked spell still acts every round
- **WHEN** a party NPC owning only the tier-blocked `firestorm` (plus the innate skills) fights
  through `combat.run_round` against a living enemy
- **THEN** every round the NPC's resolved `basic_attack` action produces an `EventLog` entry — no
  round silently discards a rejected request and no `action_skipped` entry is emitted for a castable
  entity
