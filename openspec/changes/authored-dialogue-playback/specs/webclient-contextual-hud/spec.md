# Spec Delta

## MODIFIED Requirements

### Requirement: Stage actors present the player and the dialogue host with a speaking state
Each standing portrait on the stage SHALL be rendered by one stage-actor component. The controlled figure and companions in `actor-left` SHALL follow the companion-lineup rule. The dialogue host SHALL render once: when its committed identity joins to a committed party slot or controlled lineup figure, its existing lineup StageActor is the host and no duplicate renders in `actor-right`.

#### Scenario: The host actor presents its catalog entry truthfully
- **WHEN** a non-party host's stage actor renders in `actor-right`
- **THEN** it presents the committed `art` panel's `portrait_catalog` entry named by `dialogue.host.portrait_ref` — the complete image bottom-aligned with contain fit, and a grounded silhouette with host identity and authoritative availability when the entry is a placeholder; when `portrait_ref` is null or names no catalog entry it renders the truthful placeholder: the display name's initial and display name, never a stock or guessed image; and the client constructs no catalog key from host identity or any other field

#### Scenario: Foes follow the same presentation rule
- **WHEN** a foe's stage actor renders
- **THEN** it presents its committed catalog entry under the same complete-image, grounded-silhouette and display-name-placeholder rule

#### Scenario: Speaking follows dispatch state, never prose
- **WHEN** the committed mode is dialogue and a native freeform response is presented
- **THEN** native freeform speaking follows existing dispatch-state behavior, never prose; static/generated scenes follow their explicit line attribution

#### Scenario: Companions listen unless they are the host
- **WHEN** a companion's identity does, or does not, match the active host
- **THEN** companions remain listeners unless their identity matches that active host; a speaking companion temporarily receives the highest z without moving, then restores baseline z

#### Scenario: Nothing dims outside dialogue
- **WHEN** the mode is outside dialogue, or its panel is unavailable
- **THEN** the controlled figure remains lit and foes are never dimmed

#### Scenario: The speaking cue is never colour-only or disruptive
- **WHEN** a speaking state is active
- **THEN** the dim is not the only speaking cue — the name plate names the current explicit speaker (none for narration) and each actor exposes its speaking data attribute; actors remain decorative, with no focusable element; motion owns transitions; and no other dialogue behavior changes: the name plate, pagination, choices, focus, keyboard paths and non-party host mode-transition motion retain their contracts

#### Scenario: The host portrait comes from the art catalog
- **WHEN** a non-party host's dialogue panel names ref `"41"` and its catalog entry carries an image and face rectangle
- **THEN** the actor-right host renders that complete image bottom-aligned with contain fit and requests no other image source

#### Scenario: A pending or missing portrait shows the truthful placeholder
- **WHEN** the host's catalog entry is pending, and later a host named `測試人物` has a null ref
- **THEN** the first actor shows its grounded silhouette, identity and pending state; the second shows initial `測`, identity and missing state, with neither inventing an image

#### Scenario: The host speaks and the player is dimmed
- **WHEN** a conversation opens and its greeting commits
- **THEN** the host renders lit with `data-speaking="true"` and the player dimmed with `data-speaking="false"`; a companion host appears only in its raised existing slot

#### Scenario: The player is lit until the reply commits
- **WHEN** the player's native freeform speech remains in flight until its reply revision is accepted
- **THEN** the player is lit and the host dim until that revision, then the host is lit and the player dim again

#### Scenario: A rejected choice returns the light to the host
- **WHEN** the player's freeform speech is rejected
- **THEN** rejection handling restores the host's light and the player's dim

#### Scenario: Nothing is dimmed outside dialogue
- **WHEN** mode is exploration and later combat with two active foes
- **THEN** the controlled figure is lit in both and both foes are lit in combat; companions retain their listener dim, and actor-right carries no exploration actor

