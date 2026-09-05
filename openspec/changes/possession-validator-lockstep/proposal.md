# Proposal: possession-validator-lockstep

## Why

The archived possession program's webclient change (8) added `explore.possess` /
`explore.possess_release` to the shared affordance vocabulary (`affordances.py`) and registered the
dispatch adapters, but never synchronized the three validator surfaces that sit between the
vocabulary and the browser. Audit evidence (post-archive static review, re-verified in tree):

1. **The exploration panel self-poisons.** `web/webclient/presentation/exploration.py:616-622`
   emits `explore.possess` on every bound companion target, but the same file's local `ACTION_IDS`
   (:83-89) enumerates only the five pre-possession codes; `_descriptor` (:199-200) raises
   `ProtocolValidationError` for the unknown code, the presenter's except-clause logs
   `exploration_possession_affordance_dropped`, and the registry degrades the ENTIRE exploration
   panel to internal-unavailable — in any room containing a bound companion, for every player,
   possessed or not.
2. **`context_actions` dies on a KeyError.** `web/webclient/presentation/options.py`'s
   `_ACTION_PAYLOAD_VALIDATORS` (:59-68) has no entry for the possession codes; line :88 is a bare
   dict lookup → `KeyError`. It is called for every affordance by the combat-panel validator
   (`combat_panel.py:487`) and by the context/suggestion validators (:107, :125) — so the
   PartyDrawer's panel source is unavailable whenever a bound companion is present, and an LLM
   suggestion card proposing a possession action raises instead of being cleanly refused.
3. **The production client mirror rejects what the server legally emits.**
   `web/static/webclient/js/elosern/protocol.js` — `CONTEXT_ACTIONS_ACTION_CODES` (:544-553) lists
   8 codes, `EXPLORATION_ACTION_IDS` (:3090-3096) lists 5, and the `params` switch inside
   `validateContextActionsAffordanceParams` (:1093) has no possession branches. The synced specs
   (`webclient-context-actions` "the production client mirror SHALL enforce the same contract",
   `webclient-exploration-menu`) are violated: server and client enumeration tables drifted 10↔8.

The landed tests missed all three because they exercise the bare vocabulary, the banner, and the
PartyDrawer row presenters directly — never the full panel render of a room containing a bound
companion. The feature is spec-complete but end-to-end unreachable in the webclient.

## What Changes

- **Server panel validators become total over the vocabulary.** `exploration.py`'s local
  `ACTION_IDS` widens to the full `ACTION_CODE_ALLOWLIST` (adds `explore.possess`,
  `explore.possess_release`); `options.py`'s payload-validator table registers the two possession
  validators from their current home in `exploration_actions.py` — which `options.py` already
  imports the other seven payload validators from, so no relocation and no new import edge is
  needed; and the lookup becomes a structured rejection instead of a `KeyError` for any future
  unregistered code.
- **Client mirror re-locks the table.** UMD `protocol.js` gains the two codes in both enumeration
  tables plus the `params` switch branches — both codes accept exactly the canonical
  `{"npc_id": <positive integer>}` shape the landed Python validators enforce
  (`exploration_actions.py:233-249`) and the vocabulary emits, rejecting everything else. The Vue
  app sources are audited for equivalent tables and fixture-pinned.
- **Integration regression at the layer that broke**: an EvenniaTest that renders BOTH panels for a
  room containing a bound companion and asserts available forms with the possess affordance —
  exactly the combination no existing test covers.

No game-rule, command, docs, or lore change; no protocol `schema_version` bump (the panel field
sets are unchanged — only which legal `action_id` values the enumerations admit; the affordance
shape contract is the one the vocabulary already emits).

## Capabilities

### Modified Capabilities

- `webclient-exploration-menu`: the version-1 panel's interact action enumeration widens to admit
  the two possession codes; a legal vocabulary emission can never degrade the panel from within.
- `webclient-context-actions`: affordance payload validation is a total function over the
  vocabulary allowlist (registered validator or structured rejection — never a Python error), and
  the production client mirror enforces the same widened contract.

## Impact

- Affected code: `web/webclient/presentation/exploration.py` (`ACTION_IDS`),
  `web/webclient/presentation/options.py` (validator table registration via its existing
  `exploration_actions` import + total lookup), `web/static/webclient/js/elosern/protocol.js`
  (two tables + params switch), `web/webclient-app/src/protocol/**` (audit; fixture/tables only if
  equivalent enumerations exist; `pnpm run build` regenerates the committed dist only when app
  sources change).
- Affected specs: `openspec/specs/webclient-exploration-menu/spec.md`,
  `openspec/specs/webclient-context-actions/spec.md` (MODIFIED deltas).
- Affected tests: new integration case in an existing exploration-presentation test module (no new
  shard entry if it lands there; a new module file MUST update `.github/evennia-shards.json` in
  the same change); `node --test web/static/webclient/js/tests/protocol.test.js` cases; Vitest
  fixture only if Vue sources change.
- Dependencies: none on the sibling `possession-rules-residue` change — disjoint files, either may
  land first. No multichar interaction (MC1-6 all landed).
- No player-facing command change ⇒ no `docs/game/*` edits, `tests/test_command_docs.py` unaffected.

## Sizing

Half a day: three table registrations, one total-lookup hardening, one UMD switch, plus the
pinning tests. Do not split.
