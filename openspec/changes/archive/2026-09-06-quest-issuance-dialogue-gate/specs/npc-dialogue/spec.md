# Delta spec: npc-dialogue (quest-issuance-dialogue-gate)

## MODIFIED Requirements

### Requirement: Intent application is deterministic, verified, and non-escalating

`world/rules/npc_intents.py` SHALL expose `apply_npc_intent(npc, player, intent) -> IntentOutcome` that verifies an extracted intent against the deterministic world before applying it, using existing deterministic APIs only. `request_guild_exam` SHALL delegate to change 16's `start_guild_exam(actor=player, examiner=npc, target_rank=..., requested_by="npc_intent")`, which rechecks co-location, the GuildExaminer component and branch, the exact next rank, true cumulative merit, and the absence of active combat/examination; the AI SHALL NOT be able to choose examiner stats, waive a gate, promote the player, or start combat directly. `give_item` and `take_item` SHALL verify that the giver actually holds the requested item quantity and SHALL transfer it through the validated inventory-planning boundary as one all-or-nothing operation whose failure restores both entities' database and in-process state. `adjust_relation` SHALL verify the bounded `delta` payload and delegate to `world/rules/affinity.py::apply_affinity_change(npc, player, "ai_dialogue", delta)` from `affinity-system`; the AI SHALL NOT choose a delta outside 0–10, and the applier SHALL report the actually applied amount (`IntentOutcome.delta_used`): a partially budget-applied delta SHALL be reported as applied with its applied amount, while a fully blocked or rejected delta (applied amount 0) SHALL be discarded as an intent with the speech kept. `party_invite` SHALL verify the boolean `accept` payload and, on `accept: true`, delegate to `world/rules/party.py::join_party(npc, player)` from `party-core`, which rechecks co-location, the NPC target, the absence of an existing binding, and the 4-companion bound; on `accept: false` it SHALL report an applied no-op. `offer_quest` SHALL verify the bounded `quest_key` payload and delegate to the dialogue-offer-quest applier, which rechecks the speaker's authored issuing authority (`GuildStaff` or `QuestIssuer`) and the registered issuance for the speaker's resolved issuer key under that issuer kind's own eligibility rule, then assigns the quest through the quest runtime in one all-or-nothing operation with +1 guild affinity. `reveal_lore` SHALL verify the bounded `category`/`key` payload and delegate to `world/rules/lore_knowledge.py::record_lore_reveal(player, category, key)`, which checks the category allowlist and registry resolvability and records the discovery append-only; a repeat reveal SHALL be an applied no-op and no affinity SHALL be granted. **Illegal or unverifiable intent SHALL be discarded while the speech is kept** — the world is never changed by an intent the NPC could not perform.

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
- **THEN** `apply_npc_intent` delegates to the dialogue-offer-quest applier, which rechecks the speaker's authored issuing authority and the registered issuance under that issuer kind's eligibility rule and assigns the quest through the quest runtime on success

#### Scenario: An offer-quest gate failure discards only the intent
- **WHEN** the offer-quest verification fails (speaker without an authored issuing authority, no issuance at the speaker's resolved issuer key, an ambiguous dual authority, malformed authority identity data, or a failed guild eligibility check)
- **THEN** the intent is discarded, the speech is preserved, and no quest or affinity state changes

#### Scenario: A reveal-lore intent records the discovery
- **WHEN** the extracted intent is `reveal_lore` with a bounded `category`/`key` that passes the allowlist and registry verification
- **THEN** the applier records the discovery through `record_lore_reveal`, reports applied, and grants no affinity

#### Scenario: A reveal-lore intent the NPC cannot perform is discarded
- **WHEN** the extracted intent is `reveal_lore` with an unknown category or an unresolvable key
- **THEN** the intent is discarded, the speech is preserved, and no codex record changes
