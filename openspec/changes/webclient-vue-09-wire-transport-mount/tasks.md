## 1. Bind the store to the live transport

- [ ] 1.1 Bind the C1 store to the `evennia.js` OOB events (snapshot/update/result/protocol-error); snapshot adoption, dispatch-only, one-mutation-in-flight, no local mutation
- [ ] 1.2 Add reconnect / epoch / lock integration tests against a real managed server (new-epoch lower-revision adoption, delayed old-epoch message changes nothing, stale controls stay locked)

## 2. Store-bound views + harness proof (production unchanged)

- [ ] 2.1 Bind the B-wave components to the store as the live renderers (passive; emit dispatch intents only); the keyboard router keeps focusing the preserved `#action-dock`
- [ ] 2.2 Add a managed-browser slice that mounts the Vue app via A2's XOR flag **in the test config only** against a real server and asserts transport round-trip, store adoption, and dispatch
- [ ] 2.3 In the harness, prove the vanilla text console is the fallback (bundle blocked → text still sends/renders)
- [ ] 2.4 Add a check that the production `base.html` default is UNCHANGED (still legacy) at this change and the existing production behavioral browser suite is unaffected

## 3. Gate + traceability

- [ ] 3.1 Evennia + managed browser (including the new harness slice) + Node + Vitest green; offline invariant holds (no remote request); the text fallback path works
- [ ] 3.2 Add `@covers_requirement`-annotated Python tests (wrapping the new harness/browser + Node execution) for each main requirement this change adds or modifies; run `uv run --locked python -m tools.spec_traceability check` and the `verify --evidence` flow so the traceability gate is green at this change's archive
