# Spec Delta

Archive handoff: after syncing this delta, re-list canonical IDs and annotate every new or changed substantive requirement test. Existing requirement headings are intentionally unchanged; historical titles do not preserve superseded mode or dice behavior.

## MODIFIED Requirements

### Requirement: Proposal work is deterministically bounded
The initial candidate budget SHALL be 256 and configurable in integer 1..4096. It SHALL bound deduplicated examined proposals including rejected plans. Slots SHALL be allocated round-robin across canonical skill/semantic-plan families after mandatory filtering, with a scope-digest starting offset.

#### Scenario: Exhaustion
- **WHEN** families and targets exceed the budget or many proposals fail legality
- **THEN** enumeration terminates at the bound; omitted family/target counts and exhaustion are reported without a participant cap or selection/combat RNG draw

#### Scenario: Target order and no action
- **WHEN** targets tie under the profile order or all legal plans are excluded
- **THEN** stable IDs order ties; an empty legal set returns None without forced attack or reflex fallback

### Requirement: Taunt constrains legal single-hostile target generation before estimation
For an active Taunt winner legal for an enemy single-target hostile action, candidate generation, estimation and final execution SHALL constrain that action to the winner. Hostility SHALL use the authoritative typed-effect classification. Existing range, recipient, seal and displacement restrictions SHALL remain authoritative. Effects SHALL NOT be silently redirected after selection.

#### Scenario: Non-damage harm and legal limits
- **WHEN** an enemy can choose a hostile debuff and the taunter is ordinarily legal for it
- **THEN** the candidate targets the taunter before utility scoring; if range or a mandatory seal restriction excludes that taunter, Taunt grants no exception

#### Scenario: Enemy alternatives
- **WHEN** a taunted enemy chooses an AREA action, self/allied benefit or flee
- **THEN** ordinary legal options remain available and Taunt does not force an attack or redirect area effects

#### Scenario: Suppressed winner
- **WHEN** the winner fell before the next enemy decision
- **THEN** candidate generation and estimation use ordinary legal target rules without promoting a losing declaration
