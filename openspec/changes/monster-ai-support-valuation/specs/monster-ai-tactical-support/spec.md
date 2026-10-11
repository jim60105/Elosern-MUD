## Purpose

Choose useful existing healing and calculable control through the shared utility selector. This capability defines observable behavior at the monster decision boundary.

## ADDED Requirements

### Requirement: Support uses existing legal audience plans
Owned active healing, supported buffs and hostile control SHALL enter the same candidate pipeline and legality gates. Estimates SHALL follow the submitted effect audience plan, including implicit SELF/NONE binding. Full-HP heals SHALL remain legal when settlement allows them with zero recovery benefit and real cost/waste.

#### Scenario: Submitted mixed recipients
- **WHEN** broad preview includes an ally omitted from the submitted plan and a self-bound effect
- **THEN** the omitted ally contributes no healing; the actor self effect remains; ally harm and enemy healing reduce score

#### Scenario: Unsupported benefit and harm
- **WHEN** a support plan has unknown harmless benefit or unsupported harmful consequences
- **THEN** unknown benefit is zero with diagnostics; harmful or unrepresentable plans are excluded without changing player or legacy resolution

### Requirement: Healing projects payment and actual prerequisites
Healing SHALL use shared magnitude, potency, proficiency, scale and conditional rules, capped by projected missing HP. Resource payment SHALL precede effect projection. Hit-dependent healing and drain recovery SHALL use modeled prerequisites and actual projected loss.

#### Scenario: HP cost before self heal
- **WHEN** a full-HP actor pays HP and then self-heals
- **THEN** benefit reflects missing HP after payment rather than ignoring payment

#### Scenario: Conditional combined effect
- **WHEN** ordered damage, drain and healing can miss or exceed remaining capacity
- **THEN** later effects use projected HP; impossible or unmodeled positive branches receive no fabricated recovery

### Requirement: Control value is concrete marginal opportunity value
Supported control and buff estimates SHALL use existing modifier definitions over one next action opportunity per eligible participant. Expired, redundant non-stacking, stronger existing, capped effects and beneficiaries without opportunity before expiry SHALL have zero marginal benefit.

#### Scenario: Action denial
- **WHEN** a concrete supported modifier reduces available legal opportunities
- **THEN** denial equals opportunity reduction divided by baseline opportunities; other modifiers use bounded offensive or prevented health impact normalized by faction HP

#### Scenario: Redundant control
- **WHEN** the same buff is reapplied, has expired, or cannot affect an action before expiry
- **THEN** it receives zero marginal value; unsupported positive reactions are omitted and limitations recorded

#### Scenario: Real support behavior
- **WHEN** a synthetic real healing and separately control effect offer independently known useful outcomes
- **THEN** the monster chooses and resolves useful support/control; committed reload shows the recipient change and untouched bystanders

### Requirement: Completed tactical score retains baseline healing
The score SHALL add w_heal*useful_healing as a baseline and i*w_control*marginal_control to attack utility. Focus SHALL enter through the observation change. Invalid numeric features SHALL use the existing typed error boundary.

#### Scenario: Simple survival
- **WHEN** low and high intelligence variants have a legal useful heal with identical resources
- **THEN** both may value immediate healing; control, finishing, cost and waste scale continuously without granting new capabilities

