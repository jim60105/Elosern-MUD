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
  its authored threshold, and every edge threshold is >= 1

#### Scenario: Mastery passives stay out of the graph
- **WHEN** the reverse-edge map is inspected for `fire_mastery`
- **THEN** no entry is consumed by or consumes any prerequisite edge

#### Scenario: The first-round spine survives verbatim
- **WHEN** the authored fire edges are declared
- **THEN** `fire_ball` requires `fire_arrow` >= its declared edge threshold
- **AND** `scorching_wave` requires `fire_ball` >= its declared edge threshold
- **AND** `firestorm` requires `scorching_wave` >= its declared edge threshold
- **AND** `lava_burst` requires `firestorm` >= its declared edge threshold
- **AND** `dragon_flame` requires `lava_burst` >= its declared edge threshold
- **AND** `sacrificial_flame` requires `dragon_flame` >= its declared edge threshold

#### Scenario: Sister spells keep their leaf edges onto the spine
- **WHEN** the authored fire edges are declared
- **THEN** `flame_shroud` requires `scorching_wave` >= its declared edge threshold
- **AND** `hellfire` requires `firestorm` >= its declared edge threshold
- **AND** `final_blaze` requires `hellfire` >= its declared edge threshold

#### Scenario: The catalog wave adds the third branch child
- **WHEN** the catalog wave extends the fire tree
- **THEN** `scorching_armor` requires `scorching_wave` >= its declared edge threshold, the third child of the branch point

#### Scenario: The capstone demands both authored parents
- **WHEN** the catalog wave extends the fire tree
- **THEN** the two-parent capstone `crimson_apotheosis` requires `sacrificial_flame` >= its declared edge threshold AND
  `final_blaze` >= its declared edge threshold

#### Scenario: Sacrificial flame yields its canopy status
- **WHEN** the reverse-edge map is inspected for `sacrificial_flame`
- **THEN** it is no longer a canopy node: its authored edge feeds the capstone

#### Scenario: Threshold tuning preserves topology
- **WHEN** a valid positive edge threshold changes
- **THEN** topology/reference checks remain green; fixed synthetic trees independently prove multi-parent qualification, reverse-edge caps and exact boundary behavior

### Requirement: can_use_skill is the single shared use-eligibility predicate
`can_use_skill(entity, skill)` SHALL be a pure query returning False unless the key is owned, identity/restrictions pass and every prerequisite key is owned at or above its declared minimum proficiency. The shared predicate SHALL gate ACTIVE spells and weapon skills alike.

#### Scenario: A mid-tree spell is gated by its own edge
- **WHEN** a fixed synthetic tree gives t_storm a t_wave prerequisite at level 3 and the owner has t_wave level 2
- **THEN** eligibility is False regardless of t_storm's own proficiency

#### Scenario: The exact threshold passes
- **WHEN** the synthetic owner's t_wave reaches 3
- **THEN** eligibility is True, without pinning any shipped edge

#### Scenario: The gate is school-agnostic
- **WHEN** an owned ACTIVE weapon skill has an unmet prerequisite
- **THEN** it uses the same False eligibility path as spells

#### Scenario: A root skill with no prereqs is usable on ownership
- **WHEN** an identity-eligible owner requests a synthetic root without prerequisites
- **THEN** eligibility is True regardless of proficiency

#### Scenario: Every consumer reads the single gate
- **WHEN** resolver step-1/preflight/resolve, action preview, submission revalidation, both skill menus or default attack policy needs eligibility
- **THEN** each consumes the same shared predicate rather than ownership-plus-MP-only logic

#### Scenario: An unmet chain is rejected as an unknown skill
- **WHEN** resolver step-1 sees an owned skill with an unmet chain
- **THEN** it rejects with UNKNOWN_SKILL and names the first unmet edge in declared order

#### Scenario: No mastery-tier override returns
- **WHEN** 主宰-tier entry is evaluated
- **THEN** all declared prerequisites use AND semantics with no mastery-tier override

#### Scenario: cost_tiers stays cosmetic
- **WHEN** a skill declares cost_tiers
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
For skill S, cap(S) SHALL be the maximum minimum proficiency of all edges consuming S, or the authored progression tip cap when no edge consumes S. Once proficiency reaches that cap, further practice SHALL NOT accrue. Synthetic numeric fixtures SHALL NOT approve shipped edge/tip values.

