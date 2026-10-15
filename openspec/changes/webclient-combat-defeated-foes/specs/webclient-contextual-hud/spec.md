## ADDED Requirements

### Requirement: Fallen combat figures read as defeated or down at a glance
A foe whose state is `knocked_out` or `defeated` SHALL stay in its formation slot in a dedicated defeated treatment, and a party figure whose state is `knocked_out` SHALL stay in a sibling down treatment. Each treatment SHALL combine a shape channel, a text channel on the plate and a tone change, and SHALL differ from the listener dim and from each other.

#### Scenario: A defeated foe has its own look
- **WHEN** a foe is `knocked_out` or `defeated` at rest
- **THEN** its figure is collapsed about its base (lowered by 12% and compressed to 80% of its height, never rotated, so its transformed box stays inside its slot), fully desaturated and darkened (`grayscale(1)`, brightness 0.45) at 0.8 opacity with its silhouette intact, a broken-seal mark (a seal ring split by a crack, drawn in CSS/SVG from the seal tokens, `aria-hidden`) stands over its chest, its plate's readout is replaced by `✕ 已擊破` with an empty dashed stroke, and its accessible name ends with 已擊破

#### Scenario: An ally that is down has a sibling look
- **WHEN** a companion is `knocked_out` at rest
- **THEN** its figure kneels (lowered by 8% of its height and compressed to 92% of its height about its base, without rotation), half desaturated and dimmed (`grayscale(0.6)`, brightness 0.7) at full opacity, carries no seal mark, its plate's readout is replaced by `▼ 倒地` with an empty dashed stroke, and its accessible name ends with 倒地

#### Scenario: Fallen looks never read as a dim
- **WHEN** a defeated foe, a down companion and a listener-dimmed figure in dialogue render side by side in stories and in the live client
- **THEN** the dimmed figure keeps its colour, pose and opacity and carries no mark or fallen text, while the defeated foe alone has the collapse, the seal and 已擊破 and the down companion alone has the kneel and 倒地, so every pair differs by shape and text, not by brightness alone

#### Scenario: Every art state takes the treatment
- **WHEN** a defeated foe has a finished portrait, a placeholder silhouette with its initial, and failed art with its failure marker
- **THEN** each takes the same collapse, tone, opacity and seal mark on its figure wrapper, the placeholder initial and the failure marker stay legible, and no new bitmap is used

#### Scenario: Falling plays with the beat and the motion level
- **WHEN** a playing round's defeat beat names a foe at `full`, at `reduced`, and at `off`, and when the client reloads or reconnects with a defeated foe on the stage
- **THEN** at `full` the foe collapses into its defeated look over the beat-defeat duration on the exit easing and the seal mark fades in after it; at `reduced` the pose applies without travel and only the tone and the mark fade within 150ms; at `off`, and on a reload or reconnect, the defeated look renders at rest in the commit's frame; a companion going down follows the same timings with its own look

#### Scenario: Fallen figures keep their slot
- **WHEN** one of three foes is defeated, and later one flees
- **THEN** the defeated foe keeps its slot and the formation does not re-form; the fled foe fades where it stands and the formation re-forms for the remaining drawn figures

## MODIFIED Requirements

### Requirement: Combat figures stand in a shared-scale formation
While the committed mode is `combat`, or while a round that ended the fight still plays, the stage SHALL place the controlled figure, every drawn companion and every foe that has not fled (active, knocked out or defeated; up to 16 minus the party count, in presenter order) at the boxes that "Combat formation geometry is one pure shared-scale function" returns for the live stage geometry. Every figure on both sides SHALL be drawn at the same scale at every moment, and exploration and dialogue SHALL keep their existing standing positions.

#### Scenario: Every active foe stands
- **WHEN** a combat snapshot commits one, three, five, eight and fifteen foes that have not fled, some of them knocked out or defeated, with a solo player at 1451x790
- **THEN** exactly that many foe stage actors render, in presenter order, at the formation's boxes (±1px), and no foe is left to another surface

