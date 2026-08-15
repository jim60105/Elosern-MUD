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
| [Deterministic Available Actions](2026-08-15-ai-action-options-deterministic-actions-design.md) | `context_actions` exploration/dialogue kinds, rule tables, `default_cards()`, vocabulary lock source |
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
| A-1 | **One panel, two producers.** `context_actions` gains exploration/dialogue kinds and a `suggestions` section. The deterministic producer always computes the current valid-action list; the AI producer fills `suggestions` when online. Degradation swaps producers in the same field. | No new OOB message types; the panel allowlist, revision semantics, and client validators stay the sole contract. |
| A-2 | **Hybrid card vocabulary.** Each card is `known_action` (dispatcher allowlist + bounded params) or `freeform` (a phrase that flows through the existing `explore.talk_freeform`/speech pipeline). | Freshness and safety both covered; zero new parsers. |
| A-3 | **Async fire-and-forget on situation change.** Fingerprinted triggers schedule one generation; completed proposals arrive as `ui_update`; stale fingerprints discard. | Follows `scene_flavor_service`; the player never waits on the LLM. |
| A-4 | **One LLM call per fingerprint; replay on repeat; manual dismissal evicts.** The cache is keyed by situation, not recency; a dismiss action clears the display and the cache so re-entry regenerates. | Deterministic cost; explicit player control over "AI 建議". |
| A-5 | **Deterministic degradation in the same field.** `default_cards()` derives 3–5 rule cards from the same affordance builders the AI prompt sees; `degraded` ⊆ kind list always. | Playable with every service offline; the action space never changes between AI and rule mode. |
| A-6 | **Dual placement.** `ready` cards appear as a narrative choice-point *and* in a persistent dock section; one card renderer, one click path. | VN feel in the narrative stream + a stable reference surface. |
| A-7 | **Strict validation ladder with leak gates.** 12 stages incl. CJK, length, placeholder/digit gates, and hidden-value leakage (true traits, affinity numbers, disguised values). Any failure → logged degrade. | Anti-hallucination and anti-leak land as deterministic gates. |
| A-8 | **In-memory LRU + negative memo.** Ready sets cached by fingerprint; transport failures memoized 30 s. | Single-player; reload costs one regeneration; a dead endpoint is not hammered. |
| D-1 (amendment) | **Vocabulary lock.** The LLM may only emit `action_code`s from the deterministic affordance union — an addition to the master design's generative-layer contract (§7): proposals are not merely validated *after* generation; the prompt carries the affordance set, and validation rejects anything outside it. | The suggestion surface can never teach the player an action the rules cannot execute; `degraded` and `ready` stay in the same action space by construction. |
| D-2 | **Transport states never cached.** `generating`/`degraded` live on `context_actions.suggestions`, not in the cached `OptionSet` (`status: "ready"` only). | A cached transport state would poison later presentations (schema doc §1.1). |
| D-3 | **Trigger hooks are three deterministic call sites** (location change, talk-reply success, `ui_sync`) — never inside `world/ai/`. | Single-writer boundary; `world/ai` proposes, the deterministic core owns the moments. |

---

## 3. Module Map

| Module | Role | Writes |
|---|---|---|
| `world/ai/action_options.py` (new) | Frozen schema, validation ladder, context builder, generation, degrade | none (proposals only) |
| `prompts/action_options.yaml` (new) + `world/prompts/registry.py` | Prompt + placeholder allowlist | none |
| `world/ai/profiles.py` | New `action_options` layer slot (`LAYER_NAMES`) + startup validation | none |
| `server/option_proposal_service.py` (new) | Fingerprint, LRU + negative memo, fire-and-forget scheduling, push seam | ephemeral cache + presentation only |
| `web/webclient/presentation/` | `context_actions` v3 validator; exploration/dialogue producers; `default_cards()`; `publish_panel_update` helper | presentation only |
| `web/webclient/actions/options.py` (new) | `options.dismiss` adapter; freeform bridge (reuses `explore.talk_freeform`) | none beyond normal action flow |
| `web/static/webclient/js/` | `protocol.js` v3 mirror + allowlist; dock section; narrative choice-points; card renderer | presentation only |

---

## 4. OpenSpec Slicing — Daily Changes

