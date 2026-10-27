# Spec Delta

## ADDED Requirements

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

## MODIFIED Requirements

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
