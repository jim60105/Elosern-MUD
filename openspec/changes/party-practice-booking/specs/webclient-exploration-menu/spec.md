# Spec Delta

## MODIFIED Requirements

### Requirement: explore.practice advances the clock for one declared skill
The production action registry SHALL register `explore.practice` with a payload of exactly `actor_id` (a positive safe-integer party member id) and `skill` (a bounded non-space key of at most 64 characters). The adapter SHALL reauthorize the member for the acting purpose, reject during an active combat session with `booking_in_combat`, preflight the skill against that member, and record the member's booking without advancing the clock; the next SKIP advance that settles the member grows the booked skill.

#### Scenario: Declared practice grows only the booked skill
- **WHEN** the commander books companion 艾拉's uncapped active `healing_light` through `explore.practice` and then waits 7200 seconds with 艾拉 present
- **THEN** the booking itself advances no time, the later SKIP advance grows only 艾拉's `healing_light` under the whole-hour settlement rule, and each action publishes a full snapshot at exactly one newer revision

#### Scenario: Unknown or capped practice skills advance nothing
- **WHEN** the submitted `skill` is unknown to the named member or already capped for that member
- **THEN** the result carries the stable code `PRACTICE_SKILL_UNKNOWN` or `PRACTICE_SKILL_CAPPED` with a Traditional Chinese message, the clock is unchanged, and the member's previous booking is unchanged

#### Scenario: An ambiguous practice payload rejects at the validator
- **WHEN** an `explore.practice` payload omits `actor_id` or `skill`, carries `seconds` or another extra field, or carries a non-integer `actor_id`
- **THEN** the dispatcher rejects it with outcome `rejected` and stable code `malformed_payload` without invoking the adapter

#### Scenario: Booking in combat is refused
- **WHEN** `explore.practice` arrives while the commander is in an active combat session
- **THEN** it is rejected with `booking_in_combat` and no booking changes

#### Scenario: A forged member is never replaced by the commander
- **WHEN** `explore.practice` names an NPC outside the party
- **THEN** it is rejected with `not_party_member` and the commander's booking is unchanged

#### Scenario: Rebooking replaces the member's booking
- **WHEN** a member with a standing booking for `healing_light` is booked for `mass_heal`
- **THEN** the member's single booking now names `mass_heal`

#### Scenario: The whole-hour settlement stage stays the sole practice writer
- **WHEN** a booking is recorded
- **THEN** the adapter writes only the member's booking; practice progression is written only by the clock's whole-hour practice settlement stage on a later SKIP advance
