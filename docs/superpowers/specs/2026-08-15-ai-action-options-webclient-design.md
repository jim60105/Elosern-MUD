# AI Action Options — WebClient Presentation

**Date:** 2026-08-15
**Status:** Approved
**Scope:** `context_actions` panel schema v5 (server validator + `protocol.js` mirror), the
`dismiss_options` (uid `options.dismiss`) action, dock rendering with the generating state, and
narrative-flow choice-points — the dual placement the player sees.

Part of the [AI Action Options document set](2026-08-15-ai-action-options-overview-design.md).
Server payload producers are specified in
[deterministic-actions](2026-08-15-ai-action-options-deterministic-actions-design.md); the trigger
push in [trigger-service](2026-08-15-ai-action-options-trigger-service-design.md).

---

## 1. `context_actions` Schema v5

v5 keeps the v4 combat fields and semantics (schema version bumps to 5, and a `suggestions`
envelope is added to every **available** form — the common unavailable form keeps its exact
field set `schema_version`/`available`/`reason` and never carries `suggestions`, per the
overview's D-1 amendment):

```
context_actions v5 {
  schema_version: 5
  available: bool
  kind: "combat" | "exploration"
  ... (kind-specific sections: combat keeps session/participants/root_actions/
       secondary_actions/skills; exploration carries its affordance list)
  suggestions: {
    status: "generating" | "ready" | "degraded" | "unavailable"
    cards: [ { kind, label, action_code, params, hint } ]   # present iff status ready|degraded
  }
}
```

- `generating`: transient; the client shows the "AI 正在構思建議…" line. Sent only as replacement
  *for a previously non-generating state* (the trigger service publishes it once per trigger).
- `ready`: AI-produced cards (OptionSet). `degraded`: rule cards (`default_cards()`).
  `unavailable`: hidden section (initial state, after dismiss, and when no kind applies).
- The combat presenter emits `suggestions` with `status: "unavailable"` for combat sessions — v1
  explicitly excludes combat-round proposals ([overview] §out-of-scope).
- Revision (rubber-duck R3): "byte-identical" is dropped — schema version bumps to 5 and adds
  `suggestions` to every *available* form, so the claim is **combat fields and semantics
  preserved**: the combat-specific sections keep their v4 shapes and validation, and the change
  that lands v5 must cover the combat available *and* unavailable forms, the combat dock, and
  the combat browser fixtures in one unit.

### 1.1 Server validator

`validate_context_actions` in `web/webclient/presentation/combat_panel.py` (or a shared
`context_actions_schema.py` module extracted from it) enforces v5 exactly: `suggestions` present in
every available v5 payload, `cards` validated by the optionschema ladder (schema doc §3) with the
**status-dependent count bounds: `ready` 3–5, `degraded` 0–5 accepted** (schema doc §1.2's
three-layer contract: the raw ladder accepts 0–5 and the generation rule enforces ready 3–5; v1
degraded sets always carry ≥ 1 card because the idle baseline is always eligible — the mirror
still accepts 0 so a future baseline-less room cannot break the client), and the kind-specific
sections left to their existing validators. Unknown keys reject — the closed schema contract from
the OOB foundation. The common unavailable form is built by the registry and carries exactly
`schema_version`/`available`/`reason` — both validators reject a `suggestions` field on it.

### 1.2 Client mirror + allowlist

`web/static/webclient/js/elosern/protocol.js`:

- `PANEL_ALLOWLIST.context_actions` → `5`.
- A `validateSuggestions` mirror with identical bounds (including the optionschema caps) and
  the existing dual-direction parity test extended to v5 — the convention that already guards the
  exploration panel v1.
- `ui_update` processing (`commitPresentation`) is unchanged: the whole panel replaces at the new
  revision; the narrative choice-point layer additionally reacts to `context_actions` changes
  (§4).

### 1.3 Presenter reads the options snapshot

All `context_actions` renders — `ui_sync`, full snapshots, action refreshes — assemble the
`suggestions` section from **`context.options_state`, an immutable `OptionsSnapshot` on
`PresentationContext`** (built by the coordinator/ingress from `session.ndb.options_state`;
presenters never receive the raw session — round-three review). Generation-side metadata is never
read. An async `ready` result therefore survives the next snapshot, dismiss state survives
re-renders, and a stale in-flight completion cannot clobber the display (rubber-duck R3). The
deterministic affordance list itself is always computed fresh from room state; only the
`suggestions` envelope is state-backed.

---

## 2. Dock Rendering

The exploration dock adopts the same `state.panels["context_actions"]` read the combat dock
already uses (the `webclient-app/stores/elosern.js` store + `ActionDock.vue` pattern, the legacy
`js/plugins/combat_dock.js` now deleted) and renders a
suggestions section:

| `suggestions.status` | Rendering |
|---|---|
| `generating` | One muted line: "AI 正在構思建議…" (no skeleton cards). A generating → generating transition renders nothing new — the line, if present, stands until `ready` replaces it (trigger-service doc §3.4) |
| `ready` | 3–5 labelled card buttons (label + optional hint), each with its `action_code`; a dismiss control ("✕ 清除建議") at the section corner |
| `degraded` | 0–5 rule cards + one muted "AI 建議目前不可用" note; **0 cards render an empty-state line "現在沒有什麼值得做的動作"** (the section body, not the section frame); same dismiss control. In v1 exploration the empty state is unreachable — the idle baseline always yields ≥ 1 card (deterministic-actions doc §2) — and stays a safe fallback render for future baseline-less kinds |
| `unavailable` | Section hidden entirely |

Cards render from validated data only — the dock never builds an action from unmirrored fields.

---

## 3. Card Execution

| Card kind | Dispatch | Rejection surface |
|---|---|---|
| `known_action` | `ui_action` with the card's `action_code` + `params` through the existing action client (`elosern_actions.js`), normal request-id/revision semantics; params are the validator-normalized payload by contract (§1.1 of the deterministic-actions doc) | Existing `ui_action_result` toast (rejection / stale / busy), unchanged |
| `freeform` | `ui_action` `explore.talk_freeform` with `payload = {npc_id: params.npc_id, speech: label}` — the speech is **always the label text** (schema doc §1 wire shape) | Same toast surface; schedule-blocked guard re-checks at the adapter |

The freeform bridge is the whole point of the hybrid vocabulary: clicking an AI-suggested line is
indistinguishable, server-side, from typing it.

---

## 4. Narrative Choice-Points

Dual placement (overview A-6): beside the dock section, `ready` cards also appear as a choice-point
inserted into the narrative stream.

- The narrative stream appends through the single-owner facade
  `window.Elosern.narrativeInput`, now owned by the C2 bridge
  (`webclient-app/bridge.js`; the legacy `js/plugins/goldenlayout.js` is deleted). The
  choice-point layer hooks presentation commits: when `suggestions.status` flips to `generating`,
  it appends the muted "AI 正在構思建議…" line at the stream end; a later `ready` commit replaces
  it in place with the card group; `unavailable`/dismiss removes it.
- Single stream behavior (rubber-duck R5 fix — §7's dock-only note is revoked): **the narrative
  stream shows `generating` and `ready` only; `degraded` and `unavailable` render exclusively in
  the dock section.** The rule list is a reference surface; the stream is the AI conversation.
- Movable end-block (rubber-duck R6): the choice-point is a stream-end block owned by the
  `narrativeInput` facade — narrative text appended *after* the choice-point was inserted moves
  the block to the new end instead of floating above newer text. A "text after update" ordering
  test covers the async race (look output, talk replies, scene-flavor pushes).
- Replacement is in place: a `ready` commit replaces the `generating` line instead of stacking.
- Choice-point cards are the same DOM component as the dock cards (one card renderer), so size,
  labels, and click paths cannot diverge.

---

## 5. Dismiss (`options.dismiss`)

- New action code `options.dismiss` in `web/webclient/actions/` (payload `{}`): the adapter calls
  `evict(session, actor)` with the session the dispatcher injects (trigger-service doc §4), which
  invalidates that session's in-flight generation and clears the global cache/memo for the
  displayed fingerprint. `evict` is state-only and never sends (dismiss-options-action D1); the
  completion publication — the adapter declares `affected_panels=("context_actions",)` — renders
  `suggestions.status="unavailable"` from the mutated state, and the section disappears in both
  dock and narrative stream. A failed eviction (the service reports `False`, never raising)
  rejects with the stable `dismiss_failed` code instead of claiming success.
- **Unified adapter ABI (round-three review):** `ActionSpec.adapter` becomes
  `adapter(actor, payload, session=None)` for *every* registered adapter — the same change that
  introduces `options.dismiss` updates all production adapters and the `ActionSpec` type, and
  `_invoke_adapter` passes the session positionally. No runtime signature introspection; existing
  direct two-argument adapter tests keep working through the default.
- The action is registered in `build_production_action_registry()` with
  `affected_panels=("context_actions",)` — no full-snapshot fallback needed.
- The same dismiss control belongs to both the dock section and the narrative choice-point group.

---

## 6. Tests

| Area | Method |
|---|---|
| Mirrors | Dual-direction parity test extended to v5 (server validator ↔ `protocol.js`), covering combat available + unavailable forms |
| Dock rendering | Node tests: four status renders; section hidden on `unavailable`; card click dispatches the right envelope |
| Choice-points | Node tests: generating-line append → ready in-place replacement; dismiss removal; **narrative text appended after a ready commit moves the block to stream end** |
| Null paths | Combat fields preserved (v4 shapes, v5 envelope); unknown suggestions status rejected by both mirrors; `ui_sync` after `ready` preserves cards (state-backed render) |
| Browser | Playwright: move into a room → generating line → ready cards; click a known card executes; freeform card sends speech; dismiss hides both surfaces; LLM-off path shows degraded cards in the dock only |

Browser notes per the repo conventions: put the options browser tests in a file that boots one
shared server (no combat sessions, so the shared-server reuse rule holds).

## 7. Open Questions Carried Forward

- Whether the choice-point should later appear for `degraded` rule cards — v1 keeps the narrative
  stream AI-only by declared behavior (§4); the DOM component reuse makes flipping this a one-line
  later change.