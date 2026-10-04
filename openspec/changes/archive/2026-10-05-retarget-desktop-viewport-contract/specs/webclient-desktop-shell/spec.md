## MODIFIED Requirements

### Requirement: Required desktop surfaces remain visible and usable
The narrative SHALL occupy the bottom band's message region as the bounded message window, whose
complete log is reachable in one action through its `日誌` control, with the brand, the top-meta pill, the
place card, the action dock (in every playing mode except dialogue, where the command region collapses)
and the command-line toggle visible at 1451x790 and at every larger viewport up to the chrome factor's cap, and with each HUD island visible whenever its own contextual-HUD rule renders it (the vitals
island in combat or while a vital or a `warning`, `harmful`, or `critical` condition needs attention, the party island while the party is
non-empty). The action dock and the message window SHALL NOT be permanently closable; the dock's collapse in
dialogue mode lasts exactly as long as the committed mode is `dialogue`. The command
line SHALL NOT be permanently closable either: it is collapsed by default, and its input field SHALL be
reachable in exactly one action — `/` outside an editable control, or the ⌨ toggle — in every mode that
renders it; every other surface MAY be opened on demand and closed. The reference
surfaces — the skill book, the bag and equipment, the shop, the quest board, the lore reference, and
the character status — SHALL NOT be permanently visible: each SHALL render in a drawer laid over the
stage in the shared reference workspace, SHALL be absent from the layout and from the tab order while that drawer is
closed, SHALL be reachable in at most two actions from the top navigation bar or from the action dock's
scene overview, and SHALL be closable in one action that returns focus to the control that opened it. The shell SHALL render a top navigation bar carrying
a labelled control for each navigation-presented entry of the current mode's home surface - the character
status, quest, and inventory entries - a labelled control for the map and settings surfaces, and the
tool group that the top-navigation tool-group requirement defines, which carries the help control;
activating a bar control SHALL open its surface in one action and SHALL NOT push a keyboard menu frame.
The bar SHALL carry no entry that names the screen the player is already on - no 探索 or 戰鬥 home
entry - because the stage itself is that screen; returning the dock to its root stays on Escape and
the dock's back controls.
The map control on the bar is an additional entry point beside the minimap's own control; the
map, settings and help surfaces SHALL each remain reachable from the running client by a labelled control and SHALL be closable in
one action that returns focus to that control. The foundation
SHALL target desktop only and SHALL NOT claim mobile acceptance. The shell SHALL show the game name as its brand and the connection state in the top bar's top-meta
surface, with the connected state marked by an ok-green dot paired with a label, and SHALL show the
current location and the world date/time only in the stage's place card, resolved as the
contextual-HUD place-card requirement states - never in the top bar, and never a raw mode label in
place of location. The top bar SHALL be 48px tall. The action dock SHALL render as the approved command surface: a
panel filling the bottom band's command region (the band's right third), whose exploration root
renders as the scene overview (chip rows for exits, people, and objects, and a footer) and whose
combat root renders as a vertical list of icon-and-label command rows with the focused entry marked by a muted-gold
fill, and whose remaining region renders the current frame's rows or chips. The dock SHALL carry the
shortcut legend the contextual-HUD legend requirement defines. The focused row or chip SHALL be marked
by a muted-gold fill plus a leading glyph, unfocused rows bordered, and disabled rows dimmed
but focusable for their explanation. Below the root frame the
dock SHALL render a breadcrumb naming the parent and current frames with a back control (except
over a target's verb popover, whose own heading names the target once), and SHALL
render each frame's rows in the form that frame calls for — a target's verb popover over the inert
overview, navigation rows, the waiting cards, suggestion cards, or the combat forms — beside a detail
pane that names the focused item, its availability, and the next key action wherever the frame
carries one.
The stage SHALL give the message window and the action dock one fixed-height bottom band - the
message region on the left two thirds and the command region on the right third, or the message region
across the whole band in dialogue mode - whose height comes
from one shared band-height token and never depends on the frame the dock carries, on the mode, or on
the narrative: the scene overview, a target's verb popover, the waiting frame, the combat frames, and an empty
pane host all render inside the same command-region box, so the message window and the action dock never
overlap and neither clips the other at a supported viewport. A frame whose rows exceed the region
SHALL scroll inside the pane host while the dock's chrome (the breadcrumb and
the legend strip) stays fixed around it. In dialogue
mode the message window SHALL span the whole band at the band's fixed height and carry the host's name
plate and the paged line, reachable at the 1451x790 reference viewport by paging inside the window, never by growing it; the
choice rows, the free-dialogue row, the move row and the exit row SHALL render in the dialogue choice
list centred over the stage (the contextual-HUD dialogue-choices requirement), never inside the message
window, and SHALL fit the stage above the band at the 1451x790 reference viewport without document-level scrolling.

