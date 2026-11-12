## Purpose

Define deterministic, rulebook-driven monster combat decisions that produce
resolver-ready actions without mutating combat state.

## Requirements

### Requirement: monster_behaviour_policy is a complete, drop-in action_provider
The monster policy SHALL retain its two-argument ActionRequest-or-None provider contract for ordinary rounds, battles and overwhelm. Ephemeral execution identity and observation seams SHALL be permitted in round and overwhelm orchestration without changing initiative, damage or settlement authority.

#### Scenario: The function is a valid action_provider for run_round
- **WHEN** an ordinary round uses the monster provider
- **THEN** its selected action resolves once through the existing resolver with the real context and scope, including scale and target representation

#### Scenario: The function is a valid action_provider for resolve_overwhelm
- **WHEN** overwhelm resolves several rounds with repeated actor slots
- **THEN** each call has its actual round/slot scope and unchanged combat formulas; every action uses the existing resolver

#### Scenario: Every decision is issued as a single ActionRequest through ActionResolver
- **WHEN** a monster proposes a nonempty action in either mode
- **THEN** one request with the same battlefield context settles once through the resolver, which alone owns effects, resource payment and action events

### Requirement: A monster with zero actions_per_turn is skipped by the existing gate, with no
monster-specific bypass
The existing round capability gate SHALL skip zero-action monsters without invoking their provider. Deliberation read-only capability validation SHALL be permitted and SHALL NOT bypass the gate or create state.

#### Scenario: monster_behaviour_policy is never called for a zeroed-actions combatant
- **WHEN** a monster has zero permitted action opportunities
- **THEN** the provider is not called and the existing skipped-action event is produced

#### Scenario: No source-level reference to combat-modifier or sexual-state concepts
- **WHEN** deliberation is inspected directly for a zero-action monster
- **THEN** no illegal candidate is proposed and capability state remains unchanged

### Requirement: No LLM or generative-layer involvement anywhere in monster decision-making
Monster decisions SHALL execute offline without generative-layer or network involvement. Reflex SHALL use public state and rulebook preferences with independent seeded skill sampling only for highest_expected_damage. Deliberation SHALL use settled public snapshots, configuration, observations and independent scope-seeded selection RNG without hidden submissions.

#### Scenario: A source scan finds no generative-layer import
- **WHEN** network services are disabled and identical public state, tuning and execution scope are replayed for both modes
- **THEN** each repeats its request offline without reading pending player intent; skill sampling never advances combat resolution RNG

#### Scenario: Repeated calls under an unchanged battlefield and RNG state produce the same decision
- **WHEN** the same public state, owned order, tuning, scope and selection RNG inputs are replayed in either mode
- **THEN** the action repeats, with target tie draws retaining their existing fixed-combat-RNG contract

### Requirement: Target selection differs by archetype and is deterministic under a fixed seed
reflex mode SHALL retain the following existing contract.
`world/rules/monster_behaviour.py` SHALL select a single target by the acting monster's `BehaviourProfile.target_strategy` ; `"lowest_hp"` (current `hp.value`) or `"highest_effective_power"` (change 9's `effective_power()`) ; breaking an exact tie by drawing from `dice.roll_d100()`, never Python's `random` module directly.

#### Scenario: lowest_hp strategy selects the enemy with the least current hp
- **WHEN** in reflex mode, target selection runs with `target_strategy: lowest_hp` against a set of living enemies with distinct `hp.value`s
- **THEN** the enemy with the smallest `hp.value` is selected

#### Scenario: highest_effective_power strategy selects the enemy with the greatest effective_power
- **WHEN** in reflex mode, target selection runs with `target_strategy: highest_effective_power` against a set of living enemies with distinct `effective_power()` values
- **THEN** the enemy with the greatest `combat.effective_power()` value is selected

#### Scenario: An exact tie is broken by a seeded roll, reproducibly
- **WHEN** in reflex mode, target selection runs against two enemies with exactly equal values under the active strategy's metric, under a fixed RNG seed
- **THEN** the same enemy is selected every time the identical seed and battlefield state are replayed, and the selection is made via a call to `dice.roll_d100()`, not `random.choice()` or equivalent

