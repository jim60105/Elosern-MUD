## Purpose

Element mastery is the learned whole-tree reward of one element: the mastery
passive follows every ordinary branch of its element's catalog, so holding it
means having practised the whole lineage, and holding it lawfully is what
entitles freeform scaling of that element's eligible spells. The entitlement
and scale-derivation queries are pure and write no state; the acquisition
itself is written by the progression rules under their own transaction.

## Requirements

### Requirement: Mastery ownership entitles freeform scaling of the element's eligible spells
Elemental freeform entitlement SHALL require direct mastery ownership, identity and effect
eligibility, and a lawful directly owned prerequisite closure meeting every declared proficiency
threshold; the query SHALL validate the element first and remain side-effect-free.

#### Scenario: A mastery holder's scale set follows the cast skill's proficiency ladder
- **WHEN** an actor lawfully owns a synthetic element's mastery and a synthetic ladder assigns successive scales to proficiency levels
- **THEN** the returned ascending scale set contains exactly the rungs reached by the cast skill's own proficiency and derived cap

#### Scenario: A sibling skill's proficiency never raises the set
- **WHEN** a lawful mastery owner has greater proficiency in one synthetic spell than another spell of the same element
- **THEN** the second spell's scale set remains limited to its own proficiency

#### Scenario: An entity without mastery receives an empty set
- **WHEN** an actor lacks direct mastery ownership or holds only a conferred mastery
- **THEN** the freeform scale set is empty regardless of innate magic or other proficiency

#### Scenario: An unknown element fails closed
- **WHEN** entitlement is queried for an unregistered element, even with a fabricated matching mastery key
- **THEN** the query raises a validation error before ownership can grant entitlement and writes nothing

#### Scenario: freeform_scales_for is the single ladder authority
- **WHEN** any consumer requests scales for a skill
- **THEN** one shared derivation returns an empty tuple for absent element or unlawful mastery, otherwise the authored ascending proficiency rungs bounded by that skill's cap

#### Scenario: Entitlement grants no scale by itself
- **WHEN** the entitlement query returns true
- **THEN** the cast skill's own proficiency and the authored scale ladder still determine the allowed scales

#### Scenario: A low derived tip cap excludes the top rung
- **WHEN** a synthetic skill's derived cap falls below a ladder rung's minimum level
- **THEN** that rung remains unavailable

#### Scenario: Skill anchoring protects consumers from rejected rungs
- **WHEN** preview, resolver or presentation asks for an eligible skill's scales
- **THEN** all receive the same skill-anchored set, independent of sibling proficiency

#### Scenario: Neither function writes entity state
- **WHEN** entitlement or scale derivation is queried repeatedly
- **THEN** entity and world state remain unchanged

#### Scenario: The empty tuple gates non-default scales
- **WHEN** an actor's allowed scale tuple is empty
- **THEN** every non-default scale is forbidden for that skill

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
