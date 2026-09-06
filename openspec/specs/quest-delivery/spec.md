# quest-delivery Specification

## Purpose
The DELIVER quest objective mechanic: definition validation, runtime recipient binding, committed-transfer progress tracking, and player-facing prose rendering.

## Requirements

### Requirement: DELIVER is a closed transfer-backed quest objective
`world/quests/definitions.py` SHALL define `ObjectiveKind.DELIVER`. A `DELIVER` objective SHALL
carry an `item_key` present in the item registry, a positive integer `quantity`, and
`requires_bound_targets` true; it SHALL carry no destination and no monster tier. Definition
validation SHALL reject an unregistered item key, a non-positive quantity, an unbound-target
delivery, a supplied destination, and a supplied monster tier, each by name, before the definition is
registered.

#### Scenario: A well-formed delivery objective validates
- **WHEN** a definition declares a `DELIVER` stage with a registered item key, a positive quantity,
  and bound targets required
- **THEN** the definition registers

#### Scenario: An unregistered item key rejects
- **WHEN** a `DELIVER` stage names an item key absent from the item registry
- **THEN** registration raises a named definition error

#### Scenario: A destination on a delivery rejects
- **WHEN** a `DELIVER` stage carries a destination locator
- **THEN** registration raises a named definition error

#### Scenario: An unbound delivery rejects
- **WHEN** a `DELIVER` stage does not require bound targets
- **THEN** registration raises a named definition error — a delivery with no recipient identity
  cannot be satisfied

### Requirement: The recipient is a runtime-bound identity, never a name
A `DELIVER` stage's recipient SHALL be identified through the record's existing
`objective_target_ids` runtime binding, bound by the same `bind_stage_runtime` path every other bound
objective uses. The recipient SHALL NOT be matched by display name, by keyword, or by any
player-supplied string, so two same-named characters can never be confused and a renamed recipient
stays correct.

#### Scenario: The bound recipient is the only valid target
- **WHEN** an active delivery stage is bound to one recipient identity
- **THEN** only a transfer to that exact identity advances the objective

#### Scenario: A same-named unbound character does not satisfy the delivery
- **WHEN** the parcel is handed to a different character sharing the recipient's display name
- **THEN** the objective does not advance and the record is unchanged

### Requirement: Delivery progress comes only from a committed transfer to the bound recipient
`DELIVER` progress SHALL advance only from a committed item transfer in which the quest holder is
the giver, the receiver is the stage's bound recipient, and the transferred key matches the
objective's `item_key`. Progress SHALL advance by the transferred quantity, capped at the objective
quantity, and surplus SHALL NOT carry into a later stage. A transfer of a different item, to a
different receiver, or in which the holder is the receiver rather than the giver SHALL advance
nothing. There SHALL be no public "item delivered" assertion a caller can forge: the progress
computation SHALL be reachable only from a committed transfer.

#### Scenario: Handing the parcel to the bound recipient advances the stage
- **WHEN** the holder transfers the objective's item to the bound recipient
- **THEN** the stage progress rises by the transferred quantity within the objective quantity

#### Scenario: A different item advances nothing
- **WHEN** the holder transfers an item other than the objective's to the bound recipient
- **THEN** no delivery objective advances

#### Scenario: Receiving the item advances nothing
- **WHEN** the bound recipient transfers the objective's item TO the holder
- **THEN** no delivery objective advances — only the giver side counts

#### Scenario: Progress is computed, never asserted
- **WHEN** the delivery observer is inspected
- **THEN** it exposes only a computation over a committed transfer and no public progress-assertion
  entry point

### Requirement: The delivery observer computes a replacement and writes nothing
`world/quests/deliver.py` SHALL expose a pure computation returning the quest-log replacement and pin
operations for one committed transfer, or nothing when no active delivery stage matches —
structurally parallel to the acquisition observer. The surrounding transfer operation SHALL own the
transaction, the snapshots, and the write, so the delivery advance commits atomically with the item
movement and rolls back with it.

#### Scenario: The observer performs no write
- **WHEN** the observer runs for a matching transfer
- **THEN** the actor's quest log is unchanged until the calling transfer applies the returned
  replacement

#### Scenario: A rolled-back transfer rolls back the delivery advance
- **WHEN** persistence is fault-injected during a transfer that would satisfy a delivery stage
- **THEN** the quest log, both inventories, and their in-process caches equal their pre-transfer
  values

#### Scenario: No matching stage yields no replacement
- **WHEN** a transfer occurs while the holder has no active delivery stage for that item and
  recipient
- **THEN** the observer returns nothing and the transfer proceeds unchanged

### Requirement: A delivery objective renders player-facing prose from the registries
`describe_objective` SHALL render a `DELIVER` objective as one Traditional Chinese requirement line
naming the item registry's display name and the delivery quantity. An unregistered item key SHALL
raise the renderer's named error rather than printing a raw key.

