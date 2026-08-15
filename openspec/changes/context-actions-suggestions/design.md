## Context

`context_actions` is combat-only at schema version 3 today (`combat_panel.py`,
`CONTEXT_ACTIONS_SCHEMA_VERSION = 3`, `PANEL_ALLOWLIST.context_actions = 3`). The AI action-options
slicing (overview `docs/superpowers/specs/2026-08-15-ai-action-options-overview-design.md`,
subordinate to `2026-07-29-ai-mud-engine-design.md`) is the parent plan; the root change
[`action-options-affordance-contract`](../action-options-affordance-contract/proposal.md) lands
`context_actions` **v4**: combat form byte-identical, new exploration form carrying the canonical
`AffordanceView` vocabulary, shared unavailable form with `schema_version` = panel version, and
`ACTION_CODE_ALLOWLIST`/`default_cards()` in one new module
`web/webclient/presentation/affordances.py`. That change's design explicitly records that the
suggestions slice "bumps once more" to **v5** and that the older "context-actions-v3" roadmap
wording is superseded by this v4-v5 sequence — this change implements that v5.

The behavior contract for the `suggestions` envelope is specified in the webclient design doc of
the set (`2026-08-15-ai-action-options-webclient-design.md` §1, §1.1, §1.3, §6) and the overview
decisions A-1 through A-8, D-2, D-8: transport states never cached, cards appear on the dock, the
exploration presenter reads session-scoped options state through an immutable snapshot, and
combat always reports `unavailable`.

Ground truth in the repo:

- `combat_panel.py::validate_context_actions` enforces one closed available form (exact keys,
  kind `combat`, version pin, nested bounds); the common unavailable form is emitted by the
  presentation registry (`PresenterSpec` `schema_version`), not by this validator.
- `protocol.js`: `PANEL_ALLOWLIST.context_actions: 3` (line ~208), `validateContextActionsPanel`
  (v3) used by `validateCommonMetadata` against the registered panel version; `MAX_DEPTH = 12`
  matches `web/webclient/presentation/protocol.py` (deepest legitimate leaf = combat skills at
  depth 11).
- Parity convention: `tests/test_exploration_parity_contract.py` pattern (Python constants vs JS
  constants + shared fragments) — the repo-wide contract tests own panel-bound parity.
- Presenter isolation invariant (`openspec/specs/webclient-oob-protocol`): presenters receive
  only session-derived read context; they never touch the raw session. `PresentationContext` is
  a frozen dataclass (`context.py`) with `actor`, `protocol_version`, `session_tag`.

## Goals / Non-Goals

**Goals:**

- `context_actions` v5: `suggestions` on both available forms; per-status closed schema with
  bounded cards; combat always `status: "unavailable"`.
- Exploration suggestions render **state-backed**: read only `context.options_state` snapshot +
  `default_cards()`; absent snapshot → `"unavailable"` (inert until the trigger service lands).
- Read-side presentation contract (`PresentationContext.options_state` /
  `OptionsSnapshot`) shipped here; the write side (`session.ndb.options_state` population,
  pending registry, cache, push) stays in the trigger-service change.
- Strict mirrors and fixtures in one unit: server validator ↔ `protocol.js` v5, allowlist → 5,
  one v4-vs-v5 combat-field comparison fixture, a new parity contract test, and all existing
  v4 fixtures updated in the same commit.

**Non-Goals:**

- No trigger service, fingerprint, cache, pending registry, or `session.ndb.options_state`
  population (later change; its presenter input contract is fixed here).
- No dock/card rendering, no dismiss action, no narrative choice-points (webclient surface
  changes).
- No combat proposals: combat `suggestions` stays `"unavailable"` (overview §5 out of scope).
- No deep generation ladder on the wire: leak gates, enrichment, canonical replacement remain in
  `world/ai` (generative slices); the presentation validator is a strict *shape* gate.
- No changes to adapters, commands, typeclasses, or `world/ai`; nothing here writes game state.

## Decisions

### D-1 The `suggestions` envelope is a per-status closed schema

