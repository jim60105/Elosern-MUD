## Why

`sexual-act-registry` (landed) and `sexual-act-effects` (landed) built the complete seam for a sex
act — the paired `SkillDef`/`SexualActDef` registration, the unlock query, `owned_keys()`
integration, and the `pleasure:`/`sexual_counter:`/`sexual_event:` effect machinery — but shipped
zero act content by design (`world/skills/sexual_acts/`'s six line modules all export empty tuples).
A player with a fresh character today has no sex act available at all, seeded or otherwise: every
line's first act is gated behind a non-empty `unlock` mapping in the catalog proposals that follow
this one, and until at least one act is unconditionally available, the catalog cannot be exercised
end-to-end outside the registry's own synthetic test act.

This proposal ships the seven seed acts the design set calls for: `unlock={}` acts spanning all
three targeting shapes (SELF, SINGLE, and a hostile-capable SINGLE) so every line except 異種 and
神之秘法 is enterable from the first round of play, before any catalog proposal lands.

## What Changes

- Add three solo-line seeds to `world/skills/sexual_acts/solo.py`'s `SOLO_ACTS` tuple: 自撫（私處）,
  揉捏胸部（乳房）, 摩擦大腿（大腿）. All `TargetSpec.SELF`, `unlock={}`.
- Add one shame-line seed to `world/skills/sexual_acts/shame.py`'s `SHAME_ACTS` tuple: 撩起衣襬
  （`TargetSpec.SELF`, `unlock={}`). This act raises the actor's own `exposure` field, which no
  currently-shipped `sexual.yaml` event exists to express — `sexual-act-effects`'s design.md
  disclosed this gap explicitly ("Exposure- and shame-raising acts... cannot be expressed through
  this proposal's mechanisms at all... the 羞恥線 catalog proposal must add its own `sexual.yaml`
  row(s) and event(s) when it lands"). This proposal is the first to need it, so it adds one new rule
  row, `exposure_up_on_self_exposure` (`{event: self_exposure}` → `{field: exposure, delta: "+1"}`),
  with its structurally-required matching test. `sexual-catalog-shame`'s nine remaining acts reuse
  this same event with no further rulebook change.
- Add two partner-line seeds to `world/skills/sexual_acts/partner.py`'s `PARTNER_ACTS` tuple: 愛撫
  （腰腹, `TargetSpec.SINGLE`, resistible）and 牽手交纏（`TargetSpec.SINGLE`, resistible, minimal
  pleasure — the non-coercive opener that lets a player raise a companion's affinity without ever
  forcing anything).
- Add one combat-line seed to `world/skills/sexual_acts/combat.py`'s `COMBAT_ACTS` tuple: 挑逗
  （腰腹, `TargetSpec.SINGLE`, resistible, low magnitude, `hostile_act_count` on the actor side）.
- No change to `interspecies.py` or `divine.py` — the design set's seed list deliberately excludes
  both lines (異種 has no natural unconditional opener since it requires a `Monster` target; 神之秘法
  is race-gated by `requires_divine_arts` regardless of counters, per `divine-sexual-arts`'s own
  scope).

## Capabilities

### New Capabilities
- `sexual-act-seeds`: the seven unconditionally-available seed acts, one per targeting shape spanned
  across four lines, plus the `exposure_up_on_self_exposure` rule they (and the following shame
  catalog) depend on.

### Modified Capabilities
- none — `sexual-act-registry` and `sexual-act-effects`'s existing requirements are exercised, not
  changed. `sexual-transition-rulebook`'s requirements (rule-loading mechanism, `apply_event()`
  contract) are likewise exercised unchanged by the one new rule row; no existing requirement text in
  that spec changes.

## Impact

- Code: `world/skills/sexual_acts/solo.py`, `shame.py`, `partner.py`, `combat.py`,
  `world/rules/rulebook/sexual.yaml` (one new row), `world/rules/tests/test_sexual_transitions.py`
  (one new `test_rule_exposure_up_on_self_exposure`), and one new test file,
  `world/skills/sexual_acts/tests/test_seed_acts.py` (the delta spec's ownership/resistible/counter
  scenarios have no other home — the rulebook test file covers only the `exposure`/`shame` cascade).
- No change to `world/skills/sexual_acts/_builder.py`, `__init__.py`, `interspecies.py`, `divine.py`,
  or any file outside this list — every structural invariant `sexual-act-registry`/
  `sexual-act-effects` already enforce is inherited unchanged and re-checked against real content for
  the first time.
- Player-facing: `docs/game/commands.md` and `docs/game/command-reference.md` gain no entries yet —
  cataloging every sex act's command surface is `sexual-act-docs`'s job once the full catalog lands;
  seven acts appearing mid-catalog would need immediate revision. Deferred deliberately (see
  design.md Non-Goals).
