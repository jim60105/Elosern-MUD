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
- `sexual-act-registry`'s six-modules requirement is renamed and restated: the four content modules
  now carry the seed rows registered by this change while `異種` and `神之秘法` remain empty —
  the original heading ("each exporting an empty tuple") is no longer true once this change lands.
  The registries-agreement, part, counter, event, and ownership requirements are exercised, not
  changed.
- `skill-category-registry`'s partition requirement is renamed to drop the hardcoded "117 entries"
  count from its heading — this change registers seven more `SEXUAL_ACT` skills (117 → 124), and
  the count will keep moving as the catalog proposals land. The partition property itself is
  unchanged.
- `sexual-transition-rulebook`'s requirements (rule-loading mechanism, `apply_event()` contract) are
  exercised unchanged by the one new rule row; no existing requirement text in that spec changes.

## Impact

- Code: `world/skills/sexual_acts/solo.py`, `shame.py`, `partner.py`, `combat.py`,
  `world/rules/rulebook/sexual.yaml` (one new row), `world/rules/tests/test_sexual_transitions.py`
  (one new `test_rule_exposure_up_on_self_exposure` plus a shame-cascade companion), and one new
  test file, `world/skills/sexual_acts/tests/test_seed_acts.py` (the delta spec's
  ownership/resistible/counter scenarios have no other home — the rulebook test file covers only the
  `exposure`/`shame` cascade).
- Collateral test updates (required because registering real acts into `SKILL_REGISTRY` changes
  every entity's `owned_keys()` and the assembled registry contents, which existing tests pinned to
  the pre-content state): `world/skills/sexual_acts/tests/test_registry_structure.py`,
  `world/skills/sexual_acts/tests/test_acceptance.py` (stale docstring only),
  `world/skills/tests/test_handler.py`, `world/skills/tests/test_inventory.py`,
  `world/rules/tests/test_combat_session.py`, `world/rules/tests/test_status_query.py`,
  `world/rules/tests/test_combat_view.py`, `world/rules/tests/test_cast_settlement.py`,
  `world/rules/tests/test_sexual_unlock.py`, `world/skills/tests/test_registry.py`,
  `web/webclient/presentation/tests/test_character_panel.py`, and
  `web/tests/browser/test_browser_combat.py`.
- One latent-gap fix surfaced by registering real acts (predicted by design.md's Risk section):
  the combat panel protocol validator required ASCII identifiers for skill sub-group keys, but the
  act catalog — and the pre-existing `divine_sexual_arts` — key sub-groups by Traditional Chinese
  line names (`獨處`, `羞恥`, `關係`, `戰鬥`). The webclient-combat-menu contract only requires a
  nullable group key; the validator now accepts a bounded non-empty string (rejecting
  empty/whitespace keys in both mirrors), mirroring the character panel. Touched files:
  `web/webclient/presentation/combat_panel.py`,
  `web/static/webclient/js/elosern/protocol.js`, `web/webclient/presentation/tests/test_combat_panel.py`,
  and `web/static/webclient/js/tests/protocol.test.js`.
- One more latent-gap fix surfaced by the same condition: a SINGLE-target sex act could be
  self-cast (Evennia's object search resolves `self`/`me`), crediting two-participant counters
  (`duo_act_count`, `hostile_act_count`) with no second party. `world/rules/targeting.py::resolve_targets`
  — the shared seam for both the combat and out-of-combat cast paths — now rejects the actor as
  target for `SEXUAL_ACT`-category SINGLE-target skills, with regression tests in
  `world/skills/sexual_acts/tests/test_seed_acts.py` and a new delta-spec requirement.
- No change to `world/skills/sexual_acts/_builder.py`, `__init__.py`, `interspecies.py`, `divine.py`,
  `world/skills/handler.py`, `world/rules/action.py`, or any other production file — every
  structural invariant `sexual-act-registry`/`sexual-act-effects` already enforce is inherited
  unchanged and re-checked against real content for the first time.
- Player-facing: `docs/game/commands.md` and `docs/game/command-reference.md` gain no entries yet —
  cataloging every sex act's command surface is `sexual-act-docs`'s job once the full catalog lands;
  seven acts appearing mid-catalog would need immediate revision. Deferred deliberately (see
  design.md Non-Goals).
