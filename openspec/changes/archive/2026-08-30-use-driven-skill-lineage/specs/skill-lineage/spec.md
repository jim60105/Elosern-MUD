## ADDED Requirements

### Requirement: SkillPrerequisite declares registry edges and load validation fails closed
`world/skills/registry.py` SHALL define the frozen, slotted dataclass
`SkillPrerequisite(skill_key: str, min_proficiency: int)` with `min_proficiency >= 1`, and `SkillDef`
SHALL carry `prerequisites: tuple[SkillPrerequisite, ...] = ()`. Registry load SHALL validate, in
order and fail-closed (an exception names every violator): (1) every `prerequisites.skill_key`
exists in `SKILL_REGISTRY`; (2) the prerequisite graph is acyclic — a topological sort that raises
naming the offending cycle; (3) every `min_proficiency` is an integer >= 1; (4) a skill with no
prerequisites is a tree root; (5) the reverse-edge map (skill -> consuming edges) is computed and
cached at load. The structure is an n-ary DAG: a skill may be consumed by any number of edges
(branching) and may declare any number of prerequisites (merging); every mechanical rule is
degree-independent.

#### Scenario: A dangling prerequisite key fails the load
- **WHEN** a registry entry declares `prerequisites=(SkillPrerequisite("not_a_skill", 3),)`
- **THEN** registry load raises naming the entry and the unknown key

#### Scenario: A cycle names itself at load
- **WHEN** entries `a` and `b` prereq each other
- **THEN** registry load raises from the topological sort and the exception text names the cycle

#### Scenario: A zero threshold fails the load
- **WHEN** an entry declares `min_proficiency=0`
- **THEN** registry load raises naming the entry

#### Scenario: The reverse-edge map is cached
- **WHEN** the lineage tip-cap query asks which edges consume `fire_arrow`
- **THEN** it resolves from the load-time cache without walking the registry again

### Requirement: The fire lineage ships as the first-round linear tree
`SKILL_REGISTRY` SHALL carry prerequisite edges forming the fire tree:
`fire_ball` requires `fire_arrow` >= 3; `scorching_wave` requires `fire_ball` >= 3; `firestorm`
requires `scorching_wave` >= 3; `lava_burst` requires `firestorm` >= 5; `dragon_flame` requires
`lava_burst` >= 8; `phoenix_eternal_flame` requires `dragon_flame` >= 8. The sister spells declare
leaf edges onto the same spine in the same change: `infernal_wrap` requires `scorching_wave` >= 3,
`hellfire` requires `firestorm` >= 5, and `world_ending_blaze` requires `hellfire` >= 5 — none of
them is consumed by a further edge, so `phoenix_eternal_flame` stays the strict topological canopy.
`fire_arrow` is a root with no prerequisites. The structure is therefore a chain with sister LEAVES
(one node may feed several edges), not a single-file list. The five element-mastery passives SHALL
NOT be tree nodes (PASSIVE skills are never consumed by edges and never accrue).

#### Scenario: The fire tree validates with the canopy last
- **WHEN** the registry loads with the fire edges
- **THEN** the topological order runs `fire_arrow` first and `phoenix_eternal_flame` last (consumed
  by no edge), and every edge threshold is >= 1

#### Scenario: Mastery passives stay out of the graph
- **WHEN** the reverse-edge map is inspected for `fire_mastery`
- **THEN** no entry is consumed by or consumes any prerequisite edge

### Requirement: can_use_skill is the single shared use-eligibility predicate
`world/rules/progression.py` SHALL define `can_use_skill(entity, skill) -> bool` as a pure,
side-effect-free query returning `False` unless `skill.key` is in `entity.skills.owned_keys()` and,
for every declared `SkillPrerequisite`: the prereq key is in `owned_keys()` and
`skill_proficiency_level(entity, prereq.skill_key) >= prereq.min_proficiency`. It SHALL gate every
ACTIVE skill — spell and weapon skill alike — and SHALL be consumed by `ActionResolver`
step-1/preflight/resolve, the shared action preview, submission revalidation, both skill menus, and
`world/rules/combat.py`'s `default_attack_policy`, replacing the interim ownership+MP-only gate.
An owned skill whose prerequisite chain is unmet SHALL be rejected by the resolver's step-1 with
the SAME reason as an unowned skill (`UNKNOWN_SKILL`), its deterministic detail naming the first
unmet edge in declared order. The deleted mastery-tier override SHALL NOT be reintroduced:
主宰-tier entry is the prerequisite path (AND semantics over all declared edges). `cost_tiers`
SHALL remain a display-only data label.

#### Scenario: A mid-tree spell is gated by its own edge
- **WHEN** an entity owning `firestorm` with `firestorm` practice level 0 and `scorching_wave`
  practice level 2 calls `can_use_skill`
- **THEN** it returns `False` (the `scorching_wave >= 3` edge is unsatisfied)

