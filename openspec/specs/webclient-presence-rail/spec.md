# webclient-presence-rail Specification

## Purpose
The presence rail shows who and what is in the room on the stage floor, so people and objects stop competing with exits and room actions in the command panel; the centred choice card carries every choice that needs a list.

## Requirements

### Requirement: The presence rail shows people and objects on the stage floor
In exploration mode the stage SHALL render `PresenceRail` right-aligned on the stage floor, inset left of the right-hand island column: interact targets as gold medallions, other present entities as dashed muted medallions, then a separator and objects as steel lozenges, in `ExplorationMenu.presenceEntries` order, each with a name plate. It SHALL yield to the foe line-up in combat, hide during dialogue and under a centred card, and render nothing when empty.

#### Scenario: Entries follow the overview order
- **WHEN** the room has two interact targets, one bystander, and two objects
- **THEN** the rail shows two gold medallions, one dashed muted medallion, a separator, and two lozenges, each with its name plate, in that order

#### Scenario: A medallion shows the face crop or the initial
- **WHEN** a target or bystander's `portrait_ref` resolves to a URL-bearing image in the art catalog
- **THEN** its medallion shows the face crop through the existing face-rect data

#### Scenario: A medallion without a portrait shows the initial
- **WHEN** a target or bystander has no `portrait_ref`, its catalog entry is unknown or unavailable, or its real image fails to load
- **THEN** its medallion shows the first character of the target's name

#### Scenario: The rail is hidden outside exploration and under a card
- **WHEN** the mode is combat or dialogue, or a centred card is open
- **THEN** the rail is not visible and takes no focus

#### Scenario: An empty room renders no rail
- **WHEN** the room has no people and no objects
- **THEN** the rail renders no element and no placeholder

#### Scenario: Replacement art recovers after a failed face image
- **WHEN** a medallion's image fails to load and a newer committed art entry replaces that image URL
- **THEN** the failed image uses the name initial and the new URL can render its supplied face crop without dispatch or reopening the rail

### Requirement: The rail shows at most six entries and folds the rest into a count
At most six rail entries SHALL show. Beyond six, the sixth slot SHALL become `＋N`, which opens the centred card listing the remaining entries with objects marked ◇, and picking a row there SHALL activate that entry as if it had been picked on the rail.

#### Scenario: Seven entries
- **WHEN** the room has seven rail entries
- **THEN** five entries show and the sixth slot reads `＋2`

#### Scenario: Overflow pick activates the entry
- **WHEN** the player opens `＋2` and picks a listed person
- **THEN** the person's verb card opens exactly as if its medallion had been activated

### Requirement: Rail entries activate by the payload each entry already carries
An interact target SHALL open the person-focus verb card. A bystander or an object SHALL submit its existing `explore.look` payload directly. Hovering or focusing an entry SHALL lift the entry and show `<name>` over the affordance summary (`交談／公會服務`) or `查看` in the shared readout. Entries SHALL fade in and out as the panel changes.

#### Scenario: A bystander is looked at
- **WHEN** the player activates a bystander's dashed medallion
- **THEN** exactly one `explore.look` with that entity's identity is submitted, byte-identical to the former 人物 look chip

#### Scenario: An object is looked at
- **WHEN** the player activates an object's lozenge
- **THEN** exactly one `explore.look` for that object is submitted

#### Scenario: Hover explains
- **WHEN** the pointer rests on a guild clerk's medallion
- **THEN** the readout shows the clerk's name over the affordance summary

### Requirement: The rail is one keyboard composite and digits pick entries
The rail SHALL be one tab stop after the compass, with ←/→ moving between entries and Enter activating the focused entry. While no card is open, digits 1–9 SHALL activate the Nth visible rail entry from anywhere in the exploration screen except the command line and drawers, and while a card is open the card SHALL own the digits.

#### Scenario: Digit picks the Nth entry
- **WHEN** no card is open, focus is on the compass, and the player presses `2` with three rail entries
- **THEN** the second entry is activated

#### Scenario: A card owns the digits
- **WHEN** a verb card is open and the player presses `2`
- **THEN** the card's second row is activated and the rail is not

#### Scenario: Arrow keys move along the rail
- **WHEN** the rail has focus on its first entry and the player presses ArrowRight
- **THEN** focus moves to the second entry and Enter activates it

