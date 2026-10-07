## MODIFIED Requirements

### Requirement: Compact status reports canonical true resources
The available version-3 status panel SHALL contain exactly `schema_version: 3`, `available: true`, `actor`, `resources`, `conditions`, `disguise_active`, and `combat`. `actor` SHALL contain display `name` of 1..256 Unicode code points, opaque correlation `identity` of 1..64 ASCII characters, and nullable `location`, with the existing optional composed `full_title` contract unchanged; a present location SHALL contain exactly a 1..256-code-point display `label` and 1..64-character opaque `identity`. `resources` SHALL contain exactly `hp`, `mp`, and `sp`, each with non-negative JavaScript-safe integer `current` and positive safe integer `maximum`, with current not exceeding maximum. `conditions` SHALL contain at most 32 entries. `disguise_active` SHALL be boolean, and `combat` SHALL be null or the exact combat object. Resource values SHALL come directly from canonical traits and SHALL never call `get_display_value` or substitute `disguised_stats`. Missing or malformed required traits SHALL produce the common status-unavailable payload rather than fabricated zero values. Available and unavailable status forms SHALL use the same registered version 3. Envelope protocol version and unrelated panel versions SHALL remain unchanged, and status version 2 SHALL NOT be accepted as a compatibility form.

#### Scenario: Active disguise does not alter resources
- **WHEN** an actor has true HP 80/100, MP 40/60, SP 30/50 and display-only disguised values for any traits
- **THEN** the status payload reports 80/100, 40/60, and 30/50 and marks `disguise_active` true

#### Scenario: Missing gauge fails closed
- **WHEN** the active puppet lacks a valid required HP, MP, or SP gauge
- **THEN** the status panel is unavailable at schema version 3 and does not report zero for the missing resource

#### Scenario: Status version cutover is exact
- **WHEN** equivalent available and unavailable status payloads are checked at versions 2 and 3
- **THEN** the registered version-3 forms are accepted and version-2 forms are rejected without replacing committed presentation

### Requirement: Status conditions use deterministic matched modifiers
The deterministic combat-modifier module SHALL expose a read-only query of each currently matched rule ID and its exact adjustment bundle without changing existing merged evaluation. The status presenter SHALL combine that query with active rulebook buff instances and immutable display metadata. Each condition entry SHALL contain stable `code` of 1..64 lowercase dotted or underscored identifier characters, Traditional Chinese `label` of 1..128 code points, `severity` from `beneficial`, `informational`, `warning`, `harmful`, or `critical`, and required `provenance`; it SHALL permit only optional non-negative safe-integer `remaining_seconds` and optional `modifiers` with at most 16 stable keys and exact JSON scalar rule values. An absent duration SHALL be omitted, without a fabricated value. It SHALL include sexual-state entries only while their effective canonical combat predicates match. Provenance classification SHALL NOT change global display severity, actual adjustment values, active buff stacking or duration, or condition membership. Independent and attached active instances with the same logical definition SHALL remain represented without merging away either instance.

`provenance` SHALL contain exactly `kind` and `equipment_sources`. `kind` SHALL be one of `equipment`, `non_equipment`, `mixed`, or `unknown`. `equipment_sources` SHALL be a duplicate-free array of at most eight entries sorted by item key; each entry SHALL contain exactly a stable `item_key` of 1..64 identifier characters and an item-registry-backed Traditional Chinese `label` of 1..128 code points. `equipment` and `mixed` SHALL require at least one equipment source; `non_equipment` and `unknown` SHALL require none. The read-model/presenter boundary and browser protocol validation SHALL reject missing, malformed, unknown-field, over-bound, or inconsistent provenance rather than fabricate a source or adopt a legacy shape.

#### Scenario: Matching buff reports duration and exact adjustment
- **WHEN** a synthetic actor has an active independent poisoned buff with 120 game seconds remaining and its deterministic adjustment rule matches
- **THEN** status contains the stable poisoned condition with its Traditional Chinese label, harmful severity, 120-second duration, non-equipment provenance, and the exact agility adjustment supplied by the matched deterministic rule

#### Scenario: Sexual threshold appears only while matched
- **WHEN** the actor's canonical arousal state crosses the configured combat-modifier threshold
- **THEN** status contains the matched rule ID and exact agility/accuracy adjustments, and the entry disappears after canonical state no longer matches

#### Scenario: Condition presentation metadata covers current rules
- **WHEN** current buff definitions and combat-modifier rule IDs are compared with the status display registry
- **THEN** every condition that can enter the status payload has one stable Traditional Chinese label and severity

#### Scenario: Provenance does not change actual mechanics
- **WHEN** a synthetic equipment overlay activates an adverse combat modifier and its status provenance is classified
- **THEN** its severity, exact adjustments, and combat/breakdown outcome equal those obtained from the actual effective state, and comparison-only rules are absent from status

