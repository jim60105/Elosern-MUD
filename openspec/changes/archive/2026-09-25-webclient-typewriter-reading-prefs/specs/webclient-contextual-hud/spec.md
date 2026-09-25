## MODIFIED Requirements

### Requirement: The message window presents the current response one page at a time in the band's message region
The narrative SHALL render as a message window that fills the bottom band's message region — the left
two thirds of the band, at the band's fixed height — drawn with the reference's caption panel
treatment: charcoal panel fill, a hairline border, shared radius and restrained shadow. The window
SHALL never grow into the stage and SHALL never change size with its content. Outside the dialogue
variant, the window SHALL present exactly one page of the current response at a time, paged as
`webclient-input-narrative` defines and revealed as its typing requirement defines, and SHALL NOT
present earlier responses: they remain readable in the full-log surface. Page text SHALL be set in the
serif reading face at 28px at the 1920x1080 reference size and the default prose scale, SHALL scale
with the viewport height and with the client's prose scale, and SHALL hold at most 42 CJK characters
per line.

The window's lower edge SHALL keep a control strip in which no page text renders. The strip SHALL
hold a page marker and, at its right end, a labelled `日誌` control beside the command-line toggle.
The page marker SHALL render only while the page on screen is fully shown, and SHALL be absent while
the page is typing. When rendered, it SHALL read `▼` while the current response has further pages and
`■` on its last page. It SHALL be decorative (hidden from assistive technology), and it SHALL blink
only through the client's motion tokens, so reduced motion stops the blink. An oversize page SHALL
scroll inside the window's text area; it SHALL never be truncated and SHALL never grow the window.

The `日誌` control SHALL open the full-log surface in one action. Scrolling up over a page that has
nothing left to scroll up SHALL also open it. The full-log surface's content, markup renderer, focus
trap, Escape close, focus restore to the opening control, and opening at its latest line are
unchanged. The window SHALL render no head row, no unread indicator, and no jump-to-latest control. In
creation mode the window, its marker, and the `日誌` control are hidden with the message region.

#### Scenario: The window keeps the message region's box
- **WHEN** the current response holds more text than one page and new lines keep arriving
- **THEN** the window keeps the message region's box — the band's height and two thirds of its
  width — and never expands into the stage

#### Scenario: One page of the current response is shown
- **WHEN** the log holds three responses and the latest one fills two pages
- **THEN** the window shows only the first page of the latest response, and no line of the two
  earlier responses is rendered in the window

#### Scenario: The page measure is bounded at the reference size
- **WHEN** the stage renders at 1920x1080 with the default prose scale and a long prose response
- **THEN** the page text's computed font size is 28px (±0.5px) and no rendered text line holds more
  than 42 CJK characters

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
the reduced-motion override, the text-to-HTML toggle and the colourblind palette, and the message
window for the reading preferences — and SHALL be persisted through the client's versioned,
presentation-only browser store as a harmless display preference. Each setting SHALL be re-applied at
load, and SHALL be reset to its default — fully applied, never half-applied — whenever that store
resets. The reduced-motion setting SHALL act as an override over the operating system's reduced-motion
preference, which SHALL continue to apply when no override is stored.

The settings surface SHALL offer no control it does not implement.

#### Scenario: The prose scale moves prose and nothing else
- **WHEN** the player selects the largest prose scale
- **THEN** the message window's page text, the complete-log surface's lines and the prompt line render larger, every HUD, dock and overlay label is unchanged, and no stage anchor's rendered box intersects another's at 1440x900 or 1280x720

#### Scenario: No setting dispatches an action
- **WHEN** the player changes every control the settings surface offers
- **THEN** no `ui_action` is sent for any of them, and the only `options.*` action the client can dispatch remains the suggestions dismissal

#### Scenario: A setting survives a reload and resets cleanly
- **WHEN** the player changes the prose scale and the text speed, reloads the client, and then the presentation store's stored version is unrecognised
- **THEN** the chosen scale and text speed are re-applied after the reload, and after the reset every setting is applied at its default with no setting left partly applied

#### Scenario: Reduced motion overrides, and defers when unset
- **WHEN** no reduced-motion override is stored and the operating system requests reduced motion
- **THEN** non-essential transitions are disabled and message pages appear in full at once; and when the player then sets the override off, the client honours the override

#### Scenario: The surface offers nothing inert
- **WHEN** the settings surface's controls are enumerated
- **THEN** every control changes an outcome the client actually implements, and no control is rendered that has no effect

## ADDED Requirements

### Requirement: Text speed and auto-advance are client-local reading preferences the settings surface owns
The settings surface's reading section SHALL offer a text-speed control with the four steps `慢`
(`slow`), `標準` (`normal`), `快` (`fast`), and `瞬間` (`instant`), and an auto-advance toggle
(`自動翻頁`). The text speed SHALL default to `normal` and auto-advance SHALL default to off. The
current text-speed step SHALL be marked by an indicator that does not rely on colour alone, and SHALL
be exposed as the pressed state of its button. The text-speed control SHALL say that reduced motion
shows pages at once, because the effective reduced-motion state overrides the chosen speed as
`webclient-input-narrative` defines. Both preferences SHALL follow the settings rules of "Narrative
prose scale is a client-local preference the settings surface owns": client-local, dispatching
nothing, applied to the message window immediately, persisted through the versioned presentation-only
browser store, re-applied at load, and reset to their defaults when that store resets. A stored value
outside the defined steps SHALL be discarded, and the default SHALL apply.

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
