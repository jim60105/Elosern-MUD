# Spec Delta

## MODIFIED Requirements

### Requirement: Map requests follow explicit scope and committed moves only while open
Opening or switching active scope SHALL request map.view for that scope; committed moves SHALL refresh it once while open. Closed maps SHALL request nothing. Adoption SHALL obey dispatcher ordering and epoch/revision rules. Each opening's world discovery baseline SHALL use its first fresh world response, never a retained cached body or a response from an earlier opening. Freshness SHALL remain independent of per-tab viewport memory.

#### Scenario: Open movement refreshes only the active map
- **WHEN** a movement commits with world selected
- **THEN** the client re-requests world once after the committed publication rather than optimistically on input or once per room/panel render

#### Scenario: Failed movement and closed drawer do not refresh
- **WHEN** a move is rejected or the drawer is closed
- **THEN** there is no new map.view caused by that move

#### Scenario: A cached reopening waits for its own fresh world baseline
- **WHEN** the client caches an unlit world body, closes the drawer, reaches a landmark while closed and reopens in wilderness before receiving its new world response
- **THEN** the cached body and unrelated same-epoch snapshots do not establish a discovery baseline, the opening's fresh lit response renders without discovery ink or announcement, and saved viewport/selection memory remains independent

#### Scenario: World first opens after the area tab
- **WHEN** an opening starts on area and later selects world with a retained world cache
- **THEN** only area was requested initially, the world tab's own fresh response establishes the opening baseline without replay, and the cache cannot qualify a world discovery

#### Scenario: Closed or retired requests cannot qualify a new opening
- **WHEN** a response completes after close, during a later opening waiting for its own response, or after transport generation or epoch retirement
- **THEN** it cannot qualify the later opening's baseline or reveal; existing cache/admission rules remain in force, unrelated map caches are not cleared to implement freshness, and retired view memory and pending requests remain unusable

#### Scenario: Freshness requires the requested map publication and settled action
- **WHEN** an opening request receives its action result before the matching committed map publication, its publication before the result, a partial multipart transfer, a failure or an unavailable map body
- **THEN** only the successfully settled request with a completely adopted available world body establishes the baseline; arbitrary revision changes, cached-body clones and partial transfers cannot qualify it, and no polling or retry queue is introduced

#### Scenario: A committed move is observed while opening readiness is pending
- **WHEN** a movement commits before opening readiness and its active-scope refresh follows the opening response in either supported action-result/body order
- **THEN** the opening response establishes a silent baseline; an unlit baseline followed by the movement refresh's eligible newly lit district reveals once without remounting, while a discovery already included in the first fresh baseline remains silent; normal dispatcher admission and single-refresh behavior remain unchanged