Redesigned from the two-change slicing in the original plan into **eleven 1-workday changes**, each
landing independently (specs, code, tests, `spec_traceability`, archive) and each small enough to
finish in one day.

| # | Change | Depends on | Content |
|---|---|---|---|
| 1 | `action-options-schema` | — | Frozen `OptionSet`/`SuggestionCard`, bounds, 12-stage ladder, leak gates, JSON-schema contract, pure tests |
| 2 | `action-options-prompts` | 1 | `action_options.yaml` + registry allowlist, `LAYER_NAMES` slot, `LLM_PROFILES` setting, startup validation tests |
| 3 | `action-options-layer` | 1, 2 | `world/ai/action_options.py` generative module: context builder, retry, degrade; FakeLLM suite |
| 4 | `action-options-trigger-service` | 3 | `option_proposal_service.py`: fingerprint, LRU + replay, negative memo, push seam (`publish_panel_update`), eviction API |
| 5 | `action-options-trigger-hooks` | 4 | Three deterministic hook call sites (location change, talk success, `ui_sync`) + tests |
| 6 | `context-actions-exploration` | — | Exploration kind producer + `default_cards()` + registry registration + pure/integration tests |
| 7 | `context-actions-dialogue` | 6 | Dialogue kind producer (scripted keywords, honest-empty LLM rule) + tests |
| 8 | `context-actions-v3` | 6, 7 | Server v3 validator (combat byte-stable), `PANEL_ALLOWLIST` 3, `protocol.js` mirror, parity test |
| 9 | `dismiss-options-action` | 4, 8 | `options.dismiss` action + adapter + cache eviction + `unavailable` publish |
| 10 | `webclient-options-dock` | 8, 9 | Dock section: four status renders, card component, click dispatch, dismiss control; Node/browser tests |
| 11 | `webclient-options-choicepoints` | 8, 10 | Narrative choice-point layer: generating line, ready insertion, in-place replacement, removal; Node/browser tests |

### 4.1 Dependency order

```
 1 ──▶ 2 ──▶ 3 ──▶ 4 ──▶ 5
                          │
 6 ──▶ 7 ──▶ 8 ──▶ 9 ──▶ 10 ──▶ 11
```

(Dialogue producer 7 depends on 6 for the shared affordance-builder extraction; the two trunks
meet only at 9, which needs both the eviction API from 4 and the v3 panel from 8.)

### 4.2 Parallel implementation batches

Recommended batching for parallel agents (repo constraint: evennia test files have one serial
execution owner each; browser files boot shared servers, so keep the options browser tests in
**one** file):

| Batch | Day | Changes | Why parallel-safe |
|---|---|---|---|
| B1 | 1 | 1 + 6 | Pure schema (world/ai) and exploration producer (web/presentation) touch disjoint packages |
| B2 | 2 | 2 + 7 | Prompts/profile (server-adjacent) and dialogue producer (web/presentation) |
| B3 | 3 | 3 (alone) | The generative layer is the deepest single unit; parallel work here would fight over `world/ai/` tests |
| B4 | 4 | 4 + 8 | Trigger service (server/) and v3 protocol mirrors (presentation + protocol.js) |
| B5 | 5 | 5 + 9 | Deterministic hooks (actions/world) and dismiss action (web/actions) |
| B6 | 6 | 10 (alone) | Dock rendering; the choice-point layer depends on it |
| B7 | 7 | 11 (alone) | Narrative choice-points on top of the dock surface |

Two-agent parallelism on days 1, 2, 4, 5; single-agent days 3, 6, 7. Total ≈ 7 working days of
wall clock with two agents, 11 serial days with one.

### 4.3 Verification per change

Every change runs its owned package tests (`world` / `web.webclient` / `server` as touched),
`tests/test_command_docs.py` is unaffected (no player command changes; `options.dismiss` is an OOB
action, not a command), and `uv run --locked python -m tools.spec_traceability check` stays green
with `covers_requirement` annotations on new main requirements after sync.

---

## 5. Out of Scope

- Combat-round proposals (combat already has a full menu; the state-machine interaction is risk
  without clear gain — `context_actions` combat emits `suggestions: unavailable`).
- Proposal persistence across reloads (in-memory cache; degradation covers the gap).
- New OOB message types (`ui_update` panel replacement is the whole contract).
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