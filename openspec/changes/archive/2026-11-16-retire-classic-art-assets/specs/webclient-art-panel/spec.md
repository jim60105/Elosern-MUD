## MODIFIED Requirements

### Requirement: Resolved artwork carries stage without changing asset or placeholder truth
Resolved gallery-card portraits SHALL carry validated card stage. A malformed stored stage reaching presentation SHALL degrade to `{scale: 1.0, x: 0.0, y: 0.0}` with one bounded `art_stage_invalid` warning carrying the subject. Placeholders SHALL carry null stage.

#### Scenario: Gallery portrait carries its card placement
- **WHEN** a subject resolves to a gallery card with stage `{scale: 0.6, x: 0.1, y: -0.2}`
- **THEN** its resolved portrait, art catalog and actor source carry that triple unchanged

#### Scenario: Malformed stored stage degrades without failed snapshot
- **WHEN** stored malformed stage reaches defensive portrait payload construction
- **THEN** the portrait carries identity stage and one bounded art_stage_invalid warning with subject, while the snapshot remains valid

#### Scenario: Non-card assets and placeholders preserve truthful defaults
- **WHEN** fallback or scene resources and placeholder branches are resolved
- **THEN** assets carry identity stage, placeholders carry null, and scene visuals remain unchanged

#### Scenario: Exact art validation lands in lockstep
- **WHEN** an otherwise valid asset carries a valid stage triple or a placeholder carries null stage
- **THEN** Python and dependency-free Node validators both accept; missing stage, wrong shape, non-finite/bool or out-of-bounds asset stage and non-null placeholder stage reject on both sides

#### Scenario: Non-card assets carry identity stage
- **WHEN** fallback portraits or scene resources resolve
- **THEN** each carries identity stage

#### Scenario: Producers and consumers retain the stage shape
- **WHEN** gallery/art/roster portrait production and stage/dialogue actor consumption run
- **THEN** they retain this stage shape, with exact Python and dependency-free Node validators
  deployed together

#### Scenario: Scenes ignore stage and dialogue hosts need no new field
- **WHEN** a scene renders, or a dialogue host references the art catalog
- **THEN** scene rendering ignores stage, and no new dialogue-host field is required