#### Scenario: Both sides are drawn at one scale
- **WHEN** combat renders at 1451x790 and at 1600x900 for parties of one, three and five figures against one, four, eight and the maximum (16 minus the party count) foes, and again while a foe joins, while one leaves, and during the entry into combat
- **THEN** every rendered figure box on both sides has the same height (±1px) as every other in the same frame, sampled at the start, the middle and the end of each transition

#### Scenario: The dead-centre gap stays clear
- **WHEN** combat renders any of those cases, including at the farthest point of every beat gesture
- **THEN** no figure box intersects the band from `stage centre − 132px × S` to `stage centre + 132px × S` (the card's columns) at any moment, and none intersects the band from `stage centre − 148px × S` to `stage centre + 148px × S` at rest

#### Scenario: The party forms up only in combat
- **WHEN** the committed mode changes exploration → combat → exploration with a five-figure party, and exploration → dialogue
- **THEN** in combat the party stands at the formation's boxes; on the return to exploration, and in dialogue, every party figure stands where the exploration line-up places it today (±1px)

#### Scenario: Entering and leaving combat moves figures with the motion level
- **WHEN** the mode live-changes into and out of combat at `full`, at `reduced`, and at `off`, and when the client reloads or reconnects in combat
- **THEN** at `full` each party figure glides and scales from its exploration box to its formation box (and back) over the actor duration times the travel factor, with the foes entering as the flash releases at the formation scale; at `reduced` the figures take their final boxes in the commit's frame and only fade where they enter or leave; at `off`, and on a reload or reconnect, every figure renders at its final box in the commit's frame

#### Scenario: A changing roster re-forms the line together
- **WHEN** a foe joins or flees during combat so that the shared scale or the rank count changes
- **THEN** every figure on both sides glides to its new box and scale with the same duration and easing in the same frames (instant below `full`), and the leaving foe fades where it stands

#### Scenario: Resizing keeps the formation and its pointer targets live
- **WHEN** the viewport is resized from 1451x790 to 1600x900 and back while combat is shown
- **THEN** the formation is recomputed from the new stage geometry within one frame of the resize, every figure box, plate and pointer target matches the new formation, and a pointer action on a figure's target or a plate works at once after the resize

#### Scenario: The formation is decorative art
- **WHEN** the formation renders
- **THEN** its figures are hidden from assistive technology, carry no focusable element, and intercept no pointer events outside the interactions other requirements define

### Requirement: Combat figures carry glance plates
While the formation is shown, each drawn combat figure other than the controlled figure SHALL carry one plate in its formation plate slot, in the stage's `plates` layer, showing at a glance the participant's name, a thin hit-point stroke and a tabular hit-point readout, with a third line reserved for condition glyphs; the controlled figure's vitals stay in the vitals dock. A plate SHALL NOT overlap another plate, the command card, the vitals dock or the top band.

#### Scenario: A full plate reads name, stroke and numbers
- **WHEN** a companion at 42 of 120 hit points and a foe at 18 of 30 stand in a formation with `full` plate slots
- **THEN** each 112px × S by 52px × S plate shows on its first line the display name in the serif small text (ellipsized within the plate, the full name kept in the DOM and in its accessible name), on its second line a 4px × S tapered stroke filled to the current fraction followed by the readout `42` / `120` and `18` / `30` with the current value bright and `/ maximum` receding in tabular figures, and keeps its third line empty for condition glyphs

#### Scenario: A compact plate keeps the stroke and the number
- **WHEN** the formation returns `compact` plate slots
- **THEN** each 72px × S by 36px × S plate hides the name visually (the name stays its accessible name), shows on its first line the stroke (at least 30px × S long) and the current hit points, and keeps its second line for a condition glyph

#### Scenario: Plates never collide
- **WHEN** combat renders for every party count 1–5 against foe counts 1, 3, 7, 8 and 16 minus the party count at 1451x790 and 1600x900
- **THEN** every plate lies inside its slot (±1px), no two plates intersect, and no plate intersects the command card's column, the vitals dock or the top band

#### Scenario: Plates follow playback
- **WHEN** a combat round plays damage beats on a foe and on a companion
- **THEN** each plate's stroke and readout show the displayed value the beat publishes (`displayHp`) and settle to the committed value when the round ends, so the plate never shows a later value than the beat's page

#### Scenario: The plates layer is outside the portrait anchors
- **WHEN** the formation renders
- **THEN** the plates render in the stage's `plates` layer above the portrait anchors and below the HUD islands, the band and the command card, the layer holds only the plates, carries no focusable element in this requirement, and outside combat renders nothing

#### Scenario: Repeated names carry their session token
- **WHEN** three foes share the display name 哥布林 and a fourth is named 狼
- **THEN** each 哥布林 plate shows its session token after the name (`哥布林 e1`, `哥布林 e2`, `哥布林 e3`) and the 狼 plate shows no token; a token is shown only while two drawn participants share a name

#### Scenario: Fallen figures show their state on the plate
- **WHEN** a foe is defeated and a companion is down
- **THEN** their plates keep their names and show `✕ 已擊破` and `▼ 倒地` in place of the readout, with an empty dashed stroke, in both plate forms (the compact form keeps the glyph and the word)

### Requirement: Combat beats are choreographed on the stage at the motion level
While a combat round plays by itself, as `webclient-combat-menu` "A combat round plays beat by beat" defines, each beat SHALL play one stage gesture once its page is fully shown, on the stage actors that the beat names and that stand on the stage (the player in `actor-left`, a foe in the foe line-up), taking every duration and distance from the client's motion tokens.

#### Scenario: Each beat kind plays its gesture
- **WHEN** a beat's page is fully shown
- **THEN** the first beat of each action: the acting stage actor steps 12px × S toward the stage's centre and back within 240ms, staying inside its 16px × S gutter beside the command card; `damage`: the target's stage actor shakes 6px from side to side for 180ms with a brief flash, a decorative number naming the damage rises from it and fades over 600ms, and its displayed hit points move to the beat's `hp_after` as the gesture starts, in the vitals or on the figure's plate, with the trailing bar following; `target_defeated`: a foe's stage actor collapses into the defeated look that "Fallen combat figures read as defeated or down at a glance" defines and keeps its slot — the player's stage actor never leaves the stage; `roll` and `other`: no gesture

#### Scenario: Pauses and actorless beats follow the gesture
- **WHEN** a gesture finishes, or a beat names a participant with no stage actor (a party member other than the player, or a foe beyond the third)
- **THEN** the next beat's pause starts when the gesture has played, and an actorless beat plays no gesture

#### Scenario: Choreography is decorative
- **WHEN** gestures, rising numbers, or flashes play
- **THEN** they are absent from the accessibility tree, never intercept a pointer, and are never the only carrier of any value, which the beat's page and the numerals already state

#### Scenario: The round that ends the fight holds decoration only
- **WHEN** the round's publication has already committed a mode other than `combat`, and later the round ends — by itself or because the player ended it
- **THEN** while the round plays the combat veil stays at its combat opacity and the foe line-up stays on the stage, inert; when it ends the veil fades out and the line-up leaves as a live change out of combat does; and the mode attribute, every mode-gated surface, the command region's content, focus, and the accessibility tree follow the committed mode at the commit, with the committed flash and flip playing at the commit as "Mode changes transition at the motion level" defines

#### Scenario: Reduced and off release the stage
- **WHEN** beats play at `reduced`, and at `off`
- **THEN** at `reduced` no step, shake, flash, rise, or drop moves or brightens anything, a defeated foe takes its defeated look without travel, its tone and mark fading within 150ms, and the pauses are kept; at `off` no round plays by itself, so no gesture and no stage hold occur

#### Scenario: The actor steps and the target reacts
- **WHEN** the effective level is `full` and a playing round shows the player's roll beat and then its
  damage beat on a foe on the stage
- **THEN** the player's stage actor plays one 240ms step toward the centre on the roll beat, and on the
  damage beat the foe's stage actor plays one 180ms shake with a flash, a number naming the damage rises
  from it over 600ms, and the foe's plate stroke and readout move to the beat's `hp_after`

#### Scenario: The trailing bar follows 300ms later
- **WHEN** the effective level is `full` and a damage beat lowers the player's displayed hit points
- **THEN** the vitals fill moves at once and the trailing bar starts following 300ms later

#### Scenario: A defeated foe drops out on its own beat
- **WHEN** the effective level is `full` and a playing round's defeat beat names a foe on the stage
- **THEN** that foe stays as it was until the defeat beat plays, then collapses into its defeated look in
  its slot and stays on the stage

#### Scenario: The round that ends the fight plays in front of the combat stage
- **WHEN** the effective level is `reduced` and an accepted attack defeats the last foe, committing mode
  `exploration`
- **THEN** in the commit's frame the stage's mode attribute is `exploration` and the minimap is visible,
  while the combat veil keeps its combat opacity and the foe line-up stays on the stage, inert, until the
  round's beats have played, after which the veil fades out and the line-up leaves

#### Scenario: Ending the round releases the stage
- **WHEN** a round that ended the fight is playing and the player clicks the message window
- **THEN** the veil starts fading out and the foe line-up leaves at once

#### Scenario: Reduced keeps the rhythm without motion
- **WHEN** the effective level is `reduced` and a round with a roll, a damage, and a defeat beat plays
- **THEN** no stage actor translates, shakes, or brightens, no number rises, the defeated foe takes its look
  without travel within 150ms, and each beat still follows the 400ms pause

#### Scenario: Off plays no gesture and holds nothing
- **WHEN** the effective level is `off` and an accepted attack defeats the last foe
- **THEN** no gesture plays, the combat veil and the foe line-up are gone in the commit's frame, and the
  round's beats are read as text pages

### Requirement: Surface visibility is gated by the committed game mode
The shell SHALL expose the committed mode on the stage root as `data-elosern-mode`, and surface visibility SHALL be derived from that single attribute. A surface hidden for the current mode SHALL be removed from rendering with `display:none` — never dimmed, never merely visually hidden — so it leaves the accessibility tree and the tab order, excepting only the two hold states defined in the scenarios below. The matrix SHALL be:

```text
| Surface | exploration | combat | dialogue | creation |
|---|---|---|---|---|
| place card (location, world time; `map` anchor, above the minimap) | visible | **hidden** (the formation needs the right column) | **hidden** | hidden |
| message window (band message region) | visible | visible | visible (whole band width, paged, name plate) | hidden |
| dialogue choice list (`choices` anchor, centred over the stage) | not rendered | not rendered | once the current response's last page is fully shown, while no action is in flight | not rendered |
| vitals dock (condition icons + vitals bars; `vitals` anchor, lower-left) | by the vitals rule | visible | **hidden** | hidden |
| minimap island | visible | **hidden** | **hidden** | hidden |
| objective line (under the minimap) | visible | hidden | hidden | hidden |
| controlled character and companion standing portraits (`actor-left`) | visible | visible (in the combat formation) | visible (listeners dimmed while the host speaks; the party line stays) | hidden |
| dialogue host standing portrait (`actor-right`) | not rendered | not rendered | while the `dialogue` panel is available (dimmed while the player speaks) | not rendered |
| foe line-up (`actor-right`, every foe that has not fled, up to 15, in the combat formation; fallen foes in their defeated look) | only while a round that ended the fight still plays (held, inert) | while at least one foe is active | not rendered | not rendered |
| figure plates (`plates` layer, one per drawn non-controlled combat figure) | only while a round that ended the fight still plays (held, inert) | visible | not rendered | not rendered |
| action dock (band command region) | visible | visible | **hidden** (command region collapsed: inert at commit, slides out, then `visibility: hidden`) | visible (creation form, full band width) |
| command-line toggle (⌨, message region's bottom-right) | visible | visible | visible | hidden |
| log control (日誌, beside the command-line toggle) | visible | visible | visible | hidden |
| command line (row on the message region's top edge) | while expanded | while expanded | while expanded | hidden |
| scene backdrop | visible (exploration stage; the combat stage while a round that ended the fight still plays) | visible (combat stage) | visible (unchanged art) | visible |
```

#### Scenario: The minimap disappears in combat
- **WHEN** the committed mode changes from exploration to combat
- **THEN** the minimap island is absent from the DOM layout and from the tab order, and it is not merely dimmed, while the `map` anchor renders nothing, every active foe stands in the combat formation, and each non-controlled figure carries its plate

#### Scenario: The place card stays visible through combat
- **WHEN** the committed mode changes from exploration to combat with a committed location and world time
- **THEN** the place card keeps its committed location and time but is not rendered (`display:none`) while the mode is combat, because the combat formation uses the stage's right column, and it renders again above the minimap island when the mode returns to exploration

#### Scenario: The minimap returns on leaving combat
- **WHEN** the committed mode changes from combat back to exploration, including by a round whose beats
  are still playing
- **THEN** the minimap island renders again with the committed `local_map` payload at the commit, and any
  held foe line-up or veil is inert and outside the accessibility tree

#### Scenario: A held round keeps the combat backdrop
- **WHEN** the committed art panel carries no usable scene image, a round that ends the fight by a flee
  commits mode `exploration` while its beats still play, and later the round ends
- **THEN** during the hold the scene backdrop keeps the combat gradient and the combat sample wash
  behind the held foe line-up and veil, and only when the hold ends does it return to the exploration
  stage, crossfading over the scene duration at `full` and switching in one frame at `off`

#### Scenario: Focus is rescued before its surface is hidden
- **WHEN** the focused element belongs to a surface that the incoming mode hides, including the exit compass, a place-card room action, the 建議 pill, or a person's verb card or a room card when the incoming mode is dialogue
- **THEN** focus is moved to the incoming mode's focus home before the surface is removed, and no focus is lost to the document body

#### Scenario: Creation mode presents only the creation surfaces
- **WHEN** the committed mode is creation
- **THEN** the place card, the message window, the command-line toggle, the log control, the `vitals` and `map` anchors with every island in them, the player and companion standing portraits, and the command line are absent, and the action dock renders the creation form across the whole bottom band

#### Scenario: Dialogue mode keeps the cockpit visible
- **WHEN** the committed mode changes from exploration to dialogue with an available `dialogue` panel
- **THEN** the message window spans the whole band with the host's name plate, the dialogue host's standing portrait is rendered in `actor-right`, the player's front figure and the companion standing portraits remain rendered in `actor-left` dimmed as listeners, the command-line toggle and the log control remain rendered, the command line keeps its expanded or collapsed state, the action dock is out of the accessibility tree and the tab order together with the band's command region from the commit and is `visibility: hidden` once the region's slide ends, and the `#action-dock` element is not removed from the document

#### Scenario: Dialogue mode hides the cockpit and navigation islands
- **WHEN** the committed mode changes from exploration to dialogue with a committed location, a committed `local_map` panel, and a vital below its maximum
- **THEN** the place card, the minimap island, the objective line, and the vitals dock are absent from the accessibility tree and the tab order, and once each surface's exit transition has finished it is `display:none`

#### Scenario: A vital change during dialogue does not reveal the dock
- **WHEN** the committed mode is dialogue with the dock hidden and a committed revision lowers `hp` below its maximum
- **THEN** the vitals dock stays `display:none`, no reveal transition plays, and the numerals are not visible anywhere on the stage

#### Scenario: Returning from dialogue restores the hidden surfaces
- **WHEN** the committed mode changes from dialogue back to exploration with a vital below its maximum
- **THEN** the place card and the minimap island render again at the commit, and the vitals dock enters through its reveal transition because the vitals rule holds

#### Scenario: Dialogue backdrop keeps its committed art
- **WHEN** the committed mode is dialogue
- **THEN** the scene backdrop renders the same committed exploration art as before the mode
  change, unmodified

#### Scenario: The objective line shows only in exploration
- **WHEN** a non-empty committed `objectives` panel stays committed while the mode changes from exploration to combat, then to dialogue, then back to exploration
- **THEN** the objective line renders in exploration, is hidden with `display:none` in combat and in dialogue, and renders again on the return to exploration

#### Scenario: The command line starts collapsed in every playing mode
- **WHEN** the shell mounts in exploration mode, and later the committed mode changes to combat and then to dialogue without the player opening the command line
- **THEN** in each mode the command-line toggle is rendered with `aria-expanded="false"`, the command-line row is hidden with `display:none`, and the input field is outside the tab order

#### Scenario: Entering creation collapses an expanded command line
- **WHEN** the command line is expanded with focus in its field and the committed mode changes to creation, and later back to exploration
- **THEN** focus moves to the action dock before the row is hidden, and on the return to exploration the command line is collapsed

#### Scenario: The command region animates out in dialogue
- **WHEN** the committed mode changes to `dialogue`
- **THEN** the band's command region is the one exception to `display:none` hiding: it animates out as "The command region collapses in dialogue mode and the message window spans the band" defines — it leaves the accessibility tree, the tab order, and pointer hit-testing at the commit, and is `visibility: hidden` once its slide ends

#### Scenario: The combat stage hold is the second exception
- **WHEN** a round whose publication already committed another mode still plays, as "Combat beats are choreographed on the stage at the motion level" defines
- **THEN** the decorative combat veil and the foe line-up MAY remain on the stage, outside the accessibility tree, the tab order, and pointer hit-testing, and the scene backdrop SHALL keep presenting the combat stage (its combat gradient and, where a bundled sample wash accompanies a degraded scene, the combat sample) until the round ends, while every other surface follows the committed mode at the commit

#### Scenario: Dialogue exits settle to display:none
- **WHEN** the mode commits to `dialogue`, and separately when the client mounts, reconnects, runs at motion-off, or lacks discrete display transitions
- **THEN** dialogue's `vitals` and `map` anchors MAY retain exit paint over the existing reveal duration while inert, outside the accessibility tree and pointer hit-testing from commit, and settle at `display:none`; in the mount, reconnect, motion-off, and no-discrete-transition cases they are hidden immediately

#### Scenario: Dialogue focus is carried off the backdrop
- **WHEN** the committed mode is `dialogue`
- **THEN** the scene backdrop keeps rendering its committed exploration art truthfully — the dialogue's focus is carried by the stage actors, the name plate, and the message window, and the choice list, not by mutating the backdrop

#### Scenario: Data-rule cells hide like mode-hidden surfaces
- **WHEN** a matrix cell names a data rule instead of `visible`, such as the command line's `while expanded` cell
- **THEN** the surface is shown in that mode only while its own requirement's rule holds for the committed state, and is otherwise hidden the same way (`display:none`, or not rendered at all where that requirement says so); the command line's own requirement defines when the row is expanded, and a collapsed row is hidden with `display:none` exactly like a mode-hidden surface

#### Scenario: Per-surface requirements stay consistent with the matrix
- **WHEN** a per-surface requirement names its own visible-mode set
- **THEN** it stays consistent with this matrix; the place card's visibility follows the matrix exactly — shown in exploration, hidden in combat, dialogue and creation — hiding the `map` anchor in dialogue hides the place card with the minimap, and the card's own visibility rule SHALL NOT claim dialogue after this change

#### Scenario: The mode gate outranks the dock's data rule
- **WHEN** the committed mode is `dialogue` and a committed revision drops a vital below its maximum or adds a new condition
- **THEN** the vitals dock stays hidden through the mode gate regardless of its data rule, its reveal transition does not play until the mode leaves dialogue — the dialogue's attention surface is the message window and the name plate, and the dock returns through its normal reveal when the mode commits back to exploration or combat — while the low-HP stage vignette, not mode-gated, keeps rendering in dialogue so a critical HP state is still conveyed through the stage frame

#### Scenario: Every playing mode names one focus home
- **WHEN** a mode change, a committed revision that turns a surface's data rule false, or a collapse of the command line hides the surface that currently holds focus
- **THEN** the shell moves focus to the focus home of the mode being entered or kept before the surface is removed, using the existing focus-restore path — the action dock in exploration, combat, and creation mode, and the message window's focus target in dialogue mode, as "The command region collapses in dialogue mode and the message window spans the band" defines — and a mode change into creation also collapses the command line, so leaving creation never reveals an expanded row

#### Scenario: The visibility matrix carries its amendments
- **WHEN** the `place-card-relocation` (place card in the `map` anchor), `vitals-bar-redesign` (the vitals dock at the lower left), and `companion-portrait-lineup` (the party quickbar row removed, the portrait row naming the companion line) amendments apply to this requirement
- **THEN** dialogue mode hides the cockpit and navigation surfaces: the place card, the minimap island, and the vitals dock are hidden while the committed mode is `dialogue`
