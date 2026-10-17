# Tasks

Total estimate: **6.5 hours**, including implementation, focused verification, documentation and integration.

## 1. Commander/caster split in initiation (3h)

- [ ] 1.1 Key `engage_group`, `_candidate_record`, `_prepare_opening`, `initiate_field_combat` snapshots and `submit_opening_action` on the resolved commander and seed the caster's entry through `authorize_combat_actor`; verify in `world/rules/tests/test_companion_field_opening.py` possessed and commanded companion initiators (commander-owned session, caster first actor, caster entry, no command time, cost/practice only on resolution), injected failure leaving nothing, and forged/absent/knocked-out casters rejected before any session; keep the commander-path tests unchanged.

## 2. Preview and seam removal (1.5h)

- [ ] 2.1 Make `preview_field_opening` caster-aware and replace the `companion-field-cast-rule` seam with the real route; verify preview openings for a companion equal what initiation accepts.

## 3. Text, docs and integration (2h)

- [ ] 3.1 Verify `cast … 由 <成員>` at a monster opens combat for the member; describe it in both player command documents and run `tests/test_command_docs.py`; add `caster` to the initiation event context and run `uv run --locked python -m tools.observability_lint check`; register the test module; annotate canonical IDs; run `uv run --locked python -m tools.contract_gate` and `openspec validate companion-field-combat-opening --strict`.
