# Spec Delta

## MODIFIED Requirements

### Requirement: Every presentation payload distinguishes official, runtime, and silhouette origin
Every canonical portrait source description SHALL distinguish each real resource's authored origin and separate alpha terminal from independent generation state. Consumers SHALL use the server-authored resource origin and successful load state, never infer source or generated success from URL presence. The art owner SHALL supply this vocabulary to the owning canonical wire cutovers; unchanged current flat serializers remain on their existing registered contract until then.

#### Scenario: Three sources, three discriminators
- **WHEN** three subjects resolve an official image, a generated card, and a built-in silhouette respectively
- **THEN** each payload carries the discriminator naming its own source and no payload's discriminator can be derived from its URL shape

#### Scenario: Presence of a URL proves nothing
- **WHEN** a client receives two payloads that both carry a media URL but different discriminators
- **THEN** the client renders each per its discriminator and neither is treated as the other's kind

#### Scenario: One vocabulary for current and future payload surfaces
- **WHEN** the art panel portrait catalog and the roster row portraits present resolved portrait payloads, and a read model that later carries such a payload presents
- **THEN** all of them use the same origin-discriminator vocabulary, the surfaces today being the art panel portrait catalog and the roster row portraits

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

