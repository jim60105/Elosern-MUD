# official-art-resolution Specification

## Purpose
Define official artwork's presentation semantics: the origin discriminator that keeps official, mutable runtime, and built-in-silhouette images distinguishable in every versioned payload; the confined, catalog-derived official payload fields; the eligibility ordering that official presentation must respect; and the deterministic, offline, non-mutating character of the extended chain.

## Requirements

### Requirement: Every presentation payload distinguishes official, runtime, and silhouette origin
Every portrait presentation payload SHALL carry a server-authored origin discriminator distinguishing an official read-only image from the subject's existing runtime sources (generated/seed card, classic asset) and from a built-in silhouette. The discriminator SHALL be computed by the server from the resolution branch that produced the payload, and NO consumer SHALL infer origin, source, or generation success from the mere presence of a media URL.

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
An official payload SHALL carry: the fingerprinted same-origin media URL for the content reference's default image, the face rectangle and stage from valid directory metadata or fitted defaults validated by the existing geometry rules, and the runtime entity's existing name/identity fields. It SHALL NOT expose filesystem roots, deployment sources, license text, manifest text, or prompts, and SHALL NOT count as a generated portrait — an official image is not a `done` asset.

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
- **WHEN** a subject presents an official image while its classic/gallery state is untouched
- **THEN** the payload does not report a generated/done portrait status for the subject's own art state, and no asset or gallery record was created or mutated

#### Scenario: A personal selection joins the payload in the personalization capability
- **WHEN** an entity has an explicit personal official selection made through the personalization capability
- **THEN** that explicit personal selection joins the official payload in place of the default image, selection behavior owned by the personalization capability

#### Scenario: An absent or refused catalog entry falls through cleanly
- **WHEN** the content reference resolves no catalog entry because it is absent or was refused at admission
- **THEN** resolution continues through the remaining chain (built-in silhouette) without error, without deleting any stored preference, and without a network attempt

#### Scenario: Replaced bytes update the image under the same stable identity
- **WHEN** the bytes at the same root-relative path are replaced and the server restarts
- **THEN** the presented image updates under the same stable identity while the entity's personal selection identity is retained, selection behavior owned by the personalization capability

### Requirement: Eligibility checks order before official and runtime presentation
Portrait age and eligibility validation SHALL run before official or runtime character artwork may be presented, exactly as it guards generation today: neither mounted-directory metadata nor a crafted media URL SHALL bypass the existing checks, and a rejected character SHALL present the existing truthful placeholder/placeholder-selector outcome with no subject key, no URL, and no prompt content.

#### Scenario: Directory metadata cannot unlock an ineligible character
- **WHEN** a character whose canonical ages fail the existing check has a content reference whose official directory is fully valid
- **THEN** no official URL or rectangle is presented for it and the truthful placeholder is returned

#### Scenario: Presentation adds no bypass
- **WHEN** a direct request names a well-formed official media URL for an ineligible entity's content directory
- **THEN** presentation-layer surfaces never construct such a URL, and the media route's own rules (capability `art-queue-worker`) remain the only official URL admission

#### Scenario: Built-in placeholder selection keeps its validated attributes
- **WHEN** built-in placeholder selection runs for an entity without a named portrait policy
- **THEN** it remains able to use validated entity attributes for that selection

#### Scenario: Official artwork never changes the eligibility outcome
- **WHEN** eligibility is evaluated for an entity once with official artwork present and once without
- **THEN** the eligibility outcome is identical whether or not official artwork exists for the entity

### Requirement: The extended chain stays deterministic, offline, and side-effect-free
Extending the chain with the official-default step SHALL preserve the existing purity guarantees: resolution SHALL be a function of stored state plus the startup official snapshot only, and SHALL perform no network call, filesystem write, job enqueue, or record mutation. It SHALL NOT let a catalog DEFAULT replace an entity's own resolved runtime image: a subject with a resolvable card or classic asset SHALL keep presenting it even when official artwork exists.

#### Scenario: Runtime art outranks official defaults
- **WHEN** a subject resolves a gallery default card and its content reference also has official artwork
- **THEN** the card is presented with its runtime discriminator and the official entry remains merely selectable

#### Scenario: Resolution performs no writes
- **WHEN** a hundred official-backed entities present across snapshots
- **THEN** no asset record, queue record, gallery record, stored file, or entity attribute changed

#### Scenario: The selection exemption is the player's own choice
- **WHEN** (after personalization lands) a subject with a `done` classic asset explicitly selects a resolving official image and later clears the selection
- **THEN** the selected official image presents while set and the classic asset presents again after clearing, with no mutation by either act — the outranking was the player's decision, not a catalog default replacing runtime art

#### Scenario: Artwork updates never switch runtime images to official defaults
- **WHEN** official artwork is replaced or added for a subject whose image was player-selected or generated
- **THEN** that player-selected or generated image keeps presenting — the update never switches it to an official default

#### Scenario: The personal selection is exempt by construction
- **WHEN** the personal official selection added by `official-art-personalization` is set
- **THEN** it is exempt from the catalog-default protection by construction — it is itself the player's explicit choice, presented at the personal-default slot ahead of the classic asset exactly as design §7 orders it, and clearing it restores the pre-selection resolution unchanged with nothing mutated by either act
