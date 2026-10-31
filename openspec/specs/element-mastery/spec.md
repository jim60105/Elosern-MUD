## Purpose

Element mastery is the learned whole-tree reward of one element: the mastery
passive follows every ordinary branch of its element's catalog, so holding it
means having practised the whole lineage, and holding it lawfully is what
entitles freeform scaling of that element's eligible spells. Everything here is
a pure, side-effect-free query; nothing in this capability writes game state.

## Requirements

### Requirement: Mastery ownership entitles freeform scaling of the element's eligible spells
Elemental freeform entitlement SHALL require direct mastery ownership, identity and effect
eligibility, and a lawful directly owned prerequisite closure meeting every declared proficiency
threshold; the query SHALL validate the element first and remain side-effect-free.

#### Scenario: A mastery holder's scale set follows the cast skill's proficiency ladder
- **WHEN** `freeform_scales_for(entity, skill)` is called for a fire skill on an entity whose
  `owned_keys()` contains `"fire_mastery"` and whose proficiency in THAT skill reaches 10
- **THEN** it returns `(0.25, 0.5, 1.0, 2.0, 4.0)` in ascending order; at level 0 it returns
  `(0.25,)`, at level 1 `(0.25, 0.5)`, at level 3 `(0.25, 0.5, 1.0)`, at level 6
  `(0.25, 0.5, 1.0, 2.0)`

#### Scenario: A sibling skill's proficiency never raises the set
- **WHEN** the entity holds level-10 proficiency in one fire skill and level 0 in another
- **THEN** `freeform_scales_for` returns `(0.25,)` for the level-0 skill regardless of the sibling

#### Scenario: An entity without mastery receives an empty set
- **WHEN** `freeform_scales_for(entity, skill)` is called on an entity without the element's
  mastery, including one with a high magic level and one holding only a `ConferredSkillGrant`
  referencing `<element>_mastery`
- **THEN** it returns `()` in both cases

#### Scenario: An unknown element fails closed
- **WHEN** `freeform_mastery_entitled(entity, "not_an_element")` is called on an entity owning
  `"not_an_element_mastery"`
- **THEN** it raises `ValueError` and writes no state

#### Scenario: freeform_scales_for is the single ladder authority
- **WHEN** `world/rules/progression.py`'s `freeform_scales_for(entity, skill) -> tuple[float, ...]`
  is called
- **THEN** it returns `()` for a skill with no element or an entity that is not
  `freeform_mastery_entitled` for that skill's element, and otherwise the ascending rungs of the
  `progression.yaml` `freeform_scale_ladder` whose `min_level` the entity's OWN
  `skill_proficiency_level` for THAT SKILL reaches — 0.25 unconditionally for an entitled actor,
  0.5 at level >= 1, 1.0 at >= 3, 2.0 at >= 6, 4.0 at >= 10

#### Scenario: Entitlement grants no scale by itself
- **WHEN** `freeform_mastery_entitled` returns `True`
- **THEN** it SHALL grant no scale by itself

#### Scenario: A low derived tip cap excludes the top rung
- **WHEN** a skill's derived tip cap is below 10
- **THEN** the returned set can never include 4.0

#### Scenario: Skill anchoring protects consumers from rejected rungs
- **WHEN** proficiency is anchored to the cast skill
- **THEN** proficiency in a sibling skill of the same element SHALL NOT raise the returned set, so
  no consumer can advertise a rung the resolver would reject

#### Scenario: Neither function writes entity state
- **WHEN** either function is called
- **THEN** neither SHALL write any entity state

#### Scenario: The empty tuple gates non-default scales
- **WHEN** the freeform-casting gate consumes the returned tuple and it is empty
- **THEN** every non-`1.0` scale for that skill is forbidden

#### Scenario: Bare ownership cannot shortcut an unfinished branch
- **WHEN** a directly owned synthetic mastery has satisfied terminal XP but a missing prerequisite owner or an internal edge below its threshold
- **THEN** entitlement and mastery usability are false until the entire declared closure is lawful

#### Scenario: Identity and restrictions apply throughout the closure
- **WHEN** a synthetic mastery or one of its prerequisites is identity-ineligible or effect-restricted
- **THEN** entitlement is false even when all keys and XP are present

#### Scenario: Conferred prerequisites cannot qualify direct mastery
- **WHEN** a prerequisite exists only as a conferred grant
- **THEN** the actor has no elemental freeform entitlement through that mastery

### Requirement: Elemental mastery prerequisites cover every ordinary branch
An elemental mastery SHALL follow all unrestricted ordinary ACTIVE branches of its elemental catalog through terminal prerequisites, preserving existing ordinary edges and their derived proficiency caps while excluding identity-restricted skills and other learning domains.

#### Scenario: Disconnected ordinary components and side branches all qualify
- **WHEN** a synthetic elemental catalog has disconnected ordinary components and a terminal side branch outside its highest attack path
- **THEN** every ordinary terminal is required with AND semantics and all ordinary nodes are in the mastery prerequisite closure

#### Scenario: Restricted and unrelated nodes do not qualify
- **WHEN** the catalog also contains species-only skills, element-tagged physical martial skills and an independent enhancement passive
- **THEN** none becomes an elemental mastery prerequisite

#### Scenario: Adding mastery preserves ordinary caps
- **WHEN** terminal prerequisites are added to a synthetic mastery
- **THEN** each terminal's resulting derived cap equals its prior ordinary cap, and ordinary prerequisite edges are unchanged

#### Scenario: Catalog integrity is independent of content labels
- **WHEN** authored skill labels or positive ordinary thresholds change while domain and prerequisite relationships remain valid
- **THEN** generic coverage/reference checks remain valid without an approved roster or copied balance table

### Requirement: Practice acquires a newly qualified elemental mastery atomically
Successful use or booked-study practice SHALL directly grant each newly qualified elemental mastery once from its declared prerequisite closure, sharing the award transaction and committed learner notification while awarding no passive XP.

#### Scenario: The last required practice acquires ownership
- **WHEN** a synthetic learner directly owns every required branch and a practice award satisfies the last unmet edge
- **THEN** the passive is directly owned and usable, and one committed learner-specific unlock notice is produced

#### Scenario: Use and study share acquisition
- **WHEN** otherwise identical synthetic learners satisfy the final requirement through use and booked study respectively
- **THEN** both acquire the same mastery through the same ownership semantics

#### Scenario: The sink is optional and grants are idempotent
- **WHEN** a qualifying award has no notification sink, or the actor repeats practice after acquisition
- **THEN** ownership is still granted without a sink and repeated awards create no duplicate ownership or notice

#### Scenario: No partial or ineligible grant
- **WHEN** a branch is unowned, a transitive edge is below threshold, identity or restrictions reject, or a use award is simulated, failed or deduplicated
- **THEN** no new mastery is granted

#### Scenario: Repairing an internal edge reevaluates mastery
- **WHEN** terminal XP already qualifies but a later award repairs an internal ancestor edge
- **THEN** the affected mastery becomes usable or is acquired as needed, and exactly one notice is staged for the transition

#### Scenario: A failed transaction publishes nothing
- **WHEN** settlement fails after a qualifying award and ownership write
- **THEN** raw and cached ownership and proficiency return to their pre-award state, retry claims remain lawful, and no unlock or dialogue refresh is delivered

#### Scenario: Passive practice remains unavailable
- **WHEN** use or study practice is requested for the obtained mastery itself
- **THEN** it awards no XP and creates no invented passive proficiency
