## Context

Static source: `npc_persona_card.js:92–97` uses CRLF replacement then JavaScript `trim`; Python `_normalize_text_leaf` (166–172) and `normalize_offline_greeting` (324–338) use replacement then `strip`. U+FEFF is removed only by JS; U+0085 only by Python. Shared equality therefore cannot rely on either language's builtin whitespace definition. Existing limits are 600-code-point card leaves, 600 labeled identity section, 2000 labeled card block, and 300-code-point greeting (not the review's 600).

## Goals / Non-Goals

**Goals:** Deterministic cross-language normalization, acceptance, budget and equality for NPC cards and greetings, including optional clearing and recovery after uncertain saves.

**Non-Goals:** Changing player generic persona handling, NFC/NFKC, collapsing interior spaces, converting Unicode separators to LF, text-output escaping, migration or compatibility normalization.

## Decisions

### Freeze a finite boundary set

Use the Unicode White_Space set plus U+FEFF, enumerated explicitly rather than a Unicode property or builtin: U+0009–U+000D, U+0020, U+0085, U+00A0, U+1680, U+2000–U+200A, U+2028, U+2029, U+202F, U+205F, U+3000, U+FEFF. This includes both known discrepant characters but excludes U+001C–U+001F (Python's extra strip controls), U+180E, U+200B and U+2060. The exclusion is intentional, not dependent on interpreter Unicode upgrades. These latter characters remain literal and count toward budgets, including at boundaries.

For every card leaf and greeting: first replace every CRLF pair with exactly one LF and each remaining CR with LF; then remove the longest leading/trailing run consisting only of the enumerated set; preserve everything else including interior members of the set. No normalization of Unicode composition or Unicode line/paragraph separators. Greeting checks apply afterwards: empty permitted, at most 300 code points, no remaining LF. Cards retain required/optional and labeled budgets; count Python code points / JS `Array.from`, not UTF-16 units or graphemes. No global protocol ceiling changes.

Use one NPC-only pure text normalizer in Python shared by leaf and greeting validation and one explicit JS mirror. Preserve each caller's current stable error codes. `NpcVoiceLines` currently consumes the NPC leaf normalizer, so it follows the same rule automatically without additional player template prose rewrites. Do not edit `world/rules/persona.py` or generic player normalization.

### Equality uses complete normalized card plus greeting

Use the canonical normalizers for the NPC editor baseline/draft comparison, dirty-close decision, save eligibility and reconnect reconciliation (`npc-persona-editor-model.js`, `use-npc-persona-editor.js` only if necessary). Compare all identity/card leaves and the greeting; boundary-only differences are clean/no-op, an interior or excluded-character difference is real. On save the server still checks expected version under its current serialized transaction before deciding no-op. A real optional clear changes once, repeating the clear is unchanged; stale expected version rejects even for equal normalized content. Reconnect re-reads committed state before allowing another save and must not manufacture a successful save from client equality; normalize only for comparison, preserve the user's raw local draft after rejection/uncertain transport.

### Shared fixtures describe observable outcomes

Extend existing shared boundary fixture conventions with expected normalized strings, error code/leaf, and rendered totals for valid cards; both languages consume the same cases. Include every enumerated boundary character, all excluded characters above, CRLF/lone CR/interior LF, interior whitespace preservation, optional all-whitespace clear, required all-whitespace rejection, astral near limits and combined labeled bounds. Avoid exact source/constant-copy assertions and tests pinning authored prose. Integration tests cover real version/no-op decisions; browser smoke covers save/reopen/reconnect, not mock echoes.

## Risks / Trade-offs

- [Finite set differs from both prior builtins] → Deliberate narrow correction with explicit fixtures; no silent migration of stored content. Development reset policy applies.
- [Client display changes while typing] → Normalize for validation/equality, not destructive input rewriting; raw drafts survive failures.
- [Optional values diverge] → Include all-whitespace hidden/social/greeting clears and subsequent identical save tests.
- [Budget shifts] → Validate after exact normalization in both runtimes; retain existing labeled rendering order and all bounds.

## Migration Plan

No DB migration, version-format fork, normalization shim or automatic instance repair. Fresh development DB adoption uses §13b reset runbook. Runtime writes follow the updated contract; readers remain read-only and do not rewrite official companion or player preset text.
