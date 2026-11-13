# Spec Delta

## MODIFIED Requirements

### Requirement: Public dream surface includes the approved presentation and deterministic escape

Both browser and text surfaces SHALL expose remaining exchanges, free text only while conversing below six, finalize while conversing, confirmation once finalized, and draft preservation and awakening on all failure states. Public entry SHALL include the approved explicit presentation capability rather than publishing a sanitized/incomplete session. Command documentation and contracts SHALL match the introduced syntax and availability.

#### Scenario: Six reached on either client
- **WHEN** the session completes its sixth exchange on browser or text client
- **THEN** free text closes and confirm/draft/awaken choices remain usable offline

#### Scenario: Before the cap on either client
- **WHEN** a conversing session has exchanges remaining on browser or text client
- **THEN** free text, finalize, draft preservation and awakening are offered and confirmation is not

#### Scenario: Finalized before the cap on either client
- **WHEN** the player finalizes with exchanges remaining on browser or text client
- **THEN** free text is no longer offered and confirm/draft/awaken choices are usable offline
