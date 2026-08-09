## 1. Payload shape and whitelist

- [ ] 1.1 Extend the `npc_dialogue` per-kind semantic validator so `offer_quest` accepts exactly one
      non-empty `quest_key` field of at most 64 code points (shared named constant
      `MAX_INTENT_KEY_LENGTH`); missing, empty, over-length, non-text, or extra-field payloads
      reject and retry.
- [ ] 1.2 Remove `offer_quest` from `_FORWARD_DECLARED_KINDS` in `world/rules/npc_intents.py`,
      leaving `("reveal_lore",)`.
- [ ] 1.3 Add validator tests: valid `{"quest_key": ...}` passes; missing/empty/non-text/extra-field
      payloads reject and retry; exactly-64 passes and 65 rejects (boundary).

## 2. Applier

- [ ] 2.1 Implement `_apply_offer_quest(npc, player, intent)` in `world/rules/npc_intents.py`:
      verification order — NPC type and `GuildStaff` component with `branch_key`,
      `get_guild_offer(quest_key, branch_key)` resolves, player registered member with a canonical
      rank within the offer's quest rank band (reuse the canonical eligibility check
      `list_guild_offers` applies, including the unregistered/rankless rejection paths).
- [ ] 2.2 Implement the atomic application: `with transaction.atomic(): accept_quest(player,
      quest_key)` plus `apply_affinity_change(npc, player, AffinitySource.GUILD, 1)`, with
      `quest_log` and `relations_data` snapshots restored on any exception (mirroring
      `accept_guild_offer`); the affinity write follows the sole writer's budget rules — a capped
      (applied 0) write commits the quest without rollback, exactly like the board path.
- [ ] 2.3 Wire `offer_quest` into `apply_npc_intent` dispatch; every failure path returns
      `IntentOutcome(applied=False, reason=...)` with the speech preserved.
- [ ] 2.4 Applier tests (`EvenniaTest`): success assigns the quest and applies the guild affinity
      write in one committed transaction; budget-capped affinity applies 0 without rolling back the
      quest; every rejection reason (non-NPC, no GuildStaff, unregistered offer, unregistered or
      rankless player, rank below band) discards only the intent; duplicate-quest rejection
      delegated to the quest runtime; injected commit failure restores quest log and affinity
      record.

## 3. Spec and contract updates

- [ ] 3.1 Update the `npc-dialogue` main spec by syncing the delta (offer_quest payload shape,
      executable offer_quest, not-yet-executable scenario now covers only `reveal_lore`) per the
      archive/sync workflow.
- [ ] 3.2 Annotate new `dialogue-offer-quest` main requirements with `covers_requirement` (literal
      IDs from `python -m tools.spec_traceability list`) and keep `spec_traceability check` green.
- [ ] 3.3 Run the affected Evennia test domains (world.rules, world.ai dialogue-layer tests) and
      confirm existing guild/quest/affinity suites stay green.
- [ ] 3.4 Run `openspec validate --change dialogue-offer-quest --strict`.
- [ ] 3.5 Run the affected test entry points with one shared `OPENSPEC_TEST_EVIDENCE` path, then
      run `python -m tools.spec_traceability verify --evidence` (AGENTS.md handoff gate).