#### Scenario: Standard desktop viewport contains every required surface
- **WHEN** the shell renders at 1451x790
- **THEN** the message window, the brand, the top-meta surface, the top navigation bar with its tool group, the place card, every HUD island its own rule renders, the action dock, and the command-line toggle are present without overlapping the narrative input path, and one `/` press renders the command line with its input field focused

#### Scenario: Minimum desktop viewport remains usable
- **WHEN** the shell renders at 2560x1440
- **THEN** every required surface remains reachable and the player can read narrative, open the complete log, open the character-status drawer to inspect status, and type a command after exactly one opening action (`/` or the ⌨ toggle)

#### Scenario: The reference surfaces are demand-opened, not permanently visible
- **WHEN** the shell renders at 1451x790 or 2560x1440 with no drawer open
- **THEN** no skill book, bag, shop, quest board, lore reference, or character-status surface is present in the layout or the tab order, and no permanently visible column of reference panels is rendered

#### Scenario: An open drawer is always one action from closed
- **WHEN** a reference drawer is open at the 1451x790 reference viewport
- **THEN** Escape, its labelled close control, and the scrim each close it in one action and return focus to the control that opened it, and the dock, the message window, and the command-line toggle remain present behind it

#### Scenario: The map, settings and help surfaces are reachable and closable
- **WHEN** the shell renders in exploration mode at the 1451x790 reference viewport with the command line collapsed
- **THEN** a labelled control opens each of the map, settings and help surfaces, and Escape or its close control closes the open one in one action with focus returned to the control that opened it

#### Scenario: The top navigation bar carries the persistent surface entry points
- **WHEN** the shell renders in exploration mode at the 1451x790 reference viewport
- **THEN** the top navigation bar shows one labelled control for each navigation-presented entry of the home surface plus a map control, a settings control, and the tool group, and no 探索 or 戰鬥 entry, each opening its surface in one action without pushing a keyboard menu frame, while the character, quest, and inventory entries are absent from the dock's scene overview

#### Scenario: The complete narrative stays reachable from the bounded caption
- **WHEN** the narrative holds more lines than the message window's page can display
- **THEN** the player reaches the complete retained log in one action through the window's `日誌` control

#### Scenario: Mounting the shell retires the degraded text fallback
- **WHEN** the Vue SPA shell mounts into its container
- **THEN** the degraded stock text fallback (`#messagewindow`) is hidden so it cannot stack with the mounted shell in normal document flow and push required surfaces below the visible viewport

#### Scenario: The shell identifies brand, location, time, and connection without a mode label
- **WHEN** the shell is connected in exploration mode
- **THEN** the brand shows the game name, the top-meta surface shows an ok-green "● 已連線" indicator and no location or time, the place card shows the current location label resolved from the committed panels and the world date/time, and no raw mode label is rendered

#### Scenario: The top-meta location names the region, not the raw room key
- **WHEN** the player stands in a wilderness cell whose status panel location label is the raw room key `Wilderness` while the committed `local_map` panel's current node is labelled 西部丘陵與谷地
- **THEN** the place card's location reads 西部丘陵與谷地, the raw room key is rendered neither in the place card nor anywhere in the top bar, and no composed string pairing the two appears

#### Scenario: The location falls back when the map panel cannot supply a name
- **WHEN** the `local_map` panel is absent, unavailable, or names a current node that its own nodes do not carry or that carries an empty label
- **THEN** the place card's location states the committed status panel's actor location label, and states the card's unavailable placeholder only when neither panel supplies a label

