# Spec Delta

## Purpose

Provide cut over all authored backend/text delivery and version-3 protocol through deterministic, independently testable behavior while preserving authoritative game ownership and offline play.

## ADDED Requirements

### Requirement: Scene selection is independent of content provider
Static file-backed and generated package-backed topics SHALL use the same source-aware scene selection, request identity, replay and transactional session contract. Generated topics SHALL not be limited to one host line or excluded by static registry membership.

#### Scenario: Generated scene selection uses the shared path
- **WHEN** a validated generated role exposes a multi-line formal topic
- **THEN** web and text select its stable ID through the same qualification/effect/session path as a static topic

### Requirement: Authored selection delivers complete scenes atomically
Authored selection SHALL revalidate host context before applying existing deterministic effects and storing the complete attributed delivery. Replayed deliveries and duplicate or stale transport selections SHALL cause no additional affinity, reward or world-time advancement.

#### Scenario: Duplicate after another topic
- **WHEN** a client repeats an earlier request envelope after a different topic selection
- **THEN** it is rejected as stale or returns its original receipt with no second effect

#### Scenario: Delivery write fails after affinity
- **WHEN** a failure occurs while recording an otherwise accepted formal scene
- **THEN** database and cached affinity/session state match their preselection state and no scene success is exposed

### Requirement: Text and browser resolve the same authored topic
Both interfaces SHALL select the same stable authored topic and complete scene without model services. Generated story and freeform dialogue SHALL retain their existing authority, literal-greeting and effect contracts.

#### Scenario: Offline attributed text
- **WHEN** models and image services are disabled and a known authored keyword is selected in text
- **THEN** all actor/host/narration lines emit in order without extra clock changes

#### Scenario: Guild reporting remains delegated
- **WHEN** 回報 is selected or a quest id is explicitly turned in
- **THEN** listing is read-only and the guild owner pays an eligible claim once

