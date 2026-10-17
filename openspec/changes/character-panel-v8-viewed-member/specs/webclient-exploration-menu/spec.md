# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: The character panel is an exact read-only version-7 panel`
- TO: `### Requirement: The character panel is an exact read-only version-8 panel`

## MODIFIED Requirements

### Requirement: The character panel is an exact read-only version-8 panel
The production presentation registry SHALL register panel name `character` at schema version 8 with `available` true and `kind` `character`, built for the session's viewed party member (falling back to the commander) in exploration and combat, and its available payload SHALL contain exactly `schema_version`, `available`, `kind`, `member_id`, `traits`, `conditions`, `actives`, `passives`, `equipment`, `disguise`, `guild`, and `wallet`, plus the optional `full_title`. Persona prose and intimate state SHALL NOT appear; `party_member` publishes them.

#### Scenario: Expanded state shows true values and an honest disguise
- **WHEN** an elf with active disguise opens the Character root
- **THEN** `traits` report the true values, `disguise` lists the displayed values with `active == true`, and no trait row substitutes a disguised value for a true one

#### Scenario: Worn gear decomposes into named layers
- **WHEN** an actor wearing 騎士全套板甲 with one matching condition rule opens the Character root
- **THEN** the defense row carries `base`, an `effective` equal to the shared-formula value, and layers naming the condition and the item with their kinds and amounts, and the HP row's `max` decomposes over the stored base plus an equipment flat cap layer

#### Scenario: Undisguised actor has an empty displayed list
- **WHEN** an actor has no active disguise
- **THEN** `disguise.active` is false, `displayed` is empty, and the panel still reports true traits, conditions, actives, passives, equipment, guild rank, and wallet

#### Scenario: Equipment rows carry adjustment summaries
- **WHEN** the equipment section lists a registered modifier-bearing item
- **THEN** the row's `adjustment` equals the server formatter's Traditional-Chinese summary for that item, and non-bearing items carry an empty summary

#### Scenario: The panel reports the player's own persona prose
- **WHEN** an active character's persona record carries non-empty `background`, `personality`, `life_story`, and `habit` values
- **THEN** the `character` payload carries no `persona` key, and the four values are published verbatim by the `party_member` panel's commander section

#### Scenario: Missing persona fields report null
- **WHEN** an active character has no persona record, or a record missing one or more of the four keys
- **THEN** the `character` payload is unaffected and the `party_member` commander section reports each missing key as `null`

#### Scenario: Structural persona keys never render in the panel
- **WHEN** an active character's persona record carries `identity`, `appearance`, or `social_connection` values
- **THEN** neither the four prose keys nor any structural persona key appears anywhere in the `character` payload

#### Scenario: Character panel stays read-only
- **WHEN** the character panel is built for a fully-progressed actor
- **THEN** traits, conditions, actives, passives, equipment, disguise, guild, wallet, persona, sexual state, and world time are byte-for-byte unchanged

#### Scenario: A materialized sexual-state record reports its live level words
- **WHEN** an actor's `sexual_traits` handler has been materialized with `wetness` at `濕潤`, `shame` at `輕微`, `exposure` at `低`, `climax_phase` at `未達`, `pleasure` within the `中等` arousal band, and `climax_today` at 2
- **THEN** the `character` payload carries no `intimate` key, and the `party_member` panel for that member reports `arousal: "中等"`, `wetness: "濕潤"`, `shame: "輕微"`, `exposure` at the effective vocabulary member, `climax_phase: "未達"`, and `climax_today: 2` — never the raw `pleasure` counter value

#### Scenario: An unmaterialized actor resolves from its import-time baseline
- **WHEN** a valid actor has import-time baseline sexual data but no materialized `sexual_traits` handler
- **THEN** the `party_member` intimate level fields resolve from that baseline exactly as `status.py`'s existing sexual-condition resolution does, and building either panel does not materialize a `sexual_traits` Attribute

#### Scenario: An actor with no sexual-state record at all reports a null intimate section
- **WHEN** an actor has neither a materialized `sexual_traits` handler nor an import-time `sexual` baseline
- **THEN** the `party_member` intimate section is `null` and the `character` panel is unaffected

#### Scenario: A malformed sexual-state record fails the panel closed
- **WHEN** an actor's persisted sexual-state record exists but is structurally malformed (e.g. a level field's stored value is absent from its vocabulary)
- **THEN** the `party_member` panel becomes unavailable via the common unavailable form with no partial or fabricated intimate value, and the `character` panel, which no longer reads sexual state, stays available

