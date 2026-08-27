## MODIFIED Requirements

### Requirement: The status, character, and skill surfaces present truthful, non-color-only state
The `StatusPanel`, the `CharacterStatusDrawer` (housing the `EquipmentDoll`), and the `SkillBook`
components SHALL present the `status` panel payload (schema version 1), the `character` panel
payload (schema version 3), and the character's skill data: gauges (hp/mp/sp), counters (magic_level,
guild_merit), static traits, wallet, and conditions with their derived modifiers; character
details, the equipment doll's equipped items, disguise, guild rank/merit, and persona; and a skill
book with active/passive tabs, categories, search, and per-skill cost/target/cast/availability detail. The gauges and conditions come from the `status` payload; the counters,
static traits, wallet, character details, equipment, disguise, guild, and persona come from the
`character` payload. Per-skill cost, target, cast, and out-of-combat-availability detail fields are rendered only when the
character's skill data provides them (a row the data gives without detail renders without detail
cells, so nothing is invented); where the slice carries them they are the display subset of the
`context_actions` v5 skill descriptor (a `cost` object — the empty object is the free form —,
`target_spec`, the optional `freeform_scales`, and the boolean `usable_out_of_combat`). `shorthands`
is a combat-only field: the character panel's skill data SHALL NOT carry it, because the shorthand set
depends on a live battlefield/participant roster that does not exist outside combat. The character
panel's presenter SHALL populate `cost`, `target_spec`, `usable_out_of_combat`, and (for a freeform-
eligible skill the actor has mastery to scale) `freeform_scales` for every **active** skill row it can
resolve against the skill registry; a passive skill row SHALL carry only `key` and `label`, and an
active row whose key the registry cannot resolve SHALL carry only `key` and `label` as well (nothing is
invented for an unregistered key).

The skill book's category summaries, group labels, and per-skill rows SHALL NOT convey their meaning by
colour alone: a category summary pairs its skill count with the visible digit text and its
expand/collapse state with a rotating chevron shape (not a colour change); a cost cell's resource
colour-coding (MP/SP/free) always pairs with the resource unit or the word "免費" already present in
the cost text; the out-of-combat `combat` pill and the passive `被動` badge each carry their own visible
text, never a bare colour swatch. An elemental group's colour dot is decorative and SHALL be present
only for an element the binding visual reference (`docs/design/elosern-redesign/index.html`) itself
colour-codes; a group for any other element renders its text label with no dot — no dot colour is
invented for an element the reference never colour-codes.

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
The character status drawer SHALL present the `character` payload's character details, the equipment
doll's equipped items, disguise, guild rank/merit, and persona, and SHALL NOT present a field the
payload does not carry. Each surface renders only its OOB-backed payload and SHALL NOT invent any
field (the intimate/adult block has no backing field and is not built).

#### Scenario: Status is never color-only
- **WHEN** a gauge, counter, or condition is displayed
- **THEN** the gauge pairs an icon and a text label with an explicit current/maximum numeric value, each counter and static trait renders its numeric value, and each condition pairs a distinct non-color severity glyph with its label plus every numeric or derived-modifier value the payload provides — no value is conveyed by color alone

#### Scenario: Disguised stats are display-only and distinct from true traits
- **WHEN** the character payload carries disguised statistics
- **THEN** the drawer shows them as display values distinct from the true traits, the head card keeps the true trait value, and no disguised value alters combat resolution

#### Scenario: Only backed fields render
- **WHEN** the status, character, or skill surface renders
- **THEN** every shown field comes from the `status`/`character`/`skill` OOB payload and no field (including any intimate/adult field, any race, subrace, class, or faction line, and any `shorthands` value on a character-panel skill row) is invented

#### Scenario: The status surface renders as an island stack
- **WHEN** the `StatusPanel` renders with the `status` and `character` panels available
- **THEN** it renders the head card, the vitals, and the conditions as separate HUD islands composed from `CharacterHead`, `VitalsTrack`, and `ConditionChips`, and not as one boxed column card

#### Scenario: An icon-only condition chip keeps its text reachable
- **WHEN** a condition renders as an icon-only chip with a duration badge
- **THEN** its label, remaining duration, and every derived modifier are in its accessible name and are shown visibly when the chip is focused or hovered, and any hidden overflow is reachable in one action

#### Scenario: The trailing damage indicator carries no information of its own
- **WHEN** a gauge's trailing damage indicator renders
- **THEN** it is absent from the accessibility tree, shows only a previously committed ratio of that same gauge, and the numerals already carry the same information

#### Scenario: The character status drawer presents only the backed character fields
- **WHEN** the character status drawer renders with the `character` panel available
- **THEN** it presents the character details, the equipment doll's equipped items, disguise, guild rank/merit, and persona, and no field the payload does not carry is rendered

#### Scenario: An active skill row carries its registry-backed descriptor detail
- **WHEN** the character panel's presenter serializes an active skill row whose key resolves in the skill registry
- **THEN** the row carries `cost`, `target_spec`, `usable_out_of_combat`, and — when the skill is freeform-eligible and the actor holds scaling mastery — `freeform_scales`, and the `SkillBook` renders a `combat` pill for a row whose `usable_out_of_combat` is `true`

#### Scenario: A passive row and an unregistered active key stay bare
- **WHEN** the character panel's presenter serializes a passive skill row, or an active skill row whose key does not resolve in the skill registry
- **THEN** the row carries only `key` and `label`, and `SkillBook` renders it with no cost, target, cast, or `combat` pill

#### Scenario: A skill category and cost cell are never color-only
- **WHEN** a skill category summary or a skill row's cost cell renders
- **THEN** the category summary shows its skill count as a digit and its open/closed state as a rotating chevron shape, and the cost cell's colour always accompanies the `mp`/`sp`/`免費` text already in the cell — no state is conveyed by colour alone

#### Scenario: A group dot renders only for a reference-sampled element
- **WHEN** an elemental-magic group renders whose element the binding visual reference colour-codes (fire, water, wind) or whose category is `sexual_act`
- **THEN** its label is preceded by the reference's exact colour dot; a group for any other element renders with no dot, because no dot colour is invented for an element the reference never colour-codes
