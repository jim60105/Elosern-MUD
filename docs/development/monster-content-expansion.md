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
* Two sweeps spend more than the authored SP pool, so a later MP-exhaustion
  probe would have been vacuous, and subtracting one from one skill's cost
  leaves the cheaper skill affordable. Adopted: the pools are restored before
  each exhaustion probe, and each probe sits below the cheapest kit cost of
  that resource.
* Comparing cumulative hit points after the first sweep would not prove
  per-recipient defense mitigation. Adopted: the second sweep records each
  recipient's own pre-cast value and compares that cast's two losses, with the
  roster order fixed so the hit and miss land on the intended recipients.
* The single-target strike was only selected, never settled. Adopted: the
  smoke resolves the selected charge as well, observing its damage, its single
  MP/SP payment and the untouched ally control.
