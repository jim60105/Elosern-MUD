## MODIFIED Requirements

### Requirement: Utility attack score reflects continuous intelligence
Attack utility SHALL equal w_damage*damage + w_heal*healing + w_preference*preference + i*(w_kill*finishing + w_control*control - w_cost*cost - w_waste*waste), with i=intelligence/100. ``damage``, ``healing`` and ``control`` SHALL be the estimator's bounded signed features, and recovery SHALL enter unscaled as a baseline while control SHALL enter the intelligence-scaled term. Preference SHALL combine configured target, owned-skill and area bias as bounded stable ranks with shared ranks for ties.

#### Scenario: Intelligence does not grant power
- **WHEN** identical registered variants differ only in intelligence
- **THEN** stats, proficiency, ownership and legal actions remain identical; tactical terms scale continuously and win rates need not increase

#### Scenario: Six preferences
- **WHEN** all six archetypes evaluate the same synthetic options
- **THEN** instinctive simple attacks, pack_hunter weak prey/focus, brute strong-enemy pressure, tactical_caster spell efficiency, apex_predator finishing/coverage and ambush_predator single-target opening remain distinct soft preferences

#### Scenario: Baseline recovery
- **WHEN** a low-intelligence and a high-intelligence variant hold the same legal useful heal and the same resources
- **THEN** both value the immediate recovery by the same unscaled term, while control, finishing, cost and waste scale continuously with intelligence