#### Scenario: A companion host is not duplicated on the opposite anchor
- **WHEN** dialogue host identity joins to a committed party or controlled lineup figure
- **THEN** that identity has exactly one standing figure in actor-left, actor-right has no duplicate host, and the name plate, pagination and focus retain their existing behavior

#### Scenario: Consecutive actor and host lines
- **WHEN** a complete scene has actor speech followed by two host lines and narration
- **THEN** speaker emphasis changes with each line, both host lines remain separately advanceable and narration removes emphasis

### Requirement: Dialogue choices appear centred over the stage after the line is fully read
While the committed mode is `dialogue` and the committed `dialogue` panel is available, the client SHALL present the conversation's choices as one choice list in the stage's `choices` anchor, and nowhere else. The list SHALL render only while the message window reports that a native response last page is fully shown or an authored scene has received its explicit final-page finish activation, with no pending action mark, and while no action the player dispatched is in flight.

#### Scenario: Any unread or in-flight moment hides the list
- **WHEN** a page is still typing, a further page is not yet read, or a pick or free-form speech awaits its reply
- **THEN** the list is not rendered

#### Scenario: The rows follow the payload exactly
- **WHEN** the choice list renders
- **THEN** its rows are, in order: one pick row per `dialogue.choices` entry in payload order, each carrying the digit badge of its 1-based position and its bounded label; a `⌨ 自由對話` row; a `↦ 移動…` row; and a `✕ 結束對話` row — and it renders no row the panel does not back, no reason tag, and no disabled pick

#### Scenario: Picks and exits dispatch their exact intents
- **WHEN** the player activates a pick row, or an enabled exit row
- **THEN** a pick dispatches `explore.talk_scripted` with the committed source-correct action payload plus its dispatcher selection identity through the single dispatch entry, and an enabled exit row dispatches the unchanged `explore.move` payload of its committed move row

#### Scenario: The free-form and exit rows dispatch nothing themselves
- **WHEN** the player activates `⌨ 自由對話`, or `✕ 結束對話`
- **THEN** `⌨ 自由對話` expands the command line and focuses its field through the free-form borrow path, bound to the host, and dispatches nothing itself; `✕ 結束對話` dispatches `explore.dialogue_leave` with `{npc_id: host.identity}` and nothing else

#### Scenario: The move row borrows the scene overview's exits
- **WHEN** the player activates `↦ 移動…`
- **THEN** it dispatches nothing and replaces the choices with dedicated committed `moveItems` rows from the store view, independent of the router root, in payload order, carrying their direction glyphs, enabled destination names, disabled markers and unchanged server reasons, followed by a back row

#### Scenario: The exit rows return to the choices
- **WHEN** Escape or the back row is activated in the exit rows, or the committed room has no exits
- **THEN** the choice rows return with the `↦ 移動…` row focused, and a room without exits still shows the back row alone

#### Scenario: One composite, one tab stop, full keyboard
- **WHEN** the choice list holds focus
- **THEN** it is one keyboard composite and one tab stop: DOM focus rests on the list container, which names its focused row through an active-descendant reference; ArrowUp and ArrowDown move to the previous and next row, wrapping; Home and End move to the first and last row; Enter and Space activate the focused row; while the choice rows are shown, digit `1`–`N` activates pick N directly; and a held key's auto-repeat does not activate

#### Scenario: The active row is shown by shape and fill
- **WHEN** the list holds focus on its rows, including a disabled exit row
- **THEN** the active row is shown by shape and fill — a leading `▸` and the dock's muted-gold fill — never by colour alone, and an active disabled exit row keeps a quiet treatment that promises no action

#### Scenario: Handled keys stop at the list
- **WHEN** the list handles a key, and when `/` or an unhandled key is pressed
- **THEN** every key the list handles is consumed by it and does not reach the keyboard router or the page surface, while `/` and every key the list does not handle passes on unchanged

#### Scenario: Focus arrives, leaves, and never dangles
- **WHEN** the list appears while focus is on the message window, inside the message region, or on the document body, and when an activation is about to dispatch
- **THEN** focus moves to the list with its first row focused, and before an activation dispatches focus moves to the message window's page surface, so the list's removal never leaves focus on a removed element or the document body; a pointer activation of a row focuses that row and activates it through the same path as Enter

