# Monster Content Expansion: Developer Review and Evidence

This document records the developer review and observed evidence for the monster
content expansion design
(`docs/superpowers/specs/2026-11-03-monster-content-expansion-design.md`). It is
not a balance approval table and it never duplicates the authored literals:
every magnitude lives once in its executable declaration under
`world/lore/monster_species.py`,
`world/skills/registry/data_monster_abilities.py` and
`world/rules/rulebook/`. Sections from 孢傘菇 onward record the north deep
forest species of the near-settlement programme's Wave 1. Sections from 霧泉蛙 onward record the central mountains and northwest highland forest species of the near-settlement programme's Wave 2.
Sections from 滾土甲蟲 onward record the eastern plains and southeast coast species of the near-settlement programme's Wave 3.
Sections from 負鹽蟻 onward record the southwest coast and western hills species of the near-settlement programme's Wave 4.

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

## 膠掌小鬼

The third delivered weak species of the batch is 膠掌小鬼
(`sticky_palm_goblin`) with its ordinary default variant 懸巢型
(`hanging_nest_forager`): a low-tier, grade-F individual whose only active is
the contact grab 黏掌抓扯 (`sticky_palm_grab`), an ordinary elementless
physical strike whose brief agility penalty reaches the struck enemy only when
the grab lands. Its social policy and habitat compatibility are exactly the
approved dossier's: two to four individuals forming one cohesive activity
group, habitat compatibility `western_hills_valleys`, and a retreat-oriented
ordinary foraging individual behind a defended nest.

The approved taxonomy is kept literally: this is an ordinary animal-level
monster species whose signalling is calls, knocks and learned object use. No
beastfolk or civilised-people modelling, language, writing, trade or
settlement is added, and no placement, nest-building or material-collection
mechanic is derived from the advisory prose.

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table. The complete literal
profile and its authored grade live only in `world/lore/monster_species.py`
and are band-checked at import.

* The profile lies wholly inside the low tier's declared bands, and its
  hit-point pool sits between the shipped low-tier ordinary references rather
  than at either end, so a created character's single strike is a small
  fraction of it.
* Agile climber means the authored agility is above every shipped low-tier
  ordinary variant's (the rat's is the highest of them) while staying inside
  the low agility band, with the band's own ceiling left unclaimed.
* The physical attack is a modest contact grab inside the low attack band; the
  defense equals the lowest shipped low-tier ordinary defense, so the species
  reads as thin-skinned and evasive instead of armored.
* `magic_power` is the only value the tier band admits, and neither the kit nor
  the innate attack spends MP, so the authored MP pool is zero.
* The authored SP pool holds at least two casts of the grab's positive SP cost,
  so a refresh of an aged mount is observable on the species itself.
* The grab's damage coefficient stays within the shipped low-tier monster kit
  range `0.8..1.0`, and its short agility penalty is no larger in magnitude
  than the shipped `rock_echo_stagger_agility_flat` contribution, with a
  lifetime of the same order as `rock_echo_stagger`.

### Reuse of the enemy hit-rider representative

The new active keeps the same composition signature as the shipped contact
rider kits: one damage occurrence on enemies followed by a hit-dependent
enemy buff. Its variant therefore joins that existing composition group
instead of declaring a new one, and `cliff_stepper` stays the
stable-key-ordered representative (`"cliff_stepper" < "hanging_nest_forager"`),
so no test module, representative declaration or shard entry is added.

`EnemyRiderGroupMemberTests` in
`world/rules/tests/test_sway_whistle_sparrow_resource_skill.py` derives the
group's members from the shipped declarations and exercises each of them on
its own rider axis, including this one: its own decision mode offers the owned
grab against the lone enemy, settlement pays the declared cost once on a miss
and once on a hit, the landed grab mounts its own effect on the struck enemy
only and moves that enemy's declared modifier axis, the miss leaves the
target's state untouched, the same-member control is unchanged throughout, and
a committed reload keeps both spent pools and the mounted rider.

### Decision mode

`hanging_nest_forager` stays in the permanent legacy decision: it authors
neither `variant_intelligence` nor `variant_decision_mode`, binds the existing
`instinctive` archetype, and the legacy body selects the grab because it
carries a damage occurrence. Design §12.4 therefore does not apply to it — the
species keeps the legacy flee priority and the archetype's inclusive flee
threshold, which is where its retreat orientation lives, rather than the
utility binding the slime and the rat had to take.

### Non-gating observations

Observed with
`uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_tmp_observation_probe`
(a temporary probe module, deleted after the run), a 20-decision short
inspection run of the shipped legacy policy — each iteration lowers the
actor's current hit points by one, so the cloned-actor guard stays satisfied —
in a real battlefield holding the constructed individual and one real player
opponent, followed by one real resolution of the selected grab. This is an
observation, not a test:

* Candidate count: the legacy body carries no utility trace, so no scored-plan
  count exists for it; every one of the 20 decisions returned the owned grab
  itself (`sticky_palm_grab` 20 of 20), which is the `first_owned` behaviour
  the design records as intended while the grab is affordable.
* Exclusions and unavailable skills: none.
* Low-tier role observation from the same run: the resolution succeeded,
  settlement spent the declared SP once (12 → 7 with the other payable pool
  untouched at zero), the mounted effect reached the opponent only — a
  constructed same-species control stayed clean — and the opponent's evaluated
  bundle moved `agility_flat` 0 → −2 while its authored base agility was
  unchanged at 10. The debuff is a modifier, not a stored statistic.

### Evidence map

* Identity, literal construction, ownership, AI selection, payment, recipient
  routing, the landed-hit and miss cases of the declared rider, and the
  committed reload are established for this variant by
  `world/rules/tests/test_sway_whistle_sparrow_resource_skill.py::EnemyRiderGroupMemberTests`.
* The hit-rider and fault-rollback vectors stay owned by the shared rider
  suites and by the group's representative `cliff_stepper` in
  `SwayWhistleSparrowResourceSkillSmokeTests`: this check adds the goblin's own
  axis and does not clone payment ordering, formula or rollback.
* Movement and flee availability stay governed by their ordinary gates and are
  owned by the shared flee suites; no clone is added here.
* The fingerprint moves in `activation.json` because the new buff definition
  and modifier rule enter the decision-relevant projection every estimate
  averages over. `activated` and `activation_bindings` are unchanged: this
  change activates no variant.

### Focused commands and results

The implementation runs the focused labels from the change design plus the
registry classification, narration and availability contracts the new active
enters. `/tmp/mud-field-tests.env` contains `MUD_TEST_SETTINGS=1`.

| command | result |
| --- | --- |
| `uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.lore.tests.test_monster_species_content world.lore.tests.test_monster_visuals` | OK (24 tests) |
| `... world.lore.tests.test_bestiary_documentation` | OK (13 tests) |
| `... world.rules.tests.test_sway_whistle_sparrow_resource_skill world.rules.tests.test_monster_composition_coverage` | OK (6 tests) |
| `... world.rules.tests.test_combat_modifiers.CombatModifierTests` | OK (98 tests) |
| `... world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests ...test_category_classification ...test_narration_coverage world.skills.tests.test_narration_catalog ...test_out_of_combat_policy` | OK (87 tests) |
| `... world.rules.tests.test_monster_ai_tuning` | OK (40 tests) |
| `... world.rules.tests.test_monster_ai_activation.ActivationRecordTests ...ActivationBindingTests ...RollbackTests` | OK (11 tests) |
| `uv run --locked python tools/monster_ai_manual_reports.py selector` | regenerated: paired difference 0.344 (required >= 0.15), margin met |
| `uv run --locked python -m tools.map_reference_context --check` | up to date |
| `uv run --locked openspec validate sticky-palm-goblin-species --strict` | valid |
| `uv run --locked python -m tools.contract_gate --change sticky-palm-goblin-species` | passed: reference-context, traceability, observability, test-data, manifests, contracts |

One unrelated label is red at this branch's base and not this slice's:
`world.rules.tests.test_monster_timed_effect_mechanisms` builds its roster with
`fixture:` keys against persisted objects, while `Battlefield.__post_init__` at
the base commit requires each roster key to equal `stable_actor_id(entity)`
(`dbref:<pk>`). The drift comes from the in-progress individual-identity
cutover; neither the module nor `world/rules/combat/battlefield.py` is touched
here. This change therefore carries the landed-hit and miss evidence on real
authored content instead of relying on that synthetic suite.

### Human review of the prose

The public prose was written affirmatively from design §4.2: it describes the
creature's large ears, long thin limbs and wide palms, the temporary palm
adhesive that binds twigs, grit and fur into hanging nests and helps it cling
to rough surfaces, the small group's calls and knocks, the learned use of
materials people leave behind, the thinning film in rain, and the short loss of
rhythm after a landed grab. It names no command, buff identifier or resource
field, and it states the animal-level taxonomy without inventing a people.
The author-private fields carry the unknown-origin boundary, the authoring
rationale and one explicitly unverified quarrymen's conjecture. The editorial
ledger entry records the same read; no test judges prose quality or sentence
content.

### Review dispositions

The independent plan and final reviews' findings are recorded here with their
disposition. The plan review's two blocking findings both concerned the new
derived group-member test and were adopted before implementation:

* The test assumed every member of the hit-rider group is in the legacy
  decision, but `flock_leader` and `trail_hunter` are activated utility
  variants. Adopted: the candidacy check branches on the member's own resolved
  mode — a legacy member must return its own kit against the lone enemy, and a
  utility member must offer the same kit as a scored plan aimed at that enemy —
  while the payment, hit, miss and reload assertions stay mode-independent.
* The group mixes `mp`-plus-`sp` kits with this `sp`-only kit, so a fixed
  gauge assertion would either raise on the goblin or silently skip a payment
  on the others. Adopted: payment is asserted through the skill's own declared
  cost keys and both pools are restored before the hit probe.
* The module-level `_buff_instances` helper was bound to the representative's
  key only. Adopted: it takes an optional effect key so a derived member reads
  its own mounted effect.
* The manual-evidence README carries the selector fingerprint twice (the
  regeneration paragraph and the superseded-values paragraph). Adopted: both
  updated, with the previous value moved into the superseded list.
* The ledger row had to state the animal-level taxonomy explicitly, because
  the design requires the depiction to stay distinct from beastfolk. Adopted:
  the row states it in the ecology face.

The final review over the landed diff raised one blocking finding, adopted:

* The public bestiary section carried negative exclusions — a
  "they are animals, not a people with language, writing or trade" contrast and
  a "a missed grab leaves the opponent unaffected" sentence — plus the
  rulebook-shaped phrase "movement and retreat are decided by the ordinary
  rules". `docs/lore/monster-creation-guidelines.md` §8 requires public prose to
  describe what the creature does and to keep exclusions in author-private or
  developer text. Adopted: the section now states the group's calls, knocks and
  learned object use affirmatively, states that the rhythm disruption follows a
  grab that lands, and describes the withdrawal along rock faces and scrub as
  observed behaviour. The taxonomy exclusion stays in `author_explanation_zh`,
  the editorial ledger and this document.
* Its suggestion to assert that the committed reload really returns fresh rows
  was adopted as well: the derived member test now proves the cache eviction
  happened instead of passing on an in-memory object.

## 吞潮鱷・蓄潮型

The high-tier stronger variant of the existing 吞潮鱷
(`tide_devouring_crocodile`) is 蓄潮型 (`reservoir_warden`): a complete
standalone grade-A record, not an override chain and not an in-place buff of
守灣型. It keeps the existing contact drain 吞潮咬擊 (`tide_devouring_bite`)
and adds the MP-funded self film 蓄潮護膜 (`reservoir_guard`). The crocodile's
default 潛岸型 and its ordinary 守灣型 keep their own rows and kits, and the
species' existing low/mid data is not globally strengthened.

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table. The complete literal
profile and its authored grade live only in `world/lore/monster_species.py`
and are band-checked at import.

* The profile lies wholly inside the high tier's declared bands. Every
  physical axis and the hit-point pool are no lower than 守灣型's corresponding
  value, because this is the stronger variant of the same species rather than
  a sidegrade: the pool is well above the mid-tier 守灣型's, and the attack,
  agility and defense are all at or above that row's own values while staying
  inside the high bands.
* `magic_power` is the only value the tier band admits.
* The authored MP pool covers both kit costs at once, so the variant can
  alternate the drain and the film instead of choosing one permanently. The
  bite keeps its existing cost and the film's MP cost lies inside the 學徒
  single-target band, so the film classifies as a mortal-tier elemental spell.
* The authored SP pool holds at least two casts of the bite's SP cost.
* The film raises the caster's defense for a short window of the same order as
  the shipped self guards; the refresh rule replaces an aged mount instead of
  accumulating one.
* The defense contribution is a modest single-digit value inside the high
  tier's own defense band: it is smaller than the band's width and well below
  the strongest sustained high-tier defensive mounts, so a personal film
  shifts mitigation without replacing a dedicated defender's role. The
  authored lifetime matches the other monster self guards.

### Composition and representative

The drain-plus-self-support kit is a new composition shape: one enemy damage
occurrence, one hit-qualified enemy transfer and one caster-only support
mount. No other shipped variant declares that ordered shape, so the change owns
the group's stable-key-ordered representative,
`world/rules/tests/test_reservoir_warden_resource_skill.py`. The module derives
both skill keys and costs, the mounted effect and the live modifier row from
the declarations, then observes candidacy, guard payment and routing, an
actual-loss drain with caster credit, refresh, expiry, insufficient-MP
rejection and a committed reload. The existing 潛岸型 composition keeps its own
representative untouched.

### Intelligence rationale

`reservoir_warden` authors intelligence 62 and binds the utility decision. The
authoring rationale is the behaviour itself: it weighs drawing an opponent's
magic against spending its own on the film, a recurring trade-off read from
its own resources. That is more decision depth than the reflexive film of
濕岸型 (20), the timed slip of 藏穀型 (30) and the single probing rule of
獵道型 (44), and less than the terrain-and-group reading of 守礁型 (66). The
value is read from this variant's own lore, never from its tier, grade, stats
or archetype, and it adds no statistic, resource, kit or proficiency.

### Known flee trade-off

The permanent legacy decision body never proposes a support active, so this
variant must bind utility or its film could never be selected
(`support_kit_mode_violations` reports exactly that). Under
`monster-flee-policy` a utility-mode monster never voluntarily flees, which is
the known deviation from design §5's available innate flee and §7.3's
either-side retreat record: the boss's escapes in play come from the opposing
party's paid retreat and later re-engagement, and rollback to legacy would
restore its flee priority while making the owned guard unusable.

### Non-gating observations

Observed with a temporary probe module, deleted after the run, in real
battlefields holding the constructed representative and one real player
opponent:

* One committed utility round selected `tide_devouring_bite`, wrote a damage
  entry and a `gauge_transfer` entry, lowered the defender from 400 to 354 hit
  points, and left the representative at 30/40 MP and 35/40 SP after the
  bite's payment. This is the smoke encounter outcome checked against the
  authored A-grade role: the high-band profile and the two-resource payment
  are observed through real settlement, not through the tier label.
* A 20-decision short inspection run (each iteration lowers the actor's
  current hit points by one, so the snapshot-derived selector seed differs)
  reported 3 candidates in every decision, no exclusions or unavailable
  skills, and selections of `basic_attack` 10, `tide_devouring_bite` 6 and
  `reservoir_guard` 4, at temperature 0.5246. The film is therefore a real
  candidate the selector chooses, while the committed smoke asserts candidacy
  and value rather than selection frequency.
* The committed representative smoke itself resolved a guard mount (12 MP,
  +6 defense, caster only) and two hit bites that each removed the defender's
  actual 7 MP: the first credited the caster the actual amount with headroom
  below the pool ceiling, and the second credited to the ceiling before paying
  both costs, with the opponent and a constructed ally as untouched controls.

### Evidence map

* Identity, literal construction, the new composition group, candidacy, guard
  payment and routing, actual-loss transfer with capped credit, payment order,
  refresh, expiry, insufficient-MP rejection and committed reload are
  established by `world/rules/tests/test_reservoir_warden_resource_skill.py`,
  the committed representative of the new drain-plus-self-support group.
