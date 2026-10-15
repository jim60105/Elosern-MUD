# Tasks

Total estimate: **6.5 hours**, including implementation, focused verification, documentation and integration. Prerequisites and file/spec conflicts are in proposal.md and the shared batch contract. Every group lands its own relevant tests/docs; the final group checks integration.

## 1. Bounded implementation and evidence (1.5h)

- [ ] 1.1 Introduce commander/actor authorization and stable rejection reasons; test enemy, other party, stale/moved/down/action-forbidden actor and unchanged account puppet.

## 2. Bounded implementation and evidence (1.5h)

- [ ] 2.1 Parameterize shared skill choice/target/scale preview by actor; prove SELF and MP/SP use companion state without commander capability leakage.

## 3. Bounded implementation and evidence (1.5h)

- [ ] 3.1 Build actor-local usable-item choices and canonical request conversion through existing item preflight; test item targets, no-effect rejections, inventory/mirror ownership and no shared bag.

## 4. Bounded implementation and evidence (0.75h)

- [ ] 4.1 Document actor API and exclusions in existing combat developer docs and approved design references; annotate requirements and register any new test modules.

## 5. Integration gate (1.25h)

- [ ] 5.1 Run focused combat-view, targeting and item-turn tests plus tools.contract_gate; include synthetic adversarial authorization and source-of-cost assertions.
