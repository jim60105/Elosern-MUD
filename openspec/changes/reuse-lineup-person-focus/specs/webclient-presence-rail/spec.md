# Spec Delta

## MODIFIED Requirements

### Requirement: The person-focus verb card is client-local and replaces the verb popover
Activating an interact target SHALL open the person focus with no server request and no router frame. The rail SHALL fade out, the command panel SHALL become inert and dim to about 35% opacity, and the place card and minimap SHALL step away. A target outside the rendered companion lineup SHALL use `actor-right`; a lineup target SHALL reuse its existing figure without duplication, the message window SHALL name the target as speaker, and a centred card SHALL list the target's verbs followed by `✕ 返回`.

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
Each verb row SHALL submit exactly the payload the former popover row submitted: 交談 submits one `explore.talk_open`, 交易 and 公會服務 open their drawer without a frame, 戰鬥 submits `explore.engage`, 查看 submits `explore.look` for the target and closes the card, and a disabled row stays focusable with its server-authored reason and submits nothing.

#### Scenario: 交談 enters dialogue continuously
- **WHEN** the player activates 交談 on the verb card
- **THEN** exactly one `explore.talk_open` with the host's identity is submitted, and the commit that makes the mode `dialogue` shows the dialogue surface with the same actor-right standee for a non-lineup host, or the existing actor-left figure for a lineup host without any right-side duplicate; dialogue speaking signals then own dim/z

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
If the focused person is no longer in the committed `interact` list, the card SHALL close in the same commit, a temporary actor-right standee SHALL leave or a surviving lineup SHALL lose the departed focus emphasis, the rail SHALL return, and the readout SHALL flash `<name> 已經離開了。`. A move that changes the committed location SHALL close the card as well.

#### Scenario: The focused person leaves
- **WHEN** the verb card is open and a commit removes that person from the room
- **THEN** the card closes in that commit and the readout flashes `<name> 已經離開了。`

#### Scenario: Companion focus leaves no stale elevation
- **WHEN** the normal committed presence settlement closes a companion card after departure, or a committed movement closes the card
- **THEN** every remaining non-controlled figure returns to the current lineup baseline dim/z, the existing departure message occurs only for departure, and no temporary right-side figure survives

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
