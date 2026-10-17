# Tasks

Total estimate: **5.5 hours**, including implementation, focused verification, documentation and integration.

## 1. Member cast rule (2.5h)

- [ ] 1.1 Add `cast_as_member`; verify in `world/rules/tests/test_companion_field_cast.py`: companion heal (caster MP 20, cost 8 → 12; target HP raised by the authored synthetic amount), SELF buff on the caster, practice XP on the caster only, one six-second advance settling the present party, refusals for knocked-out, absent, non-member and unowned skill; a companion's monster target reaches the initiation seam and is rejected with the existing stable reason until `companion-field-combat-opening` lands, with no session, resource or clock change.

## 2. Text suffix (1.5h)

- [ ] 2.1 Parse `由 <成員>` in `CmdCast`; out of combat call `cast_as_member`, in an active session submit the member's skill command through the existing actor command facade; verify in `commands/tests/test_cast_member_suffix.py` parity with the rule, draft-entry parity with `combat command`, and refusal messages.

## 3. Documentation and integration (1.5h)

- [ ] 3.1 Document the `由 <成員>` suffix (out of combat casts as the member; in combat saves that member's command; companion casts at monsters are documented by `companion-field-combat-opening`) in both player command documents and run `tests/test_command_docs.py`.
- [ ] 3.2 Register test modules in one shard each, annotate canonical IDs for the added `companion-field-actions` requirements, run the focused labels, the shard contract, `uv run --locked python -m tools.contract_gate` and `openspec validate companion-field-cast-rule --strict`.
