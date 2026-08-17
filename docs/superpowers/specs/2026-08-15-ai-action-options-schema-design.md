# AI Action Options — Card Schema & Validation

**Date:** 2026-08-15
**Status:** Approved (revised after rubber-duck review)
**Scope:** The immutable `OptionSet` / `SuggestionCard` vocabulary exchanged between the generative
layer (`world/ai/action_options.py`), the trigger service (`server/option_proposal_service.py`),
and the presentation layer (`context_actions` panel v5). This document defines the exact fields,
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
  action_code: str              # real dispatcher action id ("explore.move", "explore.talk_freeform", ...)
  label: str                    # player-facing Traditional Chinese, 1..24 chars, must contain CJK
  params: Mapping[str, str | int]  # see §1.2 “one wire shape” — the dispatcher payload
  hint: str | None              # optional, ≤ 60 chars, CJK optional (may include ASCII names)
}
```

Revision two (rubber-duck R2/R9) plus round-three (R3-1): the card carries **one wire shape** —
`params` is always exactly what the dispatcher needs, with no hidden side structure, and
`action_code` is the real registry action id so the client has everything to dispatch:

- `known_action`: `action_code` is the registry action id; `params` is the canonical payload of one
  current affordance (schema doc §3.1), produced by the affordance's own registered validator
  (deterministic-actions doc §1.1). A card is executable by construction: a `malformed_payload`
  rejection on a validated card is a bug.
- `freeform`: `action_code` is exactly `"explore.talk_freeform"` (injected at enrichment, §5) and
  `params` is exactly `{"npc_id": int}` — the bound target resolved from the model's `{npc_index}`
  during enrichment. **This is the single exception to the validator-normalized rule
  (round-three review R3-1):** `validate_talk_freeform_payload` requires a non-empty `speech`, so
  no validator can produce `{"npc_id"}`; the card's params are *binding-only*, and the full
  validator runs only on the client-composed dispatch payload `{"npc_id": params.npc_id,
  "speech": label}` (webclient doc §3). There is no separate `target` field.

Frozen semantics (mirrors `QuestBlueprint` in `world/ai/scenario_director.py`): construction rejects
mutable containers everywhere (`_reject_mutable_containers`), so a proposal is safe to hand across
the `world/ai` boundary and through the coordinator unchanged.

### 1.1 Why `status: "ready"` only

`generating` and `degraded` describe the *transport* of a proposal, not the proposal itself. They
are owned by the trigger service and presentation (`context_actions.suggestions`), which already
knows the difference between "waiting on the LLM", "AI delivered", and "rule fallback". Persisting
transport state in the cached `OptionSet` would let a stale cache entry poison a later presentation.

### 1.2 Card-count contract by status

Three distinct layers, so an implementer can never read two different bounds (round-three review
R3-1):

| Layer | Bound | Why |
|---|---|---|
| Raw generation ladder (stage 4) | accepts 0–5 | a sub-minimum or empty set degrades instead of failing |
| Generation rule (AI `ready`) | 3–5; a set below the minimum degrades | the curated-variety product decision |
| Emitted v5 payload | `ready` 3–5; `degraded` 1–5 in v1 | the idle baseline (deterministic-actions doc §2) is always eligible while a puppeted player is inside a location, so a v1 degraded set is never empty; the mirror still accepts 0–5 so a future room without a baseline cannot crash it |

The 3–5 minimum is a *generation* rule, not a validation rule (rubber-duck R14); the mirrors
accept `ready` 3–5 and `degraded` 0–5 (webclient doc §1.1).

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

`validate_optionset(raw: Any, *, fingerprint: str, affordances: tuple[Affordance, ...],
leak_blocklist: frozenset[str] = frozenset()) -> OptionSet` — pure; raises one named error per
stage; the caller (the generative layer) maps any error to degrade. Ladder order is fixed:

| # | Stage | Rule | Rejection code |
|---|---|---|---|
| 0 | Enrichment | The caller injects `fingerprint` and `status: "ready"` into the raw LLM dict; the ladder validates the enriched payload | (no rejection; violation → `schema_violation`) |
| 1 | Structure | Exactly the `OptionSet` keys; `cards` a sequence of dicts | `schema_violation` |
| 2 | Fingerprint | Opaque string 8..64 chars, no whitespace | `schema_violation` |
| 3 | Kind | `context_kind == "exploration"` (v1 closed enum) | `schema_violation` |
| 4 | Card count | 0 ≤ N ≤ 5 (the 3–5 minimum is a generation rule, §1.2) | `card_count_out_of_range` |
| 5 | Card kind | `known_action` / `freeform`, exact keys (`kind`, `action_code`, `label`, `params`, optional `hint`) | `schema_violation` |
| 6 | Label | Non-empty, ≤ 24 chars, **contains at least one CJK codepoint** | `empty_label` / `label_too_long` / `non_cjk_label` |
| 7 | Placeholder gate | No `{...}` template placeholder pattern in any label/hint | `placeholder_label` |
| 8 | Digit gate | No ASCII digit in any label (aligns with the narrator's mechanical no-digit gate) | `digit_in_label` |
| 9 | Canonical match | `known_action`: the model's `params` are **curation hints, never equality-checked**; stage 9 resolves `action_code` to the unique current affordance entry and **unconditionally replaces the card's params with that affordance's canonical payload** — after this stage the card always satisfies `(action_code, params) == (affordance.action_id, affordance.params)`, which is what the wire-shape guarantee means (round-three review, refined in the `action-options-schema` change); `freeform`: `action_code == "explore.talk_freeform"` and `params == {"npc_id": <int>}` where that `npc_id` equals a freeform affordance's bound target | `unknown_action_code` / `no_such_affordance` / `unknown_target` |
| 10 | Hint gate | Hint ≤ 60 chars; placeholder gate (stage 7) applies; numeric gate (§4) applies to labels and hints only — never to `params` | `hint_too_long` / `placeholder_label` / `leak_detected` |
| 11 | Normalization | Sort nothing; keep LLM order (it is the curatorial intent) | — |

Stages 6–8 amendment (landed with the `action-options-schema` change): the CJK check reuses the
exact `world/ai/narrator.py` `_validate_has_cjk` import, but the placeholder and digit gates are
implemented **locally in the action_options module** — narrator's `_TEMPLATE_PLACEHOLDER_RE` is
token-specific (`{actor}|{target}|{data[...]}`) and narrator has no digit gate. The card gates
are: a generic `{...}` placeholder pattern (`re.compile(r"\{[^{}]+\}")`) for stage 7 and a
mechanical ASCII-digit check for stage 8, both pure and tested in this module.

### 3.1 The affordances argument

`affordances` is the canonical current-valid-action list produced by the deterministic builders
(deterministic-actions doc §1) — each entry already carries real dispatcher `action_id`, exact
params, and a player-facing label, at this moment, for this room. The ladder's stage 9 turns
"vocabulary lock" (overview D-1) into an exact contract: **a validated card's payload is a copy of
one currently executable affordance**, so the player can never see a card the rules cannot execute
right now (rubber-duck R2). The LLM prompt carries the same list (pipeline doc §3); the model
selects and curates, the ladder verifies.

The wire-shape guarantee (rubber-duck R13, refined round three): each `known_action` affordance
entry's `params` is produced *by the action's own registered validator* (`validate_move_payload`
etc.), so a card shipped to the client is byte-for-byte the payload the dispatcher accepts — no
mediation layer, no shape drift between "affordance shape" and "adapter shape". Stage 9 achieves
this by **replacing** model-typed params with the canonical copy (model params are curation hints,
never equality-checked), so the guarantee holds on the validated result, not on the model's
input. The **single exception is the `freeform` card**, whose `{npc_id}` binding shape is not
producible by any validator (talk_freeform requires `speech`); its dispatcher payload is completed
client-side by appending `speech: label` (§1, webclient doc §3) before the full validator runs.

---

## 4. Leak Gates

The anti-leak predicate applies to **model-visible text only**: `label` and `hint`. `params` is
never leak-checked against numeric blocklists — after stage 9 it is a canonical payload copy from
trusted builders (or the freeform binding exception), and a numeric blocklist would only misfire
on legitimate opaque IDs (rubber-duck R5).

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
  and `status` (caller-side). `known_action` cards emit `{"action_code", "label", "params"?,
  "hint"?}` — `params` is optional and is at most a curation hint: stage 9 never validates it for
  equality and always replaces it with the canonical copy; unknown `action_code` values reject at
  stage 9. `freeform` cards emit
  `{"npc_index": <int>, "label", "hint"?}` — enrichment resolves `npc_index` to
  `{"action_code": "explore.talk_freeform", "params": {"npc_id": int}}` against the prompt's bound
  NPC list before validation (stage 0).
- `supports_response_format: true` is enforced at profile construction time.
- Parsing uses the exact-field parser pattern of `web/webclient/presentation/protocol.py`: unknown
  keys on a card are rejected.

---

## 6. Tests

| Area | Method |
|---|---|
| Ladder | One `unittest` per rejection stage with minimal hostile fixtures |
| Stage 9 | A valid-for-now card passes; a globally-allowed but not-current affordance fails; model-typed params are replaced by the canonical copy; `action_code` mismatch rejects |
| Bounds | Each cap at boundary and one-past-boundary; per-status counts: ladder 0–5, ready 3–5 generated, degraded ≥ 1 by the baseline (v1) |
| Leak gates | True-trait number, affinity number, disguised value, fabricated token in labels/hints; params exempt by construction |
| Freeform binding | `{npc_index}` resolution, single/multiple LLM NPC fixtures, unknown index rejection; `action_code` injection to `explore.talk_freeform`; the binding-only params exception is asserted (no `{"npc_id"}` is ever fed to `validate_talk_freeform_payload` unchanged) |
| JSON contract | Parsed sample payloads; unknown-key rejection; absent caller-side fields handled at enrichment |
| Parity later | Client mirror (webclient doc §5) guarded by the dual-direction parity test |

---

## 7. Open Questions Carried Forward

- Whether `hint` should ever carry skill numbers — currently blocked by the digit gate; a deliberate
  ruling is needed before any hint admits numerals.