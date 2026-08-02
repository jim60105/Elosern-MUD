## ADDED Requirements

### Requirement: World-clock presentation reads never create the singleton
`world/rules/clock.py` SHALL provide a read-only accessor that returns the existing `WorldClock` or absence without creating a Script or other persistent state. The deterministic server startup lifecycle SHALL explicitly ensure the world-clock singleton before player presentation is accepted. Presentation code SHALL use only the read-only accessor and SHALL NOT call the create-or-read mutation helper.

#### Scenario: Startup ensures the clock through its deterministic owner
- **WHEN** the server completes deterministic startup against a database without a world-clock Script
- **THEN** exactly one non-repeating world-clock Script exists before a player can request WebClient presentation

#### Scenario: Read accessor reports absence without writing
- **WHEN** the world-clock Script is absent and the read-only accessor is called
- **THEN** it returns absence and creates no Script, Attribute, or other persistent record

#### Scenario: Presentation does not use the create-or-read helper
- **WHEN** WebClient presentation source is inspected and a full snapshot is built with an existing clock
- **THEN** presentation calls only the read-only accessor and leaves the Script count and world tick unchanged
