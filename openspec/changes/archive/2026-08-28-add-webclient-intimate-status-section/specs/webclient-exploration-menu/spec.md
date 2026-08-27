## MODIFIED Requirements

### Requirement: The character panel is an exact read-only version-4 panel
The production presentation registry SHALL register panel name `character` at schema version 4. Its available payload SHALL contain exactly `schema_version`, `available`, `kind`, `traits`, `actives`, `passives`, `equipment`, `disguise`, `guild`, `wallet`, `persona`, and `intimate`; `available` SHALL be true and `kind` SHALL be `character`. `traits` SHALL be a bounded list of at most 32 rows, each containing exactly `key`, `label`, `current`, and nullable `max`, derived from canonical trait values (gauges report current and maximum; static traits report the base value). `actives` and `passives` SHALL each be an ordered, category-grouped list of skills owned through `SkillHandler.owned_keys()`, filtered to `SkillKind.ACTIVE` and `SkillKind.PASSIVE` respectively — never read from raw imported-skill storage — with the exact grouped shape and ordering defined by this capability's skill-grouping requirement below. `equipment` SHALL be a bounded list of at most 32 rows, each with exactly `slot`, `item_key`, and bounded `display_name`, derived from canonical equipment state. `disguise` SHALL contain exactly `active` (boolean), `description` (bounded string), and a bounded list of at most 32 `displayed` rows, each with exactly `key`, `label`, and `value`, describing the outwardly displayed values when `disguise_active` is true and empty otherwise; it SHALL NEVER substitute disguised values for true traits. `guild` SHALL contain exactly `rank` (nullable rank key) and `merit` (non-negative safe integer). `wallet` SHALL be a non-negative safe integer of copper. `persona` SHALL contain exactly `background` (a nullable bounded string from the character's persona record, omitted content rendered as `null`); the section is display-only and is never used to infer any mechanical value. `intimate` SHALL be `null` when the actor has no persisted sexual-state record at all (neither a materialized handler nor an import-time baseline), and otherwise SHALL contain exactly `arousal`, `wetness`, `shame`, `exposure`, and `climax_phase` — each a member of that field's fixed vocabulary tuple in `world/lore/sexual_vocab.py` (never a raw numeric gauge value, matching the domain's existing vocabulary-closed presentation) — and `climax_today` (a non-negative safe integer). The presenter SHALL strictly read canonical records and registries through the no-mutation status/service read models — sharing the same canonical trait/equipment/disguise/sexual-state source the compact `status` panel builds from, so the two panels never diverge — SHALL emit no live object reference, SHALL NOT mutate traits, equipment, disguise, guild, wallet, persona, sexual state, or world time, and SHALL use the common unavailable form outside exploration mode.

#### Scenario: Expanded state shows true values and an honest disguise
- **WHEN** an elf with active disguise opens the Character root
- **THEN** `traits` report the true values, `disguise` lists the displayed values with `active == true`, and no trait row substitutes a disguised value for a true one

#### Scenario: Undisguised actor has an empty displayed list
- **WHEN** an actor has no active disguise
- **THEN** `disguise.active` is false, `displayed` is empty, and the panel still reports true traits, actives, passives, equipment, guild rank, wallet, and the persona background

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
- **THEN** `intimate` reports `arousal: "中等"`, `wetness: "濕潤"`, `shame: "輕微"`, `exposure: "低"`, `climax_phase: "未達"`, and `climax_today: 2` — never the raw `pleasure` counter value

#### Scenario: An unmaterialized actor resolves from its import-time baseline
- **WHEN** a valid actor has import-time baseline sexual data but no materialized `sexual_traits` handler
- **THEN** `intimate`'s level fields resolve from that baseline exactly as `status.py`'s existing sexual-condition resolution does, and building the panel does not materialize a `sexual_traits` Attribute

