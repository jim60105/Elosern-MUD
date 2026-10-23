# Tasks

Implementation budget: 6 hours total. Prerequisites are the exact `depends-on` lines in proposal.md.

## 1. Implement the bounded slice

- [x] 1.1 Measure representative and supported maximum payloads using final generated world geometry/roster and synthetic all-lit/trail/quest state; inspect actual frame limits and record measured UTF-8 sizes plus a finite selected bound.
- [x] 1.2 Implement strict world-map-only envelope and nested collection allowances in Python/JS while keeping local_map and all sibling budgets unchanged; reuse on-demand coordinator policy. If real transport proves insufficient, reuse and exercise the fixed upstream bounded epoch/revision map-part codec.
- [x] 1.3 Document transport decision, concrete bounds and round-trip evidence in the existing protocol development documentation.

## 2. Focused behavioral verification

- [x] 2.1 Add focused Python and one Node file parity tests covering >64 KB valid world maps, over-bound world maps, oversized unrelated/mixed panels and preserved scalar/field checks; run only the selected files/labels.
- [x] 2.2 Add proposed managed browser class `web.tests.browser.test_map_transport.WorldMapTransportTests` that sends the measured real-data payload through the actual server/portal socket and production browser adoption path; run just that class with `uv run --locked python -m web.tests.browser.unittest_driver <class>`, registering its methods in browser-shards.
- [x] 2.3 If parts are needed, test missing/duplicate/malformed/newer-revision/old-epoch parts and bounded memory in the same focused tests; otherwise record successful intact-frame evidence, not unexercised multipart claims.

## 3. Contracts and focused handoff

- [x] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [x] 3.2 Copy the complete current implementation/tests/manifests/tooling into a disposable ordinary directory; merge prerequisite/current deltas into its copied main specs. Obtain canonical IDs with `tools.spec_traceability --repo-root <equivalent-root> list`, and retain literal intended `covers_requirement` annotations in implementation tests. Run `check` with that equivalent root and the copied contract gate from that directory before sync; the unsynced real-root gate is not an acceptance gate for new IDs.
- [x] 3.3 Run only the focused labels/files/classes named above and observability lint if logging changes; run strict validation and the equivalent-tree gate before handoff, then normal root `tools.spec_traceability check` and `tools.contract_gate` after sync. Record commands/results and existing-doc updates; no broad suites, CI shard commands or local full evidence verification.
