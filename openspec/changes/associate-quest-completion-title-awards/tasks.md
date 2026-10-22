# Tasks

## 1. Settle completion awards in the quest owner

- [ ] 1.1 Add the narrow rules-layer completion-award operation that evaluates the existing registry predicate and grants through the unified automatic award entry point, verifying a synthetic quest-completed title records the completion source, recipient and granted identity.
- [ ] 1.2 Remove the quest-completed predicate family from generic action-time automatic grant discovery while keeping the pure predicate evaluator, verifying an unrelated later skill action cannot discover or grant that completion title.
- [ ] 1.3 Finalize all completion award results before the immutable fact is written, verifying several grants from one completion share its source and a new occurrence with an already-owned title yields no new grant.
- [ ] 1.4 Return the original committed results before reevaluation on replay, verifying a replayed completion neither grants again nor loses the source's suppression effect.
- [ ] 1.5 Document the completion occurrence attribution and carry the unchanged starter reward-claim attribution, verifying no shipped registry row changed and the starter epithet still belongs to its claim.

## 2. Make rollback and forwarding complete

- [ ] 2.1 Extend title collection and equipped-state rollback ownership to every enclosing completion writer (purchase/inventory, delivery, arrival, automatic chain, action), verifying each caller has an explicit snapshot path and no parallel undo system was added.
- [ ] 2.2 Inject failure after the inner quest writer returns but before each outer owner commits, verifying gameplay, title collection and equipped state, award evidence, events and pending projection work restore in both durable storage and warmed caches.
- [ ] 2.3 Forward finalized completion results through the existing post-commit envelope into the unchanged generic award check, verifying a synthetic future completion title suppresses its immediate nomination without service changes and the deed remains usable at later wake or logout.
- [ ] 2.4 Verify recipient specificity and ownership semantics: another recipient's award does not suppress the player, and a new completion merely encountering the player's previously owned title does not suppress it.

## 3. Integration verification

- [ ] 3.1 Run a real completion with a synthetic registered title through settlement, nomination and a fresh committed read, verifying suppression is local to that occurrence, the ballot is unchanged and the next trigger can still cite the deed.
- [ ] 3.2 Replace the misleading quest-award smoke claim, verifying the evidence comes from real completion settlement rather than directly inserted award rows.
- [ ] 3.3 Run the focused title, quest and economy test labels plus `uv run --locked python -m tools.contract_gate`, verifying no unrelated automatic award path regressed.
