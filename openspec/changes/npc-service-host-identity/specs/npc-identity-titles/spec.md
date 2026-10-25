# Spec Delta

## MODIFIED Requirements

### Requirement: Guild service hosts reuse by service anchor and never rename
Service hosts SHALL reuse canonical authored profile provenance independent of component IDs/order and preserve existing identity and live state. Whole-row retirement SHALL use explicit source ownership and SHALL never consult title content.

#### Scenario: Canonical host remains stable
- **WHEN** a service ID, display-name declaration or capability order changes
- **THEN** the existing host dbref/name/location/state survive

#### Scenario: No title-based ownership inference
- **WHEN** a host carries an arbitrary historical title
- **THEN** it grants no lookup or deletion authority

#### Scenario: First sync creates the authored host
- **WHEN** no canonical profile-provenance host exists for a valid row
- **THEN** one host is created with its authored name/profile and resolved capability plan atomically

#### Scenario: Re-sync neither duplicates nor renames
- **WHEN** the canonical host exists and source name or capability order changes
- **THEN** its dbref/name/location/runtime state survive without a duplicate

#### Scenario: A host predating authored identities is reused, not backfilled
- **WHEN** an existing canonical npc_profile_key host has historical attributes
- **THEN** it is reused without name/title backfill or component-ID fallback

#### Scenario: An unrelated NPC with no service component survives convergence
- **WHEN** an unmanaged NPC shares a retired name but no source ownership
- **THEN** it is not deleted

#### Scenario: Duplicate service anchors fail closed
- **WHEN** two live hosts claim one canonical authored host profile
- **THEN** the complete operation rejects before host creation/deletion/configuration

#### Scenario: Anchor contention fails closed before any mutation
- **WHEN** canonical profile provenance has multiple claimants
- **THEN** a named integrity failure precedes all writes

#### Scenario: Convergence replaces the legacy-key cleanup as the deletion mechanism
- **WHEN** a managed lifecycle is synchronized
- **THEN** only explicit source ownership and whole-row retirement authorize deletion, never keys or component IDs

#### Scenario: A stale titleless candidate is deleted for recreation
- **WHEN** an NPC lacks current whole-row retirement authority
- **THEN** it survives regardless of old title or component IDs; losing a current host's last capability also preserves the host

#### Scenario: Component-less NPCs survive and anchored titled candidates are kept
- **WHEN** component-less or currently declared canonical hosts carry historical title attributes
- **THEN** they survive without any title-based ownership or lifecycle decision