#### Scenario: Displaced enemies leave the strike-class candidate set without extra dice
- **WHEN** in reflex mode, a strike-class-only monster's target selection runs against one displaced and one undisplaced living enemy under a fixed seed, and separately against a set where every living enemy is displaced, and separately a magic-owning caster monster selects against the same mixed set
- **THEN** the first case selects the undisplaced enemy with no additional randomness draw beyond the shipped tie-break path, the second case yields no action request, and the caster monster's magic-school single-target selection keeps the displaced candidate reachable ; replaying the identical seed and state reproduces every outcome

#### Scenario: No target selection call reads combat_modifiers or rolls outside dice.roll_d100
- **WHEN** in reflex mode, targets tie under a fixed combat RNG seed
- **THEN** the chosen target and subsequent combat dice match the established sequence with no additional draws

#### Scenario: Strike-class SINGLE candidate set excludes displaced enemies
- **WHEN** in reflex mode, a STRIKE-class (physical-school damage) SINGLE-target selection computes its candidate set
- **THEN** the set excludes enemies holding a live positional-marker instance (state-only, dice-free
  ; the same metric and tie-break machinery applies to the remaining candidates)

#### Scenario: The exclusion applies at candidate selection for strike-only kits
- **WHEN** in reflex mode, skill choice can follow target choice and the acting monster's owned SINGLE-target damage
  kit is exclusively strike-class
- **THEN** the positional exclusion is applied at candidate selection

#### Scenario: Magic SINGLE kits may keep displaced candidates
- **WHEN** in reflex mode, the acting monster owns a magic-school SINGLE-target damage skill
- **THEN** it MAY keep displaced candidates for that magic kit (magic reachability is ratified
  unaffected; the step-4a resolution gate remains the sole authority for strike-class pairings)

#### Scenario: No reachable kit yields no action this round
- **WHEN** in reflex mode, the strike-class candidate set is empty while the actor holds no reachable magic SINGLE kit or usable AREA kit
- **THEN** the policy returns no action for this round, deterministic and reproducible under a fixed
  seed exactly like the no-living-enemies case

#### Scenario: The AREA shorthand candidate set keeps displaced enemies
- **WHEN** in reflex mode, the AREA shorthand candidate set is computed
- **THEN** it keeps displaced candidates (area reachability is unaffected)

#### Scenario: The delegated policy applies the identical positional exclusion
- **WHEN** in reflex mode, the delegated `default_attack_policy` computes its strike-class candidate set
- **THEN** it applies the identical positional exclusion

### Requirement: Skill selection differs by archetype, comparing owned skills by a dice-free expected
Reflex SHALL consider qualified affordable owned ACTIVE damage skills of SINGLE and AREA shape together, excluding innate basic_attack until no authored option is usable. first_owned SHALL choose the first usable authored skill in owned order without evaluation or a selection draw. highest_expected_damage SHALL use the exact own-output metric and independent sampling defined below. Selection SHALL apply no effects or payments.

#### Scenario: first_owned selects the first matching skill in the entity's own owned order
- **WHEN** first_owned has two usable authored skills of either shape and an innate basic_attack
- **THEN** the first authored skill in owned order is selected without computing scores or drawing selection RNG

#### Scenario: Single authored kit is always used
- **WHEN** either reflex strategy has exactly one usable authored damage kit plus basic_attack
- **THEN** the authored kit is returned for every seed without a selection draw

#### Scenario: Unavailable kit falls back
- **WHEN** all authored damage skills are unaffordable, unqualified or have no usable target
- **THEN** the qualified innate basic_attack is used if legal; otherwise the policy returns None

#### Scenario: Own-output inputs
- **WHEN** a physical skill has primary damage coefficient 1.5, adjusted own attack 10 including an own buff, and two living hostile recipients
- **THEN** its SINGLE estimate is 15 and its AREA estimate is 30, without effects or payments