* Payment and effect fault rollback for the new kit is owned by the shared
  generic transfer/self-support/lifetime suites named in design §10 "Failure";
  this smoke establishes the durable happy path and does not clone those
  vectors.
* The `activation.json` intelligence entry is the existing release-record
  mirror of the tuning the process loads, not a new approval table and not a
  second source of the value. The authored value remains in
  `world/rules/rulebook/monster_behaviour.yaml`.

### Focused commands and results

The implementation runs the focused labels from the change design plus the
registry, narration and classification contracts the new elemental support
enters. `/tmp/mud-field-tests.env` contains `MUD_TEST_SETTINGS=1`.

| command | result |
| --- | --- |
| `uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_reservoir_warden_resource_skill` | OK (1 test) |
| `... world.rules.tests.test_crocodile_resource_skill` | OK (1 test) |
| `... world.rules.tests.test_monster_composition_coverage` | OK (4 tests) |
| `... world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | OK (4 tests) |
| `... world.rules.tests.test_combat_modifiers.CombatModifierTests` | OK (99 tests) |
| `... world.lore.tests.test_monster_species_content` | OK (17 tests) |
| `... world.lore.tests.test_bestiary_documentation` | OK (13 tests) |
| `... world.skills.tests.test_skill_registry.test_out_of_combat_policy world.skills.tests.test_skill_registry.test_category_classification world.skills.tests.test_skill_registry.test_narration_coverage` | OK (41 tests) |
| `... world.skills.tests.test_narration_catalog world.lore.tests.test_monster_visuals` | OK (49 tests) |
| `... world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | OK (4 tests) |
| `... world.rules.tests.test_monster_ai_activation.ActivationBindingTests` | OK (4 tests) |
| `... world.rules.tests.test_monster_ai_activation.RollbackTests` | OK (3 tests) |
| `... world.rules.tests.test_human_combat_calibration.HumanCombatCalibrationTests` | OK (3 tests) |
| `... world.rules.tests.test_human_combat_calibration.EncounterCalibrationTests` | OK (1 test) |
| `... world.rules.tests.test_human_combat_calibration.EncounterSelectedValueTests` | OK (2 tests) |
| `uv run --locked python tools/monster_ai_manual_reports.py selector` | regenerated: paired difference 0.344 (required >= 0.15), margin met |
| `uv run --locked python -m tools.map_reference_context --check` | up to date |
| `uv run --locked openspec validate reservoir-warden-variant --strict` | valid |
| `uv run --locked python -m tools.contract_gate --change reservoir-warden-variant` | passed: reference-context, traceability, observability, test-data, manifests, contracts |

### Human review of the prose

The crocodile's published ecology was rewritten affirmatively from design
§4.4: it states the contact drain, what the opponent actually has available,
its recovery after rest, and the crocodile's own reserve directly. The
bestiary replaces the former exclusion paragraph with a behaviour paragraph
and adds the three approved 蓄潮型 passages verbatim, including the local name
「閉灣者」. The section names no command, buff identifier or resource field.
The author-private fields keep the unknown-origin boundary, the authoring
rationale and one explicitly unverified ferry-station conjecture. The editorial
ledger records the same read; no test judges prose quality or sentence
content.

### Review dispositions

The independent plan review raised two blocking findings and four non-blocking
ones; all were adopted before or during implementation:

* `reservoir_guard` declares `usable_out_of_combat=False`, so the frozen false
  inventory in `world/skills/tests/test_skill_registry/_support.py` has to name
  it. Adopted, and the out-of-combat, classification and narration contracts
  were added to the focused runs.
* The planned bite assertion at full caster MP could not detect a missing
  caster credit or an actual-loss clamp. Adopted: the guard cast runs first,
  the defender is reduced below the declared fixed drain, and a first hit
  observes the uncapped actual credit while a second hit observes the pool
  ceiling, with both formulas written from the declared values.
* The candidacy check now also asserts the guard's positive control value and
  the bite's positive damage value, so a broken or zero-valued projection
  cannot pass as mere plan presence.
* The representative smoke now owns refresh and expiry as well, because the
  two-skill shape is not a member of the existing hit-independent self-support
  group.
* The activation record and both AI evidence READMEs carried five-variant
  counts and two fingerprint sites. Adopted: the set, the rollback count, both
  selector fingerprint paragraphs and the superseded-value list were updated
  together.
* The composition-coverage AST invariants were preserved: the module binds
  `REPRESENTATIVE_VARIANT` once, names no other shipped variant key and
  constructs only through that declaration.

One observation changed the insufficient-MP assertion without weakening it:
at 11 MP the selector offered the affordable bite as a candidate but chose the
innate attack, so the test asserts the guard's absence from the candidate set
and the forced request's refusal rather than requiring the bite to be
selected.

The final review over the landed diff raised one blocking finding, adopted:

* The single bite assertion still saturated the caster pool at its maximum,
  so a handler that credited the full declared fixed drain instead of the
  opponent's actual loss would have produced the same number. The smoke now
  resolves two hits: the first, after the guard payment, has headroom and
  proves the actual-amount credit is neither absent nor nominal; the second
  fills to the ceiling and proves the cap and the credit-before-cost order.

## 焙鬃野豬

The fourth delivered species of the batch, and the first high-tier species, is
焙鬃野豬 (`ember_bristle_boar`) with its ordinary default variant 焙窩型
(`warm_den_boar`): a complete high-tier, grade-B individual whose kit is two
fire-element physical strikes, 熱鬃衝撞 (`ember_tusk_charge`, one enemy) and
熱鬃橫掃 (`ember_bristle_sweep`, all eligible enemies). The species owns one
variant; no stronger variant, site or placement belongs to this change.

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table. The complete literal
profile and its authored grade live only in `world/lore/monster_species.py`
and are band-checked at import.

* The profile lies wholly inside the high tier's declared bands (hit points
  300-750, attack 26-40, agility 16-30, defense 18-32, magic `(0, 0)`).
* Ordinary B baseline below the A-grade threat: every non-magic axis is below
  the stronger crocodile variant 蓄潮型's own value, so the row is not a
  second A-grade threat. Hit points sit above the band floor and well below
  the A pool; attack sits just above the band floor; agility and defense sit
  near the floor of their bands. The row therefore reads as the lower half of
  the high tier, which is what an ordinary baseline means here.
* `magic_power` is the only value the tier band admits. Authoring a fire
  element never raises it: the strikes read the actor's physical attack under
  the existing physical-school contract, and the element follows the ordinary
  elemental rules.
* The MP pool holds at least two casts of the larger MP cost and the SP pool
  at least two casts of the larger SP cost, so either strike can be repeated
  and the innate fallback is only reached by real depletion.
* Both costs are positive and each MP cost lies inside its target-spec cost
  column: the charge's 12 MP classifies in the 學徒 single-target band and the
  sweep's 16 MP in the 學徒 area band. Both therefore resolve a magic-tier data
  label without inventing a second cost table.
* The charge's coefficient is above the sweep's: one committed impact is
  stronger per recipient than one wide motion. The sweep still pays both costs
  once per cast while each recipient is resolved on its own hit and defense.

### Composition and representative

The two-damage-actives kit is a new composition shape: two `damage`
occurrences on the enemies audience with no rider and no support mount. No
other shipped variant declares that ordered shape, so the group's
stable-key-ordered representative is `warm_den_boar`, committed as
`world/rules/tests/test_ember_bristle_boar_resource_skill.py`. The module
derives both skill keys, both costs and the behaviour binding from the
declarations, then observes the single-target selection against one opponent,
the area selection against two, separate per-recipient hit and defense
outcomes with an untouched constructed ally, one MP/SP payment per cast, the
innate fallback when either resource is exhausted, an empty freeform ladder
and a committed reload. The existing one-active and one-damage-plus-rider
groups keep their own representatives untouched.

### Decision mode and the flee threshold

`warm_den_boar` binds the existing `pack_hunter` archetype and authors neither
`variant_intelligence` nor `variant_decision_mode`, so it keeps the permanent
legacy decision with no rulebook edit. `highest_expected_damage` scores the
charge and the innate attack equally, because both read the physical attack
and the legacy tie-break die decides; `prefer_area_when_multiple_enemies`
makes the sweep the selection whenever more than one enemy stands. Its
inclusive flee fraction keeps design §7.3's "either side can flee" available
to the boar through a legal affordable route. Both actives carry damage, so
`support_kit_mode_violations` stays empty for this variant. No rulebook value
changes, so the AI tuning fingerprint and the recorded activation evidence are
unchanged.

### Non-gating role observation

Read against the existing calibration boundary, the documented high-tier lower
probe is 320 hit points / 28 attack / 18 agility / 20 defense and the upper
probe is 700/38/26/28. The authored ordinary B profile (380/28/17/20) sits just
above the lower probe on hit points, level with it on attack and defense, one
point below it on agility while staying inside the high band's floor of 16,
and below the A-grade 蓄潮型 on every axis. The row therefore reads as an
ordinary B baseline in the lower half of the high tier rather than a second
A-grade threat. This is a declaration relation observed through the existing
calibration boundary, not a balance re-approval.

### Evidence map

* Identity, literal construction, the new composition group, single-target and
  area selection, per-recipient hit and defense outcomes, one payment per
  cast, the innate fallback on either exhausted resource, the empty freeform
  ladder and committed reload are established by
  `world/rules/tests/test_ember_bristle_boar_resource_skill.py`, the committed
  representative of the new two-strike group.
* Payment and effect fault rollback for the new kit is owned by the shared
  generic damage/payment suites named in design §10 "Failure"; this smoke
  establishes the durable happy path and does not clone those vectors.
* The kit-contract correction in
  `world/skills/tests/test_skill_registry/test_registry_contract.py` names the
  real freeform gate: shape eligibility no longer stands in for the element
  mastery entitlement, and the smoke observes the empty ladder on a
  constructed boar.
* The two narration rows are covered by the shared narration catalog
  contracts, which require each element module to carry exactly its own active
  elemental spells.

### Focused commands and results

The implementation runs the focused labels from the change design plus the
narration, classification, availability and registry contracts the new
elemental strikes enter. `/tmp/mud-field-tests.env` contains
`MUD_TEST_SETTINGS=1`.

| command | result |
| --- | --- |
| `uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_ember_bristle_boar_resource_skill` | OK (1 test) |
| `... world.lore.tests.test_monster_species_content world.lore.tests.test_bestiary_documentation world.lore.tests.test_monster_visuals world.rules.tests.test_monster_composition_coverage world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | OK (45 tests) |
| `... world.skills.tests.test_skill_registry.test_narration_coverage world.skills.tests.test_skill_registry.test_category_classification world.skills.tests.test_skill_registry.test_out_of_combat_policy world.skills.tests.test_narration_catalog world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | OK (87 tests) |
| `uv run --locked python -m tools.map_reference_context` then `--check` | regenerated; up to date |
| `openspec validate ember-bristle-boar-species --strict` | valid |
| `uv run --locked python -m tools.contract_gate --change ember-bristle-boar-species` | passed: reference-context, traceability, observability, test-data, manifests, contracts |

### Human review of the prose

The three published passages are design §4.5's approved text verbatim: the
species paragraph, the appearance paragraph and the ecology paragraph, the
last including the local name 「赤背」. The bestiary section renders them
affirmatively as 原型與棲地 / 外觀 / 生態與在地關係 and adds a
戰鬥中的表現 paragraph that states the single-target charge, the sweep over
every hostile figure, the boar's own magic and stamina as the cost, and the
ordinary contact attack it keeps when those run out. The section names no
command, buff identifier or resource field. The author-private fields keep the
unknown-origin boundary, the authoring rationale and one explicitly unverified
charcoal-worker conjecture. The editorial ledger records the same read; no
test judges prose quality or sentence content.

### Review dispositions

The independent plan review raised three blocking findings and one
non-blocking one; all were adopted before implementation:

* Under `pack_hunter`, `highest_expected_damage` scores the charge and the
  innate attack equally, so the single-opponent selection was not
  deterministic. Adopted: the smoke pins the legacy tie-break die to the even
  branch that keeps the owned kit first, and asserts the charge is the
  selection.
* Two sweeps leave 4 SP (20 - 2 x 8), below the cheapest kit SP cost of 6, so
  a later MP-exhaustion probe would have been vacuous; subtracting one from
  one skill's cost would also leave the cheaper skill affordable. Adopted: the
  pools are restored before each exhaustion probe, and each probe sits below
  the cheapest kit cost of that resource.
* Comparing cumulative hit points after the first sweep would not prove
  per-recipient defense mitigation. Adopted: the second sweep records each
  recipient's own pre-cast value and compares that cast's two losses, with the
  roster order fixed so the hit and miss land on the intended recipients.
* The single-target strike was only selected, never settled. Adopted: the
  smoke resolves the selected charge as well, observing its damage, its single
  MP/SP payment and the untouched ally control.

The final review over the landed diff raised two blocking findings and two
non-blocking ones; all were adopted:

* The exhaustion probes ran against a single opponent, where the legacy body
  never prefers an area skill, so they could not prove the sweep left the
  affordable set. Adopted: both probes now run against the two-opponent field,
  where a surviving area skill would still be preferred over the innate
  attack.
* The ally-control check never exercised the sweep's declared enemy audience,
  because the `all-enemies` shorthand already filters the target pool. Adopted:
  the second sweep admits the whole roster and only the declared audience keeps
  the caster and the ally out of the strike.
* Nothing asserted that the charge is stronger per recipient than the sweep.
  Adopted: the smoke compares the two landed losses against the same
  defense-zero recipient.
* The review text described the SP arithmetic imprecisely. Adopted: it now
  states the actual remainder and the cheapest kit cost it falls below.

## 孢傘菇

This section records the north deep forest species of the near-settlement
programme's Wave 1. The first delivered one is 孢傘菇 (`spore_cap_mushroom`):
a low-tier, grade-F, slow colony fungus whose ordinary default variant is
腐木型 (`rotlog_sprout`), with the stronger 菌環型 (`ring_elder`). Both carry
the single dark bump 孢粉頂撞 (`spore_puff_bump`).

### Role constraints and the chosen literals

* Slow colony fungus: the authored agility is the low band's floor, tied with
  the slime as the slowest of every shipped low-tier ordinary variant.
* Sturdier than the evasive low animals: the authored defense lies between the
  hare's and the slime's, inside the low defense band.
* The authored MP pool holds two casts of the dark bump's MP cost, and the SP
  pool holds four casts of its SP cost.
* The stronger 菌環型 keeps the same kit with a larger pool, attack and
  defense, inside the low band and at grade E.
* The bump coefficient (0.8) and the accuracy penalty (−3) match the sparrow's
  shipped peck and rider, the smallest shipped hit-rider magnitudes; the 12 s
  lifetime is of the same order as the shipped 10-15 s hit riders.

### Reuse of the enemy hit-rider representative

The kit's composition signature is
`(("active", "damage", "enemies", None), ("active", "buff_apply", "enemies", 0))`,
the shipped enemy hit-rider group. Its representative stays `cliff_stepper`:
both new variant keys sort after it, so the representative declaration and
every shard, seed and smoke registration stay unchanged. The existing
`EnemyRiderGroupMemberTests` in
`world/rules/tests/test_sway_whistle_sparrow_resource_skill.py` derives the
group's members from the shipped declarations and exercises both new variants
on their own rider axis without a test edit.

### Decision mode

Both variants bind the shipped `instinctive` archetype and stay in the
permanent legacy decision, so they carry that archetype's flee threshold of
0.35. Neither authors intelligence, a decision-mode override nor a
`monster_behaviour.yaml` edit.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run
alone with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_sway_whistle_sparrow_resource_skill` | 2 tests, OK |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK |
| `world.rules.tests.test_combat_modifiers.CombatModifierTests` | 100 tests, OK |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationBindingTests` | 4 tests, OK |
| `world.rules.tests.test_monster_ai_activation.RollbackTests` | 3 tests, OK |

The remaining gates also passed: the registry import check,
`uv run --locked python -m tools.map_reference_context --check`,
`uv run --locked python -m tools.contract_gate --change spore-cap-mushroom-species`
and `openspec validate spore-cap-mushroom-species --strict`.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 苔棘豪豬

