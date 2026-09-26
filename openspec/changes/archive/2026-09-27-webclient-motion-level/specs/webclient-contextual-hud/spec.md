## MODIFIED Requirements

### Requirement: Narrative prose scale is a client-local preference the settings surface owns
The client SHALL expose a narrative prose scale with three steps, selectable from the settings surface,
whose current step is marked by an indicator that does not rely on colour alone. The scale SHALL apply
to narrative and dialogue prose only — the message window's page text, the complete-log surface's lines
and the prompt line — and SHALL NOT alter HUD, dock, drawer, overlay or any other interface text, so the
stage's measured anchor geometry is unaffected at either supported viewport.

The prose scale and every other setting the surface offers SHALL be client-local presentation state. No
settings control SHALL dispatch an action: the client's action allowlist carries exactly one `options.*`
action, the suggestions dismissal, and this capability adds none. Each setting SHALL be applied
immediately to the presentation it governs — the document's presentation tokens for the prose scale,
the motion level, the text-to-HTML toggle and the colourblind palette, and the message window for the
reading preferences and the motion level — and SHALL be persisted through the client's versioned,
presentation-only browser store as a harmless display preference. Each setting SHALL be re-applied at
load, and SHALL be reset to its default — fully applied, never half-applied — whenever that store
resets. The motion level SHALL follow "The motion level is a client-local preference that governs every
client animation": a stored level overrides the operating system's reduced-motion preference, which
SHALL continue to apply while no level is stored.

The settings surface SHALL offer no control it does not implement.

#### Scenario: The prose scale moves prose and nothing else
- **WHEN** the player selects the largest prose scale
- **THEN** the message window's page text, the complete-log surface's lines and the prompt line render larger, every HUD, dock and overlay label is unchanged, and no stage anchor's rendered box intersects another's at 1440x900 or 1280x720

#### Scenario: No setting dispatches an action
- **WHEN** the player changes every control the settings surface offers
- **THEN** no `ui_action` is sent for any of them, and the only `options.*` action the client can dispatch remains the suggestions dismissal

#### Scenario: A setting survives a reload and resets cleanly
- **WHEN** the player changes the prose scale, the text speed, and the motion level, reloads the client, and then the presentation store's stored version is unrecognised
- **THEN** the chosen scale, text speed, and motion level are re-applied after the reload, and after the reset every setting is applied at its default, the motion level following the operating system again, with no setting left partly applied

#### Scenario: Reduced motion overrides, and defers when unset
- **WHEN** no motion level is stored and the operating system requests reduced motion
- **THEN** the effective motion level is `reduced`, so looping and travelling motion stops and message pages appear in full at once; and when the player then selects `完整`, the client honours that stored level over the operating system

#### Scenario: The surface offers nothing inert
- **WHEN** the settings surface's controls are enumerated
- **THEN** every control changes an outcome the client actually implements, and no control is rendered that has no effect

### Requirement: Text speed and auto-advance are client-local reading preferences the settings surface owns
The settings surface's reading section SHALL offer a text-speed control with the four steps `慢`
(`slow`), `標準` (`normal`), `快` (`fast`), and `瞬間` (`instant`), and an auto-advance toggle
(`自動翻頁`). The text speed SHALL default to `normal` and auto-advance SHALL default to off. The
current text-speed step SHALL be marked by an indicator that does not rely on colour alone, and SHALL
be exposed as the pressed state of its button. The text-speed control SHALL say that the `減少` and
`關閉` motion levels show pages at once, because an effective motion level other than `full`
overrides the chosen speed as `webclient-input-narrative` defines. Both preferences SHALL follow the
settings rules of "Narrative prose scale is a client-local preference the settings surface owns":
client-local, dispatching nothing, applied to the message window immediately, persisted through the
versioned presentation-only browser store, re-applied at load, and reset to their defaults when that
store resets. A stored value outside the defined steps SHALL be discarded, and the default SHALL
apply.

#### Scenario: Choosing a text speed applies and persists it
- **WHEN** the player opens the settings surface and selects `快`
- **THEN** the `快` button is pressed and marked by a non-colour indicator, the next page the
  message window shows types at the fast speed, the stored wrapper carries `textSpeed: "fast"`, and
  no `ui_action` is sent

#### Scenario: Auto-advance is off until the player turns it on
- **WHEN** the client loads with no stored preferences, and the player then turns on `自動翻頁`
  and reloads
- **THEN** auto-advance is off on the first load, and after the reload the toggle is on and a fully
  shown page with a next page advances on its own

#### Scenario: An invalid stored speed falls back to the default
- **WHEN** the stored wrapper carries a text speed outside the four steps
- **THEN** the client loads with the `normal` speed, and the other stored preferences still apply

