## MODIFIED Requirements

### Requirement: The message window presents the current response one page at a time in the band's message region
The narrative SHALL render as a message window that fills the bottom band's message region — the left
two thirds of the band, or the whole band in dialogue mode, at the band's fixed height — drawn with the
reference's caption panel
treatment: charcoal panel fill, a hairline border, shared radius and restrained shadow. The window
SHALL never grow into the stage and SHALL never change size with its content. In every mode, dialogue
included, the window SHALL present exactly one page of the current response at a time, paged as
`webclient-input-narrative` defines and revealed as its typing requirement defines — or, while the
current response carries a combat round the client presents, as that round's beat pages followed by the
response's remaining lines, as `webclient-combat-menu` "A combat round plays beat by beat" defines — and
SHALL NOT present earlier responses: they remain readable in the full-log surface. The one exception is the clear
transition: when a new response replaces the previous one, the previous page MAY remain only as an
opaque layer over the new page that fades out within the clear duration of the client's motion level
(at most 150ms, and none at `off`), carries no focusable element, and is outside the accessibility
tree and pointer hit-testing from the moment the new response starts. Page text SHALL be set in the
serif reading face at 28px at the 1920x1080 reference size and the default prose scale, SHALL scale
with the viewport height and with the client's prose scale, and SHALL hold at most 42 CJK characters
per line in every mode, including the whole-band width of dialogue mode.

The window's lower edge SHALL keep a control strip in which no page text renders. The strip SHALL
hold a page marker and, at its right end, a labelled `日誌` control beside the command-line toggle.
The page marker SHALL render only while the page on screen is fully shown, and SHALL be absent while
the page is typing and while a combat round plays by itself. When rendered, it SHALL read `▼` while the current response has further pages and
`■` on its last page. It SHALL be decorative (hidden from assistive technology), and it SHALL blink
only through the client's motion tokens, so reduced motion stops the blink. An oversize page SHALL
scroll inside the window's text area; it SHALL never be truncated and SHALL never grow the window.

The `日誌` control SHALL open the full-log surface in one action. Scrolling up over a page that has
nothing left to scroll up SHALL also open it. The full-log surface's content, markup renderer, focus
trap, Escape close, focus restore to the opening control, and opening at its latest line are
unchanged. The window SHALL render no unread indicator and no jump-to-latest control, and no head row
other than the dialogue name plate. In creation mode the window, its marker, and the `日誌` control are
hidden with the message region.

While the committed mode is `dialogue` and the committed `dialogue` panel is available, the window SHALL
carry a name plate above its text area, naming the host with the panel's `display_name` plus
` ‧ 羈絆 <stage>` only when `bond_stage` is non-null; the window's text area below the plate SHALL
present the current response's pages — the session line as the narrative delivered it, paged and typed
like any response, with no separate reply box, no rows, no avatar, and no text removed or rewritten
from the narrative lines. The window SHALL carry no choice, free-dialogue, or exit row: those are the
dialogue choice list's. While mode is `dialogue` but the panel is unavailable (the transient window
between a clear seam and its commit), the window SHALL render no name plate. The window SHALL make known
to the shell, from its own reader state and never from narrative prose, whether the current response's
last page is on screen, fully shown, with no pending action mark — the moment the dialogue choice list
waits for.

#### Scenario: The window keeps the message region's box
- **WHEN** the current response holds more text than one page and new lines keep arriving
- **THEN** the window keeps the message region's box — the band's height and two thirds of its
  width, or the whole band in dialogue mode — and never expands into the stage

#### Scenario: One page of the current response is shown
- **WHEN** the log holds three responses and the latest one fills two pages
- **THEN** the window shows only the first page of the latest response, and once the clear transition
  has finished no line of the two earlier responses is rendered in the window

#### Scenario: The page measure is bounded at the reference size
- **WHEN** the stage renders at 1920x1080 with the default prose scale and a long prose response, in exploration mode and in dialogue mode with the panel transiently unavailable
- **THEN** the page text's computed font size is 28px (±0.5px) and no rendered text line holds more
  than 42 CJK characters in either mode

#### Scenario: The marker names more pages and the last page
- **WHEN** the current response has two pages, page 1 types to its end, and the player advances
  once and page 2 types to its end
- **THEN** no marker renders while either page is typing, the marker reads `▼` once page 1 is fully
  shown and `■` once page 2 is fully shown, and it is absent from the accessibility tree

#### Scenario: The log control opens the complete log in one action
- **WHEN** the player activates the `日誌` control and then presses Escape
- **THEN** the full-log surface opens at its latest line showing every retained line, including
  input lines and every page of earlier responses, rendered through the same markup renderer, and
  Escape closes it with focus returned to the `日誌` control

#### Scenario: Scrolling up opens the complete log
- **WHEN** the player scrolls up with the wheel over a page that is not scrollable
- **THEN** the full-log surface opens

#### Scenario: An oversize page scrolls inside the window
- **WHEN** the current response's page is a box-drawing map taller than the text area
- **THEN** the map scrolls inside the text area, every row is reachable, and the window's box is
  unchanged

#### Scenario: No unread indicator is rendered
- **WHEN** the window renders in exploration, combat, or dialogue mode while lines arrive
- **THEN** no unread count, unread live region, or jump-to-latest control exists in the window

#### Scenario: The dialogue line is paged under the name plate
- **WHEN** mode `dialogue` commits with host `灰婆婆`, `bond_stage` `親睦`, and a greeting long enough for two pages at 1920x1080
- **THEN** the window spans the whole band, shows the name plate `灰婆婆 ‧ 羈絆 親睦`, types page 1 with no marker until it is fully shown, shows `▼`, advances on Enter on the page surface to page 2, and shows `■` once page 2 is fully shown, with no choice row inside the window at any point

#### Scenario: An unbonded host's plate names only the host
- **WHEN** mode `dialogue` commits with `bond_stage` `null`
- **THEN** the name plate reads the host's `display_name` alone and carries no `羈絆` text

#### Scenario: A transiently unavailable panel shows no plate
- **WHEN** mode is `dialogue` but the committed panel is the unavailable form
- **THEN** no name plate renders and the window shows the current response's pages with their page marker

