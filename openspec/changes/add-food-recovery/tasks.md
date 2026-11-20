# Tasks

## 1. Author and verify food recovery

- [ ] 1.1 Add the eleven profiles from `design.md` to the existing catalog rows and regenerate `content/map-reference-context.json`. Verify all eleven profiles load, match the design, and retain their current shop offers and prices.
- [ ] 1.2 Exercise a synthetic food profile through the existing item-use boundary. Verify capped recovery of two gauges and consumption of exactly one serving outside combat, and verify combat refusal leaves both gauges and inventory unchanged. Add a regression test only where existing coverage does not establish the food contract, and use the verified test for requirement traceability when the delta is synced.

## 2. Handoff checks

- [ ] 2.1 Run the focused item-use tests, the repository contract gate, and `openspec validate add-food-recovery --strict`.