This section records the second delivered species of the north deep forest
Wave 1. 苔棘豪豬 (`moss_quill_porcupine`) is a low-tier, grade-F, solitary
forager porcupine whose ordinary default variant is 啃皮型 (`quill_forager`),
with the stronger 守洞型 (`den_sentry`). Both carry the single earth back ram
固棘倒撞 (`quill_brace_ram`).

### Role constraints and the chosen literals

* Defensive forager: the ordinary variant's authored defense sits two below
  the low band's ceiling and above every shipped low-tier ordinary variant
  except the slime's; it ties the hare's stronger 護巢型. The design brief
  described this as equal to the crab's and the highest shipped low-tier
  ordinary defense, but the shipped crab ordinary carries 5 and the slime
  ordinary carries 7, so this review records the actual relation instead.
* A plodding walker: the authored agility is below the hare's and the rat's.
* The authored MP pool holds two casts of the ram's MP cost, and the SP pool
  holds three casts of its SP cost.
* The guard (+2 defense for 20 s) matches the crab's, the smallest shipped
  self-guard.
* The stronger 守洞型 holds a den, so it carries the larger pool and the low
  band's defense ceiling at grade E.

### Reuse of the self-guard strike representative

The kit's composition signature is
`(("active", "damage", "enemies", None), ("active", "self_buff_apply", "self", None))`,
the shipped self-guard strike group. The guard declares no hit dependency,
following the crab and hare kits, so it mounts on every resolved attempt
including a miss. Its representative stays `burrow_maker`: both new variant
keys sort after it, so the representative declaration and every shard, seed
and smoke registration stay unchanged. The existing
`world/rules/tests/test_monster_composition_coverage.py` derives every
shipped variant's signature and proves both new variants join this group,
while the existing `world/rules/tests/test_tide_lamp_crab_resource_skill.py`
commits the group's representative evidence for `burrow_maker`; no
per-variant smoke module is added for a reused signature.

### Decision mode

Both variants bind the shipped `instinctive` archetype and stay in the
permanent legacy decision, so they carry that archetype's flee threshold of
0.35. Neither authors intelligence, a decision-mode override nor a
`monster_behaviour.yaml` edit. The new buff definition and modifier rule do
move the startup tuning fingerprint, so the activation record and the
selector evidence were re-fingerprinted; `activated` and
`activation_bindings` are unchanged.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run
alone with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_tide_lamp_crab_resource_skill` | 1 test, OK |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK |
| `world.rules.tests.test_combat_modifiers.CombatModifierTests` | blocked by the repository test guard at 101 discovered tests (the limit is 100); `CombatModifierTests.test_rule_quill_brace_defense` ran alone, 1 test OK, and the class had 100 tests before this change |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK after the re-fingerprint |
| `world.rules.tests.test_monster_ai_activation.ActivationBindingTests` | 4 tests, OK |
| `world.rules.tests.test_monster_ai_activation.RollbackTests` | 3 tests, OK after the re-fingerprint |

The remaining gates also passed: the registry import check,
`uv run --locked python -m tools.map_reference_context` followed by
`--check`, `uv run --locked python -m tools.contract_gate --change
moss-quill-porcupine-species` and
`openspec validate moss-quill-porcupine-species --strict`.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 空木蝠

This section records the third delivered species of the north deep forest
Wave 1. 空木蝠 (`hollow_tree_bat`) is a low-tier, grade-F, agile colony flier
whose ordinary default variant is 棲洞型 (`hollow_roost_flier`), with the
stronger 哨群型 (`colony_sentinel`). Both carry the single dark bite
空木吸咬 (`hollow_bat_bite`).

### Role constraints and the chosen literals

* Agile, fragile flier: the ordinary variant's authored agility is 11, one
  below the low band's ceiling of 12, while its defense is the band floor of
  2 and its hit points (28) sit near the band floor of 25.
* 棲洞型's MP pool of 20 holds two casts of the bite's MP cost of 10, and its
  SP pool of 6 holds three casts of the SP cost of 2. The stronger 哨群型
  carries 30 MP and 10 SP, which holds three and five casts respectively.
* The fixed HP drain (4) is far below the crocodile's fixed MP drain (10),
  which suits a low-tier contact bite.
* The stronger 哨群型 guards the roost mouth, so it carries a larger pool and
  attack (hp 50, attack 9) at grade E.

### Reuse of the contact drain representative

The kit's composition signature is
`(("active", "damage", "enemies", None), ("active", "gauge_transfer", "enemies", 0))`,
the shipped contact drain group. Its representative stays `bank_lurker`:
both new variant keys sort after it, so the representative declaration and
every shard, seed and smoke registration stay unchanged. The drained gauge is
HP instead of the crocodile's MP, but the signature reads only the effect
family, audience and hit dependency, so the group is the same. The existing
`world/rules/tests/test_crocodile_resource_skill.py` commits the group's
representative evidence; no per-variant smoke module is added for a reused
signature.

### Decision mode

Both variants bind the shipped `instinctive` archetype and stay in the
permanent legacy decision, so they carry that archetype's flee threshold of
0.35. Neither authors intelligence, a decision-mode override nor a
`monster_behaviour.yaml` edit. This link adds no buff definition or modifier
rule, so the startup tuning fingerprint does not move; the activation tests
passed and the evidence was left untouched, with `activated` and
`activation_bindings` unchanged.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run
alone with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_crocodile_resource_skill` | 1 test, OK |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationBindingTests` | 4 tests, OK |
| `world.rules.tests.test_monster_ai_activation.RollbackTests` | 3 tests, OK |

The remaining gates also passed: the registry import check,
`uv run --locked python -m tools.map_reference_context` followed by
`--check`, `uv run --locked python -m tools.contract_gate --change
hollow-tree-bat-species` and `openspec validate hollow-tree-bat-species
--strict`.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 靜羽梟

This section records the fourth delivered species of the north deep forest
Wave 1. 靜羽梟 (`hush_wing_owl`) is a mid-tier, grade-D, agile ambush owl
whose ordinary default variant is 夜獵型 (`hush_wing_hunter`), with the
stronger 古巢型 (`old_hollow_owl`). Both carry the single wind talon swoop
靜羽掠爪 (`hush_wing_swoop`).

### Role constraints and the chosen literals

* Agile ambush predator: the ordinary variant's authored agility is 22, two
  above the lynx's ordinary 林伏型 and below the mid band's ceiling of 24.
* Lightly built: the authored defense is 10, the mid band's floor.
* The ordinary MP pool of 30 holds three casts of the swoop's MP cost of 10,
  and its SP pool of 20 holds four casts of the SP cost of 5.
* The lift (+3 agility for 15 s) equals the rat's shipped self agility rise.
* The stronger 古巢型 guards a nest tree at grade C with a larger pool
  (hp 160, mp 50, sp 30, attack 26, agility 24, defense 12).

### Reuse of the self-guard strike representative

The kit's composition signature is
`(("active", "damage", "enemies", None), ("active", "self_buff_apply", "self", None))`,
the shipped self-guard strike group. The lift declares no hit dependency,
following the crab, hare and porcupine kits, so it mounts on every resolved
attempt including a miss. Its representative stays `burrow_maker`: both new
variant keys sort after it, so the representative declaration and every shard,
seed and smoke registration stay unchanged. The existing
`world/rules/tests/test_monster_composition_coverage.py` derives every shipped
variant's signature and proves both new variants join this group, while the
existing `world/rules/tests/test_tide_lamp_crab_resource_skill.py` commits the
group's representative evidence for `burrow_maker`; no per-variant smoke module
is added for a reused signature.

### Decision mode

Both variants bind the shipped `ambush_predator` archetype and stay in the
permanent legacy decision, so they carry that archetype's flee threshold of
0.20. Neither authors intelligence, a decision-mode override nor a
`monster_behaviour.yaml` edit. The new buff definition and modifier rule do
move the startup tuning fingerprint, so the activation record and the
selector evidence were re-fingerprinted; `activated` and
`activation_bindings` are unchanged.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run
alone with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_tide_lamp_crab_resource_skill` | 1 test, OK |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK |
| `world.rules.tests.test_combat_modifiers.CombatModifierTests` | blocked by the repository test guard as a single label at 102 discovered tests (the limit is 100); the class ran as two explicit method batches of 51 tests each, both OK |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK after the re-fingerprint |
| `world.rules.tests.test_monster_ai_activation.ActivationBindingTests` | 4 tests, OK |
| `world.rules.tests.test_monster_ai_activation.RollbackTests` | 3 tests, OK after the re-fingerprint |

The remaining gates also passed: the registry import check,
`uv run --locked python -m tools.map_reference_context` followed by
`--check`, `uv run --locked python -m tools.contract_gate --change
hush-wing-owl-species` and `openspec validate hush-wing-owl-species --strict`.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 藤網蛛

This section records the fifth delivered species of the north deep forest
Wave 1. 藤網蛛 (`vine_net_spider`) is a mid-tier, grade-D, patient web-ambush
spider whose ordinary default variant is 織藤型 (`vine_weaver`), with the
stronger 封道型 (`trail_netter`). Both carry the single elementless thread cast
藤絲纏擲 (`vine_thread_cast`).

### Role constraints and the chosen literals

* Patient web ambusher: the ordinary variant's authored agility is 15, in the
  lower half of the mid band (10–24), below the owl's and the lynx's ordinary
  variants.
* Sturdy body: the authored defense of 12 matches the goat's ordinary 踏崖型
  and the lynx's stronger 獵道型, and sits two above the lynx's ordinary
  林伏型.
* The kit spends no MP, so the MP pool is zero; the SP pool of 24 holds four
  casts of the cast's SP cost of 6.
* The rider (−3 agility for 15 s) equals the goat's shipped
  `rock_echo_stagger_agility_flat` contribution and lifetime.
* The stronger 封道型 holds a whole forest path at grade C with a larger pool
  (hp 175, sp 36, attack 25, agility 17, defense 14).

### Reuse of the enemy hit-rider representative

The kit's composition signature is
`(("active", "damage", "enemies", None), ("active", "buff_apply", "enemies", 0))`,
the shipped enemy hit-rider group. Its representative stays `cliff_stepper`:
both new variant keys sort after it, so the representative declaration and
every shard, seed and smoke registration stay unchanged. The existing
`world/rules/tests/test_monster_composition_coverage.py` derives every shipped
variant's signature and proves both new variants join this group, while
`world/rules/tests/test_sway_whistle_sparrow_resource_skill.py`'s
`EnemyRiderGroupMemberTests` derives the members from the shipped declarations
and exercises each one's landed hit, miss and committed reload; no
per-variant smoke module is added for a reused signature.

### Decision mode

