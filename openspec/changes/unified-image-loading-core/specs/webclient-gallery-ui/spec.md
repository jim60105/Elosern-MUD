# Spec Delta

## MODIFIED Requirements

### Requirement: Stage transforms affect full figures and never avatar cover crops
Stage and drawer full-figure portraits SHALL render contain/bottom-aligned with bottom-center origin, applying frame-relative translation followed by scale in the declared transform list. Missing/null stage SHALL render identity. Positive y SHALL move down; offsets SHALL remain independent of scale. Stage edits SHALL be immediate and SHALL NOT change the portrait source key or trigger crossfade.

#### Scenario: A child stays on the same ground line
- **WHEN** stage scale changes from 1.0 to 0.6 with x and y zero
- **THEN** the full figure scales around 50% 100%, its feet anchor and ground ellipse remain fixed, and no new source crossfade occurs

#### Scenario: Translation uses frame dimensions at every scale
- **WHEN** x is 0.1 and y is -0.2 at scales 0.6 and 2.0 in the same frame
- **THEN** both render offsets of 10% frame width and -20% frame height; custom properties carry the exact triple and enlarged figures are not newly clipped

#### Scenario: Null stage and cover crop remain unchanged
- **WHEN** stage is missing/null or a nonidentity triple is supplied to a cover-mode avatar
- **THEN** stage mode normalizes missing/null to identity and cover mode uses the same faceObjectPosition with no stage transform

#### Scenario: Ground and shadow behavior is preserved
- **WHEN** a stage transform is applied to a full figure
- **THEN** the ground anchor stays fixed, the figure shadow follows the figure, and existing overflow-visible behavior remains

#### Scenario: Cover crops stay face-rect driven
- **WHEN** stage transforms are active elsewhere in the gallery
- **THEN** gallery/detail cards, roster avatars and party-strip cover crops remain face-rect driven

#### Scenario: Inline placeholders are untouched
- **WHEN** the stage-transform work lands
- **THEN** existing inline stage placeholders remain unchanged

#### Scenario: Geometry revision reuses decoded resource
- **WHEN** a descriptor revision changes stage but resource identity/version is unchanged
- **THEN** updated placement applies immediately to already decoded bytes, with no new resource request, source-key change or crossfade

