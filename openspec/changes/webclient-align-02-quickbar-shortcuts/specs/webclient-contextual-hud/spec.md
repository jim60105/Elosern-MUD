# Delta spec: webclient-contextual-hud (webclient-align-02-quickbar-shortcuts)

## MODIFIED Requirements

### Requirement: Quick-word chips prepare a command without submitting it
The command line SHALL render quick-word chips for the committed mode. Activating a chip SHALL write
its command text into the input field and move focus to the field, and SHALL NOT submit: a prepared
command SHALL still travel through the field's single send implementation, so exactly one send path
exists.

Each chip SHALL render the draft's structure: a visible Traditional Chinese command label plus a
letter badge, and the text the chip inserts SHALL be exactly the badge letter followed by a trailing
space — a complete command word the server's installed command set accepts on every transport. A
badge letter SHALL therefore be an installed command key or alias, and SHALL also be the client's
keybinding for that chip: a chip SHALL NOT render a badge letter the client does not bind, and the
client SHALL NOT bind a letter that is not installed as a command word. Each chip SHALL carry a
decorative icon beside its text label, drawn from this client's stable glyph vocabulary (the same
table the action dock's tab bar and pane rows draw from); the icon SHALL be hidden from assistive
technology and SHALL NOT appear without its accompanying text label. Chips that do not apply to the
committed mode SHALL be removed with `display:none` so they leave the accessibility tree and the tab
order, never dimmed.

Pressing a chip's bound letter while focus is in no text-entry surface SHALL be equivalent to
activating the chip: the bound letter plus a trailing space SHALL be written into the input field
and focus SHALL move to the field, without submitting. In the exploration set the bound letters are
`l`→看, `g`→拿, `s`→說, `t`→交談, `w`→等待; in the combat set, `s`→說 and `c`→施法. A bound-letter
press SHALL NOT interfere with keys owned by other surfaces (the `/` focus key, Escape, arrows, the
1–4 card picks, and Tab).

#### Scenario: A chip prepares, it does not send
- **WHEN** the player activates a quick-word chip
- **THEN** the chip's badge letter plus a trailing space is written into the input field, focus
  moves to the field, and no text message and no `ui_action` is sent

#### Scenario: The chip set follows the mode
- **WHEN** the committed mode changes from exploration to combat
- **THEN** the exploration-only chips are hidden with `display:none` so they leave the
  accessibility tree and the tab order (never dimmed, and still present in the DOM), and the
  combat chip set renders in their place

#### Scenario: Every badge letter is an installed command word
- **WHEN** the rendered chip set is enumerated in any mode
- **THEN** every chip inserts exactly its badge letter plus a space, and every badge letter is a
  command key or alias the server installs

#### Scenario: A bound letter inserts like a chip click
- **WHEN** focus is in no text-entry surface and the player presses `g` in exploration mode
- **THEN** the command field holds `g `, focus moves to the field, and nothing is submitted

#### Scenario: Bound letters do not fire inside the field
- **WHEN** focus is in the command input field and the player types the letter `t`
- **THEN** the character is inserted into the draft text and no chip-insert routing occurs

#### Scenario: Every chip carries a decorative icon paired with its label
- **WHEN** the rendered chip set is enumerated in any mode
- **THEN** every chip renders an `aria-hidden` icon alongside its visible text label, and no chip
  renders an icon without that label

### Requirement: The command line advertises only affordances this client implements
The hint cluster SHALL name only behaviour the client implements. It SHALL state the command-history
recall keys and the Tab-completion affordance — matching the draft's `↑↓ 歷史 · Tab 補全` — and
Tab completion SHALL behave as named: pressing Tab inside the input field completes the current
draft against the client's candidate set (session command history, the committed mode's chip badge
letters, and the committed exploration panel's exit names and interact-target display names,
deduplicated). With exactly one matching candidate the field SHALL hold the full completion with
the caret at its end; with several the field SHALL hold the longest common prefix and successive
Tab presses SHALL cycle the matching candidates, with Shift+Tab reversing the cycle. A draft that
matches no candidate SHALL leave the field untouched, and Tab SHALL never move focus away from the
field while candidates match. The completion cycle SHALL reset when the draft text is edited
manually.

The history controls SHALL be labelled controls that drive the same history-walk state the recall
keys drive — one walk reached by two input paths — and SHALL NOT submit. No surface of the command
line SHALL name a key, gesture or affordance that has no implementation behind it.

#### Scenario: The hint names history and completion
- **WHEN** the hint cluster renders
- **THEN** it states the command-history recall keys and the Tab-completion affordance, matching
  the draft wording, and both are implemented

#### Scenario: Tab completes a unique candidate
- **WHEN** the field holds a draft matching exactly one candidate and the player presses Tab
- **THEN** the field holds that candidate in full with the caret at its end, and focus stays in
  the field

#### Scenario: Tab cycles ambiguous candidates
- **WHEN** the field holds a draft matching several candidates and the player presses Tab
  repeatedly
- **THEN** the field first completes to the longest common prefix and then cycles through the
  matching candidates, with Shift+Tab reversing the cycle, and any manual edit of the draft
  resets the cycle

#### Scenario: An unmatched draft is left alone
- **WHEN** the field holds a draft that matches no candidate and the player presses Tab
- **THEN** the field text and focus are unchanged

#### Scenario: The history controls walk the same state as the keys
- **WHEN** the player activates the previous-entry control and then presses the history recall key
- **THEN** both move through the same command-history walk in the same order, the draft is
  preserved across the walk, and neither submits

## ADDED Requirements

### Requirement: Bound quickbar letters are pinned against the installed player cmdset
The server SHALL install single-letter aliases `g` (拿), `s` (說), `t` (交談/talk), `w` (等待/wait),
and `c` (施法/cast) alongside the existing `l` (看), and a test SHALL pin that every letter the
client binds as a quick-word badge resolves to a command in the installed player cmdset, so the
chip badge contract cannot drift from the server's command set.

#### Scenario: The five letters resolve in the player cmdset
- **WHEN** the pinning test loads the installed player cmdset and enumerates the bound letters
  `l`, `g`, `s`, `t`, `w`, `c`
- **THEN** each letter resolves to its pinned command (看, 拿, 說, talk, wait, cast) with no
  collision against another installed key or alias