#### Scenario: Activations obey the dispatch lock once each
- **WHEN** a mutation is in flight or awaiting its declared presentation revision, and when key and pointer input combine
- **THEN** every activation is suppressed exactly like a dock entry, and no combination of key and pointer input emits more than one request per deliberate activation

#### Scenario: The list derives only from committed panels
- **WHEN** the list's rows and presence are computed
- **THEN** rows derive from the committed `dialogue` and `exploration` panels alone and depend on no dock frame or router descriptor, and presence derives from the window's reader state and the dispatch state, never from narrative prose

#### Scenario: The choices wait for the last page
- **WHEN** a greeting of two pages commits with three choices at the `normal` text speed
- **THEN** no choice list is rendered while page 1 types, after it is fully shown, or while page 2 types, and the list renders in the `choices` anchor with focus on its first row once page 2 is fully shown

#### Scenario: The rows follow the committed panel
- **WHEN** the list renders for a panel with three choices
- **THEN** it shows pick rows badged `1`, `2`, `3` with the panel's labels in payload order, then `⌨ 自由對話`, `↦ 移動…`, and `✕ 結束對話`, and nothing else

#### Scenario: A pick dispatches the scripted keyword
- **WHEN** the player activates pick 2 through pointer, Enter, or the `2` key
- **THEN** exactly one `explore.talk_scripted` request with the committed host identity and stable static/generated topic/context payload is submitted, the list hides while in flight, focus stays on the message surface, and the list returns after the scene's final fully visible page receives a further activation

#### Scenario: Free dialogue borrows the command line
- **WHEN** the player activates `⌨ 自由對話`
- **THEN** the command line expands with focus in its field for a freeform utterance to the host, and no action is dispatched

#### Scenario: The exit row ends the conversation
- **WHEN** the player activates `✕ 結束對話`
- **THEN** exactly one `explore.dialogue_leave` request with the committed host identity is submitted and no other action is dispatched

#### Scenario: Move swaps in the exits and Escape returns
- **WHEN** the room has two exits, one locked, and the player activates `↦ 移動…`, focuses the locked exit and presses Enter, then presses Escape
- **THEN** the list shows the two exit rows with their direction glyphs and the back row, the locked row shows its reason and nothing is submitted, and Escape returns to the choice rows with `↦ 移動…` focused

#### Scenario: A move from the list leaves the conversation
- **WHEN** the player activates `↦ 移動…` and then an enabled exit row
- **THEN** exactly one `explore.move` request with the committed move row's unchanged payload is submitted, the movement settlement clears the session through the existing seam, and the committed mode returns to `exploration` with the dock at the new room's overview

#### Scenario: The list is one tab stop and keeps its keys
- **WHEN** the list has focus and the player presses Tab, then Shift+Tab back, then ArrowDown twice and Enter
- **THEN** Tab leaves the list in one step, the list is reached again in one step, the arrows move the active-descendant reference, Enter activates the focused row once, and the keyboard router saw none of those arrow or Enter keys

#### Scenario: The choices never show beside unread text
- **WHEN** a reply's first page is on screen and further lines of the same response arrive
- **THEN** the list stays unrendered until the authored scene explicit finish activation, or the native response last page is fully shown

#### Scenario: Reconnect replays scene from first line
- **WHEN** the client reconnects to the same valid delivered scene
- **THEN** choices stay hidden until that replay finishes explicitly and replay submits no new selection/effect

### Requirement: The message window presents the current response one page at a time in the band's message region
The narrative SHALL render as a message window filling the bottom band's message region — the left two thirds of the band, or the whole band in dialogue mode, at the band's fixed height — drawn with the reference's caption panel treatment. The window SHALL never grow into the stage or change size with its content, SHALL present exactly one page of the current response at a time in every mode, and SHALL NOT present earlier responses.

