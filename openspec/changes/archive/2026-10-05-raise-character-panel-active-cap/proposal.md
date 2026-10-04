# raise-character-panel-active-cap

## Why

The character panel fails closed for every progressed character: the presenter's flattened `actives` bound (`MAX_ACTIVE_ROWS = 32`) is structurally below the number of ACTIVE skill rows the read model legitimately assembles — stored keys, innate grants, and every unlocked act-catalogue skill (the `SKILL_REGISTRY` currently carries 66 ACTIVE-kind sexual-act skills alone). Character 悠奈 (pk 229) carries 61 active rows and renders as internal-unavailable (`CharacterPanelError: actives must contain at most 32 skill rows in total`), so the panel is broken for any character past the first tier of skill acquisition.

## What Changes

- Raise the server-side flattened actives bound from 32 to 96 (`MAX_ACTIVE_ROWS = 96` in `web/webclient/presentation/character.py`).
- Raise the mirrored JS wire-validator constant `CHARACTER_MAX_ACTIVE_ROWS` to 96 in lockstep (parity contract enforces equality).
- Amend the frozen spec: the skill-grouping requirement of `webclient-exploration-menu` (the requirement that carries the numeric actives bound for the exact-read-only version-7 character panel) states the flattened actives bound as 96; passives stay 32; `schema_version` stays 7 — the payload shape is unchanged, only a bound value moves.
- Python/JS test updates: bound-driven rejection tests move from 33-row to 97-row for actives; a boundary pair (96 accepted / 97 rejected) and a presenter regression proving a progressed character's full active roster (≥61 rows) render an available panel, with `covers_requirement` traceability on the amended requirement.
- No truncation, no pagination, no schema bump, no player-command surface change.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `webclient-exploration-menu`: the requirement `Character panel skills are grouped by category with the same ordering rule as the combat panel` — the requirement text of the version-7 character-panel contract that fixes the flattened row-count bounds — amends the `actives` flattened bound from 32 to 96; `passives` explicitly stays 32. The bound-rejection scenario is rewritten to the per-array bounds (passives exceeding 32, actives exceeding 96), and new scenarios pin the 96/97 boundary and the progressed-character full-roster render.

## Impact

- `web/webclient/presentation/character.py` — `MAX_ACTIVE_ROWS` literal and the "exact shared bounds" comment block.
- `web/static/webclient/js/elosern/protocol/panels/character.js` — `CHARACTER_MAX_ACTIVE_ROWS` literal (re-exported through `protocol.js`; no JS test pins the literal 32 — the character protocol tests are constant-driven).
- `tests/test_exploration_parity_contract.py` — parity gate comparing the Python and JS literals; verifies automatically once both sides read 96.
- `docs/development/webclient-vue-frozen-contract-audit.md` and any audit manifest under `tools/` — the audit surface enumerates constant *names*, not numeric values (verified: no numeric pin for `CHARACTER_MAX_ACTIVE_ROWS` in the audit doc or under `tools/`); confirm and touch only if an implementation task finds a pinned value.
- `web/webclient/presentation/tests/test_character_panel/` — envelope/boundary tests are constant-driven and adapt; add the 97-rejection boundary and the progressed-actor presenter regression with `covers_requirement` literal IDs.
- Envelope headroom verified: the worst-case legal payload with 96 maximal actives rows serializes to 31,575 bytes vs `MAX_CANONICAL_JSON_BYTES = 65,536`; the live 61-row panel for 悠奈 is 10,332 bytes.
- `.github/evennia-shards.json` unchanged unless a new test module is added; `docs/game/commands.md` / `command-reference.md` untouched (no command surface).