#### Scenario: Invalid provenance is rejected
- **WHEN** a v3 condition omits provenance, uses an unknown kind, includes an extra field, repeats an item key, exceeds eight sources, or pairs equipment kind with an empty source list
- **THEN** it fails validation and cannot replace the accepted status panel

## ADDED Requirements

### Requirement: Equipment condition provenance preserves independent sources
Condition provenance SHALL be computed read-only from the same canonical snapshot used for the condition's actual values. An active attached buff SHALL have equipment provenance only when its instance identity, cached logical definition and cached source item agree with the currently worn item's declared attachment. An ordinary independent instance SHALL retain non-equipment provenance even when its definition matches an attached instance or its source string resembles an item key. An orphaned or inconsistent attachment whose origin cannot be proven SHALL have unknown provenance and SHALL NOT be treated as equipment-only. Missing or malformed required canonical status inputs SHALL continue to produce unavailable status rather than repaired state.

An actually matched derived condition SHALL be equipment-dependent when it does not match without the current read-time equipment contributions and those contributions have verified sources. A condition matching independently without those contributions SHALL retain independent provenance and attention. It SHALL be mixed when equipment also contributes to a matching input, and non-equipment when equipment does not change any input consumed by that condition. The equipment-free comparison SHALL preserve stored state, skills, grants, and independent buffs, remove only proven worn attachments and read-time equipment facts/overlays, and use the same deterministic condition semantics as actual combat. Buff predicates SHALL identify logical definitions rather than confusing source-specific instance identities with definitions. Unproven attribution SHALL use unknown provenance without suppressing attention. Canonical state changes previously caused by gameplay SHALL remain canonical in this comparison; historical causal reconstruction SHALL NOT be required.

Building or comparing these values SHALL NOT materialize handlers, write or repair Attributes, advance time, tick buffs, alter equipment, or change combat evaluation. Under possession, provenance SHALL follow the same canonical subject that owns the status resources and conditions, without borrowing sources from the controlled host.

#### Scenario: Worn attached adverse buff identifies its item
- **WHEN** a synthetic worn accessory declares an adverse attached buff and an active instance has the exact declared identity, logical definition and cached source item
- **THEN** its status row has equipment provenance naming that accessory's registry key and label, while its severity and remaining duration remain unchanged

#### Scenario: Independent instance of the same definition survives
- **WHEN** the actor also has an independent active instance of that attached buff's definition
- **THEN** both buff rows remain represented with their own durations and provenance, the independent instance retains attention, and any definition-based matched rule still matches independently in the equipment-free comparison

#### Scenario: A source string alone does not prove equipment ownership
- **WHEN** an independent buff has a source string equal to a worn item's key but lacks the item's declared attachment identity
- **THEN** it is not classified equipment-only and cannot lose its adverse-condition attention

#### Scenario: Inconsistent attachment retains conservative attention
- **WHEN** an otherwise readable active attached-looking instance is orphaned after its item is absent or has inconsistent cached source metadata
- **THEN** its provenance is unknown with no invented equipment source and its adverse severity retains attention

#### Scenario: Equipment induces an exposure threshold crossing
- **WHEN** a synthetic actor stores exposure 中等, synthetic worn equipment adds +1 bias, and an adverse rule requires exposure at least 高
- **THEN** actual status contains that rule with equipment provenance naming the bias contributor, while stored exposure stays 中等 and the same rule does not independently match without equipment

#### Scenario: Mixed exposure retains the independent warning
- **WHEN** a synthetic actor stores exposure 高 and equipment raises its effective exposure to 極高 while an adverse rule requires exposure at least 高
- **THEN** that rule has mixed provenance naming the equipment contributor and retains independent attention

#### Scenario: Saturated baseline already needs attention
- **WHEN** a synthetic actor stores exposure 極高, equipment adds +1 bias, and an adverse rule requires exposure at least 高
- **THEN** effective exposure remains 極高, the unchanged input yields non-equipment provenance with no equipment source, and the warning retains attention both with and without equipment

#### Scenario: Unrelated equipment cannot suppress a state warning
- **WHEN** an actor wears exposure-bias equipment while an adverse condition depends solely on stored pleasure or an independent active buff
- **THEN** the unrelated equipment is absent from that condition's provenance and the adverse condition retains independent attention

#### Scenario: Equipment prerequisite has no independent match
- **WHEN** a synthetic adverse rule requires both a stored-state threshold and a named worn item, and only the state threshold remains in the equipment-free comparison
- **THEN** the actual rule remains represented with equipment provenance and no claim that the stored prerequisite independently activates that rule

#### Scenario: Repeated reads preserve canonical storage
- **WHEN** provenance is built twice for synthetic materialized and unmaterialized actors with equipment and buffs
- **THEN** all canonical Attributes, world time, equipment and buff values remain unchanged and no lazy handler or new storage record is created

#### Scenario: Possession uses the status owner's equipment
- **WHEN** the controlled host and status resource owner wear different synthetic equipment under possession
- **THEN** condition source labels and independent-match comparison use the status resource owner's equipment and state, while the existing controlled actor identity remains unchanged
