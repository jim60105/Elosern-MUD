## Context

The exploration panel v1 (`web/webclient/presentation/exploration.py`) embeds the affordance rules
(talk/party/engage/service gates, move rows, interact targets). The `context_actions` panel is
combat-only at schema version 3 (`web/webclient/presentation/combat_panel.py`,
`CONTEXT_ACTIONS_SCHEMA_VERSION = 3`, `PANEL_ALLOWLIST.context_actions = 3`). The AI action-options
slicing (overview `2026-08-15-ai-action-options-overview-design.md`, subordinate to
`2026-07-29-ai-mud-engine-design.md`) makes this change the root: later slices consume one shared
affordance contract, `default_cards()`, and the exploration `context_actions` form. The
deterministic-playable invariant and the single-writer boundary apply: every producer here is
read-only; adapters remain the only writers.

Ground truth against which this design is written:

- Exploration v1 affordance emission: `_scripted_affordance`, `_freeform_affordance`,
  `_party_invite_affordance`, `_party_leave_affordance`, `_engage_affordance`,
  `_service_affordance`, `_interact_targets`, `_scripted_keywords` in `exploration.py`. Important:
  v1 emits **no schedule gate** (`interaction_reason` is absent from the presenter), freeform is
  always enabled for `LLMNPC`s, and a dead monster keeps a **disabled** engage entry (pinned by
  `test_dead_monster_offers_a_disabled_engage_affordance`). Look is a section, not an affordance;
  no `explore.wait` affordance exists.
- Every eligible affordance must be commit-time re-verified by its adapter
  (`web/webclient/actions/exploration_actions.py`: exact-key `validate_*_payload` validators,
  `_current_node` grid/wilderness/room encoder, `_move_adapter`'s `stale_location` compare,
  `_wait_adapter`'s `unsafe_rejection` gate, `interaction_reason(npc, "talk")` on the talk
  adapters). `DAYPARTS = ("midnight", "dawn", "noon", "dusk")`.
- The panel-level protocol conventions (exact fields, unavailable form with `PresenterSpec`
  `schema_version`, dual-direction parity tests, Node evidence bridge) come from the OOB protocol
  foundation / existing panel slices.

## Goals / Non-Goals

**Goals:**
- One shared, read-only affordance vocabulary (`affordances.py`) with validator-normalized params.
- v1 exploration panel payload byte-identical after extraction (guarded by a test).
- `context_actions` v4: combat form byte-identical; new exploration form; shared unavailable form
  (field set unchanged, `schema_version` follows the panel version).
- `default_cards()` deterministic fallback derivation (1..5, suggestible-and-enabled only, subset
  contract).
- Shared node-ID encoder so move cards pass the adapter's `stale_location` compare.
- Client mirror (`protocol.js`) at v4 with dual-direction parity coverage.

**Non-Goals:**
- No suggestions section (`suggestions` lands in a later slice as schema v5).
- No new eligibility gates in the v1-visible vocabulary (schedule gating lives in the
  suggestion-eligibility layer; this keeps v1 byte-stable).
- No changes to adapters, command surface, or Evennia typeclasses.
- No `explore.interact` action — the interact group remains a label over per-target affordances.
- No NPC/companion `explore.engage` — engagement stays monsters-only (`{monster_id}`).
- No navigation surfaces in the suggestible set; the guild/shop entries remain kind-list openers.
- No affinity/objective scoring beyond objective-identity ranking; no AI involvement.

## Decisions

### D-1 The vocabulary shape is a discriminated union, not a flat record

`AffordanceView` (frozen): **action entries** carry exactly `action_id`, `label`, `params`,
`freeform: bool`, `navigation: false`, `enabled: bool`, `disabled_reason: (code, message) | None`;
**navigation entries** carry exactly `surface` (`"guild"` / `"shop"`), `label`, `navigation:
true`, `enabled`, `disabled_reason`, and **no** `action_id`/`params`. This mirrors the v1 panel's
`kind: "navigate"`/`surface` descriptor and resolves the round-three review contradiction where a
navigation entry with no dispatcher code could not satisfy `action_id ∈ ACTION_CODE_ALLOWLIST`.
The v1 panel's own descriptor shape is a separate serialization, produced by the shared module;
each surface renders its own form.

### D-2 Wire-shape guarantee: builders call each action's registered validator

For every non-freeform action entry, the builder constructs a candid payload and passes it through
that action's `validate_*_payload` (exact keys, bounded), storing the normalized output in
`params`. `explore.look` emits `{"target_id": int}` (per present object) or `{"room": true}`
(baseline); `explore.wait` emits `{"daypart": "noon"}` (fixed legal value — pure and
deterministic); move emits `{"exit_ref", "current_node"}`. The freeform entry is the single
exception: `{"npc_id": int}` is binding-only (no validator produces it without `speech`; the
client composes the full payload at dispatch time in a later slice). A builder whose candid
payload is rejected by its validator is a logging bug (asserted in tests).

### D-3 Extracting the node-ID encoder to `web/webclient/actions/node_ids.py`

`node_id_for_location(location)` (pure, no imports) replaces `_current_node`; the move adapter and
the move affordance builder both call it, so the card's `current_node` is byte-identical to the
adapter's re-derivation. Import direction stays acyclic: `presentation` → `actions` only.

### D-4 Vocabulary keeps v1 semantics; eligibility is a separate layer

The extracted vocabulary reproduces v1 exactly: no schedule gate in the emitted entries, freeform
always enabled for `LLMNPC`s, dead monsters keep their disabled engage entry. The
**suggestion-eligibility layer** `suggestible_candidates(affordances)` then derives the
executable subset — action entries with `enabled`, code in `SUGGESTIBLE_ACTION_IDS`, not blocked
by `interaction_reason(npc, "talk")`, and no unsafe-room wait — because the round-three review
exposed that gating inside the vocabulary would change v1 fixtures (byte-stability conflict) and
that un-gated `default_cards()` could recommend cards the adapters reject. This keeps
"a card the player can click is never one the adapter rejects with `schedule_blocked`" true for
*suggestions* without touching the v1 surface.

