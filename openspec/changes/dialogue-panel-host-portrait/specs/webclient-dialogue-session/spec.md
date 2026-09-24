## ADDED Requirements

### Requirement: The dialogue panel is an exact read-only version-2 presentation panel
The presentation registry SHALL register a `dialogue` panel at schema version 2. Its available
form SHALL contain exactly `schema_version`, `available`, `kind`, `host`, `bond_stage`, `line`,
and `choices`: `host` SHALL contain exactly `identity` (the present NPC's positive database
identity), `display_name` (bounded by the shared display-name bound), and `portrait_ref`;
`bond_stage` SHALL be the affinity stage NAME from the rulebook stage table when the host NPC has
a relationship with the viewer and `null` otherwise, and the raw affinity number SHALL NOT appear
anywhere in the payload; `line` SHALL be the session's latest server-authored reply line bounded
by the shared narrative-line bound; and `choices` SHALL be an ordered list of at most four
`{keyword_id, label}` descriptors — the panel-owned presentation bound, independent of the
interact target descriptor's own sixteen-keyword keyword-pool bound — derived from the host's
dialogue table in table order (the same prefix the interact affordance truncation takes), the
same vocabulary owner the interact target descriptor uses, empty when the host's table is empty.

`portrait_ref` SHALL be the opaque `webclient-art-panel` portrait-catalog key for the host when the
host is present in the art view the `art` panel is built from for the same viewer — including an
entry that resolves to a placeholder card — and SHALL be `null` only when the host is absent from
that view or the art view cannot be built. The server SHALL derive the key with the same single
catalog-key mapper the art panel and the combat participants use, so a non-null `portrait_ref`
equals a key of the committed catalog in the same snapshot; the client SHALL NOT construct a
catalog key from the host identity. On the wire `portrait_ref` SHALL be `null` or a decimal-digit
string of at most 32 characters, the same vocabulary as a combat participant's `portrait_ref`.

The registered unavailable form SHALL carry reason `dialogue_unavailable` with the player message
`對話目前無法顯示` and the shared field set and semantics. The panel SHALL be available exactly
when the viewer's live dialogue session resolves; the presenter SHALL be read-only — it SHALL NOT
open, refresh, clear, or mutate any session, affinity, memory, art, or world state — and SHALL
emit no live object or filesystem reference.

#### Scenario: A live scripted session serializes the host triple and table choices
- **WHEN** a viewer with a live dialogue session against a bonded table host receives a snapshot
- **THEN** `dialogue` is available with the host's identity, display name, and the host's art
  catalog key as `portrait_ref`, the bond stage name, the recorded line, and the host's first four
  keyword descriptors in table order, with no affinity numeral present

#### Scenario: The host's portrait reference matches the art catalog
- **WHEN** a viewer with a live session against a scripted host receives one snapshot carrying
  both the `art` and the `dialogue` panel, once while the host's portrait is generated and once
  while it is still pending
- **THEN** in both snapshots `dialogue.host.portrait_ref` is a key of `art.portrait_catalog`, and
  that entry carries the image URL in the first snapshot and the placeholder card in the second

#### Scenario: A host outside the art view carries a null reference
- **WHEN** the session host is a generative NPC with no dialogue component and no named portrait
  policy, or the art view cannot be built for the viewer
- **THEN** `portrait_ref` is `null`, the rest of the payload is unaffected, and the panel stays
  available

#### Scenario: A host with more than four authored keywords is truncated to the first four
- **WHEN** the session host's dialogue table carries five or more authored keywords
- **THEN** the panel's `choices` carry exactly the first four in table order and the server
  validator accepts the payload

#### Scenario: An unbonded host discloses a null stage
- **WHEN** the session host has no relationship record for the viewer
- **THEN** `bond_stage` is `null` and the rest of the payload is unaffected

#### Scenario: No live session is the unavailable form
- **WHEN** a viewer without a dialogue session receives a snapshot
- **THEN** `dialogue` uses the `dialogue_unavailable` form and no host, line, or choices ship

#### Scenario: Validation rejects payload drift
- **WHEN** a candidate dialogue payload carries a fifth choice, an unknown or missing field, a
  numeric `bond_stage`, an over-bound line, a numeric `portrait_ref`, a `portrait_ref` with a
  non-digit character, or a `portrait_ref` longer than 32 characters
- **THEN** the server validator rejects it and the client mirror rejects it identically, while
  the same payload with `portrait_ref` `"42"` or `null` validates on both sides

## REMOVED Requirements

### Requirement: The dialogue panel is an exact read-only version-1 presentation panel
**Reason**: The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §8.2) stands the dialogue host's portrait in the stage's `actor-right` anchor, sourced from the art catalog. Version 1 pins `portrait_ref` to `null`, so the client has no catalog key for the host. The panel moves to schema version 2, and the requirement's title names the version, so it is replaced.
**Migration**: "The dialogue panel is an exact read-only version-2 presentation panel" restates every field, bound, and rule, and gives `portrait_ref` the art catalog key. Tests annotated with the old ID re-anchor to the new one.
