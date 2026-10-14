# Spec Delta

## Purpose

Define room-aware scene source precedence, same-place retention and full-view behavior through canonical descriptors and shared resource loading.

## ADDED Requirements

### Requirement: Normal scenes use the complete authored source chain
A normal scene SHALL attempt explicit room official art, archetype generated art, optional operator archetype official art, required bundled type art, then a distinct declared town/forest terminal image. Source selection SHALL use authored scene type rather than game mode. Exhaustion SHALL produce a non-image background with persistent reached failures.

#### Scenario: Room override suppresses lower faults
- **WHEN** a healthy room image precedes a failed archetype job
- **THEN** the room image displays with no unused job failure

#### Scenario: Generated art wins before official defaults
- **WHEN** no room override resolves and generated plus operator/bundled type art coexist
- **THEN** the generated image wins; its generation state is independent of official availability

#### Scenario: Corrupt override stays visible
- **WHEN** a configured operator image fails and bundled art succeeds
- **THEN** bundled art displays with the reached operator fault

#### Scenario: Identical terminal is never retried
- **WHEN** forest_path or city_street bundled art fails and also names itself as terminal
- **THEN** that resource is attempted once and exhaustion uses non-image presentation

#### Scenario: Malformed scene metadata is explicit
- **WHEN** a scene lacks a valid archetype or supported scene definition
- **THEN** town terminal is attempted with a configuration-failure indication

### Requirement: Retention is scoped to unchanged scene and generation subject
A new scene identity SHALL immediately invalidate previous-place background content. Same-scene regeneration MAY retain a previously successful applicable image until a same/higher-priority replacement succeeds while continuing current attempts and reached-fault processing. Binding removal, revoked access, different subject or known failed retained source SHALL invalidate retention.

#### Scenario: Move drops the old background immediately
- **WHEN** a new logical place commits while its image is delayed
- **THEN** only that new place's own provisional bundled/terminal background may display

#### Scenario: Pending regeneration retains generated success
- **WHEN** the same scene and generation subject is pending and a lower bundled image loads first
- **THEN** the prior successful generated image stays visible without an error indication

#### Scenario: Failed regeneration remains visible
- **WHEN** the same subject reports failed regeneration while bundled art is healthy
- **THEN** the retained good image may remain and the reached generation failure is locally indicated

#### Scenario: Explicit removal invalidates retained room art
- **WHEN** a room official binding is removed or access revoked
- **THEN** the retained image is discarded and resolution follows the newly applicable chain

### Requirement: Provisional backgrounds never change precedence
A scene MAY load its own bundled/terminal resource provisionally. Provisional success SHALL NOT stop ordered resolution, and provisional failure SHALL remain latent until that resource's position is reached. A reached provisional result SHALL be reused without a duplicate attempt.

#### Scenario: Delayed preferred image still wins
- **WHEN** a provisional background fails while a room image is delayed and later succeeds
- **THEN** the room image wins without an unrelated provisional fault

#### Scenario: Reached provisional failure is reused
- **WHEN** all higher sources fail and resolution reaches the failed provisional resource
- **THEN** its failure is accumulated once and the distinct permitted terminal is tried once

### Requirement: Full view shares resolved scene truth
Scene full view SHALL consume the backdrop's successful source and failure state without a second resolution implementation. It SHALL never open a broken-image-only view. Text labels, accessible focus/close behavior and existing motion preferences SHALL remain.

#### Scenario: Full view shares a fallback error
- **WHEN** the backdrop displays a fallback with a reached error
- **THEN** full view uses that same successful resource and retains that same error

#### Scenario: No image cannot open a broken full view
- **WHEN** all image attempts are exhausted
- **THEN** the scene remains playable and no broken-only full view opens

