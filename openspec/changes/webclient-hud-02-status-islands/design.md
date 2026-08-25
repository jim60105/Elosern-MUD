## Context

H1 is landed and archived. The stage exists — `HudFrame.vue` is a `position:absolute; inset:0;
overflow:hidden` root with five absolutely-positioned anchors, `data-elosern-mode` gates visibility
with `display:none`, and `[data-anchor="hud-left"]` is already a 262px `flex-direction:column` with a
9px gap and `max-height: calc(100% - var(--dock-h) - 110px)`. The panels inside it do not know that.
`StatusPanel.vue` is a `display:flex; flex-direction:column` `<aside>` with an opaque `--panel`
background, a hairline border and a `--radius` — a column card. It renders, in one undifferentiated
stack: the actor name and location, three 4px gauge bars, the five counter/static trait rows, the
wallet, the condition list as bordered text pills, the disguise line and the combat line.
`LocalMap.vue` is the same shape with a 640×400 SVG inside it, and it too sits in `hud-left`, next to
`ArtPanel.vue`'s portrait catalog. `CharacterPanel.vue` repeats seven of those rows again in
`hud-right`.

H1 also left three hooks pointed at this wave. `HudFrame` declares `lowhp: { type: Boolean, default:
false }` and swaps `--vignette` for `--vignette-lowhp` under `[data-lowhp="true"]`, but `AppShell`
never binds it. `tokens.css` carries `@keyframes elosern-hp-pulse` and `--motion-hp-pulse: 1.1s`,
referenced by no rule. And the `feed` anchor is already sized `min(880px, calc(90vw - 524px))` —
262 + 230 + gutters — i.e. H1's geometry already reserves the right anchor's 230px for a minimap that
is not there yet.

The draft (`docs/design/elosern-redesign/index.html:139-215`, `:680-750`) is a different information
architecture, not a different skin. `.hud-left` is a 262px column of *separate* islands with a 9px
gap, each `background:var(--panel); backdrop-filter:blur(9px); border:var(--line);
border-radius:var(--radius); box-shadow:var(--shadow)`. The head card is portrait + name + rank line.
The vitals island is three `.vital` rows, each an icon + label + `current / max` numerals over a 10px
`.track` containing a `.ghost` (`transition: width .6s ease .25s` — a *delayed* trailing bar) and a
`.fill`. The conditions island is a wrapped row of 34×34 icon chips with a corner duration badge and a
`+N` overflow chip. The minimap is not in this stack at all: it sits in `.hud-right` under the
`.topmeta` pill, and `.mode-combat .mini{display:none!important}`.

Two of the draft's own lines are unbacked and must not survive contact with an implementation: the
head card's `拾荒者同盟 · 灰裔` faction/subrace line, and the minimap's `北 324° · 西 262°` bearing
line. The verified payloads are in the proposal; neither field exists.

Constraints inherited from the roadmap: no server, protocol or read-model change; preserve the DOM
contract identifiers and re-map everything else to `data-testid`; every wave re-maps the browser
assertions it breaks in its own change; both 1440×900 and 1280×720 supported; the client stays
shippable at every landing — no surface may become unreachable inside this wave.

## Goals / Non-Goals

**Goals**

- Turn the left anchor into the draft's island stack, and the minimap into the draft's right-anchor
  island, at parity of *information* with today's panels.
- Make damage legible: a trailing bar behind the fill, plus the low state as text, colour and the
  stage vignette H1 already wired.
- Render only fields the two payloads actually carry, and say so in the spec rather than quietly
  omitting them.
- Bound the island stack's height so the roadmap's measured 41px margin above the dock at 1280×720
  survives a realistic condition count.
- Leave every preserved identifier, the `local_map` render model, and `explore.move` submission
  untouched.

**Non-Goals**

- The character-status drawer, the equipment paper-doll, the drawers' own wallet copies (H4).
- The dock, the combat participant frame, the skill master-detail (H3).
- The full-map overlay the draft's minimap opens (H5 mounts `MapOverlay`).
- Any new read model. No companion strip, no objective tracker, no toasts, no intimate-status block.
- Any change to `status` / `character` / `local_map` payload shape, bounds, or derivation.

## Decisions

### D1 — Re-chrome `StatusPanel` into the island-stack root; do not delete it

`StatusPanel.vue` survives as the component that owns the `hud-left` stack and composes three new
children (`CharacterHead`, `VitalsTrack`, `ConditionChips`). It keeps `data-testid="status-panel"` and
the three `status-panel__gauge-value--{hp,mp,sp}` hooks, which are the exact selectors
`test_browser_combat.py` and `test_vue_transport_mount.py` use to prove that MP is deducted after a
scaled cast and that health is never colour-only. Preserving them costs one attribute each and keeps
two browser journeys entirely out of this change's blast radius.

