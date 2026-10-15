# Tasks

Total estimate: **6 hours**, including implementation, focused verification, documentation and integration. Prerequisites and file/spec conflicts are in proposal.md and the shared batch contract. Every group lands its own relevant tests/docs; the final group checks integration.

## 1. Bounded implementation and evidence (1.5h)

- [ ] 1.1 Add bounded revision/session/operation confirmation tokens and atomic admission; test cancel, stale, cross-account/session/operation tokens and round-vs-surrender races.

## 2. Bounded implementation and evidence (1.5h)

- [ ] 2.1 Implement confirmed surrender through existing settlement with receipt/draft cleanup; test hostile aftermath, exam FAIL, zero added round and once-only accumulated time.

## 3. Bounded implementation and evidence (1h)

- [ ] 3.1 Remove direct public unconfirmed forfeit/allied-flee bypasses, route existing text aliases to explicit token prompts and preserve enemy flee; test forged calls and confirmation replay.

## 4. Bounded implementation and evidence (0.75h)

- [ ] 4.1 Inject technical failure during settlement and test draft/cache restoration and retry; document confirmation protocol and existing command syntax.

## 5. Bounded implementation and evidence (0.75h)

- [ ] 5.1 Update both command docs, command manifest expectations, traceability and shard registration for changed availability/confirmation.

## 6. Integration gate (0.5h)

- [ ] 6.1 Run focused exit/aftermath/exam/command tests plus tools.contract_gate and observability lint/focused boundary-event tests.