#### Scenario: The window wears the reference caption panel chrome
- **WHEN** the message window renders
- **THEN** it is drawn with the reference's caption panel treatment: charcoal panel fill, a hairline border, shared radius and restrained shadow

#### Scenario: Paging follows the narrative and combat contracts
- **WHEN** the window presents the current response, including while that response carries a combat round the client presents
- **THEN** pages follow `webclient-input-narrative` and are revealed as its typing requirement defines — or, for a presented combat round, as that round's beat pages followed by the response's remaining lines, as `webclient-combat-menu` "A combat round plays beat by beat" defines — and earlier responses are not presented: they remain readable in the full-log surface

#### Scenario: The clear layer is the one paging exception
- **WHEN** a new response replaces the previous one
- **THEN** the previous page MAY remain only as an opaque layer over the new page that fades out within the clear duration of the client's motion level (at most 150ms, and none at `off`), carries no focusable element, and is outside the accessibility tree and pointer hit-testing from the moment the new response starts

#### Scenario: Page typography is bounded at the reference size
- **WHEN** page text renders at the 1451x790 reference size and the default prose scale
- **THEN** it is set in the bundled monospace reading face — the same Jim Mono TC family the monospace type role ships — at 18px, scales once with the desktop chrome factor and with the client's prose scale, and holds at most 42 CJK characters per line in every mode, including the whole-band width of dialogue mode

#### Scenario: The control strip carries the marker and the log control
- **WHEN** any page renders
- **THEN** the window's lower edge keeps a control strip in which no page text renders, holding a page marker and, at its right end, a labelled `日誌` control beside the command-line toggle

#### Scenario: The marker names the page state decoratively
- **WHEN** the on-screen page is fully shown, typing, or a combat round plays by itself
- **THEN** the marker renders only while the page is fully shown and is absent while it types and while a combat round plays by itself; when rendered it reads `▼` while the current response has further pages and `■` on its last page; it is decorative (hidden from assistive technology) and blinks only through the client's motion tokens, so reduced motion stops the blink

#### Scenario: An oversize page scrolls without growing the window
- **WHEN** a page is taller than the window's text area
- **THEN** it scrolls inside the text area; it is never truncated and never grows the window

#### Scenario: The log control and scroll-up open the full log
- **WHEN** the player activates the `日誌` control, or scrolls up over a page that has nothing left to scroll up
- **THEN** the full-log surface opens in one action; its content, markup renderer, focus trap, Escape close, focus restore to the opening control, and opening at its latest line are unchanged

#### Scenario: The window carries no reading chrome beyond the plate
- **WHEN** the window renders in any mode
- **THEN** it renders no unread indicator, no jump-to-latest control, and no head row other than the dialogue name plate; in creation mode the window, its marker, and the `日誌` control are hidden with the message region

#### Scenario: The dialogue name plate names the host truthfully
- **WHEN** the committed mode is `dialogue` and the committed `dialogue` panel is available
- **THEN** the window plate names the current explicit actor or host, with bond-stage suffix only for host speech; narration has no speaker plate; native freeform retains host-name behavior; the text area pages/types the current attributed scene line or native response unchanged, with no separate reply box, rows, avatar or rewritten narrative; choices remain in the dialogue choice list

#### Scenario: A transient panel shows no plate, and reader state drives the choice list
- **WHEN** mode is `dialogue` but the panel is unavailable (the transient window between a clear seam and its commit)
- **THEN** the window renders no name plate, and the window makes known to the shell, from its own reader state and never from narrative prose, whether an authored scene has received its final explicit finish activation, or a native response last page is fully shown, with no pending action mark

#### Scenario: The window keeps the message region's box
- **WHEN** the current response holds more text than one page and new lines keep arriving
- **THEN** the window keeps the message region's box — the band's height and two thirds of its
  width, or the whole band in dialogue mode — and never expands into the stage

