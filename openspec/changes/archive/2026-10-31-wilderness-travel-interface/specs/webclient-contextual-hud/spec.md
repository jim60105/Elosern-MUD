## MODIFIED Requirements

### Requirement: Stage actors present the player and the dialogue host with a speaking state
Outside active travel presentation, standing portraits SHALL retain their current actor, companion-lineup and single dialogue-host speaking behavior; travel presentation SHALL keep both actor anchors empty and represent present members through medallions.

#### Scenario: The host actor presents its catalog entry truthfully
- **WHEN** a non-party host's stage actor renders in `actor-right`
- **THEN** it presents the committed `art` panel's `portrait_catalog` entry named by `dialogue.host.portrait_ref` , the complete image bottom-aligned with contain fit, and a grounded silhouette with host identity and authoritative availability when the entry is a placeholder; when `portrait_ref` is null or names no catalog entry it renders the truthful placeholder: the display name's initial and display name, never a stock or guessed image; and the client constructs no catalog key from host identity or any other field

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
- **THEN** the dim is not the only speaking cue , the name plate names the current explicit speaker (none for narration) and each actor exposes its speaking data attribute; actors remain decorative, with no focusable element; motion owns transitions; and no other dialogue behavior changes: the name plate, pagination, choices, focus, keyboard paths and non-party host mode-transition motion retain their contracts

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
- **WHEN** ordinary non-travel exploration is followed by combat with two active foes
- **THEN** the controlled figure is lit in both and both foes are lit in combat; companions retain their listener dim, and actor-right carries no exploration actor

#### Scenario: A companion host is not duplicated on the opposite anchor
- **WHEN** dialogue host identity joins to a committed party or controlled lineup figure
- **THEN** that identity has exactly one standing figure in actor-left, actor-right has no duplicate host, and the name plate, pagination and focus retain their existing behavior

#### Scenario: Consecutive actor and host lines
- **WHEN** a complete scene has actor speech followed by two host lines and narration
- **THEN** speaker emphasis changes with each line, both host lines remain separately advanceable and narration removes emphasis

#### Scenario: Travel and ordinary layout switch
- **WHEN** a committed wilderness exploration presentation enters or leaves travel
- **THEN** travel uses medallions with empty actor anchors and vitals above them; ordinary dialogue/combat/settlement composition restores without duplicated figures

### Requirement: Companion standing portraits line up behind the controlled character in the actor-left anchor
Outside active travel presentation, the party SHALL retain its existing controlled-front standing lineup, committed companion order and combat formation; active travel presentation SHALL replace that lineup with present-member medallions below the existing vitals island.

#### Scenario: Portraits resolve through the catalog
- **WHEN** a companion portrait renders
- **THEN** it resolves from `portrait_ref` through `art.portrait_catalog`, falling back to its display name's initial-letter placeholder when null or unresolved

#### Scenario: Every figure shares one size and ground line
- **WHEN** the lineup renders any number of figures
- **THEN** every figure, including the controlled character, has the same full anchor size and ground line; no progressively smaller scale, lift ramp or depth dimming

#### Scenario: The row compresses to stay in the left half
- **WHEN** the row renders at 1451x790, 1741x948 and 2560x1440, in ordinary exploration and dialogue
- **THEN** horizontal overlap compresses as necessary to keep the row inside the stage's left half, preserving a scaled left gutter; a multi-figure group MAY shift horizontally within that half; in dialogue the group compresses overlap to clear the choice list without resizing figures; zero companions render the existing solo portrait at its standard anchor position; the anchor has `overflow: visible`; and the vitals dock MAY cover the lowest strip of feet, never face or torso

#### Scenario: Visibility follows the mode
- **WHEN** the committed mode is exploration, combat, dialogue, or creation
- **THEN** the lineup is visible in ordinary exploration, combat and dialogue, hidden in creation and active travel; medallions replace it only in travel

#### Scenario: A speaking companion rises in z only
- **WHEN** a non-controlled rendered companion is the active host speaker in dialogue mode or the selected surviving exploration verb-card target, and when that speaking/focus changes or ends
- **THEN** companions use the existing StageActor listener dim otherwise; the speaking companion temporarily receives z above every baseline figure, returning to its exact baseline z when speaking changes or ends, including across possession swaps and lineup count changes; dialogue speaking and exploration focus change only dim and z, never position, lift or size, and remains correct at off/reduced motion; and the controlled figure retains its existing speaking and beat behavior

#### Scenario: No figure crosses the stage's centre
- **WHEN** the lineup and the foe lineup render together in combat
- **THEN** no figure box enters the dead-centre gap of "Combat figures stand in a shared-scale formation", and both sides are drawn at the same scale

#### Scenario: A two-companion party renders a three-figure group
- **WHEN** the committed `party` panel carries two resolved-portrait slots at 1451x790 in ordinary non-travel exploration mode
- **THEN** three equally sized figures share a ground line, the player is rightmost with highest baseline z, the companions overlap leftward in party order, no box crosses the horizontal centre and no figure is focusable

#### Scenario: A zero-companion party renders only the player
- **WHEN** the committed `party` panel is available with an empty `slots` list
- **THEN** the `actor-left` anchor renders the player's solo portrait at the standard standing position, byte-stable with the solo layout before this change

#### Scenario: A companion with no portrait shows the initial letter
- **WHEN** a party slot carries `portrait_ref: null` for display name `蕾娜`
- **THEN** that figure renders the initial `蕾` through the stage actor's truthful placeholder, with no invented image or constructed URL

