## ADDED Requirements

### Requirement: The status, character, and skill surfaces present truthful, non-color-only state
The `StatusPanel`, `CharacterPanel`, and `SkillBook` components SHALL present the `status` panel
payload (schema version 1), the `character` panel payload (schema version 3), and the character's
skill data: gauges (hp/mp/sp), counters (magic_level, guild_merit), static traits, wallet, and
conditions with their derived modifiers; character details, equipped items, disguise, guild
rank/merit, and persona; and a skill book with active/passive tabs, categories, search, and per-skill
cost/target/cast detail. The gauges and conditions come from the `status` payload; the counters,
static traits, wallet, character details, equipment, disguise, guild, and persona come from the
`character` payload. Per-skill cost, target, and cast detail fields are rendered only when the
character's skill data provides them (a row the data gives without detail renders without detail
cells, so nothing is invented); where the slice carries them they are the display subset of the
`context_actions` v5 skill descriptor (a `cost` object — the empty object is the free form —,
`target_spec`, and the optional `freeform_scales` / `shorthands`). Status and health information
SHALL never be conveyed by color alone: gauges SHALL pair a symbol with an explicit current/maximum
numeric value, each counter and static trait SHALL render its numeric value, and each condition
SHALL pair a non-color severity glyph with its label plus every numeric or derived-modifier value
the payload provides. Disguised statistics are display-only and SHALL be shown distinct from true
traits. Each surface renders only its OOB-backed payload and SHALL NOT invent any field (the
intimate/adult block has no backing field and is not built).

#### Scenario: Status is never color-only
- **WHEN** a gauge, counter, or condition is displayed
- **THEN** the gauge pairs a symbol with an explicit current/maximum numeric value, each counter and static trait renders its numeric value, and each condition pairs a non-color severity glyph with its label plus every numeric or derived-modifier value the payload provides — no value is conveyed by color alone

#### Scenario: Disguised stats are display-only and distinct from true traits
- **WHEN** the character payload carries disguised statistics
- **THEN** the panel shows them as display values distinct from the true traits and no disguised value alters combat resolution

#### Scenario: Only backed fields render
- **WHEN** the status, character, or skill surface renders
- **THEN** every shown field comes from the `status`/`character`/`skill` OOB payload and no field (including any intimate/adult field) is invented