Both variants bind the shipped `ambush_predator` archetype and stay in the
permanent legacy decision, so they carry that archetype's flee threshold of
0.20. Neither authors intelligence, a decision-mode override nor a
`monster_behaviour.yaml` edit. The new buff definition and modifier rule do
move the startup tuning fingerprint, so the activation record and the
selector evidence were re-fingerprinted; `activated` and
`activation_bindings` are unchanged.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run
alone with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_sway_whistle_sparrow_resource_skill` | 2 tests, OK |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK |
| `world.rules.tests.test_combat_modifiers.CombatModifierTests` | blocked by the repository test guard as a single label at 103 discovered tests (the limit is 100); the class ran as two explicit method batches of 52 and 51 tests, both OK |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK after the re-fingerprint |
| `world.rules.tests.test_monster_ai_activation.ActivationBindingTests` | 4 tests, OK |
| `world.rules.tests.test_monster_ai_activation.RollbackTests` | 3 tests, OK after the re-fingerprint |

The remaining gates also passed: the registry import check,
`uv run --locked python -m tools.map_reference_context` followed by
`--check`, `uv run --locked python -m tools.contract_gate --change
vine-net-spider-species` and `openspec validate vine-net-spider-species --strict`.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 苔冠巨鹿

This section records the sixth and last delivered species of the north deep
forest Wave 1. 苔冠巨鹿 (`moss_crown_stag`) is a high-tier, grade-B, solitary
giant-stag bruiser whose ordinary default variant is 老冠型
(`wood_crown_elder`). It carries the single-target earth strike 苔冠衝撞
(`moss_crown_charge`) and the area earth strike 苔冠橫掃 (`moss_crown_sweep`).

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table. The complete literal
profile is 460 hit points / 48 MP / 30 SP / 32 attack / 18 agility / 26 defense.

* Heavy bruiser: the authored hit points sit above the boar's shipped 380, the
  defense sits in the upper half of the high band (18–32), and the agility sits
  near that band's floor of 16.
* The MP pool holds one charge and two sweeps (12 + 16 + 16 = 44 ≤ 48), and the
  SP pool holds three of the larger sweeps (8 × 3 = 24 ≤ 30).
* Costs and coefficients repeat the boar's shipped charge and sweep shape; only
  the element differs (earth instead of fire).
* Grade B marks a dangerous solitary site boss, below the A-grade 蓄潮型.

### Reuse of the two-strike (single + area damage) representative

The kit's composition signature is
`(("active", "damage", "enemies", None), ("active", "damage", "enemies", None))`,
the shipped two-strike group. Its representative stays `warm_den_boar`: the new
variant key sorts after it, so the representative declaration and every shard,
seed and smoke registration stay unchanged. The existing
`world/rules/tests/test_monster_composition_coverage.py` derives every shipped
variant's signature and proves the new variant joins this group, while
`world/rules/tests/test_ember_bristle_boar_resource_skill.py` exercises the
group's single-target selection, area recipients, per-recipient hit and defense
outcomes, one payment per cast and the committed reload; no per-variant smoke
module is added for a reused signature.

### Decision mode

`wood_crown_elder` binds the shipped `pack_hunter` archetype and stays in the
permanent legacy decision, so it carries that archetype's flee threshold of
0.20. It authors neither intelligence, a decision-mode override nor a
`monster_behaviour.yaml` edit. The kit adds no buff definition or modifier rule,
so the startup tuning fingerprint did not move and the activation record and
selector evidence stay untouched; `activated` and `activation_bindings` are
unchanged.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run
alone with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_ember_bristle_boar_resource_skill` | 1 test, OK |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationBindingTests` | 4 tests, OK |
| `world.rules.tests.test_monster_ai_activation.RollbackTests` | 3 tests, OK |

The remaining gates also passed: the registry import check,
`uv run --locked python -m tools.map_reference_context` followed by
`--check`, `uv run --locked python -m tools.contract_gate --change
moss-crown-stag-species` and `openspec validate moss-crown-stag-species --strict`.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 霧泉蛙

This section records the first delivered species of the central mountains
Wave 2. 霧泉蛙 (`mist_spring_frog`) is a low-tier, grade-F, fragile colony
hopper whose ordinary default variant is 汲泉型 (`seep_sipper`), with the
stronger 泉主型 (`spring_keeper`). Both carry the single water tongue strike
霧舌汲取 (`mist_tongue_sip`).

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table.

* Fragile colony hopper: the ordinary variant's hit points and defense sit
  near the low band's floor, while its agility sits in that band's upper half.
* 汲泉型's MP pool holds two casts of the tongue's MP cost, and its SP pool
  holds three casts of the SP cost. The stronger 泉主型 carries a larger pool,
  which holds three and five casts respectively.
* The fixed MP drain (4) is far below the crocodile's fixed MP drain (10) and
  equals the bat's fixed HP drain, which suits a low-tier contact strike.
* The stronger 泉主型 holds a whole spring pool, so it carries a larger pool,
  attack and defense at grade E.

### Reuse of the contact drain representative

The kit's composition signature is
`(("active", "damage", "enemies", None), ("active", "gauge_transfer", "enemies", 0))`,
the shipped contact drain group. Its representative stays `bank_lurker`: both
new variant keys sort after it, so the representative declaration and every
shard, seed and smoke registration stay unchanged. The existing
`world/rules/tests/test_crocodile_resource_skill.py` exercises the group's
committed representative evidence; no per-variant smoke module is added for a
reused signature.

### Decision mode

Both variants bind the shipped `instinctive` archetype and stay in the
permanent legacy decision, so they carry that archetype's flee threshold of
0.35. Neither authors intelligence, a decision-mode override nor a
`monster_behaviour.yaml` edit. This link adds no buff definition or modifier
rule, so the startup tuning fingerprint does not move; the activation tests
passed and the evidence was left untouched, with `activated` and
`activation_bindings` unchanged.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run
alone with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_crocodile_resource_skill` | 1 test, OK |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationBindingTests` | 4 tests, OK |
| `world.rules.tests.test_monster_ai_activation.RollbackTests` | 3 tests, OK |

The remaining gates also passed: the registry import check,
`uv run --locked python -m tools.map_reference_context` followed by
`--check`, `uv run --locked python -m tools.contract_gate --change
mist-spring-frog-species` and `openspec validate mist-spring-frog-species --strict`.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 暖岩蠑螈

This section records the second delivered species of the central mountains
Wave 2. 暖岩蠑螈 (`warm_rock_salamander`) is a low-tier, grade-F, solitary
crevice crawler whose ordinary default variant is 曬岩型 (`ledge_basker`), with
the stronger 熱縫型 (`vent_crack_dweller`). Both carry the single fire strike
燃斑咬擊 (`ember_skin_bite`).

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table.

* Small solitary crawler: the ordinary variant's agility sits in the low band's
  lower half, and its defense equals the hare's ordinary 掘巢型 (`burrow_maker`).
* 曬岩型's MP pool holds two casts of the bite's MP cost, and its SP pool holds
  three casts of the SP cost.
* The flare (+2 physical attack for 15 s) is a low-tier self rise, below the
  shipped `atk_phys` precedents (+5).
* The stronger 熱縫型 lives by a warm vent, so it carries a larger pool and
  attack at grade E.

### Reuse of the self-guard strike representative

The kit's composition signature is
`(("active", "damage", "enemies", None), ("active", "self_buff_apply", "self", None))`,
the shipped self-guard strike group. Its representative stays `burrow_maker`:
both new variant keys sort after it, so the representative declaration and every
shard, seed and smoke registration stay unchanged. The existing
`world/rules/tests/test_tide_lamp_crab_resource_skill.py` exercises the group's
committed representative evidence; no per-variant smoke module is added for a
reused signature. The self mount raises physical attack rather than defense or
agility, which the modifier vocabulary already carries.

### Decision mode

Both variants bind the shipped `instinctive` archetype and stay in the
permanent legacy decision, so they carry that archetype's flee threshold of
0.35. Neither authors intelligence, a decision-mode override nor a
`monster_behaviour.yaml` edit. This link adds a timed effect and a modifier
rule, so the startup tuning fingerprint moved from `fc1dd263...` to
`3030d4a3...`; the selector report was regenerated under the new tuning, the
activation record and its rollback fingerprint (`1a134a96...`) were updated,
and `activated` and `activation_bindings` are unchanged.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run
alone from the worktree root with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_tide_lamp_crab_resource_skill` | 1 test, OK |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK |
| `world.rules.tests.test_combat_modifiers.CombatModifierTests` | 104 tests, OK (run through the Django test runner because the local focus guard caps `evennia test` discovery at 100) |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationBindingTests` | 4 tests, OK |
| `world.rules.tests.test_monster_ai_activation.RollbackTests` | 3 tests, OK |

The remaining gates also passed: the registry import check,
`uv run --locked python -m tools.map_reference_context` followed by
`--check`, `uv run --locked python -m tools.contract_gate --change
warm-rock-salamander-species` and `openspec validate
warm-rock-salamander-species --strict`.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 碎骨鷲

This section records the third delivered species of the central mountains Wave
2. 碎骨鷲 (`bone_breaker_vulture`) is a mid-tier, grade-D, pair-living soaring
flier whose ordinary default variant is 盤谷型 (`updraft_glider`), with the
stronger 崖巢型 (`crag_nest_vulture`). Both carry the single wind strike
揚礫撲擊 (`grit_wing_strike`).

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table.

* Soaring raider: the ordinary variant's agility sits in the mid band's middle,
  between the goat's ordinary 踏崖型 (`cliff_stepper`, agility 16) and the
  lynx's ordinary 林伏型 (`wood_stalker`, agility 20).
* Lightly armoured: its defense is one above the mid band's floor.
* 盤谷型's MP pool holds three casts of the strike's 10 MP cost, and its SP pool
  holds four casts of the 5 SP cost.
* The rider (−3 accuracy for 12 s) matches the sparrow's shipped accuracy
  magnitude and is milder than the lynx's −5.
* The stronger 崖巢型 guards a nest ledge at grade C with a larger pool.

### Reuse of the enemy hit-rider representative

The kit's composition signature is
`(("active", "damage", "enemies", None), ("active", "buff_apply", "enemies", 0))`,
the shipped enemy hit-rider group. Its representative stays `cliff_stepper`:
both new variant keys sort after it, so the representative declaration and every
shard, seed and smoke registration stay unchanged. The existing
`world/rules/tests/test_sway_whistle_sparrow_resource_skill.py` exercises the
group's committed representative evidence, and its `EnemyRiderGroupMemberTests`
derives the group's members from the shipped declarations, so both new variants
are exercised on their own rider axis with no test edit.

### Decision mode

Both variants bind the shipped `ambush_predator` archetype and stay in the
permanent legacy decision, so they carry that archetype's flee threshold of
0.20. Neither authors intelligence, a decision-mode override nor a
`monster_behaviour.yaml` edit. This link adds a timed effect and a modifier
rule, so the startup tuning fingerprint moved from `3030d4a3...` to
`f8858072...`; the selector report was regenerated under the new tuning, the
activation record and its rollback fingerprint (`a4c7376c...`) were updated,
and `activated` and `activation_bindings` are unchanged.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run
alone from the worktree root with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_sway_whistle_sparrow_resource_skill` | 2 tests, OK |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK |
| `world.rules.tests.test_combat_modifiers.CombatModifierTests` | 105 tests, OK (run through the Django test runner because the local focus guard caps `evennia test` discovery at 100) |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationBindingTests` | 4 tests, OK |
| `world.rules.tests.test_monster_ai_activation.RollbackTests` | 3 tests, OK |

The remaining gates also passed: the registry import check,
`uv run --locked python -m tools.map_reference_context` followed by
`--check`, `uv run --locked python -m tools.contract_gate --change
bone-breaker-vulture-species` and `openspec validate
bone-breaker-vulture-species --strict`.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 霧燈蛾

This section records the fourth delivered species of the central mountains Wave
2. 霧燈蛾 (`mist_lamp_moth`) is a mid-tier, grade-D, solitary night flier whose
ordinary default variant is 逐光型 (`lamp_seeker`), with the stronger 老翅型
(`old_veil_moth`). Both carry the single dark strike 鱗粉撲翅
(`veil_scale_flutter`).

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table.

* Fragile night flier: its hit points sit near the mid band's floor (115 against
  the floor of 110) and its defense is at the floor (10), while its agility
  (19) sits in the band's upper half.
* 逐光型's MP pool holds three casts of the strike's 10 MP cost, and its SP pool
  holds four casts of the 4 SP cost.
* The rider (−3 agility for 15 s) equals the goat's shipped
  `rock_echo_stagger_agility_flat` contribution and lifetime.
* The stronger 老翅型 holds one lamp all night at grade C with a larger pool
  (150 HP, 50 MP, 24 SP).

### Reuse of the enemy hit-rider representative

The kit's composition signature is
`(("active", "damage", "enemies", None), ("active", "buff_apply", "enemies", 0))`,
the shipped enemy hit-rider group. Its representative stays `cliff_stepper`:
both new variant keys sort after it, so the representative declaration and every
shard, seed and smoke registration stay unchanged. The existing
`world/rules/tests/test_sway_whistle_sparrow_resource_skill.py` exercises the
group's committed representative evidence, and its `EnemyRiderGroupMemberTests`
derives the group's members from the shipped declarations, so both new variants
are exercised on their own rider axis with no test edit.

### Decision mode

Both variants bind the shipped `ambush_predator` archetype and stay in the
permanent legacy decision, so they carry that archetype's flee threshold of
0.20. Neither authors intelligence, a decision-mode override nor a
`monster_behaviour.yaml` edit. This link adds a timed effect and a modifier
rule, so the startup tuning fingerprint moved from `f8858072...` to
`cd78725a...`; the selector report was regenerated under the new tuning, the
activation record and its rollback fingerprint (`def7776d...`) were updated,
and `activated` and `activation_bindings` are unchanged.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run
alone from the worktree root with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_sway_whistle_sparrow_resource_skill` | 2 tests, OK |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK |
| `world.rules.tests.test_combat_modifiers.CombatModifierTests` | 106 tests, OK, run as two focused method-label batches (100 + 6) because the local focus guard blocks the class label at 106 discovered tests |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationBindingTests` | 4 tests, OK |
| `world.rules.tests.test_monster_ai_activation.RollbackTests` | 3 tests, OK |

The remaining gates also passed: the registry import check,
`uv run --locked python -m tools.map_reference_context` followed by
`--check`, `uv run --locked python -m tools.contract_gate --change
mist-lamp-moth-species` and `openspec validate
mist-lamp-moth-species --strict`.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 霜鱗巨蟒

This section records the fifth delivered species of the central mountains Wave
2. 霜鱗巨蟒 (`rime_scale_serpent`) is a high-tier, grade-B, solitary constrictor
whose ordinary default variant is 霜谷型 (`white_rime_coil`). It carries the
single-target ice strike 霜牙噬擊 (`rime_fang_strike`) and the area ice strike
霜尾橫掃 (`rime_tail_lash`).

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table.

* Long-bodied ambusher: its hit points are above the stag's (500 against 460),
  its defense is below the stag's and sits in the high band's middle (24 in
  18–32), and its agility is a little above the band's floor (20 against 16).
* 霜谷型's MP pool holds one fang strike plus two lashes (12 + 16 + 16 = 44 ≤
  48), and its SP pool holds three of the larger casts (3 × 8 = 24 ≤ 30).
* The costs and coefficients repeat the boar's and the stag's shipped
  single-plus-area shape; only the element differs (ice).
* Grade B marks a dangerous solitary site boss, below the A-grade 蓄潮型.

### Reuse of the two-strike (single + area damage) representative

The kit's composition signature is
`(("active", "damage", "enemies", None), ("active", "damage", "enemies", None))`,
the shipped two-strike group. Its representative stays `warm_den_boar`:
`"warm_den_boar" < "white_rime_coil"`, so the representative declaration and
every shard, seed and smoke registration stay unchanged. The existing
`world/rules/tests/test_ember_bristle_boar_resource_skill.py` exercises the
group's committed representative evidence.

### Decision mode

The variant binds the shipped `pack_hunter` archetype and stays in the permanent
legacy decision, so it carries that archetype's flee threshold of 0.20. It
authors no intelligence, decision-mode override or `monster_behaviour.yaml`
edit. This link adds no timed effect or modifier, so the startup tuning
fingerprint did not move and the activation evidence was left untouched;
`activated` and `activation_bindings` are unchanged.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run
alone from the worktree root with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_ember_bristle_boar_resource_skill` | 1 test, OK |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_combat_modifiers.CombatModifierTests` | 106 tests, OK, run as two focused method-label batches (100 + 6) because the local focus guard caps `evennia test` discovery at 100 |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationBindingTests` | 4 tests, OK |
| `world.rules.tests.test_monster_ai_activation.RollbackTests` | 3 tests, OK |

The remaining gates also passed: the registry import check,
`uv run --locked python -m tools.map_reference_context` followed by
`--check`, `uv run --locked python -m tools.contract_gate --change
rime-scale-serpent-species` and `openspec validate
rime-scale-serpent-species --strict`.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 鼓翼松雞

This section records the sixth delivered species of the Wave 2 species chain and
the first northwest-highland Wave 2 species. 鼓翼松雞 (`drum_wing_grouse`) is a
low-tier, grade-F, gregarious ground grouse whose ordinary default variant is
林床型 (`pine_floor_grouse`). It carries the single-target wind strike 鼓翼驚飛
(`drum_wing_burst`).

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table.

* Ground bird with burst flight: its agility sits in the low band's upper half
  (9 for the ordinary variant and 11 for the stronger one, in 3–12), and its
  defense equals the hare's ordinary variant (3).
* 林床型's MP pool holds two casts of the burst (2 × 10 = 20) and its SP pool
  holds three casts (3 × 2 = 6); the stronger 領場型 holds three casts in MP
  (3 × 10 = 30 ≤ 30) and five in SP (5 × 2 = 10 ≤ 10).
* The burst grants +2 agility for 15 s, one below the rat's and the owl's
  shipped +3, a low-tier self rise.
* The stronger 領場型 holds the lek centre at grade E with a larger pool (56 HP
  against 32) and a stronger attack (9 against 4).

### Reuse of the self-guard strike representative

The kit's composition signature is
`(("active", "damage", "enemies", None), ("active", "self_buff_apply", "self", None))`,
the shipped self-guard strike group. Its representative stays `burrow_maker`:
both new variant keys sort after it
(`"burrow_maker" < "lek_master_cock" < "pine_floor_grouse"`), so the
representative declaration and every shard, seed and smoke registration stay
unchanged. The existing
`world/rules/tests/test_tide_lamp_crab_resource_skill.py` exercises the group's
committed representative evidence, while
`world/rules/tests/test_monster_composition_coverage.py` derives the group's
membership from the shipped declarations and confirms that `burrow_maker` stays
its representative. No variant-specific test is added.

### Decision mode

Both variants bind the shipped `instinctive` archetype and stay in the permanent
legacy decision, so they carry that archetype's flee threshold of 0.35. Neither
authors intelligence, a decision-mode override nor a `monster_behaviour.yaml`
edit. This link adds a timed effect and a modifier rule, so the startup tuning
fingerprint moved from `cd78725a...` to `d65909aa...`; the selector report was
regenerated under the new tuning, the activation record and its rollback
fingerprint (`2fa5c405...`) were updated, and `activated` and
`activation_bindings` are unchanged. The six archetype campaigns and the
performance report were not rerun and remain historical harness evidence at
`497df2c1...`, not evidence for this tuning.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run
alone from the worktree root with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_tide_lamp_crab_resource_skill` | 1 test, OK |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_combat_modifiers.CombatModifierTests` | 107 tests, OK, run as two focused method-label batches (100 + 7) because the local focus guard caps `evennia test` discovery at 100 |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationBindingTests` | 4 tests, OK |
| `world.rules.tests.test_monster_ai_activation.RollbackTests` | 3 tests, OK |
| `world.rules.tests.test_rule_id_test_correspondence` | 2 tests, OK |
| `world.rules.tests.test_status_display` | 3 tests, OK |
| `world.skills.tests.test_skill_registry.test_narration_coverage` | 15 tests, OK |

The remaining gates also passed: the registry import check,
`uv run --locked python -m tools.map_reference_context` followed by
`--check`, `uv run --locked python -m tools.contract_gate --change
drum-wing-grouse-species` and `openspec validate
drum-wing-grouse-species --strict`. The committed manifest files
`.github/evennia-shards.json`, `tools/test_data_lint_seed.json` and
`tools/test_data_freeze.json` are unchanged.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 泥壩河狸

This section records the seventh delivered species of the Wave 2 species chain
and the second northwest-highland Wave 2 species. 泥壩河狸 (`mud_dam_beaver`) is
a low-tier, grade-F, family-living beaver whose ordinary default variant is
築壩型 (`dam_builder`). It carries the single-target earth strike 泥甲尾擊
(`mud_pelt_slap`).

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table.

* Sturdy family builder: its defense equals the porcupine's ordinary variant
  (6) and sits one above the crab's (5), while its agility stays below the
  hare's ordinary variant (4 against 8).
* 築壩型's MP pool holds two casts of the slap (2 × 10 = 20) and its SP pool
  holds three casts (3 × 3 = 9); the stronger 老壩型 holds three casts in MP
  (3 × 10 = 30 ≤ 30) and five in SP (5 × 3 = 15 ≤ 15).
* The guard grants +2 defense for 20 s, matching the crab's and the porcupine's
  shipped self-guard, the smallest shipped self-guard.
* The stronger 老壩型 keeps the family's oldest dam at grade E with the low
  band's defense ceiling (8).

### Reuse of the self-guard strike representative

The kit's composition signature is
`(("active", "damage", "enemies", None), ("active", "self_buff_apply", "self", None))`,
the shipped self-guard strike group. Its representative stays `burrow_maker`:
both new variant keys sort after it
(`"burrow_maker" < "dam_builder" < "old_dam_keeper"`), so the representative
declaration and every shard, seed and smoke registration stay unchanged. The
existing `world/rules/tests/test_tide_lamp_crab_resource_skill.py` exercises the
group's committed representative evidence, while
`world/rules/tests/test_monster_composition_coverage.py` derives the group's
membership from the shipped declarations and confirms that `burrow_maker` stays
its representative. No variant-specific test is added.

### Decision mode

Both variants bind the shipped `instinctive` archetype and stay in the permanent
legacy decision, so they carry that archetype's flee threshold of 0.35. Neither
authors intelligence, a decision-mode override nor a `monster_behaviour.yaml`
edit. This link adds a timed effect and a modifier rule, so the startup tuning
fingerprint moved from `d65909aa...` to `3232b667...`; the selector report was
regenerated under the new tuning, the activation record and its rollback
fingerprint (`129487ea...`) were updated, and `activated` and
`activation_bindings` are unchanged. The six archetype campaigns and the
performance report were not rerun and remain historical harness evidence at
`497df2c1...`, not evidence for this tuning.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run from
the worktree root with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <labels>`:

