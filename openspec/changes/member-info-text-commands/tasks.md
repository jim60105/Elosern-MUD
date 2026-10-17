# Tasks

Total estimate: **4.5 hours**, including implementation, focused verification, documentation and integration.

## 1. 狀態 (1.5h)

- [ ] 1.1 Add `CmdMemberStatus` (`狀態`, alias `status` if free) rendering resources, traits with layers, conditions with source, guild and labelled disguise; verify in `commands/tests/test_party_views.py` the commander default, a disguised companion's true values, possession-identical output and the non-member refusal.

## 2. 技能 (1.5h)

- [ ] 2.1 Add `CmdMemberSkills` (`技能`, alias `skills` if free) with a `skills_text` helper; verify levels, capped, booked, new and ladder output equal the v9 presenter facts for the same member, and an alias-collision test over the character cmdset.

## 3. Documentation and integration (1.5h)

- [ ] 3.1 Document both commands in both player command documents and run `tests/test_command_docs.py`; register the test module in one shard; annotate canonical IDs for the added `party-member-text-views` requirements; run `uv run --locked python -m tools.contract_gate` and `openspec validate member-info-text-commands --strict`.
