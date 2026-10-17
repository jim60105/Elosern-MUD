# Tasks

Total estimate: **4.5 hours**, including implementation, focused verification, documentation and integration.

## 1. 給 routing (1.5h)

- [ ] 1.1 Route `CmdGive` to `transfer_item` when the target token resolves to a member; verify in `commands/tests/test_party_transfer_commands.py` a member give with quantity, a non-member NPC give and a quest delivery give unchanged, and the in-combat refusal message.

## 2. 取回 command (1.5h)

- [ ] 2.1 Add `CmdRetrieve` (`取回`, alias `retrieve`) to `commands/items.py` and the character cmdset; verify success, possession retrieval into the commander's bag, `item_equipped`, `item_locked`, `not_party_member` and `member_not_present` refusals with byte-identical bags.

## 3. Documentation and integration (1.5h)

- [ ] 3.1 Document `給 [數量] <物品> = <成員>` member routing and `取回 [數量] <物品> = <成員>` in `docs/game/commands.md` and `docs/game/command-reference.md` (out of combat only, free, no affinity effect); verify `tests/test_command_docs.py` passes.
- [ ] 3.2 Register the test module in one shard, annotate canonical IDs for the modified `equipment-inventory` requirement and the added `party-item-transfer` requirement, run the shard contract, `uv run --locked python -m tools.contract_gate` and `openspec validate party-transfer-text-commands --strict`.
