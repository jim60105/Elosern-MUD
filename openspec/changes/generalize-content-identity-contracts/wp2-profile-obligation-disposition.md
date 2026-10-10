# WP2 one-time profile-obligation disposition (task 2.1)

Baseline `master` = `fbfd20ab8755a44cf4fc3d12362a70d345d912f0`; WP1 left the branch at
`72f6d0f7`. This is implementation migration evidence recorded once, **not** a permanent expected-key
fixture and **not** a new approval table: the per-row facts below are re-derived from the live
registry in every test run, and nothing here is copied into an assertion.

Command used to produce every value in this file (read-only, run from the worktree):

```sh
uv run --locked python - <<'PY'
# old rows: ast-parse `git show 72f6d0f7:world/lore/monster_species.py`
# new rows: import world.lore.monster_species, read MONSTER_VARIANT_REGISTRY
PY
```

## 1. Before/after obligation per shipped variant

Before this change the twelve rows' obligation was implicit: a closed twelve-key test table
(`APPROVED_VARIANTS`) asserted every one of them carried a complete profile and a grade. After it,
each row declares that obligation itself.

| Variant | Before (implicit) | After (declared) | Kit |
| --- | --- | --- | --- |
| `bank_lurker` | complete profile, grade `D` | `profile_required=True`, complete profile, grade `D` | `tide_devouring_bite` + `ambush_predator` |
| `bay_warden` | complete profile, grade `C` | `profile_required=True`, complete profile, grade `C` | `tide_devouring_bite` + `ambush_predator` |
| `burrow_maker` | complete profile, grade `F` | `profile_required=True`, complete profile, grade `F` | none |
| `cliff_stepper` | complete profile, grade `D` | `profile_required=True`, complete profile, grade `D` | none |
| `flock_leader` | complete profile, grade `E` | `profile_required=True`, complete profile, grade `E` | `grain_shaking_peck` + `instinctive` |
| `grain_pecker` | complete profile, grade `F` | `profile_required=True`, complete profile, grade `F` | `grain_shaking_peck` + `instinctive` |
| `nest_guard` | complete profile, grade `E` | `profile_required=True`, complete profile, grade `E` | none |
| `pass_warden` | complete profile, grade `C` | `profile_required=True`, complete profile, grade `C` | none |
| `reef_warden` | complete profile, grade `E` | `profile_required=True`, complete profile, grade `E` | `lamp_carapace_claw` + `instinctive` |
| `shore_walker` | complete profile, grade `F` | `profile_required=True`, complete profile, grade `F` | `lamp_carapace_claw` + `instinctive` |
| `trail_hunter` | complete profile, grade `C` | `profile_required=True`, complete profile, grade `C` | none |
| `wood_stalker` | complete profile, grade `D` | `profile_required=True`, complete profile, grade `D` | none |

Observed results of the derivation: 12 rows before and after; "all complete + graded before" `True`;
"all `profile_required` after" `True`. Every one of the twelve previously required rows is still
required, and every profile literal, grade, threat tier, ordinary/stronger classification, kit and
behaviour binding is **byte-identical** to the baseline (the run reported zero profile/grade
mismatches, zero tier/ordinary mismatches, and the same six species keys). No balance value moved and
no new approval fixture was added.

## 2. Closed tables removed (by file and symbol, not by count)

| Removed symbol | Where | Replacement |
| --- | --- | --- |
| `APPROVED_SPECIES` | `world/lore/tests/test_monster_species_content.py` | live iteration of `MONSTER_SPECIES_REGISTRY` |
| `APPROVED_VARIANTS` | same | live iteration of `MONSTER_VARIANT_REGISTRY` |
| `test_the_registry_carries_the_six_approved_species_and_no_others` | same | `test_every_shipped_species_declares_its_key_and_public_narrative` |
| `test_the_registry_carries_the_twelve_approved_variant_directions` | same | `test_every_shipped_variant_declares_its_key_owner_display_and_tier` |
| `test_every_variant_is_an_ordinary_or_stronger_form_of_one_species` (pinned exactly two variants per species) | same | `test_every_variant_is_owned_and_every_species_default_is_its_baseline` (membership total both ways, no count) |
| `test_each_species_baseline_is_its_own_ordinary_variant` | same | merged into the ownership/default-membership test above |
| the per-variant `delivered = {...}` tuple map | same, `AbilitySeamNegativeTests` | delivery read from each row's own `active_skill_keys` / `passive_skill_keys` / `behaviour_profile_key` |

`test_every_declared_required_row_carries_a_complete_profile_and_grade` and
`test_every_shipped_profile_and_grade_lies_inside_its_declared_tier_band` now iterate the live
registry; the second one is still an independent reading (it does not call the registry's own
validator), so a validator that stopped checking still fails there.

## 3. Legitimate optional absence, and its surviving carriers

`profile_required=False` remains a legal declaration, and the retired requirement's
"`None` retains optional-source semantics outside the required profiled set" clause keeps direct
coverage after the cutover:

