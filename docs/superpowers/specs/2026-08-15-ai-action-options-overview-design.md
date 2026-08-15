# AI Action Options — Overview & Implementation Map

**Date:** 2026-08-15
**Status:** Approved (pending final user review of this document set)
**Scope:** `world/ai/action_options.py`, `server/option_proposal_service.py`,
`prompts/action_options.yaml` (+ registry/profile slot), `context_actions` panel v3,
`web/webclient/actions/options.py` (dismiss + freeform bridge), exploration/dialogue deterministic
producers, and the webclient dock + narrative choice-points.

This is the hub document for a six-document set. It states the problem, the cross-cutting
decisions, and the daily OpenSpec slicing with dependency order and parallel batches. The detailed
designs live in:

| Document | Covers |
|---|---|
| [Card Schema & Validation](2026-08-15-ai-action-options-schema-design.md) | The immutable `OptionSet`/`SuggestionCard` vocabulary, exact bounds, the 12-stage validation ladder, leak gates, the LLM JSON contract |
| [Generative Pipeline](2026-08-15-ai-action-options-pipeline-design.md) | Bounded-context serializer, prompt contract, `action_options` profile, retry/degrade ladder |
| [Trigger Service & Cache](2026-08-15-ai-action-options-trigger-service-design.md) | Fingerprint, one-call-per-situation LRU replay, negative memo, coordinator push seam, dismiss eviction |
| [Deterministic Available Actions](2026-08-15-ai-action-options-deterministic-actions-design.md) | The canonical affordance contract, exploration kind rule table, `default_cards()`, vocabulary lock source |
| [WebClient Presentation](2026-08-15-ai-action-options-webclient-design.md) | `context_actions` v3 mirrors, dock + narrative choice-points, generating state, dismiss, execution paths |

This document set is subordinate to `2026-07-29-ai-mud-engine-design.md`, the architectural source
of truth. Where it amends that document, the amendment is stated explicitly (D-1).

---

## 1. Problem Statement

The MUD feel survives in exploration and dialogue: the player reads narrative text and types
commands, while combat, services, and creation are already menu-driven docks
(`web/webclient/actions/`, the OOB protocol). The generative layer (`world/ai/`) is mature —
persona dialogue with intent extraction, scene flavor, quest proposals — but its output is
*prose on demand*; nothing proactively curates what the protagonist could do next, and the player
who does not know the action vocabulary must discover it by trial or documentation.

What is missing is a proactive suggestions surface:

1. **No curatorial layer.** The LLM is asked to *answer* (dialogue, flavor) but never to *suggest*.
   A curated "what now?" card row is the product's AI difference.
2. **No menu path into conversation.** Freeform conversation requires typing; a player who wants a
   point-and-click experience has no sanctioned way to start or steer it.
3. **No deterministic fallback for a curated row.** Combat has a full menu; exploration and
   dialogue have nothing equivalent when the LLM is offline, which the deterministic-playable
   invariant forbids as a design gap.
4. **No situation identity.** Nothing in the engine names "the situation" — so nothing can cache,
   dedupe, or degrade against it.

---

## 2. Cross-cutting Architectural Decisions