#### Scenario: Damage policy ordinal
- **WHEN** a skill has a non-damage occurrence before its primary damage occurrence with coefficient 1.5
- **THEN** the estimate uses that damage occurrence coefficient and school rather than the preceding occurrence policy

#### Scenario: Defender inputs are excluded
- **WHEN** defender defense, defense buffs, agility or hit chance changes with actor adjusted attack, coefficient and living recipient count fixed
- **THEN** the reflex estimates and sampling probabilities remain identical

#### Scenario: highest_expected_damage selects the skill with the greatest estimated output
- **WHEN** two usable authored skills have distinct exact E and an injected draw falls in the greater-score skill's probability interval
- **THEN** that skill is selected; greater E gives greater probability without guaranteeing every draw chooses it

#### Scenario: An unaffordable preferred skill falls back to an affordable damage skill
- **WHEN** an authored AREA skill is unaffordable and an authored SINGLE damage skill is usable
- **THEN** only the usable authored skill participates; it is chosen ahead of innate basic_attack

#### Scenario: Skill-choice comparison never rolls dice
- **WHEN** exact scores are calculated, then highest_expected_damage samples tied or distinct multiple options
- **THEN** score calculation uses no randomness and selection uses only independent RNG, never combat d100; first_owned and singleton choice draw nothing

#### Scenario: The estimate subtracts the known target's defense
- **WHEN** a known SINGLE target has nonzero adjusted defense
- **THEN** the superseding reflex estimate is A*c*1 with no subtraction or other defender term; changing that defense leaves E unchanged

#### Scenario: Affordability is evaluated before the area-versus-single decision
- **WHEN** a mixed-shape authored kit contains affordable and unaffordable skills
- **THEN** affordability filtering precedes the unified skill selection, without an early shape gate

#### Scenario: Ineligible preferred skill falls back without rolling a cast
- **WHEN** authored skills fail shared identity or prerequisite qualification and the innate attack is legal
- **THEN** reflex returns the innate attack without a cast roll; initiative-time resolver validation remains authoritative

### Requirement: Highest-expected-damage comparison uses effective value and one tie-breaking roll
Reflex highest_expected_damage SHALL sample exact E(s)=A(s)*c(s)*R(s) by stable softmax at the archetype reflex_temperature, using independent injectable scope-seeded RNG. A is own adjusted school attack, c the primary damage coefficient, and R is 1 for SINGLE or living hostile recipients for AREA. Equal estimates SHALL have equal probabilities. No buckets, defender terms or hit chance SHALL enter E; combat resolution dice SHALL remain untouched.

#### Scenario: Larger exact score has larger probability
- **WHEN** two authored skills have E values 15 and 20 at finite positive temperature
- **THEN** the latter has strictly greater probability; no quantisation merges the scores

#### Scenario: Exact ties retain uncertainty
- **WHEN** two usable authored skills have equal exact E
- **THEN** they have equal probabilities, stable owned interval order and no combat-dice tie roll

#### Scenario: The comparison stat and the single tie-break roll
- **WHEN** highest_expected_damage samples two equal exact E values using a pinned independent draw
- **THEN** the resulting skill repeats under that draw; the former combat-dice tie roll is absent

#### Scenario: Injected-seed replay
- **WHEN** state, owned order, tuning, initial injected RNG seed and real scope are replayed
- **THEN** the same skill is returned; subsequent combat hit, damage and initiative RNG are unchanged

#### Scenario: Round scope may vary the choice
- **WHEN** two usable skills are sampled with unchanged state across actual rounds or action slots
- **THEN** each uses its real distinct scope seed and may choose differently; repeating either scope reproduces its choice

#### Scenario: Fixed-seed distribution sanity
- **WHEN** two synthetic skills have E 10 and 20, temperature 10, and fresh private generators seeded with each integer 0 through 199
- **THEN** the stronger skill is chosen more than 100 times and fewer than 200 times; rerunning the finite seed set repeats every choice

#### Scenario: Temperature is independent of intelligence
- **WHEN** a reflex profile temperature changes while intelligence is fixed, then intelligence changes with temperature fixed
- **THEN** only the temperature change alters reflex probabilities; deliberation retains its own intelligence-based temperature

