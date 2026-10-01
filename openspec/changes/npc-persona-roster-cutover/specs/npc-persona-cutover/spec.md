## Purpose

Replace, exactly once and atomically, every provisional persona of existing NPCs and every pre-change generated-quest occupant characterization with a complete compact card resolved from known provenance or an offline bundle, while preserving all gameplay state and never overwriting later edits.

## ADDED Requirements

### Requirement: The cutover replaces every unmarked NPC and durable occupant characterization from known provenance
At server start, before generated-quest restore, the system SHALL plan a replacement for every NPC-family instance that lacks the current content-generation marker and for every durable generated-quest occupant whose characterization is not a valid compact card. Each replacement SHALL be a complete card resolved by known provenance — a service host's place profile, an exam opponent's rank examiner profile from the exam record naming it, a starting companion derived from its partner preset via the shared companion derivation with its owner relationship recomputed from its party binding or unique declaring owner, a scene occupant's durable declaration replacement, a shipped template occupant's template card — and otherwise an offline bundle selected by stable identity. Old persona text SHALL never be carried forward, and no instance SHALL be deleted or respawned. `Monster` instances and player characters SHALL NOT be touched.

#### Scenario: Existing hosts receive their profile cards
- **WHEN** the cutover runs against a world whose service hosts carry no persona metadata
- **THEN** each host carries its place profile's card with metadata at the current generation and `profile` provenance

#### Scenario: A companion is re-derived from its partner preset
- **WHEN** a bound starting companion still carries the legacy copied persona record
- **THEN** it carries the compact card derived from its partner preset (identity, personality, life story, and habit consistent with the preset's authored persona, `speech_style` from the preset's extension field, social connection beginning with the owner line for its bound owner), its persona metadata names `companion` provenance with the partner preset key, and its offline-greeting field holds the preset's authored greeting

#### Scenario: Durable occupants and materialized occupants share one baseline
- **WHEN** a stored generated quest has an old-shape occupant and that stage's occupant is already materialized
- **THEN** the rewritten payload and the materialized NPC carry the same new card, the payload decodes under the strict codec, and quest ids, objectives, binding ids, stages, and requirements are unchanged

#### Scenario: An unclassified NPC receives an offline bundle
- **WHEN** an imported beastfolk NPC without a tier and without metadata exists
- **THEN** it receives the beastfolk generic pool bundle selected by its database id, with `offline_bundle` provenance

### Requirement: The cutover is one exclusive, all-or-nothing transaction
The cutover SHALL compute and validate every replacement before any write and SHALL apply all instance cards, metadata, rewritten payloads, and the persistent cutover marker in one database transaction. Any failure SHALL leave the prior state intact, restore every affected attribute cache, emit a failure event naming the source or entity, and abort startup so no player is admitted to a partly rewritten world. While the cutover runs, every other NPC persona writer — editor update, import, and spawn initialization — SHALL be rejected with a stable reason, and a re-entrant or concurrent cutover attempt SHALL be refused without waiting or retrying. The cutover SHALL run as one synchronous startup step that never yields to the event loop, so no session action can interleave with it.

#### Scenario: A failure rolls everything back
- **WHEN** the write for the tenth planned NPC raises during apply
- **THEN** no NPC, metadata, payload, or marker change persists, every attribute cache equals its pre-run value, a failure event names the entity, and startup aborts

#### Scenario: Other writers are refused during the cutover
- **WHEN** an editor update, an NPC import, and a spawn initialization are attempted while the cutover is running
- **THEN** each is rejected with the stable suspension reason and writes nothing

#### Scenario: The cutover step is synchronous
- **WHEN** the startup step runs
- **THEN** it completes and returns a plain result without yielding a deferred, before any session is synchronized

#### Scenario: A second cutover is refused
- **WHEN** a cutover is started while another is running in the same process
- **THEN** the second attempt is refused immediately with a named error

### Requirement: The cutover preserves gameplay state and is idempotent
The cutover SHALL change only NPC persona records, persona metadata, and durable occupant characterization fields, preserving every stored quest definition key and object ids, keys, titles, locations, components, traits, inventory, party and quest bindings, schedules, affinity, chat memory, dialogue sessions, and every other payload field. A rerun SHALL skip every marked instance and every valid payload and write nothing, so a routine restart, registry reload, or profile text edit never overwrites an effective card, including optional leaves a player deliberately cleared. Instances created after the cutover SHALL be marked by their normal initializers.

#### Scenario: Gameplay state is unchanged
- **WHEN** full attribute snapshots of every NPC and the quest store are compared before and after a successful cutover
- **THEN** only persona records, persona metadata, and occupant characterization fields differ

#### Scenario: Edits survive restart
- **WHEN** after a successful cutover a player clears an NPC's `social_connection` and edits its `habit`, and the server restarts
- **THEN** the cutover writes nothing, and the NPC keeps the empty social connection, the edited habit, and its advanced version

#### Scenario: Old payloads are rewritten without a legacy decoder
- **WHEN** a frozen pre-change payload fixture is planned and applied
- **THEN** its occupants carry new cards, no old `persona` or `background` text remains, its definition key is unchanged, and the strict codec decodes it

#### Scenario: Restore succeeds after the cutover
- **WHEN** the server restarts after a cutover that rewrote old-shape payloads
- **THEN** generated-quest restore decodes every payload and registers every quest without error