### Requirement: The dock's shortcut legend names only real keyboard behaviour and renders as one visible instance
The action dock SHALL carry one shortcut-legend strip at the bottom of its content column, below the
scrolling region, in exploration and combat mode (never in creation mode, and never visibly in
dialogue mode, where the strip is hidden with the collapsed command region), matching
`docs/design/elosern-redesign/index.html`'s dock hint in wording and structure: the text
`數字鍵 1–9 ‧ ` followed by an `<kbd>` element naming `Enter`
and the verb `執行`, the separator `‧`, and an `<kbd>` element naming `Esc` and the verb `返回`.
The legend renders
with the reference's `<kbd>` treatment (monospace face, `--ink-780` ground, 2px bottom border).
The legend SHALL render exactly once as visible content and SHALL be the only element carrying the
legend's test hook; no root command list or pane SHALL carry a second copy. The dock SHALL NOT carry a dialogue-mode
legend variant.

The legend SHALL NOT name a key, gesture, or affordance this client does not implement or that no
longer behaves as named, and it SHALL NOT advertise implemented affordances the reference's legend
does not name. When a named affordance's behaviour changes (for example, a control that used to
open a surface and now only moves focus into an always-present one), the legend's wording SHALL be
updated in the same change that alters the behaviour.

The digits the legend names SHALL be bound: while the dock owns keyboard focus (the key target is
not editable), pressing
`1`–`9` moves the current dock frame's focus onto its first nine entries (1-indexed, rendered order —
for the scene overview, its first nine chips in reading order: exits, then people, then objects, then
the footer; a frame's `back` row takes the slot of its rendered position) and activates the entry through the
same confirm path `Enter` uses — a disabled entry shows its explanation and submits nothing, an
in-flight entry stays locked, and a held repeat is suppressed.
The slots address the frame's rendered entries, disabled ones included. In dialogue mode neither the
dock's entries nor the keyboard router claim any digit: the digits `1`–`N` belong to the dialogue choice
list while it holds focus, which handles them itself as "Dialogue choices appear centred over the stage
after the line is fully read" defines.
A digit whose entry does not exist (a frame with fewer rendered entries, dialogue mode, or
the pre-session empty stack) is not claimed and falls
through to the text / command-history path.

#### Scenario: The legend renders once
- **WHEN** the dock renders in exploration or combat mode, at the overview, in a child frame, or at the combat root, and later the mode changes to dialogue
- **THEN** exactly one element carries the shortcut-legend text and test hook, it is the dock's
  legend strip, no root command list or pane renders a duplicate copy, and in dialogue mode the strip is hidden
  with the command region and no other element shows a legend

#### Scenario: The legend matches the reference wording and kbd structure
- **WHEN** the dock renders its legend strip in exploration or combat mode
- **THEN** the legend reads `數字鍵 1–9 ‧ Enter 執行 ‧ Esc 返回` with `Enter` and `Esc` rendered as
  styled `<kbd>` elements and no other key named

#### Scenario: A digit picks its row
- **WHEN** the scene overview holds three exit chips, two person chips, and one object chip, and the
  player presses `5`, and later `6`, from a non-editable focus
- **THEN** the `5` press focuses the second person chip and opens its popover exactly as `Enter`
  would, once, and after Escape the `6` press focuses the object chip and submits its `explore.look`
  once

#### Scenario: A digit beyond the frame's rows is unclaimed
- **WHEN** the current dock frame has fewer rendered entries than the pressed digit and the command
  field is not focused
- **THEN** the digit is not claimed, the frame's focus is unchanged, and nothing submits

#### Scenario: Digits address the caption's picks while the dialogue variant presents
- **WHEN** the dialogue choice list shows four picks with focus on the list, the command region is
  collapsed, and the player presses `4` and `5`
- **THEN** the `4` press activates pick four through the same dispatch entry, the `5` press is handled
  by neither the list nor the keyboard router and falls through, and the hidden dock's focus and frame
  are unchanged

### Requirement: Reference surfaces render in a bounded workspace drawer with one modal contract
The client's reference surfaces SHALL render in a wide workspace 12px below the top navigation's
bottom edge, 16px inside each side of the viewport, and one command-line row height plus 12px above the
viewport bottom, so the workspace covers the stage, the bottom band, and the command-line row whether or
not that row is expanded, and only the band's lowest control strip stays exposed beneath it. A fine
border and a fully opaque charcoal ink panel SHALL distinguish the workspace from the stage. The existing
modal drawer lifecycle and shared motion tokens SHALL be retained over a dimmed scrim covering the whole
viewport behind the drawer. Between its header and optional footer, a decorative art column MAY
accompany the scrolling content body; only the content body scrolls. The head SHALL be the shared
reference-surface header: the title in the serif heading face at the shared workspace scale with slight
tracking, and the subtitle as the small muted line beside it. Every reference drawer SHALL declare one
leading head icon (a decorative, `aria-hidden` glyph from the shared glyph registry rendered before its
title). The drawer's close control SHALL carry an accessible name (e.g. an `aria-label`) but MAY be
rendered icon-only, with no visible text node — "labelled" in this requirement means an accessible name,
not necessarily visible text.

At most one drawer SHALL be open at any time; opening a second SHALL close the first. While a drawer
is open it SHALL trap keyboard focus, so no surface behind it is reachable by sequential navigation.
It SHALL close on Escape, on activation of its labelled close control, and on activation of the scrim,
and every one of those paths SHALL restore focus to the control that opened it. An open drawer SHALL
register itself as an open surface so the stage recession this capability already requires applies
without a second mechanism.

The skill-book drawer specifically SHALL carry, whenever the `character` panel is available, a
subtitle stating its owner's active and passive skill counts (`主動 {n} ‧ 被動 {m}`, computed from that
same payload `SkillBook` renders) in the drawer head; when the panel is unavailable the subtitle is
empty, matching the drawer's existing degrade-without-inventing-data contract. The skill-book drawer
SHALL carry a footer stating the client's own cast-command syntax
(`施放入口：cast <技法>[@威力]=<代號>`) as static client-local presentation copy — not a value the OOB
protocol carries, so its presence does not depend on any panel's availability — whenever the drawer
presents the skill book itself; while the declared-practice sub-screen replaces the book body, that
footer is absent and the head title reads 修煉, because the cast syntax belongs to the book view the
sub-screen replaced.