### Requirement: Area-versus-single-target shape is decided before target/skill selection, reusing the
Reflex SHALL consider usable SINGLE and AREA skills in one strategy selection without an early shape gate. AREA SHALL use all-enemies shorthand. The area-preference flag SHALL have no reflex effect; it retains only its existing deliberation scoring role. SINGLE target restrictions SHALL remain authoritative without eliminating usable AREA options.

#### Scenario: Coverage changes probability ordering
- **WHEN** adjusted attack is 10, SINGLE coefficient 1.5 and AREA coefficient 1.0, with one living hostile then two
- **THEN** E changes from SINGLE 15 versus AREA 10 to SINGLE 15 versus AREA 20; AREA becomes more probable and a pinned draw in its interval returns all-enemies

#### Scenario: Recipient controls
- **WHEN** an AREA roster has two living hostiles plus a dead enemy, a fled enemy and an ally
- **THEN** R is 2; excluded recipients do not increase its score

#### Scenario: No flag gate
- **WHEN** the area-preference flag is false and AREA has greater E than SINGLE
- **THEN** AREA participates with greater probability; toggling the flag does not alter reflex probabilities

#### Scenario: Single enemy can receive area
- **WHEN** one living enemy remains and a usable authored AREA is selected
- **THEN** the request retains all-enemies shorthand; there is no multiple-enemy admission gate

#### Scenario: Single restrictions do not erase area
- **WHEN** all SINGLE target options fail positional restrictions while AREA is usable
- **THEN** AREA remains selectable without applying SINGLE seal or Taunt narrowing to its roster

#### Scenario: An archetype preferring area skills uses one when multiple enemies are present
- **WHEN** the area flag is true, multiple living hostiles make AREA E larger, and an injected draw lies in AREA's interval
- **THEN** AREA is selected through the common metric with all-enemies shorthand; the flag grants no reflex admission or probability bonus

#### Scenario: A single living enemy never triggers the area branch
- **WHEN** one living enemy remains with usable authored SINGLE and AREA skills
- **THEN** the former early-return area branch does not exist; both skills participate with R=1 under the configured strategy

#### Scenario: An archetype not preferring area still falls back to it if no single-target skill exists
- **WHEN** the area flag is false and only an authored AREA damage skill is usable
- **THEN** that skill is selected ahead of the innate attack using all-enemies shorthand

#### Scenario: An entity owning no eligible damage skill of either shape returns None
- **WHEN** neither any authored damage skill nor innate basic_attack is usable
- **THEN** the policy returns None

### Requirement: A non-Monster entity is delegated to change 9's default_attack_policy unmodified
`monster_behaviour_policy(entity, battlefield)` SHALL detect whether `entity` is a `Monster` by checking
for a `threat_tier` attribute, and SHALL delegate entirely to
`world.rules.combat.default_attack_policy(entity, battlefield)` for any entity lacking one, with no
difference in outcome from calling `default_attack_policy` directly.

#### Scenario: A PlayerCharacter or NPC entity produces the identical decision as default_attack_policy
- **WHEN** `monster_behaviour_policy(entity, battlefield)` is called for an entity with no `threat_tier`
  attribute
- **THEN** it returns the exact same value `combat.default_attack_policy(entity, battlefield)` would
  return for the identical arguments

#### Scenario: A Monster entity never falls through to the delegation branch
- **WHEN** `monster_behaviour_policy(entity, battlefield)` is called for an entity with a `threat_tier`
  attribute
- **THEN** `combat.default_attack_policy` is not called at all for that turn

### Requirement: Golden fixed-seed tests demonstrate distinct, reproducible behaviour across MonsterTiers
Reflex SHALL honor distinct authored tier-default profiles on the same battlefield and reproduce decisions under identical state, tuning and random inputs. Synthetic fixtures SHALL establish strategy differences without fixing the shipped tier mapping, archetype roster or balance values.

