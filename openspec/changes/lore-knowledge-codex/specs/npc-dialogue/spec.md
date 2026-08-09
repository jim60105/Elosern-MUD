## MODIFIED Requirements

### Requirement: Intent extraction is whitelisted and shape-validated per kind

The `npc_dialogue` output contract SHALL restrict `intent.kind` to exactly the eight whitelisted kinds `give_item` / `take_item` / `offer_quest` / `request_guild_exam` / `adjust_relation` / `reveal_lore` / `party_invite` / `none`. The `request_guild_exam` intent SHALL carry exactly one payload field, `target_rank`; `give_item` and `take_item` SHALL carry `item_key` and a positive `qty`; `adjust_relation` SHALL carry exactly one payload field, `delta`, a non-negative integer with `0 <= delta <= 10`; `party_invite` SHALL carry exactly one payload field, `accept`, a boolean; `offer_quest` SHALL carry exactly one payload field, `quest_key`, a non-empty string of at most 64 code points; `reveal_lore` SHALL carry exactly two payload fields, `category` and `key`, each a non-empty string of at most 64 code points. Outputs whose kind is outside the whitelist or whose payload violates the per-kind shape SHALL be rejected by a semantic validator and retried within the budget. Whitelisting an intent kind SHALL mean the shape is accepted for extraction; it does not guarantee the intent is executable (executability is decided by the deterministic applier).

#### Scenario: A whitelisted intent with a valid payload passes
- **WHEN** the model returns an intent such as `{"kind": "give_item", "item_key": "healing_potion", "qty": 1}`, `{"kind": "request_guild_exam", "target_rank": "E"}`, `{"kind": "adjust_relation", "delta": 3}`, `{"kind": "party_invite", "accept": true}`, `{"kind": "offer_quest", "quest_key": "forest_clearing"}`, or `{"kind": "reveal_lore", "category": "race", "key": "ciaran"}`
- **THEN** the intent passes semantic validation and proceeds to deterministic verification

#### Scenario: An unknown kind is rejected and retried
- **WHEN** the model returns an `intent.kind` outside the eight-kind whitelist
- **THEN** the output is treated as a validation failure, the error is appended, and the pipeline retries within the budget

#### Scenario: A malformed exam payload is rejected
- **WHEN** the model returns `request_guild_exam` with a payload other than exactly one `target_rank` field
- **THEN** the output is rejected by the per-kind semantic validator and retried rather than passed to the engine

#### Scenario: An out-of-range delta payload is rejected
- **WHEN** the model returns `adjust_relation` with `delta` below 0, above 10, fractional, or with any extra payload field
- **THEN** the output is rejected by the per-kind semantic validator and retried rather than passed to the engine

#### Scenario: A malformed party-invite payload is rejected
- **WHEN** the model returns `party_invite` with a non-boolean `accept`, a missing `accept`, or any extra payload field
- **THEN** the output is rejected by the per-kind semantic validator and retried rather than passed to the engine

#### Scenario: A malformed offer-quest payload is rejected
- **WHEN** the model returns `offer_quest` with a missing, empty, non-text, or extra-field payload
- **THEN** the output is rejected by the per-kind semantic validator and retried rather than passed to the engine

#### Scenario: A malformed reveal-lore payload is rejected
- **WHEN** the model returns `reveal_lore` with a missing, empty, non-text, or extra-field payload
- **THEN** the output is rejected by the per-kind semantic validator and retried rather than passed
  to the engine

### Requirement: Intent application is deterministic, verified, and non-escalating

`world/rules/npc_intents.py` SHALL expose `apply_npc_intent(npc, player, intent) -> IntentOutcome` that verifies an extracted intent against the deterministic world before applying it, using existing deterministic APIs only. `request_guild_exam` SHALL delegate to change 16's `start_guild_exam(actor=player, examiner=npc, target_rank=..., requested_by="npc_intent")`, which rechecks co-location, the GuildExaminer component and branch, the exact next rank, true cumulative merit, and the absence of active combat/examination; the AI SHALL NOT be able to choose examiner stats, waive a gate, promote the player, or start combat directly. `give_item` and `take_item` SHALL verify that the giver actually holds the requested item quantity and SHALL transfer it through the validated inventory-planning boundary as one all-or-nothing operation whose failure restores both entities' database and in-process state. `adjust_relation` SHALL verify the bounded `delta` payload and delegate to `world/rules/affinity.py::apply_affinity_change(npc, player, "ai_dialogue", delta)` from `affinity-system`; the AI SHALL NOT choose a delta outside 0–10, and the applier SHALL report the actually applied amount (`IntentOutcome.delta_used`): a partially budget-applied delta SHALL be reported as applied with its applied amount, while a fully blocked or rejected delta (applied amount 0) SHALL be discarded as an intent with the speech kept. `party_invite` SHALL verify the boolean `accept` payload and, on `accept: true`, delegate to `world/rules/party.py::join_party(npc, player)` from `party-core`, which rechecks co-location, the NPC target, the absence of an existing binding, and the 4-companion bound; on `accept: false` it SHALL report an applied no-op. `offer_quest` SHALL verify the bounded `quest_key` payload and delegate to the dialogue-offer-quest applier, which rechecks the GuildStaff component and branch, the registered offer at that branch, and the player's canonical rank band, then assigns the quest through the quest runtime in one all-or-nothing operation with +1 guild affinity. `reveal_lore` SHALL verify the bounded `category`/`key` payload and delegate to `world/rules/lore_knowledge.py::record_lore_reveal(player, category, key)`, which checks the category allowlist and registry resolvability and records the discovery append-only; a repeat reveal SHALL be an applied no-op and no affinity SHALL be granted. **Illegal or unverifiable intent SHALL be discarded while the speech is kept** — the world is never changed by an intent the NPC could not perform.

