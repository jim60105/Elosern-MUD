## Purpose

The read-only `combat_beats` presentation panel. For each settled combat round it lists server-authored beats, derived only from the round's structured event records, so that the WebClient can play the exchange without parsing narrative prose.

## ADDED Requirements

### Requirement: The combat beats panel is an exact read-only panel

The production presentation registry SHALL register the panel `combat_beats` at schema version 1, with the common unavailable form and the common non-internal unavailable reason. Its available payload SHALL contain exactly `schema_version`, `available`, `round`, and `beats`:

- `round` SHALL be a non-empty string of at most 160 Unicode code points that identifies one settled round of one combat session.
- `beats` SHALL be a list of 0 to 64 beat objects.
- Each beat SHALL contain exactly `seq`, `action`, `kind`, `actor`, `target`, `amount`, `hp_after`, and `text`:
  - `seq` SHALL be the beat's 0-based position; the positions SHALL be contiguous.
  - `action` SHALL be a non-negative integer that never decreases along the list.
  - `kind` SHALL be one of `roll`, `damage`, `target_defeated`, `other`.
  - `actor` and `target` SHALL each be null or a decimal-digit string of at most 32 characters.
  - `text` SHALL be a string of at most 256 Unicode code points.
  - A `damage` beat SHALL carry a non-null `target`, a non-negative integer `amount`, and a non-negative integer `hp_after`.
  - Every other beat SHALL carry null `amount` and null `hp_after`.
- The payload's canonical UTF-8 JSON SHALL NOT exceed 12,288 bytes.

The presenter SHALL read only its read-only context and SHALL NOT mutate traits, resources, buffs, sexual state, the battlefield, the combat record, quests, location, or world time. A payload that violates any bound SHALL NOT be emitted: the panel SHALL use the unavailable form instead, and SHALL NOT truncate.

#### Scenario: A settled round renders the exact available form

- **WHEN** the panel renders for the publication that completes a settled combat round
- **THEN** the payload contains exactly the four top-level fields and each beat contains exactly the eight beat fields within their bounds, and canonical game state before and after rendering is unchanged

#### Scenario: An over-bound round is unavailable, never truncated

- **WHEN** a settled round yields more than 64 beats, a beat text over 256 code points, or a payload over 12,288 bytes
- **THEN** the panel uses the common unavailable form with the non-internal reason, and no partial beat list is emitted

### Requirement: Combat beats derive only from the settled round's event records

The beats SHALL be derived only from the event entries of the round's own event logs, in log order and then entry order. Event logs that a terminal settlement appends after the round (the defeat aftermath) SHALL NOT produce beats.

- `action` SHALL be the 0-based ordinal of the beat's source event log within the round.
- `kind` SHALL be the entry kind when that kind is `roll`, `damage`, or `target_defeated`, and `other` for every other entry kind. A kind SHALL join the closed set only through a change to this requirement.
- `actor` and `target` SHALL be the opaque participant identity used as the `art` portrait catalog key and the combat panel `portrait_ref` for the participant the entry names, and null when the entry names no round participant.
- `amount` SHALL be the integer `amount` of a `damage` entry.
- `text` SHALL be the entry's own rendered line in plain text, with ANSI markup stripped: the same line the ordinary text output delivered for that entry.

The panel SHALL NOT parse narrative prose and SHALL NOT carry any other entry data.

#### Scenario: Entry kinds map to the closed set in order

- **WHEN** a round's logs contain, in order, a `resource_spend`, a `roll`, a `damage`, a `target_defeated`, and a `target_knocked_out` entry
- **THEN** the beats are `other`, `roll`, `damage`, `target_defeated`, `other` with `seq` 0 to 4, and each beat's `action` is its source log's ordinal

#### Scenario: Beat identities match the portrait catalog

- **WHEN** a beat's entry names a round participant as actor or target
- **THEN** that field equals the participant's `portrait_ref` in `context_actions` and its `art` catalog key, and an entry naming no participant yields null

#### Scenario: Beat text equals the delivered narrative line

- **WHEN** a round is settled and its logs are emitted as ordinary text
- **THEN** each beat's `text` equals, in order, the corresponding line of the emitted narrative, and no beat carries a roll value, a hit flag, or any entry data other than a damage `amount`

### Requirement: Beat HP is projected on the server and checked against the round's recorded HP

For each round participant, the server SHALL keep a projected HP that starts at the participant's stored HP before the round. Each `damage` beat SHALL lower its target's projected HP by `amount`, clamped at 0. When the round contains a `target_knocked_out` entry naming that target, the clamp SHALL be at 1 instead (the knockout floor). The beat's `hp_after` SHALL be the new projected value.

For every target of at least one `damage` beat, the last `hp_after` SHALL equal the target's stored HP at the end of the round, recorded before any terminal settlement. On any mismatch, or when a `damage` entry names a target that is not a round participant, the panel SHALL be unavailable for that round, and the server SHALL log a bounded diagnostic. For a non-terminal round, the recorded end-of-round HP SHALL equal the `status` HP and the combat panel `hp_current` published at the same revision.

