## Context

See proposal.md for motivation. The dispatcher resolves the actor from the authenticated session puppet, validates the exact payload, enforces presentation-epoch staleness, per-session single mutation in flight, and request-id deduplication, then calls `adapter(actor, payload, session)`. `web/webclient/presentation/protocol.py` caps result `data` at 8 fields, 2,048 code points per string, and `MAX_RESULT_DATA_BYTES` (63,183), and forbids reserved keys (`revision`, `actor`, `session`, …) at any depth. `in_exploration_mode(actor)` excludes creation-pending and active-combat actors and is true in dialogue mode. `_present_by_id(actor, id)` resolves from current location contents; `is_possessed_actor` identifies a possessed puppet. Exploration `interact` targets are serialized in `_interact_targets`, which emits 交談 directly and maps vocabulary entries; navigation affordances today use surfaces `guild`/`shop`.

## Goals / Non-Goals

**Goals:** a minimal, exact, re-authorized transport for the author editor; no card data outside the requesting session's results; one source of validation truth with an exact browser mirror.

**Non-Goals:** the editor window, focus/keyboard behavior, user docs (window change); scripted-line editing; name/title/stat editing; builder permissions.

## Decisions

### D1. A dedicated action module, not the player persona action

`npc_persona_actions.py` owns both validators and adapters; it imports `update_npc_persona`/`read_npc_persona` only, never `world.rules.persona_edit`. Alternative rejected: extending `character.persona.update` (would forward an NPC id into a player API — explicitly forbidden).

### D2. Payload validation is structural; content validation is domain

Validators enforce exact key sets at both card levels, string leaves of at most the protocol string cap, and positive safe integers rejecting booleans (`type(x) is int`). Emptiness, per-leaf 600, identity-section, and total budgets are checked by the domain contract inside `update_npc_persona`, so their failures become field-specific codes (`npc_persona.required_empty.speech_style`, `npc_persona.leaf_too_long.identity.public`, `npc_persona.identity_section_too_long`, `npc_persona.card_too_long`) with Traditional Chinese messages naming the field label, instead of a generic `malformed_payload`. All codes match the protocol identifier pattern (`[a-z0-9._]{1,64}`).

### D3. Admission order and outcomes

Both adapters: (1) possession → `not_allowed`; (2) `in_exploration_mode` false → `not_allowed`; (3) `_present_by_id` → must be `isinstance(target, NPC)` (excludes `Monster`, player characters, objects) → else `no_target`; (4) read: `read_npc_persona` unavailable → `unavailable`; update: map service outcomes (`updated`/`unchanged` → success data; `version_conflict` → message 「這位角色的設定已在其他地方更新（目前第 N 版），請重新載入後再編輯。」; `invalid` → D2 codes; `unavailable` → `unavailable`). Messages never quote card text. The read declares no affected panel beyond the dispatcher's standard completion publication; the update declares `exploration` so the enabled state of the affordance stays fresh.

### D4. Success data shape

`{"npc_id": int, "display_name": npc.key, "npc_title": npc.npc_title or "", "persona_version": int, "persona": card.to_record()}`. Five fields (limit 8); leaf strings ≤ 600 (cap 2,048); worst-case bytes: a valid card is ≤ 2,000 rendered code points, so raw leaf text ≤ 2,000 code points ≤ 12,000 JSON bytes under six-byte escaping, plus fixed keys, a ≤ 64-code-point name and bounded title, far below 63,183. Tests build maximal valid cards (CJK, astral, escape-heavy) and pass the envelope through the server result-envelope validator in `web/webclient/presentation/protocol.py` and the Node protocol mirror.

### D5. The entry affordance is silent and read-only

`_interact_targets` appends `{"kind": "navigate", "surface": "npc_persona", "label": "編輯人物設定", "enabled": …, "disabled_reason": …}` to every `NPC`-family target after truncating the other affordances to `MAX_AFFORDANCES - 1`. `enabled` uses `npc_persona.is_card_available(npc)`, a read-only predicate that validates card and metadata without emitting the unavailable event (snapshots are frequent; the event is reserved for explicit reads). A possessed actor gets the possession-refusal reason. The `context_actions` panel is not changed (the row is emitted directly by the exploration presenter, like 交談).

### D6. Browser mirrors

`web/static/webclient/js/elosern/protocol/*` accepts `npc_persona` as a navigation surface (exact descriptor fields unchanged). `web/static/webclient/js/elosern/npc_persona_card.js` exports the field order, labels, bounds, `normalizeCard`, `cardBudget`, and reason codes; code points are counted with `Array.from(str).length`. `web/static/webclient/js/tests/npc_persona_card.test.js` reads `world/lore/tests/fixtures/npc_card_boundary_cases.json` (the foundation's shared fixture) and asserts identical decisions, codes, and leaves.

## Risks / Trade-offs

- [Pre-cutover shipped NPCs show a disabled editor] → intended gating; the disabled reason explains it; no editor is activated against missing cards.
- [Dispatcher request-id cache holds card data in memory] → per-session, bounded, server-side only, retired with the session epoch (existing rules).
- [JS and Python drift] → the shared fixture is the single source of boundary truth for both test suites.