#### Scenario: A fully consumed node stops at its edge
- **WHEN** a synthetic root is consumed by an edge requiring level 3 and continues practice at level 3
- **THEN** its stored XP stops increasing at level 3

#### Scenario: The canopy node caps at the yaml default
- **WHEN** a synthetic canopy with no consumers has a fixed synthetic tip cap 10
- **THEN** accrual saturates at 10; production canopy cap follows its current declaration

#### Scenario: A saturation ceiling still unlocks its child
- **WHEN** a synthetic parent caps at 5 because its child requires 5 and practice reaches 5
- **THEN** the child passes eligibility

#### Scenario: One shared award primitive clamps every writer
- **WHEN** saturation is enforced
- **THEN** one shared sole proficiency award primitive clamps storage at cap(S)

#### Scenario: Both accrual entry points route through the primitive
- **WHEN** per-use grants or booked-practice settlement award XP
- **THEN** both use that shared primitive and cannot diverge at cap boundaries

#### Scenario: The cap never starves a consuming edge
- **WHEN** a consumed skill's cap is derived
- **THEN** it is not below any consuming threshold, so saturation cannot block a child

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
Allowed freeform scales SHALL derive from the authored progression ladder over the skill's OWN proficiency, gated by its element-mastery key. Rungs above the skill's derived cap SHALL never unlock. Numeric ladder examples SHALL use fixed synthetic rows rather than approve production thresholds or scale values.

#### Scenario: A mastery holder at level 0 sees only the small rungs
- **WHEN** a fixed synthetic ladder allows 0.25 unconditionally, 0.5 at 1, 1.0 at 3, 2.0 at 6 and 4.0 at 10, and an entitled synthetic skill owner is at level 0
- **THEN** allowed scales are (0.25,)

#### Scenario: Canopy proficiency unlocks the 4.0 rung
- **WHEN** that synthetic skill reaches level 10 under synthetic tip cap 10
- **THEN** 4.0 appears

#### Scenario: A capped mid-tree skill stops below the canopy rungs
- **WHEN** a synthetic mid-tree skill with cap 5 is practiced past its cap under the same fixture
- **THEN** its maximum scale is 1.0, with the level-6 and level-10 rungs absent

#### Scenario: No mastery still means no ladder
- **WHEN** an actor lacks the required element-mastery key
- **THEN** the scale set is empty regardless of proficiency

#### Scenario: Tip caps prune unreachable rungs
- **WHEN** a rung threshold exceeds the derived tip cap
- **THEN** it never unlocks

#### Scenario: The ladder is fully deterministic
- **WHEN** scales are derived
- **THEN** registry and proficiency state alone determine them, with no hidden information

#### Scenario: All surfaces share one derivation
- **WHEN** the resolver gate, preview and combat panel require allowed scales
- **THEN** they consume the same skill-anchored derivation

### Requirement: Import and scene-build auto-seed prerequisite proficiency exactly
Within the all-or-nothing import transaction, missing prerequisite proficiency SHALL seed exactly to its declared requirement, never above, and ownership SHALL extend to transitive closure. Explicit proficiency SHALL always win, even below eligibility. Scene spawn and preset activation SHALL share the same closure/seed mechanisms.

#### Scenario: A deep imported skill arrives usable
- **WHEN** a fixed synthetic import owns t_storm requiring t_wave level 3 with no explicit t_wave proficiency
- **THEN** the loaded owner has the closed chain, t_wave exactly level 3 and passing eligibility

#### Scenario: Explicit proficiency beats auto-seed
- **WHEN** that synthetic record explicitly gives t_wave XP 120, level 2
- **THEN** level 2 remains and the unmet edge is not overwritten

#### Scenario: Auto-seed never overshoots
- **WHEN** a fixed synthetic edge requires level 5
- **THEN** seeded XP is exactly 250 under the existing 50-XP-per-level mechanism

#### Scenario: Malformed imports still reject all-or-nothing
- **WHEN** another invalid field accompanies auto-seeding
- **THEN** the whole record rejects and nothing persists, including seeded values

#### Scenario: An unregistered proficiency key rejects the record
- **WHEN** a record includes not_a_skill with XP 50
- **THEN** validation names the key and persists nothing

#### Scenario: Preset activation shares the same helpers
- **WHEN** preset activation seeds an edge
- **THEN** it produces the same result as import for identical skill inputs via the same two helpers

#### Scenario: Normalization precedes semantic validation
- **WHEN** an import is processed
- **THEN** auto-seed normalization precedes semantic validation and schema range checks still reject malformed records wholesale

