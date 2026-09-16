## 0. Prerequisites (exact predecessor contracts)

- `skill-effect-model` at master 9ca95ba ships 「A conditional follow-up strike repeats damage without repeating the action」 (evidence-gated `repeat_when` ∈ `EVIDENCE_KINDS`, `extra_strikes` ∈ {0,1}, `extra_strikes > 0 ⟹ repeat_when`, `repeat_when ⟹ extra_strikes == 1`); this change is the strict-superset MODIFIED delta that retires exactly the middle implication.
- The dual-strike settlement loop, ordered HP projection, single terminal emission and atomic rollback are shipped in `_handle_damage` (`world/rules/combat.py`) and pinned by `world/rules/tests/test_action_evidence.py`; this change reuses them verbatim.

## 1. Vocabulary widening (code)

- [x] 1.1 Confirm every predecessor contract is shipped and inspect current source/exported references (codegraph/LSP) for `DamagePolicy.__init__`/`__post_init__` (`world/skills/effects.py:484-675`), the `_handle_damage` extra-computation hunk (`world/rules/combat.py` ~360-366), `has_action_evidence`, and every shipped `extra_strikes`/`repeat_when` author (registry `penitent_touch`; the synthetic authors in `test_conditional_damage.py`/`test_action_evidence.py`) before editing; if any settlement guarantee this design claims is missing, STOP and fix it in its owning behavior surface — do not bolt code onto the catalog.
- [x] 1.2 Retire the single validation rule 「`repeat_when is None` and `extra_strikes != 0` raises」 in `DamagePolicy.__post_init__` per design D1/D3; keep every other rule byte-identical (int/bool checks, cap {0,1}, `EVIDENCE_KINDS` membership, repeat_when⟹extra_strikes==1, both-bypass rejection, empty-predicate multiplier rule); update the class docstring to state both shapes (evidence-conditional / unconditional) and the `total_strikes = 1 + extra_strikes` semantics.
- [x] 1.3 Change the extra-computation leg in `_handle_damage` per design D2: `extra = damage_policy is not None and extra_strikes > 0 and (repeat_when is None or has_action_evidence(...))`; `total_strikes = 1 + damage_policy.extra_strikes` when extra, else 1 — no other hunk of the strike loop touched (rolls, predicate matching, divert staging, pending applies, dispatch legs unchanged).
- [x] 1.4 In-file test updates: retire `test_extra_strikes_without_repeat_when_raises` (the requirement sentence it pins is deleted — replaced by 2.2's acceptance behaviors, NEVER re-pinned); every other pin in `world/rules/tests/test_conditional_damage.py` and `world/rules/tests/test_action_evidence.py` stays verbatim (the conditional sibling's scenarios are the superset base).

## 2. Behavioral evidence

- [x] 2.1 Disposable offline engine scenario exercising the widened vocabulary through real casts before writing permanent tests: unconditional dual-strike on a synthetic skill (roll matrix hit-hit/miss-hit/hit-miss/miss-miss), one payment/practice observed, both rolls recorded, ordered HP projection, two-strike lethal crossing → exactly one defeat entry, nonlethal protected target → HP 1 + one knockout, commit-step failure → full restore, conditional sibling regression (evidence absent → one strike), policy-free control → one strike.
- [x] 2.2 Synthetic behavior tests in a new module `world/rules/tests/test_unconditional_multi_strike.py`: the roll matrix, once-paid/once-practice, ordered projection, single terminal emission, nonlethal floor, atomic rollback, control-skill silence, and the construction matrix of the MODIFIED requirement's last scenario (both legal shapes construct; unknown kind / boolean / cap-2 / repeat_when-without-1 still raise). No catalog-row equality, key-set, or data-echo assertions anywhere (ratified NON-GOAL).
- [x] 2.3 Register `world.rules.tests.test_unconditional_multi_strike` in exactly one shard (`rules-a`, beside `test_action_evidence`) in `.github/evennia-shards.json` (the wave's manifest appends sequence under supervisor); verify the ownership-contract test.

## 3. Focused invocation

```sh
uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_conditional_damage world.rules.tests.test_action_evidence world.rules.tests.test_unconditional_multi_strike world.rules.tests.test_gauge_transfer world.rules.tests.test_water_mana_tide world.rules.tests.test_damage_divert
uv run --locked python -m tools.observability_lint check
uv run --locked python -m tools.test_data_lint check
uv run --locked python -m tools.spec_traceability check
uv run --locked openspec validate unconditional-multi-strike --strict
```

Pass `MUD_TEST_SETTINGS=1` through the tool environment, never a shell prefix. No full local suite/browser/aggregate-coverage run; no command above ten minutes. No apply, archive, main-spec sync or merge in the proposal turn. Canonical IDs via `uv run --locked python -m tools.spec_traceability list` at the separately authorized main-sync; the renamed requirement ID `skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action` annotates `test_unconditional_multi_strike` (renamed from `a-conditional-follow-up-strike-repeats-damage-without-repeating-the-action`; the existing annotations on `test_action_evidence`/`test_conditional_damage` re-home at the main-sync).