#### Scenario: An actor with no sexual-state record at all reports a null intimate section
- **WHEN** an actor has neither a materialized `sexual_traits` handler nor an import-time `sexual` baseline
- **THEN** `intimate` is `null` and no other section of the panel is affected

#### Scenario: A malformed sexual-state record fails the panel closed
- **WHEN** an actor's persisted sexual-state record exists but is structurally malformed (e.g. a level field's stored value is absent from its vocabulary)
- **THEN** the entire `character` panel becomes unavailable via the common unavailable form, with no partial or fabricated `intimate` value

### Requirement: Character panel skills are grouped by category with the same ordering rule as the combat panel
Each of `actives` and `passives` SHALL be an ordered array of category groups, structurally identical
in shape to `context_actions`'s `skills` field: each category group SHALL contain the category's
stable key, a bounded display label, and an ordered array of one or more sub-groups; each sub-group
SHALL contain a nullable group key, a label that is non-null exactly when the group key is non-null,
and an ordered array of `{key, label}` skill rows, each bounded the same as the prior version's
passive-row bounds. Category ordering SHALL follow `SkillCategory`'s declaration order; sub-group
ordering within `elemental_magic` SHALL follow `ELEMENT_REGISTRY`'s declaration order. A category with
zero owned skills of that kind (active or passive) SHALL be omitted from the corresponding array
entirely; a category whose skills carry no `group` SHALL emit exactly one sub-group with a `null`
group key and label. Within each sub-group, skill rows SHALL be ordered as `SkillHandler.owned_keys()`
returns them, without alphabetical reordering. The total count of skill rows across every category
and sub-group, flattened, SHALL NOT exceed 32 for `passives` and SHALL NOT exceed 32 for `actives`,
tracked as independent bounds; these bounds apply to the flattened totals, not to the count of
top-level category-group entries in either array, which is separately bounded by the number of
`SkillCategory` members plus exactly one — the extra slot carrying the presentation-only synthetic
fallback group (category `"unknown"`) for keys absent from `SKILL_REGISTRY`, so an entity owning
skills in every real category plus one unregistered key still renders.

#### Scenario: Innate active skills are visible for the first time
- **WHEN** the character panel is built for a freshly created character with no imported skill data
- **THEN** `actives` contains a `movement` category group whose one sub-group lists `flee`, and a
  `martial_arts` category group whose one sub-group lists `basic_attack` — both previously absent from
  every out-of-combat listing

#### Scenario: Category ordering matches the combat panel's rule
- **WHEN** an entity owns skills from `movement` and `elemental_magic` only
- **THEN** the `actives` array lists the `elemental_magic` category group before the `movement`
  category group, matching `SkillCategory`'s declaration order

#### Scenario: An empty active or passive category is omitted
- **WHEN** an entity owns no `PASSIVE`-kind skill classified `sexual_act`
- **THEN** `passives` contains no category group whose `category` is `"sexual_act"`

#### Scenario: A category with no group carries exactly one null-keyed sub-group
- **WHEN** an entity owns one or more `martial_arts` skills (a category whose members never declare a
  `group`)
- **THEN** the `martial_arts` category group's `groups` array contains exactly one sub-group whose
  `group` and `label` are both `null`

#### Scenario: The flattened row-count bound rejects a payload whose total exceeds the limit even when its category-group count is small
- **WHEN** a hand-constructed `passives` (or `actives`) payload has few top-level category-group
  entries but a flattened total row count across all of their sub-groups exceeding 32
- **THEN** validation rejects the payload, because the bound applies to the flattened total, not to
  the count of top-level category-group entries

#### Scenario: A skill key absent from the registry degrades to its own key rather than raising
- **WHEN** an entity's stored skill data names a key absent from `SKILL_REGISTRY`
- **THEN** the panel does not raise, and that key appears as a `{key, label}` row (with `label`
  equal to `key`) inside one synthetic category group appended after every real `SkillCategory`
  group, in whichever of `actives`/`passives` its original stored bucket indicates
