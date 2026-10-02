## 1. Deterministic NPC-only normalization

- [ ] 1.1 Implement one explicit finite-set normalizer for Python NPC card leaves/greetings and its JS mirror, preserving stable caller errors; verify CRLF-pair/lone-CR order and exact boundary exclusions without changing generic player persona code.
- [ ] 1.2 Extend existing shared boundary fixtures with expected normalized outputs for every enumerated whitespace point, U+FEFF/U+0085, excluded controls/zero-width points, interior preservation, optional clears, required-empty errors and astral/budget boundaries; verify both runtimes agree on text, reason/leaf and labeled totals.

## 2. Equality and version behavior

- [ ] 2.1 Route NPC editor draft/baseline, dirty-close and reconnect comparisons through complete normalized card-plus-greeting equality where current code diverges; verify boundary-only input stays clean, interior/excluded characters stay dirty, and raw local drafts survive failures.
- [ ] 2.2 Exercise real server current-version boundary-only/CRLF no-ops, optional clear/repeated clear and stale-version equal submissions; verify unchanged version for equality, exactly one advance for actual clearing, and conflict rejection without persistence for stale equality.
- [ ] 2.3 Exercise frontend interrupted-save/reconnect fresh-read handling with normalized equality; verify no guessed success, no second save before authoritative read and no phantom dirty/version changes, retaining request/epoch correlation.

## 3. Future consumer proof and documentation

- [ ] 3.1 Run focused Python card/persona and Node mirror/editor tests after integration, preserving fixture ownership and generic player tests; verify limits remain 600/600/2000 for cards and 300/no-LF for greeting with Unicode code-point counting.
- [ ] 3.2 In a real browser editor, save values surrounded by U+0085/U+FEFF, reopen to inspect canonical values, try optional clears and boundary-only edits, then interrupt/reconnect one save and inspect authoritative version/dirty state. Record actual surface behavior rather than mock payload echoes.
- [ ] 3.3 Document the exact finite whitespace policy, normalization order and no-op semantics in NPC authoring guidance/changelog, update traceability and run strict OpenSpec validation; confirm no companion prose/player preset rewrite or migration. These are future implementation tasks; no runtime/test commands run during proposal authoring.
