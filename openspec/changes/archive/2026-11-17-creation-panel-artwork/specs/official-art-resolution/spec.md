# Spec Delta

## MODIFIED Requirements

### Requirement: Official payloads are catalog-derived, confined, and fall through when unresolvable
Official candidates SHALL use snapshot-admitted fingerprinted same-origin URLs and validated metadata or personal geometry. Applicable missing/rejected/configured-source faults SHALL remain attributed at their precedence positions before fallthrough. Optional never-configured sources SHALL add no fault. Official availability SHALL never complete a generation job or expose roots, prompts or license text.

#### Scenario: A resolved official default presents with metadata geometry
- **WHEN** a preset-born character's preset content reference has a valid catalog directory declaring a manifest rectangle and a non-identity stage
- **THEN** the payload carries the fingerprinted official URL, the declared validated rectangle, the declared validated stage, and no path, license, or prompt text

#### Scenario: No declared stage defaults to identity placement
- **WHEN** an official image resolves from a directory with no manifest or no valid declared stage
- **THEN** the payload carries the fitted default rectangle and the identity stage triple, personal overrides taking precedence once personalization lands

#### Scenario: A disappeared official entry falls through
- **WHEN** an entity whose content reference previously had official artwork presents after an update removed that content directory, with no restart gap (the new startup's snapshot simply lacks it)
- **THEN** resolution falls through to the built-in silhouette with no exception, no preference deletion, and no acquisition attempt

#### Scenario: An official image is never labeled generated
- **WHEN** an official image can display while a recorded generation job is pending or failed
- **THEN** the descriptor preserves that independent generation state without fabricating completion or mutating any asset/gallery record

#### Scenario: A personal selection joins the payload in the personalization capability
- **WHEN** an entity has an explicit personal official selection made through the personalization capability
- **THEN** that explicit personal selection joins the official payload in place of the default image, selection behavior owned by the personalization capability

#### Scenario: An absent or refused catalog entry falls through cleanly
- **WHEN** an official source is unconfigured, or explicitly selected/configured but missing or refused
- **THEN** normal unconfigured absence contributes no fault; broken explicit/configured sources contribute an attributed fault before remaining candidates, with no preference deletion or network acquisition

#### Scenario: Replaced bytes update the image under the same stable identity
- **WHEN** the bytes at the same root-relative path are replaced and the server restarts
- **THEN** the presented image updates under the same stable identity while the entity's personal selection identity is retained, selection behavior owned by the personalization capability

#### Scenario: A preset preview uses only its own catalog default
- **WHEN** creation previews a registered synthetic preset directly from its preset key
- **THEN** its artwork offers only that content reference’s snapshot-admitted default as an official image attempt with validated geometry, and never consults a character’s gallery or personal selection

#### Scenario: Absent preset artwork is normal preview absence
- **WHEN** the mounted snapshot admits no default for the preview’s own preset reference
- **THEN** the preview offers no image attempt or fault and falls through to its built-in alpha terminal without acquisition, record creation or policy change
