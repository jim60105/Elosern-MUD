## 1. Implement the bounded behavior

- [x] 1.1 Author and expose branch letter service via existing anchoring plus text send/collect/read commands; verify any-branch acquisition, recipient ambiguity and context rejection.
- [x] 1.2 Add browser server actions/read models and client controls with matching text behavior; verify unauthorized owner and uncollected-body requests are rejected.
- [x] 1.3 Record first-read transactionally once and preserve collected unread state; verify portable reread and duplicate submissions.
- [x] 1.4 Update both command docs and their contract tests; verify actual keys/aliases/syntax/context agree with server behavior.

## 2. Evidence and handoff

- [x] 2.1 Add synthetic behavior tests for every delta scenario and use recorded/FakeLLMClient responses only; verify no permanent test calls live model/image services and any shipped-lore test is a registered data-contract test.
- [x] 2.2 Register each new/moved Evennia test module in exactly one `.github/evennia-shards.json` shard; obtain existing canonical main requirement IDs with `uv run --locked python -m tools.spec_traceability list` and annotate substantive tests. After delta sync makes new main IDs available, obtain them from that same tool rather than guessing; verify traceability and shard contracts.
- [x] 2.3 Update owning developer documentation/changelog and applicable command documentation, extend the observability catalog for new boundary events, and use only `world.observability` with IDs/counts/context and exception chains; verify logging privacy and focused facade assertions.
- [x] 2.4 Run focused tests, the actual changed-path recorded/offline smoke, `uv run --locked python -m tools.contract_gate`, and `openspec validate correspondence-player-surface --strict`; record exercised results and leave broad browser/evidence gates CI-owned.

## Exercised evidence

- Focused guarded Evennia run: 94 tests passed, including player surface,
  predecessor delivery, authored settlement contracts, actual service-interior
  bootstrap, both command-document contracts and shard ownership. The surface
  suite includes actual text send → clock delivery → another-branch browser
  collection → remote browser/text read/reread with no generation dependencies.
- Focused Vue run: 114 tests passed across letters, navigation, shared drawers,
  store drawer teardown and command-echo surface contracts.
- Dependency-free Node gate: 479 tests passed.
- Production bundle and offline Storybook builds passed; showcase coverage
  passed with all 63 registered/required component titles.
- Actual isolated Storybook branch folio opened in agent-browser, accessible
  controls inspected, explicit letter opened and screenshot visually reviewed.
- `tools.contract_gate` passed: 1836 main requirements covered, zero
  observability or test-data violations, manifests and 18 repository contracts.
- `openspec validate correspondence-player-surface --strict` and
  `git diff --check` passed.
- Canonical current IDs came from `tools.spec_traceability list --json-output`.
  New delta IDs remain the later sync/archive owner's responsibility, obtained
  from that same tool after sync. No main spec is changed here.
- Broad managed browser and evidence-verification gates remain CI-owned.

## Single final review disposition

The final rubber-duck review found no blockers and no suggestions. Its one
non-blocking finding was that separate text command invocations have no stable
retry identity. Both player references and the owning developer guide now
explicitly document text sends as new letters and prohibit automatic uncertain
resubmission. An additional identified text-retry command is not introduced:
body-based deduplication would suppress intentional identical letters, and
transport retries cannot be inferred from separate text commands. Browser
identified retries and transactional first-read deduplication remain covered.