## ADDED Requirements

### Requirement: The motion level is a client-local preference that governs every client animation
The client SHALL have exactly three motion levels: `full`, `reduced`, and `off`. The settings surface
SHALL offer them as one `動態效果` control with the three buttons `完整`, `減少`, and `關閉`. The pressed
button SHALL be the effective level, marked by an indicator that does not rely on colour alone. Selecting
a button SHALL store that level. The effective level SHALL be the stored level when one is stored.
While no level is stored, it SHALL be `reduced` when the operating system requests reduced motion and
`full` otherwise, and it SHALL follow a change of the operating system's preference without a reload.
A stored value that is not one of the three levels SHALL be discarded, as if nothing were stored.

The effective level SHALL be applied to the whole document at once, the moment it changes, and every
client animation and transition SHALL read it through the client's motion tokens:
- **`full`** plays every animation and transition the client defines.
- **`reduced`** plays no translation, no shake, no flash, and no looping animation (pulses, blinking,
  spinners). The stage and mode transitions the client defines play only as opacity fades of at most
  150ms. Every other transition, drawers and control feedback included, is instant. Message pages
  appear in full at once.
- **`off`** makes every visual change instant, fades included.

Every animation and transition duration, delay, and travel distance SHALL come from the client's motion
tokens. No component SHALL declare a literal duration. The motion level SHALL never withhold
information: at every level each transition ends in the same rendered state, and every state it
conveys is also conveyed without motion.

#### Scenario: The operating system is followed while nothing is stored
- **WHEN** the client loads with no stored motion level and the operating system requests reduced
  motion, and the operating system's preference then changes to no preference
- **THEN** the effective level is `reduced` and the `減少` button is pressed, and after the change the
  effective level is `full` and the `完整` button is pressed, with no reload and nothing stored

#### Scenario: A stored level overrides the operating system
- **WHEN** the operating system requests reduced motion and the player selects `完整`, then reloads
- **THEN** the effective level is `full` before and after the reload, the stored wrapper carries
  `motionLevel: "full"`, and no `ui_action` is sent

#### Scenario: Reduced keeps short fades and drops travel and loops
- **WHEN** the effective level is `reduced`
- **THEN** every stage and mode transition duration resolves to at most 150ms, every travel distance
  resolves to zero, no looping animation runs, drawers and control feedback change instantly, and
  message pages appear in full at once

#### Scenario: Off makes every change instant
- **WHEN** the effective level is `off`
- **THEN** every animation and transition duration and delay resolves to zero, including fades, and
  every committed change renders in its final state in the same frame

#### Scenario: No component hard-codes a duration
- **WHEN** the client's component styles are scanned for animation and transition declarations
- **THEN** every duration and delay they declare is a motion token, and none is a literal time

#### Scenario: Every level ends in the same state
- **WHEN** the same committed change renders at `full`, at `reduced`, and at `off`
- **THEN** once any transition has finished, the three renders carry the same content, the same
  accessibility tree, and the same focus

### Requirement: Presentation timing never gates committed state or input
The client SHALL apply every committed change to its state and to the document immediately; motion
SHALL only decide how the view moves between two committed states. A transition SHALL NOT delay a
committed value, a mode or visibility attribute, the accessibility tree, or the tab order beyond the
moment the change commits, and SHALL NOT delay the player's ability to act beyond its own duration at
the current motion level. A transition interrupted by a newer committed change SHALL run toward the
newer state, and SHALL NOT first finish the older one.

Presentation that plays in steps — message pages today, and combat beats when the client plays them —
SHALL follow three rules. Steps play in the order their data committed, and a step never reorders,
drops, or alters committed data. A player click or press that advances the presentation shows the
current step's end state at once. A new player action shows every queued non-combat step's end state
before its own response starts. Nothing is lost: every stepped text stays in the full log. Any duration
a stepped presentation waits for SHALL come from the motion tokens, and SHALL resolve to zero at `off`.

#### Scenario: A mode change commits before its transition ends
- **WHEN** the effective level is `full` and a committed revision changes the mode
- **THEN** the stage's mode attribute, the committed surfaces' accessibility state, and the store's
  view carry the new mode in the same frame as the commit, before any transition finishes

#### Scenario: Input is available within the transition's duration
- **WHEN** the effective level is `full` and the player opens a drawer or a new response starts
- **THEN** the drawer takes focus and the message window accepts Enter at once, without waiting for
  a transition to finish

#### Scenario: A click shows the step's end state and a new action flushes
- **WHEN** a page is typing and the player clicks the message window, and later acts while unread
  pages remain
- **THEN** the click shows the page in full at once, and the action shows the previous response's
  last page complete before the new response's first page starts, with every page still in the full
  log
