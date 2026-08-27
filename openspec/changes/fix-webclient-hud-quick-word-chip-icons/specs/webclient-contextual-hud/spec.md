## MODIFIED Requirements

### Requirement: Quick-word chips prepare a command without submitting it
The command line SHALL render quick-word chips for the committed mode. Activating a chip SHALL write
its command text into the input field and move focus to the field, and SHALL NOT submit: a prepared
command SHALL still travel through the field's single send implementation, so exactly one send path
exists.

Each chip's visible label SHALL be the literal command verb it inserts, and every chip SHALL insert a
verb the server's installed command set actually accepts — a chip SHALL NOT offer a verb the parser
would reject. Each chip SHALL carry a decorative icon beside its text label, drawn from this client's
stable glyph vocabulary (the same table the action dock's tab bar and pane rows draw from); the icon
SHALL be hidden from assistive technology and SHALL NOT appear without its accompanying text label.
Chips SHALL carry no key-mnemonic badge unless this client binds that key. Chips that do not apply to
the committed mode SHALL be removed with `display:none` so they leave the accessibility tree and the tab
order, never dimmed.

#### Scenario: A chip prepares, it does not send
- **WHEN** the player activates a quick-word chip
- **THEN** the chip's command text plus a trailing space is written into the input field, focus moves to the field, and no text message and no `ui_action` is sent

#### Scenario: The chip set follows the mode
- **WHEN** the committed mode changes from exploration to combat
- **THEN** the exploration-only chips are absent from the DOM and from the tab order, and the combat chip set renders in their place

#### Scenario: No chip offers a verb the game does not have
- **WHEN** the rendered chip set is enumerated in any mode
- **THEN** every chip's inserted text is a command key or alias the server installs, and no chip advertises a key mnemonic that this client does not bind

#### Scenario: Every chip carries a decorative icon paired with its label
- **WHEN** the rendered chip set is enumerated in any mode
- **THEN** every chip renders an `aria-hidden` icon alongside its visible text label, and no chip renders an icon without that label