### Requirement: The person-focus verb card is client-local and replaces the verb popover
Activating an interact target SHALL open the person focus with no server request or router frame. The rail SHALL fade out, the command panel SHALL become inert and dim to about 35% opacity, and the place card and minimap SHALL step away. A target outside the rendered lineup SHALL slide into `actor-right`; a lineup target SHALL reuse its existing figure without duplication. The message window SHALL name the target as speaker, and a centred card SHALL list the target's verbs followed by `✕ 返回`.

#### Scenario: A target without a portrait uses the dialogue silhouette
- **WHEN** the focused target has no portrait
- **THEN** the standee shows the same silhouette, initial, and 無肖像 treatment as the dialogue screen

#### Scenario: Opening is local
- **WHEN** the player activates an interact target's medallion
- **THEN** the card opens with the target's verbs in `verbMenuFor` order followed by `✕ 返回`, and no `ui_action` is emitted and no router frame is pushed

#### Scenario: The command panel is inert while focused
- **WHEN** the verb card is open
- **THEN** the command panel is `inert` at about 35% opacity and takes no focus

#### Scenario: Closing restores the opener
- **WHEN** the player presses Escape or activates `✕ 返回`
- **THEN** a temporary actor-right standee slides out or the selected lineup figure returns to its current baseline dim/z, the rail returns, and focus returns to the medallion that opened the card

#### Scenario: Opening a rendered companion is local and singular
- **WHEN** the player opens a verb card for an identity already rendered in the current actor-left lineup, including through overflow
- **THEN** the existing non-controlled figure becomes lit and rises above every baseline figure, no actor-right copy appears, and no action, router frame or control mutation occurs

#### Scenario: Same names do not imply membership
- **WHEN** a non-lineup target has the same name or portrait reference as a lineup figure
- **THEN** its different identity selects the normal actor-right standee and no lineup companion gains exploration emphasis

#### Scenario: A raw party row is not a rendered figure
- **WHEN** a target occurs in raw party data but is outside the actual displayed bounded lineup
- **THEN** its card uses actor-right and no unrelated companion receives emphasis

#### Scenario: The controlled front cannot be elevated as a listener
- **WHEN** focus identity matches the actual controlled front figure after a possession swap or while party rows are unavailable
- **THEN** no actor-right duplicate appears and the controlled figure retains its baseline z and existing dim/beat behavior

#### Scenario: Membership changes while focus survives
- **WHEN** an open card's surviving interact target enters or leaves the committed rendered lineup
- **THEN** representation transfers between the existing left figure and actor-right in that commit, without a transition-leaving duplicate, and only the current non-controlled selected figure can remain emphasized

#### Scenario: Unavailable panels and epoch reset cannot retain emphasis
- **WHEN** the focused target becomes unavailable, the mode leaves exploration or transport resets the epoch
- **THEN** exploration emphasis clears without retaining the former selected slot, while existing store lifecycle and focus-restoration rules remain authoritative

### Requirement: Verb card rows submit the payloads the popover rows submitted
Each verb row SHALL submit exactly the payload the former popover row submitted: 交談 submits one `explore.talk_open`, contextual service rows open the exact selected-provider existing flow without a frame, 戰鬥 submits `explore.engage`, 查看 submits `explore.look` for the target and closes the card, and a disabled row stays focusable with its server-authored reason and submits nothing.

#### Scenario: 交談 enters dialogue continuously
- **WHEN** the player activates 交談 on the verb card
- **THEN** exactly one `explore.talk_open` with the host's identity is submitted, and the commit that makes the mode `dialogue` shows the dialogue surface with the same actor-right standee for a non-lineup host, or the existing actor-left figure for a lineup host without any right-side duplicate; dialogue speaking signals then own dim/z

#### Scenario: A navigate verb opens its drawer
- **WHEN** the player activates a guild clerk's 公會服務 row
- **THEN** the existing drawer opens from a correlated services.open snapshot for that exact provider and no router frame is pushed

#### Scenario: 戰鬥 submits engage
- **WHEN** the player activates an enabled 戰鬥 row
- **THEN** exactly one `explore.engage` with the target's identity is submitted

#### Scenario: A disabled row explains without submitting
- **WHEN** the player focuses a disabled 交談 or 戰鬥 row and presses Enter
- **THEN** its disabled reason remains readable and no `ui_action` is emitted

#### Scenario: An affordance-less target still gets a card
- **WHEN** an interact target has no mapped affordance
- **THEN** its card retains disabled talk at 1, look at 2 and unnumbered return

#### Scenario: A generative host offers one 交談 row
- **WHEN** the card of an `LLMNPC` host opens
- **THEN** it lists one 交談 row and no free-form row