#### Scenario: Low-tier and calamity-tier monsters choose different targets on an identical roster
- **WHEN** two synthetic tier-default profiles use lowest_hp and highest_effective_power on the same roster with distinct metric winners and each actor has one usable SINGLE kit
- **THEN** each chooses its configured metric winner without relying on the shipped tier-to-archetype mapping

#### Scenario: The golden fixture's decisions are byte-identical across repeated runs under the same seed
- **WHEN** in reflex mode, the synthetic fixture is run twice under identical tuning, scope, fixed seed and starting battlefield state
- **THEN** every `ActionRequest` `monster_behaviour_policy()` produces across both runs is identical in
  `skill_key` and `targets`

### Requirement: A delegated non-Monster entity proposes the first usable resolver-backed damage skill
`world/rules/combat.py`'s `default_attack_policy(entity, battlefield)` SHALL consider every owned
`ACTIVE` skill with a `damage:`-prefixed effect and select the first one `ActionResolver` can
resolve — ownership, prerequisite satisfaction via `can_use_skill`, and MP affordability are the
eligibility gates.

#### Scenario: A prerequisite-unsatisfied spell falls back to the innate basic_attack
- **WHEN** `default_attack_policy` runs for a non-Monster entity (e.g. a party NPC) that owns an
  affordable `firestorm` whose `scorching_wave` prerequisite is below the edge threshold — and a
  living enemy is present
- **THEN** the returned `ActionRequest` names `"basic_attack"` targeting that enemy, never the
  gated spell, and `ActionResolver` accepts the request

#### Scenario: An unaffordable spell falls back to the innate basic_attack
- **WHEN** `default_attack_policy` runs for a non-Monster entity (e.g. a party NPC) that owns an
  elemental spell it cannot afford — `skills=["firestorm"]`, `mp < 30` — and a living enemy
  is present
- **THEN** the returned `ActionRequest` names `"basic_attack"` targeting that enemy, never the
  unaffordable spell, and `ActionResolver` accepts the request

#### Scenario: A usable owned spell is chosen ahead of the innate
- **WHEN** the entity owns an affordable damage spell earlier in `owned_keys()` order than the innate
  skills, and its prerequisites are satisfied
- **THEN** `default_attack_policy` returns an `ActionRequest` naming that spell, because it passes
  `can_use_skill` and affordability

#### Scenario: A companion with only an unaffordable spell still acts every round
- **WHEN** a party NPC owning only the unaffordable `firestorm` (plus the innate skills) fights
  through `combat.run_round` against a living enemy
- **THEN** every round the NPC's resolved `basic_attack` action produces an `EventLog` entry — no
  round silently discards a rejected request and no `action_skipped` entry is emitted for a castable
  entity

#### Scenario: Resolver-rejected skills are skipped, never proposed
- **WHEN** a candidate skill would be rejected by the resolver (prerequisite-unsatisfied per
  `can_use_skill`, unowned, or MP-unaffordable for the current gauge)
- **THEN** it is skipped in favor of the next candidate — in practice the innate `basic_attack`,
  which is always affordable — and never proposed in an `ActionRequest` that `ActionResolver`
  rejects

#### Scenario: A malformed spell never raises the policy
- **WHEN** `default_attack_policy` encounters a malformed spell
- **THEN** the policy does not raise

### Requirement: Authored monster kits use shared policy selection and fallback
A reflex monster SHALL use its validated behavior binding or tier default. Its usable authored damage skills SHALL precede innate basic_attack; first_owned retains owned order and highest_expected_damage samples exact output. Declared flee thresholds SHALL retain inclusive priority. Existing target/displacement/knockout gates and initiative-time revalidation SHALL remain authoritative.

#### Scenario: Selection and exhaustion
- **WHEN** a synthetic one-kit monster executes with full resources, then separately exhausted MP and SP
- **THEN** the authored action and riders execute when usable; each exhaustion selects a legal innate fallback

#### Scenario: Threshold and late changes
- **WHEN** a monster reaches its declared flee edge or targets/eligibility change before resolution
- **THEN** flee keeps inclusive priority and final resolver gates reject invalid late state without creature-specific logic