#### Scenario: Explicit proficiency always wins
- **WHEN** an import has an explicit proficiency entry
- **THEN** it wins even if its edge remains unmet

#### Scenario: Explicit keys resolve in the registry against the raw record
- **WHEN** explicit proficiency keys are validated
- **THEN** validation reads the raw record before normalization, naming and rejecting unknown keys rather than dropping/persisting them

#### Scenario: The NPC spawn path shares the helper
- **WHEN** scene-builder NPC spawn seeds lineage proficiency
- **THEN** it uses the character-loader's shared helper

#### Scenario: Preset activation composes the helpers directly
- **WHEN** preset activation seeds proficiency
- **THEN** it composes ownership closure and proficiency seed directly over declared keys, not the import-record wrapper

#### Scenario: Exactly three production callers
- **WHEN** production closure/seed callers are counted
- **THEN** there are exactly three, with no reimplemented closure/seed algorithm

### Requirement: The wind lineage ships as the authored two-root branching tree with a two-parent canopy
`SKILL_REGISTRY` SHALL carry prerequisite edges forming the authored wind tree of the node-data authority (`docs/lore/skill-trees/wind.md`): TWO roots ;  `gale_step` (mobility) and `wind_blade` (destruction) ;  each with no prerequisites. The structure is a two-root DAG whose strict topological canopy is `sky_apotheosis`; `wind_mastery` and `flight` SHALL NOT be tree nodes (PASSIVE skills are never consumed by edges and never accrue).

#### Scenario: The wind tree validates with two roots and the canopy last
- **WHEN** the registry loads with the authored wind edges
- **THEN** the topological order runs both roots (`gale_step`, `wind_blade`) before their descendants and `sky_apotheosis` last (consuming two parents and consumed by no edge), `sky_tempest` and `vacuum_severance` are consumed only by the canopy edge at its authored threshold, and every edge threshold is >= 1

#### Scenario: Both branches of the destruction root validate in parallel
- **WHEN** the reverse-edge map is inspected for `tornado_blade`
- **THEN** it is consumed by exactly two edges (storm_domain at its declared edge threshold and gale_dance_strike at its declared edge threshold ;  the two authored branch children), each branch progresses through validation independently, and no cross-branch edge exists between the storm and dance chains

#### Scenario: Mastery and movement passives stay out of the graph
- **WHEN** the reverse-edge map is inspected for `wind_mastery` and `flight`
- **THEN** no entry is consumed by or consumes any prerequisite edge

#### Scenario: The mobility chain is linear
- **WHEN** the authored wind edges are declared
- **THEN** `gale_chain_step` requires `gale_step` >= its declared edge threshold
- **AND** `afterimage_step` requires `gale_chain_step` >= its declared edge threshold
- **AND** `haste_domain` requires `afterimage_step` >= its declared edge threshold, a branch-terminal leaf

#### Scenario: The destruction branch point feeds both authored children
- **WHEN** the authored wind edges are declared
- **THEN** `tornado_blade` requires `wind_blade` >= its declared edge threshold ;  the branch point feeding BOTH authored children
- **AND** `storm_domain` requires `tornado_blade` >= its declared edge threshold
- **AND** `gale_dance_strike` requires `tornado_blade` >= its declared edge threshold

#### Scenario: The storm branch chain
- **WHEN** the authored wind edges are declared
- **THEN** `heavens_wrath_storm` requires `storm_domain` >= its declared edge threshold
- **AND** `sky_tempest` requires `heavens_wrath_storm` >= its declared edge threshold

#### Scenario: The dance branch chain
- **WHEN** the authored wind edges are declared
- **THEN** `sky_rending_slash` requires `gale_dance_strike` >= its declared edge threshold
- **AND** `vacuum_severance` requires `sky_rending_slash` >= its declared edge threshold

#### Scenario: The two-parent 神格 canopy demands both parents
- **WHEN** the authored wind edges are declared
- **THEN** the two-parent 神格 canopy `sky_apotheosis` requires `sky_tempest` >= its declared edge threshold AND
  `vacuum_severance` >= its declared edge threshold ;  consuming both authored parents and itself consumed by no edge

#### Scenario: Threshold tuning preserves topology
- **WHEN** a valid positive edge threshold changes
- **THEN** topology/reference checks remain green; fixed synthetic trees independently prove multi-parent qualification, reverse-edge caps and exact boundary behavior

