## ADDED Requirements

### Requirement: Personal letters load once per opening

The personal letters panel SHALL have no Reload or Refresh control. Each genuine opening SHALL request the first collected-letter page exactly once when dispatch is ready. An opening while a preceding request or global mutation/presentation lock prevents dispatch SHALL wait for readiness without submitting a refused request, then submit its one initial list request if still open. Closing SHALL cancel an unsent initial load. Ordinary presentation updates SHALL NOT schedule additional initial loads. Closing and reopening SHALL start a fresh first-page load; explicit next-page requests SHALL remain available through the server-provided cursor.

#### Scenario: Open and reopen
- **WHEN** a player opens a dispatch-ready personal letters panel, leaves it open through ordinary presentation updates, then closes and reopens it
- **THEN** each opening submits exactly one first-page list request and no reload control is rendered
- **AND** ordinary updates during either opening submit no additional initial requests

#### Scenario: Wait for a preceding request
- **WHEN** the panel opens while an earlier request or global mutation/presentation lock prevents dispatch and later becomes dispatch-ready while the panel remains open
- **THEN** no initial list request is submitted while blocked and exactly one is submitted after readiness

#### Scenario: Close before readiness
- **WHEN** the player closes a newly opened panel before dispatch readiness and the lock later releases
- **THEN** that closed opening submits no list request
- **AND** a subsequent opening owns a separate single initial load

#### Scenario: Paginate collected letters
- **WHEN** a loaded page has a next cursor and the player explicitly requests the next page
- **THEN** the panel submits a list request using that cursor and displays the returned collected-letter page without collecting or reading any letter

### Requirement: Letter panel state follows genuine lifecycle boundaries

Ordinary presentation publications with unchanged transport generation and identity SHALL preserve the loaded page, opened letter prose, and unsent recipient/body draft. Disconnect, puppet detach, identity/epoch replacement, or transport-generation reset SHALL close the panel and discard its private local state and unsent initial load. Closing SHALL discard the unsent draft without persisting it. Only a result correlated to the current opening's pending request, identity epoch, and transport generation SHALL update the panel; late results from a previous opening or session SHALL NOT populate it or change its status message.

#### Scenario: Ordinary publication preserves private local state
- **WHEN** an ordinary presentation publication replaces the client view with the same identity and transport generation after a page and letter body are loaded and a draft is entered
- **THEN** the page, opened prose, and unsent recipient/body draft remain available without a false session-change warning or a new initial request

#### Scenario: Genuine boundary tears down the panel
- **WHEN** a panel containing private prose or an unsent draft encounters disconnect, puppet detach, identity/epoch replacement, or a new transport generation
- **THEN** it closes and discards the page, opened prose, draft, and any unsent initial load
- **AND** another character or later opening receives none of that private local state

#### Scenario: Late prior-opening result
- **WHEN** an opening submits a request, closes, and a new opening begins before the old response arrives
- **THEN** the old response neither populates the new panel nor changes its message
- **AND** only the new opening's correlated result is accepted

### Requirement: Letter loading has explicit recovery and authoritative response updates

Opening or listing the panel SHALL NOT automatically collect letters or mark them read. The panel SHALL NOT poll or automatically retry any submitted request that fails. A failed list request SHALL present failure information and instruct the player to close and reopen to load the list again. Successful explicit collection or sending SHALL update the displayed page using the authoritative operation response without an additional browser list request. These behaviors SHALL be documented in both player command references without changing text-command syntax.

#### Scenario: Submitted load fails
- **WHEN** a submitted list request fails and subsequent ordinary publications or lock releases occur while the panel remains open
- **THEN** the failure is displayed with close-and-reopen recovery guidance and no automatic retry is submitted
- **AND** closing and reopening starts one fresh initial load when dispatch-ready

#### Scenario: Sender fails synchronously without a server result
- **WHEN** the transport reports a correlated synchronous send failure for this opening's list attempt and no server action result arrives
- **THEN** the panel leaves its local processing state and displays failure with close-and-reopen guidance without clearing global transport uncertainty
- **AND** subsequent ordinary publications neither retry the consumed initial attempt nor overwrite that failure guidance

#### Scenario: Successful collection updates without reading
- **WHEN** a player explicitly collects letters at an authorized branch and receives success
- **THEN** the returned authoritative page is displayed with no additional browser list request
- **AND** newly collected unread letters retain absent first-read state and content knowledge

#### Scenario: Successful send reuses its response
- **WHEN** an authorized explicit send succeeds
- **THEN** its authoritative page updates the panel without another browser list request and the sent body draft clears

## MODIFIED Requirements

### Requirement: Sending and collection require any branch

Players SHALL send bounded free text to established recipients only at an authored 銀羽驛站 branch with letter service and a unique permanent room anchor. At any such branch they SHALL explicitly collect all due letters for their identity with no home-city restriction. Server authorization SHALL enforce these branch checks for both browser and text requests, including forged requests. Away from branches the personal surface SHALL expose only owned previously collected letters, including collected-but-unread letters, never uncollected bodies. Previously collected letters SHALL remain readable anywhere.

#### Scenario: Collect at another settlement
- **WHEN** a player has due letters and visits a different authorized branch
- **THEN** explicit collection acquires all due letters without changing their unread state

#### Scenario: Remote personal list
- **WHEN** a player opens personal letters away from a branch
- **THEN** only owned previously collected letters are listed and their bodies remain accessible through explicit authorized reading
- **AND** sending and collection controls are unavailable and opening does not acquire any due letter

#### Scenario: Forged remote acquisition
- **WHEN** a browser or text request attempts sending or collection outside an authored uniquely anchored branch, including a duplicate-tagged or unauthored room
- **THEN** server authorization rejects it without sending or acquiring letters

#### Scenario: Invalid send
- **WHEN** recipient resolution is invalid/ambiguous or body bounds fail
- **THEN** no send, deadline or narrative source commits

### Requirement: Collection and reading remain distinct

Collection SHALL NOT establish content knowledge or first-read state. Opening the personal panel and listing metadata SHALL NOT open a letter or establish content knowledge or first-read state. First authorized explicit opening of an owned collected letter SHALL record first-read exactly once and a durable read source. Previously collected letters SHALL be readable anywhere; rereading SHALL NOT duplicate read events or cognition.

#### Scenario: Collected remains unread
- **WHEN** a letter is collected but never explicitly opened, including after panel opening, listing, or pagination
- **THEN** its content remains unknown and first-read tick is absent

#### Scenario: Read and reread remotely
- **WHEN** the player explicitly opens an owned collected letter twice away from a branch
- **THEN** first opening records one read occurrence and subsequent opening changes no first-read state

### Requirement: Browser and text channels share authoritative permissions

Finite letter operations SHALL use server-authorized actions with text-client equivalents; text fields SHALL remain free-form. Actual command keys/syntax/context SHALL be documented in both player command references with contract tests. Requesting another player's letter or an uncollected body SHALL reject server-side regardless of browser control visibility or forged identifiers, without leaking private prose or creating first-read/knowledge state.

#### Scenario: Forged letter access
- **WHEN** a browser or text request names another identity's letter or an uncollected body
- **THEN** the owner/collection gate rejects without text leakage, first-read updates, or content knowledge
