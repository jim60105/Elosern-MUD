# skill-lineage Specification

## Purpose
Define the prerequisite-lineage graph, the single use-eligibility gate, use-driven practice accrual with per-tick dedupe and derived tip-cap saturation, the proficiency-anchored freeform scale ladder, and import/scene-build auto-seed.

## Requirements

### Requirement: SkillPrerequisite declares registry edges and load validation fails closed
`world/skills/registry.py` SHALL define the frozen, slotted dataclass
`SkillPrerequisite(skill_key: str, min_proficiency: int)` with `min_proficiency >= 1`, and `SkillDef`
SHALL carry `prerequisites: tuple[SkillPrerequisite, ...] = ()`. Registry load SHALL validate, in
order and fail-closed (an exception names every violator), the five checks of the following
scenarios: key existence, graph acyclicity, threshold validity, root identification, and the
load-time reverse-edge map.

#### Scenario: A dangling prerequisite key fails the load
- **WHEN** a registry entry declares `prerequisites=(SkillPrerequisite("not_a_skill", 3),)`
- **THEN** registry load raises naming the entry and the unknown key

#### Scenario: Load validates every prerequisite key exists
- **WHEN** registry load runs its first check
- **THEN** every `prerequisites.skill_key` is validated to exist in `SKILL_REGISTRY`

#### Scenario: Load proves the graph acyclic
- **WHEN** registry load runs its acyclicity check
- **THEN** a topological sort runs and raises naming the offending cycle

#### Scenario: Load validates every threshold
- **WHEN** registry load runs its threshold check
- **THEN** every `min_proficiency` is validated to be an integer >= 1

#### Scenario: Load identifies tree roots
- **WHEN** registry load runs its root check
- **THEN** a skill with no prerequisites is a tree root

#### Scenario: The reverse-edge map is computed at load
- **WHEN** registry load completes
- **THEN** the reverse-edge map (skill -> consuming edges) is computed and cached at load

#### Scenario: A cycle names itself at load
- **WHEN** entries `a` and `b` prereq each other
- **THEN** registry load raises from the topological sort and the exception text names the cycle

#### Scenario: A zero threshold fails the load
- **WHEN** an entry declares `min_proficiency=0`
- **THEN** registry load raises naming the entry

#### Scenario: The reverse-edge map is cached
- **WHEN** the lineage tip-cap query asks which edges consume `fire_arrow`
- **THEN** it resolves from the load-time cache without walking the registry again

#### Scenario: Branching is unbounded
- **WHEN** a skill is consumed by any number of edges (branching)
- **THEN** every mechanical rule applies unchanged: the structure is an n-ary DAG, degree-independent

#### Scenario: Merging is unbounded
- **WHEN** a skill declares any number of prerequisites (merging)
- **THEN** every mechanical rule applies unchanged: the structure is an n-ary DAG, degree-independent

### Requirement: The fire lineage ships as the authored branching tree with a two-parent canopy
`SKILL_REGISTRY` SHALL carry prerequisite edges forming the authored fire tree of the node-data
authority (`docs/lore/skill-trees/fire.md`). `fire_arrow` is a root with no prerequisites. The
structure is a branching DAG whose strict topological canopy is `crimson_apotheosis` (consuming both
authored parents, itself consumed by no edge). The five element-mastery passives SHALL NOT be tree
nodes (PASSIVE skills are never consumed by edges and never accrue).

#### Scenario: The fire tree validates with the canopy last
- **WHEN** the registry loads with the authored fire edges
- **THEN** the topological order runs `fire_arrow` first and `crimson_apotheosis` last (consuming two
  parents and consumed by no edge), `sacrificial_flame` is consumed only by the capstone edge at
  threshold 10, and every edge threshold is >= 1

#### Scenario: Mastery passives stay out of the graph
- **WHEN** the reverse-edge map is inspected for `fire_mastery`
- **THEN** no entry is consumed by or consumes any prerequisite edge

#### Scenario: The first-round spine survives verbatim
- **WHEN** the authored fire edges are declared
- **THEN** `fire_ball` requires `fire_arrow` >= 3
- **AND** `scorching_wave` requires `fire_ball` >= 3
- **AND** `firestorm` requires `scorching_wave` >= 3
- **AND** `lava_burst` requires `firestorm` >= 5
- **AND** `dragon_flame` requires `lava_burst` >= 8
- **AND** `sacrificial_flame` requires `dragon_flame` >= 8