#### Scenario: One page of the current response is shown
- **WHEN** the log holds three responses and the latest one fills two pages
- **THEN** the window shows only the first page of the latest response, and once the clear transition
  has finished no line of the two earlier responses is rendered in the window

#### Scenario: The page measure is bounded at the reference size
- **WHEN** the stage renders at 1451x790 with the default prose scale and a long prose response, in exploration mode and in dialogue mode with the panel transiently unavailable
- **THEN** the page text's computed font size is 18px (±0.5px) in the bundled monospace reading face and no rendered text line holds more
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
- **WHEN** mode `dialogue` commits with host `灰婆婆`, `bond_stage` `親睦`, and a greeting long enough for two pages at 1451x790
- **THEN** the window spans the whole band, shows the name plate `灰婆婆 ‧ 羈絆 親睦`, types page 1 with no marker until it is fully shown, shows `▼`, advances on Enter on the page surface to page 2, and shows `■` once page 2 is fully shown, with no choice row inside the window at any point

#### Scenario: An unbonded host's plate names only the host
- **WHEN** mode dialogue presents host speech with bond_stage null
- **THEN** host speech names the host alone, actor speech names the acting body alone, and narration has no speaker plate or bond text

#### Scenario: A transiently unavailable panel shows no plate
- **WHEN** mode is `dialogue` but the committed panel is the unavailable form
- **THEN** no name plate renders and the window shows the current response's pages with their page marker

#### Scenario: Narration and actor plate change with text
- **WHEN** an actor speech begins after a host line and then narration begins
- **THEN** text/name/portrait transition synchronously to actor and then to no speaker, with no host plate retained for narration

### Requirement: Text speed and auto-advance are client-local reading preferences the settings surface owns
The settings surface's reading section SHALL offer a text-speed control with the four steps `慢` (`slow`), `標準` (`normal`), `快` (`fast`), and `瞬間` (`instant`), and an auto-advance toggle (`自動翻頁`). The text speed SHALL default to `normal` and auto-advance SHALL default to off.

#### Scenario: The speed step is marked without colour
- **WHEN** a text-speed step is current
- **THEN** it is marked by an indicator that does not rely on colour alone and is exposed as the pressed state of its button

#### Scenario: The control names the motion override
- **WHEN** the text-speed control renders
- **THEN** it says that the `減少` and `關閉` motion levels show pages at once, because an effective motion level other than `full` overrides the chosen speed as `webclient-input-narrative` defines

#### Scenario: Both preferences follow the settings rules
- **WHEN** either reading preference changes
- **THEN** it follows the settings rules of "Narrative prose scale is a client-local preference the settings surface owns": client-local, dispatching nothing, applied to the message window immediately, persisted through the versioned presentation-only browser store, re-applied at load, and reset to its defaults when that store resets

#### Scenario: An out-of-range stored value falls back
- **WHEN** a stored value lies outside the defined steps
- **THEN** it is discarded and the default applies

#### Scenario: Choosing a text speed applies and persists it
- **WHEN** the player opens the settings surface and selects `快`
- **THEN** the `快` button is pressed and marked by a non-colour indicator, the next page the
  message window shows types at the fast speed, the stored wrapper carries `textSpeed: "fast"`, and
  no `ui_action` is sent

#### Scenario: Auto-advance is off until the player turns it on
- **WHEN** the client loads with no stored preferences, and the player then turns on `自動翻頁`
  and reloads
- **THEN** auto-advance is off on the first load, and after the reload the toggle is on and a fully
  shown native prose page with a next page advances on its own; authored scenes remain manual at every line/page including their final finish activation

#### Scenario: An invalid stored speed falls back to the default
- **WHEN** the stored wrapper carries a text speed outside the four steps
- **THEN** the client loads with the `normal` speed, and the other stored preferences still apply

#### Scenario: Stored auto advance never drives authored scenes
- **WHEN** auto-advance is on and an authored scene is playing at any motion level
- **THEN** typing may be accelerated or instantaneous but no page, line or finish activation occurs automatically
