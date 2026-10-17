# Tasks

Total estimate: **6.5 hours**, including implementation, focused verification, documentation and integration.

## 1. Member cast rule and companion initiation (3.5h)

- [ ] 1.1 Add `cast_as_member` and the companion initiator path in `initiate_field_combat`; verify in `world/rules/tests/test_companion_field_cast.py`: companion heal (caster MP 20, cost 8 → 12; target HP raised by the authored synthetic amount), SELF buff on the caster, practice XP on the caster only, one six-second advance settling the present party, refusals for knocked-out, absent, non-member and unowned skill; a companion opening creates one commander-owned session with 艾拉's opening draft entry, charges no command time and changes MP/practice only when the entry resolves, and a failed companion initiation leaves no session, entry, resource or clock change.

## 2. Text suffix (1.5h)

- [ ] 2.1 Parse `由 <成員>` in `CmdCast`; out of combat call `cast_as_member`, in an active session submit the member's skill command through the existing actor command facade; verify in `commands/tests/test_cast_member_suffix.py` parity with the rule, draft-entry parity with `combat command`, and refusal messages.

## 3. Documentation and integration (1.5h)

- [ ] 3.1 Document the `由 <成員>` suffix (out of combat casts as the member; in combat saves that member's command; a companion's cast at a monster opens combat like the commander's) in both player command documents and run `tests/test_command_docs.py`.
- [ ] 3.2 Register test modules in one shard each, annotate canonical IDs for the added `companion-field-actions` requirements, run the focused labels, the shard contract, `uv run --locked python -m tools.contract_gate` and `openspec validate companion-field-cast-rule --strict`.
