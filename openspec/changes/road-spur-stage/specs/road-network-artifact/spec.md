# Spec Delta

## ADDED Requirements

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