### D-5 Idle baseline: at least one always-eligible entry

`explore.look {room: true}` is always emitted in exploration mode (puppeted player inside a
location). `explore.wait {"daypart": "noon"}` is emitted only when `unsafe_rejection(actor)` is
absent (a room with a living monster makes the wait adapter reject with `unsafe_skip`), so an
executable baseline is guaranteed while wait never appears as an unrunnable card. Baseline entries
are vocabulary-only in this slice — they do not appear in the v1 panel payload (look is a section
there; wait has no v1 affordance) — and they do appear in the exploration context form and in
`default_cards()`.

### D-6 Suggestible set and `default_cards()`

`SUGGESTIBLE_ACTION_IDS = {explore.move, explore.look, explore.talk_scripted,
explore.talk_freeform, explore.engage, explore.wait}` — excludes `party_invite`/`party_leave`
(companion management is a dock affordance, not a suggested action) and all navigation entries.
`default_cards(affordances, *, objective_npc_ids=frozenset())` filters to
`suggestible_candidates()`, ranks objective-relevant first (objective Npc identity matching
talk/engage targets), then talk/engage over baseline, preserves vocabulary order within a rank,
and caps at `MAX_CARDS = 5`. The room-look baseline guarantees ≥ 1; the subset contract
(`default_cards` ⊆ current union, same params/labels) is asserted per-fixture.

### D-7 `context_actions` v4 — one available form per kind, bounded via shared caps

`validate_context_actions` dispatches on `kind`: `combat` keeps the exact v3 field set,
validation, and semantics (a single `kind == "combat"` branch stays untouched apart from the
version constant); `exploration` requires exactly `schema_version (4), available (true), kind,`
and `affordances` (list of `AffordanceView` union entries, `action_id ∈ ACTION_CODE_ALLOWLIST` or
`surface ∈ {"guild", "shop"}`, validator-normalized params, exact flags/bounds) with
`MAX_CONTEXT_AFFORDANCES = 320`. That bound derives from the shared v1 caps (≤ 32 targets × ≤ 8
affordances, ≤ 16 keywords per host, ≤ 12 exits, ≤ 32 objects look-targets, ≤ 2 baseline, ≤ 2
navigation = 324 worst case; 320 with the v1 `MAX_AFFORDANCES`-per-target cap never truncating a
legal room — asserted by a maximal-fixture test). The presenter (`context_actions_presenter`)
switches on canonical mode: active combat session → combat form; exploration mode → exploration
form in vocabulary order; creation-pending/absent location → `PanelUnavailableError` (registry
emits the shared unavailable form). The unavailable form's field set, reason, and semantics are
unchanged; its `schema_version` equals the panel version like every other form (so the literal
"unchanged" claim in tests must expect exactly the version field to differ). The client mirror
(`PANEL_ALLOWLIST.context_actions` → 4) is updated in the same change, including every existing
v3 fixture in `protocol.js`, `protocol.test.js`, `combat_menu.js`, and the Python/browser suites,
while one v3-vs-v4 comparison fixture pins the combat field byte-identity.

### D-8 Module boundaries stay read-only

`affordances.py` imports only canonical handlers/components/registries and action validators; a
deterministic-path test asserts none of its call graph reaches a mutator. No module-level Evennia
imports; deferred imports where needed, matching exploration.py's idiom.

## Risks / Trade-offs

- [Schema-version skew between slices] → This slice pins
  `CONTEXT_ACTIONS_SCHEMA_VERSION = 4` and the mirror; the suggestions slice (v5) bumps once more.
  Combat form byte-identity across bumps is re-pinned by the comparison fixture here and
  re-verified there. The overview's later "context-actions-v3" wording is superseded by this
  v4-v5 sequence; the roadmap note in proposal.md records the amendment.
- [Eligibility duality (vocabulary vs suggestible) drifts] → `suggestible_candidates` is the
  single derivation consumed by `default_cards()` and (later) by the trigger service; tests pin
  the v1-visible vocabulary unchanged while suggestible output adapts to gates.
- [Extraction drift silently changes v1 payloads] → A byte-stability test serializes the v1
  exploration payload from the extracted module against the pre-refactor expected fixtures.
- [Validator reuse couples vocabulary to adapter contract] → Deliberate: that coupling is the
  wire-shape guarantee; a shape drift between vocabulary and adapter is exactly the failure this
  slice exists to make impossible.
- [320-entry form size] → The form is bounded by the same caps the v1 panel already uses; a full
  maximal room is a degenerate fixture, and the JSON depth is unchanged (flat entries).
- [Two producer kinds in one panel confuse the dock] → The dock renders the exploration context
  form only in a later slice; until then the form exists server-side, validated, with no client
  rendering beyond the strict mirror.

## Migration Plan

No release migration: the project has no released users. Deployment is a single commit landing
the extraction and the v4 panel together — the v4 mirror and all v3 fixture updates land in the
same commit, so no client ever parses a v4 payload it cannot validate. Rollback is the prior
commit (no data schema changes; only presentation paths).

## Open Questions

- Whether the objective-first ranking in `default_cards()` should consume the quest public view
  directly or accept an injected objective-npc set — this slice keeps the injected-argument
  variant (pure), and the trigger-service slice decides the producer.
- Whether later slices should allow `party_invite` cards via a dedicated "companion" grouping —
  currently decided against (D-6), kept revisable without a contract break since the set is one
  constant.