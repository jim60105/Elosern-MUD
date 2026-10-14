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
Activating an interact target SHALL open the person focus with no server request and no router frame. The rail SHALL fade out, the command panel SHALL become inert and dim to about 35% opacity, and the place card and minimap SHALL step away. The target's standee SHALL slide into the `actor-right` anchor, the message window SHALL name the target as speaker, and a centred card SHALL list the target's verbs followed by `✕ 返回`.

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
- **THEN** the standee slides out, the rail returns, and focus returns to the medallion that opened the card

### Requirement: Verb card rows submit the payloads the popover rows submitted
Each verb row SHALL submit exactly the payload the former popover row submitted: 交談 submits one `explore.talk_open`, 交易 and 公會服務 open their drawer without a frame, 戰鬥 submits `explore.engage`, 查看 submits `explore.look` for the target and closes the card, and a disabled row stays focusable with its server-authored reason and submits nothing.

#### Scenario: 交談 enters dialogue continuously
- **WHEN** the player activates 交談 on the verb card
- **THEN** exactly one `explore.talk_open` with the host's identity is submitted, and the commit that makes the mode `dialogue` shows the dialogue surface with the same standee already on stage

#### Scenario: A navigate verb opens its drawer
- **WHEN** the player activates a guild clerk's 公會服務 row
- **THEN** the quest drawer opens from the unchanged `services` payload and no router frame is pushed

#### Scenario: 戰鬥 submits engage
- **WHEN** the player activates an enabled 戰鬥 row
- **THEN** exactly one `explore.engage` with the target's identity is submitted

#### Scenario: A disabled row explains without submitting
- **WHEN** the player focuses a disabled 交談 or 戰鬥 row and presses Enter
- **THEN** its disabled reason remains readable and no `ui_action` is emitted

#### Scenario: An affordance-less target still gets a card
- **WHEN** an interact target has no mapped affordance
- **THEN** its card holds 查看 and `✕ 返回`

#### Scenario: A generative host offers one 交談 row
- **WHEN** the card of an `LLMNPC` host opens
- **THEN** it lists one 交談 row and no free-form row

### Requirement: A departed person closes the card
If the focused person is no longer in the committed `interact` list, the card SHALL close in the same commit, the standee SHALL leave, the rail SHALL return, and the readout SHALL flash `<name> 已經離開了。`. A move that changes the committed location SHALL close the card as well.

#### Scenario: The focused person leaves
- **WHEN** the verb card is open and a commit removes that person from the room
- **THEN** the card closes in that commit and the readout flashes `<name> 已經離開了。`

### Requirement: ChoiceCard is the one centred card shell
`ChoiceCard` SHALL render the card frame, digit-badged rows, the rule before a trailing row, the active-row fill and caret, and the staggered entrance with motion-level handling, as one keyboard composite with one tab stop (ArrowUp and ArrowDown wrap, Home and End, digits 1–N, Enter and Space, Escape, `aria-activedescendant`). New consumers SHALL append a trailing `✕ 返回` row and emit `pick(key)` and `back`, and the card SHALL trap focus and return it to its opener on close.

#### Scenario: Keys and digits
- **WHEN** a card with four rows has focus and the player presses `3`, then ArrowDown, then Enter
- **THEN** the third row is picked, then the active row moves, then the active row is picked

#### Scenario: Escape emits back
- **WHEN** a card has focus and the player presses Escape
- **THEN** `back` is emitted and no `pick` is emitted

#### Scenario: Focus is trapped and restored
- **WHEN** a card opens from a rail medallion and then closes
- **THEN** Tab does not leave the card while open, and focus returns to that medallion on close

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
- **THEN** the standee does not leave and re-enter between the card and the dialogue surface

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