#### Scenario: A drawer opens over the stage with a scrim
- **WHEN** the player opens a reference drawer
- **THEN** the workspace is bounded below the navigation and above the band's lowest control strip, covering the command-line row, as an opaque panel over a dimmed scrim, its content body is the only scrolling region, and the stage behind it carries the recession mark

#### Scenario: The head carries the reference display type scale
- **WHEN** a reference drawer renders its head
- **THEN** the title renders in the serif heading face with slight tracking and the subtitle renders as the small muted line beside it

#### Scenario: Only one drawer is open at a time
- **WHEN** a drawer is open and the player opens a different one
- **THEN** the first drawer closes as the second opens, and exactly one drawer and one scrim are present

#### Scenario: Focus is trapped and returned
- **WHEN** a drawer is open and the player cycles focus forward past its last control and backward past its first
- **THEN** focus stays inside the drawer in both directions, and on closing by Escape, by the close control, or by the scrim, focus returns to the control that opened it

#### Scenario: Closing the last drawer clears the recession
- **WHEN** the open drawer closes and no overlay remains open
- **THEN** the scrim is removed and the stage's recession mark is cleared

#### Scenario: Reduced motion keeps the state and drops the transition
- **WHEN** `prefers-reduced-motion` is set and a drawer opens
- **THEN** the drawer is open and correctly placed with no slide transition played

#### Scenario: The close control is icon-only but keeps its accessible name
- **WHEN** a reference drawer's close control renders
- **THEN** it carries no visible text node, renders a decorative close glyph, and exposes the same accessible name (e.g. `aria-label="關閉"`) an assistive technology would have read from the previous visible text

#### Scenario: The skill-book drawer states its skill counts and cast syntax
- **WHEN** the skill-book drawer opens with the `character` panel available
- **THEN** its head carries a leading skill glyph and a `主動 {n} ‧ 被動 {m}` subtitle matching the panel's active/passive row counts, its title renders exactly once (not duplicated inside the body), and its footer states the client's `/cast` syntax as static copy

### Requirement: Reference drawers present no router frame and never host a dock row region
No reference drawer SHALL present a keyboard router frame. Opening any reference drawer — including the 背包 ‧ 裝備 drawer from the top navigation's 背包 entry, the 商店 drawer from a merchant's `navigate` affordance row, and the 任務 drawer from the top navigation's 任務 entry or from a guild clerk's `navigate` affordance row — SHALL push no frame, switch no sub-dock, and record no drawer-hosted service surface; an opener that is itself a top-navigation entry MAY first return the dock to its root frame exactly as every top-navigation entry does, and the drawer open SHALL add nothing to the stack after that. The client SHALL NOT maintain a second frame stack, a second focus model, or a second set of menu keys for a drawer. No reference drawer body SHALL render the dock's row renderer (`dock-menu`) or detail pane (`dock-detail`) in any state. Closing a reference drawer — by Escape, its close control, or the scrim — SHALL leave the router alone, popping no menu level, and SHALL restore focus to the control that opened it. Committed rows inside a reference drawer SHALL remain reachable by keyboard without a hosted router frame.

A drawer SHALL be openable only while its backing payload is present. When the committed mode changes so that a drawer's payload is no longer available, when the presentation epoch resets, or when the transport is lost, every open drawer SHALL close and every local selection, quantity and confirmation state inside it SHALL be discarded.

#### Scenario: Opening the quest drawer from the guild clerk pushes no frame
- **WHEN** the player activates the guild clerk's `navigate` affordance row inside an open target frame
- **THEN** the 任務 drawer opens with the quest book and the guild counter, the router's current frame is still that target frame, no frame was pushed, no sub-dock switch occurred, and the breadcrumb is unchanged

#### Scenario: Opening the bag or the shop pushes no frame
- **WHEN** the player activates the top navigation's 背包 entry at the exploration root, or a merchant's shop `navigate` affordance row inside an open target frame
- **THEN** the matching drawer opens, the router's current frame is the frame that was current before the open, no frame was pushed, no sub-dock switch occurred, and the breadcrumb is unchanged

#### Scenario: Keyboard reachability does not depend on a hosted list
- **WHEN** a keyboard-only player moves through the open bag drawer, or moves into a shop stock row, types a quantity within its advertised bounds, and activates its buy control
- **THEN** every committed inventory row is reachable through the focusable item tiles with the shared inspector, the shop row becomes the selected row carrying the quantity hooks and exactly one `shop.buy` is emitted with that row's `item_key` and quantity, and no parallel navigation list of those rows exists to traverse

#### Scenario: Opening the quest drawer from the top navigation pushes no frame
- **WHEN** the player activates the top navigation's 任務 entry at any dock depth
- **THEN** the dock returns to its root frame as for every top-navigation entry, the 任務 drawer opens, and the router's depth is 1 with no frame pushed by the open

#### Scenario: No drawer renders the dock's row renderer
- **WHEN** any reference drawer is open, including the quest drawer while a guild counter control or a quest-book row holds focus
- **THEN** no `dock-menu` row region and no `dock-detail` pane exists inside the drawer, and the dock itself renders exactly the router's current frame

#### Scenario: Closing a drawer pops nothing and returns focus
- **WHEN** the open 任務 drawer closes by Escape, by its close control, or by the scrim
- **THEN** the router's frame stack is exactly what it was right after the open, no action is dispatched, and focus returns to the control that opened it

#### Scenario: A mode change closes the drawers it invalidates
- **WHEN** the committed mode changes from exploration to combat while a services-backed drawer is open
- **THEN** that drawer closes, its local selection, quantity and confirmation state is discarded, and no stale service surface remains reachable