#### Scenario: Sister spells keep their leaf edges onto the spine
- **WHEN** the authored fire edges are declared
- **THEN** `flame_shroud` requires `scorching_wave` >= 3
- **AND** `hellfire` requires `firestorm` >= 5
- **AND** `final_blaze` requires `hellfire` >= 5

#### Scenario: The catalog wave adds the third branch child
- **WHEN** the catalog wave extends the fire tree
- **THEN** `scorching_armor` requires `scorching_wave` >= 3, the third child of the branch point

#### Scenario: The capstone demands both authored parents
- **WHEN** the catalog wave extends the fire tree
- **THEN** the two-parent capstone `crimson_apotheosis` requires `sacrificial_flame` >= 10 AND
  `final_blaze` >= 10

#### Scenario: Sacrificial flame yields its canopy status
- **WHEN** the reverse-edge map is inspected for `sacrificial_flame`
- **THEN** it is no longer a canopy node: its Lv.10 edge feeds the capstone

### Requirement: can_use_skill is the single shared use-eligibility predicate
`world/rules/progression.py` SHALL define `can_use_skill(entity, skill) -> bool` as a pure,
side-effect-free query returning `False` unless `skill.key` is in `entity.skills.owned_keys()` and passes shared identity eligibility and applicable restrictions and,
for every declared `SkillPrerequisite`: the prereq key is in `owned_keys()` and
`skill_proficiency_level(entity, prereq.skill_key) >= prereq.min_proficiency`. It SHALL gate every
ACTIVE skill, spell and weapon skill alike.

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
- **WHEN** an identity-eligible entity owns `fire_arrow` (no prerequisites)
- **THEN** `can_use_skill` returns `True` regardless of proficiency

#### Scenario: Every consumer reads the single gate
- **WHEN** `ActionResolver` step-1/preflight/resolve, the shared action preview, submission
  revalidation, both skill menus, and `world/rules/combat.py`'s `default_attack_policy` need use
  eligibility
- **THEN** all consume `can_use_skill`, replacing the interim ownership+MP-only gate

#### Scenario: An unmet chain is rejected as an unknown skill
- **WHEN** the resolver's step-1 sees an owned skill whose prerequisite chain is unmet
- **THEN** it rejects with the SAME reason as an unowned skill (`UNKNOWN_SKILL`), its deterministic
  detail naming the first unmet edge in declared order

#### Scenario: No mastery-tier override returns
- **WHEN** 主宰-tier entry is evaluated
- **THEN** it is the prerequisite path (AND semantics over all declared edges); the deleted
  mastery-tier override SHALL NOT be reintroduced

#### Scenario: cost_tiers stays cosmetic
- **WHEN** a skill declares `cost_tiers`
- **THEN** it remains a display-only data label

