## Purpose

The deterministic stat-breakdown read model: a pure, fail-closed projection of every panel stat into a stored `base` plus accounting-complete, source-classified, named layers composed into the single `effective` value each stat's named authoritative shipped computation produces — assembled once per read and shared by the character panel, the text client, and the compact in-combat status surface so no surface re-derives a stat.

## Requirements

### Requirement: Breakdown read model decomposes each panel stat by source

The status read model SHALL expose, for every panel stat, a breakdown row of stored `base` (the literal, never skill-baked), accounting-complete named `layers`, and one `effective` value composed FROM those layers. Each layer SHALL be exactly `{source, name, kind, amount}` with `source` in the closed set `skill|condition|equipment`, `kind` in `mult|flat|pct`, a signed amount, and a `name` resolved through the corresponding registry label.

#### Scenario: Plate armor appears as its own layer

- **WHEN** an actor wearing 騎士全套板甲 requests the breakdown
- **THEN** the defense row carries an equipment layer named 騎士全套板甲 with a flat amount and the agility row a pct layer, alongside any skill and condition layers

#### Scenario: Empty sources add no fake layer

- **WHEN** an actor owns no skill mults, conditions, or equipment for a stat
- **THEN** the row shows `effective` equal to `base` and an empty layer list

#### Scenario: Unresolvable label fails closed

- **WHEN** a contributing modifier has no resolvable registry display name
- **THEN** the read model raises and the character panel serves the common unavailable form instead of an incomplete breakdown

#### Scenario: Panel reads never create state

- **WHEN** a breakdown is built for an entity whose equipment, buff, skills, or sexual handlers were never materialized
- **THEN** no handlers or attributes are created and persisted attributes are byte-for-byte identical before and after the build

#### Scenario: Layer labels resolve through their registries

- **WHEN** a layer's `name` is resolved
- **THEN** it comes from the corresponding registry label: the skill registry label, the
  `STATUS_DISPLAY` label, or the item display name

#### Scenario: Layer order is deterministic on fixed identity tuples

- **WHEN** a row's layers are ordered
- **THEN** skills sort by skill key, then conditions by (source kind, key), then equipment by
  (slot order, item key)

#### Scenario: Accounting is complete and bounded, failing closed

- **WHEN** a non-empty contribution feeding the effective value has no resolvable label, or a
  stat exceeds the 16-layer bound
- **THEN** the read model fails closed into the common unavailable panel form — never a silent
  skip or truncation — and every other non-empty contribution appears as a layer

#### Scenario: Gauge rows decompose with the same layer structure

- **WHEN** a gauge maximum row is built
- **THEN** it decomposes with the same layer structure (equipment gauge caps as equipment flat
  layers), while gauge `current` — persisted resource state — carries no layers

#### Scenario: Breakdown building mutates nothing

- **WHEN** a breakdown is built
- **THEN** it operates on validated stored snapshots and the no-create bundle, materializes no
  handlers, and mutates nothing

### Requirement: Each displayed stat matches its named authoritative computation

For every displayed stat, the panel's `effective` SHALL equal the shipped authoritative computation named for it under identical inputs: attack/defense via the merged-bundle flat/pct with skill mults and single final rounding; agility identical plus the ≥ 0 floor (initiative's raw-agility exception is explicitly out of parity scope); `magic_power` via the shipped skill effective-value arithmetic's rounding form; gauge maximum via the shipped gauge reader form.

#### Scenario: Panel defense equals the defense used in resolution

- **WHEN** an actor with skill mults, a matched condition rule, and worn gear has both a panel breakdown and a live defense evaluation from the same fixed inputs
- **THEN** both show the identical defense value

#### Scenario: Heavy-gear agility displays floored

- **WHEN** modifiers drive raw adjusted agility below zero
- **THEN** the panel shows agility 0, matching the consumer-side floor

#### Scenario: Gauge ceiling layers include the equipment cap

- **WHEN** an actor wearing the `hp +15` plate requests the HP breakdown
- **THEN** the maximum decomposes over the stored base plus an equipment flat layer of 15 and the panel maximum equals the heal-clamp ceiling

#### Scenario: Parity tests pin each stat to its named computation

- **WHEN** behavior tests verify displayed-stat parity
- **THEN** each stat is pinned against ITS named computation, and consumer-specific
  post-effective floors (to-hit, heal) are documented non-contradictions, not parity targets

### Requirement: Text client renders layers and compact surfaces stay totals-only

The status read model SHALL assemble the breakdown exactly once per read; the text status and inventory views SHALL render the same layer rows and equipment adjustment summaries server-side in Traditional Chinese, and the compact in-combat status surface SHALL serialize effective totals only from the same result — no second assembly path. No command key, alias, or syntax changes.

#### Scenario: Text status shows the source line

- **WHEN** a player runs the status view while wearing breakdown-bearing equipment
- **THEN** each affected stat row prints the value with its named source segments and the equipment rows print adjustment summaries

#### Scenario: Combat status stays compact and shares the source

- **WHEN** the in-combat compact status surface renders the same actor
- **THEN** it shows totals with no layer segments and its values equal the character panel's effective values from the same read
