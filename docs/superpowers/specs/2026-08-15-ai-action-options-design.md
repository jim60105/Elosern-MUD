# AI Action Option Proposals — Design

**Date:** 2026-08-15
**Status:** Approved
**Scope:** An asynchronous generative "action options" layer — AI-composed suggestion cards for
exploration, NPC, and dialogue contexts — presented in the WebClient through one
`context_actions` panel with two producers, fully degradable to deterministic rules.

This document is a slice of the master design
(`docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`, §7 generative layer). Where this
document conflicts with the master design, the master design wins unless this document explicitly
amends it. The single-writer boundary is untouched: `world/ai/` emits validated proposals only.

---

## 1. Product Context

The MUD feel persists in exploration and dialogue contexts: the player reads narrative text and
types commands, while combat, services, and creation are already menu-driven docks. This change
activates an AI "companion suggestions" surface: after a situation change (room entry, NPC
encounter, dialogue start, narrative switch), an asynchronous generation produces 3–5 option
cards the player can click instead of typing. The LLM is never on the interaction path; when it is
offline, timed out, or its output fails validation, the same panel degrades to a deterministic
list of currently-valid actions produced by rules.

Existing assets the design builds on:

- `context_actions` panel (schema v2), currently produced only by the combat presenter
  (`web/webclient/presentation/combat_panel.py`); the combat dock already renders it.
- The fire-and-forget Deferred scheduling pattern (`server/scene_flavor_service.py`).
- The validated-proposal pipeline (`world/ai/`): JSON-schema-constrained LLM output
  (`world/ai/client.py`), bounded-context serialization, CJK/no-placeholder/no-leak validation
  (`world/ai/narrator.py`, `world/ai/npc_dialogue.py`), `FakeLLMClient` replay tests.
- The OOB panel contract: `ui_update` replaces one named panel at a newer revision
  (`docs/superpowers/specs/2026-08-02-webclient-oob-foundation-design.md` §4).

---

## 2. Design Decisions

| # | Decision | Rationale |
|---|---|---|
| A1 | **One panel, two producers.** `context_actions` gains exploration/dialogue kinds and a `suggestions` section. The deterministic producer always computes the current valid-action list; the AI producer fills `suggestions` when online. Degradation swaps producers in the same field; the player never loses the surface. | No new OOB message types; the panel allowlist, revision semantics, and client validators stay the sole contract. |
| A2 | **Hybrid card vocabulary.** Each card is `known_action` (action code from the existing dispatcher allowlist plus bounded params) or `freeform` (a Traditional Chinese phrase that flows through the existing speech/`say` intent pipeline). | Freshness and safety both covered; the freeform path reuses `npc_dialogue` intent extraction with zero new parsers. |
| A3 | **Async fire-and-forget generation on situation change.** Fingerprinted triggers schedule one generation; the completed proposal is delivered as a `ui_update`; a stale fingerprint (situation moved on) discards it. | Follows `scene_flavor_service`; the player never waits on the LLM. |
| A4 | **One LLM call per fingerprint, replay on repeat.** The cache is keyed by fingerprint, not by recency: any later trigger for the same situation replays the cached response instead of calling again. | Deterministic cost; identical situations don't burn calls. |
| A5 | **Manual dismissal.** A `dismiss_options` UI action hides the current suggestions and evicts that fingerprint from the cache, so re-entering the situation regenerates. | Explicit player control; also the cache-eviction affordance. |
| A6 | **Deterministic degradation source.** The fallback list is produced by read-only rules in the presentation layer (room exits → `move`, present NPCs → `talk`/`approach`/`examine`, node items → `interact`, idle baseline `look`/`inventory`/`rest`/`map`; dialogue kind from relationship level). | Reads registries, never duplicates rule logic; playable with every service offline. |
| A7 | **Strict validation ladder.** Schema, CJK label, length caps, no template placeholder, no hidden-value leakage (true traits, affinity numbers, disguised values) — reusing the narrator/npc_dialogue validators. Any failure → logged degrade. | Anti-hallucination and anti-leak land as deterministic gates, not LLM discretion. |
| A8 | **In-memory LRU cache.** Bounded, per-fingerprint, non-persistent. | Single-player; after a reload the cache is empty and the next trigger regenerates; degradation covers the gap. |

---

## 3. System Design

### 3.1 Proposal schema

Frozen payloads in `world/ai/action_options.py`:

```
OptionSet {
  fingerprint: opaque          # room id + npc ids + dialogue session + narrative fingerprint
  context_kind: "exploration" | "dialogue"
  status: "generating" | "ready" | "degraded" | "unavailable"
  cards: 3–5 × Card
}
Card {
  kind: "known_action" | "freeform"
  label: player-facing Traditional Chinese, ≤ 24 characters
  action_code: only for known_action, from the dispatcher allowlist
  params: only for known_action, bounded allowlisted fields (target_id / exit_ref / keyword_id …)
  hint: optional, ≤ 60 characters
}
```

### 3.2 Generative layer

- New module `world/ai/action_options.py`: prompt construction, JSON-schema-constrained output
  (`response_format` inline schema via `world/ai/client.py`), validation ladder, `OptionSet`
  proposal. Context assembly uses the bounded-context serialization pattern from
  `npc_dialogue`: room summary, present NPCs (name + persona digest), public-level relationship,
  current quest objective, capped recent narrative tail. No hidden values enter the prompt.
- Prompt file `prompts/action_options.yaml` registered in `world/prompts/registry.py` with a
  matching placeholder allowlist.

