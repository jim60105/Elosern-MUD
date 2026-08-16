## 1. Confirm the dependency surface this change reads and extends

- [x] 1.1 Confirm `world/skills/sexual_acts/_builder.py`'s `_act_family()` row-tuple shape is still
  `(key, label, description, target_spec, unlock, base_pleasure, actor_part, target_part,
  actor_pleasure_ratio, actor_counters, participant_counters, sexual_events, resistible)` and its
  structural checks (forbidden events, non-zero `actor_pleasure_ratio` unless divine, no
  `GENERIC_BODY_PART`, part membership, no target part for 異種/神之秘法) are unchanged from
  design.md's description. If the row shape has moved, re-derive design.md's D-1 table against the
  new shape before writing any act row.
- [x] 1.2 Confirm `SexualState`'s eleven counter attribute names and their sole mutators
  (`masturbation_count`→`record_masturbation()`, `exposure_act_count`→`record_exposure_act()`,
  `duo_act_count`→`record_duo_act()`, `hostile_act_count`→`record_hostile_act()`) are unchanged in
  `world/rules/sexual_state.py`.
- [x] 1.3 Confirm `resolve_part()` in `world/rules/sexual_act_effects.py` still collapses `None` to
  `GENERIC_BODY_PART` unconditionally (design.md D-3's dependency) and that
  `world/lore/sexual_vocab.py::BODY_PARTS` still excludes any hand-adjacent part (design.md D-4's
  dependency — if a hand part now exists, revisit `partner_hand_hold`'s part choice before writing
  it).
- [x] 1.4 Confirm `world/rules/rulebook/sexual.yaml`'s existing `shame_up_on_exposure_increase` rule
  (`{field_changed: exposure, direction: up}` → `{field: shame, delta: "+1"}`) and `FIELD_KINDS` in
  `world/rules/sexual_transitions.py` still include `exposure` as an ordered-level kind, so the new
  rule needs no `FIELD_KINDS` change.
- [x] 1.5 Confirm `world/rules/tests/test_sexual_transitions.py`'s `test_every_rule_id_has_a_test()`
  and `world/skills/sexual_acts/tests/test_registry_structure.py`'s structural checks are still
  present and passing on the current worktree HEAD before adding any new row (a pre-existing failure
  here is out of this change's scope and must be reported, not silently worked around).

## 2. `world/rules/rulebook/sexual.yaml` and its test

- [x] 2.1 Add the `exposure_up_on_self_exposure` rule row (design.md D-2) in the file's existing
  event-conditioned-rule style, placed near `exposure_up_on_clothing_damaged` for readability.
- [x] 2.2 Add `test_rule_exposure_up_on_self_exposure` to
  `world/rules/tests/test_sexual_transitions.py`, mirroring `test_rule_exposure_up_on_clothing_
  damaged`'s shape: call `apply_event(entity, "self_exposure")` and assert `exposure`'s ordinal rose
  by exactly one.
- [x] 2.3 Add a second test in the same module (or extend 2.2) asserting the cascade into `shame`
  within the same `apply_event()` call, per the delta spec's "cascades within the same call"
  scenario — construct an entity with `shame` below ceiling, call `apply_event(entity,
  "self_exposure")` once, and assert both `exposure` and `shame` moved.
- [x] 2.4 Run `uv run --locked evennia test --settings test_settings.py --keepdb
  world.rules.tests.test_sexual_transitions` and confirm the whole module passes, not just the two
  new tests.

## 3. `world/skills/sexual_acts/solo.py`: the three solo seeds

- [x] 3.1 Replace `SOLO_ACTS`'s empty tuple with `_act_family("獨處", <three rows>)` using design.md
  D-1's table for `solo_self_touch`, `solo_fondle_breasts`, and `solo_thigh_rub` verbatim (labels,
  descriptions, parts, `base_pleasure`, counters, events, `resistible=False`).
- [x] 3.2 Confirm the module still imports only `SkillDef`/`SexualActDef`/`_act_family` (no new
  imports needed for plain data rows).

## 4. `world/skills/sexual_acts/shame.py`: the shame seed

- [x] 4.1 Replace `SHAME_ACTS`'s empty tuple with `_act_family("羞恥", <one row>)` for
  `shame_hem_lift`, using `actor_part=None`, `target_part=None`, `sexual_events=("self_exposure",)`,
  per design.md D-1/D-3.

## 5. `world/skills/sexual_acts/partner.py`: the two partner seeds

- [x] 5.1 Replace `PARTNER_ACTS`'s empty tuple with `_act_family("關係", <two rows>)` for
  `partner_caress` and `partner_hand_hold`, both `TargetSpec.SINGLE`, `resistible=True`, both parts
  `"腰腹"` per design.md D-1/D-4.

## 6. `world/skills/sexual_acts/combat.py`: the combat seed

- [x] 6.1 Replace `COMBAT_ACTS`'s empty tuple with `_act_family("戰鬥", <one row>)` for
  `combat_tease`, `TargetSpec.SINGLE`, `resistible=True`, `actor_counters=("hostile_act_count",)`,
  `participant_counters=()`, per design.md D-1.

## 7. Behaviour tests for the delta spec

- [x] 7.1 Run `uv run --locked python -m tools.spec_traceability list` and note the canonical
  requirement IDs generated for `sexual-act-seeds::*` from this change's already-written delta spec
  (`specs/sexual-act-seeds/spec.md`).
- [x] 7.2 Add behaviour tests under `world/skills/sexual_acts/tests/` (new module, e.g.
  `test_seed_acts.py`, `EvenniaTest`-based since casting exercises `ActionResolver`) covering each
  delta-spec scenario: all seven seeds present in `owned_keys()` at zero counters;
  `interspecies`/`divine` stay `()`; each SELF seed's `resistible is False` and each SINGLE seed's
  `resistible is True`; `solo_*` increments `masturbation_count` on the actor only; only
  `solo_self_touch` adds `"自慰"` to `experience_types`; `partner_*` increments `duo_act_count` on
  both participants; `combat_tease` increments `hostile_act_count` on the actor only.
- [x] 7.3 Apply `covers_requirement("sexual-act-seeds::<id>")` (using the IDs from 7.1) to the test
  function whose assertions establish each requirement — one test may cover more than one scenario
  under the same requirement heading; do not annotate an unrelated or assertion-free test.
- [x] 7.4 Run `uv run --locked python -m tools.spec_traceability check` and confirm every
  `sexual-act-seeds` requirement is covered.

## 7.5 Collateral test updates (existing tests that pinned the empty-registry state)

Registering seven real acts changes every entity's `owned_keys()` and the assembled
`SKILL_REGISTRY`/`SEXUAL_ACT_REGISTRY` contents, which the following existing tests pinned to the
pre-content state. Update each so the whole suite stays green:

- [x] 7.5.1 `world/skills/sexual_acts/tests/test_registry_structure.py`:
  - `LineModuleTests.test_every_line_module_is_importable_and_empty` now asserts only
    `interspecies.py`/`divine.py` remain `()` and the four content modules are non-empty; its
    `covers_requirement` ID updates to the renamed `sexual-act-registry::the-six-line-modules-…-異種-and-神之秘法-remain-empty` requirement (see the delta spec's RENAMED section).
  - `OwnershipDriftGuardTests.test_owned_keys_matches_base_owned_keys_when_nothing_is_unlocked`
    asserts `unlocked_act_keys() == frozenset()` and `owned_keys() == ["fire_ball", "flee",
    "basic_attack"]` — with seven seeds unconditionally unlocked these are now false; rework to
    assert the seven seed keys appear and `owned_keys()` is base plus the sorted seed keys.
  - `test_registries_agree_with_zero_acts_registered` still passes (the agreement check is
    registry-derived) — confirm, and rename only if its name becomes misleading.
- [x] 7.5.2 `world/skills/tests/test_handler.py`: `owned_keys()` equality assertions
  (`["flee", "basic_attack"]`, `["fire_ball", "defense_instinct", "flee", "basic_attack"]`, and the
  bare-monster `before` list) gain the seven sorted seed keys.
- [x] 7.5.3 `world/skills/tests/test_inventory.py`:
  `test_imported_inventory_and_private_handler_storage_are_reflected`'s `owned_keys()` equality
  gains the seven sorted seed keys.
- [x] 7.5.4 `world/rules/tests/test_combat_session.py`: `InnateSkillTests`' two `owned_keys()`
  equality assertions gain the seven sorted seed keys.
- [x] 7.5.5 `world/rules/tests/test_status_query.py`: `CharacterReadModelTests`' `active_keys`
  equality assertions (the seeds are ACTIVE-kind, so they land in `active_keys`) gain the seven
  sorted seed keys.
- [x] 7.5.6 `world/rules/tests/test_combat_view.py`:
  `test_skills_follow_handler_order_and_exclude_passives`' exact key list gains the seven sorted
  seed keys (they are ACTIVE, so the panel renders them).
- [x] 7.5.7 `world/rules/tests/test_cast_settlement.py`:
  `test_catalog_actives_are_exactly_the_declared_seven` — the ACTIVE+out-of-combat set now also
  contains the seven seeds; update the expected set (and the constant/comment if it names the count).
- [x] 7.5.8 `world/rules/tests/test_sexual_unlock.py`:
  `test_conferred_mastery_grant_does_not_unlock_the_catalogue` asserts
  `unlocked_act_keys() == frozenset()` — with seeds unconditionally unlocked it is now false; assert
  instead that the gated synthetic act stays absent (and optionally that the seven seeds are
  present), preserving the test's point about conferred grants.
- [x] 7.5.9 `world/skills/tests/test_registry.py`: the D4 classification table's `SEXUAL_ACT`
  expected set gains the seven seed keys, and its `covers_requirement` IDs update to the renamed
  `skill-category-registry::skill-registry-s-entries-partition-…` requirement (see the delta spec's
  RENAMED section).
- [x] 7.5.10 `web/webclient/presentation/tests/test_character_panel.py`: the two `actives`
  `_flattened_keys` equality assertions gain the seven seed keys.
- [x] 7.5.11 `web/tests/browser/test_browser_combat.py`:
  `test_panel_groups_skills_by_category_in_enum_order` — the seeded character now owns a
  `sexual_act` category, so the expected category list gains `"sexual_act"` (with the four line
  sub-groups); re-run this browser file after the update.
- [x] 7.5.12 Latent-gap fix surfaced by real content: the combat panel protocol validator rejected
  the act catalog's Traditional Chinese line-name sub-group keys (the `webclient-combat-menu`
  contract requires only a nullable group key). Update
  `web/webclient/presentation/combat_panel.py` and its JS mirror
  `web/static/webclient/js/elosern/protocol.js` to accept a bounded non-empty string group key
  (mirroring the character panel, and rejecting empty/whitespace keys in both mirrors), and add
  acceptance tests for a Chinese group key and for empty-key rejection in both
  `web/webclient/presentation/tests/test_combat_panel.py` and
  `web/static/webclient/js/tests/protocol.test.js`.
- [x] 7.5.13 Latent-gap fix surfaced by real content: SINGLE-target sex acts must reject the actor
  as target. Evennia's object search resolves `self`/`me`, so `cast partner_caress = self` would
  otherwise credit `duo_act_count`/`hostile_act_count` with no second party. Add the rejection to
  `world/rules/targeting.py::resolve_targets` (shared by the combat and out-of-combat cast paths),
  extend the `sexual-act-seeds` delta spec with the self-cast requirement and its two scenarios,
  and add regression tests in `world/skills/sexual_acts/tests/test_seed_acts.py` asserting both
  rejection and zero counter credit.

## 8. Full verification

- [x] 8.1 Run `uv run --locked evennia test --settings test_settings.py --keepdb world.skills.tests
  world.rules.tests world.webclient` and confirm the whole package suite passes, including
  `test_registry_structure.py`, `test_acceptance.py`, and the collateral updates against the
  now-non-empty registry.
- [x] 8.2 Run `uv run --locked python -m compileall -q world` to catch any syntax error the above
  test run would not otherwise isolate cleanly.
- [x] 8.3 Run `openspec validate sexual-act-seeds --strict` and resolve any reported issue.
- [x] 8.4 Confirm no file outside `world/rules/rulebook/sexual.yaml`,
  `world/rules/tests/test_sexual_transitions.py`, `world/rules/targeting.py` (the self-cast
  rejection from 7.5.13), `world/skills/sexual_acts/{solo,shame,partner,
  combat}.py`, the new `world/skills/sexual_acts/tests/test_seed_acts.py`, the collateral test
  files listed in 7.5, the main-spec sync (new `openspec/specs/sexual-act-seeds/spec.md`, and the
  RENAMED+MODIFIED headings in `openspec/specs/sexual-act-registry/spec.md` and
  `openspec/specs/skill-category-registry/spec.md`, following the implementation-time sync pattern
  of B5/B6a), and this change's own `openspec/changes/sexual-act-seeds/` artifacts was touched —
  matching the proposal's declared Impact list (including its collateral section) exactly.