#### Scenario: The full party fits the left half at every viewport
- **WHEN** the committed party carries four slots and the shell renders at 1451x790 and at 2560x1440
- **THEN** all five equally sized figures render with compressed horizontal overlap inside the left half in exploration, each face at least partially visible; in combat they stand in the formation at the shared scale; and in dialogue a speaking companion is brought above the overlapping listeners without moving its slot

#### Scenario: A speaking companion rises temporarily without moving
- **WHEN** the committed dialogue host is a companion and the existing speaker signal changes from player to host and back
- **THEN** that companion changes from dim baseline z to lit highest z and back, preserving its exact geometry; possession swaps, lineup changes and off motion cannot retain stale speaking z

#### Scenario: The companion line and the foe line-up do not overlap
- **WHEN** the committed mode is combat with two companions and three active foes at 1451x790
- **THEN** no companion figure's rendered box intersects any foe figure's rendered box

#### Scenario: Exploration reuses companion emphasis
- **WHEN** a verb card opens for a non-controlled rendered companion while another companion and the controlled figure are present
- **THEN** only the selected companion gains the existing highest focus z and loses listener dim; the other companion keeps baseline/listener dim and the controlled figure keeps its independent dim/beat behavior, without position, size or ground-line changes

#### Scenario: Exploration closure restores current baselines
- **WHEN** that card closes through back, look-close, departure, movement or invalidation, including after lineup count changes
- **THEN** the surviving non-controlled figures use the current geometry's exact baseline z and listener dim with no remembered focus z, at full, reduced and off motion

#### Scenario: Possession preserves the controlled role during focus
- **WHEN** possession/release swaps the front figure while an exploration card is open
- **THEN** identity joins use the current rendered figures, a selected non-controlled companion can be emphasized at its current slot, and the controlled front never receives companion-listener elevation or loses its existing beat/dim semantics

#### Scenario: The party takes the listener dim during the stage target step
- **WHEN** the stage target step is active for a skill whose candidates include the controlled figure and one companion, with the focus on that companion
- **THEN** that companion's stage actor is lit (`data-speaking="true"`) and every other party figure, the controlled figure included, carries the listener dim; no figure moves, lifts, resizes or changes z for the step, and when the step ends every figure returns to the state it had before the step (in combat the controlled figure undimmed and the companions in their existing listener dim)

#### Scenario: Travel and ordinary layout switch
- **WHEN** a committed wilderness exploration presentation enters or leaves travel
- **THEN** travel uses medallions with empty actor anchors and vitals above them; ordinary dialogue/combat/settlement composition restores without duplicated figures

### Requirement: The vitals dock stands at the stage's lower-left above the band
The vitals dock SHALL retain its bounded lower-left placement above the band and existing conditional visibility; during travel it SHALL occupy the same column above party medallions, with their combined content bounded away from other interactive anchors.

#### Scenario: The dock's width stays viewport-relative
- **WHEN** the dock's width resolves at any viewport
- **THEN** it is a viewport-relative width, not multiplied by the chrome factor

#### Scenario: The dock never claims the upper-left corner
- **WHEN** the left column renders
- **THEN** the dock is not top-anchored and claims no stage upper-left corner: at the top of the left column the stage shows only the standing portrait line, and the condition icon row is the dock's topmost content, directly above the bars

#### Scenario: The dock may overlap the portraits' feet
- **WHEN** the dock and the `actor-left` standing portraits render together
- **THEN** the dock MAY overlap the lowest strip of the portraits (the party line's feet); the portraits keep their full standing height and the dock paints above them

#### Scenario: The dock is feathered ink on a brass spine, not a box
- **WHEN** the dock's chrome renders
- **THEN** it does not read as a rectangular box: its ground is the shared panel ink with the backdrop blur, feathered out towards its right and top edges so the scene reads through them; it is mounted on a hairline brass spine down its left side capped by the band's lozenge ornament, with a hairline brass crown fading out along its top; it carries no full border and no square corners; and every island chrome it carries comes from the shared design tokens

#### Scenario: The command line starts past the dock
- **WHEN** the command-line row docks on the same band edge
- **THEN** it begins past the dock's right edge, so the two never intersect

#### Scenario: The interim quickbar holds its place until removed
- **WHEN** the dock renders before `companion-portrait-lineup` removes the interim party quickbar
- **THEN** the quickbar island stands in the `vitals` anchor between the dock and the band

#### Scenario: The dock stands on the band's edge
- **WHEN** the shell renders in ordinary non-travel exploration mode with the vitals dock visible at 1451x790
- **THEN** the `vitals` anchor's bottom edge coincides with the bottom band's top edge (the dock's own bottom edge does too whenever no interim party quickbar stands below it), the dock's left edge sits at the stage's left gutter and its width is a quarter of the viewport's width (±1.5px), its rendered height is the compact height of the icon row, the readout, and the three lines, and the stage's upper-left corner holds no vitals surface

#### Scenario: The dock covers only the portraits' lowest strip
- **WHEN** the dock is visible and the player's standing portrait renders at 1451x790 and at 2560x1440
- **THEN** the overlap of the two rendered boxes reaches no higher than the portrait's lowest quarter, the portrait's face and torso are fully visible, and neither box moves the other

#### Scenario: The dock stays bounded at the minimum viewport
- **WHEN** the shell renders at 1451x790 with the dock visible and conditions overflowing the row
- **THEN** the dock's box stays inside the left gutter between the top band and the band's top edge, its content scrolls within that bound, and it intersects no other interactive anchor's content

#### Scenario: Travel and ordinary layout switch
- **WHEN** a committed wilderness exploration presentation enters or leaves travel
- **THEN** travel uses medallions with empty actor anchors and vitals above them; ordinary dialogue/combat/settlement composition restores without duplicated figures