#### Scenario: The action dock fills the command region with its mode's root and one legend
- **WHEN** the action dock is mounted in any mode
- **THEN** it renders as one panel filling the band's command region with one shortcut-legend strip, its exploration root renders as the scene overview and its combat root as a vertical command list with the focused row in a muted-gold fill, its current frame's rows or chips render with a shape-marked focused entry and dimmed but focusable disabled entries, and a breadcrumb with a back control appears below the root frame on every frame except a target's verb popover, which states its target in its own heading

#### Scenario: A tall frame grows the band without touching the narrative
- **WHEN** the dock carries a taller frame (a crowded scene overview, a target's verb popover, or the waiting frame) at 1451x790 or 2560x1440
- **THEN** the bottom band keeps its fixed height, the frame's rows scroll inside the command region, the message window's box is unchanged, and neither surface clips the other

#### Scenario: Pane content scrolls inside the band
- **WHEN** the active frame's rows exceed the command region's height
- **THEN** the rows scroll within the pane host, the dock's chrome (the breadcrumb and the legend strip) remains visible and fixed around the scrolling region, and the last row becomes reachable by scrolling

#### Scenario: The dialogue caption stays bounded at the minimum viewport
- **WHEN** the committed mode is dialogue at 1451x790
- **THEN** the message window spans the whole band and carries the host's name plate and the paged line, the command region is not rendered, and once the line is fully shown every choice row, the free-dialogue row, the move row and the exit row are reachable in the choice list centred over the stage, never inside the message window, without document-level scrolling and without the window or the band changing size

### Requirement: Theme and controls remain accessible
The shell SHALL use the approved desktop palette — near-black charcoal surfaces, warm paper-gray text, a deep seal-red accent retained for its semantic roles (decisive primary action, danger affordances, selection, status markers) alongside a muted-gold navigation, focus, and emphasis accent, and an ok-green connection indicator — while pairing color with labels, borders, icons, or shapes, and SHALL use a serif face for headings, the bundled monospace face for the narrative's message-window page text and full-log lines, and a legible UI face for the remaining controls. Focus SHALL be visibly indicated, resource values SHALL include numeric text, disabled reasons SHALL be programmatically associated with controls, action results SHALL use a non-interrupting live region, and reduced-motion preference SHALL disable nonessential transitions. Every server-authored value carried in a structured presentation panel — labels, descriptions, reasons, names, and legend entries — SHALL be inserted as text and SHALL NEVER be treated as markup. The single bounded exception is the narrative transport stream, which the portal already converts to HTML and escapes player content within; it SHALL be rendered only through the `webclient-narrative-markup` allowlist pipeline, which constructs nodes exclusively through element and text-node constructors and degrades everything outside its allowlist to literal text. No other surface SHALL render server bytes as markup.

#### Scenario: Keyboard focus does not depend on color alone
- **WHEN** keyboard focus moves between action controls
- **THEN** the focused control is distinguishable by a non-color visual indicator and an accessible focus state

#### Scenario: The seal-red accent never carries meaning alone
- **WHEN** a seal-red (vermilion) element is rendered
- **THEN** it is paired with a label, border, glyph, or shape, and seal-red small text on dark surfaces is not used

#### Scenario: Disabled rows expose their reason programmatically
- **WHEN** a disabled action-dock cell is rendered
- **THEN** its disabled reason is programmatically associated with the cell (for example `aria-describedby`) and is readable in the detail pane or a visually hidden description, at every navigation depth including the root

#### Scenario: Player-authored label is not executed as markup
- **WHEN** a server-authored display value in a structured panel contains HTML-like player text
- **THEN** the browser renders it as literal text and no element or script is created from it

#### Scenario: The narrative exception is bounded to one pipeline
- **WHEN** the shell's panel renderers are inspected
- **THEN** only the narrative log renders converted markup, every other renderer inserts server values as text, and no renderer uses an HTML-parsing API

### Requirement: Settings switches preserve native accessible operation
Settings toggle controls SHALL be native checkboxes exposed as switches, named by their visible label and described by their help line, with a checked state marked by both the knob's position and the track's fill. Their labels and help SHALL render through the shared type tokens at or above the 16px chrome floor, they SHALL remain keyboard operable with Space, and they SHALL use the existing preference persistence path. The settings cards SHALL share equal column tracks while each takes its own content height.

#### Scenario: Keyboard toggles a preference
- **WHEN** the focused switch receives Space
- **THEN** exactly one preference change occurs and its new checked state is announced

### Requirement: Reading settings preview preferences without touching play
The settings surface SHALL offer a local reading sample: one fixed line of prose set in the message window's page face — the bundled monospace reading face — at the page size and leading of the chosen prose scale, above both groups of settings controls, with a replay control. The sample SHALL type at the rate the message window would use for the chosen text speed and the effective motion level, so it SHALL show at once for `瞬間` and whenever the effective motion level is not `完整`, and it SHALL name that rule in a visible caption. It SHALL play once when the settings surface opens, SHALL restart once when the prose scale, the text speed or the motion level changes, SHALL play again only through replay, and SHALL NOT loop. Its whole line SHALL stay laid out while it types, so the sample never re-wraps or changes height mid-line, and assistive technology SHALL read the complete line rather than a partly typed one. Updating or replaying the sample SHALL NOT append narrative, send an action, change the live message window's page or reading position, consume or arm its auto-advance, or change gameplay. Closing the settings surface SHALL stop all preview work.

#### Scenario: Preference changes are visible locally
- **WHEN** the player changes the prose scale or the text speed
- **THEN** the sample restarts once at that preference while the live response position and narrative history remain unchanged and no action is sent

#### Scenario: Reduced motion shows the sample at once
- **WHEN** the effective motion level is `減少` or `關閉` and the player replays the sample at any text speed
- **THEN** the whole line is shown at once and the caption names the motion level as the reason

#### Scenario: Preview closes mid-type
- **WHEN** the player closes settings while the sample types
- **THEN** preview timers stop and no later preview content reaches the live reader

### Requirement: The top navigation bar carries the tool group

The top navigation bar SHALL carry, after its 設定 control, one labelled group (`工具`) of icon
controls that open the client's secondary overlays and reference drawers: 技能系譜 (the skill lineage
overlay), 圖鑑 (the world-codex reference drawer), 稱號冊 (the title-codex overlay), 角色肖像圖庫 (the
portrait gallery overlay), and 說明 (the help overlay), in that order. Each control SHALL carry an
accessible name equal to its label, taken from the one tool model that also titles the header of the
surface it opens, SHALL disclose that label visually in the shared tool tooltip that the stable
top-navigation placement requirement defines (and carry no native `title` tooltip), SHALL be reachable
by sequential keyboard navigation, and SHALL open its surface in one pointer action or one Enter press, through the
same opener-captured path every other overlay or drawer opener uses, so closing the surface returns
focus to that control. The 角色肖像圖庫 control SHALL render only while the committed `gallery` panel is
available. The group SHALL render in every mode that renders the top navigation bar, whether the
command line is expanded or collapsed, and SHALL NOT push a keyboard menu frame. No other surface
SHALL carry a second opener for these five surfaces, and the command line SHALL carry none. The group
SHALL fit the 48px bar: at the 1451x790 reference viewport, with every navigation entry, the gallery control, and a
maximum-length character name present, the navigation bar's controls SHALL NOT intersect the top-meta
and character-switcher cluster.