### Requirement: The bag renders the bounded inventory rows without inventing a total or a rarity
The bag workspace SHALL use shared chrome for the `背包 ‧ 裝備` title, local inventory SVG icon, close control, and wallet subtitle formatted as integer copper from the committed available character panel. The wallet SHALL additionally render exactly once in the body as the single row of a `金錢` section. The available body SHALL present an `裝備` section carrying the read-only equipment doll, an `物品` section whose heading carries the shipped listing size above the bounded responsive grid, a `金錢` section carrying the same committed wallet, and a reserved non-interactive detail column driven by the existing hover/focus selection. The listing SHALL remain bounded by the server row ceiling and state that ceiling in words when reached; no shipped count SHALL claim to be the player's untruncated holdings.

Each registered row's non-null `presentation` SHALL select one local inline SVG by `icon_key`, an item-kind label, rarity label, bounded summary, and non-colour-only rarity treatment. Its tile SHALL show committed held count and a non-colour equipped marker. A null presentation SHALL render only the neutral unknown-item SVG and visible unknown marker; the browser SHALL NOT derive type, icon, rarity, summary, or mechanics from item key or display name. The grid SHALL use native keyboard-focusable buttons and one non-focusable inspector shared by pointer hover and keyboard focus; both inspection paths SHALL expose identical committed name, kind, rarity, count, equipped state, and summary, and the focused tile SHALL reference the stable inspector through `aria-describedby`.

Each tile SHALL follow only its committed nullable action descriptor. Inspect-only and unknown tiles SHALL dispatch nothing. Disabled tiles SHALL remain keyboard reachable, expose `aria-disabled`, and show the committed reason on activation without dispatch. Enabled usable items SHALL open a labelled, focus-trapped inventory-use confirmation; enabled equipment SHALL dispatch its toggle immediately. Selection and dialog state SHALL remain client-local and reset on panel replacement, drawer close, mode/epoch change, or transport loss. The bag SHALL NOT render or infer numeric item statistics, recovery amounts, conditions, effects, consumable flags, slots, set bonuses, comparisons, sorting, filtering, search, drag, or drop behavior, and SHALL render no static sort/filter/search pill.

The drawer SHALL remain available from its combat affordance when services v3 inventory is available. When services commits its unavailable form or inventory is absent, the bag SHALL render only the registered reason and fabricate no wallet, equipment, row, count, action, or dialog. When services inventory is available but character is unavailable, the grid SHALL remain available, the doll SHALL render its registered unavailable state, and no wallet subtitle, wallet body value, or zero balance SHALL be invented. All inspector, confirmation, and warning transitions SHALL use existing motion tokens so reduced motion makes them effectively instant.

#### Scenario: A registered actionable row preserves truthful inspection
- **WHEN** a committed registered inventory row carries presentation and an enabled action descriptor
- **THEN** its tile renders committed visual identity and inspector data, and deliberate activation follows the descriptor without deriving mechanics locally

#### Scenario: An unknown row has a neutral truthful fallback
- **WHEN** a committed inventory row has `presentation` null and `action` null
- **THEN** its tile shows the neutral unknown state and real quantity with no inferred metadata or mutation

#### Scenario: Keyboard inspection and activation match pointer behavior
- **WHEN** keyboard and pointer users inspect and activate the same tile
- **THEN** both receive identical committed inspector data and action behavior, and the focused tile references the inspector through `aria-describedby`

#### Scenario: Eligible item use opens confirmation
- **WHEN** the player activates an enabled usable-item tile
- **THEN** the labelled confirmation dialog opens without dispatch and confirm is the only path that submits use

#### Scenario: Equipment activates directly
- **WHEN** the player activates an enabled equipment tile
- **THEN** one equipment-toggle intent is emitted without opening a confirmation

#### Scenario: Disabled item presents its reason
- **WHEN** the player activates a full-HP potion or an unequipped accessory at the five-slot cap
- **THEN** the committed reason is presented and no request is dispatched

#### Scenario: Combat bag keeps personal items reachable
- **WHEN** mode changes to active combat and services v3 commits canonical inventory
- **THEN** the combat root's client-local `背包` row opens the frameless bag without dispatch or a router frame, and personal item tiles remain reachable while guild and shop surfaces are absent

#### Scenario: The bag body retains its authoritative sections in a wide workspace
- **WHEN** the bag is available with inventory, character equipment, and wallet
- **THEN** it renders equipment, items, and money from their existing sources, with a reserved
  non-interactive item-detail column, and invents no inventory total or additional holdings

#### Scenario: Wallet renders only in the bag head and money row
- **WHEN** the bag renders with available character and inventory panels
- **THEN** the same integer copper wallet appears in the head subtitle and the single `金錢` row and nowhere else in the drawer

#### Scenario: Ceiling is stated without inventing a total
- **WHEN** the shipped inventory reaches its maximum row count
- **THEN** the bag states the listing ceiling and never labels that count as complete holdings

#### Scenario: Unavailable services fabricates nothing
- **WHEN** the services panel commits its unavailable form
- **THEN** the bag renders only the registered reason with no rows, wallet, equipment, count, heading, action, or dialog

#### Scenario: Character unavailability preserves inventory without fabricating equipment
- **WHEN** services inventory is available but the character panel is unavailable
- **THEN** the bag renders held tiles, the equipment registered unavailable reason, and no wallet subtitle, wallet value, or zero balance

#### Scenario: Reduced motion preserves action information
- **WHEN** reduced motion is active and focus, inspector, confirmation, or warning state changes
- **THEN** transitions are effectively instant while labels, reasons, focus, and committed item information remain available

### Requirement: The equipment doll renders only server-authored slots and drops nothing
The equipment presentation SHALL be built from the committed `character` panel's equipment rows, each of which carries a slot, an item key and a display name and nothing more. The section SHALL be introduced by the bag's small tracked section heading `裝備` carrying the right-aligned tag `真值 ‧ 偽裝不影響`, and SHALL NOT be introduced by a standalone `裝備人偶` title. The doll SHALL lay out as the redesign's equipment row: a compact two-column square slot grid beside a 裝備描述 column that lists the committed rows grouped under their slot labels. The doll SHALL render the server's three singleton slots and one accessory summary as four named positions in the square grid. The main-hand, armor, and accessory-summary positions SHALL each render a fixed local SVG selected by its server-authored slot role; the off-hand position SHALL be the iconless position. The doll SHALL NOT select an item icon from an item key or display name. A singleton slot with no row SHALL render a visible named empty state with a dashed outline. An occupied singleton slot SHALL render its visible slot label in the grid and its committed display name in the 裝備描述 column; when the committed rows carry more than one row for a recognised singleton slot, the square position consumes only the first row and every further row for that slot SHALL render as a labelled overflow row, so no committed row is lost. The accessory summary SHALL render its visible label and committed item count, while every repeatable accessory row SHALL render in the 裝備描述 column's accessory group. Any slot key outside the recognised set SHALL render as a labelled fallback row rather than being discarded, so no row the payload sends is lost. When the committed rows carry no equipment at all the doll SHALL render only its visible empty statement.

