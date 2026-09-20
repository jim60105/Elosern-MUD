## 1. The guard first

- [ ] 1.1 Capture the resolved shop catalog — every shop's offers, prices, stock and hours —
  before touching anything, and write the test that compares it after. Moving 470 lines of
  YAML by hand is exactly where a row goes missing.

## 2. The split

- [ ] 2.1 Create `rulebook/commerce/scales.yaml` with the `price_scales:` section.
- [ ] 2.2 Create `rulebook/commerce/altoria.yaml` with the four capital assortments and the
  four capital shop rows, moved verbatim.
- [ ] 2.3 Create `rulebook/commerce/ciaran.yaml` with the four elven assortments and the four
  village shop rows, moved verbatim.
- [ ] 2.4 Delete `rulebook/commerce.yaml`.

## 3. The loader

- [ ] 3.1 Replace the single `yaml.safe_load` of `commerce.yaml` in `guild_config.py` with a
  sorted read of every `*.yaml` in `rulebook/commerce/`.
- [ ] 3.2 Merge: concatenate `assortments:` and `shops:`, merge `price_scales:`. Reject a
  duplicate assortment key, shop key or settlement scale, naming the key and both files.
- [ ] 3.3 A parse or shape error must name the offending file, not just the rulebook.

## 4. Coverage

- [ ] 4.1 The resolved catalog is unchanged — the task 1.1 comparison passes.
- [ ] 4.2 Sections spread across synthetic files load as one catalog.
- [ ] 4.3 A duplicate key across two synthetic files fails naming both.
- [ ] 4.4 Run the rules-commerce, guild-config and guild-economy-sync suites plus
  `uv run --locked python -m tools.spec_traceability check`.
