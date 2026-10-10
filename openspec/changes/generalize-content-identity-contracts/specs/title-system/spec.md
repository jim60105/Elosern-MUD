# Spec Delta

## MODIFIED Requirements

### Requirement: compose_title is the single pure composition of the full title
`world/rules/titles.py` SHALL define `compose_title(fixed: str | None, epithet: str | None) -> str` joining the non-empty parts fixed-first, epithet-second, with a full-width space (「　」), returning the empty string when both slots are empty. No consumer SHALL store a composed copy; every read composes live from the two slots' identifiers.

#### Scenario: Both slots compose with the full-width space
- **WHEN** `compose_title("F級冒險者", "測試異名")` is called
- **THEN** it returns 「F級冒險者　測試異名」

#### Scenario: A single occupied slot omits the separator
- **WHEN** either argument is `None`
- **THEN** the result is the other part alone, and `compose_title(None, None)` returns `""`

#### Scenario: The empty composition falls back to the name, never a placeholder
- **WHEN** the composition is the empty string
- **THEN** narrative consumers fall back to the character's own name and the LLM prompt's identity section is omitted entirely, never filled with a placeholder

### Requirement: The fixed-title lore registry validates and syncs idempotently
`world/lore/titles.py` SHALL hold frozen `FixedTitleDef(key, display_name_zh, category, flavor_zh, hint_zh, predicate)` entries in a keyed registry mirrored into Evennia Scripts idempotently at startup, alongside the registry constant `STARTER_EPITHET` (authored display and origin basis). Load validation SHALL reject malformed or ambiguous registries before anything is published.

#### Scenario: A dangling predicate reference fails at load
- **WHEN** a registry row's predicate names a nonexistent quest key
- **THEN** registry load raises naming the row and the dangling reference

#### Scenario: Startup sync twice changes nothing
- **WHEN** the title registry sync runs twice against one database
- **THEN** the mirrored Script state is identical after the second run

#### Scenario: A clergy-category row is accepted; a foreign category is not
- **WHEN** a ladder row declares the 聖職 category, and a planted row declares a category outside the closed enum
- **THEN** the ladder row loads and the planted row raises naming the row

#### Scenario: Duplicate keys and empty hints fail at load
- **WHEN** the registry carries a duplicate key or a row with empty `hint_zh`, or a predicate references a nonexistent registry face (element, monster threat tier, quest key, guild rank key, sexual experience type)
- **THEN** load validation rejects the registry

#### Scenario: Ambiguous equip identifiers fail at load
- **WHEN** a `display_name_zh` is duplicated or a key equals another row's display
- **THEN** load validation rejects the registry, keeping every equip identifier unambiguous

#### Scenario: An overlong display fails at load
- **WHEN** a row's display is longer than 63 code points
- **THEN** load validation rejects the registry

#### Scenario: The published registry is immutable
- **WHEN** a caller attempts in-place mutation of the published registry
- **THEN** the immutable mapping proxy refuses it

#### Scenario: Predicate families are declarative
- **WHEN** the predicate families (`lineage_complete`, `mastery_owned`, `first_kill_tier`, `quest_completed`, `guild_rank_reached`, `sexual_experience`, `counter_threshold`, `church_skills_redeemed`) are inspected
- **THEN** each carries parameters only; `church_skills_redeemed` carries the integer `threshold` parameter and references no external registry face

#### Scenario: The clergy category joins the codex vocabulary
- **WHEN** the shipped clergy ladder rows validate at module load
- **THEN** they validate against the codex `category` vocabulary extended with the 聖職 (`clergy`) member, exactly as the guild rows validate against the guild-rank face

### Requirement: Guild registration and rank promotion grant paired titles atomically
Each `GUILD_RANK_REGISTRY` row SHALL pair one fixed title. The existing `world/rules/guild.py::register_adventurer` transaction SHALL grant the F-rank title (「F級冒險者」) in one commit, with no planner or LLM involvement. Exam promotions SHALL grant the new rank's title inside `settle_exam_outcome`'s promotion transaction; a rolled-back promotion removes it.

#### Scenario: Registration banks the rank title only
- **WHEN** a fresh character completes guild registration
- **THEN** the collection holds fixed 「F級冒險者」 with the fixed slot auto-equipped, no epithet entry exists, and the live full title is 「F級冒險者」

#### Scenario: The composed starter title arrives at the first reward claim
- **WHEN** a registered member completes their first guild reward claim
- **THEN** the collection holds fixed 「F級冒險者」 plus the authored starter epithet, both empty slots auto-equip and the live full title composes that fixed title with the authored epithet display

#### Scenario: Re-registration is inert
- **WHEN** an already-registered member registers again
- **THEN** collection and equip record are unchanged

#### Scenario: Promotion grants inside the transaction; rollback revokes
- **WHEN** an exam promotion commits, and separately when the same promotion is rolled back
- **THEN** the E-rank title appears exactly in the first case

#### Scenario: Re-registration dedupes through the fixed-key rule
- **WHEN** a member registers again
- **THEN** the grant is an idempotent no-op through the fixed-key dedupe rule

#### Scenario: The starter epithet is granted at the first reward claim, not registration
- **WHEN** guild registration completes
- **THEN** the authored starter epithet is not granted; the actor's first reward claim banks its configured display and origin through the regular writer in the claim transaction

#### Scenario: Non-promotion guild changes never revoke titles
- **WHEN** merit changes, branch moves, or any future demotion occurs
- **THEN** banked titles are not revoked