- `world/lore/tests/test_monster_species_registry.py::ProfileObligationTests.test_an_optional_row_keeps_the_absence_semantics`
  accepts a synthetic row with `profile_required=False` and no profile or grade, and also a row that
  carries a profile it does not require.
- `...::test_a_required_row_missing_a_profile_or_grade_is_rejected` and
  `...::test_a_non_boolean_obligation_is_rejected` are the negative halves.
- `...::test_a_valid_add_rename_and_retirement_keeps_the_registry_valid` is the "valid content edit"
  scenario: add, rename, retire-and-repoint all validate, while the un-repointed retirement fails.
- Synthetic rows that actually exercise absence in shipped-shaped data:
  `world/tests/synthetic_data/data_monster_species.py::SYNTH_MONSTER_VARIANTS["t_whisper_quail_ordinary"]`
  (`False`, no profile, no grade) and `world/lore/tests/test_monster_placement.py::_variant_row`.
- The tier-band fallback branch of the shipped construction check
  (`ApprovedProfileConstructionTests.test_every_shipped_variant_constructs_an_individual_with_those_values`)
  is written against the contract rather than against today's data, so a future optional row is
  checked without editing the test. The fallback itself is exercised with synthetic rows in
  `world/rules/tests/test_monster_individual.py`.

## 4. Assertion review for the retained field-set pin

`world/lore/tests/test_monster_species_registry.py::RecordShapeTests.test_the_declared_field_sets_are_exactly_the_contract`
keeps its exact-equality pin and now names `profile_required` alongside the other eleven variant
fields. The retained "complete standalone record" semantics are unchanged: a declared obligation is
not an override/merge field, so the `INHERITANCE_FIELDS` and `ABILITY_BASELINE_FIELDS` intersection
pins stay empty (asserted by the two neighbouring tests).

`world/lore/tests/test_registry_index_contract.py` was re-derived: `profile_required` is a plain
boolean with no `ref()` metadata, so `FIRST_BATCH`'s declared-reference set,
`EXPECTED_DEFAULTS` and the summary fields are unchanged, and no count pin (or any pin at all) was
added there.

The retained `monster-species-registry::species-and-variant-registries-are-frozen-keyed-read-only-lore-data`
scenario enumerates the fields the variant dataclass *declares*; adding a declared obligation field
removes none of them, so the retained requirement needs no delta and none was added.

## 5. Retargets performed by WP2, and the scope line held with WP3

Retired ids re-attached by this package (D3), each to the effective requirement its assertions
actually establish:

| Retired id | Re-attached to |
| --- | --- |
| `monster-species-registry::numeric-combat-profiles-and-danger-grades-are-balance-gated-slots-never-invented-values` | `monster-species-registry::authored-profile-requirements-are-declared-per-variant` |
| `monster-species-registry::the-approved-first-batch-profiles-and-grades-are-user-approved-literals` | `monster-species-registry::shipped-profile-completeness-follows-authored-declarations` |
| `monster-species-registry::special-abilities-are-narrative-boundaries-with-a-named-mechanics-prerequisite-never-fake-skills` | `monster-species-registry::narrative-and-executable-monster-configurations-remain-separate` |
| `monster-species-registry::approved-bestiary-narrative-lands-as-zh-tw-display-strings-and-synchronizes-idempotently` | `monster-species-registry::authored-monster-narratives-synchronize-without-a-fixed-roster` |
| `monster-individual-construction::穗鳴雀-construction-persists-both-approved-contact-kits` | `monster-individual-construction::shipped-variants-construct-their-declared-configuration-through-the-common-boundary` |
| `monster-individual-construction::潮燈蟹-construction-persists-both-approved-contact-kits` | same |
| `monster-resource-abilities::crocodile-bite-is-one-authored-shared-engine-physical-resource-skill` | `monster-resource-abilities::monster-ability-identity-and-composition-are-authored-registry-data` |
| `monster-resource-abilities::穗鳴雀-owns-its-approved-contact-resource-ability` | same |
| `monster-resource-abilities::潮燈蟹-owns-its-approved-contact-resource-ability` | same |

Two deliberate deviations from `cutover-matrix.md` Matrix B's *candidate* id list, both because the
annotation is a claim and must name what the site actually establishes:

1. `test_the_published_narrative_is_the_approved_zh_tw_prose`,
   `test_the_author_private_notes_keep_the_unknown_origin_boundary`,
   `test_every_published_string_is_verbatim_approved_prose_in_order` and the four
   `MonsterSpeciesSyncTests` mirror cases are attached to
   `monster-species-registry::authored-monster-narratives-synchronize-without-a-fixed-roster` only.
   The candidate list also offered
   `monster-resource-abilities::bestiary-documentation-covers-keyed-public-content-relationships`,
   whose statement is about *keyed documentation relationships* — a claim these prose comparisons do
   not establish (they currently do the opposite, comparing sentences). That id's direct coverage
   belongs to the keyed bestiary checker, which is a later package's deliverable.
