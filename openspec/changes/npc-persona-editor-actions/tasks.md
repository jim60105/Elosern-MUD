Apply on branch `feat/npc-persona-editor-actions` in worktree `.worktrees/npc-persona-editor-actions`. Run every Evennia label with `MUD_TEST_SETTINGS=1` passed through the Bash tool's `env` input, one focused label per command, output captured to a scratch file. Node: `node --test web/static/webclient/js/tests/<file>.test.js` per file.

## 1. Actions

- [ ] 1.1 Create `web/webclient/actions/npc_persona_actions.py` with the two exact payload validators (design D2) and adapters (design D3/D4); verify validator unit tests in `web/webclient/actions/tests/`: missing/extra keys at both card levels, non-string leaf, boolean and non-positive and over-safe-range integers all rejected; exact five-field success data.
- [ ] 1.2 Register both actions in `build_production_action_registry` and update its docstring; verify the production-registry exact-ID test lists both and `malformed_payload` rejects without invoking the adapter.
- [ ] 1.3 Add `EvenniaTest` admission tests: exploration and dialogue modes admitted; creation-pending, active combat, possessed puppet → `npc_persona.not_allowed`; forged id, another account's player character, monster, remote NPC, NPC moved or deleted after read → `npc_persona.no_target` with no data and no write; uninitialized NPC → `npc_persona.unavailable`; a stale presentation epoch rejected by the dispatcher before the adapter.
- [ ] 1.4 Add update tests: changed card advances version and touches only the selected NPC (two NPCs from one synthetic profile; clock, wallet, quests, relations, party byte-identical); identical card returns success at the same version; cross-session stale version → `npc_persona.version_conflict` naming the current version; field violations map to `npc_persona.<reason>.<leaf>`; a retried identical request id returns the cached result without a second write.

## 2. Privacy and protocol bounds

- [ ] 2.1 Add tests that capture `world.observability` calls (patching the caller modules' bindings) and `actor.msg` output during a read, a successful update, and a rejected update, asserting no card leaf text appears; and that a full snapshot for an actor beside an NPC with a hidden identity contains no card text.
- [ ] 2.2 Build maximal valid cards (CJK, astral, JSON-escape-heavy) at the total budget and assert the success envelope passes the server result validator; verify the label passes.

## 3. Entry affordance

- [ ] 3.1 Add the silent `is_card_available` predicate to `world/rules/npc_persona.py` and the 編輯人物設定 `npc_persona` navigation per design D5 in `web/webclient/presentation/exploration.py`; verify presentation tests (new module under `web/webclient/presentation/tests/`): enabled for a valid card, disabled with `npc_persona.unavailable` for an uninitialized NPC, absent for a monster, possession reason for a possessed actor, last position and survival at the eight-descriptor bound, no unavailable event emitted per snapshot, and the version-3 validator accepting the new surface while rejecting extra descriptor fields; plus a maximal-room fixture (32 NPC targets × 8 affordances, maximal names) that passes the server panel validator and, exported as JSON, the Node protocol mirror.
- [ ] 3.2 Register the new presentation test module in exactly one `webclient-presentation-*` shard of `.github/evennia-shards.json`; verify `tests.test_evennia_test_optimization_contract`.

## 4. Browser mirrors

- [ ] 4.1 Accept the `npc_persona` navigation surface in `web/static/webclient/js/elosern/protocol/*` and add Node tests for acceptance and extra-field rejection; pass the maximal-card success envelopes from task 2.2 (exported as a JSON fixture) through the Node protocol mirror.
- [ ] 4.2 Create `web/static/webclient/js/elosern/npc_persona_card.js` per design D6 and `web/static/webclient/js/tests/npc_persona_card.test.js` over the foundation's shared boundary fixture; verify `node --test web/static/webclient/js/tests/npc_persona_card.test.js` passes with identical decisions, codes, and leaves.

## 5. Gates

- [ ] 5.1 Run `uv run --locked python -m tools.observability_lint check` with the focused labels if any event was added; sync the deltas (new `npc-persona-editor`, MODIFIED `webclient-exploration-menu` and `webclient-action-dispatch`) into `openspec/specs/`, re-anchor/annotate with literal IDs from `uv run --locked python -m tools.spec_traceability list`; verify `tools.spec_traceability check`, `tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate`, `git diff --check`, and `openspec validate npc-persona-editor-actions --strict`.
