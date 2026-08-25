## Context

H1 is landed and archived, so the container the dock needs already exists. `HudFrame.vue` gives the
dock a dedicated anchor — `left:0; right:0; bottom:46px; height:var(--dock-h); z-index:5` — and
`--dock-h` (`clamp(150px, 22vh, 184px)`) is finally consumed. What sits in that anchor is unchanged
from the migration: `ActionDock.vue` prints one static guidance line above a `DockMenu` whose grid is
`repeat(auto-fill, minmax(150px,1fr))`, with the suggestions section stacked underneath and, in a
submenu, a fixed 220px detail pane beside the grid. Every cell is the same `DockMenuItem`: centred
text, a `▶` focus caret, a `（無法使用）` suffix when disabled.

The navigation model beneath it is sound and must survive intact. `AppClient.vue:191-283` maps the
KeyboardRouter's *current frame* (`store.view.combatMenu.items`) into `DockMenu`'s item contract for
both exploration and combat; `onDockFocusChange` mirrors every pointer focus into
`store.focusItemByKey`, and `onDockActivate` funnels pointer activation into `store.focusConfirm(
"pointer")`. `store.view.dockDepth` is `router.depth()`. That is exactly the parity model
`webclient-pointer-activation` requires, and H3 changes none of it.

What the draft adds is a *presentation* hierarchy that the current chrome flattens. `index.html:
756-880` shows one dock with three visible levels at once: the tab bar (which root entry is open),
the crumb (how deep, and under what), and the pane (the current frame's rows in a shape chosen for
what they are — exits, targets, affordances, cards, skills, tokens). The temptation is to build that
with a component-local `activePane` string and a local crumb stack. That is precisely the failure
mode the roadmap warns about for Escape: a second navigation state drifts from `router.depth()` the
first time a panel replacement pops a frame, and the player's Escape then contradicts what the crumb
says. Everything visible in H3 is therefore derived from the router.

Two smaller facts shape the work. `combat_menu.js:346-375` builds the root with `gridCols: 5` for six
items, which is invisible today (the grid wraps) and wrong the moment the root is one row of tabs.
And `exploration_menu.js:192-222` builds move rows as `label: row.label` — the exit object's display
name, e.g. `north` — while `row.destination` (the canonical arrival node, re-derived server-side at
`web/webclient/presentation/exploration.py:429-486`) is carried in the payload and dropped on the
floor. The shipped move submenu therefore reads like a telnet exit list inside a graphical dock.

Constraints inherited from the roadmap: no server, protocol or read-model change; preserve the DOM
contract identifiers and re-map everything else to `data-testid`; every wave re-maps the browser
assertions it breaks in its own change; both 1440×900 and 1280×720 supported; the client stays
shippable at every landing; a surface with no backing read model is absent, never mocked.

## Goals / Non-Goals

**Goals**

- Replace the dock's chrome with the draft's floating panel, tab bar, breadcrumb and pane vocabulary,
  at parity of function and with every preserved identifier untouched.
- Keep exactly one navigation state: the router's frame stack drives the tabs, the crumb and the
  pane, and the back chevron is the Escape path.
- Make the combat surfaces the draft calls for real: the participant token frame and the skill
  master-detail, both from fields the panels actually carry.
- Fix the move submenu so it names where each exit goes.
- Render nothing the read models do not back, and say which fields each dropped element waits on.

**Non-Goals**

- The left island stack, the vitals, the condition chips and the minimap island (H2).
- The right-side drawers and the migration of SkillBook / Inventory / Shop / QuestBoard / LoreDrawer
  out of `hud-right` (H4) — H3 leaves the `Quests` / `Inventory` / `Character` root rows opening the
  same re-homed sub-dock frames they open today.
- The persistent command line, its quick-word chips, and the three unmounted overlays (H5).
- Any change to the *server's* menu content: no new action id, no new panel field, no reordering of
  server-authored lists.
- Dialogue mode. The draft has a `d-dialogue` dock, but the client has no dialogue `mode` value —
  scripted dialogue is an exploration target-affordance flow, and it stays one.

## Decisions

### D1 — The dock panel is the same `#action-dock` node, restyled in place