Its rows are redistributed, not dropped: the counters and static traits (`atk_phys`, `agility`,
`defense`) are already rendered in full by `CharacterPanel`, which H1 left mounted; `magic_level` and
`guild_merit` move onto the head card's rank line; the wallet moves onto the head card; the disguise
flag becomes the head card's marker; the combat-session line becomes a vitals-island header row. No
row loses its only home inside this wave.

*Alternative rejected:* deleting `StatusPanel` and mounting three siblings directly in the anchor.
That drops `Data/StatusPanel` from the frozen manifest — a *shrink*, which H1's added growth rule does
not sanction — and falsifies the component-enumeration requirement's phrase "the status panel with its
gauges, counters, and conditions", forcing a second `webclient-component-showcase` `MODIFIED` for no
functional gain.

### D2 — The head card renders backed identity only, and says so in the spec text

The card renders exactly: a glyph portrait tile, a numeric badge, a name, a rank line, a wallet line,
and a disguise marker when `status.disguise_active` is true.

- **Portrait** — a glyph, never an image. `world/rules/art_view.py:176`: *"The actor itself is never a
  present focusable subject of their own exploration catalog."* There is no player portrait outside
  combat, and the draft itself draws `.portrait .mono` rather than a bitmap. The glyph is the first
  Unicode grapheme of `status.actor.name`; an empty name renders an empty tile, never a substitute
  character.
- **Badge** — the integer `current` of the `magic_level` trait row. It is the only bounded numeric
  progression the payload carries, and it is what the draft's `.lv` badge shape wants.
- **Rank line** — `魔階·<title>` where `<title>` is derived from that same integer, plus
  `公會 <rank> · 功績 <merit>` from `character.guild`.
- **No race, subrace, class, or faction line.** Not dimmed, not "未知", not present.

*Alternative rejected:* rendering a 職業 line from the character's skill categories (`actives[]` group
keys). Those are skill taxonomy, not a class; synthesising an identity label out of them would be
exactly the "component faked to look real" the roadmap forbids.

### D3 — The magic rank title is a client-side derivation over a duplicated display band table

The client receives `magic_level` as a bare integer; the title lives in
`world/rules/progression.py::MAGIC_RANK_BANDS` (學徒 0–15 / 術師 16–30 / 大師 31–70 / 賢者 71–90 /
主宰 90+) and is never serialized. H2 duplicates that table as a **display-only** constant in
`components/character-identity.js`, scanned in order so a magic level of exactly 90 resolves to 賢者
exactly as the server's own comment requires.

This is a knowing duplication, so it carries a knowing guard: a Vitest pins all five band boundaries
and both edge cases (0, and 90 → 賢者), and the change adds no server call, no new payload field, and
no request for one. The alternative — adding a `rank_title` string to the `character` payload — is a
presenter and schema change, which the roadmap's Non-Goals forbid outright for all six waves.

*Alternative rejected:* rendering the bare integer with no title. The draft's rank line and
REDESIGN.md §1.1's *「顯示 rank 標題＋功績」* both call for the title, and a pure function of a backed
integer is a derivation, not an invention.

### D4 — The trailing bar shows only a previously committed ratio, and is decorative

`VitalsTrack` holds the previous committed ratio of its own gauge. On a revision that lowers the
ratio, the fill animates immediately (`--motion-base`) and the trailing bar animates to the new ratio
after a delay, so the gap between them *is* the damage taken. On a revision that raises the ratio the
fill overtakes the trailing bar and no gap appears.

Three rules make this safe:

- The trailing bar is `aria-hidden` and carries no accessible name. Everything it shows is already in
  the numerals, which change on the same revision.
- It never renders a value that was not a previously committed ratio of *that same gauge*. It is not
  interpolated, not extrapolated, and not derived from narrative or from an action result.
- It resets to the current ratio on an epoch change, so a reconnect never draws a trail across two
  sessions' worth of state.

Under `prefers-reduced-motion` the existing token block collapses every transition to 1ms, so the
trailing bar has no visible life — which is correct: it is reinforcement, and its absence removes
nothing.

*Alternative rejected:* a numeric damage delta (`-42`) beside the numerals. That requires the client
to compute and present an authoritative-looking quantity that the server never sent, across a
revision boundary that may have carried several rounds of resolution.

### D5 — The low-HP state is one derived boolean on the store, bound to H1's stage hook

