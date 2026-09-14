## ADDED Requirements

### Requirement: Conditional damage policies compose without double matching
A damage effect SHALL support a validated target-fact predicate, conditional attack multiplier, conditional defense bypass and maximum-HP fraction. Multiple matching facts within one ANY predicate SHALL activate a policy once. Defaults SHALL preserve ordinary damage. Other elements SHALL be able to use the same policy behavior.

#### Scenario: Two facts match once
- **WHEN** a target matches both configured alternative classifications
- **THEN** the declared conditional multiplier applies once, not once per fact

#### Scenario: Bypass and bonus are independent
- **WHEN** a configured defense-bypass predicate matches without an attack bonus declaration
- **THEN** defense is ignored and no undeclared bonus appears

#### Scenario: Percent rider requires a hit
- **WHEN** a configured percent-HP damage effect misses
- **THEN** it deals zero damage including its percentage component
