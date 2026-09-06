# Delta spec: quest-delivery (quest-deliver-action)

## ADDED Requirements

### Requirement: A delivery is completable with every generative service offline

A player SHALL be able to hand a quest item to its bound recipient through a deterministic path that
consults no LLM, no image service, and no generative proposal. The deterministic path SHALL be
reachable both from the web client, as the registered `explore.deliver` action, and from the text
surface, as a player command. Neither route SHALL depend on an NPC dialogue intent, so a delivery
quest SHALL be completable end to end with every generative profile failing.

#### Scenario: A delivery completes with all generative services failing
- **WHEN** every `LLM_PROFILES` entry is configured to fail and the holder hands the objective item
  to its bound recipient through the deterministic path
- **THEN** the transfer commits, the delivery stage advances, and no generative service is consulted

#### Scenario: Both surfaces reach the same rule
- **WHEN** the same delivery is performed once through the registered action and once through the
  player command
- **THEN** both invoke the identical deterministic rule and produce identical state changes and
  identical rejection reasons

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
the record is terminal. A refusal SHALL change no inventory, no quest log, and no other state.

#### Scenario: A distant recipient is refused
- **WHEN** the named recipient is not in the holder's location
- **THEN** the delivery is refused with a stable reason code and no state changes

#### Scenario: An unheld item is refused
- **WHEN** the holder no longer holds the objective's item
- **THEN** the delivery is refused with a stable reason code and no state changes

#### Scenario: An unbound recipient is refused
- **WHEN** the named co-located entity is not the bound recipient of any active delivery stage
- **THEN** the delivery is refused with a stable reason code and no state changes

#### Scenario: A refusal leaves the world untouched
- **WHEN** any refusal branch is taken
- **THEN** the holder's inventory, the recipient's inventory, and the quest log are byte-for-byte
  unchanged
