# Spec Delta

## Purpose

Install and run the independent local editor service and browser workspace with bounded authenticated domain APIs. This capability defines the observable mechanism boundary for its consumers.

## ADDED Requirements

### Requirement: Editor runs without game services or dependencies
The editor SHALL install, load maps and serve its browser application in an independent environment without the game framework, database, frontend bundle, Node runtime or external network assets.

#### Scenario: Independent launch
- **WHEN** the editor is installed from its own locks with Evennia and Django absent and the game stopped
- **THEN** a real browser opens continental, settlement and interior snapshots with core-derived geometry and diagnostics

#### Scenario: Local build assets
- **WHEN** the built editor is served with Node unavailable and network access denied
- **THEN** essential UI and shared map drawing remain available without CDN or game dist requests

### Requirement: Local API confines and authorizes workspace access
The service SHALL enforce expected Host/Origin, launch-session authorization for mutations, bounded data input and allowlisted confined document access.

#### Scenario: Rejected request
- **WHEN** a foreign origin/host, absent mutation token, traversal path or escaping symlink is submitted
- **THEN** the request is rejected without file changes or execution

#### Scenario: Untrusted content
- **WHEN** oversized data or authored executable-looking prose/scene URLs are supplied
- **THEN** data limits reject before expensive processing and displayed text causes no markup execution or arbitrary asset fetch

