## MODIFIED Requirements

### Requirement: Combat results update canonical panels and preserve narrative logs
After an admitted combat action settles, the server SHALL emit every returned EventLog and terminal
message through Evennia's ordinary escaped text output path. The dispatcher SHALL then publish
canonical `status`, `context_actions`, and `art` replacements at one newer revision before sending
the matching safe `ui_action_result`, so a combat result that changes the participant roster, combat
mode, or session state replaces the portrait catalog and scene in the same `ui_update`. When the
action settled an ordinary round, the same publication SHALL also carry the `combat_beats` panel
owned by the `webclient-combat-beats` capability, at the same revision as `status`. The panel is
the only structured account of the round's exchange, and the text output stays the authoritative
narrative. The browser SHALL keep submission locked until that declared presentation revision is
accepted. It SHALL NOT parse narrative prose to update resources, participants, round, art, beats,
or menu state.

#### Scenario: One combat round updates text, panels, and art
- **WHEN** an accepted cast completes a nonterminal round
- **THEN** every committed EventLog appears in narrative, status, combat choices, and the art catalog
  reflect committed state at one newer revision, and the dock unlocks only after that revision is
  accepted

#### Scenario: A defeated or fled participant leaves the art catalog in the same revision
- **WHEN** an accepted combat action removes a participant from the session (defeat, flee, or
  terminal settlement)
- **THEN** the `art` panel at the same newer revision no longer contains that participant's catalog
  entry, and the browser never keeps a portrait for a no-longer-present entity

#### Scenario: Rejected preflight emits no fabricated combat prose
- **WHEN** current deterministic validation rejects before initiative
- **THEN** no combat EventLog is fabricated, the result contains a stable safe reason, and refreshed panel state permits another legal choice

#### Scenario: Duplicate request does not repeat a round or prose
- **WHEN** one live request ID is delivered twice
- **THEN** the adapter and combat round execute once, EventLog text is emitted once, and the duplicate receives the cached result

#### Scenario: The round's beats ride the status revision
- **WHEN** an accepted cast completes a nonterminal round
- **THEN** the same `ui_update` that carries `status` also carries `combat_beats` for that round, and the `ui_action_result` names that revision and carries no beat, EventLog, or round-record field
