## MODIFIED Requirements

### Requirement: The dock's shortcut legend names only real keyboard behaviour and renders as one visible instance
The action dock SHALL carry a shortcut-legend element matching
`docs/design/elosern-redesign/index.html`'s dock hint in wording and structure: the text
`數字鍵 1–4 · ` followed by an `<kbd>` element naming `Enter`
and the verb `執行`, the separator `·`, and an `<kbd>` element naming `Esc` and the verb `返回`.
The legend renders
with the reference's `<kbd>` treatment (monospace face, `--ink-780` ground, 2px bottom border).
The legend SHALL render exactly once as visible content and SHALL be the only element carrying the
legend's test hook. The dock SHALL NOT carry a dialogue-mode legend variant.

The legend SHALL NOT name a key, gesture, or affordance this client does not implement or that no
longer behaves as named, and it SHALL NOT advertise implemented affordances the reference's legend
does not name. When a named affordance's behaviour changes (for example, a control that used to
open a surface and now only moves focus into an always-present one), the legend's wording SHALL be
updated in the same change that alters the behaviour.

The digits the legend names SHALL be bound: while the dock owns keyboard focus (the key target is
not editable), pressing
`1`–`4` moves the current dock frame's focus onto the first four rows (1-indexed, rendered order)
and activates the row through the same confirm path `Enter` uses — a disabled row shows its
explanation and submits nothing, an in-flight row stays locked, and a held repeat is suppressed.
The slots address the pane's rendered rows: where a pane does not render the standard `back`
cell as a row (the exit-outlet pane), that cell takes no slot. While the narrative caption
presents the dialogue variant with at least one pick, the slots address the caption's pick rows
instead of the dock's pane rows — the caption's trailing free-dialogue and exit rows never take
a digit slot — and the dock's own rows claim no digit while that hold applies.
A digit whose row does not exist (a frame with fewer rendered rows, a caption variant with no
picks, or
the pre-session empty stack) is not claimed and falls
through to the text / command-history path.

#### Scenario: The legend renders once
- **WHEN** the dock renders in a mode where its chrome (tab bar) is shown
- **THEN** exactly one element carries the shortcut-legend text and test hook, and no duplicate
  copy is rendered

#### Scenario: The legend matches the reference wording and kbd structure
- **WHEN** the dock tab bar renders in exploration, combat, or dialogue mode
- **THEN** the legend reads `數字鍵 1–4 · Enter 執行 · Esc 返回` with `Enter` and `Esc` rendered as
  styled `<kbd>` elements and no other key named

#### Scenario: A digit picks its row
- **WHEN** the current dock frame has at least two rows and the player presses `2` from a
  non-editable focus
- **THEN** the second row becomes the frame's focus and its action submits exactly as `Enter`
  would, once

#### Scenario: A digit beyond the frame's rows is unclaimed
- **WHEN** the current dock frame has fewer rows than the pressed digit and the command field is
  not focused
- **THEN** the digit is not claimed, the frame's focus is unchanged, and nothing submits

#### Scenario: Digits address the caption's picks while the dialogue variant presents
- **WHEN** the dialogue variant renders three picks over a dock root frame and the player presses
  `2` and `4` from a non-editable focus
- **THEN** the `2` press activates caption pick two through the same dispatch entry, the `4` press
  is unclaimed and falls through, and no dock row is focused or activated
