## ADDED Requirements

### Requirement: A place's authored host sex must be permitted by the host's race
Place-registry validation SHALL reject a place that authors a host whose `host_sex` is not permitted by its `host_race`'s registry declaration, naming the place, the race and the sex, and SHALL leave an unauthored host alone.

#### Scenario: An elf host declaring a non-female sex fails load
- **WHEN** a synthetic place authors a complete host with an elf `host_race` and a `host_sex` that race forbids (derived from `RACE_REGISTRY["elf"].allowed_sexes`)
- **THEN** place-registry validation raises naming the place key, the race and the declared sex, so the host can never be materialized by the startup sync

#### Scenario: A permitted host sex still loads and still reaches the host
- **WHEN** a synthetic place authors a complete elf host declaring the permitted member
- **THEN** validation passes and the synced host carries that member as its persisted sex

#### Scenario: Hosts of races that permit every member are unchanged
- **WHEN** a synthetic place authors a complete host whose race permits all of `SEX_VALUES`
- **THEN** any of the three members validates, exactly as it does today

#### Scenario: A hostless place is untouched
- **WHEN** a place authors no host at all
- **THEN** this check produces no rejection and the existing hostless rules decide