`view.vitals` is added to the committed store view: the three gauge ratios plus `lowHp`, computed from
`status.resources.hp` alone against a single display-only threshold of **25%**. `AppClient` passes it
to `AppShell`, which forwards it onto `HudFrame`'s already-declared `lowhp` prop; `HudFrame`'s
`[data-lowhp="true"]` rule then swaps in `--vignette-lowhp`. The same boolean is passed down the
island stack to `VitalsTrack`, which sets it on its own row and binds `elosern-hp-pulse` to the HP
fill there — a scoped style cannot select a stage ancestor, and the keyframe has been defined and
unreferenced since B1.

The threshold is a presentation constant, not a game rule: no server field, trait, or condition
expresses "low health" anywhere in `world/rules/`, and inventing one on the wire would be a read-model
change. It is pinned by a Vitest at 25% and it is never load-bearing — the numerals and the 「危險」
text marker say the same thing at every value, so a reader who cannot see the vignette loses nothing.

This is H2's only touch on `AppShell.vue` — one prop declaration and one attribute binding onto a
prop H1 built for exactly this purpose (H1 D7, H1 task 2.2). It is not a structural edit, so roadmap
§7's forced-serialize rule does not trigger.

*Alternative rejected:* computing `lowHp` inside `VitalsTrack` and emitting it upward. The stage root
is three components above the vital row; an emit chain through `StatusPanel` → `AppClient` → `AppShell`
would put presentation state on an event bus for no reason, and a second consumer (H3's participant
frame) would have to subscribe to a component instead of the store.

### D6 — Five shape glyphs for five severities; `▲`/`▽` carry the buff/debuff direction

The chip is icon-only at 34×34, so the severity must be legible without colour and without the label.
The mapping is:

| severity | glyph | note |
|---|---|---|
| `beneficial` | `▲` | the draft's `.cond .up` |
| `informational` | `◆` | unchanged from today |
| `warning` | `▽` | **changed** — today's `StatusPanel` renders `▲` here |
| `harmful` | `▼` | the draft's `.cond .dn`, filled |
| `critical` | `✕` | unchanged from today |

Today `beneficial` and `warning` share `▲` and are separated by colour plus border-style plus the
visible label. The chip form drops the visible label, so that collision becomes a colour-only
distinction and has to be fixed here. `▽` (hollow, down) versus `▼` (filled, down) is a fill-and-
direction distinction, not a hue one.

*Alternative rejected:* two glyphs per chip — a direction marker plus a severity marker. At 34×34 with
a duration badge already occupying the bottom-right corner there is no second corner that stays
legible, and the draft's own chip carries exactly one.

### D7 — The `+N` chip discloses in place; it does not wait for H4's drawer

Visible chips are capped at **6** (REDESIGN.md §1.1: *「溢出顯示 6–8 +「…」」*; the payload bound is 32,
and the roadmap's §8 margin analysis makes the island stack's height the binding constraint at
1280×720). The `+N` chip activates a **bounded, scrollable in-island disclosure** of the remaining
chips, collapsing on re-activation or Escape.

The roadmap's H4 row owns the full character-status drawer, and the draft's `+N` chip
(`data-full="status"`) opens it. H2 therefore hands off the *target*, not the *control*: when H4 lands
it re-points the chip's activation at the drawer and removes the disclosure.

The tempting alternative — rendering `+N` as an inert marker (or omitting it) until H4 exists — was
**rejected**: with 7+ conditions committed it would leave conditions 7..32 with no path to them at
all, and roadmap §5's first rule is that no wave may leave a required surface unreachable, with a
surface moved *within one change*, never split across two. An in-island disclosure costs one boolean
of component state, touches no file H4 owns, and keeps H2 shippable standing alone.

### D8 — The duration badge is verbatim payload, never a client-side countdown

`remaining_seconds` is **absent** from the payload when the server has none (`status.py:34-35`), so a
condition without a duration renders no badge — not `∞`, not `—`, not `0`. When present, the badge
shows that integer and the chip's accessible name reads 「剩 N 秒」. The client never decrements it on
a timer: the value is a game-time quantity resolved by the server at snapshot time, and a smooth local
countdown would drift away from the next committed revision and present a fabricated number in the
interval.

*Alternative rejected:* a depleting ring around the chip. It needs a *starting* duration to compute a
fraction, and the payload carries only the remainder.

### D9 — The minimap moves to `hud-right`, and its meta line states the axis convention only

