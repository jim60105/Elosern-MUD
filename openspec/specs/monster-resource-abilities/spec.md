# monster-resource-abilities Specification

## Purpose
Defines the approved crocodile resource ability and its complete authored-kit, combat, payment and persistence behavior through the common player/NPC/monster skill engine.

## Requirements

### Requirement: Monster ability identity and composition are authored registry data
Executable monster abilities SHALL come from validated authored skills and variant kits. Species/variant names, kit membership, effect keys and taxonomy choices SHALL remain data. Shared identity eligibility SHALL reject incompatible ownership before dice or writes and exclude monster-only abilities from character catalogs. Existing target, battlefield, cost-tier and freeform-shape gates SHALL apply without species-specific branches.

#### Scenario: Declaration closure
- **WHEN** a shipped kit is inspected
- **THEN** all skill, kind, eligibility, prerequisite, effect, buff and behavior references resolve; no prose creates an effect

#### Scenario: Contact and shared selection
- **WHEN** a synthetic physical SINGLE ability selects a dead, displaced, missing target or valid ally
- **THEN** shared gates reject invalid contact; enemy-only effects never reach allies; selectable-outside-combat damage still requires a battlefield

#### Scenario: Independent composition checks
- **WHEN** synthetic damage/transfer, enemy hit-rider and hit-independent self-guard kits execute
- **THEN** ordinary physical damage reads physical attack, elemental taxonomy adds no magic-power scaling, and effect audiences follow declarations

### Requirement: Hit-qualified transfers credit actual removal once
A hit-dependent resource transfer SHALL use invocation-local hit evidence for its referenced damage occurrence and recipient. It SHALL credit the caster from actual removal within target and caster caps, once per target; misses SHALL transfer nothing. Critical damage SHALL NOT multiply transfer, zero resources SHALL NOT cancel damage, and defeat-crossing hits SHALL finish same-action transfer.

#### Scenario: Actual removal oracle
- **WHEN** a synthetic target has MP 3, drain request 10, full recovery share and caster MP 20 with cost 10
- **THEN** target ends at 0 and caster at 13; untouched controls remain unchanged

#### Scenario: Hit evidence and defeat
- **WHEN** synthetic hit, miss, absorbed hit, critical and defeat-crossing cases execute
- **THEN** hit qualifies independently of HP loss, miss excludes the rider, and no duplicate credit or second hit roll occurs

#### Scenario: Transfer limits
- **WHEN** a transfer-only component is read
- **THEN** it grants no undeclared HP healing or permanent stat mutation

### Requirement: Monster effects and payments share the ordinary atomic action
Affordability SHALL precede dice/effects for both adjusted resource costs. Effects and capped recovery SHALL precede payment once in the ordinary transaction. Rejected requests SHALL write nothing; late failure SHALL restore all touched gauges, buffs and practice claims. Resource modifiers and reactions SHALL keep their existing order. Narrative and forged environment context SHALL grant no runtime effect.

#### Scenario: Order at the cap
- **WHEN** a synthetic caster starts at maximum MP 30, removes 10 with full share and pays MP 10/SP 5
- **THEN** MP ends at 20 and SP drops by 5; starting MP 20 also ends at 20

#### Scenario: Unaffordable and invalid requests
- **WHEN** either resource is short or the target is invalid or missing
- **THEN** no roll, buff, damage, cost or practice occurs; drain cannot fund initial affordability

#### Scenario: Late rollback
- **WHEN** failure follows a relevant gauge/buff write and acquired practice claim
- **THEN** reload and caches match pre-action snapshots and a retry succeeds without stale claims

#### Scenario: Environment remains prose
- **WHEN** otherwise identical sessions vary ecological prose or forged environmental facts
- **THEN** outcomes stay unchanged without a new environment engine

### Requirement: Timed monster effects follow declared recipients and lifetime
Timed effects SHALL use their declared audience, hit dependency, duration, polarity and modifier reference. Refresh SHALL replace lifetime without accumulating magnitude; expiry/removal SHALL remove the contribution. Enemy riders SHALL require the referenced enemy hit. A hit-independent self effect SHALL reach only the caster on a valid affordable resolved attempt, including misses, and SHALL grant nothing on rejected or no-target requests.

#### Scenario: Rider routing
- **WHEN** a synthetic enemy-rider kit hits, misses and hits with fully absorbed damage
- **THEN** only hit-qualified selected enemies gain one effect; caster/ally controls stay unchanged

#### Scenario: Self routing
- **WHEN** a synthetic guard kit misses a valid enemy and then attempts invalid/no-target casts
- **THEN** the valid attempt grants caster guard only; rejected casts grant nothing

#### Scenario: Lifetime
- **WHEN** an aged instance is refreshed then time crosses its refreshed expiry
- **THEN** one same-key contribution persists until expiry and none remains afterward; no undeclared DoT, displacement or lock appears

### Requirement: Delivered monster compositions retain representative consumer evidence
Every shipped variant SHALL receive generic identity/profile/kit/reference checks. Representative production smoke SHALL execute each distinct delivered composition through formal construction, real policy selection, resolver payment and committed reload without live generative services. Shared synthetic suites SHALL establish mechanism arithmetic, hit/miss, recipient controls and post-write rollback; a new species reusing a composition SHALL NOT clone that engine battery.

#### Scenario: Real consumer boundaries
- **WHEN** representatives of all delivered composition shapes execute then deplete either payable resource
- **THEN** victim/caster/control state, payment, ordinary fallback and reloaded identity/kit/depleted resources are observed independently

#### Scenario: Shared reuse
- **WHEN** a second synthetic species is constructed with an eligible synthetic transfer kit
- **THEN** it actually executes the same APIs with isolated hit evidence and independently known end state

#### Scenario: Data edit
- **WHEN** valid species names or kit keys change with all references updated
- **THEN** integrity and representative wiring tests pass without copying a roster approval table

### Requirement: Bestiary documentation covers keyed public content relationships
Published bestiary documentation SHALL identify every shipped species and variant by stable key, attach each variant to its owning species and reference only public narrative fields. Current executable status SHALL follow declared kits; historical approval notes SHALL be separate. Programmatic checks SHALL reject missing, duplicate, orphan or wrong-owner documentation links and private-field references without pinning prose sentences.

#### Scenario: Complete keyed documentation
- **WHEN** the shipped registries and current bestiary index are checked
- **THEN** species and variant keys match in both directions, each public field link resolves and every variant links to its actual species

#### Scenario: Fault detection
- **WHEN** a section link is removed, duplicated, orphaned, assigned to a wrong species or points to a private field
- **THEN** the check fails naming key and relationship

#### Scenario: Prose remains editable
- **WHEN** public prose is reworded in its existing valid keyed sections
- **THEN** relationship checks pass; editorial review assesses semantic accuracy and approved ability limits
