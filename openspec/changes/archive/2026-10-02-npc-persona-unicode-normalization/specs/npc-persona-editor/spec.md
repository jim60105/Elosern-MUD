## ADDED Requirements

### Requirement: NPC editor mirror equality includes normalized card and greeting text
Browser and server SHALL produce exactly the same normalized strings, acceptance/rejection reason and offending leaf, code-point counts, and valid labeled-card totals under the NPC contract's explicit finite boundary-whitespace and CRLF normalization policy. Complete normalized card plus offline greeting equality SHALL define a no-op, including both identity leaves and optional clears. The server SHALL check the submitted expected version before accepting even an equal submission. Neither mirror SHALL alter generic player persona rules or relax any protocol limit.

#### Scenario: Astral and boundary characters agree at limits
- **WHEN** shared fixtures combine enumerated boundary characters, astral characters, and preserved interior/excluded characters at 600-leaf, 600-identity, 2000-card or 300-greeting limits and just beyond them
- **THEN** both runtimes produce identical normalized values, counts and accept/reject field reasons

#### Scenario: Boundary-only resave is a no-op
- **WHEN** a current-version submission differs from stored card/greeting only by outer members of the explicit boundary set or CRLF versus LF card line endings
- **THEN** normalized equality succeeds unchanged and persona version does not advance

#### Scenario: Clear advances once and stale equality still rejects
- **WHEN** optional hidden/social/greeting content is cleared using only boundary whitespace and that normalized empty submission is repeated
- **THEN** the first actual clear advances once, the current-version repeat is unchanged, and a stale-version repeat rejects as version conflict without writing