| labels | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` + `world.lore.tests.test_monster_visuals` | 24 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` + `world.rules.tests.test_tide_lamp_crab_resource_skill` + `world.rules.tests.test_rule_id_test_correspondence` + `world.rules.tests.test_status_display` | 10 tests, OK |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` + `world.skills.tests.test_skill_registry.test_narration_coverage` | 21 tests, OK |
| `world.rules.tests.test_combat_modifiers.CombatModifierTests` | 108 tests, OK, run as two focused method-label batches (100 + 8) because the local focus guard caps `evennia test` discovery at 100 |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` + `.ActivationBindingTests` + `.RollbackTests` | 11 tests, OK after re-fingerprinting; before it, `ActivationRecordTests` failed 1 of 4 and `RollbackTests` failed 2 of 3, each on the recorded fingerprint comparison, as designed |

The remaining gates also passed: the registry import check,
`uv run --locked python -m tools.map_reference_context` followed by `--check`,
`uv run --locked python -m tools.contract_gate --change
mud-dam-beaver-species` (reference-context, traceability 2726/2726 covered,
observability, test-data, manifests and 19 contract tests) and `openspec
validate mud-dam-beaver-species --strict`. The committed manifest files
`.github/evennia-shards.json`, `tools/test_data_lint_seed.json` and
`tools/test_data_freeze.json` are unchanged.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 礦脈鼴

This section records the eighth delivered species of the Wave 2 species chain
and the third northwest-highland Wave 2 species. 礦脈鼴 (`ore_vein_mole`) is a
low-tier, grade-F, solitary mole whose ordinary default variant is 掘脈型
(`vein_digger`). It carries the single-target earth strike 揚砂爪刨
(`grit_claw_scrape`).

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table.

* Solitary burrower: the ordinary variant's agility sits in the low band's
  lower half (3–12, so at or below 7), and its defense sits between the hare's
  ordinary variant (3) and the crab's ordinary variant (5).
* 掘脈型's MP pool holds two casts of the scrape (2 × 10 = 20) and its SP pool
  holds four casts (4 × 2 = 8), the scrape costing 10 MP and 2 SP.
* The rider is −3 accuracy for 10 s, exactly the sparrow's shipped
  `grain_rattle_accuracy` contribution and lifetime.
* The stronger 深脈型 holds a deep nest chamber at grade E with the larger pool
  and the higher defense of the pair.

### Reuse of the enemy hit-rider representative

The kit's composition signature is
`(("active", "damage", "enemies", None), ("active", "buff_apply", "enemies", 0))`,
the shipped enemy hit-rider group. Its representative stays `cliff_stepper`:
both new variant keys sort after it (`"cliff_stepper" < "deep_seam_mole" <
"vein_digger"`), so the representative declaration and every shard, seed and
smoke registration stay unchanged. The existing
`world/rules/tests/test_sway_whistle_sparrow_resource_skill.py` exercises the
group's committed representative evidence, while
`world/rules/tests/test_monster_composition_coverage.py` derives the group's
membership from the shipped declarations and confirms that `cliff_stepper` stays
its representative. No variant-specific test is added.

### Decision mode

Both variants bind the shipped `instinctive` archetype and stay in the permanent
legacy decision, so they carry that archetype's flee threshold of 0.35. Neither
authors intelligence, a decision-mode override nor a `monster_behaviour.yaml`
edit. This link adds a timed effect and a modifier rule, so the startup tuning
fingerprint moved from `3232b667...` to `abb0989c...`; the selector report was
regenerated under the new tuning, the activation record and its rollback
fingerprint (`129487ea...` to `1582c6d3...`) were updated, and `activated` and
`activation_bindings` are unchanged. The six archetype campaigns and the
performance report were not rerun and remain historical harness evidence at
`497df2c1...`, not evidence for this tuning.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run from
the worktree root with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <labels>`:

| labels | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` + `world.rules.tests.test_sway_whistle_sparrow_resource_skill` | 6 tests, OK |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_combat_modifiers.CombatModifierTests` | 109 tests, OK, run as two focused method-label batches (55 + 54) because the local focus guard caps `evennia test` discovery at 100 |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` + `.ActivationBindingTests` + `.RollbackTests` | 11 tests, OK after re-fingerprinting; before it, `ActivationRecordTests` failed 1 of 4 and `RollbackTests` failed 2 of 3, each on the recorded fingerprint comparison, as designed |

The remaining gates also passed: the registry import check,
`uv run --locked python -m tools.map_reference_context` followed by `--check`,
`uv run --locked python -m tools.contract_gate --change
ore-vein-mole-species` (reference-context, traceability 2726/2726 covered,
observability, test-data, manifests and 19 contract tests) and `openspec
validate ore-vein-mole-species --strict`. The committed manifest files
`.github/evennia-shards.json`, `tools/test_data_lint_seed.json` and
`tools/test_data_freeze.json` are unchanged.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 掠藏獾

This section records the ninth delivered species of the Wave 2 species chain
and the fourth northwest-highland Wave 2 species. 掠藏獾
(`cache_raider_wolverine`) is a mid-tier, grade-D, solitary wolverine whose
ordinary default variant is 掠索型 (`trapline_raider`). It carries the
single-target elementless strike 鉗顎扳咬 (`jaw_lock_bite`), the first monster
ability that lowers the struck target's defense.

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table.

* Tenacious ground raider: hit points sit in the mid band's lower half
  (110–230, so at or below 170), defense at its middle (10–16), and agility in
  its lower half (10–24); the stronger 冬穴型 sits in the band's upper half.
* The kit spends no MP, so the MP pool is zero; the ordinary variant's SP pool
  holds four casts of the bite's SP cost (4 × 6 = 24) and the stronger 冬穴型
  holds six (6 × 6 = 36).
* The rider (−2 defense for 15 s) is the first monster defense rider; its size
  equals the goblin's shipped −2 rider, the smallest shipped hit-rider
  magnitude.
* The stronger 冬穴型 guards its snow cache at grade C.
* The damage formula clamps the struck entity's defense at zero, so the −2
  rider never amplifies damage against a defenseless target.

### Reuse of the enemy hit-rider representative

The kit's composition signature is
`(("active", "damage", "enemies", None), ("active", "buff_apply", "enemies", 0))`,
the shipped enemy hit-rider group. Its representative stays `cliff_stepper`:
both new variant keys sort after it (`"cliff_stepper" < "trapline_raider" <
"winter_den_glutton"`), so the representative declaration and every shard, seed
and smoke registration stay unchanged. The existing
`world/rules/tests/test_sway_whistle_sparrow_resource_skill.py` exercises the
group's committed representative evidence, while
`world/rules/tests/test_monster_composition_coverage.py` derives the group's
membership from the shipped declarations and confirms that `cliff_stepper`
stays its representative. No variant-specific test is added.

### Decision mode

Both variants bind the shipped `ambush_predator` archetype and stay in the
permanent legacy decision, so they carry that archetype's flee threshold of
0.20. Neither authors intelligence, a decision-mode override nor a
`monster_behaviour.yaml` edit. This link adds a timed effect and a modifier
rule, so the startup tuning fingerprint moved from `abb0989c...` to
`03ad9da4...`; the selector report was regenerated under the new tuning, the
activation record and its rollback fingerprint (`1582c6d3...` to
`66c7e8a0...`) were updated, and `activated` and `activation_bindings` are
unchanged. The six archetype campaigns and the performance report were not
rerun and remain historical harness evidence at `497df2c1...`, not evidence
for this tuning.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run from
the worktree root with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_sway_whistle_sparrow_resource_skill` | 2 tests, OK |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_combat_modifiers.CombatModifierTests` | 110 tests, OK, run as two focused method-label batches (55 + 55) because the local focus guard caps `evennia test` discovery at 100 |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK |
| `.ActivationBindingTests` | 4 tests, OK |
| `.RollbackTests` | 3 tests, OK after re-fingerprinting; before it, `ActivationRecordTests` failed 1 of 4 and `RollbackTests` failed 2 of 3, each on the recorded fingerprint comparison, as designed |

The remaining gates also passed: the registry import check,
`uv run --locked python -m tools.map_reference_context` followed by `--check`,
`uv run --locked python -m tools.contract_gate --change
cache-raider-wolverine-species` (reference-context, traceability 2726/2726
covered, observability, test-data, manifests and 19 contract tests) and
`openspec validate cache-raider-wolverine-species --strict`. The committed
manifest files `.github/evennia-shards.json`, `tools/test_data_lint_seed.json`
and `tools/test_data_freeze.json` are unchanged.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 礦巢獅鷲

This section records the tenth delivered species of the Wave 2 species chain
and the fifth northwest-highland Wave 2 species. 礦巢獅鷲
(`ore_nest_griffin`) is a high-tier, grade-B griffin whose ordinary default
variant is 巔巢型 (`windcrest_elder`). It carries two wind strikes: the
single-target dive 俯衝裂爪 (`ore_crest_dive`) and the area wing gale
振翼風壓 (`ore_crest_gale`).

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table.

* Aerial striker: agility sits near the high band's upper end (16–30, so 26),
  hit points fall between the boar's (380) and the stag's (460), and defense
  sits in the band's lower half (18–32, so 21).
* MP holds one dive plus two gales (12 + 16 + 16 = 44 ≤ 48); SP holds three of
  the larger casts (3 × 8 = 24 ≤ 30).
* Costs and coefficients repeat the boar's and the stag's shipped
  single-plus-area shape; only the element differs (wind).
* Grade B marks a dangerous site boss, below the A-grade 蓄潮型.
* `magic_power` is zero: the kit's riders are damage occurrences only, so no
  timed effect, modifier or status row is authored.

### Reuse of the two-strike (single + area damage) representative

The kit's composition signature is
`(("active", "damage", "enemies", None), ("active", "damage", "enemies", None))`,
the shipped two-strike group. Its representative stays `warm_den_boar`: the new
variant key sorts after it (`"warm_den_boar" < "windcrest_elder"`), so the
representative declaration and every shard, seed and smoke registration stay
unchanged. The existing
`world/rules/tests/test_ember_bristle_boar_resource_skill.py` exercises the
group's committed representative evidence, while
`world/rules/tests/test_monster_composition_coverage.py` derives the group's
membership from the shipped declarations and confirms that `warm_den_boar`
stays its representative. No variant-specific test is added.

### Decision mode

The variant binds the shipped `pack_hunter` archetype and stays in the
permanent legacy decision, so it carries that archetype's flee threshold of
0.20. It authors neither intelligence, a decision-mode override nor a
`monster_behaviour.yaml` edit. This link adds no timed effect or modifier, so
the startup tuning fingerprint did not move; the activation record, the
rollback fingerprint and the selector evidence stay untouched, and `activated`
and `activation_bindings` are unchanged.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run from
the worktree root with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_ember_bristle_boar_resource_skill` | 1 test, OK |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK |
| `.ActivationBindingTests` | 4 tests, OK |
| `.RollbackTests` | 3 tests, OK |

The remaining gates also passed: the registry import check,
`uv run --locked python -m tools.map_reference_context` followed by `--check`,
`uv run --locked python -m tools.contract_gate --change
ore-nest-griffin-species` and `openspec validate ore-nest-griffin-species
--strict`. The committed manifest files `.github/evennia-shards.json`,
`tools/test_data_lint_seed.json` and `tools/test_data_freeze.json` are
unchanged.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 滾土甲蟲

This section records the first delivered species of the eastern plains Wave 3.
滾土甲蟲 (`clod_ball_beetle`) is a low-tier scarab beetle whose ordinary default
variant is 滾球型 (`road_ball_roller`) and whose stronger variant is 育堆型
(`heap_brood_keeper`). Both carry the single earth strike 鏟頭滾球
(`clod_ball_shove`), a hit-rider that lowers the struck enemy's flat agility.

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table. The complete literal
profile and its authored grade live only in `world/lore/monster_species.py`
and are band-checked at import.

* Armoured slow pusher: the ordinary variant's authored defense equals the
  beaver's ordinary 築壩型, and its agility sits in the low band's lower half
  (3–12).
* MP holds two casts of the shove's MP cost on the ordinary variant and three
  on 育堆型; the ordinary variant's SP holds three casts of its SP cost, while
  育堆型 holds five.
* The rider (−2 agility for 12 s) equals the goblin's shipped −2 agility rider,
  the smallest shipped agility debuff.
* The stronger 育堆型 guards a brood heap at grade E with the low band's defense
  ceiling.

### Reuse of the enemy hit-rider representative

The kit's composition signature is
`(("active", "damage", "enemies", None), ("active", "buff_apply", "enemies", 0))`,
the shipped enemy hit-rider group. Its representative stays `cliff_stepper`: both
new variant keys sort after it (`"cliff_stepper" < "heap_brood_keeper"` and
`"cliff_stepper" < "road_ball_roller"`), so the representative declaration and
every shard, seed and smoke registration stay unchanged. The existing
`world/rules/tests/test_sway_whistle_sparrow_resource_skill.py` exercises the
group's committed representative evidence, while
`world/rules/tests/test_monster_composition_coverage.py` derives the group's
membership from the shipped declarations and confirms that `cliff_stepper`
stays its representative. No variant-specific test is added.

### Decision mode

Both variants bind the shipped `instinctive` archetype and stay in the permanent
legacy decision, so they carry that archetype's flee threshold of 0.35. Neither
variant authors intelligence, a decision-mode override nor a
`monster_behaviour.yaml` edit. This link adds one timed effect and one modifier,
so the startup tuning fingerprint moved from `03ad9da4...` to `5f4a4506...`; the
selector report was regenerated under the new tuning, the activation record and
its rollback fingerprint (`66c7e8a0...` to `cb5ead22...`) were updated, and
`activated` and `activation_bindings` are unchanged. The six archetype campaigns
and the performance report were not rerun and remain historical harness evidence
at `497df2c1...`, not evidence for this tuning.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run from
the worktree root with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_sway_whistle_sparrow_resource_skill` | 2 tests, OK |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK |
| `world.rules.tests.test_combat_modifiers.CombatModifierTests` | 111 tests, OK, run as two focused method-label batches (56 + 55) because the local focus guard caps `evennia test` discovery at 100 |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK |
| `.ActivationBindingTests` | 4 tests, OK |
| `.RollbackTests` | 3 tests, OK |

The registry import check reports the 48 registered variants, and the remaining
gates passed: `uv run --locked python -m tools.map_reference_context` followed by
`--check`, `uv run --locked python -m tools.contract_gate --change
clod-ball-beetle-species` and `openspec validate clod-ball-beetle-species
--strict`. The committed manifest files `.github/evennia-shards.json`,
`tools/test_data_lint_seed.json` and `tools/test_data_freeze.json` are
unchanged.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 揚塵野馬

