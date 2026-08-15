## Why

The upcoming AI action-options feature needs one canonical, read-only "current valid actions"
contract that the exploration panel, the `context_actions` panel, the deterministic degradation
fallback, and (later) the AI proposal ladder all consume. Today those affordance rules are
embedded in `web/webclient/presentation/exploration.py` and unusable by any other surface; the
`context_actions` panel is combat-only; and nothing derives a deterministic "what now?" fallback
list. This change extracts the affordance vocabulary into a shared module (behavior-preserving for
the exploration panel v1), teaches `context_actions` an exploration form carrying that vocabulary,
and delivers `default_cards()` — the deterministic rule-card derivation that later slices feed
into the suggestions surface.

## What Changes

- Extract the room-entity affordance rules out of `web/webclient/presentation/exploration.py` into
  a new shared module `web/webclient/presentation/affordances.py`:
  - A frozen, discriminated `AffordanceView` contract: **action entries** carry `action_id`,
    `label`, `params`, `freeform`, `navigation: false`, `enabled`, `disabled_reason`; **navigation
    entries** carry `surface` (`"guild"` / `"shop"`), `label`, `navigation: true`, `enabled`,
    `disabled_reason`, and **no** `action_id`/`params` — matching the v1 navigate descriptor's
    `surface` representation, so no entry ever carries a fake dispatcher code.
  - Builders for `explore.move` (per exit), `explore.look` (targeted per present object), per
    keyword `explore.talk_scripted` / per-NPC `explore.talk_freeform` (same host/party/companion
    gates and disabled semantics the v1 panel has today — no new eligibility gates in this slice),
    `explore.party_invite` / `explore.party_leave`, `explore.engage` (living-hostile-monster rule;
    dead monsters keep their disabled entry, exactly as v1), and the idle baseline
    (`explore.look {room: true}` always; `explore.wait {daypart: "noon"}` only when the wait
    adapter's `unsafe_rejection` is absent).
  - The exploration panel v1 presenter keeps emitting a byte-identical payload while delegating
    its internal builders to the shared module (guarded by a byte-stability test).
- Add a suggestion-eligibility layer `suggestible_candidates(affordances)` over the vocabulary: an
  entry is suggestible iff it is an action entry with `enabled`, code in
  `SUGGESTIBLE_ACTION_IDS`, not `freeform`-less talk blocked by the schedule gate
  (`interaction_reason(npc, "talk")`), and not a wait entry in an unsafe room (baseline already
  encodes that). The vocabulary itself keeps today's panel semantics untouched.
- Move the node-ID encoder out of `web/webclient/actions/exploration_actions.py` into a shared
  pure module `web/webclient/actions/node_ids.py` (`node_id_for_location(location)`), used by
  both the move adapter's `stale_location` check and the move affordance builder so a move card's
  `current_node` is byte-identical to what the adapter re-derives (GridRoom, TerrainRoom,
  ordinary-room covers, tested).
- Bump `context_actions` from schema version 3 to **version 4**:
  - The combat available form stays byte-identical (same exact fields, validation, and semantics
    as v3; `kind == "combat"` emits only inside a valid active combat session).
  - A new exploration available form (`kind == "exploration"`) carries the room's complete
    canonical affordance vocabulary (union of action and navigation entries) in vocabulary order.
  - The registered unavailable form keeps its exact field set, reason, and semantics; its
    `schema_version` follows the panel version (4) like every other form.
  - Vocabulary output is bounded by shared cap constants carried over from the v1 panel
    (≤ 32 interact targets, ≤ 16 scripted keywords per host, ≤ 8 affordances per target, ≤ 12
    exits, ≤ 32 objects) and validated by the server validator at
    `MAX_CONTEXT_AFFORDANCES = 320`; because producer and validator share those caps, a legal
    room can never truncate the list.
- Update `PANEL_ALLOWLIST.context_actions` to `4`, the `protocol.js` client mirror, and the
  dual-direction parity coverage for the new exploration form. Update every existing v3 fixture
  across `protocol.js`, `protocol.test.js`, `combat_menu.js`, and the Python/browser suites in
  the same change (keeping one v3-to-v4 combat-field comparison fixture).
- Add `ACTION_CODE_ALLOWLIST` (the eight emitted action ids; no `explore.interact` — the panel's
  interact group is a label over per-target affordances) and `SUGGESTIBLE_ACTION_IDS` (excludes
  `party_invite`/`party_leave`), asserted by one pure parity test each. Navigation entries are
  excluded from suggestions by construction (no action code exists for them).
- Add `default_cards(affordances, *, objective_npc_ids=...)` in `affordances.py`: the
  deterministic degradation derivation restricted to `suggestible_candidates()` — at most 5
  cards, at least 1 in v1 exploration (the room-look baseline is always suggestible),
  objective-relevant ranked first, vocabulary order within a rank, every card an executable
  suggestion card (same `action_id`, validator-normalized `params`, same label), strict subset of
  the current affordance union (asserted by a subset test).
- All producers remain read-only: no new code path mutates traits, knowledge, dialogue, quests,
  inventory, combat sessions, party, or world time.

**BREAKING**: `context_actions` schema version 3 clients cannot parse a version-4 payload (a new
available form exists). The project has no released users; no compatibility shim is added. The
combat form payload itself is byte-identical.

**Version sequence (roadmap amendment, recorded here):** `context_actions` is already v3
(combat) since the skill-category-combat-panel change; this change lands v4; the suggestions
section lands as **v5** in a later slice (the overview's later "context-actions-v3" wording is
superseded — see design.md Decisions).

## Capabilities

### New Capabilities
- `exploration-affordances`: the canonical, shared, read-only affordance contract — the
  `AffordanceView` discriminated union (action vs navigation), the eight emitted action codes
  plus the guild/shop surfaces, validator-normalized params, the freeform binding-only exception,
  the idle baseline (room-look always, wait when safe), the suggestible set with schedule-gate
  eligibility, and the deterministic `default_cards()` derivation.
- `webclient-context-actions`: the `context_actions` panel contract at schema version 4 —
  available combat form (referencing the `webclient-combat-menu` field contract, preserved
  unchanged), the new available exploration form with its complete canonical affordance list, and
  the shared unavailable form whose field set is unchanged across versions.

### Modified Capabilities
- `webclient-combat-menu`: the panel registration requirement is restated for schema version 4 —
  the combat available form keeps its exact v3 fields and semantics but is emitted only inside a
  valid active combat session and never fabricates combat fields outside one.

## Impact

- **Code**: `web/webclient/actions/node_ids.py` (new shared encoder),
  `web/webclient/actions/exploration_actions.py` (delegates to it), `web/webclient/presentation/
  affordances.py` (new shared vocabulary), `web/webclient/presentation/exploration.py` (delegates
  to the shared builders, byte-identical v1 output), `web/webclient/presentation/combat_panel.py`
  (v4 validation with the exploration form and kind-switching presenter),
  `web/webclient/presentation/registry.py` (unchanged mechanics),
  `web/static/webclient/js/elosern/protocol.js` (`PANEL_ALLOWLIST` → 4, v4 mirror).
- **Tests**: pure `unittest` fixtures per affordance rule; a byte-stability test pinning the v1
  exploration payload; node-encoder tests across room kinds; `default_cards()` subset/order/bounds
  and suggestible-filter tests; v4 validator tests (combat preserved including a v3-vs-v4
  comparison fixture, exploration form, unavailable form versioned only in `schema_version`);
  Node mirror + parity tests for the new form; read-only assertions via the existing
  deterministic-path scanning.
- **Downstream**: this change is the root change of the AI action-options slicing; later slices
  (schema, prompts, layer, trigger service, suggestions v5) build on `affordances.py`,
  `default_cards()`, and the exploration form without touching the v1 panel behavior. No player
  commands are added or changed (`options.dismiss` is a later OOB action, not a command), so
  `docs/game/commands.md` and `docs/game/command-reference.md` are unaffected.