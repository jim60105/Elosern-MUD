# Tasks

Total estimate: **6.5 hours**, including implementation, focused verification, documentation and integration.

## 1. Rules view (2.5h)

- [ ] 1.1 Add `inventory_view(member, *, in_combat)` with row grouping and the three descriptors; verify rules tests for equipped/locked give refusals with `max_quantity`, combat give refusal text, combat-draft use enabled for a commandable companion and disabled for a knocked-out one, and toggle reasons (accessory cap, exam kit).

## 2. Presenter, validator and mirror (2.5h)

- [ ] 2.1 Implement and register `party_inventory` v1 (purse, equipment, rows) for the viewed member; verify presenter tests (companion subject, possession-identical, malformed storage unavailable, maximal bound) and the JS mirror/parity/allowlist contract.

## 3. Selection wiring and integration (1.5h)

- [ ] 3.1 Add `party_inventory` to the `party.view_member` affected panels with an action test, register new test modules in one shard each, annotate canonical IDs for the added `webclient-party-inventory-panel` requirements, run `uv run --locked python -m tools.contract_gate` and `openspec validate party-inventory-panel --strict`.