### 3.3 Trigger service and cache

- New `server/option_proposal_service.py` (mirrors `scene_flavor_service`): fire-and-forget
  Deferred per situation change; obtains the fingerprint; replays the LRU cache on hit; otherwise
  schedules one generation. Completion pushes `ui_update(context_actions, suggestions=ready)`;
  any failure path pushes `suggestions=degraded` with the deterministic list.

### 3.4 Deterministic producers

- `web/webclient/presentation/exploration.py` and the dialogue path gain `context_actions`
  producers for kinds `exploration` and `dialogue`, always computing the current valid-action
  list from registries and room state. Combat behavior is unchanged.

### 3.5 Client

- `context_actions` schema v3 with mirrored validators in `web/static/webclient/js/elosern/protocol.js`
  (unknown-field rejection stays).
- Dual placement: narrative-flow choice-point rendering of `ready` cards inline after narrative
  text; a persistent `suggestions` section wherever `context_actions` is docked (combat dock
  already reads the panel; exploration dock adopts it).
- `generating` shows a transient "AI 正在構思建議…" line that is replaced in place when `ready`
  arrives; `degraded` shows the deterministic list; `unavailable` hides the section.
- Known cards dispatch the existing `ui_action` envelope (request-id/revision semantics reused);
  freeform cards send their text through the existing speech pipeline. A discard control
  ("✕ 清除建議") dispatches the new `dismiss_options` action.

### 3.6 Execution paths

- `known_action` → `ui_action` with the allowlisted code + params; rejection/staleness surface
  through the existing `ui_action_result` handling.
- `freeform` → identical path to player speech (`say` pipeline → `npc_dialogue` intent
  extraction), so the LLM-proposed phrase is treated exactly like a typed sentence.
- `dismiss_options` → new action code in `web/webclient/actions/`; clears the panel
  (`unavailable`) and evicts the fingerprint from the proposal cache.

---

## 4. Integration Points

| Integration | Direction |
|---|---|
| `world/ai/action_options.py` (new) | Generative module: OptionSet schema, prompt, validation, proposal emission |
| `prompts/action_options.yaml` (new) + `world/prompts/registry.py` | Placeholder contract |
| `server/option_proposal_service.py` (new) | Trigger scheduling, fingerprint cache, replay, ui_update push |
| `web/webclient/actions/` | `dismiss_options` code; freeform card bridge to the speech pipeline |
| `web/webclient/presentation/` | `context_actions` v3; exploration/dialogue deterministic producers |
| `web/static/webclient/js/` | protocol.js v3 validators; narrative choice-points; dock section; generating state; discard control |
| `world/ai/profiles.py` | New `action_options` slot in `LAYER_NAMES` with a registered profile (no existing seam; this change claims the slot) |

---

## 5. Error Handling and Degradation

| Situation | Behavior |
|---|---|
| LLM offline / timeout / retry exhausted | `suggestions=degraded` with deterministic list; play unchanged |
| Output fails schema/CJK/length/placeholder/leak validation | Proposal discarded + bounded log → degraded list |
| Proposal completes after the situation moved on | Fingerprint mismatch → discarded, no push |
| Player dismisses | Cache entry evicted; panel `unavailable`; re-entry regenerates |
| Reload before completion | In-memory cache empty; next trigger regenerates; deterministic list shown meanwhile |
| Player is in a fast succession of situation changes | Fingerprint dedup: one generation per situation; no burst |

---

## 6. Testing Strategy

| Area | Method |
|---|---|
| Generative layer | `FakeLLMClient` replays: valid OptionSet, CJK rejection, length rejection, leak rejection, offline degrade; retry flow |
| Cache | One call per fingerprint; replay on repeat trigger; eviction on dismiss; LRU bound |
| Trigger service | Fire-and-forget scheduling; stale fingerprint discard; `ui_update` shape and revision semantics (EvenniaTest) |
| Deterministic producers | Per-context fixtures: room exits, NPC presence, node items, idle baseline, dialogue relationship levels |
| Execution | Known card dispatches `ui_action`; freeform card equals speech pipeline output; `dismiss_options` evicts |
| Browser | Dual placement, generating → ready replacement, degraded list, discard control, rejection toast |
| Offline gate | Full suite green with every AI service offline (FakeLLM conventions) |
| Traceability | Main requirements annotated with `covers_requirement`; `spec_traceability check` passes |

---

## 7. OpenSpec Slicing

Two sequential changes:

| # | Change | Content |
|---|---|---|
| 1 | `ai-action-options-layer` | OptionSet schema, prompt + registry, generative module, validation ladder, trigger service + fingerprint cache, dismiss eviction, FakeLLM tests |
| 2 | `ai-action-options-presentation` | `context_actions` v3, exploration/dialogue deterministic producers, `dismiss_options` action, client validators, narrative choice-points, dock section, browser tests |

---

## 8. Out of Scope

- Combat-round proposals (combat already has a full menu; interactions with the combat state
  machine are risk without clear gain).
- Proposal persistence (in-memory cache is enough for single-player; degradation covers reload).
- New OOB message types (`ui_update` panel replacement is the whole contract).
- Card analytics, per-player personalization, streaming output, reorder/rating UI.
- Any AI write to game state (single-writer boundary holds; `world/ai` emits proposals only).

---

## 9. Open Questions Carried Forward

- Whether proposals should later extend to combat and services contexts, and whether the
  deterministic idle baselines should vary by time of day — both are seams the
  fingerprint/cache and deterministic producer structure would extend without redesign.