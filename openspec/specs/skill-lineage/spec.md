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

### Requirement: can_use_skill is the single shared use-eligibility predicate
`can_use_skill(entity, skill)` SHALL be a pure query returning False unless the key is owned, identity/restrictions pass and every prerequisite key is owned at or above its declared minimum proficiency. The shared predicate SHALL gate ACTIVE skills and require the lawful full prerequisite closure for elemental mastery passives.

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

#### Scenario: A mastery checks internal ancestor edges
- **WHEN** a synthetic owned mastery has qualified terminal XP but an ancestor below a declared internal edge
- **THEN** the shared use gate denies the mastery without changing state

#### Scenario: A passive submission never dereferences a missing edge
- **WHEN** an action request names a directly owned passive whose closure fails solely through an ancestor restriction
- **THEN** the action rejects as non-ACTIVE without an exception, dice or state change, preserving ACTIVE rejection ordering

### Requirement: Successful ACTIVE resolution accruses lineage practice XP
Successful ACTIVE resolution SHALL award practice XP atomically from the configured base and independent race, affinity, conferred-growth and owned scoped-growth factors; affinity and owned elemental growth SHALL apply to registered elemental-magic learning, including damage-free spells, while other domains remain neutral and PASSIVE skills earn no XP.

#### Scenario: A physical skill accrues like a spell
- **WHEN** an ACTIVE sword skill resolves successfully for a fixed synthetic race (learning x2) with no affinity and no growth buff
- **THEN** `db.skill_proficiency[skill_key]` increases by exactly `SKILL_PRACTICE_XP_PER_USE × 2.0`

#### Scenario: The affinity multiplier participates
- **WHEN** an entity with `affinity_elements == ["t_element"]` successfully casts a fixed synthetic elemental-magic spell
- **THEN** the accrued XP carries a synthetic configured `1.25` factor; a non-favored element carries the synthetic configured `0.75` factor, and a
  physical skill carrying `element == t_element` carries `1.0`

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
- **THEN** it is the product of the multipliers of every eligible owned scoped `growth_rate` effect carried by a
  skill the actor OWNS whose declared scope equals the element of the skill being practised, and
  `1.0` for a skill of any other element, a skill outside elemental magic and a skill declaring no element, so an unscoped
  acceleration is not expressible

#### Scenario: Neither growth factor reads the other
- **WHEN** the owned-skill growth factor and `growth_rate_multiplier(entity)` (the conferred-buff
  pull path) are both in play
- **THEN** the two factors are independent; they multiply, and neither reads the other

#### Scenario: The affinity factor is magic-damage-scoped
- **WHEN** affinity and owned scoped growth are evaluated for a synthetic ACTIVE elemental-magic skill with a registered element
- **THEN** both use that element regardless of damage, healing, buff, control, cleanse or mixed effects; elemental-tagged physical martial skills and other learning domains use neutral elemental factors

#### Scenario: Storage and derivation are unchanged
- **WHEN** practice XP accrues
- **THEN** it lands in `db.skill_proficiency[skill_key]` as float XP with `level = floor(xp / configured_xp_per_level)`

#### Scenario: A simulated resolution accrues nothing
- **WHEN** a resolution carries the simulated marker (a guild examination's
  `event_context["simulated"]`)
- **THEN** it accrues nothing

#### Scenario: Accrual ignores school and stats
- **WHEN** any accrual is computed
- **THEN** it reads neither the actor's school nor any magic stat

#### Scenario: The one divine cadence exception
- **WHEN** an ACTIVE skill in `SkillCategory.DIVINE_MYSTERY` resolves successfully; the exactly one
  category-scoped exception that additionally passes a per-world-calendar-day claim before accruing
- **THEN** that rule and its scenarios are owned by the `divine-mystery` capability and SHALL NOT be
  restated here; no other category carries a cadence of any kind

#### Scenario: Damage-free magic shares both award paths
- **WHEN** synthetic elemental healing, self-buff and control skills are practised through successful use and booked study
- **THEN** both paths apply the same affinity and owned scoped-growth eligibility, retaining their independently configured base amounts and caps

#### Scenario: Learning modifiers change XP alone
- **WHEN** the same synthetic eligible spell is resolved with different elemental affinity or owned scoped-growth factors
- **THEN** XP changes by those factors while innate bases, resolved damage/heal output and MP charge remain unchanged

#### Scenario: No declared affinity remains neutral
- **WHEN** a synthetic learner has no declared elemental affinity
- **THEN** the affinity factor is neutral for each eligible elemental skill, with owned scoped growth evaluated independently

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
Allowed freeform scales SHALL derive from the authored progression ladder over the skill's OWN proficiency, gated by lawful direct elemental-mastery entitlement. Rungs above the skill's derived cap SHALL never unlock. Numeric ladder examples SHALL use fixed synthetic rows rather than approve production thresholds or scale values.

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
- **WHEN** an actor lacks lawful direct mastery entitlement, including an owned mastery with an unmet closure
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
Within the all-or-nothing import transaction, missing prerequisite proficiency SHALL seed exactly to its declared requirement, never above, and ownership SHALL extend to transitive closure. Explicit proficiency SHALL always win, even below eligibility; an invalid mastery closure SHALL deny use and entitlement. Scene spawn and preset activation SHALL share the same closure/seed mechanisms.

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
- **WHEN** the originally covered preset, import and scene construction paths close and seed a declared skill kit
- **THEN** it uses the shared closure/seed algorithms without a copied implementation or a fixed caller-count assertion

#### Scenario: Mastery closure includes every declared branch
- **WHEN** a synthetic preset, import or scene declares a mastery whose prerequisites cover disconnected ordinary branches
- **THEN** each path obtains identical transitive ownership and minimum prerequisite XP

#### Scenario: Explicit low ancestor XP never creates invalid entitlement
- **WHEN** that record explicitly declares an internal ancestor below its required edge
- **THEN** the explicit XP remains unchanged and the mastery stays unusable and unentitled until lawful practice repairs the edge

### Requirement: Identity rejection is distinct from an unmet prerequisite
Use-eligibility failure SHALL distinguish identity rejection from an unmet prerequisite. An identity-ineligible root SHALL reject without assuming a prerequisite exists and without any dice or state change.

#### Scenario: Owned root cannot crash the gate
- **WHEN** an ineligible owner invokes a skill with no prerequisite edges
- **THEN** a named identity rejection is returned before costs, effects and practice; unmet-edge detail remains reserved for actual unmet edges
