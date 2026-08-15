# AI Action Options — Card Schema & Validation

**Date:** 2026-08-15
**Status:** Approved (revised after rubber-duck review)
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
  fingerprint: str              # stable situation identity (trigger-service doc §3.1)
  context_kind: "exploration"   # single kind in v1; dialogue kind deferred (overview D-6)
  status: "ready"               # never persisted as generating/degraded; those are transport states
  cards: tuple[SuggestionCard, ...]   # len 3..5 (layer-enforced), order is presentation order
}

SuggestionCard {
  kind: "known_action" | "freeform"
  label: str                    # player-facing Traditional Chinese, 1..24 chars, must contain CJK
  params: Mapping[str, str | int]  # see §1.2 “one wire shape” — always the dispatcher payload
  hint: str | None              # optional, ≤ 60 chars, CJK optional (may include ASCII names)
}
```

Revision two (rubber-duck R2/rubber-duck R9): the card carries **one wire shape** — `params` is
always exactly what the dispatcher needs, with no hidden side structure:

- `known_action`: `params` is the canonical payload of one current affordance (schema doc §3.1),
  produced by the affordance's own registered validator (deterministic-actions doc §1.1). A card
  is executable by construction: a `malformed_payload` rejection on a validated card is a bug.
- `freeform`: `params` is exactly `{"npc_id": int}` — the bound target resolved from the model's
  `{npc_index}` during enrichment. The client dispatches `explore.talk_freeform` with
  `payload = {"npc_id": params.npc_id, "speech": label}`: `speech` is *always the label text*, by
  contract. There is no separate `target` field.

Frozen semantics (mirrors `QuestBlueprint` in `world/ai/scenario_director.py`): construction rejects
mutable containers everywhere (`_reject_mutable_containers`), so a proposal is safe to hand across
the `world/ai` boundary and through the coordinator unchanged.

### 1.1 Why `status: "ready"` only

`generating` and `degraded` describe the *transport* of a proposal, not the proposal itself. They
are owned by the trigger service and presentation (`context_actions.suggestions`), which already
knows the difference between "waiting on the LLM", "AI delivered", and "rule fallback". Persisting
transport state in the cached `OptionSet` would let a stale cache entry poison a later presentation.

### 1.2 Card-count contract by status

`ready` cards: 3–5 (layer-enforced at generation: a set failing the minimum degrades). `degraded`
cards: 0–5 (deterministic-actions doc §3 — a room with truly nothing actionable yields 0). The
validation ladder accepts 0–5 in both mirrors; the 3–5 minimum is a *generation* rule, not a
validation rule (rubber-duck R14).

---

## 2. Bounds and Constants

Exact caps (single source in `world/ai/action_options.py`; the client mirror in `protocol.js`
repeats them under the dual-direction parity test):

| Constant | Value | Rationale |
|---|---|---|
| `MIN_CARDS` / `MAX_CARDS` | 3 / 5 | Curated variety without card-wall; matches the "3–5 個動作" product decision |
| `MAX_LABEL_LENGTH` | 24 chars | One short line on a card; CJK-heavy labels stay readable |
| `MAX_HINT_LENGTH` | 60 chars | Optional fine print only |
| `MAX_PARAMS` | 4 keys | A card carries at most one target + one selector + one qualifier |
| `MAX_OPTIONSET_CACHE_ENTRIES` | 16 | LRU bound (trigger-service doc §3.2) |
| `NEGATIVE_MEMO_TTL` | 30 s | Transport-failed fingerprints are not retried within the TTL (trigger-service doc §3.4) |

`params` values: ints within `MAX_SAFE_INTEGER` (the presentation protocol bound) or strings
≤ 32 chars — the same shape the per-action validators accept. The set of legal keys is per-action,
inherited from the canonical affordance payload (§3 stage 9); there is no free-form key allowlist.

---

## 3. Validation Ladder

`validate_optionset(raw: Any, *, fingerprint: str, affordances: tuple[Affordance, ...]) -> OptionSet`
— pure; raises one named error per stage; the caller (the generative layer) maps any error to
degrade. Ladder order is fixed:

| # | Stage | Rule | Rejection code |
|---|---|---|---|
| 0 | Enrichment | The caller injects `fingerprint` and `status: "ready"` into the raw LLM dict; the ladder validates the enriched payload | (no rejection; violation → `schema_violation`) |
| 1 | Structure | Exactly the `OptionSet` keys; `cards` a sequence of dicts | `schema_violation` |
| 2 | Fingerprint | Opaque string 8..64 chars, no whitespace | `schema_violation` |
| 3 | Kind | `context_kind == "exploration"` (v1 closed enum) | `schema_violation` |
| 4 | Card count | 0 ≤ N ≤ 5 (the 3–5 minimum is a generation rule, §1.2) | `card_count_out_of_range` |
| 5 | Card kind | `known_action` / `freeform`, exact keys (`kind`, `label`, `params`, optional `hint`) | `schema_violation` |
| 6 | Label | Non-empty, ≤ 24 chars, **contains at least one CJK codepoint** | `empty_label` / `label_too_long` / `non_cjk_label` |
| 7 | Placeholder gate | No `{...}` template placeholder pattern in any label/hint | `placeholder_label` |
| 8 | Digit gate | No ASCII digit in any label (aligns with the narrator's mechanical no-digit gate) | `digit_in_label` |
| 9 | Canonical match | `known_action`: `(action_code, params)` must **exactly match one entry of `affordances`**; the canonical payload replaces whatever the model typed; `freeform`: `params == {"npc_id": <int>}` and that `npc_id` equals a freeform affordance's bound target | `unknown_action_code` / `no_such_affordance` / `unknown_target` |
| 10 | Hint gate | Hint ≤ 60 chars; placeholder gate (stage 7) applies; numeric gate (§4) applies to labels and hints only — never to `params` | `hint_too_long` / `placeholder_label` / `leak_detected` |
| 11 | Normalization | Sort nothing; keep LLM order (it is the curatorial intent) | — |

Stages 6–8 reuse the exact validator imports from `world/ai/narrator.py` (`_validate_has_cjk`,
`_validate_no_template_placeholder`, and the narrator's digit gate).

### 3.1 The affordances argument

`affordances` is the canonical current-valid-action list produced by the deterministic builders
(deterministic-actions doc §1) — each entry already carries real dispatcher `action_id`, exact
params, and a player-facing label, at this moment, for this room. The ladder's stage 9 turns
"vocabulary lock" (overview D-1) into an exact contract: **a validated card's payload is a copy of
one currently executable affordance**, so the player can never see a card the rules cannot execute
right now (rubber-duck R2). The LLM prompt carries the same list (pipeline doc §3); the model
selects and curates, the ladder verifies.

The wire-shape guarantee (rubber-duck R13): each affordance entry's `params` is produced *by the
action's own registered validator* (`validate_move_payload` etc.), so a card shipped to the client
is byte-for-byte the payload the dispatcher accepts — no mediation layer, no shape drift between
"affordance shape" and "adapter shape".

---

## 4. Leak Gates

The anti-leak predicate applies to **model-visible text only**: `label` and `hint`. `params` and
`target` are never leak-checked against numeric blocklists — after stage 9 they are canonical
payload copies from trusted builders, and a numeric blocklist would only misfire on legitimate
opaque IDs (rubber-duck R5).

| Category | Token source | Effect |
|---|---|---|
| True traits | true HP/MP/SP numbers, raw skill values | A suggestion may *reference targeting a wounded enemy*, never encode the number |
| Affinity numbers | numeric affinity values (as counted, not tier labels) | Reuses `npc_dialogue`'s no-affinity-leak validator shape |
| Disguised values | values that differ between `disguised_stats` and true traits | Suggestions must not leak the discrepancy |
| Hidden secrets | anything not present in the bounded public context (pipeline doc §2) | A token that never entered the prompt is fabrication — reject |

Mechanical implementation: the bounded context builder emits a `LEAK_BLOCKLIST` (numeric literals
and hidden trait keys of the deterministic view); the validator applies it to labels/hints only.

---

## 5. LLM Output Contract

- The generative layer requests `response_format` inline JSON schema (schema_id `action_options`,
  registered in `world/ai/schemas/registry.py`), matching the card dicts **without** `fingerprint`
  and `status` (caller-side); freeform cards emit `{"npc_index": <int>}` which enrichment resolves
  to `params: {"npc_id": int}` against the prompt's bound NPC list before validation.
- `supports_response_format: true` is enforced at profile construction time.
- Parsing uses the exact-field parser pattern of `web/webclient/presentation/protocol.py`: unknown
  keys on a card are rejected.

---

## 6. Tests

| Area | Method |
|---|---|
| Ladder | One `unittest` per rejection stage with minimal hostile fixtures |
| Stage 9 | A valid-for-now card passes; a globally-allowed but not-current affordance fails; model-typed params are replaced by the canonical copy |
| Bounds | Each cap at boundary and one-past-boundary |
| Leak gates | True-trait number, affinity number, disguised value, fabricated token in labels/hints; params exempt by construction |
| Freeform binding | `{npc_index}` resolution, single/multiple LLM NPC fixtures, unknown index rejection |
| JSON contract | Parsed sample payloads; unknown-key rejection; absent caller-side fields handled at enrichment |
| Parity later | Client mirror (webclient doc §5) guarded by the dual-direction parity test |

---

## 7. Open Questions Carried Forward

- Whether `hint` should ever carry skill numbers — currently blocked by the digit gate; a deliberate
  ruling is needed before any hint admits numerals.