The draft anchors `.mini` in `.hud-right` beneath `.topmeta`, and roadmap §4 makes the draft binding
where the roadmap is silent. Moving it there is also what makes the roadmap's §8 measurement true:
the 41px margin between the left stack's bottom (y=474) and the dock top (y=515) at 1280×720 was
measured against the draft, i.e. against a left stack of head + vitals + conditions *without* a
480px-tall map in it. Leaving the minimap in `hud-left` would consume that margin immediately.

H1's own geometry already assumes this: the `feed` anchor is sized `min(880px, calc(90vw - 524px))`,
and 524 is 262 (`hud-left`) + 230 (`hud-right`) + gutters. The right anchor is currently reserving
230px for nothing. Moving a component between two anchors H1 already established is a slot fill in
`AppClient.vue`, not a frame edit.

**The `.local-map` root class is load-bearing and stays.** H1 implemented the matrix's combat hide as
`.elosern-stage[data-elosern-mode="combat"] .local-map { display: none !important }` in `HudFrame.vue`,
and `AppShell.vue`'s `HIDDEN_BY_MODE` focus-rescue map selects the same literal for both `combat` and
`creation`. Re-chroming the component must therefore add island styling to that class rather than
rename it; renaming would silently un-hide the minimap in combat — the roadmap's single load-bearing
contextual rule — and silently break the focus rescue. This is exactly the "satisfy, do not
re-specify" instruction, and it is enforced here by a Vitest that asserts the rendered root still
carries `.local-map`.

The island's top-meta line carries the payload's `title` and, on the `grid` and `wilderness` layers
only, a renderer-axis orientation legend (`北↑`). That legend is true by construction: the wilderness
adapter's neighbour deltas put north at `+y` (`local_map.py:678-682`) and the renderer inverts `y` so
`+y` draws upward. It is a statement about the drawing, not about the world. On the `instance` and
`interior` layers the graph is explicitly coordinate-free, so the legend is omitted rather than
asserted. Nothing renders a bearing or a distance, because node `x`/`y` are declared
presentation geometry, not world coordinates.

*Alternative rejected:* deriving a bearing from the current node to the nearest landmark. Presentation
geometry cannot support it, and a plausible-looking degree figure is precisely the class of invented
data §5 forbids.

### D10 — The minimap island exposes no full-map control in this wave

The draft's `.mini` is `cursor:pointer` with `data-full="map"`. `MapOverlay.vue` exists, is
manifest-listed and is imported by nothing; H5 owns wiring it. H2 therefore ships the island with **no
full-map control** rather than a control that does nothing — a dead affordance is worse than an absent
one, and the island's per-node `explore.move` activation (the existing, unchanged contract) is
untouched, so the map remains as operable as it is today.

### D11 — The wallet lives on the head card, not on the top-meta pill

The draft puts the coin count in `.topmeta`. H1 explicitly declined it there and assigned it to this
wave (H1 D5). H2 places it on the head card's third meta line — the exact slot the draft fills with
the unbacked 拾荒者同盟 · 灰裔 line, so the card keeps its three-line proportion with a backed field in
place of an unbacked one.

The reason is ownership, not taste: `TopBar.vue` is H1's file (roadmap §7), and editing it for a
cosmetic relocation is a forced serialize behind H1 for zero functional gain. The head card is H2's,
it already renders the character's other counters, and grouping wallet with guild rank and merit
matches REDESIGN.md §1.1's own 計數器 row.

Four other components still print 錢包 — `CharacterPanel`, `ShopPanel`, `LoreDrawer`,
`InventoryPanel`. All four are H4's drawer content, so H2 makes the HUD the single *persistent*
wallet surface and records the duplicate removal as an H4 hand-off; it does not reach into H4's files
to do it early.

### D12 — `ArtPanel` stays in `hud-left` as a budgeted non-island, not a re-chromed one

H1 reduced `ArtPanel.vue` to the portrait catalog (the scene became `SceneBackdrop`) and left it in
`hud-left`, where it renders a boxed `美術展示` card above or below the island stack whenever the
`art` panel is available. Roadmap §7 assigns the file to H2, so H2 *may* re-chrome it — and does not.

H1's `webclient-art-panel` delta already routes the portrait catalog's presentation to H3's combat
participant frame, so any island chrome H2 gave it would be re-authored one wave later. What H2 owes
it instead is honesty about the height budget: the left stack's bounded-height and non-overlap
assertions are run with `ArtPanel` present and populated, not with an idealised three-island stack, so
D7's chip cap is validated against the layout that actually ships.

*Alternative rejected:* moving `ArtPanel` to `hud-right` to buy left-stack height. That puts a
portrait catalog under the minimap where the draft has nothing, for a surface H3 is about to relocate
anyway.

## Risks / Trade-offs

