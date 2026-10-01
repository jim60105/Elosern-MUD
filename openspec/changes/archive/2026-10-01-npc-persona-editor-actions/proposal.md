## Why

The approved design (`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §8, §11.1 cases 5–7) makes every NPC's card editable by the ordinary authenticated player as an author tool, opened from the interaction surface. That needs a server-authorized transport first: two allowlisted OOB actions that re-resolve the target from the actor's room on every request, gate by mode and ownership, delegate writes to the deterministic persona service with a version check, return a private snapshot within the existing result-data contract, and a server-authored entry affordance plus an exact browser mirror of the card contract. The existing player persona editor must not be reused by forwarding an NPC id.

## What Changes

- Register `npc.persona.read` and `npc.persona.update` in the production action registry (new module `web/webclient/actions/npc_persona_actions.py`) with exact payload validators (positive safe-integer `npc_id`/`expected_persona_version`, never booleans; exact card shape) and adapters that admit only the session's own activated puppet in exploration or dialogue mode, re-resolve an NPC-family target from current room contents, and call `read_npc_persona` / `update_npc_persona`.
- Success `data` is exactly `npc_id`, `display_name`, `npc_title`, `persona_version`, `persona`; stable rejection codes `npc_persona.no_target`, `npc_persona.not_allowed`, `npc_persona.unavailable`, `npc_persona.version_conflict`, and contract codes `npc_persona.<reason>[.<leaf>]`; error results carry no data; no card text in messages or events.
- The exploration presenter adds one 編輯人物設定 `navigate` affordance with surface `npc_persona` to every NPC-family target (last, reserved within the 8-descriptor bound), enabled only when the target's card and metadata are readable and valid, computed by a silent read-only predicate.
- Browser protocol mirror: the `npc_persona` navigation surface; a DOM-independent card-contract mirror (`web/static/webclient/js/elosern/npc_persona_card.js`) tested in Node against the foundation's shared boundary fixture; maximal-card envelope tests through both protocol validators.

The editor window itself is `npc-persona-editor-window`.

## Capabilities

### New Capabilities

- `npc-persona-editor`: the server-authorized author-editor read/update actions, their admission, privacy, version semantics, and the browser card-contract mirror.

### Modified Capabilities

- `webclient-exploration-menu`: the navigation surface set gains `npc_persona`, and every NPC target carries the author-editor navigation.
- `webclient-action-dispatch`: the production registry gains the two NPC author-editor actions.

## Impact

- Code: `web/webclient/actions/npc_persona_actions.py` (new), `web/webclient/actions/registry.py`, `web/webclient/presentation/exploration.py` (affordance), `world/rules/npc_persona.py` (silent `is_card_available` predicate only), `web/static/webclient/js/elosern/protocol/*` (surface), `web/static/webclient/js/elosern/npc_persona_card.js` (new), Node tests under `web/static/webclient/js/tests/`.
- Tests: `web/webclient/actions/tests/` (package-owned), `web/webclient/presentation/tests/` (explicit shard registration), Node gate.
- No UI component, no browser test (the window change owns those).

## Batch:

depends-on: npc-persona-card-foundation

Code-conflict notes: sole editor in this batch of `web/webclient/actions/registry.py`, `web/webclient/presentation/exploration.py`, and the client protocol mirror (`web/static/webclient/js/elosern/protocol/*`). It imports `_present_by_id` from `web/webclient/actions/exploration_actions.py` without editing it (that file is edited by `npc-persona-dialogue-consumption`). `world/rules/npc_persona.py` gains one read-only predicate here; dialogue-consumption and the cutover add other functions there (mechanical rebase). Shared append-only: `.github/evennia-shards.json` (presentation test registration), observability catalog if new events are added. Prerequisite of `npc-persona-editor-window`. Shipped NPCs show an enabled editor only after producers or the cutover initialize their cards, which is how this change avoids activating the editor against incomplete profile data.
