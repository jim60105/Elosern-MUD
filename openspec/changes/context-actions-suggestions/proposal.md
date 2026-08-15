## Why

The AI action-options feature needs one wire slot on the `context_actions` panel where the
deterministic suggestions surface ("AI 正在構思建議…" / rule cards / hidden) rides. The
affordance-contract change ([`action-options-affordance-contract`](../action-options-affordance-contract/proposal.md))
lands the panel at schema version 4 (combat form byte-identical + exploration form +
versioned unavailable form) and explicitly leaves the `suggestions` section to "a later change
bumping to version 5". This change is that later change: it adds the `suggestions` envelope to
every available form, defines the read-side session snapshot the trigger service will fill next,
and keeps the strict validator/mirror/parity contract in one unit.

## What Changes

- Bump `context_actions` from schema version 4 to **version 5** in
  `web/webclient/presentation/combat_panel.py` and `PANEL_ALLOWLIST.context_actions` → `5` in
  `web/static/webclient/js/elosern/protocol.js` (update every existing v4 fixture across
  `protocol.js`, `protocol.test.js`, `combat_menu.js`, the Python presentation suites, and the
  browser suites in the same change).
- Add a `suggestions` section to **both available forms** (combat and exploration):
  - exactly `status` (`"generating"` | `"ready"` | `"degraded"` | `"unavailable"`) and `cards`
    present **iff** status is `ready` or `degraded` (closed per-status schema; `cards` forbidden
    for `generating`/`unavailable`);
  - each card is exactly `kind` (`"known_action"` | `"freeform"`), `action_code`
    (∈ the affordance contract's `ACTION_CODE_ALLOWLIST`; freeform cards use
    `"explore.talk_freeform"`), `label` (1–24 chars, CJK), `params` (the known-action
    validator-normalized canonical payload — ≤ 4 keys, safe ints/bounded strings plus the
    literal boolean `true` for the `explore.look` room-survey form — or the freeform
    `{"npc_id": int}` binding shape), and optional `hint` (≤ 60 chars);
  - per-status card counts: `ready` 3–5, `degraded` 0–5 accepted (the ladder's 0–5 acceptance and
    the v1 degraded nonemptiness rule live in the generative slices; the presentation validator
    and mirror enforce the emitted bounds).
  - The shared common unavailable form keeps its exact field set (`schema_version`, `available`,
    `reason`) with `schema_version` 5 — the webclient design doc's "one field added to every
    form" is amended: a shared panel-agnostic unavailable builder cannot carry a panel-specific
    field (oob-protocol contract), and both validators reject `suggestions` on the unavailable
    form.
- Presenter behavior (deterministic, no trigger service yet):
  - combat available form emits `suggestions.status: "unavailable"` always (combat proposals are
    out of scope; overview §5);
  - exploration available form emits `suggestions` from the read-side session snapshot
    (`context.options_state`); when the snapshot is absent or its status is `unavailable`, emit
    `"unavailable"`; `ready` re-serializes the snapshot's displayed cards; `degraded` derives
    rule cards from `default_cards(affordances)` over the **same affordance tuple just
    serialized into the form**; `generating`/`ready` cards come exclusively from snapshot state,
    never from generation-side metadata.
- Add the read-side contract to `PresentationContext`: a frozen, immutable
  `options_state: OptionsSnapshot | None = None` field (`OptionsSnapshot` = `fingerprint`,
  `status`, `generation_token`, `displayed` cards), built by an `options_snapshot(session)`
  factory that deep-copies displayed cards into immutable representations and wired into every
  existing context-construction site (dispatcher completion/error publication, `ui_sync`
  ingress). The write side (`session.ndb.options_state` population) belongs to the
  trigger-service change; here the field defaults to `None` and every existing presenter and
  test keeps working.
- Presenter isolation and closed-schema discipline stay intact: the presenter reads only snapshot
  state and canonical affordances, never the raw session, never writes game state.
- **BREAKING**: the `context_actions` wire contract changes at v5 (unknown panels/versions are
  rejected by the mirror; no released users — no compatibility layer, mirror and fixtures ship in
  the same commit).

## Capabilities

### New Capabilities
- `webclient-context-actions-suggestions`: the v5 `context_actions` panel contract — the
  `suggestions` envelope on both available forms, the per-status card schema and bounds, the
  read-only state-backed exploration presenter, the v5 client mirror, and the dual-direction
  parity contract.

### Modified Capabilities
- `webclient-combat-menu`: the combat available form's exact field set gains the `suggestions`
  field (status `"unavailable"`); the requirement "Combat context actions are an exact read-only
  panel" is amended so "exactly these fields" includes `suggestions` and the schema-version bound
  of the panel advances per the version contract.
- `webclient-context-actions` (the v4 panel capability introduced by the affordance-contract
  change): the panel advances to version 5 with `suggestions` on both available forms, the
  exploration form's former "SHALL NOT contain a suggestions section" constraint is removed, and
  the common unavailable form's exact field set (no `suggestions`) is pinned.

## Impact

- `web/webclient/presentation/combat_panel.py`: `CONTEXT_ACTIONS_SCHEMA_VERSION` → 5,
  `validate_context_actions` gains the `suggestions` per-status validation, combat presenter
  emits `suggestions`.
- `web/webclient/presentation/` (the v4 presenter from the affordance-contract change):
  exploration suggestions from `context.options_state`.
- `web/webclient/presentation/context.py`: `PresentationContext.options_state` +
  `OptionsSnapshot` (read-side only).
- `web/static/webclient/js/elosern/protocol.js` (+ `protocol.test.js`, `combat_menu.js`):
  allowlist → 5, v5 `validateContextActionsPanel` mirror incl. per-status suggestions validators
  and option caps, fixture updates.
- `tests/test_context_actions_parity_contract.py` (new): Python/JS bounds + fragments parity for
  the suggestions section; existing panel/browser suites update their v4→v5 fixtures.
- No changes to adapters, commands, typeclasses, `world/ai/`, or canonical game state; the
  single-writer boundary and deterministic-playable invariant are untouched (the section is
  hidden-inert until the trigger-service change populates snapshot state).