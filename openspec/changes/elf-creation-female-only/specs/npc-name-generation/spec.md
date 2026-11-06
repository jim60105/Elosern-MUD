## MODIFIED Requirements

### Requirement: roll_name_for_race resolves via NAME_PACK_BY_RACE with a bound-packs-only random fallback
`world/rules/namegen.py` SHALL expose `roll_name_for_race(race_key: str | None, sex: str | None, rng: Random) -> str` that resolves the pack through `NAME_PACK_BY_RACE` when `race_key` names a bound race, delegating to the same rolling logic as `roll_name`. When `race_key` is `None` or has no mapping, it SHALL choose uniformly at random via `rng` among the packs that appear as values of `NAME_PACK_BY_RACE` (the race-bound packs). A race's declared sex set SHALL bound the resolved sex.

#### Scenario: Bound races roll from their mapped pack
- **WHEN** `roll_name_for_race` is called with `"human"`, `"elf"`, or `"beastfolk"`
- **THEN** the given and surname components of the result come from the pools of the pack mapped
  to that race in `NAME_PACK_BY_RACE` (`fantasy-human`, `fantasy-elf`, `fantasy-orc` respectively)

#### Scenario: Unbound or missing race falls back to a random bound pack
- **WHEN** `roll_name_for_race` is called with `None`, an unknown race key such as `"dragonborn"`,
  or any key absent from `NAME_PACK_BY_RACE`
- **THEN** the result comes from one of the race-bound packs, chosen reproducibly via `rng`, and
  across the full seed space never comes from `fantasy-dwarf` or `fantasy-halfling`. The fallback
  SHALL offer `rng` exactly the sorted distinct values of `NAME_PACK_BY_RACE` as the choice
  candidates, so every bound pack is selectable and the choice index is decoupled from the
  mapping's literal insertion order.

#### Scenario: Unbound registered packs never join the fallback
- **WHEN** packs such as `fantasy-dwarf` and `fantasy-halfling` are registered with `race_key=None`
- **THEN** they never participate in the random fallback

#### Scenario: A race with one declared sex pins the pool for every sex it forbids
- **WHEN** `roll_name_for_race` is called for a race whose `RACE_REGISTRY` entry declares exactly
  one permitted sex, with `sex` `None`, `""`, an unrecognised value, or any other `SEX_VALUES`
  member outside that declared set
- **THEN** the given part comes from the declared sex's own pool through `rng` and no random pool
  choice is offered, so a female-only race is never named from the male or unisex pool — including
  on the creation surface, which always sends the sex its select currently displays

#### Scenario: Races with several declared sexes keep the existing mapping
- **WHEN** `roll_name_for_race` is called for a race declaring more than one permitted sex with an
  unspecified or unrecognised `sex`, or with `race_key` `None`
- **THEN** the existing random choice among `"m"`, `"f"`, and `"u"` is offered to `rng` exactly once,
  and an explicitly supplied `SEX_VALUES` member those races permit still selects its own mapped
  pool verbatim
