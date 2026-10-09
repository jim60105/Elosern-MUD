# Spec Delta

## Purpose
The exit compass is the exploration screen's movement control: it encodes each exit's bearing as position on a circular pad, so a player aims at a direction instead of reading a list of destination names.

## ADDED Requirements

### Requirement: Each exploration exit resolves to exactly one angled or portal target
The exit compass SHALL resolve every `move` row of the committed exploration panel to exactly one target, in payload order, as either **angled** (a bearing in degrees clockwise from north) or a **portal**. The rules apply in this order: a map bearing, then a direction word, then portal. `interior` and `instance` coordinates SHALL NOT be used for bearings.

#### Scenario: A wilderness exit takes its map bearing
- **WHEN** the layer is `wilderness`, the current node is at (0, 0), and an exit leads to a node at (1, 1)
- **THEN** the exit is an angled target at 45° and the same exit's remote-direction marker on the minimap points the same way

#### Scenario: An irregular city bearing is preserved
- **WHEN** the layer is `grid` and an exit leads to a node at (3, 4) from (0, 0)
- **THEN** the exit is an angled target at about 36.9° and is not rounded to a cardinal direction

#### Scenario: The map bearing needs both coordinates and a difference
- **WHEN** the destination is absent from the committed local map, or either node lacks coordinates, or the two coordinates are equal
- **THEN** the map-bearing rule does not apply and the next rule is tried

#### Scenario: A direction word is the fallback
- **WHEN** an exit label is `northeast` and its destination is absent from the committed local map
- **THEN** the exit is an angled target at 45°

#### Scenario: Interior doors are portals
- **WHEN** the layer is `interior` and an exit is labelled 公會大廳 with coordinates present on both nodes
- **THEN** the exit is a portal and its coordinates are not used to place it

#### Scenario: Same-coordinate stairs are portals
- **WHEN** an exit labelled up leads to a node with the same coordinates as the current node
- **THEN** the exit is a portal pinned to the up position

### Requirement: Portals occupy deterministic slots on an outer track
Portals SHALL sit on an outer track of the compass. Up SHALL be pinned to 0° and down to 180°. The other portals SHALL take the free slot of a 12-slot ring (30° per slot) nearest their ideal position `round((i + 0.5) · 12 / n)` in payload order, with ties going to the clockwise slot, and more than ten non-vertical portals SHALL switch the ring to 24 slots.

#### Scenario: Three portals spread evenly
- **WHEN** an interior room has three non-vertical portals in payload order
- **THEN** they take the free ring slots nearest ideal positions 2, 6, and 10 of 12 (60°, 180°, 300°) and no two share a slot

#### Scenario: Up and down are pinned
- **WHEN** a room has an up exit, a down exit, and one other portal
- **THEN** up is at 0°, down is at 180°, and the other portal takes neither slot

#### Scenario: More than ten portals switch to 24 slots
- **WHEN** a room has eleven non-vertical portals
- **THEN** the ring has 24 slots and every portal has a distinct slot

### Requirement: An aim snaps to the nearest angled exit within thirty degrees
An aim angle SHALL snap to the angled exit nearest within ±30°, with a tie going to the smaller clockwise angle, and an aim with no angled exit within tolerance SHALL have no target. On the outer track an aim SHALL snap to the nearest portal instead.

#### Scenario: A near exit captures the aim
- **WHEN** angled exits exist at 0° and 90° and the aim is 20°
- **THEN** the target is the exit at 0°

#### Scenario: An aim outside tolerance has no target
- **WHEN** the only angled exit is at 0° and the aim is 100°
- **THEN** there is no target

#### Scenario: A tie goes to the smaller clockwise angle
- **WHEN** angled exits exist at 0° and 60° and the aim is exactly 30°
- **THEN** the target is the exit at 0°

### Requirement: The compass pad answers hover and click
The compass SHALL render a circular pad with four cardinal ticks, a dotted dead-zone ring at 20% of the pad radius, and a current-position dot at the centre. Hovering SHALL aim without sending anything, and leaving the compass SHALL clear the aim and stop any walk. A click SHALL move once to the aimed target through the unchanged `explore.move` payload.

#### Scenario: Hover aims without sending anything
- **WHEN** the pointer moves over the pad toward an angled exit
- **THEN** that exit's pip is highlighted, the readout names its destination, and no `ui_action` is emitted

#### Scenario: The dead zone has no target
- **WHEN** the pointer is inside the dead-zone ring
- **THEN** there is no target and the readout says the direction has no exit

#### Scenario: Click moves once
- **WHEN** the player clicks with an enabled angled exit aimed
- **THEN** exactly one `explore.move` is submitted whose payload is byte-identical to the one the exit's move row has always produced

#### Scenario: Click on nothing or on a disabled target shakes
- **WHEN** the player clicks with no target, or on a disabled target
- **THEN** no `ui_action` is emitted, the pad shakes horizontally for about 260 ms, and the readout shows the reason

