## ADDED Requirements

### Requirement: Degraded text remains playable alongside the Vue shell
The application SHALL remain fully playable by ordinary text commands when the Vue graphical surfaces are
unavailable, when the Vite bundle fails to load, or when the OOB channel is incompatible. An incompatible
or failed OOB presentation SHALL lock the graphical controls while leaving the text path functional.
Narrative and command output SHALL remain the authoritative text surface and SHALL degrade a message that
cannot be fully tokenized to readable literal text rather than suppressing the log.

#### Scenario: Bundle blocked keeps text playable
- **WHEN** the Vue bundle cannot load
- **THEN** ordinary text commands can still be sent and rendered and no required input path is lost

#### Scenario: Incompatible OOB locks graphical, keeps text
- **WHEN** the application receives an unsupported protocol version
- **THEN** graphical actions are disabled and locked while a text command round-trips and renders normally

#### Scenario: Unparseable message degrades to literal text
- **WHEN** a message cannot be fully tokenized by the markup pipeline
- **THEN** the narrative shows readable literal text rather than being suppressed