### Requirement: The ice lineage ships as the authored two-root branching tree with a two-parent canopy
`SKILL_REGISTRY` SHALL carry prerequisite edges forming the authored ice tree of the node-data
authority (`docs/lore/skill-trees/ice.md`): TWO roots ;  `frost_breath` (遲緩路線) and `ice_shard`
(監禁路線) ;  each with no prerequisites. The two routes are otherwise independent chains; they
converge ONLY at the strict topological canopy `eternal_frost_apotheosis`. The element-mastery
passive SHALL NOT be a tree node.

#### Scenario: The ice tree validates with two roots and the canopy last
- **WHEN** the registry loads with the authored ice edges
- **THEN** the topological order runs both roots (`frost_breath`, `ice_shard`) before their
  descendants and `eternal_frost_apotheosis` last (consuming two parents and consumed by no edge),
  `eternal_ice_field` and `absolute_zero` are consumed only by the canopy edge at its authored threshold, and
  every edge threshold is >= 1

#### Scenario: Both branch points gate exactly their two authored children
- **WHEN** the reverse-edge map is inspected for `ice_wall` and `ice_prison`
- **THEN** `ice_wall` is consumed by exactly two edges (frost_mire at its declared edge threshold and permafrost_domain at its declared edge threshold)
  and `ice_prison` is consumed by exactly two edges (blizzard at its declared edge threshold and crystal_shatter at its declared edge threshold), each
  route progresses through validation independently, and no cross-route edge exists between the
  slow line and the imprisonment line outside the canopy's two authored parent edges

#### Scenario: The mastery passive stays out of the graph
- **WHEN** the reverse-edge map is inspected for `ice_mastery`
- **THEN** no entry is consumed by or consumes any prerequisite edge

#### Scenario: The slow line branch point feeds both authored children
- **WHEN** the authored ice edges are declared
- **THEN** `ice_wall` requires `frost_breath` >= its declared edge threshold ;  the branch point feeding BOTH authored children
- **AND** `frost_mire` requires `ice_wall` >= its declared edge threshold, a branch-terminal leaf
- **AND** `permafrost_domain` requires `ice_wall` >= its declared edge threshold

#### Scenario: The permafrost chain continues
- **WHEN** the authored ice edges are declared
- **THEN** `absolute_tundra` requires `permafrost_domain` >= its declared edge threshold
- **AND** `eternal_ice_field` requires `absolute_tundra` >= its declared edge threshold

#### Scenario: The imprisonment line branch point feeds both authored children
- **WHEN** the authored ice edges are declared
- **THEN** `frost_arrow_rain` requires `ice_shard` >= its declared edge threshold
- **AND** `ice_prison` requires `frost_arrow_rain` >= its declared edge threshold ;  the second branch point feeding BOTH
  authored children
- **AND** `blizzard` requires `ice_prison` >= its declared edge threshold
- **AND** `crystal_shatter` requires `ice_prison` >= its declared edge threshold, a branch-terminal leaf

#### Scenario: The blizzard chain continues
- **WHEN** the authored ice edges are declared
- **THEN** `absolute_zero` requires `blizzard` >= its declared edge threshold

#### Scenario: The canopy demands both authored parents
- **WHEN** the authored ice edges are declared
- **THEN** `eternal_frost_apotheosis` requires `eternal_ice_field` >= its declared edge threshold AND `absolute_zero` >= its declared edge threshold

#### Scenario: The canopy consumes both routes and nothing consumes it
- **WHEN** the canopy's edges are inspected
- **THEN** `eternal_frost_apotheosis` consumes both authored parents and is itself consumed by no
  edge ;  the lore's 匯合 of 遲緩 and 監禁 at the 神格 rung

#### Scenario: PASSIVE rationale for staying out of the graph
- **WHEN** the element-mastery passive is considered as a tree node
- **THEN** it is excluded because PASSIVE skills are never consumed by edges and never accrue

#### Scenario: Threshold tuning preserves topology
- **WHEN** a valid positive edge threshold changes
- **THEN** topology/reference checks remain green; fixed synthetic trees independently prove multi-parent qualification, reverse-edge caps and exact boundary behavior

### Requirement: The lightning lineage ships as the authored two-root branching tree with a two-parent canopy
`SKILL_REGISTRY` SHALL carry prerequisite edges forming the authored lightning tree of the node-data
authority (`docs/lore/skill-trees/lightning.md`): TWO roots ;  `static_ward` (先制路線) and
`spark_shock` (過載路線) ;  each with no prerequisites. The two routes are otherwise independent
chains; they converge ONLY at the strict topological canopy `thunder_apotheosis`. The
element-mastery passive SHALL NOT be a tree node.