This section records the second delivered species of the eastern plains Wave 3.
揚塵野馬 (`dust_mane_horse`) is a mid-tier wild horse whose ordinary default
variant is 奔原型 (`plain_runner`) and whose stronger variant is 頭馬型
(`herd_stallion`). Both carry the single wind strike 疾蹄踢擊
(`dust_gallop_kick`), whose brief self agility rise mounts on the caster for
every resolved attempt.

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table. The complete literal
profile and its authored grade live only in `world/lore/monster_species.py`
and are band-checked at import.

* Herd runner: the ordinary variant's authored agility sits in the upper half of
  the mid band (10–24) and equals the lynx's ordinary 林伏型, while its defense
  is one above the band's floor.
* MP holds three casts of the kick's MP cost on the ordinary variant; SP holds
  four casts of its SP cost.
* The gallop (+3 agility for 15 s) equals the rat's shipped self agility rise.
* The stronger 頭馬型 leads the herd at grade C with a larger pool.

### Reuse of the self-guard strike representative

The kit's composition signature is
`(("active", "damage", "enemies", None), ("active", "self_buff_apply", "self", None))`,
the shipped self-guard strike group. Its representative stays `burrow_maker`:
both new variant keys sort after it (`"burrow_maker" < "herd_stallion"` and
`"burrow_maker" < "plain_runner"`), so the representative declaration and every
shard, seed and smoke registration stay unchanged. The existing
`world/rules/tests/test_tide_lamp_crab_resource_skill.py` exercises the group's
committed representative evidence, while
`world/rules/tests/test_monster_composition_coverage.py` derives the group's
membership from the shipped declarations and confirms that `burrow_maker`
stays its representative. No variant-specific test is added.

### Decision mode

Both variants bind the shipped `pack_hunter` archetype and stay in the permanent
legacy decision, so they carry that archetype's flee threshold of 0.20. Neither
variant authors intelligence, a decision-mode override nor a
`monster_behaviour.yaml` edit. This link adds one timed effect and one modifier,
so the startup tuning fingerprint moved from `5f4a4506...` to `955832b5...`; the
selector report was regenerated under the new tuning, the activation record and
its rollback fingerprint (`cb5ead22...` to `4e289789...`) were updated, and
`activated` and `activation_bindings` are unchanged. The six archetype campaigns
and the performance report were not rerun and remain historical harness evidence
at `497df2c1...`, not evidence for this tuning.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run from
the worktree root with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_tide_lamp_crab_resource_skill` | 1 test, OK |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK |
| `world.rules.tests.test_combat_modifiers.CombatModifierTests` | 112 tests, OK, run as two focused method-label batches (56 + 56) because the local focus guard caps `evennia test` discovery at 100 |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK |
| `.ActivationBindingTests` | 4 tests, OK |
| `.RollbackTests` | 3 tests, OK |

The registry import check reports the 50 registered variants, and the remaining
gates passed: `uv run --locked python -m tools.map_reference_context` followed by
`--check`, `uv run --locked python -m tools.contract_gate --change
dust-mane-horse-species` and `openspec validate dust-mane-horse-species
--strict`. The committed manifest files `.github/evennia-shards.json`,
`tools/test_data_lint_seed.json` and `tools/test_data_freeze.json` are
unchanged.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 渠矛蒼鷺

This section records the third delivered species of the eastern plains Wave 3.
渠矛蒼鷺 (`sluice_spear_heron`) is a mid-tier wading bird whose ordinary default
variant is 涉渠型 (`sluice_wader`) and whose stronger variant is 林巢型
(`heronry_elder`). Both carry the single elementless strike 矛喙疾刺
(`spear_beak_jab`), whose brief accuracy drop mounts on the struck enemy only
after the jab lands.

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table. The complete literal
profile and its authored grade live only in `world/lore/monster_species.py`
and are band-checked at import.

* Patient wading striker: the ordinary variant's authored agility sits in the
  upper half of the mid band (10–24), its defense is exactly at the band's
  floor, and its hit points sit in the lower part of the band.
* The kit spends no MP, so the MP pool is zero; SP holds four casts of the
  jab's SP cost on the ordinary variant.
* The rider (−3 accuracy for 12 s) matches the sparrow's shipped accuracy
  magnitude and is milder than the lynx's −5.
* The stronger 林巢型 guards a heronry at grade C with a larger pool.

### Reuse of the enemy hit-rider representative

The kit's composition signature is
`(("active", "damage", "enemies", None), ("active", "buff_apply", "enemies", 0))`,
the shipped enemy hit-rider group. Its representative stays `cliff_stepper`:
both new variant keys sort after it (`"cliff_stepper" < "heronry_elder"` and
`"cliff_stepper" < "sluice_wader"`), so the representative declaration and
every shard, seed and smoke registration stay unchanged. The existing
`world.rules.tests.test_sway_whistle_sparrow_resource_skill` exercises the
group's committed representative evidence, and its `EnemyRiderGroupMemberTests`
derives the group's membership from the shipped declarations and exercises each
member's own rider axis;
`world.rules.tests.test_monster_composition_coverage` keeps the derivation that
leaves `cliff_stepper` this group's representative. No variant-specific test is
added.

### Decision mode

Both variants bind the shipped `ambush_predator` archetype and stay in the
permanent legacy decision, so they carry that archetype's flee threshold of
0.20. Neither variant authors intelligence, a decision-mode override nor a
`monster_behaviour.yaml` edit. This link adds one timed effect and one modifier,
so the startup tuning fingerprint moved from `955832b5...` to `b0dd9da6...`; the
selector report was regenerated under the new tuning, the activation record and
its rollback fingerprint (`4e289789...` to `9d55a75c...`) were updated, and
`activated` and `activation_bindings` are unchanged. The six archetype campaigns
and the performance report were not rerun and remain historical harness evidence
at `497df2c1...`, not evidence for this tuning.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run from
the worktree root with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_sway_whistle_sparrow_resource_skill` | 2 tests, OK |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK |
| `world.rules.tests.test_combat_modifiers.CombatModifierTests` | 113 tests, OK, run as two focused method-label batches (57 + 56) because the local focus guard caps `evennia test` discovery at 100 |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK |
| `.ActivationBindingTests` | 4 tests, OK |
| `.RollbackTests` | 3 tests, OK |

The registry import check reports the 52 registered variants, and the remaining
gates passed: `uv run --locked python -m tools.map_reference_context` followed by
`--check`, `uv run --locked python -m tools.contract_gate --change
sluice-spear-heron-species` and `openspec validate sluice-spear-heron-species
--strict`. The committed manifest files `.github/evennia-shards.json`,
`tools/test_data_lint_seed.json` and `tools/test_data_freeze.json` are
unchanged.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 湖丘巨龜

This section records the fourth delivered species of the eastern plains Wave 3
and the high-tier link of that chain. 湖丘巨龜 (`lake_mound_turtle`) is a
solitary giant snapping turtle whose ordinary and only variant is 丘背型
(`wide_mound_elder`). It carries the two earth strikes 碎顎咬合
(`lake_mound_bite`) and 背甲震地 (`lake_mound_quake`), the site's armoured
bruiser kit.

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table. The complete literal
profile and its authored grade live only in `world/lore/monster_species.py`
and are band-checked at import.

* Armoured lake boss: its defense sits near the high band's ceiling (30 of 32),
  its agility is exactly at the band's floor (16), and its hit points (500) sit
  between the boar's ordinary 380 and the A-grade 蓄潮型's 520.
* MP holds one bite plus two slams (12 + 16 + 16 = 44 ≤ 48); SP holds three of
  the larger casts (3 × 8 = 24 ≤ 30).
* Costs and coefficients repeat the boar's, the stag's and the griffin's
  shipped single-plus-area shape (1.2 single, 0.8 area, 12 + 6 / 16 + 8); the
  element is earth, as for the stag.
* Grade B: a dangerous site boss, below the A-grade 蓄潮型.

### Reuse of the two-strike (single + area damage) representative

The kit's composition signature is
`(("active", "damage", "enemies", None), ("active", "damage", "enemies", None))`,
the shipped two-strike (single + area damage) group. Its representative stays
`warm_den_boar`: the one new variant key sorts after it
(`"warm_den_boar" < "wide_mound_elder"`), so the representative declaration and
every shard, seed and smoke registration stay unchanged. The existing
`world.rules.tests.test_ember_bristle_boar_resource_skill` exercises the
group's committed representative evidence, and
`world.rules.tests.test_monster_composition_coverage` keeps the derivation that
leaves `warm_den_boar` this group's representative. No variant-specific test is
added.

### Decision mode

`wide_mound_elder` binds the shipped `ambush_predator` archetype and stays in
the permanent legacy decision, so it carries that archetype's flee threshold of
0.20. It authors neither intelligence nor a decision-mode override, and this
link adds no timed effect, modifier or `monster_behaviour.yaml` edit. The
startup tuning fingerprint therefore stayed at `b0dd9da6...`; no activation
evidence was re-fingerprinted, and `activated` and `activation_bindings` are
unchanged.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run from
the worktree root with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_ember_bristle_boar_resource_skill` | 1 test, OK |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK |
| `.ActivationBindingTests` | 4 tests, OK |
| `.RollbackTests` | 3 tests, OK |

The registry import check reports the 53 registered variants, and the remaining
gates passed: `uv run --locked python -m tools.map_reference_context` followed by
`--check`, `uv run --locked python -m tools.contract_gate --change
lake-mound-turtle-species` and `openspec validate lake-mound-turtle-species
--strict`. The committed manifest files `.github/evennia-shards.json`,
`tools/test_data_lint_seed.json` and `tools/test_data_freeze.json` are
unchanged.

The `world.rules.tests.test_combat_modifiers.CombatModifierTests` regression was
also run, as two focused method-label batches (57 + 56) totalling 113 tests and
both OK, because the local focus guard caps `evennia test` discovery at 100.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 灘跳魚

This section records the fifth delivered species of the Wave 3 species chain and
the first southeast-coast species of that wave. 灘跳魚 (`flat_leap_goby`) is a
low-tier mudskipper whose ordinary default variant is 跳灘型 (`mudflat_skipper`)
and whose stronger variant is 築塔型 (`turret_keeper`). Both carry the single
elementless strike 甩尾濺泥 (`mud_tail_flick`), a hit-rider that lowers the
struck enemy's accuracy.

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table. The complete literal
profile and its authored grade live only in `world/lore/monster_species.py`
and are band-checked at import.

* Fragile mudflat hopper: the ordinary variant's hit points sit near the low
  band's floor (25–70) and its agility sits in the band's upper half (3–12).
* The kit spends no MP, so both MP pools are zero; the ordinary variant's SP
  holds three casts of the slap's 3 SP cost, and the stronger variant holds
  five.
* The rider (−2 accuracy for 12 s) is the smallest monster accuracy rider,
  below the sparrow's and the mushroom's −3.
* The stronger 築塔型 guards a mud turret at grade E.

### Reuse of the enemy hit-rider representative

The kit's composition signature is
`(("active", "damage", "enemies", None), ("active", "buff_apply", "enemies", 0))`,
the shipped enemy hit-rider group. Its representative stays `cliff_stepper`: both
new variant keys sort after it (`"cliff_stepper" < "mudflat_skipper"` and
`"cliff_stepper" < "turret_keeper"`), so the representative declaration and
every shard, seed and smoke registration stay unchanged. The existing
`world/rules/tests/test_sway_whistle_sparrow_resource_skill.py` exercises the
group's committed representative evidence, while
`world/rules/tests/test_monster_composition_coverage.py` derives the group's
membership from the shipped declarations and confirms that `cliff_stepper`
stays its representative. No variant-specific test is added.

### Decision mode

Both variants bind the shipped `instinctive` archetype and stay in the permanent
legacy decision, so they carry that archetype's flee threshold of 0.35. Neither
variant authors intelligence, a decision-mode override nor a
`monster_behaviour.yaml` edit. This link adds one timed effect and one modifier,
so the startup tuning fingerprint moved from `b0dd9da6...` to `75b74aa1...`; the
selector report was regenerated under the new tuning, the activation record and
its rollback fingerprint (`9d55a75c...` to `92205e80...`) were updated, and
`activated` and `activation_bindings` are unchanged. The six archetype campaigns
and the performance report were not rerun and remain historical harness evidence
at `497df2c1...`, not evidence for this tuning.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run from
the worktree root with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_sway_whistle_sparrow_resource_skill` | 2 tests, OK |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK |
| `world.rules.tests.test_combat_modifiers.CombatModifierTests` | 114 tests, OK, run as two focused method-label batches (57 + 57) because the local focus guard caps `evennia test` discovery at 100 |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK |
| `.ActivationBindingTests` | 4 tests, OK |
| `.RollbackTests` | 3 tests, OK |

The registry import check reports the 55 registered variants, and the remaining
gates passed: `uv run --locked python -m tools.map_reference_context` followed by
`--check`, `uv run --locked python -m tools.contract_gate --change
flat-leap-goby-species` and `openspec validate flat-leap-goby-species
--strict`. The committed manifest files `.github/evennia-shards.json`,
`tools/test_data_lint_seed.json` and `tools/test_data_freeze.json` are
unchanged.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 桅風海鷗

This section records the sixth delivered species of the Wave 3 species chain and
the second southeast-coast species of that wave. 桅風海鷗 (`mast_wind_gull`) is a
low-tier harbour gull whose ordinary default variant is 繞桅型 (`mast_circler`)
and whose stronger variant is 堤群型 (`stack_colony_elder`). Both carry the
single wind strike 掠風啄擊 (`wind_snatch_dive`), a dive peck that mounts its own
agility lift on every resolved attempt.

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table. The complete literal
profile and its authored grade live only in `world/lore/monster_species.py`
and are band-checked at import.

* Light harbour flier: the ordinary variant's agility sits near the low band's
  ceiling (3–12), its defense rests on the band's floor (2) and its hit points
  sit in the band's lower part (25–70).
* The peck costs 10 MP and 3 SP, so the ordinary variant's MP holds two casts
  and its SP holds three; the stronger variant's MP holds three casts and its
  SP holds five.
* The gust (+2 agility for 15 s) is below the rat's shipped self agility rise
  (+3).
* The stronger 堤群型 leads a breakwater colony at grade E.

### Reuse of the self-guard strike representative

The kit's composition signature is
`(("active", "damage", "enemies", None), ("active", "self_buff_apply", "self", None))`,
the shipped self-guard strike group. Its representative stays `burrow_maker`
(築埂兔 `ridge_burrow_hare`): both new variant keys sort after it
(`"burrow_maker" < "mast_circler"` and `"burrow_maker" < "stack_colony_elder"`),
so the representative declaration and every shard, seed and smoke registration
stay unchanged. The existing
`world/rules/tests/test_tide_lamp_crab_resource_skill.py` exercises the group's
committed representative evidence, while
`world/rules/tests/test_monster_composition_coverage.py` derives the group's
membership from the shipped declarations and confirms that `burrow_maker`
stays its representative. No variant-specific test is added.

### Decision mode

