# Spec Delta

## MODIFIED Requirements

### Requirement: Telnet combat discovery and target tokens have rule parity
`combat actions [actor-token]` SHALL list the selected actor complete active skill, item and tactic choices with draft progress; skills SHALL retain deterministic handler order and it SHALL assign tokens using session-local target tokens from persisted participant order: `a1`, `a2`, and so on for `player_ids`, then `e1`, `e2`, and so on for `enemy_ids`. A token SHALL remain bound to the same dbref for the session lifetime and SHALL never be persisted separately.

#### Scenario: Combat actions lists stable tokens and active skills
- **WHEN** a Telnet player requests `combat actions` before and after one nonterminal round
- **THEN** the same participant dbrefs retain the same `aN` and `eN` tokens and active skills retain stored order

#### Scenario: Comma-separated tokens submit AREA targets
- **WHEN** the player enters `cast wind_blade=e1,e2`
- **THEN** both tokens resolve from the active record and the same explicit-list facade used by the WebClient receives those participants

#### Scenario: Single display-name lookup remains available
- **WHEN** the player enters one unambiguous existing target name on the right-hand side
- **THEN** the command resolves that one target through existing search and submits it as a one-element list

#### Scenario: Mixed syntax cannot bypass target rules
- **WHEN** the player enters a duplicate token list, a token mixed with a display name, or `all-enemies,e1`
- **THEN** the command rejects before preview, initiative, round count, or world-time change

#### Scenario: Active-session cast accepts the approved syntax set
- **WHEN** the player casts inside an active session
- **THEN** `cast` accepts one token, a comma-separated list containing tokens only, or one complete approved AREA shorthand, and retains existing one-target display-name search

#### Scenario: Comma input rejects malformed entries before initiative
- **WHEN** comma input contains names, unknown or duplicate tokens, or shorthand/token mixtures
- **THEN** it rejects before initiative

#### Scenario: Actor and target are independent
- **WHEN** combat command names a2 as actor and a1 or e1 as target
- **THEN** only authorized a2 capabilities and costs are used, and SELF ignores target tokens and binds a2

## ADDED Requirements

### Requirement: Text clients can complete and revise every party command kind
Text clients SHALL offer actor-scoped skill including scale/targets, usable own item and Defend/Dodge/Taunt choices with the same server validation as browser commands. Each command SHALL confirm one draft entry, allow earlier-entry replacement and automatically resolve only the final valid selection. Progress and member-specific reasons SHALL remain discoverable.

#### Scenario: Complete text round
- **WHEN** a text player selects a companion skill, revises an earlier member choice and confirms the final item/tactical choice
- **THEN** the same durable draft and complete-round provider execute without possession or autonomous missing commands

#### Scenario: Commander cast and use
- **WHEN** existing cast or use is entered during a multi-actor session
- **THEN** it confirms the commander entry through the same facade and cannot execute an incomplete round