`ActionDock.vue` keeps rendering exactly one `<section id="action-dock" tabindex="0" :data-mode>` and
gains the draft's chrome around it: `max-width:1180px; margin:0 auto`, the upward gradient, the
`--line` top border, the `0 -14px 34px -24px #000` upward shadow, and a three-part internal layout
(fixed 38px bar / auto crumb / `flex:1; min-height:0; overflow-y:auto` pane).
`webclient-character-creation-ui` pins that exactly one `#action-dock` exists and survives a mode
change by switching `data-mode` rather than being remounted; a floating panel that is a *different*
element per mode would break that and the `browser_helpers.py` focus path with it.

*Alternative rejected:* a new `DockPanel.vue` wrapper owning the chrome with `ActionDock` nested
inside. It reads cleaner but puts a second element between the anchor and the focus target, and the
"exactly one `#action-dock`, persists across modes" assertion then depends on which of the two
elements Vue re-keys.

### D2 — The tab bar is the root frame's row container, not chrome above it

At depth 1 the root frame's items render as the tab bar and the tab bar carries the listbox role,
the single tab stop, `aria-activedescendant`, and `data-testid="dock-menu"`. At depth ≥ 2 the pane's
row container takes all four, and the tab bar degrades to inert ancestor chrome marking which root
entry is open. Exactly one row container is the listbox at any moment, which is what
`webclient-pointer-activation`'s composite-widget requirement demands, and `data-testid="dock-menu"`
therefore keeps meaning "the active row container" for the 22 existing browser assertions that use
it.

The draft's exploration dock opens with a pane already showing (`.pane[data-pane="move"]` is `on`).
H3 does not auto-open a frame: an auto-push would make Escape at depth 2 appear to do nothing,
because the client would immediately re-push. At depth 1 the pane instead renders the root's short
guidance line, which is where the legend the shipped dock prints statically now lives.

*Alternative rejected:* keeping a separate always-visible tab strip plus a root row grid in the pane.
That renders the root's items twice, gives the surface two tab stops, and forces a choice about which
copy `aria-activedescendant` names.

### D3 — The breadcrumb is derived from the router, via one additive accessor

`keyboard_router.js` gains `trail()`, a read-only accessor returning each stacked frame's
`menu.title` in order; the menu builders supply `title` (constants such as 移動 / 查看 / 互動 /
技能, and for a target frame the `target.display_name` those frames already carry at
`exploration_menu.js:412,438`). The store publishes `view.dockTrail` beside the existing
`view.dockDepth`, and `DockBreadcrumb.vue` renders `parent › current` with the back chevron bound to
the same `focusEscape()` the Escape key uses. The crumb is `hidden` at depth 1.

Adding a member to a frozen façade is additive — `webclient-browser-verification`'s freeze names the
existing members, and no behaviour of `pushMenu` / `popMenu` / `escape` changes. Deriving the trail
inside the Vue layer instead would require the component to observe every push and pop, which is the
second navigation state this decision exists to prevent.

*Alternative rejected:* reconstructing the trail from the parent frame's focused item label. The
router exposes `currentItem()` for the top frame only, so the component would have to cache the label
at push time — a cache that goes stale on a panel replacement exactly when the crumb matters most.

### D4 — A click on a non-current tab is expressed as router operations

Clicking the tab of a root entry that is not the open one, while the router is at depth ≥ 2, is
admitted as: pop frames until the root frame is current, `focusItemByKey(tabKey)`, then the same
`focusConfirm("pointer")` an enabled row click performs. It is never a direct pane swap. The pops are
the router's own `escape()` path, so nothing is torn down that Escape would not tear down, and the
confirm passes through the identical disabled / in-flight / awaiting-revision gates. A click on the
tab of the *already open* root entry is a no-op.

*Alternative rejected:* disabling non-current tabs at depth ≥ 2. It is honest but hostile — the draft
shows the tabs live, and a pointer user would have to press Escape twice before the tab they can see
becomes clickable.

### D5 — `建議` becomes the eighth exploration root row

The dock is 150–184px tall. The shipped layout stacks the suggestions section *under* the menu frame;
in the floating panel there is no vertical room for both, and the draft resolves it by making 建議 a
tab. Rather than inventing a non-router tab, H3 adds a root item keyed `suggestions` whose frame's
rows are the cards, the `✕ 清除建議` row and a back row. Consequences, all of them wanted: the cards
become router rows and are keyboard-reachable for the first time; the tab badge is the true
`cards.length`; the dismiss control goes through the same gate as every other action row; and the
root row is simply absent when `status` is `unavailable`, which is exactly today's "renders nothing at
all". `generating` renders one disabled row carrying `AI 正在構思建議…`, so the status is reachable
and readable without being submittable; `degraded` keeps its muted `AI 建議目前不可用` note and, at
zero cards, the `現在沒有什麼值得做的動作` empty-state line.