#### Scenario: Ordered damage projects hp_after

- **WHEN** a foe at 30 HP takes damage entries of 12 and then 25 in one round
- **THEN** the two damage beats carry `hp_after` 18 and then 0, and the last value equals the foe's `hp_current` in `context_actions` at the same revision

#### Scenario: A knockout floors the projection at 1

- **WHEN** a protected companion at 10 HP takes a 15-point damage entry followed by a `target_knocked_out` entry
- **THEN** the damage beat carries `hp_after` 1 and the panel is available

#### Scenario: An HP change without a damage entry makes the round unavailable

- **WHEN** a damaged target is also healed in the same round, so its recorded end-of-round HP differs from its last projected `hp_after`
- **THEN** the panel uses the common unavailable form with the non-internal reason for that round, and `status`, `context_actions`, and `art` still publish at the same revision

### Requirement: The beats panel is published only with the combat action that produced it

The beats panel SHALL be available only in the single presentation publication that completes an admitted `combat.cast`, `combat.flee`, or in-session `inventory.use` action whose ordinary round settled.

- A non-terminal round SHALL publish `combat_beats` in the same `ui_update` and at the same revision as `status`.
- A terminal round SHALL carry the available panel in its full snapshot, even though that snapshot's mode is `exploration`.

Every other publication SHALL render the common unavailable form. This includes:
- a reconnect or `ui_sync` snapshot;
- a text-command refresh;
- a forfeit;
- a rejected, stale, or error completion;
- a push;
- a round opened by the overwhelm opening or by a typed command.

`round` SHALL be unique per settled round and SHALL be stable for that round, so that a client never plays one round twice. A duplicate `request_id` SHALL replay only the cached result and SHALL NOT republish beats.

#### Scenario: A non-terminal round carries beats beside status

- **WHEN** an accepted `combat.cast` completes a non-terminal round
- **THEN** the one `ui_update` at the newer revision contains `status`, `context_actions`, `art`, and an available `combat_beats` whose `round` names that session and round

#### Scenario: A terminal round carries beats in its full snapshot

- **WHEN** an accepted cast defeats the last foe
- **THEN** the full snapshot at the newer revision has mode `exploration` and an available `combat_beats` whose beats end with the `target_defeated` beat

#### Scenario: Reconnect never replays beats

- **WHEN** the transport reconnects after a settled round and the client sends `ui_sync`
- **THEN** the new-epoch snapshot's `combat_beats` is the common unavailable form

#### Scenario: Other publications are unavailable

- **WHEN** a snapshot or update is published by a text command, a forfeit, a rejected combat action, or any path other than the completing publication of a settled round
- **THEN** every `combat_beats` value it contains is the common unavailable form

### Requirement: Combat beats disclose nothing the combat panel does not

The beats panel SHALL read HP only from the same stored true-HP source the combat panel's participant rows use. It SHALL ship `hp_after` as a number for every participant, foes included, exactly as the combat panel ships `hp_current`. It SHALL NOT call the disguise accessor or read the disguise layer. It SHALL NOT expose any structured roll value, hit flag, hidden modifier, or entry data other than a damage `amount`. Its only prose SHALL be lines the ordinary text output already delivered.

#### Scenario: A disguised foe discloses only true combat-panel HP

- **WHEN** a foe carrying display-only disguised stats is damaged in a round
- **THEN** the beats carry its true projected HP, which equals the combat panel's `hp_current`, and no disguised value or disguise-layer field appears in the panel

#### Scenario: The beats modules never read the disguise layer

- **WHEN** the beats rules module and the beats presenter module are scanned
- **THEN** neither references the disguise accessor or the disguise-layer attribute

### Requirement: The client protocol mirrors the combat beats schema

The client protocol validator SHALL register `combat_beats` at schema version 1 in its panel allowlist, and the WebClient store's panel allowlist SHALL include it. The client SHALL validate the available form with the same exact fields, bounds, closed kind set, contiguous `seq`, non-decreasing `action`, damage invariants, identity shape, and byte budget as the server. It SHALL reject any payload that violates them without replacing or merging the stored panel, and SHALL accept the common unavailable form. The server and client schema versions and bounds SHALL stay equal under the dual-direction parity contract.

#### Scenario: The client accepts a valid beats panel

- **WHEN** a snapshot or update carries a valid available `combat_beats` panel or its unavailable form
- **THEN** the client validator accepts it and the store commits it under `combat_beats`

#### Scenario: The client rejects an out-of-schema beat

- **WHEN** a `combat_beats` beat carries an unknown kind, an extra field, a non-contiguous `seq`, a `damage` beat with a null `hp_after`, a non-damage beat with an `amount`, or a non-decimal identity
- **THEN** the client rejects that presentation message and keeps the previously stored panel