The doll SHALL NOT render an item statistic, attack or defence value, rarity, item icon, summary, or comparison against another item: the equipment rows carry none of those. Equipment SHALL be presented as true values that a disguise does not affect, and the section tag SHALL state exactly that.

#### Scenario: The equipment section is titled 裝備 with the true-value tag
- **WHEN** the bag renders its equipment section
- **THEN** the section heading reads `裝備` with the tag `真值 ‧ 偽裝不影響` in the bag's shared section-heading style, and the string `裝備人偶` appears nowhere in the drawer

#### Scenario: An empty slot is shown as empty
- **WHEN** the committed equipment rows carry no row for a singleton slot
- **THEN** that slot renders its visible name with a dashed explicit empty state, and no item is invented for it

#### Scenario: An occupied singleton slot is identified without guessing its item type
- **WHEN** the committed equipment rows carry one primary-hand item
- **THEN** the square grid renders only that position's fixed slot SVG and visible slot name, the 裝備描述 column renders its committed display name under the `主手` label, and nothing is inferred about the item's icon, rarity, statistic, or comparison

#### Scenario: An occupied off-hand position renders without an item icon
- **WHEN** the committed equipment rows carry a `weapon_off` item
- **THEN** the off-hand position stays the iconless position of the binding design, rendering its visible slot label in the grid and its committed display name in the 裝備描述 column with no item icon

#### Scenario: The description column lists only committed rows
- **WHEN** the committed equipment rows carry equipment
- **THEN** the 裝備描述 column shows one labelled entry per primary row (slot label plus committed display name) — the first committed row of each recognised singleton slot and, in the accessory group, every accessory row — grouped by slot label, while duplicate and unrecognised-slot rows are rendered only by the doll's labelled fallback sections so each committed row appears exactly once, and with no committed row the column shows only the visible empty statement

#### Scenario: Duplicate singleton rows are rendered, not discarded
- **WHEN** the committed equipment rows carry more than one row for a recognised singleton slot
- **THEN** the square position shows the first row for that slot and every additional row renders as a labelled overflow row, so the duplicate committed row is never dropped

#### Scenario: Repeated accessories all render
- **WHEN** the committed equipment rows carry more than one accessory row
- **THEN** the accessory summary states the committed count and every accessory row renders in the description column's accessory group, and none is dropped for want of a fixed position

#### Scenario: An unrecognised slot is rendered, not discarded
- **WHEN** an equipment row carries a slot key outside the recognised set
- **THEN** the row renders with its slot key as its label and its display name, and the doll drops no row

#### Scenario: No statistics are invented for an equipped item
- **WHEN** an equipped item renders in the doll
- **THEN** it shows its display name and its slot only, with no attack, defence, rarity, item icon, summary, or comparison value

### Requirement: The character-status drawer degrades section by section and never substitutes a disguise
The character-status drawer SHALL present the committed `status` panel's resources and its complete condition roster in every mode, because that panel is available in every mode; each condition SHALL pair a non-colour severity glyph with its label and every numeric or derived-modifier value the payload provides. It SHALL present the committed `character` panel's true traits, guild standing, and persona background, and SHALL mark each of those sections with the registry-owned reason when the `character` panel is unavailable — as it is outside exploration mode — rather than hiding the drawer or inventing a value. Equipment and wallet presentation belong exclusively to the inventory drawer and SHALL NOT render in character status.

Where a disguise is active the drawer SHALL render the displayed values beside the true trait rows they describe, distinctly labelled, together with the statement that a disguise affects display, registration and identification only and that combat always resolves against true values. A displayed value SHALL NEVER replace a true trait row.

The character-status drawer SHALL preserve the 親密狀態 disclosure section added by the archived intimate-status change: when the committed `character` panel's `intimate` field is present the drawer renders its collapsed-by-default disclosure widget immediately after the 偽裝 (disguise) section and before the 背景 (persona) section, and no change SHALL remove it, reorder it, or alter its disclosure widget, content, or collapsed default; like the persona area it spans the full row of the section grid. When `intimate` is `null` or the `character` panel is unavailable, the section is absent from the DOM, exactly as the merged main spec requires. This change removes only the equipment and wallet sections.

Each of the drawer's sections (vitals, traits, conditions, guild counters, disguise, intimate status, persona) SHALL carry a labelled, small-caps section heading naming what it presents, using the same heading treatment the HUD's other islands use. The vitals, traits, and guild-counter sections SHALL render each value as its own bordered card tile in an auto-fill grid of equal-width tracks rather than a plain text row, each tile only as tall as its own content, with the tile's label at the left and its `current`/`current / maximum` value in the shared numeral treatment at the right; a tile carrying more than two breakdown chips SHALL span its grid's full row so its chips wrap in one wide line; no value not already present in the committed payload (such as an effective-vs-base delta) SHALL be invented to fill the tile. The sections themselves SHALL be content-sized cards in an auto-fit grid of equal-width tracks in their DOM order, with the persona area, the intimate disclosure, and a panel-wide unavailable reason spanning the full row, so no section's height depends on another's.

