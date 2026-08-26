## ADDED Requirements

### Requirement: The command line is a permanently present bar in the stage's command-line anchor
The client's text control SHALL render as a single bar filling the stage's `command-line` anchor,
containing — in this order — the mode's quick-word chips, a prompt chevron, the command input field, a
hint cluster, the command-history controls, and the overlay utility controls. In the modes this
capability's visibility matrix renders the command line (exploration and combat), the input field SHALL
be present in the DOM, visible and focusable without any opening action: there SHALL be no entry
control, no `aria-expanded` state and no closed state. No stored presentation state SHALL be able to
remove it. (The command line is intentionally absent from the layout in creation mode, per H1's
visibility matrix and design D10.)

The bar SHALL NOT overlap the action dock, the narrative caption or any HUD anchor at 1440x900 or
1280x720. When horizontal space is insufficient, the hint cluster SHALL be dropped first and the
quick-word chips SHALL scroll within their own cluster; the input field, the history controls and the
utility controls SHALL never be dropped, because they are the only pointer path to their behaviour.

#### Scenario: The field is usable without an opening action
- **WHEN** the shell mounts in exploration mode
- **THEN** the command input field is present in the DOM and focusable, no entry control is rendered, and no element in the bar reports an `aria-expanded` state

#### Scenario: The bar keeps its geometry at the minimum viewport
- **WHEN** the stage renders at 1280x720 with the full quick-word chip set
- **THEN** the bar's rendered box intersects no other stage anchor's box, and the input field, the history controls and the utility controls are all still rendered

#### Scenario: Constrained width drops the hint before any control
- **WHEN** the bar's content exceeds its available width
- **THEN** the hint cluster is removed first and the chip cluster scrolls within itself, and no input field, history control or utility control is removed

### Requirement: Quick-word chips prepare a command without submitting it
The command line SHALL render quick-word chips for the committed mode. Activating a chip SHALL write
its command text into the input field and move focus to the field, and SHALL NOT submit: a prepared
command SHALL still travel through the field's single send implementation, so exactly one send path
exists.

Each chip's visible label SHALL be the literal command verb it inserts, and every chip SHALL insert a
verb the server's installed command set actually accepts — a chip SHALL NOT offer a verb the parser
would reject. Chips SHALL carry no key-mnemonic badge unless this client binds that key. Chips that do
not apply to the committed mode SHALL be removed with `display:none` so they leave the accessibility
tree and the tab order, never dimmed.

#### Scenario: A chip prepares, it does not send
- **WHEN** the player activates a quick-word chip
- **THEN** the chip's command text plus a trailing space is written into the input field, focus moves to the field, and no text message and no `ui_action` is sent

#### Scenario: The chip set follows the mode
- **WHEN** the committed mode changes from exploration to combat
- **THEN** the exploration-only chips are absent from the DOM and from the tab order, and the combat chip set renders in their place

#### Scenario: No chip offers a verb the game does not have
- **WHEN** the rendered chip set is enumerated in any mode
- **THEN** every chip's inserted text is a command key or alias the server installs, and no chip advertises a key mnemonic that this client does not bind

### Requirement: The command line advertises only affordances this client implements
The hint cluster SHALL name only behaviour the client implements. It SHALL state the command-history
recall keys, and SHALL NOT state a completion affordance, because the client implements none.

The history controls SHALL be labelled controls that drive the same history-walk state the recall keys
drive — one walk reached by two input paths — and SHALL NOT submit. No surface of the command line
SHALL name a key, gesture or affordance that has no implementation behind it.

#### Scenario: The hint names history and nothing else
- **WHEN** the hint cluster renders
- **THEN** it states the command-history recall keys and states no completion affordance

#### Scenario: The history controls walk the same state as the keys
- **WHEN** the player activates the previous-entry control and then presses the history recall key
- **THEN** both move through the same command-history walk in the same order, the draft is preserved across the walk, and neither submits

### Requirement: A full-screen overlay is one focus-trapped surface, and only one is open at a time
A full-screen overlay SHALL render as one shared surface laid over the stage, carrying a header naming
the surface and a labelled close control, with its body as its only scrolling region. The surface is fixed
from the stage's 46px command-line height (`top:46px; left:0; right:0; bottom:0`), so the command line
stays visible and usable underneath it. While an overlay
is open it SHALL trap keyboard focus, so no surface behind it is reachable by sequential navigation. It
SHALL close on Escape and on activation of its close control, and both paths SHALL restore focus to the
control that opened it. It SHALL use the shared focus trap the client already owns rather than a second
implementation.

At most one overlay SHALL be open at any time; opening a second SHALL close the first, and the opener
recorded for the replacement is the control that opened it, so closing restores focus to the most recent
trigger, never to the trigger of the closed overlay. An overlay and a
reference drawer SHALL NOT be open together: opening either SHALL close the other, so at most one
focus-trapped surface exists at any moment. An open overlay SHALL register itself as an open surface so
the stage recession this capability already requires applies without a second mechanism.

Escape SHALL be resolved by a single precedence order, topmost first — the open overlay, then an open
drawer, then the focused command field, then the dock's current menu level — with each level consuming
the key and stopping.

A mode change into creation, a presentation-epoch reset and a loss of the transport SHALL each close
every open overlay. The mode-driven character-creation surface SHALL NOT be part of this single-open
stack, because it is not opened by the player and a utility control must never dismiss it.

#### Scenario: An overlay opens, traps focus, and returns it
- **WHEN** the player activates an overlay trigger, cycles focus forward past the overlay's last control and backward past its first, and then presses Escape
- **THEN** focus stays inside the overlay in both directions, the overlay closes on Escape, and focus returns to the trigger that opened it