- **Risk: the duplicated rank-band table drifts from `world/rules/progression.py`.** → D3's Vitest
  pins all five boundaries and the 90 → 賢者 edge; the table is display-only and no gate, cost, or
  action depends on it, so a drift is a wrong caption, never a wrong mechanic. A future presenter
  change that adds a real `rank_title` field retires the duplicate in one line.
- **Risk: the island stack grows past its height budget and collides with the dock at 1280×720.** The
  roadmap measured a 41px margin. Conditions are bounded at 32 by the payload, and `ArtPanel` shares
  the anchor (D12). → D7 caps visible chips at 6 and puts the rest behind a bounded disclosure; D9
  moves the 480px map out of the stack entirely; and the browser acceptance asserts non-overlap
  between the left stack, the minimap island, the feed and the dock at **both** viewports, with the
  disclosure expanded and `ArtPanel` present. H1's `[data-anchor="hud-left"]` also carries
  `overflow-y: auto` as a backstop, but the island stack must fit without relying on it — a required
  surface that has to be scrolled to is the failure mode `webclient-contextual-hud`'s "Required
  surfaces never scroll out of view" scenario exists to prevent.
- **Risk: re-chroming `LocalMap` silently disarms the combat hide.** H1 pinned the matrix's one
  load-bearing rule to the literal `.local-map` class in two files. → D9 keeps the class and adds a
  Vitest asserting the island root still carries it; the existing browser assertion that the minimap
  is absent in combat re-runs unchanged as the end-to-end proof.
- **Risk: the icon-only chip hides the condition label from a sighted mouse user.** → The chip's
  accessible name carries label + duration + every modifier, and focusing or hovering the chip opens a
  text detail line inside the island. `test_browser_combat.py`'s existing assertion that the seeded
  poisoned buff shows `agility` and `-10%` is re-mapped onto that name/detail rather than deleted, so
  the modifier text stays proven present.
- **Risk: the trailing bar reads as a second, authoritative value.** → D4 makes it `aria-hidden`,
  decorative, restricted to previously committed ratios of its own gauge, and reset on epoch change;
  reduced motion removes it without removing information.
- **Risk: H2 needs a binding on `AppShell.vue`, which H1 owns.** → H1 is archived, so there is no
  concurrent author; D5 keeps the edit to one prop declaration plus one attribute binding onto
  `HudFrame`'s already-declared `lowhp` prop, with no structural change to the frame.
- **Risk: re-chroming `LocalMap.vue` disturbs the preserved lattice render model.** → The model lives
  in `web/static/webclient/js/elosern/local_map.js` behind `lib/local_map.js` and is not edited; H2
  changes the wrapper's chrome, its anchor and its meta line only. `node --test` over the preserved
  Node gate runs in this change's gates as the proof.
- **Risk: `.local-map__*` and `.status-gauge__*` class selectors are pinned in spec *text*, not just
  tests.** → The `webclient-local-map` and `webclient-component-showcase` `MODIFIED` deltas land in
  this same change, so no window exists where the spec and the DOM disagree — the same mechanism H1
  used for `.art-panel__scene-frame`.
- **Trade-off: `CharacterPanel` still renders seven rows the head card now also shows.** Accepted for
  one wave. Removing it would either delete information (the full eight-row trait table has no other
  home until H4's drawer) or force H2 into H4's files. The duplicate is visible, harmless, and
  explicitly scheduled.

## Migration Plan

No data migration: 0 released users, no persisted status or map state, no server change. The store
gains one derived slice computed from an existing committed panel, so a stale snapshot needs no
handling — the slice is recomputed from whatever `status` is committed.

Landing order inside the change is the tasks order: chrome first, then each island, then the minimap
move, then the manifest, then the browser re-map. The client is operable after every group — the
island stack renders the same information at every intermediate step, because D1 redistributes rows
rather than deleting them.

Rollback is `git revert`. No preserved identifier moves, no protocol or store contract changes shape
(the added `view.vitals` slice is additive), and the `local_map` render model and its Node gate are
untouched, so a revert cannot strand the transport, the bridge or the keyboard router.

## Open Questions

None blocking. Two deferred to their owning waves:

- Whether the `+N` chip's target becomes H4's character-status drawer or stays an in-island
  disclosure once the drawer exists — H4 decides, and D7 already states the expected hand-off.
- Whether the minimap island gains the draft's full-map affordance — H5, when `MapOverlay` is wired
  (D10).

One question this change answers rather than defers, recorded here because a future reader will ask
it: the low-HP threshold is 25% by client-side decision, not by any server rule, and it is
deliberately non-load-bearing (D5).
