# road-network-artifact Specification

## Purpose
Define the authored road parameters and the frozen road artifact format, so that the offline generator and the game share one validated contract for decoding and freshness.

## Requirements

### Requirement: Road parameters are a validated authored document
The authored source set SHALL include one optional road parameter document. A supplied document SHALL be validated with no default substitution, and an absent document SHALL leave authoring load unaffected.

#### Scenario: Invalid content is rejected
- **WHEN** a candidate road parameter document has an unknown field, an unknown node kind, or a value outside its declared range
- **THEN** authoring load rejects the candidate with a source diagnostic naming the field

#### Scenario: Unknown forbidden region is rejected
- **WHEN** a road parameter document forbids a region the continent does not declare
- **THEN** authoring load rejects the candidate with a diagnostic naming that region

#### Scenario: An absent document loads
- **WHEN** a synthetic world has no road parameter document
- **THEN** authoring load succeeds and the world reports no road parameters

#### Scenario: Tuning leaves other artifacts current
- **WHEN** only the road parameter document changes
- **THEN** the district partition signature and the elevation source signature do not change

### Requirement: The road artifact decodes and reports freshness without generation dependencies
Artifact encoding, decoding, metadata and freshness SHALL work without the generation extra, and any change to a road input SHALL read as stale.

#### Scenario: Codec round trip
- **WHEN** a synthetic network is encoded and decoded
- **THEN** its roads and cell set are equal to the input, and encoding it again gives identical bytes

#### Scenario: Changed input reads as stale
- **WHEN** a continent, location, settlement or road parameter source, the elevation fingerprint or a region speed changes
- **THEN** the source signature changes and the artifact is not current

#### Scenario: Unrelated sources stay current
- **WHEN** only an interior document or the district document changes
- **THEN** the source signature does not change

#### Scenario: A missing signature is never current
- **WHEN** freshness is asked with no current source signature
- **THEN** the artifact is not current

#### Scenario: Corrupt artifact is rejected
- **WHEN** an artifact has a wrong version, a malformed field, an odd cell list, a cell outside the frame or a fingerprint that disagrees with its roads
- **THEN** decoding raises the road document error

#### Scenario: Independent decoding
- **WHEN** the codec is imported in a fresh interpreter with NumPy and SciPy blocked
- **THEN** encoding, decoding and freshness complete

### Requirement: The road artifact marks spur roads
The artifact SHALL mark each spur road with the settlement that owns it and SHALL leave a trunk road unmarked. Decoding SHALL expose the owner of every marked road, and an artifact with no marked road SHALL encode to the same bytes as before the mark existed.

#### Scenario: Spur round trip
- **WHEN** a synthetic network with one trunk and one spur is encoded and decoded
- **THEN** the decoded roads and cell set equal the input, the spur's owner is exposed, the trunk has no owner, and encoding again gives identical bytes

#### Scenario: Unmarked networks keep their bytes
- **WHEN** a synthetic network with no spur is encoded with no owner information and with an empty owner mapping
- **THEN** both outputs are identical and contain no spur key

#### Scenario: Invalid owner
- **WHEN** an artifact row's owner is not a string or is neither of the row's two settlements, or the owner was changed without updating the fingerprint
- **THEN** decoding raises the road document error