#### Scenario: The lightning tree validates with two roots and the canopy last
- **WHEN** the registry loads with the authored lightning edges
- **THEN** the topological order runs both roots (`static_ward`, `spark_shock`) before their
  descendants and `thunder_apotheosis` last (consuming two parents and consumed by no edge),
  `judgement_thunder` and `divine_lightning_slaughter` are consumed only by the canopy edge at
  its authored threshold, and every edge threshold is >= 1

#### Scenario: Both branch points gate exactly their authored children
- **WHEN** the reverse-edge map is inspected for `spark_shock`, `thunder_combo` and the two
  branch-terminal leaves
- **THEN** `spark_shock` is consumed by exactly two edges (chain_lightning at its declared edge threshold and paralyzing_bolt
  at its declared edge threshold) and `thunder_combo` by exactly two (thunder_gods_haste at its declared edge threshold and thunder_shatter_strike at
  its declared positive edge threshold), `thunder_shatter_strike` and `thunder_prison` consume exactly one edge each and are consumed
  by none, and no cross-route edge exists between the initiative line and the overload line outside
  the canopy's two authored parent edges

#### Scenario: The mastery passive stays out of the graph
- **WHEN** the reverse-edge map is inspected for `lightning_mastery`
- **THEN** no entry is consumed by or consumes any prerequisite edge

#### Scenario: The initiative line branch point feeds both authored children
- **WHEN** the authored lightning edges are declared
- **THEN** `lightning_flicker` requires `static_ward` >= its declared edge threshold
- **AND** `thunder_combo` requires `lightning_flicker` >= its declared edge threshold ;  the branch point feeding BOTH authored
  children
- **AND** `thunder_gods_haste` requires `thunder_combo` >= its declared edge threshold
- **AND** `thunder_shatter_strike` requires `thunder_combo` >= its declared edge threshold, a branch-terminal leaf

#### Scenario: The haste chain continues
- **WHEN** the authored lightning edges are declared
- **THEN** `judgement_thunder` requires `thunder_gods_haste` >= its declared edge threshold

#### Scenario: The overload root branches at itself
- **WHEN** the authored lightning edges are declared
- **THEN** `chain_lightning` requires `spark_shock` >= its declared edge threshold AND `paralyzing_bolt` requires
  `spark_shock` >= its declared edge threshold ;  the root's own branch point

#### Scenario: The overload chains continue
- **WHEN** the authored lightning edges are declared
- **THEN** `lightning_strike` requires `chain_lightning` >= its declared edge threshold
- **AND** `thunder_prison` requires `paralyzing_bolt` >= its declared edge threshold, a branch-terminal leaf
- **AND** `heavens_thunder` requires `lightning_strike` >= its declared edge threshold
- **AND** `divine_lightning_slaughter` requires `heavens_thunder` >= its declared edge threshold

#### Scenario: The canopy demands both authored parents
- **WHEN** the authored lightning edges are declared
- **THEN** `thunder_apotheosis` requires `judgement_thunder` >= its declared edge threshold AND
  `divine_lightning_slaughter` >= its declared edge threshold

#### Scenario: The canopy consumes both routes and nothing consumes it
- **WHEN** the canopy's edges are inspected
- **THEN** `thunder_apotheosis` consumes both authored parents and is itself consumed by no
  edge ;  the lore's 匯合 of 先制 and 過載 at the 神格 rung

#### Scenario: PASSIVE rationale for staying out of the graph
- **WHEN** the element-mastery passive is considered as a tree node
- **THEN** it is excluded because PASSIVE skills are never consumed by edges and never accrue

#### Scenario: Threshold tuning preserves topology
- **WHEN** a valid positive edge threshold changes
- **THEN** topology/reference checks remain green; fixed synthetic trees independently prove multi-parent qualification, reverse-edge caps and exact boundary behavior

### Requirement: Identity rejection is distinct from an unmet prerequisite
Use-eligibility failure SHALL distinguish identity rejection from an unmet prerequisite. An identity-ineligible root SHALL reject without assuming a prerequisite exists and without any dice or state change.

#### Scenario: Owned root cannot crash the gate
- **WHEN** an ineligible owner invokes a skill with no prerequisite edges
- **THEN** a named identity rejection is returned before costs, effects and practice; unmet-edge detail remains reserved for actual unmet edges