| # | Decision | Rationale |
|---|---|---|
| A-1 | **One panel, two producers.** `context_actions` gains an exploration kind and a `suggestions` section. The deterministic producer always computes the current valid-action list; the AI producer fills `suggestions` when online. Degradation swaps producers in the same field. | No new OOB message types; the panel allowlist, revision semantics, and client validators stay the sole contract. |
| A-2 | **Hybrid card vocabulary.** Each card is `known_action` (canonical payload of a current affordance) or `freeform` (a phrase that flows through the existing `explore.talk_freeform`/speech pipeline, bound to a present NPC). | Freshness and safety both covered; zero new parsers. |
| A-3 | **Async fire-and-forget on situation change.** Fingerprinted triggers schedule one generation; completed proposals land in session state and publish via one `ui_update`. | Follows `scene_flavor_service`; the player never waits on the LLM. |
| A-4 | **One LLM call per fingerprint; replay on repeat; manual dismissal evicts.** The cache is keyed by situation, not recency; a dismiss action clears the display and the cache so re-entry regenerates. | Deterministic cost; explicit player control over "AI 建議". |
| A-5 | **Deterministic degradation in the same field.** `default_cards()` derives rule cards from the same affordance builders the AI prompt sees; `degraded` ⊆ kind list always; navigation surfaces excluded. | Playable with every service offline; the action space never changes between AI and rule mode. |
| A-6 | **Dual placement.** `ready` cards appear as a narrative choice-point *and* in a persistent dock section; one card renderer, one click path. Stream shows generating/ready only; degraded/unavailable render in the dock only. | VN feel in the narrative stream + a stable reference surface. |
| A-7 | **Strict validation ladder with leak gates.** 12 stages incl. CJK, length, placeholder/digit gates, and hidden-value leakage (true traits, affinity numbers, disguised values) on labels/hints; params are canonical payload copies. Any failure → logged degrade. | Anti-hallucination and anti-leak land as deterministic gates. |
| A-8 | **In-memory LRU + pending registry + negative memo.** Ready sets cached by fingerprint; in-flight generations deduped; transport failures memoized 30 s. | One call per fingerprint holds even mid-flight; a dead endpoint is not hammered. |
| D-1 (amendment) | **Vocabulary lock.** AI proposals must exactly match a currently-executable affordance — an addition to the master design's generative-layer contract (§7): proposals are not merely validated *after* generation; the prompt carries the affordance set, and the schema ladder stage 9 requires `(action_code, params)` to equal one canonical affordance, replacing model-typed params. | The suggestion surface can never teach the player an action the rules cannot execute right now; `degraded` and `ready` stay in the same action space by construction. |
| D-2 | **Transport states never cached.** `generating`/`degraded` live on `context_actions.suggestions`, not in the cached `OptionSet` (`status: "ready"` only). | A cached transport state would poison later presentations (schema doc §1.1). |
| D-3 | **Trigger hooks are three deterministic call sites** (location change, talk-reply completion publication, `ui_sync`) — never inside `world/ai/`. | Single-writer boundary; `world/ai` proposes, the deterministic core owns the moments. |
| D-4 (review fix) | **Session-scoped options presentation state.** `session.ndb.options_state` (fingerprint, status, generation token, displayed set) is owned by the trigger service and read by every `context_actions` render. | An async `ready` result survives the next snapshot; dismiss state survives re-renders (rubber-duck R3). |
| D-5 (review fix) | **Pending registry + generation token.** `pending[fingerprint]` attaches later triggers to the in-flight Deferred; a dismiss increments the token so a racing completion publishes nothing. | "One LLM call per fingerprint" holds mid-flight; evict-vs-generation is deterministic (rubber-duck R4). |
| D-6 (review fix) | **No `dialogue` kind in v1.** Conversation is steered by the exploration kind's `talk_scripted`/bound `talk_freeform` affordances; there is no persistent dialogue session from which a "current conversation partner" is derivable. | Removes the provenance problem and the degraded-empty-card contradiction (rubber-duck R5). |

---

## 3. Module Map

| Module | Role | Writes |
|---|---|---|
| `world/ai/action_options.py` (new) | Frozen schema, validation ladder, context builder, generation, degrade | none (proposals only) |
| `prompts/action_options.yaml` (new) + `world/prompts/registry.py` | Prompt + placeholder allowlist | none |
| `world/ai/profiles.py` | New `action_options` layer slot (`LAYER_NAMES`) + startup validation | none |
| `server/option_proposal_service.py` (new) | Fingerprint, pending registry, LRU + negative memo, session options state, fire-and-forget scheduling, push seam | ephemeral cache + presentation state only |
| `web/webclient/presentation/affordances.py` (new) | Canonical affordance builders, `default_cards()`, vocabulary source | presentation only |
| `web/webclient/presentation/` | `context_actions` v3 validator + presenter reading `options_state`; `publish_panel_update` helper | presentation only |
| `web/webclient/actions/options.py` (new) | `options.dismiss` adapter; freeform bridge (reuses `explore.talk_freeform`) | none beyond normal action flow |
| `web/static/webclient/js/` | `protocol.js` v3 mirror + allowlist; dock section; narrative choice-points; card renderer | presentation only |

---

## 4. OpenSpec Slicing — Daily Changes

Redesigned after the rubber-duck review into **nine 1-workday changes**, each landing
independently (specs, code, tests, `spec_traceability`, archive) and each small enough to finish
in one day. The dependency graph fixes the review's R7 findings: the shared canonical affordance
contract is a root change (everything vocabulary-shaped depends on it), and the v3 panel seam lands
before the trigger service publishes through it.