```
suggestions: {
  status: "generating" | "ready" | "degraded" | "unavailable",   # required
  cards: [ ...card... ],   # required iff status ready|degraded; forbidden otherwise
}
card: {
  kind: "known_action" | "freeform",   # required
  action_code: str,                    # required; ∈ ACTION_CODE_ALLOWLIST;
                                       #   freeform ≡ "explore.talk_freeform"
  label: str,                          # 1..24 code points, must contain CJK
  params: {...},                       # 0 < keys ≤ 4, string/int values (int ≤ MAX_SAFE_INTEGER)
  hint: str | None,                    # optional; ≤ 60 code points
}
```

Status decides the exact key set: `generating`/`unavailable` carry only `status`; `ready`/
`degraded` carry both. Counts: `ready` 3–5; `degraded` 0–5 (mirror accepts the same; v1
non-emptiness of degraded sets is a guarantee of `default_cards()`, not a validator rule —
schema-doc §1.2 three-layer contract). Rationale: a closed per-status schema means the client can
never render cards it has no right to (generating/unavailable), and server and mirror agree on
exactly one shape per state. Alternative considered: an always-present `cards` array — rejected
because an empty `cards: []` for `generating` invites parsers to treat it as a degraded truth.

**The common unavailable form carries no `suggestions` (D-1 amendment to the webclient design
doc's "one field added to every form").** The unavailable form is a single shared builder for
every panel (oob-protocol's "Every panel payload has an exact availability discriminator"), so a
panel-specific field there would break every other panel's contract; the field set stays exactly
`schema_version`, `available`, `reason` (version 5 value only). The design doc's "every form"
wording is superseded by this decision; a synchronous test pins that the shared unavailable
builder is unchanged and that a v5 unavailable payload carrying `suggestions` is rejected by both
validators.

### D-2 The presentation validator is a shape gate; the deep ladder stays in `world/ai`

The server validator checks envelope kinds, action codes against `ACTION_CODE_ALLOWLIST`
(imported from `affordances.py`), label/hint/params bounds, per-status counts, and the freeform
binding shape (`params == {"npc_id": int}` exactly). Params typing follows each action's own
validator: safe integers and bounded strings for every action, plus the literal boolean `true`
for the `explore.look` room-survey form (`{"room": true}`) — so a degraded card reusing the
canonical baseline payload always passes; any other boolean in `params` is rejected. It does NOT
re-run leak gates, enrichment, or canonical replacement — a wire card is already the output of
the generative layer's ladder (`world/ai/action_options.py`); a card that fails this shape gate
is a bug in the producer, not a player-tamperable path (no `ui_action` accepts raw suggestion
payloads). Same caps mirrored in `protocol.js` as `OPTIONS_*` constants. Alternative considered:
importing the full ladder — rejected: `world/ai` must stay out of the presentation call path
(single-writer, import discipline), and the shape gate is all the wire needs.

### D-3 Exploration suggestions are state-backed through an immutable snapshot

`PresentationContext` gains `options_state: OptionsSnapshot | None = None` (frozen; default
`None` keeps every existing presenter/tests unchanged). `OptionsSnapshot` is a frozen
`{fingerprint: str | None, status, generation_token: int, displayed: tuple[card-dict, ...] |
None}` copied from `session.ndb.options_state` wherever a context is built (dispatcher
publication paths, `ui_sync`, future service pushes). Presenters never read `session.ndb`
directly — the oob-protocol isolation invariant. Rendering rules, in order:

1. snapshot absent or `status == "unavailable"` → `status: "unavailable"` (inert).
2. `generating` → `{status: "generating"}` (no cards).
3. `ready` → cards from `snapshot.displayed` only; if `displayed` is None or fails the v5 shape
   gate the presenter emits `"unavailable"` and logs a bounded diagnostic — never fabricated
   cards (the write side is required to keep ready ⇒ validated displayed).
4. `degraded` → `default_cards(...)` (pure, from the affordance-contract module; subset
   contract), emitted as `degraded`.

`ready`/`generating` never consult `default_cards()`; `degraded` never consults snapshot cards.
Alternative considered: letting the presenter read `session.ndb.options_state` directly —
rejected: it breaks presenter isolation, is untestable without a live session, and duplicates the
ingress's snapshot job.

### D-4 Combat always reports `unavailable`

The combat available form gains `suggestions: {"status": "unavailable"}` unconditionally
(combat-round proposals are out of scope; the dock keeps its existing combat menu as the only
combat surface). The v4-vs-v5 comparison fixture (extending the affordance-contract change's
v3-vs-v4 one) pins that every combat field serializes exactly as v4 with only the version and
`suggestions` added.

### D-5 Version bump, mirrors, and fixtures move as one unit

`CONTEXT_ACTIONS_SCHEMA_VERSION = 5`, `PANEL_ALLOWLIST.context_actions = 5`,
`validateContextActionsPanel` gains the suggestions branches for all three forms (unavailable /
combat / exploration), and every pre-existing v4 expected payload/fixture in `protocol.js`,
`protocol.test.js`, `combat_menu.js`, `web/webclient/presentation/tests/*`, and the browser
suites is updated in the same commit — the unchanged-field claim is pinned by the comparison
fixture rather than by leaving old fixtures green. JSON nesting: the deepest legitimate leaf
remains combat skills at depth 11 (suggestions cards leaf at depth 7), so `MAX_DEPTH = 12`
needs no change; asserted by a test.

### D-6 New parity contract test

`tests/test_context_actions_parity_contract.py` follows the `test_exploration_parity_contract.py`
convention: Python/JS `OPTIONS_*` constant pairs and shared fragments (`"generating"`,
`"ready"`, `"degraded"`, `"unavailable"`, `"known_action"`, `"freeform"`,
`"explore.talk_freeform"`) must co-exist identically in `combat_panel.py`/`affordances.py` and
`protocol.js`.

### D-7 Dependency honesty

This change depends on the affordance-contract change (`ACTION_CODE_ALLOWLIST`,
`default_cards()`, the v4 presenter seam) but is written so it can land immediately after it in
the slice order (overview §4: change 7 then 5). If the dependency change is not yet merged at
implementation time, the tasks are not executable; the change's spec/design documents that
dependency explicitly.

## Risks / Trade-offs

- [Wire contract break at v5] → No released users; mirror + all fixtures land in the same
  commit; rollback is the prior commit (presentation-only path).
- [Snapshot/write-side skew with the later trigger-service change] → The snapshot shape and
  rendering rules are pinned here (read side); the write side (session state population) is
  explicitly out of scope, and `None` defaults make the panel inert rather than wrong.
- [Ready-without-displayed corruption] → Presenter degrades to `"unavailable"` with a bounded
  log, never fabricated cards; the write-side requirement (ready ⇒ validated displayed) is
  recorded in the trigger-service change's contract.
- [Depth bound regression] → Explicit test asserting the suggestions leaf depth stays ≤ 11 given
  `MAX_DEPTH = 12`.
- [Combat byte-identity drift across bumps] → Same comparison-fixture technique the
  affordance-contract change established, re-pinned at v4→v5.

## Roadmap Amendment

The overview's older "context-actions-v3" wording (change 7) is superseded by the v4→v5
sequence: the affordance-contract change lands v4 (and records this amendment in its proposal),
and this change lands v5. Before archiving, the overview doc's §4 table row and the webclient
design doc's "v3" version wording are updated to read `context-actions-suggestions` at v5, so the
design set and the main specs cannot drift.

## Migration Plan

No release migration (0 users). Deployment is one commit: v5 validator + v5 mirror + all fixture
updates together, so no client ever parses a v5 payload it cannot validate. Rollback is the prior
commit (presentation-only; no data schema changes).

## Open Questions

- Whether the exploration form's `suggestions` should later gain a `generated_at`/fingerprint
  echo for diagnostics — currently out of scope (closed schema; the snapshot itself carries the
  fingerprint server-side only).
- Whether the dock needs the `generating` line before the trigger-service change lands — not in
  this change; the wire slot exists, the surface change owns rendering.