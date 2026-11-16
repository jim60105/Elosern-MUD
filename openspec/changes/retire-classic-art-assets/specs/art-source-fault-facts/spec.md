## MODIFIED Requirements

### Requirement: Faults are attributed to requested sources
The startup snapshot SHALL preserve bounded requested-default, rejected-identity and selected-source metadata faults. A broken declared default SHALL precede its deterministic substitute. Unselected rejected siblings SHALL remain diagnostics and SHALL NOT taint a healthy selected source.

#### Scenario: Default faults precede substitution
- **WHEN** a manifest default is missing or rejected and a valid sibling is selected deterministically
- **THEN** resolution can attribute a fault to the declared default before the substitute

#### Scenario: Selected metadata falls back safely
- **WHEN** selected-source geometry or applicable manifest metadata is invalid
- **THEN** a metadata fault accompanies safe geometry without blocking valid image bytes

#### Scenario: Unselected rejection remains isolated
- **WHEN** one unselected sibling is corrupt while the requested image is healthy
- **THEN** the healthy image has no presentation fault from that sibling

#### Scenario: Unified chain preserves reached source attribution
- **WHEN** a scene or portrait explicit official choice is missing and its generated default resolves
- **THEN** the missing choice contributes its own fault before that default, unrelated lower official siblings contribute none, and no preference changes

#### Scenario: Removed sources produce no fault positions
- **WHEN** a descriptor is built after classic retirement
- **THEN** only current gallery, official and declared terminal sources contribute faults; no classic source or fixed-output lookup occurs
