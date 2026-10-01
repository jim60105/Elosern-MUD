## ADDED Requirements

### Requirement: A newly created service host receives its authored card
When synchronization creates a service host, it SHALL initialize the host's compact NPC card from the place's host profile, with `profile` provenance naming that profile, in the same transaction as the host's creation, before the host is published as usable. A roster row whose profile does not resolve SHALL fail synchronization before any write, naming the service. Synchronization SHALL NOT initialize, rewrite, or repair the card of a reused host: a restart, a registry reload, or an edit to the authored profile SHALL leave every existing host's effective card and persona version unchanged. Two hosts created from equal profiles SHALL carry independent cards.

#### Scenario: A created host carries its profile card
- **WHEN** synchronization creates the host for a place naming a synthetic profile
- **THEN** the host's persona equals that profile's card and its persona metadata is at version 1 with `profile` provenance naming the profile

#### Scenario: Restart never overwrites an edited host
- **WHEN** a host's card was edited to version 2 and synchronization runs again after the authored profile text changed
- **THEN** the host's card and version 2 are unchanged

#### Scenario: A reused host without a card is left untouched
- **WHEN** synchronization reuses an existing host that carries no persona metadata
- **THEN** synchronization writes no persona or metadata for it

#### Scenario: A failed initialization leaves no host
- **WHEN** the card initialization raises while synchronization creates a host
- **THEN** the startup transaction rolls back and no host for that service exists
