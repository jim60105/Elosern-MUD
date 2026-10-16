# Tasks

Total estimate: **6 hours**, including implementation, focused verification, documentation and integration. Direct prerequisites and file/spec conflicts are in proposal.md and the shared batch contract. Each group lands its own tests/docs; the final group checks integration.

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

## Annotation timing

This change's own new requirement (the session/round/operation-bound party exit and its surrender settlement) has no identifier in `openspec/specs/` until the archive step syncs the delta, and `tools.spec_traceability check` rejects unknown identifiers. The new tests therefore annotate only the existing main-spec requirements they genuinely establish (`player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes`, `...::combat-time-settles-once-at-terminal-session-outcome`, `...::round-revisions-execute-at-most-once-across-retries-and-stale-requests`); the added requirement's annotations must be attached during the archive sync, exactly as the sibling changes in this batch did.