#### Scenario: A delivery line names the item
- **WHEN** a `DELIVER` objective for a registered item is rendered
- **THEN** the line carries that item's registry display name and its quantity

#### Scenario: An unknown item raises rather than leaking a key
- **WHEN** a `DELIVER` objective naming an unregistered item is rendered
- **THEN** the renderer raises its named describe error

### Requirement: A delivery is completable with every generative service offline

A player SHALL be able to hand a quest item to its bound recipient through a deterministic path that
consults no LLM, no image service, and no generative proposal. The deterministic path SHALL be
reachable both from the web client, as the registered `explore.deliver` action, and from the text
surface, as a player command. Neither route SHALL depend on an NPC dialogue intent, so a delivery
quest SHALL be completable end to end with every generative profile failing.
The deterministic path SHALL hand exactly the remaining objective quantity
(`objective.quantity - stage_progress`) of the selected active stage in one invocation; the payload
carries no quantity, and the quantity is re-derived server-side. When several in-progress records
bind the same recipient and item key, one shared selection policy — used by both the deterministic
rule and the affordance builder — SHALL select the stage with the lowest remaining quantity (ties
breaking in quest-log order), so an advertised delivery is always satisfiable by the hand-over that
follows it.

#### Scenario: A delivery completes with all generative services failing
- **WHEN** every `LLM_PROFILES` entry is configured to fail and the holder hands the objective item
  to its bound recipient through the deterministic path
- **THEN** the transfer commits, the delivery stage advances, and no generative service is consulted

#### Scenario: Both surfaces reach the same rule
- **WHEN** the same delivery is performed once through the registered action and once through the
  player command
- **THEN** both invoke the identical deterministic rule and produce identical state changes and
  identical rejection reasons

#### Scenario: A partially advanced stage is completed by one hand-over
- **WHEN** the holder's delivery stage has already gained progress and the holder carries exactly
  the remaining objective quantity
- **THEN** the deterministic hand-over transfers exactly that remaining quantity and the stage
  completes

### Requirement: The delivery action is registered with an exact bounded payload

The production action registry SHALL additionally contain `explore.deliver` with its own exact
payload validator and deterministic adapter. Its payload SHALL be exactly the recipient's integer
identity and the bounded item key; a payload carrying extra, missing, mistyped, or out-of-bound
fields SHALL be rejected before the adapter runs. The adapter SHALL obtain the actor from the
authenticated session, re-resolve the recipient and the quest record itself, and SHALL NOT trust any
client-supplied quest ID, stage index, quantity, or reward value. It SHALL route no action ID or
payload through the text command parser.

#### Scenario: The registry binds the delivery action
- **WHEN** the production action registry is enumerated
- **THEN** it additionally contains `explore.deliver` bound to exactly one payload validator and one
  deterministic adapter

#### Scenario: An out-of-shape payload is rejected before the adapter
- **WHEN** a delivery request carries an extra field, a missing field, a non-integer recipient, or an
  over-long item key
- **THEN** the request is rejected by the validator and the adapter is never invoked

#### Scenario: The adapter re-resolves rather than trusting the client
- **WHEN** a well-formed delivery request names a recipient and an item
- **THEN** the adapter resolves the actor from the session and re-derives the matching quest record,
  stage, and quantity from stored state

### Requirement: A delivery is refused honestly and changes nothing when refused

The deterministic rule SHALL refuse, with a stable reason code and a safe Traditional Chinese
message, when the recipient is not co-located with the holder, when the holder has no active
`DELIVER` stage bound to that recipient, when the holder does not hold the objective's item, or when
an active combat session blocks the holder. The combat refusal SHALL precede the other rule-level
checks. A refusal SHALL change no inventory, no quest log, and no other state.

#### Scenario: A distant recipient is refused
- **WHEN** the named recipient is not in the holder's location
- **THEN** the delivery is refused with a stable reason code and no state changes

#### Scenario: An unheld item is refused
- **WHEN** the holder no longer holds the objective's item
- **THEN** the delivery is refused with a stable reason code and no state changes

#### Scenario: An unbound recipient is refused
- **WHEN** the named co-located entity is not the bound recipient of any active delivery stage
- **THEN** the delivery is refused with a stable reason code and no state changes

#### Scenario: A mid-fight delivery is refused before every other check
- **WHEN** the holder has an active combat session and names a recipient or item that would
  otherwise be deliverable
- **THEN** the delivery is refused with the combat reason code before any co-location, binding, or
  holding evaluation

#### Scenario: A refusal leaves the world untouched
- **WHEN** any refusal branch is taken
- **THEN** the holder's inventory, the recipient's inventory, and the quest log are byte-for-byte
  unchanged