#### Scenario: The exact threshold passes
- **WHEN** the same entity's `scorching_wave` level is exactly 3
- **THEN** it returns `True`

#### Scenario: The gate is school-agnostic
- **WHEN** an entity owns an ACTIVE weapon skill declaring a prerequisite its practice level does not meet
- **THEN** `can_use_skill` returns `False` on the identical code path used for spells

#### Scenario: A root skill with no prereqs is usable on ownership
- **WHEN** an entity owns `fire_arrow` (no prerequisites)
- **THEN** `can_use_skill` returns `True` regardless of proficiency

### Requirement: Successful ACTIVE resolution accruses lineage practice XP
Every successful ACTIVE skill resolution SHALL accrue to the actor, inside the existing action
snapshot/restore face and the same transaction as the skill's own effects: `SKILL_PRACTICE_XP_PER_USE
× RACE_REGISTRY[race].learning_multiplier × element_affinity_multiplier(entity, skill.element)`
(physical or non-elemental skills multiply by `1.0`) `× growth_rate_multiplier(entity)` (the
conferred-buff pull path). The affinity factor SHALL apply only to a skill whose parsed effects
include a magic-school damage of its own element — a physical skill carrying an element (e.g.
`basic_attack`) multiplies by `1.0`. Storage and derivation are unchanged:
`db.skill_proficiency[skill_key]` float XP with `level = floor(xp / 50)`. PASSIVE skills SHALL NOT
accrue. A resolution carrying the simulated marker (a guild examination's
`event_context["simulated"]`) SHALL accrue nothing. Accrual SHALL NOT read the actor's school or any
magic stat.

#### Scenario: A physical skill accrues like a spell
- **WHEN** an ACTIVE sword skill resolves successfully for an elf (learning x10) with no affinity and no growth buff
- **THEN** `db.skill_proficiency[skill_key]` increases by exactly `SKILL_PRACTICE_XP_PER_USE × 10.0`

#### Scenario: The affinity multiplier participates
- **WHEN** an entity with `affinity_elements == ["fire"]` successfully casts a magic fire spell
- **THEN** the accrued XP carries the `1.1` factor; a non-favored element carries `0.9`, and a
  physical skill carrying `element == fire` carries `1.0`

#### Scenario: The conferred growth buff participates
- **WHEN** an entity with an active `conferred_growth_rate` buff successfully uses a skill
- **THEN** the accrued XP equals the base formula multiplied by `growth_rate_multiplier(entity)`

#### Scenario: A PASSIVE skill never accrues
- **WHEN** any game event touches a PASSIVE skill of the actor
- **THEN** `db.skill_proficiency` gains nothing for that key

#### Scenario: Rolled-back resolutions restore proficiency
- **WHEN** a successful resolution's later pending effect fails and the action snapshot restores
- **THEN** `db.skill_proficiency` is byte-equal to its pre-action value

### Requirement: Practice saturates at the derived tip cap
For any skill `S`, `cap(S)` SHALL equal the maximum `min_proficiency` over all edges consuming `S`
(read from the load-time reverse-edge map), or `PROFICIENCY_TIP_CAP` (from `progression.yaml`,
initial value 10) when no edge consumes `S`. Practice accrual SHALL saturate: once
`skill_proficiency_level(entity, S) >= cap(S)`, no further XP accrues to `S`. Saturation SHALL live
in one shared award primitive (clamping storage at `cap(S)`) that is the sole accrual writer of
`skill_proficiency` — the per-use grant and the booked-practice settlement of
`declared-practice-skip` SHALL both route through it, so the two entry points cannot diverge at cap
boundaries. `cap(S)` SHALL never fall below any single consuming edge's threshold, so a saturated
prerequisite never blocks its child node.

#### Scenario: A fully consumed node stops at its edge
- **WHEN** an entity at `fire_arrow` level 3 continues using `fire_arrow` (consumed by one edge requiring 3)
- **THEN** `db.skill_proficiency["fire_arrow"]` stops increasing at exactly level 3

#### Scenario: The canopy node caps at the yaml default
- **WHEN** `phoenix_eternal_flame` (consumed by nobody) accrues past level 10
- **THEN** accrual saturates at level 10

#### Scenario: A saturation ceiling still unlocks its child
- **WHEN** an entity's `firestorm` is capped at 5 and it practices to exactly 5
- **THEN** `can_use_skill(..., lava_burst)` (edge requires `firestorm >= 5`) returns `True`

### Requirement: Each (actor, skill, target) accrues once per world-clock tick
Practice accrual SHALL dedupe by `(actor, skill_key, target)` per world-clock tick: at most one
accrual per distinct triple per tick. Dedupe state SHALL live in a transient module-level dict
cleared whenever the current tick changes; it SHALL NOT be persisted, snapshotted, or restored, and
claims taken by a rolled-back commit SHALL be released explicitly so a legitimate same-tick retry
still accrues. An AREA skill SHALL accrue once per distinct target. An out-of-combat cast SHALL
advance the world clock (as existing cast settlement does), so consecutive casts by one actor land
on different ticks.

#### Scenario: Same target twice in one tick accrues once
- **WHEN** an actor resolves the same skill against the same target twice within one tick
- **THEN** `db.skill_proficiency[skill_key]` reflects a single accrual

#### Scenario: Distinct targets in one AOE each accrue
- **WHEN** an AREA skill successfully hits three distinct targets in one resolution
- **THEN** the actor's practice for that skill reflects three accruals

#### Scenario: Dedupe state survives no persistence face
- **WHEN** the dedupe dict's contents are checked against snapshot registries and database attributes
- **THEN** it appears in neither, and a world-clock tick change alone clears it

### Requirement: The freeform scale ladder is anchored to proficiency
The set of freeform scales an actor may cast for a skill SHALL be derived by a ladder over the
skill's OWN proficiency level, gated on the `<element>_mastery` key-presence entitlement: scale 0.25
unconditionally for an entitled actor, 0.5 at level >= 1, 1.0 at level >= 3, 2.0 at level >= 6,
4.0 at level >= 10 (thresholds and set SHALL be `progression.yaml` constants). The interaction with
tip caps is intentional: a rung whose threshold exceeds the skill's derived cap NEVER unlocks, so
no skill advertises a scale it can never practise to. The ladder SHALL be
derived deterministically from registry + proficiency state with no hidden information, and the
resolver gate, the preview, and the combat-panel advertisement SHALL all read the same
skill-anchored `freeform_scales_for(entity, skill)` so they can never diverge.

#### Scenario: A mastery holder at level 0 sees only the small rungs
- **WHEN** `freeform_scales_for(entity, skill)` is called for a fire skill on an entity owning
  `fire_mastery` whose proficiency in THAT skill is level 0
- **THEN** the returned scales are `(0.25,)`

#### Scenario: Canopy proficiency unlocks the 4.0 rung
- **WHEN** the entity's proficiency in the skill reaches 10 (the canopy cap)
- **THEN** `4.0` appears in the allowed scale set

#### Scenario: A capped mid-tree skill stops below the canopy rungs
- **WHEN** `firestorm` (derived cap 5) is practiced past its cap by a mastery holder
- **THEN** its allowed scale set tops out at 1.0 — the 2.0 rung (Lv.6) and 4.0 rung (Lv.10) sit
  above the skill's own ceiling and never appear, so no skill advertises a rung it cannot practise to

#### Scenario: No mastery still means no ladder
- **WHEN** an entity without `<element>_mastery` asks for any scale set
- **THEN** it receives `()` regardless of proficiency

### Requirement: Import and scene-build auto-seed prerequisite proficiency exactly
The character loader SHALL, inside the existing all-or-nothing transaction, seed the practice
proficiency of any prerequisite edge that is unsatisfied for an owned skill to EXACTLY the required
value, never above, and SHALL extend the record's ownership with the transitive prerequisite
closure so a deep import is gate-usable, not merely seeded. Auto-seed normalization SHALL run on
the record before the semantic validation phase reads it (schema range checks included), so
malformed imports still reject wholesale, and an explicit `skill_proficiency` entry in the import
record SHALL always win over auto-seed, even when it leaves an edge unmet. Every explicit
`skill_proficiency` key SHALL resolve in `SKILL_REGISTRY` — the check runs against the RAW record
before normalization, so an unregistered key names itself and rejects the whole record instead of
being silently dropped or silently persisted by the seed.
`world/quests/scene_builder.py`'s NPC spawn path SHALL share the same helper.

#### Scenario: A deep imported skill arrives usable
- **WHEN** an import record owns `firestorm` (prereq `scorching_wave >= 3`) and carries no proficiency for `scorching_wave`
- **THEN** the loaded entity owns the closed chain, its `scorching_wave` level is exactly 3 and `can_use_skill` passes

#### Scenario: Explicit proficiency beats auto-seed
- **WHEN** the same record explicitly carries `skill_proficiency: {"scorching_wave": 120}` (level 2)
- **THEN** the loaded level is 2 (below the edge) and auto-seed does not overwrite it

#### Scenario: Auto-seed never overshoots
- **WHEN** auto-seed satisfies a `>= 5` edge
- **THEN** the stored XP is exactly `5 * 50`, the minimal value meeting the threshold

#### Scenario: Malformed imports still reject all-or-nothing
- **WHEN** a record with an invalid field also triggers auto-seed
- **THEN** validation rejects the record and nothing persists, seed included

#### Scenario: An unregistered proficiency key rejects the record
- **WHEN** a record carries `skill_proficiency: {"not_a_skill": 50}`
- **THEN** validation rejects the record naming the key, and nothing persists