#### Scenario: Talk submission does not prematurely remove companion focus
- **WHEN** a focused companion's enabled talk row submits and an in-flight or intermediate exploration commit still carries that target and lineup figure
- **THEN** exactly one talk action is submitted and the card's existing left-side emphasis remains until dialogue or normal card invalidation commits

#### Scenario: Dialogue hands over companion speaking state
- **WHEN** a rendered companion's card enters dialogue, then dialogue changes from host to player speaker
- **THEN** that identity remains represented once on the left, exploration-only emphasis ends, and existing host/player dialogue dim/z behavior applies without changing possession or figure geometry beyond existing mode compaction

#### Scenario: A failed talk retains the surviving focus
- **WHEN** talk rejects while its focused target still survives in exploration and its existing lineup figure remains
- **THEN** existing action feedback is shown and that card and companion emphasis remain without resubmitting or mutating party/control state

### Requirement: A departed person closes the card
Committed loss of the focused interact identity or its readable availability SHALL immediately retire the card and pending service correlation regardless of submission locks. Actual departure SHALL restore the existing presence fallback and flash its departure message once. Unreadable presence SHALL close without claiming departure. A committed location change SHALL also close the card.

#### Scenario: The focused person leaves
- **WHEN** the verb card is open and a committed readable presence update removes that person, including while submission is locked
- **THEN** the card closes in that commit and the readout flashes `<name> 已經離開了。`

#### Scenario: A locked departure waits for normal settlement
- **WHEN** the target disappears or presence becomes unreadable while a service read or mutation is pending
- **THEN** that first committed availability loss closes the card and removes correlation/emphasis immediately; late responses cannot reopen it, and later settlement does not flash a duplicate departure message

#### Scenario: Companion focus leaves no stale elevation
- **WHEN** the normal committed presence settlement closes a companion card after departure, or a committed movement closes the card
- **THEN** every remaining non-controlled figure returns to the current lineup baseline dim/z, the existing departure message occurs only for departure, and no temporary right-side figure survives

### Requirement: ChoiceCard is the one centred card shell
`ChoiceCard` SHALL render the card frame, digit-badged rows, the rule before a trailing row, the active-row fill and caret, and the staggered entrance with motion-level handling, as one keyboard composite with one tab stop (ArrowUp and ArrowDown wrap, Home and End, digits 1–9 only, Enter and Space, Escape, `aria-activedescendant`). New consumers SHALL append a trailing `✕ 返回` row and emit `pick(key)` and `back`, and the card SHALL trap focus and return it to its opener on close.

#### Scenario: Keys and digits
- **WHEN** a card with four rows has focus and the player presses `3`, then ArrowDown, then Enter
- **THEN** the third row is picked, then the active row moves, then the active row is picked

#### Scenario: Escape emits back
- **WHEN** a card has focus and the player presses Escape
- **THEN** `back` is emitted and no `pick` is emitted

#### Scenario: Focus is trapped and restored
- **WHEN** a card opens from a rail medallion and then closes
- **THEN** Tab does not leave the card while open, and focus returns to that medallion on close

#### Scenario: Accessible groups and paused focus
- **WHEN** the NPC card contains grouped disabled services
- **THEN** real labeled group headings are nonselectable, every disabled row remains focusable with aria-disabled and inline described reasons, End selects return, and activation sends nothing

### Requirement: The dialogue screen does not change when it renders through ChoiceCard
`DialogueChoices` SHALL keep its view-model logic (picks, `⌨ 自由對話`, `↦ 移動…`, `✕ 結束對話`, and the exits view) and render through `ChoiceCard`, with no visual or behavioral change to the dialogue screen.

#### Scenario: Existing dialogue behavior is unchanged
- **WHEN** the existing dialogue choice tests run unchanged
- **THEN** they pass, including digit picks, the exits view, and the entrance behavior

### Requirement: The presence rail and verb card are verified in the live client at two viewports
The rail, the verb card, the standee handover into dialogue, and the overflow card SHALL be verified by `agent-browser` in the live client at 1451×790 and 1920×1080.

#### Scenario: Geometry at both viewports
- **WHEN** a room with a portrait-bearing host, a bystander, and an object is shown at 1451×790 and at 1920×1080
- **THEN** the rail sits right-aligned above the band without overlapping the right-hand island column, and the verb card is centred and fully visible

