## 1. Confirm the dependency surface this change reads

- [ ] 1.1 Confirm `sexual-act-seeds` has landed with `PARTNER_ACTS` containing exactly
  `partner_caress` and `partner_hand_hold`, both `TargetSpec.SINGLE`, both crediting
  `duo_act_count` in `actor_counters` and `participant_counters`.
- [ ] 1.2 Confirm `world/rules/sexual_state.py`'s `duo_act_count`/`group_act_count`/`climax_count`
  and their sole mutators (`record_duo_act`, `record_group_act`, `record_climax_count`) are
  unchanged, and that `climax_count` is credited only by the climax-settlement clock
  (`sexual_state.py`, the `record_climax_count()` call site near its `climax_turns` bookkeeping),
  never by an act's own `actor_counters`.
- [ ] 1.3 Confirm `_act_family()`'s structural requirement that a non-`SELF`/`NONE`, non-異種/
  神之秘法 act declares a non-null `target_part` is unchanged — this proposal's three `AREA` rows
  depend on it (and on `target_part="腰腹"` being a valid `BODY_PARTS` member, which it already is).
- [ ] 1.4 Confirm `world/rules/rulebook/sexual.yaml`'s `experience_titfuck_added` row
  (`when: {event: breast_sex_performed}` → `then: {field: experience_types, add: 乳交}`) is
  unchanged. If its event name differs at implementation time, update `partner_breast_sex`'s
  `sexual_events` tuple accordingly before writing any row.
- [ ] 1.5 Confirm `_handle_sexual_event`'s target-only application (`world/rules/action.py`,
  `_handle_sexual_event` looping over its `targets` parameter rather than
  `participants(actor, targets)`) is still the case. If a prior proposal has already fixed this,
  update design.md D-3 and this change's tests to assert the corrected (actor-inclusive) behavior
  instead of the currently-shipped one.

## 2. `world/skills/sexual_acts/partner.py`: Tier 1 (four acts)

- [ ] 2.1 Extend `PARTNER_ACTS`'s `_act_family("關係", ...)` call with the four Tier 1 rows from
  design.md D-1 (`partner_kiss`, `partner_neck_caress`, `partner_breast_play`,
  `partner_ear_whisper`), each `unlock={"duo_act_count": 5}`, `target_spec=TargetSpec.SINGLE`,
  `actor_pleasure_ratio=0.5`, `actor_counters=("duo_act_count",)`,
  `participant_counters=("duo_act_count",)`, `sexual_events=()`, `resistible=True`, with
  `actor_part == target_part` per the table.

## 3. `world/skills/sexual_acts/partner.py`: Tier 2 (five acts)

- [ ] 3.1 Add `partner_deep_caress`, `partner_oral_service`, `partner_thigh_rub`, and
  `partner_foot_service` (`unlock={"duo_act_count": 15}`, otherwise matching Tier 1's shape).
- [ ] 3.2 Add `partner_breast_sex` (`unlock={"duo_act_count": 15}`,
  `sexual_events=("breast_sex_performed",)`, otherwise matching Tier 2's shape).

## 4. `world/skills/sexual_acts/partner.py`: Tier 3 (two acts)

- [ ] 4.1 Add `partner_anal_sex` (`unlock={"duo_act_count": 30, "climax_count": 10}`,
  `target_spec=TargetSpec.SINGLE`, `actor_part=target_part="後庭"`, `base_pleasure=26`,
  `actor_pleasure_ratio=0.6`, `actor_counters=("duo_act_count",)`,
  `participant_counters=("duo_act_count",)`, `sexual_events=()`, `resistible=True`).
- [ ] 4.2 Add `partner_mutual_masturbation` (same unlock, `actor_part=target_part="私處"`,
  `base_pleasure=18`, `actor_pleasure_ratio=1.0`, otherwise matching 4.1's shape).

## 5. `world/skills/sexual_acts/partner.py`: Tier 4 (three AREA acts)

- [ ] 5.1 Add `partner_group_caress` (`unlock={"duo_act_count": 30}`,
  `target_spec=TargetSpec.AREA`, `actor_part=None`, `target_part="腰腹"`,
  `actor_pleasure_ratio=0.5`, `base_pleasure=18`, `actor_counters=("group_act_count",)`,
  `participant_counters=("group_act_count",)`, `sexual_events=()`, `resistible=True`).
- [ ] 5.2 Add `partner_group_orgy` (`unlock={"group_act_count": 15}`, `base_pleasure=20`,
  otherwise matching 5.1's shape).
- [ ] 5.3 Add `partner_group_service` (`unlock={"group_act_count": 30}`, `base_pleasure=22`,
  otherwise matching 5.1's shape).

## 6. Behaviour tests for the delta spec

- [ ] 6.1 Run `uv run --locked python -m tools.spec_traceability list` and note the canonical
  requirement IDs for `sexual-catalog-partner::*` from this change's delta spec.
- [ ] 6.2 Add `world/skills/sexual_acts/tests/test_partner_catalog.py` (new `EvenniaTest`-based
  module) covering each delta-spec scenario: a Tier 1 act absent below threshold and present at it;
  `partner_anal_sex`'s compound gate; `partner_group_orgy` gated by `group_act_count` alone; every
  Tier 1-3 act crediting `duo_act_count` on both the actor and the target; every Tier 4 act
  crediting `group_act_count` (not `duo_act_count`) on every participant; `partner_breast_sex`
  emitting `breast_sex_performed` and no other new act naming that event;
  `compute_pleasure_gain`'s target-side and actor-side comparison between `partner_anal_sex` and
  `partner_mutual_masturbation` at `participant_count == 2` and baseline sensitivity/shame (D-4's
  baseline trade-off, pinned numerically — not a claim of dominance-freedom under sensitivity
  divergence, per D-4's corrected reasoning); all three Tier 4 acts declaring
  `target_part == "腰腹"` and `target_spec == TargetSpec.AREA`; every one of the fourteen acts
  declaring `resistible=True`; the fourteen new keys are disjoint from every key already in
  `SEXUAL_ACT_REGISTRY` before this change.
- [ ] 6.3 Add one test (not in the delta spec, a design.md D-3 regression) proving
  `partner_breast_sex`'s cast currently credits `乳交` to the experience-type set of the *chosen
  target only*, not the actor — pinning the presently-shipped, disclosed asymmetry so a future
  `_handle_sexual_event` fix is a deliberate, visible behavior change rather than a silent one.
- [ ] 6.4 Apply `covers_requirement("sexual-catalog-partner::<id>")` (using the IDs from 6.1) to
  each test function whose assertions establish that requirement.
- [ ] 6.5 Run `uv run --locked python -m tools.spec_traceability check` and confirm every
  `sexual-catalog-partner` requirement is covered.

## 7. Full verification

- [ ] 7.1 Run `uv run --locked evennia test --settings test_settings.py --keepdb world.skills.tests
  world.rules.tests` and confirm the whole package suite passes, including
  `test_registry_structure.py` and `test_acceptance.py` against the now-sixteen-row `PARTNER_ACTS`
  tuple.
- [ ] 7.2 Run `uv run --locked python -m compileall -q world`.
- [ ] 7.3 Run `openspec validate sexual-catalog-partner --strict` and resolve any reported issue.
- [ ] 7.4 Confirm no file outside `world/skills/sexual_acts/partner.py` and the new
  `world/skills/sexual_acts/tests/test_partner_catalog.py` was touched, matching the proposal's
  Impact list exactly — in particular, confirm `world/rules/action.py` and `world/rules/rulebook/
  sexual.yaml` both have zero diff from this change.
