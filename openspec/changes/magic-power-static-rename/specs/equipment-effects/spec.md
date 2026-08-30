## MODIFIED Requirements

### Requirement: The equipment-effect rulebook validates a closed schema at load time
The equipment-effect rulebook SHALL be loaded through one validated loader that is idempotent on reload and accepts a path override for tests. Each entry SHALL contain only the closed vocabulary: `adjustments` restricted to `atk_phys`, `defense`, `magic_power`, `agility` (signed integer or signed percent string), `mp_cost` and `sp_cost` (signed percent strings only), `pleasure_gain` and `heal_gain` (signed percent strings only); plus `gauge_caps` (positive integers over `hp`/`mp`/`sp`), `immune` and `attached_buffs` (lists of buff keys), and `exposure_bias` (signed integer). Malformed entries SHALL fail the load with a named error; the loader SHALL NOT repair, clamp, or silently drop deviating data.

#### Scenario: Out-of-vocabulary field is rejected
- **WHEN** a rulebook entry contains any field or adjustment key outside the closed vocabulary
- **THEN** the load raises the named rulebook error and nothing loads

#### Scenario: Percent-shaped fields reject flat values
- **WHEN** an `mp_cost` adjustment is authored as a flat integer or an `atk_phys` adjustment as a percent string
- **THEN** the load fails, keeping the flat/percent kinds unambiguous for later consumer changes
