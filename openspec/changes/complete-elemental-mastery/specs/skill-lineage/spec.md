# Spec Delta

## MODIFIED Requirements

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

## REMOVED Requirements

### Requirement: The fire lineage ships as the authored branching tree with a two-parent canopy
**Reason**: Authored node rosters belong in registry/lore data; the former exclusion of mastery from lineage conflicts with the learned whole-tree mechanism.
**Migration**: Preserve authored ordinary edges in tracked catalog documentation, use the generic mastery/graph contracts, and reassociate discoverable tests by assertion role without compatibility IDs.

### Requirement: The wind lineage ships as the authored two-root branching tree with a two-parent canopy
**Reason**: Authored node rosters belong in registry/lore data; the former exclusion of mastery from lineage conflicts with the learned whole-tree mechanism.
**Migration**: Preserve authored ordinary edges in tracked catalog documentation, use the generic mastery/graph contracts, and reassociate discoverable tests by assertion role without compatibility IDs.

### Requirement: The ice lineage ships as the authored two-root branching tree with a two-parent canopy
**Reason**: Authored node rosters belong in registry/lore data; the former exclusion of mastery from lineage conflicts with the learned whole-tree mechanism.
**Migration**: Preserve authored ordinary edges in tracked catalog documentation, use the generic mastery/graph contracts, and reassociate discoverable tests by assertion role without compatibility IDs.

### Requirement: The lightning lineage ships as the authored two-root branching tree with a two-parent canopy
**Reason**: Authored node rosters belong in registry/lore data; the former exclusion of mastery from lineage conflicts with the learned whole-tree mechanism.
**Migration**: Preserve authored ordinary edges in tracked catalog documentation, use the generic mastery/graph contracts, and reassociate discoverable tests by assertion role without compatibility IDs.
