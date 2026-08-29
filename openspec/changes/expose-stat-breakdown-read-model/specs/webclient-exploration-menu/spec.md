## MODIFIED Requirements

### Requirement: The character panel is an exact read-only version-5 panel
The production presentation registry SHALL register panel name `character` at schema version 5. Its available payload SHALL contain exactly `schema_version`, `available`, `kind`, `traits`, `actives`, `passives`, `equipment`, `disguise`, `guild`, `wallet`, `persona`, and `intimate`; `available` SHALL be true and `kind` SHALL be `character`. `traits` SHALL be a bounded list of at most 32 rows, each containing exactly `key`, `label`, `base`, `current`, nullable `max`, `effective`, and a bounded list of at most 16 `layers`, derived from the character-breakdown-view read model: `base` is the stored literal value (never skill-baked), `effective` is the authoritative-computation value, `current` remains the total-display field on every row (static traits report it equal to `effective`; gauges report the persisted resource remainder and an effective `max` whose layers decompose the maximum, equipment gauge caps rendered as equipment flat layers); each layer contains exactly `source` (`skill`, `condition`, or `equipment`), bounded `name` (registry label only), `kind` (`mult`, `flat`, or `pct`), and signed `amount`, in the read model's deterministic order. `actives` and `passives` SHALL each be an ordered, category-grouped list of skills owned through `SkillHandler.owned_keys()`, filtered to `SkillKind.ACTIVE` and `SkillKind.PASSIVE` respectively — never read from raw imported-skill storage — with the exact grouped shape and ordering defined by this capability's skill-grouping requirement below. `equipment` SHALL be a bounded list of at most 32 rows, each with exactly `slot`, `item_key`, bounded `display_name`, and a bounded server-formatted `adjustment` summary generated from the equipment rulebook and registry in Traditional Chinese, derived from canonical equipment state. `disguise` SHALL contain exactly `active` (boolean), `description` (bounded string), and a bounded list of at most 32 `displayed` rows, each with exactly `key`, `label`, and `value`, describing the outwardly displayed values when `disguise_active` is true and empty otherwise; it SHALL NEVER substitute disguised values for true traits. `guild` SHALL contain exactly `rank` (nullable rank key) and `merit` (non-negative safe integer). `wallet` SHALL be a non-negative safe integer of copper. `persona` SHALL contain exactly `background` (a nullable bounded string from the character's persona record, omitted content rendered as `null`); the section is display-only and is never used to infer any mechanical value. `intimate` SHALL be `null` when the actor has no persisted sexual-state record at all (neither a materialized handler nor an import-time baseline), and otherwise SHALL contain exactly `arousal`, `wetness`, `shame`, `exposure`, and `climax_phase` — each a member of that field's fixed vocabulary tuple in `world/lore/sexual_vocab.py` (never a raw numeric gauge value, matching the domain's existing vocabulary-closed presentation; `exposure` is the effective value per the equipment overlay contract) — and `climax_today` (a non-negative safe integer). The presenter SHALL strictly read canonical records and registries through the no-mutation status/service read models — sharing the same canonical trait/equipment/disguise/sexual-state source the compact `status` panel builds from, so the two panels never diverge — SHALL emit no live object reference, SHALL NOT mutate traits, equipment, disguise, guild, wallet, persona, sexual state, or world time, and SHALL use the common unavailable form outside exploration mode.

#### Scenario: Expanded state shows true values and an honest disguise
- **WHEN** an elf with active disguise opens the Character root
- **THEN** `traits` report the true values, `disguise` lists the displayed values with `active == true`, and no trait row substitutes a disguised value for a true one

#### Scenario: Worn gear decomposes into named layers
- **WHEN** an actor wearing 騎士全套板甲 with one matching condition rule opens the Character root
- **THEN** the defense row carries `base`, an `effective` equal to the shared-formula value, and layers naming the condition and the item with their kinds and amounts, and the HP row's `max` decomposes over the stored base plus an equipment flat cap layer

#### Scenario: Undisguised actor has an empty displayed list
- **WHEN** an actor has no active disguise
- **THEN** `disguise.active` is false, `displayed` is empty, and the panel still reports true traits, actives, passives, equipment, guild rank, wallet, and the persona background

#### Scenario: Equipment rows carry adjustment summaries
- **WHEN** the equipment section lists a registered modifier-bearing item
- **THEN** the row's `adjustment` equals the server formatter's Traditional-Chinese summary for that item, and non-bearing items carry an empty summary

#### Scenario: The panel reports the player's own background
- **WHEN** an active character's persona record carries a non-empty `background`
- **THEN** `persona.background` equals that text verbatim and the panel renders it as a display-only row

#### Scenario: A character without a background reports null
- **WHEN** an active character has no persona record or no background key
- **THEN** `persona.background` is `null` and no placeholder text is rendered

#### Scenario: Character panel stays read-only
- **WHEN** the character panel is built for a fully-progressed actor
- **THEN** traits, actives, passives, equipment, disguise, guild, wallet, persona, intimate, and world time are byte-for-byte unchanged

#### Scenario: A materialized sexual-state record reports its live level words
- **WHEN** an actor's `sexual_traits` handler has been materialized with `wetness` at `濕潤`, `shame` at `輕微`, `exposure` at `低`, `climax_phase` at `未達`, `pleasure` within the `中等` arousal band, and `climax_today` at 2
- **THEN** `intimate` reports `arousal: "中等"`, `wetness: "濕潤"`, `shame: "輕微"`, `exposure` at the effective vocabulary member, `climax_phase: "未達"`, and `climax_today: 2` — never the raw `pleasure` counter value

## ADDED Requirements

### Requirement: The legacy client tolerates the version-5 character payload

Until the Vue breakdown renderer lands, the legacy web client SHALL accept
character payloads at schema version 4 or 5 through version-dispatched
exact-shape validators (v5 validating the added `base`, `effective`,
`layers`, and `adjustment` fields exactly, not by relaxing v4 rules),
rendering `current`/`max` values exactly as at v4 — static traits
included, because `current` remains populated — and ignoring `layers`
without console errors. Component and Python-side fixtures SHALL pin both
version branches.

#### Scenario: Version-5 payload renders totals in the legacy client

- **WHEN** the legacy client receives a version-5 character payload with
  layer-bearing trait rows including static traits
- **THEN** it renders the same `current`/`max` values as it would for the
  equivalent v4 payload and no error is raised

#### Scenario: Version branches validate exactly

- **WHEN** a v5 payload with an unknown extra field, or a v4 payload at
  schema version 5, reaches the validator
- **THEN** it is rejected by the version-dispatched exact-shape rules