| # | Change | Depends on | Content |
|---|---|---|---|
| 1 | `action-options-affordance-contract` | — | Extract `presentation/affordances.py` from exploration builders (panel v1 byte-stable), exploration-kind context_actions producer, `default_cards()`, vocabulary union, read-only + subset tests |
| 2 | `action-options-schema` | 1 | Frozen `OptionSet`/`SuggestionCard` (typed canonical params, freeform `target` binding), enrichment, ladder stages 0–11, leak gates on labels/hints, JSON contract, pure tests |
| 3 | `action-options-prompts` | 1 | `action_options.yaml` + registry allowlist, `LAYER_NAMES` slot, `LLM_PROFILES` setting, startup validation tests |
| 4 | `action-options-layer` | 2, 3 | `world/ai/action_options.py`: context builder, prompt, `{npc_index}` binding resolution, retry/degrade, enrichment; FakeLLM suite |
| 5 | `action-options-trigger-service` | 4 | Fingerprint (public state digest), pending registry + tokens, LRU + negative memo, `session.ndb.options_state`, `publish_panel_update` helper, `evict()` |
| 6 | `action-options-trigger-hooks` | 5 | Three hook call sites (location change; talk completion publication; `ui_sync`) + integration tests |
| 7 | `context-actions-v3` | 1 | Server v3 validator (combat fields preserved, available + unavailable forms), `PANEL_ALLOWLIST` → 3, `protocol.js` mirror, presenter reading `options_state`, parity test |
| 8 | `dismiss-options-action` | 5, 7 | `options.dismiss` action + adapter + `evict()` wiring + `unavailable` publish + tests |
| 9 | `webclient-options-surface` | 5, 7, 8 | Dock section (four status renders) + card component + execution paths + dismiss control; Node/browser tests |
| 10 | `webclient-options-choicepoints` | 7, 9 | Narrative stream movable end-block: generating line, ready replacement, text-after-update ordering; Node/browser tests |

### 4.1 Dependency order

```
        ┌── 2 ──┐
 1 ────│        ├── 4 ── 5 ── 6
        └── 3 ──┘          │
                            └── 8 ── 9 ── 10
 1 ──── 7 ── (9)
```

(9 depends on the panel from 7, the eviction path from 5, and the dismiss action from 8; 10
depends on 7 and 9 for the shared card component.)

### 4.2 Parallel implementation batches

Recommended batching for parallel agents (rubber-duck R8: parallel agents must not share a test
database or the retained Evennia test server — see isolation note below):

| Batch | Day | Changes | Why parallel-safe |
|---|---|---|---|
| B1 | 1 | 1 (alone) | The affordance contract is the shared root everyone else builds against |
| B2 | 2 | 2 + 3 | Pure schema (world/ai) vs prompts/profile (world/prompts + settings) — disjoint packages |
| B3 | 3 | 4 (alone) | The generative layer is the deepest single unit |
| B4 | 4 | 5 + 7 | Trigger service (server/) vs v3 protocol (presentation + protocol.js) |
| B5 | 5 | 6 + 8 | Hook call sites (world/actions) vs dismiss action (web/actions) — both depend on 5 but touch disjoint files |
| B6 | 6 | 9 (alone) | Dock surface; choice-points depend on it |
| B7 | 7 | 10 (alone) | Narrative choice-points on top of the dock surface |

Two-agent parallelism on days 2, 4, 5; single-agent days 1, 3, 6, 7. Total ≈ 7 working days of
wall clock with two agents, 9 serial days with one.

**Isolation note (rubber-duck R8):** parallel agents must each run Evennia tests in their own `git
worktree` (separate `server/db/evennia-test.sqlite3`) or serialize Evennia/browser test execution;
OpenSpec spec-sync and `spec_traceability` runs are serialized after each batch, and B4 is the
single owner of the shared parity contract test.

### 4.3 Verification per change

Every change runs its owned package tests (`world` / `web.webclient` / `server` as touched),
`tests/test_command_docs.py` is unaffected (no player command changes; `options.dismiss` is an OOB
action, not a command), and `uv run --locked python -m tools.spec_traceability check` stays green
with `covers_requirement` annotations on new main requirements after sync.

---

## 5. Out of Scope

- Combat-round proposals (combat already has a full menu; `context_actions` combat emits
  `suggestions: unavailable`).
- A `dialogue` context kind while no persistent conversation session exists (D-6; conversation
  entry is an affordance of the exploration kind).
- Proposal persistence across reloads (in-memory cache + pending registry; degradation covers the
  gap).
- New OOB message types (`ui_update` panel replacement is the whole contract).
- Navigation surfaces as suggestion cards (map/guild/shop stay in the kind list, never in
  `default_cards()` — they have no dispatcher action code).
- Card analytics, per-player personalization, streaming output, reorder/rating UI.
- Freeform *option* interpretation (no second LLM pass; the freeform card is the phrase itself).
- Any AI write to game state (single-writer boundary holds; `world/ai` emits proposals only).

---

## 6. Open Questions Carried Forward

- Whether `hint` may ever carry numerals (schema doc §7) — blocked by the digit gate until ruled.
- Whether degraded choice-points belong in the narrative stream (webclient doc §7) — v1 keeps the
  stream AI-only.
- Whether proximity-guarded `engage` cards should surface for guard NPCs when guard rules land
  (deterministic-actions doc §7).