#### Scenario: Continuous handover into dialogue
- **WHEN** 交談 is activated from the verb card at both viewports
- **THEN** the non-lineup actor-right standee or the lineup actor-left figure does not leave and re-enter between the card and dialogue, and no duplicate actor-right companion appears

#### Scenario: Companion focus changes no figure geometry
- **WHEN** a companion card opens and closes at both viewports, including reduced and off motion
- **THEN** the selected existing companion changes only dim and z, returns to baseline on close, preserves its box and shared ground line, and remains represented once throughout; all card and cockpit controls remain reachable

### Requirement: Rail digits are claimed by the rail and never fall through
While no card is open, digits 1–9 SHALL be claimed by the rail: a digit beyond the number of visible entries SHALL do nothing, and opening a card SHALL stop any compass walk.

#### Scenario: A digit beyond the rail count is a no-op
- **WHEN** the rail has two entries and the player presses `3`
- **THEN** no `ui_action` is emitted and no room action or dock row is activated

#### Scenario: Opening a card stops a walk
- **WHEN** a compass walk is running and the player presses a rail digit that opens a verb card
- **THEN** the walk stops

### Requirement: Non-party person focus uses the admitted portrait and truthful fallback
A focused target rendered outside the companion lineup SHALL use its server-authored exploration reference to resolve the current art catalog image, preserving the existing stage placeholder when null, unknown, unavailable or failed. Catalog updates SHALL refresh the open target without reopening its verb card or dispatching a focus action.

#### Scenario: An accepted portrait reaches non-party focus
- **WHEN** an accepted exploration snapshot names a real catalog image for a non-lineup target and its medallion opens the verb card
- **THEN** the medallion renders the supplied face crop and the actor-right figure renders that image using the supplied stage geometry; opening sends no action and pushes no frame

#### Scenario: A non-party image cannot load
- **WHEN** the non-party target's real image fails to load or its reference resolves to no usable image
- **THEN** focus retains the same target and usable verbs while the figure shows the established truthful placeholder without inventing a URL

#### Scenario: Current art refresh reaches an open card
- **WHEN** one newer committed update supplies a usable reference and image for the still-focused target, or replaces its prior catalog image URL
- **THEN** that open card's figure renders the new admitted image, its target identity and verb order remain unchanged, and no focus message is sent

### Requirement: NPC cards preserve common slots and grouped service order
NPC cards SHALL retain talk at 1 and look at 2, including disabled reasons, followed by deterministic conditional operations, contextual services and unnumbered return. Only positions 1 through 9 SHALL advertise digit shortcuts; later entries SHALL remain keyboard/scroll reachable.

#### Scenario: Unavailable talk
- **WHEN** the selected NPC cannot converse
- **THEN** talk remains disabled at 1 and look remains at 2; services do not take those slots

#### Scenario: Paused numbering
- **WHEN** a service becomes paused without removal
- **THEN** it retains its semantic identity/position and inline reason

#### Scenario: Overflow
- **WHEN** a test fixture contains more than nine rows
- **THEN** digits activate only their labeled first nine rows; later rows work with arrows/Enter and return remains unnumbered

### Requirement: Menu refresh requires a fresh selection against the current mapping
Activation SHALL be correlated to the rendered stable entry mapping and SHALL reject an obsolete mapping before submission. Equal-content publications SHALL preserve valid focus and local state; a changed entry set, target, route or availability SHALL require a fresh selection.

#### Scenario: Old digit cannot select new row
- **WHEN** a row set changes between render and queued activation
- **THEN** the queued activation is consumed without sending and the user selects again against current rows

#### Scenario: Pointer uses same safety
- **WHEN** a stale click names an entry whose route changed
- **THEN** no old or replacement route is executed

#### Scenario: Equal alignment
- **WHEN** an unchanged presentation arrives with a newer revision
- **THEN** the valid card, selection and drawer input survive

### Requirement: Service return and departure use valid focus origins
Closing a service flow SHALL restore its originating service entry while the actor, NPC, card and entry remain valid. Otherwise the card's valid fallback or existing presence fallback SHALL apply. A departed/invisible target SHALL close the card and invalidate pending routes.

#### Scenario: Service return
- **WHEN** an existing shop drawer closes while its origin still exists
- **THEN** focus returns to the originating shop row

#### Scenario: Departure while opening
- **WHEN** the selected NPC departs before a service read returns
- **THEN** the card closes, the late response is discarded and existing rail fallback owns focus

#### Scenario: Origin disappears
- **WHEN** a service disappears before flow close
- **THEN** focus uses a valid surviving card row or presence fallback without stale selection
