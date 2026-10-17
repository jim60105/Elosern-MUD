# Spec Delta

## MODIFIED Requirements

### Requirement: Service actions are exact, allowlisted, and server-authoritative
The existing service action allowlist and exact bounded payloads SHALL remain. Party member references SHALL appear only in the exact member-scoped fields their owning capabilities define (`inventory.toggle_equip` and `inventory.use` `actor_id`), each reauthorized by the rules and never replaced by the commander. guild.quest_abandon SHALL revalidate the authenticated owner and referenced record. Active private escort records MAY abandon without a guild host through the quest-owned compensated operation; ordinary guild counter actions retain existing host/eligibility gates. No other new action ID or host authority field SHALL be added.

#### Scenario: Existing registration reaches its deterministic API once
- **WHEN** an unregistered actor submits an empty `guild.register` at the local guild hall
- **THEN** the adapter resolves the local staff host and calls `register_adventurer`, and the snapshot thereafter reports rank F with the recorded branch

#### Scenario: Repeated registration is idempotent
- **WHEN** a registered actor submits an empty `guild.register` again after a state change between render and submit
- **THEN** the adapter returns the original record without replacing branch, tick, or snapshot, reports success, and refreshes canonical services/status panels

#### Scenario: Quest accept is board-gated
- **WHEN** a registered member submits `guild.quest_accept` with a visible definition key
- **THEN** the adapter revalidates board eligibility and creates exactly the deterministic quest record

#### Scenario: Quest tracking rides the lifecycle operation anywhere
- **WHEN** a holder submits `guild.quest_track` with a tracked-true payload for one of their active quests while standing outside any guild hall
- **THEN** the adapter calls the tracking operation exactly once, the commit reports success, and the refreshed payload reports the row's `tracked` true

#### Scenario: The tracking cap refusal mutates nothing
- **WHEN** a holder with three tracked active quests submits a fourth `guild.quest_track` tracked-true payload
- **THEN** the dispatch rejects with the lifecycle module's bounded refusal message and every record's tracking state is unchanged

#### Scenario: Exam start cannot choose an examiner or rank
- **WHEN** a client submits a non-next rank or includes a host, examiner, branch, clock or threshold field
- **THEN** exact validation or the coordinator rejects before any exam creation and only the exact next-rank payload is accepted

#### Scenario: Existing buy and sell submit only item and quantity
- **WHEN** a client submits `shop.buy` with item key and quantity only
- **THEN** the adapter re-resolves and rechecks the local merchant before calling deterministic economy settlement

#### Scenario: Inventory use submits only item key
- **WHEN** a client submits `inventory.use` with one item key and the user's `actor_id`
- **THEN** the adapter reauthorizes the member, resolves current mode and delegates to the matching deterministic item-use facade exactly once

#### Scenario: Inventory toggle submits only item key
- **WHEN** a client submits `inventory.toggle_equip` with one item key and the member's `actor_id`
- **THEN** the adapter reauthorizes the member and delegates to deterministic equipment toggle without accepting a client-selected slot

#### Scenario: Authority-like fields can never be supplied
- **WHEN** any service or inventory action contains an actor-like field outside its exact member reference, or a host, session, effect, or slot-like field
- **THEN** exact-schema validation rejects before adapter invocation

#### Scenario: Below merit request stays enabled
- **WHEN** a registered next-rank member below true merit threshold stands at a functioning guild counter and the qualified host is absent
- **THEN** merit_qualified is false, exam_request is enabled and dispatch returns exam_schedule without mutation

#### Scenario: Payload schemas are exact and bounded
- **WHEN** any service action payload is validated
- **THEN** `guild.register` accepts exactly an empty payload, guild quest and exam actions retain their exact
  bounded identifiers, `guild.quest_track` accepts exactly `quest_id` (the shared bounded quest identifier) and
  boolean `tracked`, and `shop.buy` and `shop.sell` retain exactly bounded `item_key` and integer `quantity`

#### Scenario: Registration idempotency is retained
- **WHEN** registration is submitted again after the actor is already registered
- **THEN** `guild.register` retains its current idempotency

#### Scenario: Inventory actions carry only a bounded item key
- **WHEN** an `inventory.use` or `inventory.toggle_equip` payload is validated
- **THEN** its `item_key` is a 1..64-character non-empty string, `inventory.toggle_equip` accepts exactly `actor_id` and `item_key`, and `inventory.use` accepts exactly `actor_id`, `item_key` and an optional `target_key`

#### Scenario: Adapters are session-scoped and re-resolve everything
- **WHEN** a service adapter runs
- **THEN** it resolves the authenticated actor and referenced canonical state, resolves local hosts where the action requires them, and delegates to the existing public owner; private escort abandonment needs no guild staff

#### Scenario: Inventory payloads reject every authority field
- **WHEN** an inventory payload carries any of host, branch, session, effect, consumable, quantity,
  slot, HP, combat, price, stock, or wallet fields, or any member reference other than its exact `actor_id`
- **THEN** exact-schema validation rejects it

#### Scenario: Adapters never write canonical state directly
- **WHEN** any adapter settles
- **THEN** no adapter assigns `.db`, traits, registration, rank, merit, quest log, wallet, inventory, equipment,
  merchant stock, location, combat, or clock state directly

#### Scenario: Actions never route through the text parser
- **WHEN** any service or inventory action is dispatched
- **THEN** no action routes an action ID or payload through the text command parser

#### Scenario: Host-independent escort abandonment uses the existing action
- **WHEN** a holder confirms guild.quest_abandon for an active owned private escort away from a counter
- **THEN** the unchanged quest_id payload invokes compensated abandonment once, releases only that record's sources and refreshes committed quest/party/dialogue state

#### Scenario: Forged terminal or foreign abandonment is refused
- **WHEN** a stale, invalidated, non-owned or foreign quest ID is submitted as a private escort abandonment
- **THEN** current domain authorization refuses without control, membership, quest or reward mutation
