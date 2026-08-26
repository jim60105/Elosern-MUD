## Why

`CharacterStatusDrawer.vue` (the `角色狀態` drawer, H4 `webclient-hud-04-reference-drawers`) renders every
one of its sections — vitals, attributes/traits, condition roster, and guild counters — as a flat list of
`label ... value` rows separated by a plain 1px top border, with no section heading text at all (confirmed
by reading `CharacterStatusDrawer.vue:135-262`: each `.character-status-drawer__section` carries only
`border-top: var(--line)`, never an `<h4>` or label child). `docs/design/elosern-redesign/index.html:1063-1087`
renders the identical data — the same hp/mp/sp resources, the same true-trait rows, the same condition
roster, the same guild counters — as labelled `<section class="block"><h4>...</h4>` groups, with vitals and
attributes laid out as a 2-column grid of bordered stat tiles (`.statgrid`/`.statrow`,
`index.html:432-435`) and conditions as a wrapped row of rounded pill badges
(`.pillrow`/`.pill`, `index.html:426-430`) — the same card/pill visual language `ConditionChips.vue`,
`CharacterHead.vue`, and `VitalsTrack.vue` already use correctly elsewhere in this HUD (confirmed: those
three files' `.hud`/`.chip`/`.track` rules are already byte-for-byte matches of the design's `--panel`,
`--radius`, `--line` tokens). The drawer is the one HUD surface that never received this chrome pass, so
opening it produces a page of undifferentiated plain text next to the rest of the HUD's carded, gridded
presentation — the single largest confirmed "比例和細節不一樣" (proportions/details don't match) gap found
by screenshotting the live client against the design at 1440×900 and reading both sides' source.

This is presentation-only: every value the drawer renders today (resources, traits, conditions, guild
counters) already exists in the committed `status`/`character` payloads: no new field is read, no new
network request is made, and the existing content-correctness requirement (`webclient-contextual-hud`'s
"The character-status drawer degrades section by section and never substitutes a disguise") is unaffected.

## What Changes

- Add a small-caps section-label heading (matching `ConditionChips.vue`'s existing `.clab` style: e.g.
  `生命量`/`屬性`/`計數 · 公會`/`狀態`) to each of the drawer's vitals, traits, conditions, and guild
  sections, so every section states what it is exactly like the design and every other HUD island already
  do.
- Re-chrome the vitals and traits sections from flat rows into the design's 2-column `statgrid`/`statrow`
  card-tile layout: each stat (生命/魔力/耐力, 攻擊/敏捷/防禦/魔法階級) becomes its own bordered, rounded
  tile with the label at the left and the `current / maximum` (or trait current/max) value in gold
  monospace at the right, using the design's exact `--ink-820`/`--ink-700`/9px-radius/`9px 12px` padding
  values. The guild counters (功績, 公會階級) move into the same grid pattern. No value, ordering, or
  content-availability rule changes — only the presentational wrapper around each existing row.
- Re-chrome the condition roster from flat wrapped label/severity/timer/modifier rows into the design's
  wrapped pill-badge row (`pillrow`/`pill`): one rounded pill per condition, carrying the label and a
  trailing muted "stat" suffix. The suffix carries the SAME content the row shows today — the visible
  severity word (`SEVERITY_LABELS`, e.g. `增益`/`減益`), the non-color severity glyph, and the
  timer/modifier text — none of it is dropped; only its layout moves from a separate flex-wrapped span
  into the pill's muted suffix. Pills are colored by severity using the same five
  `--buff`/`--debuff`/`--warn`/`--crit`/neutral tint rules `ConditionChips.vue`'s `.chip--*` classes
  already define (reused, not reinvented — the design's own markup only demonstrates two of the five
  severities in its static sample).
- **Explicitly out of scope (non-goals):** the vitals/attributes/conditions *content* rules already
  specified by `webclient-contextual-hud` (registry-owned unavailable reasons, the disguise
  true/displayed comparison, the absent intimate-state block, the single wallet location); `EquipmentDoll.vue`
  (already deliberately re-chromed in H4 task 6.3 to the design's named-slot boxes); the disguise,
  wallet, and persona-background sections (already plain text in the design itself, `index.html:1087`).
- **BREAKING**: none. Every `data-testid` on the drawer's rows is unchanged; this is a template/style-only
  re-chrome of existing rows, not a restructuring of what is rendered or its DOM test hooks.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-contextual-hud`: the "character-status drawer degrades section by section and never
  substitutes a disguise" requirement gains explicit presentation scenarios: each section carries a
  labelled heading, the vitals/attributes/guild-counter sections render as the shared card-tile grid, and
  the condition roster renders as the shared pill-badge row — all using the same chrome tokens the rest of
  the HUD already uses, with no change to which values are shown or when a section degrades.

## Impact

- **Code**: `web/webclient-app/components/CharacterStatusDrawer.vue` only (template + scoped style).
  `EquipmentDoll.vue`, `ConditionChips.vue`, `CharacterHead.vue`, and `VitalsTrack.vue` are read for their
  existing chrome values (`--radius`, `--line`, `--panel`, the five severity tint rules) but not edited —
  their token values are reused, not duplicated ad hoc.
- **Stories**: update the existing `web/webclient-app/stories/Data/CharacterStatusDrawer.stories.js`
  (title `Data/CharacterStatusDrawer`, frozen in `component-manifest.json`) to cover a populated
  vitals/traits/conditions/guild state and the degraded (`character` unavailable) state, so the new
  grid/pill chrome is visible in Storybook against both states.
- **Tests**: existing `character-status-drawer__*` testid-based tests are unaffected (same hooks, same
  values); add a component test asserting the new section-heading elements are present and a
  bounding-box/visual check (reusing the pattern from the sibling minimap-crowding change) that stat
  tiles and pills never overlap or clip their text at 1440×900 and 1280×720.
- **No protocol, read-model, store, or OOB payload changes** — with one narrow exception found during
  verification: the global JSON-safety integer bound is relaxed to the full JavaScript-safe range so the
  deterministic `combat_modifiers.yaml`'s signed modifier values (`defense: -15`, `accuracy: -10`) pass
  the client's envelope validation and reach the drawer's full condition roster. The `status`/`character`
  panel contracts and the store's `elosern.js` slices are untouched.
