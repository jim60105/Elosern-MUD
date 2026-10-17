# Tasks

Total estimate: **6.5 hours**, including implementation, focused verification, documentation and integration.

## 1. Shared sections and rules read (1.5h)

- [ ] 1.1 Extract persona/intimate serializers into `persona_sections.py` (character keeps using them) and add `bond_stage_position`; verify the existing character panel tests stay green and a unit test pins step/steps against a synthetic stage table.

## 2. Presenter and validator (2.5h)

- [ ] 2.1 Implement `party_member` v1 with descriptors and register it; verify in `web/webclient/presentation/tests/test_party_member_panel.py` companion/commander payloads, escort-bound leave, possessed release with an otherwise identical payload, commander persona while possessing, fallback to the commander, maximal bounds, no raw affinity, and an unchanged attribute snapshot after rendering.

## 3. Mirrors and selection wiring (1.5h)

- [ ] 3.1 Add the JS mirror, parity entries, store allowlist and fixtures; add `party_member` to the `party.view_member` affected panels; verify the Node mirror tests, the allowlist contract and an action test that selection republishes the panel.

## 4. Integration (1h)

- [ ] 4.1 Register the new test module in one shard, annotate canonical IDs for the added `webclient-party-member-panel` requirements, run `uv run --locked python -m tools.contract_gate` and `openspec validate party-member-panel --strict`.
