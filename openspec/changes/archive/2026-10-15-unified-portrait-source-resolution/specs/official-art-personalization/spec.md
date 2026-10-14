# Spec Delta

## MODIFIED Requirements

### Requirement: Stale official selections are retained but ignored for resolution
Unresolvable personal official selections SHALL remain stored and contribute an attributed fault at their original precedence position before the remaining runtime-default, classic, official-default and alpha sources. Resolution SHALL not delete preferences or images. Replaced bytes at the same identity SHALL use the refreshed snapshot fingerprint.

#### Scenario: Removed image falls through, preference survives
- **WHEN** the official image a player selected disappears from a later prepared directory and the server restarts
- **THEN** presentation falls through to the remaining chain, the stored preference remains, and no runtime card was affected

#### Scenario: Same identity resolves new bytes after restart
- **WHEN** an operator replaces the bytes at the selected identity's path and the server restarts
- **THEN** the retained selection presents the new bytes under the same identity with a refreshed cache fingerprint, and the player's selection state is unchanged

#### Scenario: Unresolvable-identity causes enumerated
- **WHEN** the selected identity is no longer resolved because it was removed by an update, refused by admission, or absent from the content directory
- **THEN** resolution treats the selection as stale and ignores it while retaining the preference

#### Scenario: Surviving identity picks up updated bytes
- **WHEN** a selection's identity still exists and its content changed across a maintenance restart
- **THEN** the selection SHALL resolve its updated bytes after the restart — same identity, new content, no re-selection required

#### Scenario: Broken personal selection remains visible after fallback
- **WHEN** a retained explicit official selection is missing and the runtime default loads
- **THEN** the preferred-source fault remains locally indicated while preference and files stay unchanged

