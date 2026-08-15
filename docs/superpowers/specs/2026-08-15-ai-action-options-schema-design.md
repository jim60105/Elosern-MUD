# AI Action Options — Card Schema & Validation

**Date:** 2026-08-15
**Status:** Approved
**Scope:** The immutable `OptionSet` / `SuggestionCard` vocabulary exchanged between the generative
layer (`world/ai/action_options.py`), the trigger service (`server/option_proposal_service.py`),
and the presentation layer (`context_actions` panel v3). This document defines the exact fields,
bounds, the validation ladder, the leak gates, and the LLM output contract.

Part of the [AI Action Options document set](2026-08-15-ai-action-options-overview-design.md),
subordinate to `2026-07-29-ai-mud-engine-design.md`. The single-writer boundary is untouched:
this vocabulary is proposal-only; nothing here writes game state.

---

## 1. Vocabulary Design

Two frozen dataclasses live in `world/ai/action_options.py`:

```
OptionSet {
  fingerprint: str              # stable situation identity (see trigger-service doc §3.1)
  context_kind: "exploration" | "dialogue"
  status: "ready"               # never persisted as generating/degraded; those are transport states
  cards: tuple[SuggestionCard, ...]   # len 3..5, order is presentation order
}

SuggestionCard {
  kind: "known_action" | "freeform"
  label: str                    # player-facing Traditional Chinese, 1..24 chars, must contain CJK
  action_code: str | None       # required & allowlisted for known_action; None for freeform
  params: Mapping[str, str]     # bounded, per-action allowlisted keys; empty for freeform
  hint: str | None              # optional, ≤ 60 chars, CJK optional (may include ASCII names)
}
```

Frozen semantics (mirrors `QuestBlueprint` in `world/ai/scenario_director.py`): construction rejects
mutable containers everywhere (`_reject_mutable_containers`), so a proposal is safe to hand across
the `world/ai` boundary and through the coordinator unchanged.

### 1.1 Why `status: "ready"` only

`generating` and `degraded` describe the *transport* of a proposal, not the proposal itself. They
are owned by the trigger service and presentation (`context_actions.suggestions`), which already
knows the difference between "waiting on the LLM", "AI delivered", and "rule fallback". Persisting
transport state in the cached `OptionSet` would let a stale cache entry poison a later presentation
(say, replay a `degraded` set into a live AI session).

---

## 2. Bounds and Constants

Exact caps (single source in `world/ai/action_options.py`; the client mirror in `protocol.js`
repeats them under the dual-direction parity test):

| Constant | Value | Rationale |
|---|---|---|
| `MIN_CARDS` / `MAX_CARDS` | 3 / 5 | Room for curated variety without card-wall; matches the "3–5 個動作" product decision |
| `MAX_LABEL_LENGTH` | 24 chars | One short line on a card; CJK-heavy labels stay readable |
| `MAX_HINT_LENGTH` | 60 chars | Optional fine print only |
| `MAX_PARAMS` | 4 keys | A card carries at most one target + one selector + one qualifier |
| `MAX_CARDS_TOTAL_BYTES` | ≤ `MAX_CANONICAL_JSON_BYTES` | Reuses `web/webclient/presentation/protocol.py`'s canonical JSON bound so any `OptionSet` always fits one `ui_update` payload |
| `MAX_OPTIONSET_CACHE_ENTRIES` | 16 | LRU bound; a long play session cycles far fewer situations |
| `NEGATIVE_MEMO_TTL` | 30 s | A transport-failed fingerprint is not retried within the TTL (see trigger-service doc §3.4) |

---

## 3. Validation Ladder

`validate_optionset(raw: Any) -> OptionSet` — pure, raises one named error per stage; the caller
(the generative layer) maps any error to degrade. Ladder order is fixed:

| # | Stage | Rule | Rejection code |
|---|---|---|---|
| 1 | Structure | Exactly the `OptionSet` keys; `cards` a sequence of dicts | `schema_violation` |
| 2 | Fingerprint | Opaque string 8..64 chars, no whitespace | `schema_violation` |
| 3 | Kind | `context_kind` in the closed enum | `schema_violation` |
| 4 | Card count | 3 ≤ N ≤ 5 | `card_count_out_of_range` |
| 5 | Card kind | `known_action` / `freeform`, exact keys | `schema_violation` |
| 6 | Label | Non-empty, ≤ 24 chars, **contains at least one CJK codepoint** | `empty_label` / `label_too_long` / `non_cjk_label` |
| 7 | Placeholder gate | No `{...}` template placeholder pattern in any label/hint | `placeholder_label` |
| 8 | Digit gate | No ASCII digit in any label (aligns with the narrator's mechanical no-digit gate; a label like "3 連擊" is rejectable content, not rules) | `digit_in_label` |
| 9 | Action code | `known_action` → code present and in `ACTION_CODE_ALLOWLIST`; `freeform` → code/params absent | `unknown_action_code` / `schema_violation` |
| 10 | Params | Keys in the per-action param allowlist; values ≤ 32 chars each | `disallowed_param` / `param_out_of_bounds` |
| 11 | Leak gate | No label/param value matches a hidden-value token (see §4) | `leak_detected` |
| 12 | Normalization | Sort nothing; keep LLM order (it is the curatorial intent) | — |

Stages 6–8 reuse the exact validator imports from `world/ai/narrator.py`
(`_validate_has_cjk`, `_validate_no_template_placeholder`, and the narrator's digit gate); stage 11
reuses the no-leak construction from `world/ai/npc_dialogue.py`—a shared predicate, not a copy.

### 3.1 Action code allowlist

`ACTION_CODE_ALLOWLIST` is derived, not hand-written: the generative layer imports the deterministic
affordance builders (deterministic-actions doc §2) and unions their emitted `action_id`s. A code the
rules never emit is by construction unproposable — the vocabulary lock (overview D-1).

---

## 4. Leak Gates

The anti-leak predicate rejects a card when any label/param/hint token carries information the
player must not see through suggestions:

| Category | Token source | Effect |
|---|---|---|
| True traits | true HP/MP/SP numbers, raw skill values | A suggestion may *reference targeting a wounded enemy*, never encode the number |
| Affinity numbers | numeric affinity values (as counted, not tier labels) | Reuses `npc_dialogue`'s no-affinity-leak validator shape |
| Disguised values | values that differ between `disguised_stats` and true traits | `disguised_stats` is display-only; suggestions must not leak the discrepancy |
| Hidden secrets | anything not present in the bounded public context (§4 of pipeline doc) | If a token never entered the prompt, a card echoing it is fabrication — reject |

Mechanical implementation: the bounded context builder emits a `LEAK_BLOCKLIST` — the set of numeric
literals and hidden trait keys present in the deterministic view — and the validator rejects any
card containing a blocklisted token. The blocklist is part of the context struct, never of the
prompt.

---

## 5. LLM Output Contract

- The generative layer requests `response_format` inline JSON schema (schema_id `action_options`,
  registered in `world/ai/schemas/registry.py` alongside the other layer schemas), matching the
  `OptionSet` shape **without** `status` (transport-owned) and **without** `fingerprint` (supplied
  by the caller; the LLM never sees or emits it).
- `supports_response_format: true` is enforced at profile construction time (startup failure, not a
  runtime surprise).
- Parsing uses the exact-field parser pattern of `web/webclient/presentation/protocol.py`:
  unknown keys on a card are rejected (the closed vocabulary invites the model to invent fields).

---

## 6. Tests

| Area | Method |
|---|---|
| Ladder | One `unittest` per rejection stage with minimal hostile fixtures |
| Bounds | Each cap at boundary and one-past-boundary |
| Leak gates | True-trait number, affinity number, disguised value, fabricated token fixtures |
| Allowlist | A code emitted by no deterministic affordance is rejected |
| JSON contract | Parsed sample payloads; unknown-key rejection; absent `status`/`fingerprint` handling |
| Parity later | Client mirror (webclient doc §5) guarded by the existing dual-direction parity test |

---

## 7. Open Questions Carried Forward

- Whether `hint` should ever carry skill numbers (e.g. "氣勢 20 以內可施展") — currently blocked by the
  digit gate; a deliberate ruling is needed before any hint admits numerals.