2. `test_the_author_private_notes_keep_the_unknown_origin_boundary` was listed against the bestiary
   documentation id; its assertions are about the registry's public/private narrative fields, so it
   is attached to the narrative requirement instead.

Scope line held with the bestiary package: the approved-sentence constants
(`APPROVED_ABILITY_LIMITS`, `APPROVED_CONTACT_CLAUSES`) and the `_normalised` / `_sentences`
comparison helpers stay in place, with a comment naming the keyed bestiary relationship checker as
what replaces them. That package's task removes the prose fixtures and adds the checker; WP2 only
rebased their iteration onto the live registries and re-attached their annotations, so no coverage
window is opened by this package.

## 6. Ledger/metadata edit path, and a conflict between two recorded rules

The two carried reasons this package changed
(`world/lore/tests/test_monster_species_content.py`,
`world/skills/tests/test_skill_registry/test_registry_contract.py`) were changed in all three places
at once: the file's first docstring line, `tools/test_data_lint_seed.json`, and
`tools/test_data_freeze.json`. `uv run --locked python -m tools.test_data_lint check` reports
`violations=0` with a two-line ledger diff.

The ledger was **not** regenerated with `tools.test_data_lint seed`, and the reason is itself a
conflict between two recorded rules:

* `metadata-map.md` rule 5 (as amended in `00015605`) says to regenerate the ledger with that command
  and not to hand-edit it.
* `metadata-map.md` rule 6, and its Table C entry for `world/rules/tests/test_buffs.py`, forbid the
  move that regeneration performs: the tool rebuilds `contract` from the seed, which is missing that
  one pre-existing contract entry, so regenerating moves it from `contract` to `debt` — "never the
  reverse by reason of this cutover" — and rewrites the whole 470-entry ledger (356 insertions / 38
  deletions in the working tree, reordered).

The regenerating path therefore cannot be taken without breaking rule 6 and reopening the
asymmetry WP1 recorded for exactly this reason. The surgical three-place edit satisfies the gate,
keeps the diff to the two reasons, and leaves the ledger/seed asymmetry exactly as WP1 recorded it.
This is called out for WP7, which owns the integrated gate, in case the project prefers to resolve
the rule conflict the other way at that point.

## 7. WP2 post-implementation review, every finding and disposition

One blocking whole-diff review ran over the four WP2 commits with the effective-id catalogue,
WP1's planning artifacts and the focused suite results. It found no false annotation claim that
leaves a requirement unestablished, and confirmed that every assertion deleted with the three
species skill tests has another carrier. Its findings and dispositions:

| Id | Finding | Disposition |
| --- | --- | --- |
| B1 | The all-kit loop enumerated both slots but asserted active-only shape (non-empty cost, truthy cost tier, non-`NONE` target) for every reference, so a future authored passive kit skill would fail a valid content edit. | **Adopted.** Target shape, payment channels and cost tier are now asserted only for the active slot; faction constraint, typed parsed effects, policy parallelism, the freeform-shape gate and prerequisite closure stay unconditional. No passive-only pin was added in its place. |
| B2 | `allowed_species` was only checked as a subset, so widening a kit skill across two kit-declaring species passed silently, and the deleted exact equality had no other carrier. | **Adopted.** The test now derives, per skill, the set of species whose variants declare it and asserts equality against `allowed_species`; the derivation is registry data, not a roster, so no per-species tuple returns. |
| N1 | The new fault matrix lacked unknown-skill-key and unknown-behaviour-profile cases; those lived only in the older, unprobed test. | **Adopted.** Both are now entries in the matrix and get the same "no object created" probe. |
| N2 | The retained bestiary prose tests index `APPROVED_ABILITY_LIMITS` / `APPROVED_CONTACT_CLAUSES` by live registry key, so adding a species raises `KeyError` inside the test. | **Accepted as the documented interim state.** Those constants and their comparison helpers are the bestiary package's removal target (task 3.4); until then a species add fails loudly rather than silently skipping the narrative check. It is recorded here so the deferred `KeyError`-as-signal semantics are not mistaken for drift. |
| N3 | `monster-resource-abilities::bestiary-documentation-covers-keyed-public-content-relationships` has no test carrier after WP2. | **Accepted deferral.** Its direct coverage is the keyed bestiary checker (task 3.4). WP7's zero-carrier acceptance must fail if that carrier does not land. |
| N4 | The audience annotation on the kit test rested on an `isinstance` check that the definition class already enforces. | **Adopted.** The audience half now also asserts that a declared audience never turns the skill into an enemy- or ally-restricted one, and that a hit-qualified rider is never routed to the ally or caster pools. The id stays on the test. |
| N5 | The construction test's single branch would crash (`db.skills` is `None`) on a row that binds a behaviour profile without declaring a kit. | **Adopted.** The kit assertions and the binding assertions are now gated on their own declarations. |
| N6 | The class name still read `ApprovedProfileConstructionTests` after the approved-literal basis was removed. | **Adopted.** Renamed to `ShippedProfileConstructionTests`; the cross-reference in the seam tests was updated with it. |
