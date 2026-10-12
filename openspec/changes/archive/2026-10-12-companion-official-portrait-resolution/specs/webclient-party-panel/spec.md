# Spec Delta

## MODIFIED Requirements

### Requirement: The party panel is an exact read-only version-2 presentation panel
The party panel SHALL present one ordered row per exact NPC in the canonical roster, including dual membership. Existing version-2 identity/display/portrait/HP/bond-stage vocabulary, possession owner resolution, unavailable forms and read-only behavior SHALL remain; server/client validators SHALL extend the version-2 shape together. Each row SHALL add `membership` with boolean `general` and ordered `temporary_commissions`; the panel SHALL add `general_quota` with integer `used` and `limit`.

#### Scenario: Full general party plus escorts is complete
- **WHEN** four general members and two temporary-only members are presented
- **THEN** six ordered rows appear, general usage is four of four, every temporary actor is reachable through existing controls and no quota-based truncation occurs

#### Scenario: Dual member is one truthful row
- **WHEN** a general member carries two escort reasons
- **THEN** one row marks general true and identifies both commissions without duplicate identity or raw affinity

#### Scenario: Stale and dangling bindings do not leak
- **WHEN** membership references a deleted actor or invalid temporary source, or a possessed actor has no valid owner
- **THEN** stale rows/reasons are filtered through canonical readers and invalid-owner presentation uses the shared unavailable form

#### Scenario: Shape validators and clients change together
- **WHEN** server, protocol mirror and Vue validators receive the extended panel or malformed metadata/quota
- **THEN** all accept the same valid shape and reject malformed shapes while retaining existing portrait/HP/display bounds

#### Scenario: A two-companion party serializes exactly the six-key bounded rows
- **WHEN** two general members are presented through the extended version-2 panel
- **THEN** each preserves the existing six NPC fields and adds validated membership metadata, while the panel separately reports general quota usage

#### Scenario: The raw affinity number never appears
- **WHEN** any party payload is serialized
- **THEN** the raw affinity number appears nowhere in the payload

#### Scenario: Possession keeps listing the owner's party
- **WHEN** the player possesses one of her two companions and the next full snapshot arrives
- **THEN** `party.slots` still carries both companions — the possessed NPC among them — with the owner-keyed bond stages, and a client can join the front figure to the banner by identity

#### Scenario: A possessed stranger's party is unavailable, not empty
- **WHEN** the session actor is an NPC whose `party_member` back-reference names no live player and a snapshot presents the party panel
- **THEN** the panel takes the shared unavailable form rather than an available empty row list

#### Scenario: An empty party is an available empty list
- **WHEN** a puppeted explorer with no companions receives a full snapshot
- **THEN** `party` is available with `slots` exactly `[]` and no unavailable reason

#### Scenario: Stale membership bindings never reach the wire
- **WHEN** a player's stored party list contains a database identity whose NPC no longer exists
- **THEN** the party panel's slots omit that identity without error and validation accepts the
  payload

#### Scenario: Validation rejects row-shape drift
- **WHEN** a panel contains missing/unknown keys, malformed membership or quota, numeric bond stage, invalid HP, display or portrait reference
- **THEN** server and client mirrors reject identically; a fifth valid temporary row is accepted

#### Scenario: Creation-pending puppets see the unavailable form
- **WHEN** a creation-pending puppet receives a snapshot
- **THEN** `party` uses the shared unavailable form with its standard reason

#### Scenario: Identity is the database identity shared with combat rows
- **WHEN** a slot row is serialized
- **THEN** `identity` is the companion's positive integer database identity — the same field a
  combat participant row carries, so a client can join the two panels

#### Scenario: Display names honor the shared bound
- **WHEN** the companion's canonical NPC display name exceeds the shared display-name bound
- **THEN** `display_name` is the canonical name truncated to that bound

