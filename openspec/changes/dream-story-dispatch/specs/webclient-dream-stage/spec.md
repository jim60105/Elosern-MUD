# Spec Delta

## ADDED Requirements

### Requirement: Dream confirmation displays the frozen experience requirements

The existing keepsake/draft presentation SHALL show readable bounded experience requirements for the version being confirmed alongside its direction. Rehydration and confirmation SHALL preserve server-authored requirement identity with the draft/version. Summary edits SHALL invalidate stale requirement confirmation until the corresponding version is presented. Existing exit, local-word preservation and accessibility behavior SHALL remain intact, without JSON or a new story panel.

#### Scenario: Player sees the intended executable experience
- **WHEN** the south-gate girl request is prepared for confirmation
- **THEN** the current dream surface displays place/new-role/private-commission meaning and sends the exact shown current version requirements with confirmation

#### Scenario: Reconnect and local edit
- **WHEN** the saved draft republishes during unsent local editing
- **THEN** unsent words survive, current requirements track the reviewed version and unseen or stale server requirements are not silently confirmed

#### Scenario: Confirmation closes without preparation lock
- **WHEN** valid confirmation commits with generation still pending
- **THEN** the dream stage closes and waking controls remain usable; preparation/waiting messages appear through ordinary output rather than keeping the dream modal locked
