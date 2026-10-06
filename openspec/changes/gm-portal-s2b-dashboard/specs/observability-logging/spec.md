## MODIFIED Requirements

### Requirement: Facade is the sole game-code log entry point
All game code under world/, typeclasses/, commands/, server/ and web/ MUST emit operational logs exclusively through world.observability (log_info/log_warn/log_error/log_debug). The facade MUST depend only on stdlib, Evennia logger, Django settings and observability-local modules; it MUST NOT import other game modules. After a log line is written it SHALL feed the observability-local recent sink for llm_call and warn/error events. Sink failures SHALL remain inside the never-raises boundary and SHALL NOT erase or prevent the already-written operational line.

#### Scenario: Facade routes levels to the Evennia logger
- **WHEN** log_info, log_warn or log_error emits a valid event
- **THEN** the corresponding Evennia level receives its operational line before recent-sink delivery

#### Scenario: Debug events respect the VERBOSE setting
- **WHEN** log_debug is called with VERBOSE false or true
- **THEN** false emits nothing and true emits the operational event

#### Scenario: Sink containment
- **WHEN** the recent-event sink raises
- **THEN** the facade returns normally and the previously written line remains available