#### Scenario: Trait rows carry the breakdown-view shape
- **WHEN** the presenter builds `traits`
- **THEN** it is a bounded list of at most 32 rows, each containing exactly `key`, `label`, `base`, `current`, nullable `max`, `effective`, and a bounded list of at most 16 `layers`, derived from the character-breakdown-view read model
- **AND** `base` is the stored literal value (never skill-baked), `effective` is the authoritative-computation value, and `current` remains the total-display field on every row: static traits report it equal to `effective`, gauges report the persisted resource remainder and an effective `max` whose layers decompose the maximum, with equipment gauge caps rendered as equipment flat layers

#### Scenario: Trait layers carry exactly their four fields in deterministic order
- **WHEN** a trait row serializes its `layers`
- **THEN** each layer contains exactly `source` (`skill`, `condition`, or `equipment`), bounded `name` (registry label only), `kind` (`mult`, `flat`, or `pct`), and signed `amount`, in the read model's deterministic order

#### Scenario: Actives and passives come from owned keys, never raw imported storage
- **WHEN** the presenter builds `actives` and `passives`
- **THEN** each is an ordered, category-grouped list of skills owned through `SkillHandler.owned_keys()`, filtered to `SkillKind.ACTIVE` and `SkillKind.PASSIVE` respectively — never read from raw imported-skill storage — with the exact grouped shape and ordering defined by this capability's skill-grouping requirement below

#### Scenario: Equipment rows carry the server-formatted adjustment summary
- **WHEN** the presenter builds `equipment`
- **THEN** it is a bounded list of at most 32 rows, each with exactly `slot`, `item_key`, bounded `display_name`, and a bounded server-formatted `adjustment` summary generated from the equipment rulebook and registry in Traditional Chinese, derived from canonical equipment state

#### Scenario: Disguise reports displayed values without touching true traits
- **WHEN** the presenter builds `disguise`
- **THEN** it contains exactly `active` (boolean), `description` (bounded string), and a bounded list of at most 32 `displayed` rows, each with exactly `key`, `label`, and `value`, describing the outwardly displayed values when `disguise_active` is true and empty otherwise
- **AND** it never substitutes disguised values for true traits

#### Scenario: Guild and wallet carry their exact scalar shapes
- **WHEN** the presenter builds `guild` and `wallet`
- **THEN** `guild` contains exactly `rank` (nullable rank key) and `merit` (non-negative safe integer), and `wallet` is a non-negative safe integer of copper

#### Scenario: Persona carries exactly the four bounded prose keys
- **WHEN** the presenter builds the version-8 payload
- **THEN** it contains no `persona` key; the four bounded prose keys `background`, `personality`, `life_story`, and `habit` are published only by the `party_member` commander section under the same persona-field cap
- **AND** that section remains display-only, never used to infer any mechanical value, and never includes the `identity`, `appearance`, or `social_connection` persona keys

#### Scenario: Intimate reports vocabulary members, never raw gauges
- **WHEN** the `party_member` presenter builds the intimate section for an actor with a persisted sexual-state record
- **THEN** `character` carries no `intimate` key, and the `party_member` section is `null` when the actor has no persisted sexual-state record at all (neither a materialized handler nor an import-time baseline), and otherwise contains exactly `arousal`, `wetness`, `shame`, `exposure`, and `climax_phase` — each a member of that field's fixed vocabulary tuple in `world/lore/sexual_vocab.py`, never a raw numeric gauge value, matching the domain's existing vocabulary-closed presentation, with `exposure` the effective value per the equipment overlay contract — and `climax_today` (a non-negative safe integer)

#### Scenario: The character presenter reads canonically and mutates nothing
- **WHEN** the `character` presenter builds its payload
- **THEN** it strictly reads canonical records and registries through the no-mutation status/service read models — sharing the same canonical trait/equipment/disguise/sexual-state source the compact `status` panel builds from, so the two panels never diverge — emits no live object reference, does not mutate traits, equipment, disguise, guild, wallet, persona, sexual state, or world time, is available in exploration and combat, and uses the common unavailable form only when the viewed member cannot be read

#### Scenario: The panel follows the viewed member
- **WHEN** the session's viewed member is companion 艾拉, including while the player possesses 卡恩
- **THEN** `member_id` is 艾拉's identity and every section reports 艾拉's true values; the payload is identical with and without possession

#### Scenario: Conditions carry exact rows
- **WHEN** the viewed member has an active buff from an altar and a debuff from fatigue
- **THEN** `conditions` lists exactly two rows, each with exactly `code`, `label`, `severity` (`buff` or `debuff`), nullable `remaining_seconds`, bounded `modifiers` summary and bounded `source`, in the status panel's deterministic order

#### Scenario: Combat keeps the panel available
- **WHEN** a snapshot is built during an active combat session
- **THEN** `character` is available for the viewed member instead of the unavailable form