Both variants bind the shipped `instinctive` archetype and stay in the permanent
legacy decision, so they carry that archetype's flee threshold of 0.35. Neither
variant authors intelligence, a decision-mode override nor a
`monster_behaviour.yaml` edit. This link adds one timed effect and one modifier,
so the startup tuning fingerprint moved from `75b74aa1...` to `5828d932...`; the
selector report was regenerated under the new tuning, the activation record and
its rollback fingerprint (`92205e80...` to `561da0df...`) were updated, and
`activated` and `activation_bindings` are unchanged. The six archetype campaigns
and the performance report were not rerun and remain historical harness evidence
at `497df2c1...`, not evidence for this tuning.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run from
the worktree root with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_tide_lamp_crab_resource_skill` | 1 test, OK |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK |
| `world.rules.tests.test_combat_modifiers.CombatModifierTests` | 115 tests, OK, run as two focused method-label batches (58 + 57) because the local focus guard caps `evennia test` discovery at 100 |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK |
| `.ActivationBindingTests` | 4 tests, OK |
| `.RollbackTests` | 3 tests, OK after re-fingerprinting; before it, `ActivationRecordTests` failed 1 of 4 and `RollbackTests` failed 2 of 3, each on the recorded fingerprint comparison, as designed |

The registry import check reports the 57 registered variants, and the remaining
gates passed: `uv run --locked python -m tools.map_reference_context` followed by
`--check`, `uv run --locked python -m tools.contract_gate --change
mast-wind-gull-species` and `openspec validate mast-wind-gull-species
--strict`. The committed manifest files `.github/evennia-shards.json`,
`tools/test_data_lint_seed.json` and `tools/test_data_freeze.json` are
unchanged.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 臥堤海豹

This section records the seventh delivered species of the Wave 3 species chain
and the third southeast-coast species of that wave. 臥堤海豹 (`breakwater_seal`)
is a mid-tier harbour seal whose ordinary default variant is 曬堤型
(`pier_basker`) and whose stronger variant is 霸灘型 (`haulout_bull`). Both carry
the single elementless strike 滑身壓撞 (`flipper_slide_slam`), a hit-rider that
lowers the struck enemy's agility.

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table. The complete literal
profile and its authored grade live only in `world/lore/monster_species.py`
and are band-checked at import.

* Heavy colony slider: the ordinary variant's hit points and defense sit in the
  middle of the mid band (110–230 hit points, 10–16 defense), the stronger
  variant raises both, and both keep agility near the band's floor (10).
* The kit spends no MP, so both MP pools are zero; the ordinary variant's SP
  holds four casts of the slam's 6 SP cost, and the stronger variant holds six.
* The rider (−3 agility for 15 s) equals the goat's shipped agility rider.
* The stronger 霸灘型 holds a sandbar at grade C.

### Reuse of the enemy hit-rider representative

The kit's composition signature is
`(("active", "damage", "enemies", None), ("active", "buff_apply", "enemies", 0))`,
the shipped enemy hit-rider group. Its representative stays `cliff_stepper`: both
new variant keys sort after it (`"cliff_stepper" < "haulout_bull"` and
`"cliff_stepper" < "pier_basker"`), so the representative declaration and every
shard, seed and smoke registration stay unchanged. The existing
`world/rules/tests/test_sway_whistle_sparrow_resource_skill.py` exercises the
group's committed representative evidence, while
`world/rules/tests/test_monster_composition_coverage.py` derives the group's
membership from the shipped declarations and confirms that `cliff_stepper`
stays its representative. No variant-specific test is added.

### Decision mode

Both variants bind the shipped `ambush_predator` archetype and stay in the
permanent legacy decision, so they carry that archetype's flee threshold of
0.20. The design originally named `pack_hunter`, but its
`highest_expected_damage` ranking weighs an elementless physical kit level with
the innate `basic_attack` and breaks the tie with a die, while the shipped
`EnemyRiderGroupMemberTests` contract requires a legacy member's own decision to
return its kit; `ambush_predator` keeps the same `lowest_hp` target strategy and
the same 0.20 threshold and selects the kit deterministically through
`first_owned`. Neither variant authors intelligence, a decision-mode override nor a
`monster_behaviour.yaml` edit. This link adds one timed effect and one modifier,
so the startup tuning fingerprint moved from `5828d932...` to `ef4b4b14...`; the
selector report was regenerated under the new tuning, the activation record and
its rollback fingerprint (`561da0df...` to `5a57f049...`) were updated, and
`activated` and `activation_bindings` are unchanged. The six archetype campaigns
and the performance report were not rerun and remain historical harness evidence
at `497df2c1...`, not evidence for this tuning.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run from
the worktree root with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_sway_whistle_sparrow_resource_skill` | 2 tests, OK |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK |
| `world.rules.tests.test_combat_modifiers.CombatModifierTests` | 116 tests, OK, run as two focused method-label batches (58 + 58) because the local focus guard caps `evennia test` discovery at 100 |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK |
| `.ActivationBindingTests` | 4 tests, OK |
| `.RollbackTests` | 3 tests, OK after re-fingerprinting; before it, `ActivationRecordTests` failed 1 of 4 and `RollbackTests` failed 2 of 3, each on the recorded fingerprint comparison, as designed |

The registry import check succeeds and the registry holds 59 variants
(`len(MONSTER_VARIANT_REGISTRY)` printed 59); the remaining gates passed:
`uv run --locked python -m tools.map_reference_context` followed by `--check`,
`uv run --locked python -m tools.contract_gate --change
breakwater-seal-species` and `openspec validate breakwater-seal-species
--strict`. The committed manifest files `.github/evennia-shards.json`,
`tools/test_data_lint_seed.json` and `tools/test_data_freeze.json` are
unchanged.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 負鹽蟻

This section records the first delivered species of the southwest coast Wave 4.
負鹽蟻 (`salt_column_ant`) is a low-tier harvester ant whose ordinary default
variant is 搬鹽型 (`salt_hauler`, grade F) and whose stronger variant is 守丘型
(`salt_mound_soldier`, grade E); both own the single bite 銜鹽拖咬
(`salt_jaw_haul`).

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table. The complete literal
profile and its authored grade live only in `world/lore/monster_species.py` and
are band-checked at import.

* Small column worker: the authored agility sits in the low band's middle,
  while defense and hit points sit in their lower part.
* The kit spends no MP, so the authored MP pool is zero; the SP pool holds
  three casts of the bite's SP cost (five on 守丘型).
* The rider (−2 agility for 12 s) equals the goblin's shipped −2 agility rider.
* The stronger 守丘型 guards a salt-crusted nest mound at grade E.

### Reuse of the enemy hit-rider representative

The kit declares the shipped enemy hit-rider signature
`(("active", "damage", "enemies", None), ("active", "buff_apply", "enemies",
0))`. Its representative is unchanged: `cliff_stepper`, declared in
`world.rules.tests.test_sway_whistle_sparrow_resource_skill`. Both new variant
keys sort after that representative, so no smoke module, shard entry or seed
entry is added; `EnemyRiderGroupMemberTests` derives the whole group from the
shipped declarations and exercises both new members on their own rider axis.

### Decision mode

Both variants bind the legacy `instinctive` archetype: `first_owned` skill
choice against the lowest-hit-point enemy, with that archetype's authored flee
threshold of 0.35. No intelligence value, decision-mode override or
`monster_behaviour.yaml` edit is authored. Because the archetype selects the
first owned kit deterministically, the group-member contract does not depend on
a damage tie-break.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run from
the worktree root with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_sway_whistle_sparrow_resource_skill` | 2 tests, OK, run twice consecutively |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK, run twice consecutively |
| `world.rules.tests.test_combat_modifiers.CombatModifierTests` | 117 tests, OK, run as two exhaustive focused method-label batches (59 + 58) because the local focus guard caps `evennia test` discovery at 100 |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK |
| `.ActivationBindingTests` | 4 tests, OK |
| `.RollbackTests` | 3 tests, OK after re-fingerprinting; before it, `ActivationRecordTests` failed 1 of 4 and `RollbackTests` failed 2 of 3, each on the recorded fingerprint comparison, as designed |

The registry import check succeeds and the registry holds 61 variants
(`len(MONSTER_VARIANT_REGISTRY)` printed 61); the remaining gates passed:
`uv run --locked python -m tools.map_reference_context` followed by `--check`,
`uv run --locked python -m tools.contract_gate --change
salt-column-ant-species` and `openspec validate salt-column-ant-species
--strict`. The committed manifest files `.github/evennia-shards.json`,
`tools/test_data_lint_seed.json` and `tools/test_data_freeze.json` are
unchanged.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 硬腕海星

This section records the second delivered species of the southwest coast Wave 4.
硬腕海星 (`stiff_arm_starfish`) is a low-tier sea star whose ordinary default
variant is 爬架型 (`oyster_rack_creeper`, grade F) and whose stronger variant is
老礁型 (`tide_pool_elder`, grade E); both own the single arm press 硬腕撲壓
(`stiff_arm_press`).

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table. The complete literal
profile and its authored grade live only in `world/lore/monster_species.py` and
are band-checked at import.

* Slow armoured creeper: the authored defense sits in the low band's upper part,
  agility at its floor, and hit points in its middle.
* The kit spends no MP, so the authored MP pool is zero; the SP pool holds three
  casts of the press's SP cost (five on 老礁型).
* The guard (+2 defense for 20 s) equals the crab's shipped self guard.
* The stronger 老礁型 holds a deep cliff-foot pool at grade E with the low band's
  defense ceiling.

### Reuse of the self-guard strike representative

The kit declares the shipped self-guard strike signature
`(("active", "damage", "enemies", None), ("active", "self_buff_apply", "self",
None))`. Its representative is unchanged: `burrow_maker`, declared in
`world.rules.tests.test_tide_lamp_crab_resource_skill`, whose production smoke
exercises the representative and the derived group. Both new variant keys sort
after that representative, so no smoke module, shard entry or seed entry is
added; `world.rules.tests.test_monster_composition_coverage` derives the whole
group from the shipped declarations and checks the representative wiring.

### Decision mode

Both variants bind the legacy `instinctive` archetype: `first_owned` skill
choice against the lowest-hit-point enemy, with that archetype's authored flee
threshold of 0.35. No intelligence value, decision-mode override or
`monster_behaviour.yaml` edit is authored. Because the archetype selects the
first owned kit deterministically, the group-member and parallel-gauge contracts
do not depend on a damage tie-break.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run from
the worktree root with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_tide_lamp_crab_resource_skill` | 1 test, OK, run twice consecutively |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK, run twice consecutively |
| `world.rules.tests.test_combat_modifiers.CombatModifierTests` | 118 tests, OK, run as two exhaustive disjoint focused method-label batches (59 + 59) because the local focus guard caps `evennia test` discovery at 100 |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK |
| `.ActivationBindingTests` | 4 tests, OK |
| `.RollbackTests` | 3 tests, OK after re-fingerprinting; before it, `ActivationRecordTests` failed 1 of 4 and `RollbackTests` failed 2 of 3, each on the recorded fingerprint comparison, as designed |

The registry import check succeeds and the registry holds 63 variants
(`len(MONSTER_VARIANT_REGISTRY)` printed 63); the remaining gates passed:
`uv run --locked python -m tools.map_reference_context` followed by `--check`,
`uv run --locked python -m tools.contract_gate --change
stiff-arm-starfish-species` and `openspec validate
stiff-arm-starfish-species --strict`. The committed manifest files
`.github/evennia-shards.json`, `tools/test_data_lint_seed.json` and
`tools/test_data_freeze.json` are unchanged.

This link adds one timed effect and one modifier, so the startup tuning
fingerprint moved from `383b1eff...` to `70e5f38d...`; the selector report was
regenerated under the new tuning, the activation record and its rollback
fingerprint (`ca010d35...` to `c99f82a5...`) were updated, and `activated` and
`activation_bindings` are unchanged. The six archetype campaigns and the
performance report were not rerun and remain historical harness evidence at
`497df2c1...`, not evidence for this tuning.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 碎殼蝦

This section records the third delivered species of the southwest coast Wave 4.
碎殼蝦 (`shell_crack_shrimp`) is a mid-tier mantis shrimp whose ordinary default
variant is 穴擊型 (`reef_burrow_striker`, grade D) and whose stronger variant is
深穴型 (`seawall_den_holder`, grade C); both own the single club strike 錘肢彈擊
(`club_limb_strike`).

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table. The complete literal
profile and its authored grade live only in `world/lore/monster_species.py` and
are band-checked at import.

* Burrow ambusher: the authored attack sits in the mid band's upper part,
  agility above the band's middle, and defense and hit points in its lower
  part.
* The kit spends no MP, so the authored MP pool is zero; the SP pool holds four
  casts of the strike's SP cost (six on 深穴型).
* The rider (−2 defense for 15 s) equals the wolverine's shipped −2 defense
  rider.
* The stronger 深穴型 holds a seawall den at grade C with the mid band's attack
  ceiling.

### Reuse of the enemy hit-rider representative

The kit declares the shipped enemy hit-rider composition signature
`(("active", "damage", "enemies", None), ("active", "buff_apply", "enemies", 0))`.
Its representative is unchanged: `cliff_stepper`, declared in
`world.rules.tests.test_sway_whistle_sparrow_resource_skill`, whose production
smoke exercises the representative and the derived group. Both new variant keys
sort after that representative, so no smoke module, shard entry or seed entry is
added; `world.rules.tests.test_monster_composition_coverage` derives the whole
group from the shipped declarations and checks the representative wiring, and
`EnemyRiderGroupMemberTests` in the same module exercises every derived member,
including both of these, on its own rider axis.

### Decision mode

Both variants bind the legacy `ambush_predator` archetype: `first_owned` skill
choice against the lowest-hit-point enemy, with that archetype's authored flee
threshold of 0.20. No intelligence value, decision-mode override or
`monster_behaviour.yaml` edit is authored. Because `first_owned` selects the
only owned kit deterministically, the group-member and parallel-gauge contracts
do not depend on a damage tie-break, so no deterministic-profile deviation from
the design was needed; the group-member and resource contract labels were run
twice consecutively with identical results.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run from
the worktree root with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_sway_whistle_sparrow_resource_skill` | 2 tests, OK, run twice consecutively |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK, run twice consecutively |
| `world.rules.tests.test_combat_modifiers.CombatModifierTests` | 119 tests, OK, run as two exhaustive disjoint focused method-label batches (60 + 59) because the local focus guard caps `evennia test` discovery at 100 |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK |
| `.ActivationBindingTests` | 4 tests, OK |
| `.RollbackTests` | 3 tests, OK after re-fingerprinting; before it, `ActivationRecordTests` failed 1 of 4 and `RollbackTests` failed 2 of 3, each on the recorded fingerprint comparison, as designed |

The registry import check succeeds and the registry holds 65 variants
(`len(MONSTER_VARIANT_REGISTRY)` printed 65); the remaining gates passed:
`uv run --locked python -m tools.map_reference_context` followed by `--check`,
`uv run --locked python -m tools.contract_gate --change
shell-crack-shrimp-species` and `openspec validate
shell-crack-shrimp-species --strict`. The committed manifest files
`.github/evennia-shards.json`, `tools/test_data_lint_seed.json` and
`tools/test_data_freeze.json` are unchanged.

This link adds one timed effect and one modifier, so the startup tuning
fingerprint moved from `70e5f38d...` to `877fdd6d...`; the selector report was
regenerated under the new tuning, the activation record and its rollback
fingerprint (`c99f82a5...` to `3bc2239f...`) were updated, and `activated` and
`activation_bindings` are unchanged. The six archetype campaigns and the
performance report were not rerun and remain historical harness evidence at
`497df2c1...`, not evidence for this tuning.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 噴鹽鬣蜥

This section records the fourth delivered species of the southwest coast Wave 4.
噴鹽鬣蜥 (`salt_snort_iguana`) is a mid-tier marine iguana whose ordinary default
variant is 曬崖型 (`seacliff_basker`, grade D) and whose stronger variant is
冠刺型 (`salt_dike_holder`, grade C); both own the single head butt 噴鹽頂撞
(`brine_snort_butt`).

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table. The complete literal
profile and its authored grade live only in `world/lore/monster_species.py` and
are band-checked at import.

* Heavy basker: the authored defense sits in the mid band's upper part, agility
  near its floor, and hit points just below the band's middle.
* The kit spends no MP, so the authored MP pool is zero; the SP pool holds four
  casts of the butt's SP cost (six on 冠刺型).
* The rider (−3 accuracy for 15 s) matches the mushroom's shipped −3 accuracy
  rider in size and lasts three seconds longer.
* The stronger 冠刺型 holds the warmest dike stretch at grade C with the mid
  band's defense ceiling.

### Reuse of the enemy hit-rider representative

The kit declares the shipped enemy hit-rider composition signature
`(("active", "damage", "enemies", None), ("active", "buff_apply", "enemies", 0))`.
Its representative is unchanged: `cliff_stepper`, declared in
`world.rules.tests.test_sway_whistle_sparrow_resource_skill`, whose production
smoke exercises the representative and the derived group. Both new variant keys
sort after that representative, so no smoke module, shard entry or seed entry is
added; `world.rules.tests.test_monster_composition_coverage` derives the whole
group from the shipped declarations and checks the representative wiring, and
`EnemyRiderGroupMemberTests` in the same module exercises every derived member,
including both of these, on its own rider axis.

### Decision mode

Both variants bind the legacy `instinctive` archetype: `first_owned` skill
choice against the lowest-hit-point enemy, with that archetype's authored flee
threshold of 0.35. No intelligence value, decision-mode override or
`monster_behaviour.yaml` edit is authored. Because `first_owned` selects the
only owned kit deterministically, the group-member and resource contract
contracts do not depend on a damage tie-break, so no deterministic-profile
deviation from the design was needed; the group-member and resource contract
labels were run twice consecutively with identical results.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run from
the worktree root with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_sway_whistle_sparrow_resource_skill` | 2 tests, OK, run twice consecutively |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK, run twice consecutively |
| `world.rules.tests.test_combat_modifiers.CombatModifierTests` | 120 tests, OK, run as two exhaustive disjoint focused method-label batches (60 + 60) because the local focus guard caps `evennia test` discovery at 100 |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK |
| `.ActivationBindingTests` | 4 tests, OK |
| `.RollbackTests` | 3 tests, OK after re-fingerprinting; before it, `ActivationRecordTests` failed 1 of 4 and `RollbackTests` failed 2 of 3, each on the recorded fingerprint comparison, as designed |

