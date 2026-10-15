# Tasks

Total estimate: **6.5 hours**, including implementation, focused verification, documentation and integration. Direct prerequisites and file/spec conflicts are in proposal.md and the shared batch contract. Each group lands its own tests/docs; the final group checks integration.

## 1. Bounded implementation and evidence (1.5h)

- [ ] 1.1 Extend the closed equipment loader, entry model and rarity-budget validation and author valid initial ceiling1.0 cells for every shipped rarity; test startup load plus malformed/bool/nonfinite/below-one/nonweapon/over-budget cases.

## 2. Bounded implementation and evidence (1.5h)

- [ ] 2.1 Implement one pure main/off-hand factor read and physical scalar wiring; test dual wield, nonweapon main hand, empty hands, elemental physical, magic and healing controls.

## 3. Bounded implementation and evidence (1h)

- [ ] 3.1 Wire AI decision reads and estimation to the same factor; pin multi-strike and conditional/critical multiplication with independent synthetic expected amounts.

## 4. Bounded implementation and evidence (0.75h)

- [ ] 4.1 Extend deterministic equipment prose and its tests; document the nonadditive field and keep old flat/off-hand/passive semantics.

## 5. Bounded implementation and evidence (0.75h)

- [ ] 5.1 Update traceability and shard manifests for added tests; run focused rulebook, equipment, damage and estimator tests.

## 6. Integration gate (1h)

- [ ] 6.1 Run tools.contract_gate and focused observability checks if a logging path changed; document the calibration dependency without claiming shipped growth is complete.
