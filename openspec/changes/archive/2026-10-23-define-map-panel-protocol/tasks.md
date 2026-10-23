# Tasks

Implementation budget: 8 hours total. Prerequisites are the exact `depends-on` lines in proposal.md.

## 1. Implement the bounded slice

- [x] 1.1 Implement the exact Python/JS panel schemas and normalized map store slots from design.md, with stable map/frame discriminators and matched schema versions; do not register fake production presenters.
- [x] 1.2 Add separate same-epoch on-demand map storage and coordinator exclusion from eager rendering, preserving eager replacement and epoch clearing; amend both protocol tests.
- [x] 1.3 Implement the bounded map-only part codec and atomic logical reassembly with per-frame limits, finite count/bytes and epoch/revision guards; expose it for both area and world publishers.
- [x] 1.4 Document fixed wire forms, multipart constraints and which later change selects measured area/world numeric limits.

## 2. Focused behavioral verification

- [x] 2.1 Run one focused Python map-schema/part-codec module and one matching Node file for exact fields, frame identities, mixed panel budgets, complete/missing/duplicate/malformed/stale transfer behavior and eager snapshot retention/reset.
- [x] 2.2 Add a discoverable focused Python executed-evidence wrapper for browser-decoder Node assertions if needed for requirement ownership; register any package test modules and run only that wrapper/affected coordinator methods.

## 3. Contracts and focused handoff

- [x] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [x] 3.2 Copy the complete current implementation/tests/manifests/tooling into a disposable ordinary directory; merge prerequisite/current deltas into its copied main specs. Obtain canonical IDs with `tools.spec_traceability --repo-root <equivalent-root> list`, and retain literal intended `covers_requirement` annotations in implementation tests. Run `check` with that equivalent root and the copied contract gate from that directory before sync; the unsynced real-root gate is not an acceptance gate for new IDs.
- [x] 3.3 Run only the focused labels/files/classes named above and observability lint if logging changes; run strict validation and the equivalent-tree gate before handoff, then normal root `tools.spec_traceability check` and `tools.contract_gate` after sync. Record commands/results and existing-doc updates; no broad suites, CI shard commands or local full evidence verification.