#### Scenario: Rapid clicks queue one step
- **WHEN** a move is in flight and the player clicks three more times
- **THEN** exactly one further step is queued, it is sent only after the arrival commit, and it re-snaps the same aim angle against the new room's exits

### Requirement: Holding a pointer press on an angled target starts a walk
A press held for 400 ms on an angled target SHALL start continuous movement. Cursor movement while held SHALL steer the aim, release SHALL stop the walk, and no drag SHALL be required.

#### Scenario: Hold starts a walk
- **WHEN** the player presses and holds on an enabled angled target for 400 ms
- **THEN** the pad rim turns gold and the walk begins with a move to that target

#### Scenario: Steering while held
- **WHEN** a walk is running and the cursor moves to a different angled sector
- **THEN** the next step snaps against the new aim angle

#### Scenario: Leaving the pad stops a walk
- **WHEN** a walk is running and the pointer leaves the compass
- **THEN** the walk stops and no further `explore.move` is sent

### Requirement: The compass is one keyboard composite
The compass SHALL be a single tab stop with `role="application"` and `aria-label="出口羅盤"`, and entering exploration SHALL focus it. Arrow keys SHALL set an eight-way aim that snaps like the pointer, and a tap SHALL only aim. Enter and Space SHALL move to the aimed target and key repeat SHALL be ignored.

#### Scenario: Arrows aim without moving
- **WHEN** the compass has focus and the player taps ArrowUp
- **THEN** the aim is 0°, the readout names the snapped exit, and no `ui_action` is emitted

#### Scenario: Two arrows give a diagonal and opposing arrows cancel
- **WHEN** the player holds ArrowUp and ArrowRight, and then also ArrowDown
- **THEN** the aim is 45° and then 90°

#### Scenario: Enter moves once and repeat is ignored
- **WHEN** an enabled exit is aimed and the player holds Enter for less than 400 ms with key repeat firing
- **THEN** exactly one `explore.move` is submitted

#### Scenario: Entering exploration focuses the compass
- **WHEN** the client enters exploration mode
- **THEN** the compass holds keyboard focus

### Requirement: Bracket keys cycle every target and holding a key walks
The `[` and `]` keys SHALL cycle every target, angled exits by ascending angle and then portals by ascending slot, so an exit crowded out of every arrow sector stays reachable. Holding an arrow or Enter for 400 ms SHALL start continuous movement, and releasing every arrow and Enter, or blur, SHALL stop it.

#### Scenario: Bracket keys reach a crowded exit
- **WHEN** four angled exits lie within one arrow sector and the player presses `]` repeatedly
- **THEN** the aim steps through them by ascending angle, then through the portals by ascending slot, then wraps

#### Scenario: A keyboard hold starts a walk
- **WHEN** an angled exit is aimed and the player holds Enter for 400 ms
- **THEN** continuous movement starts and releasing Enter stops it

#### Scenario: Blur stops a walk
- **WHEN** a keyboard walk is running and the compass loses focus
- **THEN** the walk stops

### Requirement: Continuous movement is commit-driven
During continuous movement the compass SHALL, after each arrival (the next committed exploration panel) and at least 350 ms after the previous step, re-snap the live aim against the new room's angled exits and send the next `explore.move`. It SHALL NOT send a move while another is in flight, and portals SHALL never chain.

#### Scenario: A walk follows the aim across rooms
- **WHEN** the player holds ArrowUp on a wilderness compass and every room has an exit within ±30° of north
- **THEN** the compass sends one `explore.move` per arrival commit, never two in flight, until release

#### Scenario: Portals do not chain
- **WHEN** the aim snaps to a portal during a hold
- **THEN** the hold does not start continuous movement and the portal moves only on a discrete click or Enter

### Requirement: Continuous movement stops safely with a reason
Continuous movement SHALL stop, with a pad shake and a readout reason, when no angled exit lies within ±30°, when the snapped exit is disabled, when the server rejects the move, when the frame leaves exploration, or when the input is released.

#### Scenario: A walk stops at a dead end
- **WHEN** the new room has no angled exit within ±30° of the held aim
- **THEN** no further move is sent, the pad shakes, and the readout shows `這個方向沒有路了，停下腳步。`

#### Scenario: A walk stops at a disabled exit with its reason
- **WHEN** the snapped exit in the next room is disabled with a server-authored reason
- **THEN** the walk stops and the readout shows that reason in the warn tone

#### Scenario: A server rejection stops the walk
- **WHEN** the server rejects a walk step
- **THEN** the walk stops and the readout shows the rejection message

#### Scenario: A mode change stops the walk
- **WHEN** a commit moves the frame to combat or dialogue during a walk
- **THEN** the walk stops without sending another move

