## ADDED Requirements

### Requirement: The ingress-maintained watcher registry resolves live sessions for targeted pushes

`web/webclient/presentation/watchers.py` SHALL expose `watchers_for(actor)` returning the live `(session, coordinator_epoch)` pairs currently watching that actor — each with the coordinator epoch current at query time — and SHALL be updated only by the WebClient ingress: every successful `synchronize_session` registers its session (covering both `ui_sync` and post-command refresh), and every registration prunes entries whose session is no longer connected or whose puppet changed.

#### Scenario: Every targeted push audience resolves through one registry

- **WHEN** a targeted panel push (dialogue reading, party, lore codex, travel log, or alignment facts) resolves its audience for a puppet
- **THEN** it receives exactly the live WebClient sessions watching that puppet with their current epochs, and sessions without a puppet or of non-webclient transports never appear

#### Scenario: Sync and command settlement register the same live session

- **WHEN** a puppeted session synchronizes through `ui_sync` and later through a post-command refresh
- **THEN** `watchers_for(actor)` returns exactly the live WebClient sessions for that actor, each with the coordinator epoch current at registration time

#### Scenario: A disconnected session is pruned on the next registration

- **WHEN** a session disconnects and any later registration occurs
- **THEN** the disconnected session no longer appears in `watchers_for` results, and a matching epoch guard would have dropped its push anyway
