# Spec Delta

## MODIFIED Requirements

### Requirement: Creation presents a bounded desktop identity form and allocation workspace
The creation wizard SHALL organize identity/race context, a bounded-width form and allocation preview into three desktop regions. All current required and optional fields, errors and confirmation actions SHALL remain reachable at 1451x790 and 2560x1440 without page-level horizontal scrolling. Preset cards SHALL render server-supplied canonical artwork in one card wall without inventing media URLs.

#### Scenario: Custom form remains complete
- **WHEN** a keyboard user completes creation at the 1451x790 reference viewport
- **THEN** name, sex, both ages, race/subrace, allocations and optional fields are reachable in logical order, with visible errors and confirmation controls

#### Scenario: Preset lacks artwork
- **WHEN** a synthetic preset’s descriptor has no official image attempt
- **THEN** the card uses the supplied alpha terminal through the shared artwork loader, never a fabricated portrait URL

## ADDED Requirements

### Requirement: Preset browsing is local until deliberate selection
The preset wall SHALL keep expanded-card state separate from the saved draft. Pointer opening, horizontal arrows and digit shortcuts SHALL only expand a supplied card. The expanded card’s primary action or Enter SHALL run the existing preset-save and explicit activation-confirmation flow once, subject to dispatch admission.

#### Scenario: Opening sends nothing
- **WHEN** a player opens another supplied card by pointer, a horizontal arrow or its displayed ordinal digit
- **THEN** the card expands locally, no action or narrative mutation echo is sent, and the server draft is unchanged

#### Scenario: Deliberate selection preserves confirmation
- **WHEN** the player activates the expanded card’s primary action or presses Enter in its wall context
- **THEN** exactly one preset save names that card’s key, confirmation opens only after its matching successful save, and activation waits for explicit confirmation

#### Scenario: Entry restores a valid expansion
- **WHEN** preset mode opens or its supplied cards change
- **THEN** a surviving saved preset key is expanded on entry, otherwise the first supplied card is expanded; a surviving local browse selection is kept during equal-content republication

#### Scenario: Unavailable ordinal is inert
- **WHEN** a shortcut names no supplied card, an input or drawer owns the key, or the event is composing, modified or repeated
- **THEN** no wall selection or action occurs and native text entry remains intact

#### Scenario: Accessible opening and motion
- **WHEN** a keyboard user browses cards or changes motion preference
- **THEN** collapsed cards are named native buttons, the expanded card exposes aria-current and visible focus, and reduced/off motion switches without interpolating the card transition
