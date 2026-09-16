## MODIFIED Requirements

### Requirement: Conditional damage policies compose without double matching
A damage effect SHALL support a validated target-fact predicate, conditional attack multiplier, conditional defense bypass and maximum-HP fraction. Multiple matching facts within one ANY predicate SHALL activate a policy once. Defaults SHALL preserve ordinary damage. Other elements SHALL be able to use the same policy behavior. Additionally, the predicate vocabulary SHALL accept a validated dynamic-fact entry of the form `buff:<definition-key>`, naming a loaded buff definition whose live, unexpired instance on the target IS the matching fact at settlement time; the entry SHALL be rejected at policy construction when the key names no loaded definition, and every other namespaced entry form SHALL keep failing exactly as before. A `buff:` entry SHALL match only through the target's current buff state — never through static affinity or classification data — and SHALL compose with bare static facts, the conditional multiplier, the conditional bypass and the maximum-HP fraction under the identical any-match-once-per-strike semantics, at any point in the action's life (a marker applied, expired or removed between authoring and settlement flips the fact with the instance). A policy MAY additionally declare the independent boolean `unconditional_defense_bypass` (default False), which ignores defense subtraction for EVERY target regardless of predicate match. Construction SHALL reject `unconditional_defense_bypass=True` co-declared with a non-empty `bypass_defense=True` (one meaning, one field) and accept it with an empty predicate (reducing to the shipped unconditional-execution behavior) or with any predicate set; the shipped conditional `bypass_defense` semantics stay unchanged, and every existing policy (empty or non-empty predicate, with or without conditional bypass) behaves bit-identically.

#### Scenario: Two facts match once
- **WHEN** a target matches both configured alternative classifications
- **THEN** the declared conditional multiplier applies once, not once per fact

#### Scenario: Bypass and bonus are independent
- **WHEN** a configured defense-bypass predicate matches without an attack bonus declaration
- **THEN** defense is ignored and no undeclared bonus appears

#### Scenario: Percent rider requires a hit
- **WHEN** a configured percent-HP damage effect misses
- **THEN** it deals zero damage including its percentage component

#### Scenario: A marker-fact entry matches while the live instance lasts
- **WHEN** a synthetic spell declares a `buff:` predicate entry with a conditional multiplier and strikes the same target before application, while a live synthetic buff instance of the named key is applied, and after that instance expires
- **THEN** only the during-instance strike receives the declared multiplier once, the other strikes deal ordinary policy-free damage, and no other policy component changes

#### Scenario: A marker entry composes any-match-once with static facts
- **WHEN** one ANY predicate declares both a static classification fact and a `buff:` fact, and the target satisfies both
- **THEN** the conditional multiplier applies once, not once per matching entry

#### Scenario: Only the buff namespace enters; unknown keys fail closed
- **WHEN** a policy declares `buff:<unknown-key>`, `terrain:cracked`, `hp_loss` or any other non-buff namespaced or unknown entry
- **THEN** construction raises naming the offending entry, and bare vocabulary entries keep their existing accepted/rejected set unchanged

#### Scenario: Unconditional bypass rides independently of the dynamic fact
- **WHEN** a synthetic policy declares a `buff:` predicate entry with a conditional multiplier plus `unconditional_defense_bypass`, and strikes the same high-defense target while standing-on-the-marker and while not standing on it
- **THEN** both strikes ignore defense subtraction while only the marker-standing strike receives the declared multiplier, a predicate-bearing `bypass_defense=True` policy keeps bypassing only on a static-predicate match, an empty-predicate `bypass_defense=True` policy keeps bypassing unconditionally, and a policy declaring both bypass fields True is rejected at construction