The registry import check succeeds and the registry holds 67 variants
(`len(MONSTER_VARIANT_REGISTRY)` printed 67); the remaining gates passed:
`uv run --locked python -m tools.map_reference_context` followed by `--check`,
`uv run --locked python -m tools.contract_gate --change
salt-snort-iguana-species` and `openspec validate
salt-snort-iguana-species --strict`. The committed manifest files
`.github/evennia-shards.json`, `tools/test_data_lint_seed.json` and
`tools/test_data_freeze.json` are unchanged.

This link adds one timed effect and one modifier, so the startup tuning
fingerprint moved from `877fdd6d...` to `8b56d98c...`; the selector report was
regenerated under the new tuning, the activation record and its rollback
fingerprint (`3bc2239f...` to `4c696e11...`) were updated, and `activated` and
`activation_bindings` are unchanged. The six archetype campaigns and the
performance report were not rerun and remain historical harness evidence at
`497df2c1...`, not evidence for this tuning.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 沉船巨蛸

This section records the fifth delivered species of the southwest coast Wave 4.
沉船巨蛸 (`wreck_arm_octopus`) is a high-tier sea-cave octopus whose ordinary
default variant is 沉骸型 (`wreck_den_elder`, grade B); it owns the single arm
bind 觸腕絞纏 (`wreck_arm_bind`) and the area arm sweep 群腕橫掃
(`wreck_arm_sweep`).

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table. The complete literal
profile and its authored grade live only in `world/lore/monster_species.py` and
are band-checked at import.

* Reach-heavy sea-cave boss: agility above the high band's floor, defense in its
  lower part, and hit points between the boar's and the turtle's.
* The MP pool holds one bind plus two sweeps (12 + 16 + 16 = 44 of the authored
  48); the SP pool holds three of the larger casts (three times eight of the
  authored 30).
* The two costs and coefficients repeat the boar's and the turtle's
  single-plus-area shape, and the element is water, as for the crocodile's bite.
* Grade B: a dangerous site boss, below the A-grade 蓄潮型.

### Reuse of the two-strike (single + area damage) representative

The kit declares the shipped two-strike composition signature
`(("active", "damage", "enemies", None), ("active", "damage", "enemies", None))`.
Its representative is unchanged: `warm_den_boar`, declared in
`world.rules.tests.test_ember_bristle_boar_resource_skill`, whose production
smoke exercises the representative and the derived group. The new variant key
sorts after that representative (`"warm_den_boar" < "wreck_den_elder"`), so no
smoke module, shard entry or seed entry is added;
`world.rules.tests.test_monster_composition_coverage` derives the whole group
from the shipped declarations and checks the representative wiring.

### Decision mode

The variant binds the legacy `ambush_predator` archetype: `lowest_hp` targeting,
`first_owned` skill choice, with that archetype's authored flee threshold of
0.20. No intelligence value, decision-mode override or `monster_behaviour.yaml`
edit is authored.

This is the design's one recorded deviation. D2's first choice was
`pack_hunter`, but its `highest_expected_damage` choice cannot select this kit
deterministically: `_choose_skill` compares only the actor's adjusted attack
against the defender's defense and ignores the coefficient, so `wreck_arm_bind`
and the innate `basic_attack` — both physical, both in the owned key list — tie
and consume one tie-break die, which is exactly what the shipped boar smoke has
to pin. `ambush_predator` preserves the design's targeting and flee semantics
(`lowest_hp` and the same 0.20 threshold) and its `first_owned` choice makes the
arm bind the deterministic single-target selection; it is also the archetype
the shipped two-strike kit 湖丘巨龜 binds for the identical single-plus-area
shape. The trade-off, stated rather than hidden: the archetype carries no area
preference, so the legacy body always opens on the single-target arm bind and
never selects 群腕橫掃, exactly as the turtle's area slam behaves today. The
area row stays declared, contract-checked and reproduced by the composition
group, and the public prose still describes what the kit does.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run from
the worktree root with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_ember_bristle_boar_resource_skill` | 1 test, OK, run twice consecutively |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK, run twice consecutively |
| `world.rules.tests.test_combat_modifiers.CombatModifierTests` | 120 tests, OK, run as two exhaustive disjoint focused method-label batches (60 + 60) because the local focus guard caps `evennia test` discovery at 100 |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK |
| `.ActivationBindingTests` | 4 tests, OK |
| `.RollbackTests` | 3 tests, OK |

The registry import check succeeds and the registry holds 38 species and 68
variants. A throwaway focused probe, run twice consecutively and deleted
afterwards (`world.rules.tests.test_wreck_arm_octopus_selection_probe`, 4
tests, OK both times), constructed `wreck_den_elder` and asserted with
`dice.roll_d100` patched to raise: a two-opponent field selects
`wreck_arm_bind` against the lowest-hit-point enemy twice in a row, the area
sweep is never selected, a drained MP and SP pool falls back to `basic_attack`
without dice, and 20% of the authored maximum hit points is the flee boundary
while 21% still attacks. The probe was not committed, because design D7
authors no test file and a committed module would need a shard entry this
change does not touch.

The remaining gates passed:
`uv run --locked python -m tools.map_reference_context` followed by `--check`,
`uv run --locked python -m tools.contract_gate --change
wreck-arm-octopus-species` and `openspec validate wreck-arm-octopus-species
--strict`. The committed manifest files `.github/evennia-shards.json`,
`tools/test_data_lint_seed.json` and `tools/test_data_freeze.json` are
unchanged.

This link adds no timed effect, modifier, intelligence value or mode entry, so
the startup tuning fingerprint did not move and stays `8b56d98c...`, with the
rollback tuning unchanged at `4c696e11...`; `activated` and
`activation_bindings` are unchanged and the activation and manual evidence
files are untouched. The six archetype campaigns and the performance report
remain historical harness evidence at `497df2c1...`, not evidence for this
tuning.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 坑道灶馬

This section records the first delivered species of the western hills Wave 4.
坑道灶馬 (`shaft_leap_cricket`) is a low-tier cave cricket whose ordinary
default variant is 躍窖型 (`cellar_leaper`, grade F); it owns the single hind
kick 蓄腿蹬踢 (`coiled_hind_kick`), and 守坑型 (`old_shaft_leaper`, grade E) is
the older individual that leads the swarm at an abandoned shaft mouth.

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table. The complete literal
profile and its authored grade live only in `world/lore/monster_species.py` and
are band-checked at import.

* Light cellar leaper: agility one below the low band's ceiling, defense one
  above the band floor, and hit points in the band's lower part.
* The kit spends no MP, so the MP pool is zero; the SP pool holds three casts
  of the kick's cost on 躍窖型 and five casts on 守坑型.
* The lift (+2 agility for 15 s) is below the rat's shipped self agility rise
  (+3), so this species' own mount is the weaker of the two.
* The stronger 守坑型 leads a swarm at an abandoned shaft mouth at grade E: a
  local, avoidable threat, not a site boss.

### Reuse of the self-guard strike representative

The kit declares the shipped self-guard strike composition signature
`(("active", "damage", "enemies", None), ("active", "self_buff_apply", "self",
None))`. Its representative is unchanged: `burrow_maker`, declared in
`world.rules.tests.test_tide_lamp_crab_resource_skill`, whose production smoke
exercises the representative itself. Both new variant keys sort after that
representative (`"burrow_maker" < "cellar_leaper" < "old_shaft_leaper"`), so
no smoke module, shard entry or seed entry is added;
`world.rules.tests.test_monster_composition_coverage` derives the whole group
from the shipped declarations, so it establishes these variants' membership and
the representative wiring without executing every member.

### Decision mode

Both variants bind the legacy `instinctive` archetype: `lowest_hp` targeting,
`first_owned` skill choice, with that archetype's authored flee threshold of
0.35. No intelligence value, decision-mode override or `monster_behaviour.yaml`
edit is authored, so the startup tuning moves only through this change's new
buff definition and modifier rule.

The kit's determinism was observed rather than assumed. A temporary probe,
run twice consecutively and deleted afterwards
(`world.rules.tests.test_shaft_leap_cricket_selection_probe`, 2 tests, OK both
times), constructed both variants through the production construction entry
point and decided through `combat_session.policies._enemy_policy` with
`world.rules.monster_behaviour.dice.roll_d100` patched to raise: against one
unique lowest-hit-point opponent each variant selected `coiled_hind_kick`
twice in a row with no selection die, a drained SP pool fell back to
`basic_attack` without dice, and the inclusive 35% flee edge was reproduced
(the edge flees, one hit point above it selects the kit). The probe was not
committed, because design D7 authors no test file and a committed module would
need a shard entry this change does not touch. Equal-hit-point targets keep
the ordinary target-selection tie-break, which is unrelated to skill choice.

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run from
the worktree root with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK, run twice consecutively |
| `world.rules.tests.test_tide_lamp_crab_resource_skill` | 1 test, OK, run twice consecutively |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK |
| `world.rules.tests.test_combat_modifiers.CombatModifierTests` | 121 tests, OK, run as two exhaustive disjoint focused method-label batches (61 + 60) collected once from the class and split because the local focus guard caps `evennia test` discovery at 100 |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK after re-fingerprinting; before it, 1 of 4 failed on the recorded fingerprint comparison |
| `.ActivationBindingTests` | 4 tests, OK |
| `.RollbackTests` | 3 tests, OK after re-fingerprinting; before it, 2 of 3 failed on the recorded fingerprint comparison |

The registry import check succeeds and the registry holds 39 species and 70
variants. The remaining gates passed:
`uv run --locked python -m tools.map_reference_context` followed by `--check`,
`uv run --locked python -m tools.contract_gate --change
shaft-leap-cricket-species` and `openspec validate shaft-leap-cricket-species
--strict`. The committed manifest files `.github/evennia-shards.json`,
`tools/test_data_lint_seed.json` and `tools/test_data_freeze.json` are
unchanged.

This link adds one timed effect and one modifier, so the startup tuning
fingerprint moved from `8b56d98c...` to `7c1cafd7...`; the selector report was
regenerated under the new tuning at its own baseline commit `18141b8a...`, the
activation record and its rollback fingerprint (`4c696e11...` to `6639e736...`)
were updated, and `activated` and `activation_bindings` are unchanged. The six
archetype campaigns and the performance report were not rerun and remain
historical harness evidence at `497df2c1...`, not evidence for this tuning.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.

## 陷坑蟻獅

### Role constraints and the chosen literals

The design fixes roles, not numbers, so the review states the relation each
chosen literal holds rather than repeating a value table. The complete literal
profile and its authored grade live only in `world/lore/monster_species.py` and
are band-checked at import.

* Pit ambusher: the ordinary 伏坑型 holds attack in the mid band's upper half,
  defense in its middle, hit points in its lower half, and agility near its
  floor. The stronger 大坑型 keeps the same attack and agility relations and
  lifts its hit points above the band's midpoint with defense toward the top.
* The kit spends no MP, so the MP pool is zero; the SP pool holds four casts
  of the bite's six-point cost on 伏坑型 and six casts on 大坑型.
* The rider (−3 agility for 15 s) equals the goat's shipped
  `rock_echo_stagger_agility_flat` contribution and lifetime.
* The stronger 大坑型 holds the widest spoil-heap pit at grade C: a local,
  avoidable threat, not a site boss.

### Reuse of the enemy hit-rider representative

The kit declares the shipped enemy hit-rider composition signature
`(("active", "damage", "enemies", None), ("active", "buff_apply", "enemies", 0))`.
Its representative is unchanged: `cliff_stepper`, declared in
`world.rules.tests.test_sway_whistle_sparrow_resource_skill`, whose production
smoke exercises the representative itself. Both new variant keys sort after
that representative (`"cliff_stepper" < "quarry_pit_lurker" <
"spoil_heap_elder"`), so no smoke module, shard entry or seed entry is added.
The existing `EnemyRiderGroupMemberTests` in that module derives the whole group
from the shipped declarations and exercises both new variants on their own
rider axis through a landed hit, a miss and a committed reload; it also asserts
that each member's legacy decision returns its damage kit against a lone enemy.

### Decision mode

Both variants bind the legacy `ambush_predator` archetype: `lowest_hp` targeting,
`first_owned` skill choice, with that archetype's authored flee threshold of
0.20. No intelligence value, decision-mode override or `monster_behaviour.yaml`
edit is authored, so the startup tuning moves only through this change's new
buff definition and modifier rule.

The derived group-member check constructs both variants through the production
construction entry point and asks the shipped behaviour policy for their action
against one living enemy; each variant returns `sand_toss_pincer` targeted at
that enemy. `first_owned` takes the sole owned damage skill and a lone enemy
leaves no target tie to break, so this path spends no selection die. The check
was run twice consecutively and passed both times (2 tests each, OK).

### Focused commands and results

`/tmp/mud-species.env` contains `MUD_TEST_SETTINGS=1`. Every label was run from
the worktree root with
`uv run --locked --env-file=/tmp/mud-species.env evennia test --settings test_settings.py --keepdb <label>`:

| label | result |
| --- | --- |
| `world.lore.tests.test_monster_species_content` | 17 tests, OK |
| `world.lore.tests.test_monster_visuals` | 7 tests, OK |
| `world.lore.tests.test_bestiary_documentation` | 13 tests, OK |
| `world.rules.tests.test_monster_composition_coverage` | 4 tests, OK |
| `world.rules.tests.test_sway_whistle_sparrow_resource_skill` | 2 tests, OK, run twice consecutively |
| `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests` | 4 tests, OK, run twice consecutively |
| `world.rules.tests.test_combat_modifiers.CombatModifierTests` | 122 tests, OK, run as two exhaustive disjoint focused method-label batches (61 + 61) collected once from the class and split because the local focus guard caps `evennia test` discovery at 100 |
| `world.skills.tests.test_narration_catalog` | 42 tests, OK |
| `world.skills.tests.test_skill_registry.test_out_of_combat_policy` | 6 tests, OK |
| `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` | 4 tests, OK after re-fingerprinting; before it, 1 of 4 failed on the recorded fingerprint comparison |
| `.ActivationBindingTests` | 4 tests, OK |
| `.RollbackTests` | 3 tests, OK after re-fingerprinting; before it, 2 of 3 failed on the recorded fingerprint comparison |

The registry import check succeeds and the registry holds 40 species and 72
variants. The remaining gates passed:
`uv run --locked python -m tools.map_reference_context` followed by `--check`,
`uv run --locked python -m tools.contract_gate --change
pit-sand-antlion-species` and `openspec validate pit-sand-antlion-species
--strict`. The committed manifest files `.github/evennia-shards.json`,
`tools/test_data_lint_seed.json` and `tools/test_data_freeze.json` are
unchanged.

This link adds one timed effect and one modifier, so the startup tuning
fingerprint moved from `7c1cafd7...` to `bd82767e...`; the selector report was
regenerated under the new tuning at its own baseline commit `b456b01a...`, the
activation record and its rollback fingerprint (`6639e736...` to `56152d3a...`)
were updated, and `activated` and `activation_bindings` are unchanged. The six
archetype campaigns and the performance report were not rerun and remain
historical harness evidence at `497df2c1...`, not evidence for this tuning.

### Human review of the prose

The prose was transcribed from this change's design and is pending human
editorial review in the ledger.