#### Scenario: Each tool opens its surface in one action
- **WHEN** the shell renders in exploration mode with the command line collapsed and the `gallery` panel available, and the player activates 技能系譜, then 稱號冊, then 角色肖像圖庫, then 說明, closing each surface in between
- **THEN** each activation opens its overlay, and each close returns focus to the control that opened it

#### Scenario: The codex tool opens the reference drawer
- **WHEN** the player activates the 圖鑑 control in the tool group
- **THEN** the world-codex reference drawer opens through the single open-drawer entry point, and closing it returns focus to the control

#### Scenario: The gallery tool follows the committed gallery panel
- **WHEN** the committed `gallery` panel is available, and a later revision commits the panel's unavailable form
- **THEN** the 角色肖像圖庫 control is rendered in the tool group while the panel is available, and after the unavailable form commits it is absent from the bar and the tab order

#### Scenario: The tool group is keyboard reachable
- **WHEN** the player moves focus through the top navigation bar with Tab
- **THEN** focus reaches every tool-group control in order, each exposes its label as its accessible name, and Enter on a focused control opens its surface

#### Scenario: The tool group fits the 48px bar at the minimum viewport
- **WHEN** the shell renders in exploration mode at 1451x790 with every navigation entry, the gallery control, and a maximum-length character name present
- **THEN** every tool-group control lies inside the 48px bar, and no navigation control intersects the top-meta or character-switcher cluster