> **Removed scenario.** The former "A whitelisted but not-yet-executable intent is rejected without state change" scenario is removed by this change: `reveal_lore` becomes executable here, `offer_quest` became executable in `dialogue-offer-quest`, and no forward-declared intent kinds remain.

#### Scenario: A guild exam intent is routed through the deterministic gate
- **WHEN** the extracted intent is `request_guild_exam` with a `target_rank`
- **THEN** `apply_npc_intent` calls `start_guild_exam(actor=player, examiner=npc, target_rank=..., requested_by="npc_intent")`, which applies its own checks and records the exam outcome

#### Scenario: A failed exam gate discards only the intent
- **WHEN** `start_guild_exam` rejects the request (remote examiner, wrong branch, wrong next rank, below merit threshold, or active combat/exam)
- **THEN** the intent is discarded, the speech is preserved, and no exam, rank, or combat state changes

#### Scenario: An item intent verifies holdings before transfer
- **WHEN** the extracted intent is `give_item` or `take_item` and the giver holds the requested item quantity
- **THEN** the items transfer through the inventory-planning boundary and the result is reported deterministically

#### Scenario: An item intent the giver cannot perform is discarded
- **WHEN** the extracted intent asks for an item the giver does not hold or a quantity it cannot provide
- **THEN** the intent is discarded, the speech is kept, and no inventory changes

#### Scenario: A failed transfer rolls back both entities atomically
- **WHEN** the second side of a two-entity item transfer fails after the first side applied
- **THEN** both entities' database inventory and in-process attributes return to their pre-transfer state, and no partial transfer is observable

#### Scenario: An adjust_relation delta applies through the sole-writer API
- **WHEN** the extracted intent is `adjust_relation` with `delta` 0–10 and the daily budget permits the full amount
- **THEN** `apply_affinity_change(npc, player, "ai_dialogue", delta)` applies the delta and the applier reports `applied=True` with the applied amount

#### Scenario: A partially budgeted delta applies what the budget allows
- **WHEN** the extracted intent is `adjust_relation` with `delta` 4 and only 2 budget remains
- **THEN** exactly 2 is applied and the applier reports `applied=True` with `delta_used=2`

#### Scenario: A fully budget-capped delta discards only the intent
- **WHEN** the extracted intent is `adjust_relation` with an in-range delta and no budget remains
- **THEN** the intent is discarded with a capped outcome (`applied=False`), the speech is preserved, and no affinity state changes

#### Scenario: A zero delta creates no affinity record
- **WHEN** the extracted intent is `adjust_relation` with `delta` 0, including for a recordless player on a later world day
- **THEN** the intent is discarded (`applied=False`), the writer is not invoked, and no affinity record is created or modified

#### Scenario: An accepted party invite routes through join_party
- **WHEN** the extracted intent is `party_invite` with `accept: true`
- **THEN** `apply_npc_intent` delegates to `join_party(npc, player)`, which applies its own co-location, target, binding, and party-bound checks and creates the binding on success

#### Scenario: A declined party invite is an applied no-op
- **WHEN** the extracted intent is `party_invite` with `accept: false`
- **THEN** the outcome reports applied without any membership change

#### Scenario: A join gate failure discards only the intent
- **WHEN** `join_party` rejects the request (remote NPC, full party, or duplicate binding)
- **THEN** the intent is discarded, the speech is preserved, and no binding changes

#### Scenario: An offer-quest intent routes through the dialogue-offer-quest applier
- **WHEN** the extracted intent is `offer_quest` with a valid `quest_key`
- **THEN** `apply_npc_intent` delegates to the dialogue-offer-quest applier, which rechecks the GuildStaff component and branch, the registered offer, and the player's rank band and assigns the quest through the quest runtime on success

#### Scenario: An offer-quest gate failure discards only the intent
- **WHEN** the offer-quest verification fails (NPC not GuildStaff, unregistered offer at the branch, or rank below the quest band)
- **THEN** the intent is discarded, the speech is preserved, and no quest or affinity state changes

#### Scenario: A reveal-lore intent records the discovery
- **WHEN** the extracted intent is `reveal_lore` with a bounded `category`/`key` that passes the allowlist and registry verification
- **THEN** the applier records the discovery through `record_lore_reveal`, reports applied, and grants no affinity

#### Scenario: A reveal-lore intent the NPC cannot perform is discarded
- **WHEN** the extracted intent is `reveal_lore` with an unknown category or an unresolvable key
- **THEN** the intent is discarded, the speech is preserved, and no codex record changes
