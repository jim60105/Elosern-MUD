## MODIFIED Requirements

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
`target_spec`, and the optional `freeform_scales` / `shorthands`).

`StatusPanel` SHALL present its share of that data as the stage's left HUD island stack rather than as
a single boxed column card: a character head card, a vitals island, and a conditions island, composed
from the `CharacterHead`, `VitalsTrack`, and `ConditionChips` components. The head card SHALL render
only identity the payloads carry — the display name, the numeric magic level with its client-derived
display rank title, the guild rank and merit, the wallet, and the disguise marker — with a glyph
portrait rather than an image, and SHALL render no race, subrace, class, or faction line, because no
such field exists in either payload. The wallet SHALL have exactly one persistently-visible surface.

Status and health information SHALL never be conveyed by color alone: gauges SHALL pair an icon and a
text label with an explicit current/maximum numeric value, each counter and static trait SHALL render
its numeric value, and each condition SHALL pair a non-color severity glyph — one distinct glyph shape
per severity, so two severities are never separated by color alone — with its label plus every numeric
or derived-modifier value the payload provides. Where a condition renders as an icon-only chip, that
label, duration, and modifier text SHALL be carried in the chip's accessible name and SHALL also be
presented visibly when the chip is focused or hovered, and any bounded overflow SHALL keep every
committed condition reachable in one action. A gauge's trailing damage indicator SHALL be decorative,
absent from the accessibility tree, and SHALL never display a value that was not previously committed
for that same gauge. Disguised statistics are display-only and SHALL be shown distinct from true
traits, and a disguised displayed value SHALL NOT be substituted for a true trait on the head card.
Each surface renders only its OOB-backed payload and SHALL NOT invent any field (the intimate/adult
block has no backing field and is not built).

#### Scenario: Status is never color-only
- **WHEN** a gauge, counter, or condition is displayed
- **THEN** the gauge pairs an icon and a text label with an explicit current/maximum numeric value, each counter and static trait renders its numeric value, and each condition pairs a distinct non-color severity glyph with its label plus every numeric or derived-modifier value the payload provides — no value is conveyed by color alone

#### Scenario: Disguised stats are display-only and distinct from true traits
- **WHEN** the character payload carries disguised statistics
- **THEN** the panel shows them as display values distinct from the true traits, the head card keeps the true trait value, and no disguised value alters combat resolution

#### Scenario: Only backed fields render
- **WHEN** the status, character, or skill surface renders
- **THEN** every shown field comes from the `status`/`character`/`skill` OOB payload and no field (including any intimate/adult field, and any race, subrace, class, or faction line) is invented

#### Scenario: The status surface renders as an island stack
- **WHEN** the `StatusPanel` renders with the `status` and `character` panels available
- **THEN** it renders the head card, the vitals, and the conditions as separate HUD islands composed from `CharacterHead`, `VitalsTrack`, and `ConditionChips`, and not as one boxed column card

#### Scenario: An icon-only condition chip keeps its text reachable
- **WHEN** a condition renders as an icon-only chip with a duration badge
- **THEN** its label, remaining duration, and every derived modifier are in its accessible name and are shown visibly when the chip is focused or hovered, and any hidden overflow is reachable in one action

#### Scenario: The trailing damage indicator carries no information of its own
- **WHEN** a gauge's trailing damage indicator renders
- **THEN** it is absent from the accessibility tree, shows only a previously committed ratio of that same gauge, and the numerals already carry the same information
