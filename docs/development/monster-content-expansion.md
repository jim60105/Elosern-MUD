# Monster Content Expansion: Developer Review and Evidence

This document records the developer review and observed evidence for the monster
content expansion design
(`docs/superpowers/specs/2026-11-03-monster-content-expansion-design.md`). It is
not a balance approval table and it never duplicates the authored literals:
every magnitude lives once in its executable declaration under
`world/lore/monster_species.py`,
`world/skills/registry/data_monster_abilities.py` and
`world/rules/rulebook/`.

## 泥膜史萊姆

The first delivered weak species of the batch is 泥膜史萊姆 (`mudfilm_slime`)
with its ordinary default variant 濕岸型 (`mudbank_dweller`): a low-tier,
grade-F, slow defensive individual whose only active is the self film guard
泥膜收束 (`mudfilm_guard`).

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table. The complete literal
profile and its authored grade live only in `world/lore/monster_species.py`
and are band-checked at import.

* The profile lies wholly inside the low tier's declared bands. The hit-point
  pool sits inside the low band and near its comfortable middle, so a created
  character's single strike is a small fraction of it; the physical attack is
  a modest contact impact inside the low attack band.
* Slow means the authored agility is no greater than the lowest agility among
  shipped low-tier ordinary variants (the crab's), and the slime takes the low
  band's floor.
* Defensive means the authored defense is no lower than the highest defense
  among shipped low-tier ordinary variants (again the crab's), and the slime
  sits well above it while remaining inside the low defense band.
* `magic_power` is the only value the tier band admits, and the kit spends no
  MP, so the authored MP pool is zero.
* The authored SP pool holds at least two casts of the guard's positive SP
  cost, so a refresh of an aged mount is observable.
* The short film guard raises the caster's defense by no more than the largest
  shipped low-tier self-guard contribution, and its lifetime is of the same
  order as the shipped self guards `lamp_carapace_guard` and `ridge_brace`.

### Intelligence rationale

`mudbank_dweller` authors intelligence 20 and binds the utility decision. The
authoring rationale is the behaviour itself: it tightens its film only when
pressed and bumps back at short range, so reflexive self-protection is the
least decision depth of the activated set — below `trail_hunter` (44),
`flock_leader` (58) and `reef_warden` (66). The value is read from this
variant's own lore, never from its tier, grade, stats or archetype, and it adds
no statistic, resource, kit or proficiency.

### Known flee trade-off

The legacy decision body never proposes a support active, so this variant binds
utility; under `monster-flee-policy` a utility monster never flees voluntarily.
That is the deviation design §12.4 records from §5's available innate flee and
§7.1's retreat orientation for the slime, the rat and the crocodile boss. For
this species the retreat orientation is expressed instead through its passive
field aggression in `weak-species-habitats`, and the opposing party's paid
retreat remains available. The goblin and the boar stay legacy and keep their
own flee thresholds.

### Non-gating observations

Observed with `uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_tmp_observation_probe`
(a temporary probe module, deleted after the run), a 20-decision short
inspection run of the shipped policy (each iteration lowers the actor's current
hit points by one, so the snapshot-derived selector seed differs), in a real
battlefield holding the constructed representative, one real player opponent
and one constructed control individual. This is an observation, not a test:

* Candidate count: 2 in every decision (the owned guard and the innate basic
  attack), with 2 scored plans in every decision.
* Exclusions and unavailable skills: none.
* Selection over the short run: `basic_attack` 13, `mudfilm_guard` 7 — the
  guard is a real candidate that the selector actually chooses, while the
  smoke asserts candidacy and value rather than selection frequency.
* The guard plan's estimated `control` value was positive (0.025) and its
  target projection is the implicit self binding.
* Low-tier role observation from the representative smoke: the constructed
  individual's authored defense is a low-tier defensive value, the mounted
  guard adds its authored flat contribution for the duration, and settlement
  leaves the opponent and the constructed control unchanged.

### Evidence map

* Identity, literal construction, payment, refresh, expiry and committed reload
  are established by `world/rules/tests/test_mudfilm_slime_resource_skill.py`,
  the committed representative of the new hit-independent self-support
  composition group.
* Payment and effect fault rollback for the new kit is owned by the shared
  generic suites named in design §10 "Failure"; this smoke establishes the
  durable happy path and does not clone those vectors.
* The `activation.json` intelligence entries are the existing release-record
  mirror of the tuning the process loads, not a new approval table and not a
  second source of the value. The authored value remains in
  `world/rules/rulebook/monster_behaviour.yaml`.

### Focused commands and results

The implementation runs the focused labels from the change design plus the
registry classification and narration contracts the new body action enters.
`/tmp/mud-field-tests.env` contains `MUD_TEST_SETTINGS=1`.

| command | result |
| --- | --- |
| `uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_mudfilm_slime_resource_skill` | OK (1 test) |
| `... world.rules.tests.test_monster_composition_coverage` | OK (4 tests) |
| `... world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | OK (4 tests) |
| `... world.rules.tests.test_combat_modifiers.CombatModifierTests` | OK (96 tests) |
| `... world.lore.tests.test_monster_species_content` | OK (17 tests) |
| `... world.lore.tests.test_monster_visuals` | OK (7 tests) |
| `... world.lore.tests.test_bestiary_documentation` | OK (13 tests) |
| `... world.skills.tests.test_narration_catalog` | OK (42 tests) |
| `... world.skills.tests.test_skill_registry.test_narration_coverage` | OK (15 tests) |
| `... world.skills.tests.test_skill_registry.test_category_classification` | OK (20 tests) |
| `... world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | OK (4 tests) |
| `... world.rules.tests.test_monster_ai_activation.ActivationBindingTests` | OK (4 tests) |
| `... world.rules.tests.test_monster_ai_activation.RollbackTests` | OK (3 tests) |
| `uv run --locked python -m tools.map_reference_context --check` | up to date |
| `uv run --locked openspec validate mudfilm-slime-species --strict` | valid |
| `uv run --locked python -m tools.contract_gate --change mudfilm-slime-species` | passed: reference-context, traceability, observability, test-data, manifests, contracts |

### Human review of the prose

The public prose was written affirmatively from design §4.1: it describes the
body, the attached silt film, the short impact and the local channel-mouth
relationship, and it names no command, buff identifier or resource field. The
author-private fields carry the unknown-origin boundary, the authoring
rationale and one explicitly unverified conjecture. The editorial ledger entry
records the same read; no test judges prose quality or sentence content.

## 蠟囊鼠

The second delivered weak species of the batch is 蠟囊鼠 (`wax_pouch_rat`) with
its ordinary default variant 藏穀型 (`wax_cache_forager`): a low-tier, grade-F,
fast individual whose only active is the self agility slip 滑蠟翻身
(`wax_pouch_slip`). Its social policy and habitat compatibility are exactly the
approved dossier's: a family foraging unit of two to five, and the two habitat
tags the design names.

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table. The complete literal
profile and its authored grade live only in `world/lore/monster_species.py`
and are band-checked at import.

* The profile lies wholly inside the low tier's declared bands, and its
  hit-point pool sits near the comfortable middle of that band, so a created
  character's single strike is a small fraction of it.
* Fast means the authored agility is no lower than the highest agility among
  shipped low-tier ordinary variants (the burrow hare's), and the rat sits
  above that reference while remaining inside the low agility band.
* The physical attack is a modest contact bite inside the low attack band; the
  defense is a low value that lets the species read as evasive rather than
  armored.
* `magic_power` is the only value the tier band admits, and neither the kit nor
  the innate bite spends MP, so the authored MP pool is zero.
* The authored SP pool holds more than two casts of the slip's positive SP
  cost, so a refresh of an aged mount is observable.
* The short slip raises the caster's agility by no more than the absolute value
  of the shipped `rock_echo_stagger_agility_flat` contribution, and its
  lifetime is of the same order as the shipped self guards `lamp_carapace_guard`,
  `ridge_brace` and `mudfilm_shell`.

### Intelligence rationale

`wax_cache_forager` authors intelligence 30 and binds the utility decision. The
authoring rationale is the behaviour itself: it times its slip around a
defended cache and family foraging, a little more situational reading than the
slime's reflexive film — above `mudbank_dweller` (20) and below `trail_hunter`
(44). The value is read from this variant's own lore, never from its tier,
grade, stats or archetype, and it adds no statistic, resource, kit or
proficiency.

### Reuse of the self-support representative

The new body action keeps the same composition signature as the slime's guard:
one active self-buff with no hit dependency. Its variant therefore joins the
existing composition group rather than declaring a new one, and
`mudbank_dweller` keeps the stable-key-ordered representative, so no test
module or shard entry is added. `SelfSupportGroupMemberTests` derives the
group's members from the shipped declarations and exercises each of them on
its own declared axis, so the rat's candidacy, payment, recipient routing and
modifier wiring are established on a real rat instead of the representative's
defense.

### Known flee trade-off

The legacy decision body never proposes a support active, so this variant binds
utility; under `monster-flee-policy` a utility monster never flees voluntarily.
That is the deviation design §12.4 records from §5's available innate flee and
§7.1's retreat orientation for the slime, the rat and the crocodile boss. For
this species the retreat orientation is expressed instead through its
defended-cache field aggression — hostile inside the authored cache area and
retreat-oriented while foraging outside it — in the placement changes, and the
opposing party's paid retreat remains available.

### Non-gating observations

Observed with
`uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_tmp_observation_probe`
(a temporary probe module, deleted after the run), a 20-decision short
inspection run of the shipped policy (each iteration lowers the actor's current
hit points by one, so the snapshot-derived selector seed differs), in a real
battlefield holding the constructed individual, one real player opponent and
one constructed control individual. This is an observation, not a test:

* Candidate count: 2 in every decision (the owned slip and the innate basic
  attack), with 2 scored plans in every decision.
* Exclusions and unavailable skills: none.
* Selection over the short run: `basic_attack` 14, `wax_pouch_slip` 6 — the
  slip is a real candidate that the selector actually chooses, while the smoke
  asserts candidacy and value rather than selection frequency.
* The slip plan's estimated `control` value was positive (1.8e-05) with no
  estimation limit, and its target projection is the implicit self binding.
* Low-tier role observation from the same run: the constructed individual's
  authored agility is above the shipped low-tier ordinary reference, the
  mounted slip adds its authored flat contribution for the duration
  (`agility_flat` 0 → 3 with the authored base unchanged), settlement spends the
  declared SP once, and the opponent and the constructed control are unchanged.

### Evidence map

* Identity, literal construction, payment, recipient routing and the declared
  modifier axis are established for this variant by
  `world/rules/tests/test_mudfilm_slime_resource_skill.py::SelfSupportGroupMemberTests`.
* Payment ordering, formula and fault rollback stay owned by the shared
  generic suites named in design §10 "Failure"; this check establishes the
  durable happy path and does not clone those vectors.
* The `activation.json` intelligence entries are the existing release-record
  mirror of the tuning the process loads, not a new approval table and not a
  second source of the value. The authored value remains in
  `world/rules/rulebook/monster_behaviour.yaml`.

### Focused commands and results

The implementation runs the focused labels from the change design plus the
registry classification, narration and availability contracts the new body
action enters. `/tmp/mud-field-tests.env` contains `MUD_TEST_SETTINGS=1`; the
`CombatModifierTests` class is run as two explicit method batches because one
label discovers more than the repository's 100-test guard allows.

| command | result |
| --- | --- |
| `uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.lore.tests.test_monster_species_content world.lore.tests.test_monster_visuals world.lore.tests.test_bestiary_documentation` | OK (37 tests) |
| `... world.rules.tests.test_mudfilm_slime_resource_skill world.rules.tests.test_monster_composition_coverage` | OK (6 tests) |
| `... world.rules.tests.test_combat_modifiers.CombatModifierTests.<64 rule tests>` | OK (64 tests) |
| `... world.rules.tests.test_combat_modifiers.CombatModifierTests.<33 remaining> ...ApplyCostModifierTests.<7>` | OK (40 tests) |
| `... world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests ...test_category_classification ...test_narration_coverage ... world.skills.tests.test_narration_catalog ...test_content_completion` | OK (91 tests) |
| `... world.skills.tests.test_skill_registry.test_out_of_combat_policy` | OK (6 tests) |
| `... world.rules.tests.test_monster_ai_activation.ActivationRecordTests ...ActivationBindingTests ...RollbackTests` | OK (11 tests) |
| `uv run --locked python -m tools.map_reference_context --check` | up to date |
| `uv run --locked openspec validate wax-pouch-rat-species --strict` | valid |
| `uv run --locked python -m tools.contract_gate --change wax-pouch-rat-species` | passed: reference-context, traceability, observability, test-data, manifests, contracts |

### Human review of the prose

The public prose was written affirmatively from design §4.3: it describes the
rat's body, its wax-lined cheek pouches and belly coat, the short slip, and the
local grain-store relationship, and it names no command, buff identifier or
resource field. The author-private fields carry the unknown-origin boundary,
the authoring rationale and one explicitly unverified conjecture. The
editorial ledger entry records the same read; no test judges prose quality or
sentence content.

### Review dispositions

The independent plan and final reviews raised four findings; each is recorded
here with its disposition.

* The representative-smoke AST contract was weakened by the derived-members
  allowance: a dead helper could satisfy the representative construction, and
  a second literal copy of the representative key could pass. Adopted: the
  check now accepts only the declared name or a loop variable of a group the
  module derives from the registries, requires the resolving test itself to
  construct the declared representative, and permits exactly one module-level
  declaration binding with no other shipped variant-key literal. Temporary
  probe modules proved the good shape passes and the dead-helper, copied-literal,
  arbitrary-variable, loop-literal and shadowed-declaration shapes are rejected.
* A stale pre-change selector fingerprint remained in the activation evidence
  prose. Adopted: updated to the regenerated fingerprint.
* The rat's field aggression was described as passive. Adopted: both documents
  now describe its defended-cache aggression with retreat-oriented foraging,
  as the approved design states.
* No test pinned the derived members' authored lifetime shape. Adopted in part:
  `SelfSupportGroupMemberTests` asserts each member's buff declares a positive
  duration and `refresh` stacking; aging, expiry and the refresh arithmetic stay
  with the representative and shared lifetime suites, as the change design
  assigns them.
* Comprehension-bound group members were suggested as an additional accepted
  form. Rejected: no representative module constructs individuals inside a
  comprehension, so the extra AST branch would be untested generality.