The drawer body SHALL open with a hero naming the committed character: the `status` panel's actor name, its composed full title (`status` actor `full_title`), and the `character` panel's guild rank, each rendered only when the payload supplies a non-blank value and omitted — never guessed — otherwise; the name and title therefore stay in every mode, and the rank is absent while the `character` panel is unavailable. The hero SHALL carry the drawer's existing secondary openers (技能書, and 同伴 ‧ 隊伍 while the party panel is available) in one wrapping action row, with their existing behavior. The body SHALL NOT repeat the drawer title the shared header already renders. The condition roster SHALL render as a wrapped row of rounded pill badges, one per condition, each carrying that condition's label, its visible severity word, its non-colour severity glyph, and its duration/modifier text — the same content the roster shows today, none of it dropped — coloured per severity using the same severity-to-colour mapping the capped status-island condition chips use elsewhere in the HUD. These presentation rules apply identically whether a section is fully populated or marked with a registry-owned unavailable reason.

#### Scenario: The drawer is useful in combat
- **WHEN** the committed mode is combat, so the `character` panel is unavailable
- **THEN** the drawer opens and renders the `status` resources and the complete condition roster, and marks the trait, guild and persona sections with the registry-owned reason without a wallet or equipment placeholder

#### Scenario: Conditions are never colour-only
- **WHEN** the condition roster renders a committed condition
- **THEN** it pairs a non-colour severity glyph with the condition's label and every numeric or derived-modifier value the payload provides

#### Scenario: A disguise is a comparison, not a substitution
- **WHEN** the committed `character` panel carries an active disguise with displayed values
- **THEN** the drawer renders each displayed value beside the true trait row it describes with an explicit label, states that combat resolves against true values, and shows no true row replaced by a displayed one

#### Scenario: The intimate section is preserved in place
- **WHEN** the character-status drawer renders with the `character` panel available and its `intimate` field present
- **THEN** the drawer renders the 親密狀態 disclosure collapsed by default immediately after the 偽裝 section and before the 背景 section, and this change leaves it unchanged

#### Scenario: Every section states what it is
- **WHEN** the character-status drawer renders any of its sections
- **THEN** each section carries a labelled small-caps heading naming it, matching the heading treatment used elsewhere in the HUD

#### Scenario: Vitals, traits, and guild counters render as card tiles
- **WHEN** the vitals, traits, or guild-counter sections render their rows
- **THEN** each row renders as its own bordered tile inside an auto-fill grid of equal-width tracks, only as tall as its content, showing only the label and the value already present in the committed payload, with no invented delta or base-vs-effective figure

#### Scenario: The condition roster renders as coloured pill badges
- **WHEN** the condition roster renders one or more committed conditions
- **THEN** each condition renders as a rounded pill carrying its label, its visible severity word, its severity glyph, and its duration/modifier text — with no content dropped relative to today's rendering — coloured by the same severity-to-colour mapping the capped status-island chips use, and the pills wrap onto additional lines rather than clipping or scrolling horizontally

#### Scenario: The hero names the committed character
- **WHEN** the character-status drawer opens with a `status` panel carrying an actor name and full title and an available `character` panel carrying a guild rank
- **THEN** the hero shows that name, that title and `公會階級 <rank>` above one row holding the 技能書 and 同伴 ‧ 隊伍 openers, and the drawer title appears only in the shared header