### Requirement: The compass feeds one shared readout line
The exploration command panel SHALL render a single readout (`aria-live="polite"`, a gold left rule, a small lead line, and one to two lines of text) explaining the compass aim. A blocked move SHALL flash the readout in the warn tone for about 1.6 s, taking priority over the aim, and with no aim the readout SHALL show the idle summary `出口 N · 在場 M` in the quiet tone.

#### Scenario: An angled target
- **WHEN** the compass aims an enabled exit whose destination node is labelled 西部丘陵與谷地
- **THEN** the readout lead shows `前往` with the octant glyph and the text shows 西部丘陵與谷地

#### Scenario: A portal target
- **WHEN** the compass aims an enabled up exit
- **THEN** the readout lead shows `通道 ⇧` and the text shows the destination name

#### Scenario: A disabled exit shows the server reason
- **WHEN** the compass aims a disabled exit
- **THEN** the readout lead shows `無法通行` and its text is the exit's server-authored reason, unaltered, in the warn tone

#### Scenario: An aim with no target
- **WHEN** the aim points at a sector with no exit
- **THEN** the readout shows the octant glyph over `這個方向沒有出口` in the quiet tone

#### Scenario: Idle summary
- **WHEN** nothing is aimed in a room with three exits and two present entities
- **THEN** the readout shows `出口 3 · 在場 2`

#### Scenario: Destination names fall back to the exit label
- **WHEN** the destination is absent from the committed local map
- **THEN** the readout text is the exit's own label

### Requirement: The aimed destination lights on the minimap and motion respects the motion level
The minimap SHALL highlight the node of the aimed exit and clear the highlight when the aim clears. At the `off` effective motion level every compass transition SHALL resolve in the commit frame and the shake SHALL become a static seal-red flash of the readout.

#### Scenario: The aimed node lights on the minimap
- **WHEN** the compass aims an exit whose destination is a committed minimap node
- **THEN** that node is highlighted on the minimap and the highlight clears when the aim clears

#### Scenario: Motion off removes the shake
- **WHEN** the effective motion level is `off` and a click has no target
- **THEN** the pad does not animate and the readout shows a static warn-tone flash

### Requirement: The compass never loosens the server's gate
The compass SHALL render only committed payload fields and SHALL NOT enable an action the server disabled, and a disabled exit SHALL stay aimable so its reason can be read. Every `explore.move` the compass submits SHALL pass the same stale, duplicate, and in-flight guards as any other exploration action.

#### Scenario: A disabled exit never submits
- **WHEN** the player aims a disabled exit and presses Enter
- **THEN** no `ui_action` is emitted and the reason stays readable

#### Scenario: A stale or duplicate step is suppressed
- **WHEN** the compass is activated while an action is in flight or awaiting its declared presentation revision
- **THEN** no `explore.move` is submitted

### Requirement: The compass degrades honestly
When no local map is committed, exits SHALL resolve by direction word only and the rest SHALL become portals, each disabled with the server's `地圖資料尚未同步。` reason. A room with no exits SHALL render an empty pad with no portal track, and when the exploration panel is unavailable the compass SHALL NOT render.

#### Scenario: No local map
- **WHEN** the local map is not committed and the room has a `north` exit and a named door
- **THEN** the exit labelled north is an angled target at 0°, the door is a portal, both are disabled, and aiming either shows `地圖資料尚未同步。`

#### Scenario: No exits
- **WHEN** the room has no exits
- **THEN** the pad renders with no pips and no portal track, a click shakes, and the readout idles at `出口 0 · 在場 M`

#### Scenario: Exploration panel unavailable
- **WHEN** the exploration panel is unavailable
- **THEN** no compass is rendered and the dock keeps its degraded root

### Requirement: The controls reference documents the compass and the exploration panel shows no key hints
The controls reference SHALL list the compass bindings: arrow aim, `[` and `]` cycling, Enter or Space to move, and holding to walk. The exploration command panel SHALL render no permanent key-hint line.

#### Scenario: The help overlay lists the compass keys
- **WHEN** the player opens the help overlay in exploration
- **THEN** it lists the compass aim, cycle, move, and hold bindings

#### Scenario: No legend in exploration
- **WHEN** the exploration dock renders
- **THEN** no `action-dock-description` key-hint element is present, while dialogue and combat keep theirs

### Requirement: Compass behavior is verified in the live client at two viewports
The compass SHALL be verified by `agent-browser` in the live client at 1451×790 and 1920×1080, where the pad fits the band height minus padding without scrolling the command panel.

#### Scenario: The pad fits at both viewports
- **WHEN** the live client shows an exploration room at 1451×790 and at 1920×1080
- **THEN** the compass pad, readout, and interim overview rows are fully visible with no horizontal overflow and the command panel's box is unchanged from before this change

#### Scenario: Hover, click, and a hold-walk behave as specified in the wilderness
- **WHEN** the wilderness room is explored with hover, a click, and a held direction
- **THEN** each behaves as the pad, click, and walk requirements state