*Alternative rejected:* a non-router 建議 tab that discloses today's section unchanged. It would put
a second tab stop inside the composite widget and reintroduce the parallel-state problem D2 and D3
exist to avoid.

### D6 — A count badge exists only where the count is knowable and truthful

A tab carries a badge only when the number of rows its frame will contain is derivable from the
committed payload before the frame is opened: `互動` from `exploration.interact.length`, `建議` from
`suggestions.cards.length`, `技能` from the flattened `context_actions.skills` descriptor count.
`查看` and `移動` render no badge (the draft does not draw them either), and a zero count renders no
badge rather than a `0`. A badge is never a guess, and never a count of something the frame will not
actually list.

*Alternative rejected:* badging every tab for consistency. It looks tidier and lies the first time a
frame filters its rows.

### D7 — One shared row renderer with variants, never a component per pane

`webclient-pointer-activation` requires that "Rows SHALL be produced by one shared renderer so the
row markup, the focused marker, the disabled marker and its `（無法使用）` suffix, the accessible
disabled association, and the row identity attribute are defined in exactly one place." The pane
vocabulary is therefore a `variant` prop on `DockMenuItem` (`tab` / `outlet` / `nav` / `affordance` /
`card` / `skill` / `token` / `scale` / `confirm`), chosen by a pure classifier in `dock-panes.js`
from the frame's own shape — never five row components with five copies of the disabled contract.
`OptionCard` keeps ownership of a card's *content* and gains a row mode so the card can be the
`role="option"` element inside the pane's listbox, which keeps the narrative choice-point's plain-
button usage unchanged.

*Alternative rejected:* `ExitOutletRow.vue`, `TargetRow.vue`, `SkillRow.vue`, `TokenRow.vue`. Five
files is the natural Vue decomposition and it would fork the disabled-and-focusable contract five
ways within a release.

### D8 — Disabled cells stay focusable; the draft is wrong on this point