### Requirement: The command line advertises only affordances this client implements
The hint cluster SHALL name only behaviour the client implements. It SHALL state the command-history
recall keys and the Tab-completion affordance — matching the draft's `↑↓ 歷史 ‧ Tab 補全` — and
Tab completion SHALL behave as named: pressing Tab inside the input field completes the current
draft against the client's candidate set (session command history and the committed exploration panel's exit names and interact-target display names, deduplicated). With exactly one matching candidate the field SHALL hold the full completion with
the caret at its end; with several the field SHALL hold the longest common prefix and successive
Tab presses SHALL cycle the matching candidates, with Shift+Tab reversing the cycle. A draft that
matches no candidate SHALL leave the field untouched, and Tab SHALL never move focus away from the
field at all (the release path is Escape, which the dock's shortcut legend names). The completion
cycle SHALL reset when the draft text is edited manually, and a change to the committed candidate
sources SHALL drop any in-flight cycle.

The history controls SHALL be labelled controls that drive the same history-walk state the recall
keys drive — one walk reached by two input paths — and SHALL NOT submit. No surface of the command
line SHALL name a key, gesture or affordance that has no implementation behind it.

#### Scenario: The hint names history and completion
- **WHEN** the hint cluster renders
- **THEN** it states the command-history recall keys and the Tab-completion affordance, matching
  the draft wording, and both are implemented

#### Scenario: Tab completes a unique candidate
- **WHEN** the field holds a draft matching exactly one candidate and the player presses Tab
- **THEN** the field holds that candidate in full with the caret at its end, and focus stays in
  the field

#### Scenario: Tab cycles ambiguous candidates
- **WHEN** the field holds a draft matching several candidates and the player presses Tab
  repeatedly
- **THEN** the field first completes to the longest common prefix and then cycles through the
  matching candidates, with Shift+Tab reversing the cycle, and any manual edit of the draft
  resets the cycle

#### Scenario: An unmatched draft is left alone
- **WHEN** the field holds a draft that matches no candidate and the player presses Tab
- **THEN** the field text and focus are unchanged

#### Scenario: The history controls walk the same state as the keys
- **WHEN** the player activates the previous-entry control and then presses the history recall key
- **THEN** both move through the same command-history walk in the same order, the draft is preserved across the walk, and neither submits

### Requirement: The party quickbar island presents the committed party only
The `vitals` anchor SHALL carry a compact party island, beneath the vitals and conditions islands, while
the committed `party` panel is available with at least one slot in exploration, combat, or dialogue
mode, and SHALL render no party island — no header, no count, and no cell — when the panel is
unavailable, when its `slots` list is empty, or when the committed mode is creation. The island's
header SHALL read `同伴` with the slot count as `N / 4`, where `N` equals the committed slot count. Each
row of `party.slots` SHALL render one compact cell, in payload order and in one row, carrying: an avatar
showing the bound portrait only when the row's `portrait_ref` resolves through the client's art
catalog, otherwise the display name's initial letter in the reference's gold display face; beneath it
an HP hairline bar whose fill ratio is `hp_current / hp_maximum`; and an accessible name, also exposed
as the cell's tooltip, stating the display name, the HP numerals, and the row's bond stage name. When
the committed combat panel's participant rows carry a row with the same `identity`, the cell SHALL
additionally show that participant's session token (e.g. `a2`) as a visible badge on the avatar; a
companion not fighting SHALL show no token. The island SHALL render no invite cell and no padding for
missing companions: inviting and the 空位 row live in the 同伴 ‧ 隊伍 drawer, where every row's name,
numerals, and bond stage are also visible text. Activating the island or any cell SHALL open the
同伴 ‧ 隊伍 drawer and SHALL NOT dispatch any action. The island SHALL present no affinity numeral, no
companion trait the panel does not carry, and no estimate.

Because the island is absent for an empty party, the character-status drawer SHALL carry one
labelled `同伴 ‧ 隊伍` control, rendered while the committed `party` panel is available, that opens
the 同伴 ‧ 隊伍 drawer and dispatches nothing, so that drawer stays reachable at every party size.

#### Scenario: The quickbar mirrors the committed party
- **WHEN** a snapshot commits two party slots with HP 180/220 and 144/160 and bond stages 親睦
  and 信賴
- **THEN** the island reads `同伴 2 / 4` and renders exactly two compact cells with their HP hairline
  bars, each cell's accessible name and tooltip state its display name, `180/220` or `144/160`, and
  `親睦` or `信賴`, no invite cell is rendered, and no numeric affinity appears

#### Scenario: The combat token is joined by identity
- **WHEN** the committed combat panel carries a participant row whose `identity` equals a party
  slot's `identity` with token `a2`
- **THEN** that companion's cell shows the `a2` badge on its avatar, and a party row with no matching
  participant shows no token

#### Scenario: No portrait falls back to the initial letter
- **WHEN** a party row carries `portrait_ref: null` for display name `蕾娜`
- **THEN** the avatar renders the gold initial `蕾`, not an invented image

#### Scenario: An unavailable party panel hides the island
- **WHEN** the committed `party` panel switches to the unavailable form
- **THEN** no party island is rendered anywhere in the HUD (not an emptied or dimmed island)

#### Scenario: The quickbar opens the drawer without mutating
- **WHEN** the player activates a party cell
- **THEN** the 同伴 ‧ 隊伍 drawer opens and no `ui_action` or text command is sent

#### Scenario: An empty party renders no island
- **WHEN** the committed `party` panel is available with an empty `slots` list in exploration mode
- **THEN** no party island, header, count, or invite cell is rendered anywhere in the HUD, and nothing in the `vitals` anchor is focusable on its behalf

#### Scenario: The party drawer stays reachable with an empty party
- **WHEN** the committed party is empty and the player opens the character-status drawer and activates its `同伴 ‧ 隊伍` control
- **THEN** the 同伴 ‧ 隊伍 drawer opens with its 空位 row and follow rules, and no `ui_action` or text command is sent

### Requirement: The party drawer presents compbig rows and the fixed follow rules
The 同伴 ‧ 隊伍 drawer SHALL render on the shared reference drawer contract with the sub-count
`N / 4`, one compbig row per committed party slot (initial-letter/gold avatar with the same
portrait fallback, display name, bond stage line, HP bar with numerals, the joined 參戰 token
when the companion fights, and a 請其離隊 control), and one 空位 row stating the invite rule in
stage-name words — the raw affinity threshold number SHALL NOT be shown. The 空位 row's
`邀請當前 NPC…` control SHALL dispatch `explore.party_invite` with the exact existing payload
`{npc_id: <the committed invite-capable interact target's identity>, message: ""}` — the fixed
empty message, since the drawer invents no freeform invitation input — under the existing
dispatch and confirmation contract, enabled only when the committed exploration context names
an invite-capable interact target, and SHALL be disabled with its rule line as the reason
otherwise — it SHALL never fabricate a target. Activating 請其離隊 SHALL dispatch `explore.party_leave` for that identity
under the same contract. The drawer SHALL close the party section with three fixed follow-rule
statements matching the reference draft verbatim, and SHALL render no companion detail control
that has no backing read model.

#### Scenario: Rows follow the committed party
- **WHEN** the drawer is open and a party mutation commits a third companion
- **THEN** a third compbig row appears with its committed fields and the sub-count reads `3 / 4`

#### Scenario: Leaving dispatches through the confirmation contract
- **WHEN** the player activates 請其離隊 on a companion row
- **THEN** the existing confirmation flow submits `explore.party_leave` for that identity and the
  row disappears only when the corresponding commit lands

#### Scenario: The invite control is honest about its preconditions
- **WHEN** the exploration context carries no invite-capable interact target
- **THEN** 邀請當前 NPC… is disabled with the stated rule as its reason and dispatches nothing,
  and the raw invite threshold number is never shown

#### Scenario: The follow rules are the reference's three lines
- **WHEN** the drawer body is enumerated
- **THEN** the 跟隨規則 card carries the reference draft's three fixed statements and no invented
  rules

### Requirement: The place card names the current location and the world time
The stage SHALL carry a place card in its `place` anchor, at the stage box's top-left corner below the
top band, while the committed mode is exploration, dialogue, or combat, and SHALL NOT render it in
creation mode. The card SHALL state the current location as its heading and the world date/time
beneath it, and SHALL be the only surface on the stage or in the top band that states either value.
The location SHALL be the best server-authored place name the client already holds, resolved in a
fixed order: the committed `local_map` panel's `current_node` label when that panel is available,
names a current node, that node is present in the panel's nodes, and its label is a non-empty string;
otherwise the committed status panel's actor location label; otherwise the card's own unavailable
placeholder `位置：--`. The world date/time SHALL be the committed world-time label, and the card's own
unavailable placeholder `時間：--` when none is committed. The card SHALL NOT compose a third string
from the two location candidates, SHALL NOT derive a name from any node or room identifier, SHALL NOT
render a raw room key while a committed panel carries the authored place name for the same room, and
SHALL render no raw mode label in place of the location.

The card SHALL wear the HUD island chrome (the translucent panel fill, the backdrop blur, the
hairline border, the shared radius and shadow, all from the shared design tokens), SHALL keep a fixed
height whatever the label lengths, and SHALL truncate a label that exceeds its width with an overflow
indicator while keeping the full label as its accessible text. It SHALL be display-only: no control,
no tab stop, and no dispatch.

The card SHALL set its two values on two levels: the location heading in the serif face, then a
quiet decorative gold rule, hidden from assistive technology, then the world-time line. The
world-time line SHALL carry no leading separator glyph or rule before its first value, SHALL use the
numeral face with tabular, lining figures at the `--text-sm` step (no smaller than the 12px chrome
floor), and SHALL render the committed world-time label (or its placeholder) verbatim, with every
date and time value intact: all time values SHALL remain server-authored, and the card SHALL NOT
reformat, abbreviate, or derive them. The heading, the rule, and the time line SHALL fit the card's
fixed height.

#### Scenario: The card names the location and the time
- **WHEN** the shell renders in exploration mode with a committed status location `測試起點` and world time `春季 3 日 ‧ 12:00`, and no `local_map` panel
- **THEN** the place card's heading reads `測試起點`, its second line reads `春季 3 日 ‧ 12:00`, and no other stage or top-band element states either string

#### Scenario: The card names the region, not the raw room key
- **WHEN** the player stands in a wilderness cell whose status location label is the raw room key `Wilderness` while the committed `local_map` panel's current node is labelled 西部丘陵與谷地
- **THEN** the card's heading reads 西部丘陵與谷地, `Wilderness` is rendered nowhere in the card, and no composed string pairing the two appears

#### Scenario: The card falls back to its placeholders
- **WHEN** neither the `local_map` panel nor the status panel supplies a location label, and no world time is committed
- **THEN** the card reads `位置：--` and `時間：--`

#### Scenario: The card keeps its size and is absent in creation
- **WHEN** a location label longer than the card's width commits, and later the committed mode becomes creation
- **THEN** the card's rendered box is unchanged and the label is truncated with its full text still exposed to assistive technology, and in creation mode the place card is not rendered and holds no tab stop

#### Scenario: No prefix exists
- **WHEN** a time line has no preceding qualifier
- **THEN** it renders without a leading dash and retains every actual date/time value

#### Scenario: The heading and the time read as two levels
- **WHEN** the place card renders a location and a committed world time
- **THEN** a decorative gold rule lies between the heading and the time line, the time line's numerals are tabular lining figures in the numeral face, and the card keeps its fixed height

### Requirement: Stage actors present the player and the dialogue host with a speaking state
Each standing portrait on the stage SHALL be rendered by one stage-actor component. The player's stage
actor in `actor-left` SHALL present the current roster character's portrait. The dialogue host's stage
actor in `actor-right` SHALL present the committed `art` panel's `portrait_catalog` entry named by the
committed `dialogue` panel's `host.portrait_ref` — the complete image bottom-aligned
with contain fit, and a grounded silhouette with the host identity and authoritative
availability state when the entry is a placeholder. When `portrait_ref`
is `null` or names no catalog entry, the host's stage actor SHALL render the truthful placeholder: the
host display name's initial and the display name, never a stock or guessed image. The client SHALL
NOT construct a catalog key from the host identity or any other field. Each foe's stage actor in the foe
line-up SHALL present the committed `art` panel's `portrait_catalog` entry named by that participant's
`portrait_ref` in the committed combat panel, under the same rule: the complete entry image, the
grounded silhouette for a placeholder entry, and the truthful placeholder built from the
participant's display name when the reference is `null` or names no entry.

While the committed mode is `dialogue` and the host's stage actor renders, the stage actors SHALL carry
a speaking state. The speaker SHALL
render at full brightness and the other side SHALL render dimmed to 60% brightness, from one shared
dim token. The host SHALL be the speaker, except while a `explore.talk_scripted` or
`explore.talk_freeform` action the player submitted is in flight — from its dispatch until its result
is handled and its declared presentation revision is accepted, or until it is rejected — during which
the player SHALL be the speaker. The speaking state SHALL be derived from the dispatch state, the
committed mode, and the panel's availability only, never from narrative prose. Outside dialogue mode,
and in dialogue mode while the `dialogue` panel is unavailable, no stage actor SHALL be dimmed, and a
foe's stage actor SHALL never be dimmed.
The dim SHALL NOT be the only indication of who is speaking: the name plate names the host, and the
speaking state SHALL be exposed on each stage actor as a data attribute for tests. The stage actors are
decorative art and SHALL carry no focusable element; this requirement covers static states only, and
any transition between them is owned by the motion layer.

#### Scenario: The host portrait comes from the art catalog
- **WHEN** the committed `dialogue` panel names `portrait_ref` `"41"` and the committed `art` panel's catalog entry `"41"` carries an image URL and a face rectangle
- **THEN** the host's stage actor renders that complete image bottom-aligned with contain fit, and no other image source is requested

#### Scenario: A pending or missing portrait shows the truthful placeholder
- **WHEN** the host's catalog entry is a pending placeholder, and later a host with `portrait_ref` `null` named `葛里安‧衛登` opens a conversation
- **THEN** the first stage actor shows a grounded silhouette with the host identity and pending state, and the second shows the initial `葛`, identity `葛里安‧衛登` and missing state, and neither renders an image

#### Scenario: The host speaks and the player is dimmed
- **WHEN** a conversation opens and the host's greeting commits
- **THEN** the host's stage actor renders at full brightness with `data-speaking="true"`, and the player's stage actor renders at 60% brightness with `data-speaking="false"`

#### Scenario: The player is lit until the reply commits
- **WHEN** the player activates a pick, and the `explore.talk_scripted` request stays in flight until its reply's revision is accepted
- **THEN** from the dispatch until that revision is accepted the player's stage actor is at full brightness and the host's is dimmed, and once the reply commits the host is lit and the player dimmed again

#### Scenario: A rejected choice returns the light to the host
- **WHEN** the player's `explore.talk_freeform` request is rejected
- **THEN** once the rejection is handled the host's stage actor is lit and the player's is dimmed

#### Scenario: Nothing is dimmed outside dialogue
- **WHEN** the committed mode is exploration, and later combat with two active foes
- **THEN** the player's stage actor renders at full brightness in both, `actor-right` carries no stage
  actor in exploration, and in combat both foes' stage actors render at full brightness