#### Scenario: Only one overlay is open at a time
- **WHEN** an overlay is open and the player activates a different overlay's trigger
- **THEN** the first overlay closes as the second opens, and exactly one overlay is present

#### Scenario: An overlay and a drawer are never open together
- **WHEN** a reference drawer is open and the player activates an overlay trigger
- **THEN** the drawer closes as the overlay opens, and exactly one focus-trapped surface is present

#### Scenario: Escape resolves at exactly one level
- **WHEN** an overlay is open above a focused command field and a dock frame at depth two, and the player presses Escape once
- **THEN** the overlay closes, focus returns to its trigger, the command field's content is untouched, and the dock's menu depth is unchanged

#### Scenario: Closing the last overlay clears the recession
- **WHEN** the open overlay closes and no drawer remains open
- **THEN** the stage's recession mark is cleared

#### Scenario: A creation transition closes the overlays
- **WHEN** the committed mode changes to creation while an overlay is open
- **THEN** that overlay closes, focus is routed to the action dock, and the character-creation surface is not itself treated as one of the single-open overlays

### Requirement: The map, settings, and help surfaces are reachable from the live client
The map, settings and help surfaces SHALL each be reachable from the running client by a labelled
control, not only from the component showcase. The minimap island SHALL carry a labelled control that
opens the map surface, rendered as a sibling of its lattice rather than as a wrapper around its
actionable nodes. The command line's utility controls SHALL open the settings and help surfaces.

The map surface SHALL render the committed `local_map` payload through the same component the minimap
island renders, and SHALL re-render its available and unavailable branches whenever that read model is
replaced, so a superseded payload never leaves a stale lattice or a stale reason on screen. It SHALL
present no zoom or pan affordance and SHALL NOT advertise one. It SHALL render no bearing, compass angle
or distance figure, because node coordinates are renderer-local presentation geometry.

The help surface SHALL render the client's own control reference — the keys this client binds, the dock's
navigation model, the quick-word chips and the close paths — from a single client-owned source, and SHALL
state how the game's own help output is reached. It SHALL NOT render authored game-help content for which
no committed panel exists, and SHALL NOT stand a placeholder in for it.

#### Scenario: Each surface has a live trigger
- **WHEN** the client renders in exploration mode with the `local_map` panel committed
- **THEN** the minimap island carries a labelled control that opens the map surface, and the command line carries labelled controls that open the settings and help surfaces

#### Scenario: The map surface tracks read-model replacement in the live client
- **WHEN** the map surface is open and an update replaces the committed `local_map` payload with the registry-owned unavailable form, and then with a different available payload
- **THEN** the surface renders only the registry-owned reason, then the replacement lattice, and at no point shows a lattice or a reason from the superseded payload

#### Scenario: The map surface advertises no zoom or pan
- **WHEN** the map surface renders on any layer
- **THEN** no zoom or pan control, hint or legend entry is present, and no bearing, compass angle or distance figure appears

#### Scenario: The help surface tells the truth about what it knows
- **WHEN** the help surface renders with no committed panel carrying authored guide content
- **THEN** it renders the client's own control reference and a statement of how the game's help output is reached, and it renders no authored game-help entry and no placeholder standing in for one

### Requirement: Narrative prose scale is a client-local preference the settings surface owns
The client SHALL expose a narrative prose scale with three steps, selectable from the settings surface,
whose current step is marked by an indicator that does not rely on colour alone. The scale SHALL apply
to narrative and dialogue prose only — the narrative caption's lines, the complete-log surface's lines
and the prompt line — and SHALL NOT alter HUD, dock, drawer, overlay or any other interface text, so the
stage's measured anchor geometry is unaffected at either supported viewport.

The prose scale and every other setting the surface offers SHALL be client-local presentation state. No
settings control SHALL dispatch an action: the client's action allowlist carries exactly one `options.*`
action, the suggestions dismissal, and this capability adds none. Each setting SHALL be applied to the
document's presentation tokens immediately and persisted through the client's versioned,
presentation-only browser store as a harmless display preference, SHALL be re-applied at load, and SHALL
be reset to its default — fully applied, never half-applied — whenever that store resets. The
reduced-motion setting SHALL act as an override over the operating system's reduced-motion preference,
which SHALL continue to apply when no override is stored.

The settings surface SHALL offer no control it does not implement.

#### Scenario: The prose scale moves prose and nothing else
- **WHEN** the player selects the largest prose scale
- **THEN** the narrative caption's lines, the complete-log surface's lines and the prompt line render larger, every HUD, dock and overlay label is unchanged, and no stage anchor's rendered box intersects another's at 1440x900 or 1280x720

#### Scenario: No setting dispatches an action
- **WHEN** the player changes every control the settings surface offers
- **THEN** no `ui_action` is sent for any of them, and the only `options.*` action the client can dispatch remains the suggestions dismissal

#### Scenario: A setting survives a reload and resets cleanly
- **WHEN** the player changes the prose scale, reloads the client, and then the presentation store's stored version is unrecognised
- **THEN** the chosen scale is re-applied after the reload, and after the reset every setting is applied at its default with no setting left partly applied

#### Scenario: Reduced motion overrides, and defers when unset
- **WHEN** no reduced-motion override is stored and the operating system requests reduced motion
- **THEN** non-essential transitions are disabled; and when the player then sets the override off, the client honours the override

#### Scenario: The surface offers nothing inert
- **WHEN** the settings surface's controls are enumerated
- **THEN** every control changes an outcome the client actually implements, and no control is rendered that has no effect
