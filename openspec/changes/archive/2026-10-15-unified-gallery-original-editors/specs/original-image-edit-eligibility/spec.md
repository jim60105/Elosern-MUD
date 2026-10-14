# Spec Delta

## Purpose

Constrain gallery crop and placement saving to the exact decoded original image while keeping substitutes and the adult reference display-only.

## ADDED Requirements

### Requirement: Only decoded original dimensions enable saving
Crop and placement saves SHALL be enabled only after the exact requested original resource successfully decodes with usable dimensions and existing mutation admission permits saving. A silhouette, other card, scene fallback or adult reference SHALL never be an edit target.

#### Scenario: Failed original stays unsaveable
- **WHEN** an original fails while a display substitute or adult ruler loads
- **THEN** save remains disabled and no geometry dispatch occurs

#### Scenario: A new original recovers eligibility
- **WHEN** the exact original changes to a repaired resource version and decodes
- **THEN** its dimensions enable saving only for that new original identity

#### Scenario: Stale dimensions cannot enable saving
- **WHEN** subject/card/revision changes before an older load callback settles
- **THEN** the older callback cannot authorize a save or replace dimensions

### Requirement: Editing failures have distinct visible states
Editors SHALL distinguish loading from failed-original states, remove broken original images and show a persistent accessible local failure explanation. The fixed adult reference SHALL remain a ruler, be observed separately and report its own resource failure.

#### Scenario: Original failure removes broken images
- **WHEN** the original request returns invalid image bytes
- **THEN** both original and crop-preview broken img elements disappear with failure explanation

#### Scenario: Ruler failure is explicit
- **WHEN** the fixed adult reference fails while the original is healthy
- **THEN** the ruler is absent with its own local indication and can never contribute original dimensions or persisted geometry