#### Scenario: portrait_ref is the art panel's opaque reference format
- **WHEN** the existing art resolution chain yields a real image for a companion's named portrait subject, through a matching equipment-bound card, personal official selection, record default card, classic runtime asset or mounted official default
- **THEN** `portrait_ref` is the companion's opaque ASCII decimal catalog key of 1–32 characters, in the same format used by the art panel
- **AND** for the companion present in the same snapshot's art view, that key resolves in `art.portrait_catalog` to the chain-selected image; an official image has `origin: official` and its admitted `/art/official/...` URL

#### Scenario: A missing portrait is null, not fabricated
- **WHEN** the companion has no named portrait subject or the complete art chain yields no real runtime or official image, including an absent or unresolvable personal official selection and no mounted official default
- **THEN** `portrait_ref` is `null` and the client renders its truthful initial-letter placeholder, even if decorative silhouette fallback artwork is available

#### Scenario: Personal official selection works without runtime cards
- **WHEN** a present named companion has a resolving retained personal official selection, no runtime card and no classic runtime asset
- **THEN** its non-null `portrait_ref` resolves in the same snapshot's `art.portrait_catalog` to that selected official image with `origin: official` and its `/art/official/...` URL
- **AND** no runtime default card is required and official artwork is never appended to the card list

#### Scenario: Mounted official default works without a gallery record
- **WHEN** a present preset-born named companion has a mounted official content-directory default and no gallery record or classic runtime asset
- **THEN** its non-null `portrait_ref` resolves in the same snapshot's `art.portrait_catalog` to that official default with `origin: official` and its `/art/official/...` URL
- **AND** the gallery record remains absent

#### Scenario: Equipment matching retains chain precedence
- **WHEN** a companion has a matching equipment-bound runtime card and a resolving personal official selection
- **THEN** its `portrait_ref` resolves to the runtime card with `origin: runtime`
- **AND** precedence remains equipment-bound matching card > personal official selection > record default card > classic runtime asset > mounted official default > null, subject to the chain's existing eligibility and validation rules

#### Scenario: HP fields come from the true traits
- **WHEN** a slot row is serialized
- **THEN** `hp_current` and `hp_maximum` are non-negative integers from the companion's true traits

#### Scenario: bond_stage carries only the stage name
- **WHEN** a slot row is serialized
- **THEN** `bond_stage` is the canonical stage NAME string from the affinity rulebook's stage table

#### Scenario: The presenter is read-only and leak-free
- **WHEN** the party presenter runs
- **THEN** it does not mutate party membership, traits, affinity, combat, quest, or world state,
  and emits no live object or filesystem reference

#### Scenario: Portrait resolution never writes or invents
- **WHEN** the presenter resolves `portrait_ref` through the existing runtime and official art chain
- **THEN** any gallery record read is non-creating, and resolution never creates a record, queues generation, writes attributes or files, walks the official filesystem per render, or invents a URL
- **AND** official steps read the admitted startup catalog snapshot, official files remain read-only, and personal default mutual clearing and art-chain semantics remain unchanged

#### Scenario: A possessed NPC presents the bound owner's party
- **WHEN** the session actor is a possessed NPC
- **THEN** the presenter resolves the party's bound OWNER — the player named by the NPC-side
  `party_member` back-reference — and serializes that player's live companions with their
  owner-keyed bond stages, so the panel keeps listing the whole party, including the possessed
  companion, instead of the NPC's own (empty) party binding

#### Scenario: A dangling owner back-reference raises unavailable
- **WHEN** the `party_member` back-reference resolves to no live player
- **THEN** the presenter raises the registry-unavailable error and the panel takes the shared
  unavailable form

#### Scenario: Quota, row count and commission reference bounds
- **WHEN** a dual member or an over-quota party is presented
- **THEN** General usage SHALL use valid general identity, total roster rows SHALL not be limited to four, and temporary commission references SHALL contain exact quest identity and protected-role reference with player-permitted labels, never private planning data. Existing portrait formatting/bounds and no-raw-affinity rules SHALL remain.