#### Scenario: The command line carries no tool opener
- **WHEN** the command line is expanded
- **THEN** it carries no 技能系譜, 圖鑑, 稱號冊, 設定, 說明, or 角色肖像圖庫 control

### Requirement: Top navigation retains stable tool placement while respecting mode availability
The top navigation bar SHALL lay its labelled primary controls out in one primary region, in this
order: the character status entry (角色狀態), the quest entry (任務), the inventory entry (背包 — the
exploration `inventory` entry and the combat root's `bag` entry are the same concept), the map control
(地圖), and the settings control (設定), followed by the `工具` group. Each primary control SHALL be as
wide as its concept's label length dictates, whatever the mode, and the region SHALL be exactly as
wide as all five controls together and SHALL pack its present controls against its trailing edge, so
the 設定 control and the `工具` group keep the same horizontal position (within 1px) in exploration,
dialogue, and combat at a fixed viewport size, and the space a missing entry leaves collects on the
brand side. An entry the current mode or the committed panels do not supply (the map control in
combat, the character and quest entries in combat, an entry whose panel is unavailable) SHALL be
absent from rendering, the accessibility tree, and the tab order, and SHALL NOT be replaced by a
disabled, `aria-disabled`, `visibility: hidden`, or otherwise present placeholder. The DOM order of
the present controls SHALL equal their visual order. A disabled primary entry keeps its disabled
reason as its `title`. At viewports up to 1350px wide the controls SHALL use compact padding, and at
the 1451x790 reference viewport no navigation control SHALL intersect the top-meta or character-switcher cluster.

Each icon-only `工具` control SHALL disclose its label visually in one shared tooltip treatment,
shown while the pointer rests on the control or on the tooltip itself, and when keyboard focus
arrives on the control by Tab. Focus returned to the control programmatically (a closing surface
restoring its opener) SHALL NOT show the tooltip. The tooltip text SHALL be the control's label; the
tooltip SHALL be hidden from assistive technology (the label is already the control's accessible
name), SHALL NOT take focus, SHALL hide when the control is activated, and SHALL follow the motion
level. Escape SHALL hide a visible tooltip without moving focus. When the tooltip belongs to the
focused control, that Escape SHALL be consumed by the dismissal and SHALL NOT also reach the dock's
keyboard router; once no tooltip shows, Escape on the control SHALL reach the router as before. A
tooltip shown by the pointer SHALL hide on any Escape without consuming it. The next hover or Tab
focus SHALL show the tooltip again.

#### Scenario: Combat removes unavailable entries
- **WHEN** the committed mode changes from exploration to combat at a fixed viewport of 1451x790, 1741x948, or 2560x1440
- **THEN** the 角色狀態, 任務, and 地圖 controls are absent from rendering and the tab order, the combat 背包 control stands immediately before 設定, and the left edges of the 設定 control and of the `工具` group differ from their exploration positions by at most 1px

#### Scenario: An unavailable panel leaves no placeholder
- **WHEN** the committed exploration panel reports the quest surface unavailable
- **THEN** no quest control and no placeholder renders, and the 設定 control and the `工具` group keep their positions

#### Scenario: Keyboard user identifies a tool
- **WHEN** a `工具` control receives keyboard focus by Tab
- **THEN** its label appears as a visible tooltip while focus stays on the control, and Escape hides the tooltip, keeps focus on the control, and leaves the dock's frame unchanged

#### Scenario: A second Escape reaches the dock
- **WHEN** the tooltip of the focused `工具` control has been dismissed with Escape and the player presses Escape again
- **THEN** the key reaches the dock's keyboard router exactly as it would without the tooltip

#### Scenario: A restored opener stays quiet
- **WHEN** a surface opened from a `工具` control closes and returns focus to that control
- **THEN** no tooltip appears

#### Scenario: Pointer user identifies a tool
- **WHEN** the pointer rests on a `工具` control and then moves onto its tooltip
- **THEN** the label appears as a visible tooltip and stays visible, and activating the control hides it