`docs/design/elosern-redesign/index.html` styles `.sk.disabled{opacity:.5}` and `.pick.disabled`
similarly — dimming only, with no statement that the row keeps focus. Three landed requirements say
otherwise: `webclient-desktop-shell` ("disabled cells dimmed but focusable for their explanation"),
`webclient-combat-menu` ("its descriptor remains focusable with `enabled: false`, one stable code,
and a Traditional Chinese explanation"), and REDESIGN.md §5's own accessibility checklist
(`disabled 行仍可 focus 讀 reason_message`). **The spec follows the existing requirement, not the
draft.** Every disabled row in every new pane keeps `role="option"`, `aria-disabled="true"`, the
`（無法使用）` suffix and its `aria-describedby` reason, and remains reachable by arrow keys and by
pointer focus; only submission is blocked. Roadmap §4 makes the draft binding *where this roadmap and
the specs are silent* — they are not silent here.

*Alternative rejected:* following the draft and moving the reason into a hover tooltip. It is the
draft's literal pixels and it makes a server-authored explanation unreachable by keyboard.

### D9 — Move rows render a direction glyph plus the destination's name

`.outlet` renders `<b>` glyph over destination name. The glyph comes from a fixed client-side table
mapping the canonical direction words the exit label carries (`north`/`n`/`北` …) to 北 / 南 / 東 /
西 / 東北 / 上 / 下 …; a label outside that table renders verbatim in the glyph slot (named doors and
wilderness gateways keep their own names). The destination *name* is resolved by joining
`exploration.move[].destination` — a node id — against the committed `local_map.nodes[].label`; when
the destination is not in the committed lattice (fog, or a bounded map that does not include it) the
row renders the glyph alone with no sub-line. Nothing is invented and no client-side geography is
performed: `explore.move` still submits `{exit_ref, current_node}` exactly as today.

*Alternative rejected:* printing the raw `destination` node id as the sub-line. It is backed, and it
is meaningless to a player — it would replace one identifier (`north`) with a worse one.

### D10 — A row's sub-line carries only backed fields

`.nrow .ns` in the draft prints 「攻/敏/防·魔階·生命」 for a look target. `exploration.look.entities[]`
carries exactly `identity`, `display_name`, `kind`; there is no stat line to print. Look rows
therefore render the `kind` as their sub-line, interact rows render their server-authored affordance
labels, and neither renders a portrait — exploration's `portrait_ref` is hard-forced `null` by the
presenter (`exploration.py:224-225,283-284`), so the row's leading glyph is a decorative icon chosen
from a fixed table keyed by the stable `kind`, not an image slot waiting for art.

*Alternative rejected:* rendering an empty stat line to preserve the draft's row height. A blank
「— / — / —」 reads as data that failed to load rather than data that does not exist.

### D11 — Skills gain a category frame, and a group frame only when the group is a real choice

`Skills` currently pushes one flat list of every owned active skill (`combat_menu.js:138-158`; the
`page` parameter is vestigial — `skillItems` ignores it and returns everything). In a 100px pane that
is unusable, and the draft's answer is the master-detail: `.skcat` chips, then a grouped list, then
`.skdetail`. H3 pushes a **category frame** (one row per `skills[]` category group, badged with its
flattened owned count), then — only when that category carries more than one sub-group — a **group
frame**, then the **skill frame**. A category with exactly one sub-group (every `martial_arts`-shaped
category, per `webclient-combat-menu`'s own "exactly one sub-group whose `group` and `label` are both
`null`" rule) skips the group frame entirely, so no level ever offers a single choice. The group's
label renders as the skill pane's heading, matching the draft's `.skgroup` line. Escape still pops
exactly one level at every step.

*Alternative rejected:* keeping the flat list and rendering categories as scroll headings with the
chips as a client-local filter. The chips would then be a second navigation state (D3's problem) and
the crumb could not name where the player is.

### D12 — The combat root's column count becomes its item count

`combat_menu.js:359` sets `gridCols: 5` for a six-item root. Today that is harmless because the grid
wraps; as a single-row tab bar it means ArrowRight from `逃跑` lands on a geometric second row. The
root menu's `gridCols` becomes `items.length` (so `1` in the `recovery` state, where the root is the
confirmed-Forfeit path alone), making ArrowLeft/ArrowRight traverse the visible tab order and
ArrowUp/ArrowDown a no-op — the same geometry the exploration root already declares
(`exploration_menu.js:452`, `gridCols: 7`).

*Alternative rejected:* leaving `gridCols: 5` and letting CSS lay the tabs out in one row anyway.
The rendered order and the focus geometry would disagree, which is the exact class of bug the
composite-widget contract exists to prevent.

### D13 — The participant frame is a combat-only `hud-left` island, and owns the portrait catalog there

REDESIGN.md §2 says the companion strip becomes the 參戰 party/foes frame in combat. The companion
strip itself has no read model and stays unbuilt (roadmap §2.4, and H2 drops it explicitly), but the
combat participant frame is fully backed: `participants[]` carries `token`, `display_name`, `team`,
`state`, `hp_current`, `hp_maximum` and a real `portrait_ref` that resolves through
`art.portrait_catalog` (`combat_panel.py:191-198`) — the one place in the client where a portrait per
entity is truthful. `ParticipantFrame.vue` mounts into H1's `hud-left` anchor, renders 我方 / 敵方
groups, and pairs every state with a text marker (`已逃離` / `倒地` / `已敗退`) rather than colour
alone. While it is mounted it is the sole presenter of the catalog, so `ArtPanel`'s standalone strip
is absent in combat — one payload, one presenter.

The frame is read-only display, not a row container: the *selectable* tokens live in the dock's
target pane as router rows, so the composite widget stays single.

*Alternative rejected:* rendering the frame inside the dock panel above the tab bar. The dock is
150–184px tall and the frame would eat most of it, and REDESIGN.md §2 places the participant queue
where the companion strip was — in the HUD, not the dock.

### D14 — No `戰鬥外` badge

The draft badges a skill row `戰鬥外` when it can be cast outside combat. `SkillDef` carries
`usable_out_of_combat` (`world/rules/action.py:273`), but **no presenter serializes it**: the v5 combat
skill descriptor is `{key, label, description, cost, target_spec, element, enabled, disabled_reason,
targets, shorthands, freeform_scales?}` and the character panel's rows are `{key, label}`. Rendering
the badge would require a presenter change, which roadmap §3 puts out of scope for all six waves. The
badge is therefore not built and not mocked, and is named in the deferred-surface assertion with the
field it waits on.

*Alternative rejected:* deriving it client-side from the skill's category. `movement` and `enhance`
skills are not uniformly out-of-combat castable; the derivation would be a guess presented as fact.

### D15 — The focused row is scrolled into view inside the bounded pane

Removing the (vestigial) pagination and putting long lists in a `~100px` scrolling pane means the
router can focus a row that is not visible. Every frame render scrolls the focused row into view with
`block:"nearest"`, so arrow navigation never focuses an off-screen row. This is the reach mechanism
that replaces pagination, and it applies to every pane, not only skills.

*Alternative rejected:* keeping `PAGE_SIZE = 6` pagination inside each frame. It adds a navigation
concept the draft does not have, and after D11 a group frame rarely exceeds a screen anyway.

### D16 — Creation mode renders the panel without the bar or the crumb

In creation mode the dock is the creation surface's host, and the creation form is not a router frame
(`webclient-pointer-activation` names it one of the three modal-form exceptions). The floating panel
therefore renders in creation mode with no tab bar, no badges and no crumb — the same node, the same
`data-mode="creation"`, the same chrome, an empty bar row. This keeps the "exactly one `#action-dock`,
persisting across mode changes" assertion literally true through the re-chrome.

*Alternative rejected:* hiding the whole panel in creation and letting `CreationOverlay` own the
bottom of the stage. It would remove `#action-dock` from the creation DOM, which the creation
capability's browser acceptance asserts against directly.

### D17 — Icons are a fixed table keyed by stable server keys, and are decorative

`dock-icons.js` maps stable keys — the root item keys (`move`, `look`, `interact`, `skills`, …), the
`kind` values of look entities, the canonical direction words, and the `team` values — to inline SVG
paths lifted from the draft. Every icon is `aria-hidden="true"` beside a real text label, so no
information is icon-only, and no icon is ever selected from server-authored free text (a display name
never picks a glyph). An unmapped key renders no icon rather than a fallback that implies a category.

*Alternative rejected:* an icon font or a sprite sheet. Both are extra fetched assets, and the
offline-load requirement forbids anything that is not bundled.

## Risks / Trade-offs

- **Risk: the dock's vertical budget is tight.** At 1280×720 `--dock-h` resolves to 158px; the bar is
  38px and the crumb ~28px, leaving ~92px of pane. A skill master-detail, a token row and a cast
  button do not fit in 92px side by side. → **Mitigation:** the pane is the only scrolling region, the
  master-detail is a 1fr/1fr split so the detail scrolls independently of the list, D15 keeps the
  focused row visible, and the browser acceptance asserts at **both** viewports that the cast/confirm
  control of the deepest combat frame is reachable without the pane clipping it.
- **Risk: making suggestions a router frame collides with "a suggestions-only update SHALL re-render
  the section without resetting the keyboard router".** `replaceMenu` resets focus to the first row.
  → **Mitigation:** a suggestions-only panel update replaces the frame's items through the same
  deterministic nearest-surviving-focus rule the combat menu already implements for panel
  replacement: a card whose `action_code` + `params` survive keeps focus, otherwise focus lands on the
  nearest surviving row. The requirement is re-expressed to state that rule instead of "no reset".
- **Risk: the category/group frames add keystrokes to every cast.** A single-target elemental cast
  goes 技能 → 分類 → 群組 → 技能 → 威力 → 目標 where it once went 技能 → 技能 → 威力 → 目標. →
  **Mitigation:** D11 collapses the group frame whenever it would offer one choice, `攻擊` still
  reaches `basic_attack` targets in one step, and the frames narrow a list that is otherwise up to
  192 rows long. Measured against the alternative — scrolling 192 rows in a 92px pane — the extra
  level is a net reduction in input.
- **Risk: D4's tab click performs several router pops in one gesture.** A mis-implementation could
  pop past the root or fire a submit mid-teardown. → **Mitigation:** the pop loop is bounded by
  `router.depth()` and stops at the root frame; the confirm is a separate, ordinary gated activation;
  and the "a stale row cannot push a second frame" scenario is extended to cover a tab click landing
  on a frame that a re-render has already replaced.
- **Risk: H2 and H3 both edit `AppClient.vue` and `component-manifest.json`.** → **Mitigation:**
  roadmap §7 makes the manifest a serial bottleneck — whichever wave archives first sets the count and
  the other rebases its extension. In `AppClient.vue` the two waves touch disjoint slots (H2 moves
  `LocalMap` to `#panel-right` and passes `lowHp`; H3 adds the participant frame to `#panel-left` and
  the dock's new props), so the file is a merge, not a forced serialize.
- **Risk: editing preserved `js/elosern/*` logic.** `keyboard_router.js`, `exploration_menu.js` and
  `combat_menu.js` are frozen-façade modules with a dependency-free Node gate. → **Mitigation:**
  `trail()` is purely additive; the menu `title` field is additive; the `suggestions` root row and the
  category/group frames are new menu builders, not edits to existing item shapes; and `node --test
  web/static/webclient/js/tests/*.test.js` is a landing gate, extended with cases for the new frames
  rather than relaxed.
- **Risk: 12 browser files touch the dock.** → **Mitigation:** `#action-dock`, `#combat-row-<i>`,
  `data-item-key` and `data-testid="dock-menu"` are preserved by construction, which keeps most of
  those assertions valid; the four re-mapped hooks (`exploration-detail`, `combat-detail`,
  `suggestions-section`, `action-dock-description`) are re-mapped in this change, and the
  `webclient-*` requirements that name them in prose are re-expressed in the same change, so no
  window exists where a spec and the DOM disagree.
- **Risk: the crumb and the tabs disagree after a panel replacement.** → **Mitigation:** both read
  `view.dockTrail` / `view.dockDepth` from the same commit, in the same render pass; there is no
  second source that could lag. A Vitest asserts that after a replacement the crumb's depth equals
  `router.depth()`.

## Migration Plan

No data migration: 0 released users, and the dock persists nothing. The persisted layout wrapper is
untouched by this change (`webclient-desktop-shell`'s versioned-persistence rule already resets an
unknown version). Landing order inside the change is the tasks order: the router/menu-model additions
land first behind their Node gate, then the chrome, then the panes, then the browser re-map — so the
client is operable at every commit and the parity contract is provable before any pixel moves.
Rollback is `git revert` of the change: no preserved identifier moved, no store contract was removed
(`view.dockTrail` is additive), and no server, presenter or protocol code was touched, so a revert
restores the shipped dock without touching anything else.

## Open Questions

None blocking. Three deferred to their owning wave:

- Whether the `Quests` / `Inventory` / `Character` tabs should open a drawer instead of a dock frame
  once the drawers exist — **H4**, which owns that migration; H3 leaves them opening the re-homed
  sub-dock frames unchanged.
- Whether the dock's freeform-dialogue row should focus the persistent command line rather than the
  borrowed drawer — **H5**, which replaces the drawer with the command line; H3 keeps the existing
  borrow-and-return contract byte-identical.
- Whether the `戰鬥外` badge (D14) and the look-row stat line (D10) become buildable — both wait on a
  presenter change that is out of scope for the whole roadmap; each is recorded in the deferred-
  surface assertion with the field it needs.

## Preserved-contract record (tasks 1.1 / 1.3 / 1.4)

### 1.1 — identifiers this change must not move
- `#action-dock`: its `tabindex="0"`, `data-mode`, the listbox composite role, and its documented
  focus-target status (the single tab stop at depth 1, the `dock-menu` hook moving to the active row
  container at depth ≥ 2).
- The `#combat-row-<i>` row-id pattern (and `#exploration-row-<i>` for the exploration root).
- `data-item-key` with the `action-` / `target-` prefixes (the preserved item-key contract).
- The bare G2 root keys (`move`, `look`, `interact`, `character`, `quests`, `inventory`, `wait`) and
  the combat root keys (`attack`, `skills`, `items`, `defend`, `flee`, `forfeit`).
- `data-testid="dock-menu"` — from this change forward it marks whichever container is the **active**
  row container (the tab bar at depth 1, the pane at depth ≥ 2).

### 1.3 — the 12 affected browser files (re-mapped in group 8)
`web/tests/browser/browser_helpers.py`, `test_browser_art.py`, `test_browser_choicepoints.py`,
`test_browser_combat.py`, `test_browser_creation.py`, `test_browser_exploration.py`,
`test_browser_input_narrative.py`, `test_browser_layout.py`, `test_browser_options_surface.py`,
`test_browser_pointer.py`, `test_browser_services.py`, `test_browser_shell.py`.

### 1.4 — hooks re-mapped to `data-testid` (for H6's audit re-freeze)
`exploration-detail`, `combat-detail`, `suggestions-section`, `action-dock-guidance`, and
`action-dock-description`. The Node contract gate reads `action-dock-guidance` and
`action-dock-description` from `ActionDock.vue` (carried there even when the tab bar is absent).
