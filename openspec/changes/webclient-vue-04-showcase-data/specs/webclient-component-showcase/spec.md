## ADDED Requirements

### Requirement: The status, character, and skill surfaces present truthful, non-color-only state
The `StatusPanel`, `CharacterPanel`, and `SkillBook` components SHALL present the `status` v3 and
`character` v3 payloads and the character's skill data: gauges (hp/mp/sp), counters (magic_level,
guild_merit), static traits, wallet, and conditions with their derived modifiers; character details,
equipped items, disguise, guild rank/merit, and persona; and a skill book with active/passive tabs,
categories, search, and per-skill cost/target/cast detail. Status and health information SHALL never be
conveyed by color alone (an icon or symbol plus a numeric value are required). Disguised statistics are
display-only and SHALL be shown distinct from true traits. Each surface renders only its OOB-backed
payload and SHALL NOT invent any field (the intimate/adult block has no backing field and is not built).

#### Scenario: Status is never color-only
- **WHEN** a gauge, counter, or condition is displayed
- **THEN** it pairs an icon or symbol with a numeric value rather than relying on color alone

#### Scenario: Disguised stats are display-only and distinct from true traits
- **WHEN** the character payload carries disguised statistics
- **THEN** the panel shows them as display values distinct from the true traits and no disguised value alters combat resolution

#### Scenario: Only backed fields render
- **WHEN** the status, character, or skill surface renders
- **THEN** every shown field comes from the `status`/`character`/`skill` OOB payload and no field (including any intimate/adult field) is invented
