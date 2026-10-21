# Spec Delta

## ADDED Requirements

### Requirement: Sleep prohibits actions while retaining ordinary target legality
Sleep alone SHALL not remove battlefield presence, normal range, enemy or allied targeting eligibility. Existing HP/knockout/fled/defeat exclusions SHALL retain precedence. Sleeping allies SHALL render with a textual sleeping/action-unavailable state separate from defeated appearance.

#### Scenario: Real damage to sleeper
- **WHEN** a legal enemy action selects a present sleeping ally
- **THEN** normal damage changes real HP; sleep alone did not set knockout or defeat, and the ally was visible and not assigned a command

#### Scenario: Knockout remains different
- **WHEN** a sleeping companion is also genuinely marked knocked out
- **THEN** existing knockout target/action exclusions still apply; sleep creates no immunity exception

