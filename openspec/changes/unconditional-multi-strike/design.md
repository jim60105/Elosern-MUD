## Context

Delivers the generic **unconditional multi-strike** authoring seam the wind tree prices on 疾風刃舞 gale_dance_strike — 「2.0，多段傷害（連續兩次判定）」(`docs/lore/skill-trees/wind.md`; constitution §4.2 wind row: 動作與閃避（…、多段）). The engine already ships a repeat-strike primitive — but locked to a condition. Pre-audited engine facts (verified at master 9ca95ba):

- **`DamagePolicy` gates extra strikes behind evidence** (`world/skills/effects.py:484-675`): `repeat_when: str | None` accepts ONLY a member of `EVIDENCE_KINDS = {"forced_interaction"}` (`world/lore/action_evidence.py:9`), `extra_strikes: int` is fixed to `{0, 1}`, `extra_strikes > 0` REQUIRES `repeat_when` (construction raises), and `repeat_when` REQUIRES `extra_strikes == 1`. So 「連續兩次判定 with NO condition」 is inexpressible today: `DamagePolicy(extra_strikes=1)` alone raises, and the only shipped multi-hit authoring (light `penitent_touch`, `repeat_when="forced_interaction"` at registry.py ~1697) is evidence-conditional.
- **The settlement path the wind node needs is fully shipped and battle-tested**: `_handle_damage` (`world/rules/combat.py:313+`) computes `extra = repeat_when is not None and extra_strikes > 0 and has_action_evidence(...)`, `total_strikes = 2 if extra else 1`, then loops two independent hit rolls at the same coefficient/policy, projects ordered HP through the staged `apply()` closures, floors nonlethal crossings at 1 HP, and emits at most one terminal defeat/knockout — the requirement `skill-effect-model::a-conditional-follow-up-strike-repeats-damage-without-repeating-the-action` pins the shape and `world/rules/tests/test_action_evidence.py` (incl. `test_ordered_hp_projection_and_single_defeat_entry`) covers it.
- **The conditional sibling's contract is the superset base**: resources/time/practice paid once per cast, both rolls retained, atomic rollback — the unconditional variant must reuse it verbatim with the evidence lookup removed.

