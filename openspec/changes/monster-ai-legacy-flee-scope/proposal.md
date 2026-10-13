# Proposal

## Why

`openspec/specs/monster-flee-policy/spec.md` states its flee requirements against `monster_behaviour_policy()` without naming a decision mode, so the main spec currently promises flee behavior to every monster. The shipped engine evaluates `_should_flee` only inside `_legacy_action` (`world/rules/monster_behaviour.py`); the utility dispatch never checks flee. The shipped behavior is the approved contract (`docs/superpowers/specs/2026-10-11-monster-ai-design.md` section 1 and "Deliberately unchanged contracts"), so the specification text is what is wrong. Scoping the flee contract to legacy mode now keeps the current-contract index truthful instead of inviting a future change to "fix" working engine semantics.

## What Changes

- `monster-flee-policy`: explicitly scope the threshold/tier-override resolution, the inclusive-boundary HP predicate and the flee-before-attack priority to `legacy` mode, each keeping its existing requirement identity and scenarios.
- `monster-flee-policy`: add the utility-mode contract as its own requirement — a monster whose effective decision mode is `utility` never voluntarily flees at any HP fraction, flee stays outside its enumerated candidate set, score terms and returned request, an empty candidate set stays the utility decision's own no-action boundary, and the configured typed-invalid-state fallback keeps its existing contract (it still reaches the legacy body, inclusive flee request included).
- Establish the added and re-scoped contract with real behavior tests: one authored threshold, two otherwise identical registered monsters, one legacy and one utility, at the same inclusive boundary (and below it) and with no legal candidate at all. Legacy returns the flee request; utility returns its scored action, its own no-action boundary, and never the flee key; the typed invalid-state fallback at that boundary still returns the legacy flee request. Deterministic, synthetic kit only.
- Register the new non-browser test module in exactly one shard of `.github/evennia-shards.json` and add the change's line to the monster-AI changelog in `docs/development/monster-ai.md`.

No production behavior change. `world/rules/monster_behaviour.py` keeps its shipped dispatch, its legacy body and its utility body. No tuning value, no mode override and no production variant activation changes. No player command documentation changes because no command changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `monster-flee-policy`: three existing requirements gain an explicit legacy scope, and one requirement is added for the utility mode's no-voluntary-flee contract. The remaining flee-policy requirements stay unchanged: request shape and orchestration describe a flee request once one has been selected, archetype threshold declaration is load-time validation, and determinism is mode-neutral once state and RNG inputs are fixed.

## Impact

- Specs: `openspec/specs/monster-flee-policy/spec.md` at archive time, through this change's delta only.
- Tests: one new module `world/rules/tests/test_monster_ai_flee_scope.py`, plus the `.github/evennia-shards.json` registration. Existing annotations on the three scoped requirements are re-reviewed, not re-mounted.
- Docs: one changelog line in `docs/development/monster-ai.md` in the existing per-slice style. `docs/superpowers/specs/2026-10-11-monster-ai-design.md` is the authority and is not amended.
- Gates: the added requirement's identity enters the traceability index only when the archive workflow syncs the delta, so implementation proves the merged-tree state and the unaffected gate subsets, and the sync/archive owner runs the aggregate `tools.contract_gate` after the sync. No waiver or weakened workflow is added.
- No production module, no rulebook YAML, no settings, no migration, no new dependency, no schema, no player-facing command surface.

## Batch:

```text
depends-on: none
```

The monster-AI program is complete and archived; `master` is `5ba74a8c` plus the two test-repair commits `d93a07d3` and `c88e30a4`, and `openspec list` is empty, so there is no in-flight dependency or competing delta.

Code-conflict notes. The only shared files are `.github/evennia-shards.json` (shard 2, `rules-b`) and `docs/development/monster-ai.md`, both owned by this change alone while it is the only active change. The new test module is disjoint from every existing module. No production file is edited, so no code-conflict ownership is required.

Downstream apply uses `feat/monster-ai-legacy-flee-scope` and `.worktrees/monster-ai-legacy-flee-scope`; this planning operation creates neither.