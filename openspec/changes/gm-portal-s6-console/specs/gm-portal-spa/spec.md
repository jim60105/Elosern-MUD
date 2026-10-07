## MODIFIED Requirements

### Requirement: S1 navigation and history routing

The SPA SHALL retain history routing at /gm/ and session identity/time/version. The home overview SHALL render the gm-operations-dashboard snapshot instead of calling the removed health endpoint, using the landed S1 fetch boundary and component layer and S2a transcript-detail contract. Navigation SHALL retain the approved future sections; genuinely undelivered sections SHALL remain disabled with 尚未開放 and no placeholder pages. Delivered S6 SHALL use contextual entity drawers, raw/memory actions and the dashboard clock control under gm-developer-console, not a standalone intervention route. The navigation SHALL omit the obsolete disabled GM 介入 entry rather than imply that delivered S6 is unavailable or provide a placeholder link. Router guards SHALL handle authorization failures without redirect loops.

#### Scenario: Foundation overview
- **WHEN** a permitted operator loads /gm/
- **THEN** session information and dashboard sections render and no request targets /gm/api/health

#### Scenario: Future sections disabled
- **WHEN** pointer or keyboard activation targets a genuinely undelivered section
- **THEN** it remains disabled and cannot navigate to a placeholder

#### Scenario: History and authorization guard
- **WHEN** a client route is entered directly, through history, or receives a forbidden API outcome
- **THEN** routing stays under /gm/ and permission denial never exposes protected content or loops

#### Scenario: Contextual S6 navigation
- **WHEN** S6 is delivered and the operator navigates to an entity, raw tab, NPC memory tab or dashboard world section
- **THEN** the appropriate console controls are available there, no obsolete disabled GM 介入 entry or standalone placeholder remains, and genuinely undelivered entries retain disabled behavior