User-ratified givens: **no second rules engine, no element-key branches in generic code** — the seam is a strict-superset MODIFIED delta on the shipped `DamagePolicy` validation + one boolean leg in the existing strike computation; the wind data (`gale_dance_strike`'s policy, MP/coefficient rows) belongs to `wind-spell-catalog`. **NON-GOAL: 遊戲資料契約** — verification is behavior contracts on synthetic skills through real settlement only; this change ships zero live rows. **Clean cut, zero users**: no migrations, no aliases.

## Goals / Non-Goals

**Goals:** Author extra-strikes-without-condition as legal `DamagePolicy` vocabulary; keep the evidence-conditional shape bit-identical; reuse the shipped ordered-HP-projection / dual-roll / single-terminal-emission settlement unchanged; behavior-test-only proof; the vocabulary element-agnostic (any element's future 多段 node rides it).

**Non-Goals:** No wind registry rows (`wind-spell-catalog` authors `gale_dance_strike`'s policy data); no `extra_strikes > 1` (the cap `{0,1}` stays — 「連續兩次判定」 is exactly 1+1, and a higher cap invites a per-strike practice/cost accounting redesign nobody asked for); no new `EVIDENCE_KINDS` members; no per-strike independent coefficients (same coefficient/policy both legs — the shipped shape); no `world/rules/targeting.py` or `spell_conditions` edits (displaced-gate territory, owned by `displaced-knockback`); no data-contract tests.

## Decisions

### D1 — Vocabulary: retire the unconditional rejection; `extra_strikes=1` with `repeat_when=None` means always-repeat

| Axis | retire-the-rejection (chosen) | `repeat_mode: "always"` enum field (rejected) |
|---|---|---|
| Superset honesty | the current rule 「extra_strikes > 0 requires repeat_when」 exists ONLY because no unconditional shape had a consumer; every policy legal today stays legal and identical — no shipped construction changes meaning | a second mode field must then pin `repeat_mode="evidence"` ⟺ `repeat_when is not None`, a redundant encoding of information already in the data |
| Grammar surface | zero new fields; the validation sentence narrows (delete one rejection; keep `extra_strikes ∈ {0,1}`; keep repeat_when⟹extra_strikes=1) | new closed enum on a frozen dataclass for a single boolean distinction |
| Settlement read | one boolean leg: `extra = extra_strikes > 0 and (repeat_when is None or has_action_evidence(...))` — the evidence lookup runs only for conditional policies | field dispatch on mode, same shape, more code |

Authoring shape for the wind node (catalog data): `DamagePolicy(extra_strikes=1)` (equivalently `extra_strikes=1, repeat_when=None`) on the `damage:wind:magic` component — 「兩次判定，無條件」. The `extra_strikes=None` normalization (`__init__` line 528-529: defaults to 1 iff repeat_when given) is unchanged: omitted stays 0, conditional keeps its default-1 ergonomics. `total_strikes = 1 + extra_strikes` replaces the hard-coded `2 if extra else 1` (identical while the cap holds — stated so a future cap widening has one arithmetic site).

Rejected alternatives: widening `extra_strikes` to 2+ (out of the lore ask, changes the strike-loop cap accounting contract); a boolean `always_repeat` (a second vocabulary word for `repeat_when=None and extra_strikes=1` — two ways to say one thing, drift risk); attaching the repeat to `EffectPolicy` (the repeat IS a damage-policy fact; the shipped requirement's home).

### D2 — Settlement: one boolean leg in the shipped extra-computation; every other guarantee inherited verbatim

`_handle_damage` computes (contract, not code): `extra = damage_policy is not None and damage_policy.extra_strikes > 0 and (damage_policy.repeat_when is None or has_action_evidence(target, repeat_when, now=now))`. Both legs of the existing loop are untouched: independent `roll_d100` per strike, same coefficient/policy (incl. predicates, `bypass_defense`/`unconditional_defense_bypass`, `max_hp_fraction`, divert staging) per strike, ordered HP projection through the staged pending applies, at most one terminal defeat/knockout emission, nonlethal flooring, atomic rollback restoring all HP and evidence, single payment/practice of the action. A miss on strike one never suppresses strike two (already the conditional semantics — the unconditional variant inherits the scenario verbatim minus the evidence precondition). The strike count stays deterministic-by-policy (no dice gate the repeat itself): 「連續兩次判定」 always rolls twice.

`has_action_evidence` remains imported/used only by the conditional branch — no evidence-store behavior changes (`recent-action-evidence` untouched).

### D3 — Validation matrix (fail-closed, strict superset)

`DamagePolicy.__post_init__` keeps every current rule and changes exactly one:

- `extra_strikes` ∈ {0, 1}, int-typed, boolean-rejected — unchanged.
- `repeat_when` ∈ `EVIDENCE_KINDS` (string-typed) — unchanged.
- `repeat_when is not None ⟹ extra_strikes == 1` — unchanged.
- ~~`extra_strikes > 0 ⟹ repeat_when is not None`~~ — RETIRED (the one rule deleted; `extra_strikes=1, repeat_when=None` now constructs and means unconditional dual-strike).

The shipped test `test_extra_strikes_without_repeat_when_raises` retires in-file with its requirement sentence (behavior-first convention; the superset replaces it with the acceptance behavior); every other pin in `test_conditional_damage`/`test_action_evidence` stays verbatim.

### D4 — Wave interface-ownership matrix

See `displaced-knockback` design.md D8 (single wave table; this change's row: 「unconditional extra-strike authoring vocabulary — first owner `unconditional-multi-strike`, consumer `wind-spell-catalog`」). File ownership: this change owns `world/skills/effects.py` (`DamagePolicy.__init__`/`__post_init__` + docstrings) and `world/rules/combat.py` (`_handle_damage`'s extra-computation hunk, lines ~360-366, + the `total_strikes` arithmetic) and the existing evidence/conditional-damage test modules' in-file updates; `displaced-knockback` owns everything else including `combat.py`'s `default_attack_policy` candidate filter — **shared file, disjoint functions ~400 lines apart; the supervisor sequences the two merges** (`displaced-knockback` first per the declared queue; either order applies cleanly — the hunks are textually disjoint, `combat.py` ~360 vs ~767). `.github/evennia-shards.json` is the wave's only other shared file.

### D5 — Verification contract (shared wave text in displaced-knockback design.md D10)

This change's own proof, all behavior on synthetic skills through real `_handle_damage`/action settlement: unconditional dual-strike lands two independent rolls (fixed-roll matrix: hit-hit, miss-hit, hit-miss, miss-miss), one payment/practice, both rolls recorded, ordered HP projection, single terminal defeat across a two-strike lethal crossing, nonlethal floors at 1 HP with one knockout, atomic rollback restores both strikes' HP, policy-free control skills stay single-strike, the conditional sibling behaves bit-identically (evidence present/absent/expired), construction accepts `extra_strikes=1` with no predicate and every other malformed combination still raises. New synthetic module(s) in exactly one shard; focused invocation per the wave contract.
