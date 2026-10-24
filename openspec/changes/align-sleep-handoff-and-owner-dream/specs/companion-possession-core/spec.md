# Spec Delta

## MODIFIED Requirements

### Requirement: Sleep-driven handoff is contextual and requires confirmation
Committed sleep of the controlled body SHALL automatically open contextual browser selection with text parity. Every effective companion SHALL remain visible with reserve/fatigue and availability/reason; choices SHALL distinguish possession and lawful awake-owner return. The final companion-list option SHALL be exactly `全員一起睡眠`. No candidate SHALL be auto-selected; choice/cancel SHALL cost no time or alter commander/combat draft.

#### Scenario: Possessed sleeper returns home
- **WHEN** a controlled companion enters voluntary sleep while its owner is awake
- **THEN** the zero-time entry automatically offers explicit owner return and other companion choices before recovery; owner actions may recover that companion without making the owner asleep

#### Scenario: Unselected transition
- **WHEN** an unselected companion sleeps or a sleeping owner wakes
- **THEN** status changes without mandatory handoff or automatic repuppeting

#### Scenario: Cancel
- **WHEN** the player closes handoff while controlling a sleeper
- **THEN** choice/cancel adds no time, claims no completed sleep and exposes only lawful status/control/recovery actions; all-asleep dream refusal follows its explicit continuation policy

#### Scenario: Complete companion list
- **WHEN** the controlled owner sleeps with awake, sleeping, remote and action-incapable effective companions
- **THEN** all companions appear with current state and disabled reasons as applicable, the final companion option is `全員一起睡眠`, and no Party Drawer navigation is needed

#### Scenario: Owner sleep and local play
- **WHEN** owner sleep opens selection and the player confirms an eligible companion then performs a lawful local action
- **THEN** one verified possession occurs, owner sleep recovers through real elapsed action time, and travel remains blocked while any present member sleeps

#### Scenario: Explicit party choice
- **WHEN** the player selects `全員一起睡眠`
- **THEN** the shared atomic party operation executes once without implicit elapsed time; the resulting no-possession sleeping-owner view offers the owner-only dream decision before automatic recovery

#### Scenario: Modal interaction conventions
- **WHEN** keyboard or pointer operates the contextual selection, cancels it or receives a stale revision
- **THEN** existing focus trap, active-row navigation, Escape/focus restoration and stale-result refresh conventions apply without duplicate action dispatch