### Requirement: Successful ACTIVE resolution accruses lineage practice XP
Every successful ACTIVE skill resolution SHALL accrue to the actor, inside the existing action
snapshot/restore face and the same transaction as the skill's own effects: `SKILL_PRACTICE_XP_PER_USE
× RACE_REGISTRY[race].learning_multiplier × element_affinity_multiplier(entity, skill.element)
× growth_rate_multiplier(entity) × the owned-skill growth factor`. PASSIVE skills SHALL NOT accrue.

#### Scenario: A physical skill accrues like a spell
- **WHEN** an ACTIVE sword skill resolves successfully for an elf (learning x10) with no affinity and no growth buff
- **THEN** `db.skill_proficiency[skill_key]` increases by exactly `SKILL_PRACTICE_XP_PER_USE × 10.0`

#### Scenario: The affinity multiplier participates
- **WHEN** an entity with `affinity_elements == ["fire"]` successfully casts a magic fire spell
- **THEN** the accrued XP carries the `1.1` factor; a non-favored element carries `0.9`, and a
  physical skill carrying `element == fire` carries `1.0`

#### Scenario: An elementless skill carries the neutral factor
- **WHEN** an entity with declared affinities successfully resolves a physical skill that declares no
  element, and a control entity with no declared affinities resolves the same skill
- **THEN** both accruals carry the `1.0` factor and neither entity's affinity set is read as a bonus
  or a penalty

#### Scenario: The conferred growth buff participates
- **WHEN** an entity with an active `conferred_growth_rate` buff successfully uses a skill
- **THEN** the accrued XP equals the base formula multiplied by `growth_rate_multiplier(entity)`

#### Scenario: An owned scoped growth skill accelerates only its own tree
- **WHEN** an entity owning a passive that declares a `growth_rate` effect scoped to one element
  successfully casts a magic spell of that element, and separately casts a magic spell of another
  element
- **THEN** the first accrual carries the declared multiplier and the second carries `1.0`

#### Scenario: An owned scoped growth skill leaves non-elemental practice alone
- **WHEN** an entity owning a scoped `growth_rate` passive successfully resolves a skill that
  declares no element
- **THEN** the accrual carries the `1.0` owned-skill factor

#### Scenario: The owned-skill and conferred factors multiply independently
- **WHEN** an entity owning a scoped `growth_rate` passive, and also carrying an active
  `conferred_growth_rate` buff, practises a skill of the scoped element
- **THEN** the accrued XP carries both factors multiplied together

#### Scenario: A PASSIVE skill never accrues
- **WHEN** any game event touches a PASSIVE skill of the actor
- **THEN** `db.skill_proficiency` gains nothing for that key

#### Scenario: Rolled-back resolutions restore proficiency
- **WHEN** a successful resolution's later pending effect fails and the action snapshot restores
- **THEN** `db.skill_proficiency` is byte-equal to its pre-action value

#### Scenario: A non-divine category carries no daily brake
- **WHEN** an ACTIVE skill outside `SkillCategory.DIVINE_MYSTERY` resolves successfully many times
  across one world-calendar day on distinct ticks
- **THEN** every resolution accrues, because the cadence applies to that one category only

#### Scenario: The owned-skill growth factor is defined
- **WHEN** the owned-skill growth factor is computed for a practised skill
- **THEN** it is the product of the multipliers of every scoped `growth_rate` effect carried by a
  skill the actor OWNS whose declared scope equals the element of the skill being practised, and
  `1.0` for a skill of any other element and for a skill declaring no element, so an unscoped
  acceleration is not expressible

#### Scenario: Neither growth factor reads the other
- **WHEN** the owned-skill growth factor and `growth_rate_multiplier(entity)` (the conferred-buff
  pull path) are both in play
- **THEN** the two factors are independent — they multiply, and neither reads the other

#### Scenario: The affinity factor is magic-damage-scoped
- **WHEN** the affinity factor is evaluated for a skill
- **THEN** it applies only to a skill whose parsed effects include a magic-school damage of its own
  element — a physical skill carrying an element (e.g. `light_sword_style`) multiplies by `1.0`,
  and so does a physical skill declaring no element at all

#### Scenario: Storage and derivation are unchanged
- **WHEN** practice XP accrues
- **THEN** it lands in `db.skill_proficiency[skill_key]` as float XP with `level = floor(xp / 50)`

#### Scenario: A simulated resolution accrues nothing
- **WHEN** a resolution carries the simulated marker (a guild examination's
  `event_context["simulated"]`)
- **THEN** it accrues nothing

#### Scenario: Accrual ignores school and stats
- **WHEN** any accrual is computed
- **THEN** it reads neither the actor's school nor any magic stat

#### Scenario: The one divine cadence exception
- **WHEN** an ACTIVE skill in `SkillCategory.DIVINE_MYSTERY` resolves successfully — the exactly one
  category-scoped exception that additionally passes a per-world-calendar-day claim before accruing
- **THEN** that rule and its scenarios are owned by the `divine-mystery` capability and SHALL NOT be
  restated here; no other category carries a cadence of any kind

### Requirement: Practice saturates at the derived tip cap
For any skill `S`, `cap(S)` SHALL equal the maximum `min_proficiency` over all edges consuming `S`
(read from the load-time reverse-edge map), or `PROFICIENCY_TIP_CAP` (from `progression.yaml`,
initial value 10) when no edge consumes `S`. Practice accrual SHALL saturate: once
`skill_proficiency_level(entity, S) >= cap(S)`, no further XP accrues to `S`.

#### Scenario: A fully consumed node stops at its edge
- **WHEN** an entity at `fire_arrow` level 3 continues using `fire_arrow` (consumed by one edge requiring 3)
- **THEN** `db.skill_proficiency["fire_arrow"]` stops increasing at exactly level 3

#### Scenario: The canopy node caps at the yaml default
- **WHEN** `crimson_apotheosis` (consumed by nobody) accrues past level 10
- **THEN** accrual saturates at level 10

#### Scenario: A saturation ceiling still unlocks its child
- **WHEN** an entity's `firestorm` is capped at 5 and it practices to exactly 5
- **THEN** `can_use_skill(..., lava_burst)` (edge requires `firestorm >= 5`) returns `True`

#### Scenario: One shared award primitive clamps every writer
- **WHEN** saturation is enforced
- **THEN** it lives in one shared award primitive (clamping storage at `cap(S)`) that is the sole
  accrual writer of `skill_proficiency`

#### Scenario: Both accrual entry points route through the primitive
- **WHEN** the per-use grant and the booked-practice settlement of `declared-practice-skip` award XP
- **THEN** both route through the shared primitive, so the two entry points cannot diverge at cap
  boundaries

#### Scenario: The cap never starves a consuming edge
- **WHEN** `cap(S)` is derived for a consumed skill
- **THEN** it SHALL never fall below any single consuming edge's threshold, so a saturated
  prerequisite never blocks its child node

### Requirement: Each (actor, skill, target) accrues once per world-clock tick
Practice accrual SHALL dedupe by `(actor, skill_key, target)` per world-clock tick: at most one
accrual per distinct triple per tick. Dedupe state SHALL live in a transient module-level dict
cleared whenever the current tick changes; it SHALL NOT be persisted, snapshotted, or restored.

#### Scenario: Same target twice in one tick accrues once
- **WHEN** an actor resolves the same skill against the same target twice within one tick
- **THEN** `db.skill_proficiency[skill_key]` reflects a single accrual

#### Scenario: Distinct targets in one AOE each accrue
- **WHEN** an AREA skill successfully hits three distinct targets in one resolution
- **THEN** the actor's practice for that skill reflects three accruals

#### Scenario: Dedupe state survives no persistence face
- **WHEN** the dedupe dict's contents are checked against snapshot registries and database attributes
- **THEN** it appears in neither, and a world-clock tick change alone clears it

#### Scenario: A rolled-back commit releases its claim
- **WHEN** a commit takes a dedupe claim and later rolls back
- **THEN** the claim is released explicitly so a legitimate same-tick retry still accrues

#### Scenario: An AREA skill accrues per distinct target
- **WHEN** an AREA skill resolves against multiple targets in one tick
- **THEN** it accrues once per distinct target

#### Scenario: Out-of-combat casts advance the clock
- **WHEN** an actor casts out of combat
- **THEN** the cast advances the world clock (as existing cast settlement does), so consecutive
  casts by one actor land on different ticks

### Requirement: The freeform scale ladder is anchored to proficiency
The set of freeform scales an actor may cast for a skill SHALL be derived by a ladder over the
skill's OWN proficiency level, gated on the `<element>_mastery` key-presence entitlement: scale 0.25
unconditionally for an entitled actor, 0.5 at level >= 1, 1.0 at level >= 3, 2.0 at level >= 6,
4.0 at level >= 10 (thresholds and set SHALL be `progression.yaml` constants).

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

#### Scenario: Tip caps prune unreachable rungs
- **WHEN** a rung's threshold exceeds the skill's derived tip cap
- **THEN** that rung NEVER unlocks — the interaction is intentional, so no skill advertises a scale
  it can never practise to

#### Scenario: The ladder is fully deterministic
- **WHEN** the ladder is derived
- **THEN** it comes deterministically from registry + proficiency state with no hidden information

#### Scenario: All surfaces share one derivation
- **WHEN** the resolver gate, the preview, and the combat-panel advertisement need the scale set
- **THEN** all read the same skill-anchored `freeform_scales_for(entity, skill)` so they can never
  diverge

### Requirement: Import and scene-build auto-seed prerequisite proficiency exactly
The character loader SHALL, inside the existing all-or-nothing transaction, seed the practice
proficiency of any prerequisite edge that is unsatisfied for an owned skill to EXACTLY the required
value, never above, and SHALL extend the record's ownership with the transitive prerequisite
closure so a deep import is gate-usable, not merely seeded.

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

#### Scenario: Preset activation shares the same helpers
- **WHEN** a preset activation seeds a prerequisite edge
- **THEN** the seeded value equals what the import path would write for the same skill set, produced by the same two helpers rather than a parallel implementation

#### Scenario: Normalization precedes semantic validation
- **WHEN** the loader processes a record
- **THEN** auto-seed normalization runs on the record before the semantic validation phase reads it
  (schema range checks included), so malformed imports still reject wholesale

#### Scenario: Explicit proficiency always wins
- **WHEN** the import record carries an explicit `skill_proficiency` entry
- **THEN** it always wins over auto-seed, even when it leaves an edge unmet

#### Scenario: Explicit keys resolve in the registry against the raw record
- **WHEN** every explicit `skill_proficiency` key is checked for resolution in `SKILL_REGISTRY`
- **THEN** the check runs against the RAW record before normalization, so an unregistered key names
  itself and rejects the whole record instead of being silently dropped or silently persisted by the
  seed

#### Scenario: The NPC spawn path shares the helper
- **WHEN** `world/quests/scene_builder.py`'s NPC spawn path seeds lineage proficiency
- **THEN** it shares the same helper as the character loader

#### Scenario: Preset activation composes the helpers directly
- **WHEN** `world/rules/character_creation.py`'s preset activation path seeds lineage proficiency
- **THEN** it composes `lineage_ownership_closure` and `seed_lineage_proficiency` directly over the
  preset's declared keys rather than through the import-record wrapper

#### Scenario: Exactly three production callers
- **WHEN** the closure and seed helpers are counted across production
- **THEN** they have exactly three production callers, and no caller reimplements either algorithm

### Requirement: The wind lineage ships as the authored two-root branching tree with a two-parent canopy
`SKILL_REGISTRY` SHALL carry prerequisite edges forming the authored wind tree of the node-data authority (`docs/lore/skill-trees/wind.md`): TWO roots — `gale_step` (mobility) and `wind_blade` (destruction) — each with no prerequisites. The structure is a two-root DAG whose strict topological canopy is `sky_apotheosis`; `wind_mastery` and `flight` SHALL NOT be tree nodes (PASSIVE skills are never consumed by edges and never accrue).

#### Scenario: The wind tree validates with two roots and the canopy last
- **WHEN** the registry loads with the authored wind edges
- **THEN** the topological order runs both roots (`gale_step`, `wind_blade`) before their descendants and `sky_apotheosis` last (consuming two parents and consumed by no edge), `sky_tempest` and `vacuum_severance` are consumed only by the canopy edge at threshold 10, and every edge threshold is >= 1

#### Scenario: Both branches of the destruction root validate in parallel
- **WHEN** the reverse-edge map is inspected for `tornado_blade`
- **THEN** it is consumed by exactly two edges (storm_domain at 3 and gale_dance_strike at 3 — the two authored branch children), each branch progresses through validation independently, and no cross-branch edge exists between the storm and dance chains

#### Scenario: Mastery and movement passives stay out of the graph
- **WHEN** the reverse-edge map is inspected for `wind_mastery` and `flight`
- **THEN** no entry is consumed by or consumes any prerequisite edge

#### Scenario: The mobility chain is linear
- **WHEN** the authored wind edges are declared
- **THEN** `gale_chain_step` requires `gale_step` >= 3
- **AND** `afterimage_step` requires `gale_chain_step` >= 3
- **AND** `haste_domain` requires `afterimage_step` >= 5, a branch-terminal leaf

#### Scenario: The destruction branch point feeds both authored children
- **WHEN** the authored wind edges are declared
- **THEN** `tornado_blade` requires `wind_blade` >= 3 — the branch point feeding BOTH authored children
- **AND** `storm_domain` requires `tornado_blade` >= 3
- **AND** `gale_dance_strike` requires `tornado_blade` >= 3

#### Scenario: The storm branch chain
- **WHEN** the authored wind edges are declared
- **THEN** `heavens_wrath_storm` requires `storm_domain` >= 5
- **AND** `sky_tempest` requires `heavens_wrath_storm` >= 8

#### Scenario: The dance branch chain
- **WHEN** the authored wind edges are declared
- **THEN** `sky_rending_slash` requires `gale_dance_strike` >= 8
- **AND** `vacuum_severance` requires `sky_rending_slash` >= 8

#### Scenario: The two-parent 神格 canopy demands both parents
- **WHEN** the authored wind edges are declared
- **THEN** the two-parent 神格 canopy `sky_apotheosis` requires `sky_tempest` >= 10 AND
  `vacuum_severance` >= 10 — consuming both authored parents and itself consumed by no edge

### Requirement: The ice lineage ships as the authored two-root branching tree with a two-parent canopy
`SKILL_REGISTRY` SHALL carry prerequisite edges forming the authored ice tree of the node-data
authority (`docs/lore/skill-trees/ice.md`): TWO roots — `frost_breath` (遲緩路線) and `ice_shard`
(監禁路線) — each with no prerequisites. The two routes are otherwise independent chains; they
converge ONLY at the strict topological canopy `eternal_frost_apotheosis`. The element-mastery
passive SHALL NOT be a tree node.

#### Scenario: The ice tree validates with two roots and the canopy last
- **WHEN** the registry loads with the authored ice edges
- **THEN** the topological order runs both roots (`frost_breath`, `ice_shard`) before their
  descendants and `eternal_frost_apotheosis` last (consuming two parents and consumed by no edge),
  `eternal_ice_field` and `absolute_zero` are consumed only by the canopy edge at threshold 10, and
  every edge threshold is >= 1

#### Scenario: Both branch points gate exactly their two authored children
- **WHEN** the reverse-edge map is inspected for `ice_wall` and `ice_prison`
- **THEN** `ice_wall` is consumed by exactly two edges (frost_mire at 3 and permafrost_domain at 3)
  and `ice_prison` is consumed by exactly two edges (blizzard at 5 and crystal_shatter at 5), each
  route progresses through validation independently, and no cross-route edge exists between the
  slow line and the imprisonment line outside the canopy's two authored parent edges

#### Scenario: The mastery passive stays out of the graph
- **WHEN** the reverse-edge map is inspected for `ice_mastery`
- **THEN** no entry is consumed by or consumes any prerequisite edge

#### Scenario: The slow line branch point feeds both authored children
- **WHEN** the authored ice edges are declared
- **THEN** `ice_wall` requires `frost_breath` >= 3 — the branch point feeding BOTH authored children
- **AND** `frost_mire` requires `ice_wall` >= 3, a branch-terminal leaf
- **AND** `permafrost_domain` requires `ice_wall` >= 3

#### Scenario: The permafrost chain continues
- **WHEN** the authored ice edges are declared
- **THEN** `absolute_tundra` requires `permafrost_domain` >= 8
- **AND** `eternal_ice_field` requires `absolute_tundra` >= 8

#### Scenario: The imprisonment line branch point feeds both authored children
- **WHEN** the authored ice edges are declared
- **THEN** `frost_arrow_rain` requires `ice_shard` >= 3
- **AND** `ice_prison` requires `frost_arrow_rain` >= 3 — the second branch point feeding BOTH
  authored children
- **AND** `blizzard` requires `ice_prison` >= 5
- **AND** `crystal_shatter` requires `ice_prison` >= 5, a branch-terminal leaf

#### Scenario: The blizzard chain continues
- **WHEN** the authored ice edges are declared
- **THEN** `absolute_zero` requires `blizzard` >= 8

#### Scenario: The canopy demands both authored parents
- **WHEN** the authored ice edges are declared
- **THEN** `eternal_frost_apotheosis` requires `eternal_ice_field` >= 10 AND `absolute_zero` >= 10

#### Scenario: The canopy consumes both routes and nothing consumes it
- **WHEN** the canopy's edges are inspected
- **THEN** `eternal_frost_apotheosis` consumes both authored parents and is itself consumed by no
  edge — the lore's 匯合 of 遲緩 and 監禁 at the 神格 rung

#### Scenario: PASSIVE rationale for staying out of the graph
- **WHEN** the element-mastery passive is considered as a tree node
- **THEN** it is excluded because PASSIVE skills are never consumed by edges and never accrue

### Requirement: The lightning lineage ships as the authored two-root branching tree with a two-parent canopy
`SKILL_REGISTRY` SHALL carry prerequisite edges forming the authored lightning tree of the node-data
authority (`docs/lore/skill-trees/lightning.md`): TWO roots — `static_ward` (先制路線) and
`spark_shock` (過載路線) — each with no prerequisites. The two routes are otherwise independent
chains; they converge ONLY at the strict topological canopy `thunder_apotheosis`. The
element-mastery passive SHALL NOT be a tree node.

#### Scenario: The lightning tree validates with two roots and the canopy last
- **WHEN** the registry loads with the authored lightning edges
- **THEN** the topological order runs both roots (`static_ward`, `spark_shock`) before their
  descendants and `thunder_apotheosis` last (consuming two parents and consumed by no edge),
  `judgement_thunder` and `divine_lightning_slaughter` are consumed only by the canopy edge at
  threshold 10, and every edge threshold is >= 1

#### Scenario: Both branch points gate exactly their authored children
- **WHEN** the reverse-edge map is inspected for `spark_shock`, `thunder_combo` and the two
  branch-terminal leaves
- **THEN** `spark_shock` is consumed by exactly two edges (chain_lightning at 3 and paralyzing_bolt
  at 3) and `thunder_combo` by exactly two (thunder_gods_haste at 5 and thunder_shatter_strike at
  5), `thunder_shatter_strike` and `thunder_prison` consume exactly one edge each and are consumed
  by none, and no cross-route edge exists between the initiative line and the overload line outside
  the canopy's two authored parent edges

#### Scenario: The mastery passive stays out of the graph
- **WHEN** the reverse-edge map is inspected for `lightning_mastery`
- **THEN** no entry is consumed by or consumes any prerequisite edge

#### Scenario: The initiative line branch point feeds both authored children
- **WHEN** the authored lightning edges are declared
- **THEN** `lightning_flicker` requires `static_ward` >= 3
- **AND** `thunder_combo` requires `lightning_flicker` >= 3 — the branch point feeding BOTH authored
  children
- **AND** `thunder_gods_haste` requires `thunder_combo` >= 5
- **AND** `thunder_shatter_strike` requires `thunder_combo` >= 5, a branch-terminal leaf

#### Scenario: The haste chain continues
- **WHEN** the authored lightning edges are declared
- **THEN** `judgement_thunder` requires `thunder_gods_haste` >= 8

#### Scenario: The overload root branches at itself
- **WHEN** the authored lightning edges are declared
- **THEN** `chain_lightning` requires `spark_shock` >= 3 AND `paralyzing_bolt` requires
  `spark_shock` >= 3 — the root's own branch point

#### Scenario: The overload chains continue
- **WHEN** the authored lightning edges are declared
- **THEN** `lightning_strike` requires `chain_lightning` >= 3
- **AND** `thunder_prison` requires `paralyzing_bolt` >= 3, a branch-terminal leaf
- **AND** `heavens_thunder` requires `lightning_strike` >= 5
- **AND** `divine_lightning_slaughter` requires `heavens_thunder` >= 8

#### Scenario: The canopy demands both authored parents
- **WHEN** the authored lightning edges are declared
- **THEN** `thunder_apotheosis` requires `judgement_thunder` >= 10 AND
  `divine_lightning_slaughter` >= 10

#### Scenario: The canopy consumes both routes and nothing consumes it
- **WHEN** the canopy's edges are inspected
- **THEN** `thunder_apotheosis` consumes both authored parents and is itself consumed by no
  edge — the lore's 匯合 of 先制 and 過載 at the 神格 rung

#### Scenario: PASSIVE rationale for staying out of the graph
- **WHEN** the element-mastery passive is considered as a tree node
- **THEN** it is excluded because PASSIVE skills are never consumed by edges and never accrue

### Requirement: Identity rejection is distinct from an unmet prerequisite
Use-eligibility failure SHALL distinguish identity rejection from an unmet prerequisite. An identity-ineligible root SHALL reject without assuming a prerequisite exists and without any dice or state change.

#### Scenario: Owned root cannot crash the gate
- **WHEN** an ineligible owner invokes a skill with no prerequisite edges
- **THEN** a named identity rejection is returned before costs, effects and practice; unmet-edge detail remains reserved for actual unmet edges
