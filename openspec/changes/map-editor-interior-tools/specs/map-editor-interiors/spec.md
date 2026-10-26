# Spec Delta

## Purpose

Implement coordinate-free permanent interior room/connection editing and separately persisted layout controls. This capability defines the observable mechanism boundary for its consumers.

## ADDED Requirements

### Requirement: Interior editing keeps topology separate from presentation layout
Interior tools SHALL edit permanent room identity/prose/scene and named directed connections without requiring service metadata or physical coordinates, while layout operations change only editor preferences.

#### Scenario: Standalone room
- **WHEN** a non-service interior room is created or duplicated
- **THEN** it receives a new stable identity and valid source topology without creating a service/NPC record

#### Scenario: Layout-only change
- **WHEN** rooms are rearranged or positioned through keyboard inputs
- **THEN** one layout document is saved and no runtime geometry, physical distance or room source coordinates are introduced

#### Scenario: Existing service room
- **WHEN** an existing joined room is inspected and its prose is edited
- **THEN** its stable service-room identity remains and no duplicate interior is created

