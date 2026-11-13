# Spec Delta

## MODIFIED Requirements

### Requirement: Dream presentation changes no live character effects

The dream track SHALL NOT write a live SexualState handler, persistent traits/pleasure/sensitivity, virginity/experience, lifetime counters, climax_today, relationship state, buffs, skills or codex. Existing committed sleep SHALL be the sole restoration. At reached climax the deterministic ending SHALL report the canonical post-climax phase as the ending phase, before fading/awakening with no additional model call, and its ending text SHALL be the fixed farewell line selected for that phase.

#### Scenario: Completed climax has no live side effects
- **WHEN** a session reaches climax then ends
- **THEN** all live character effects equal the post-sleep baseline and only private authoring/session data changed

#### Scenario: Offline ending at climax
- **WHEN** generation fails after the server track reached climax
- **THEN** the ending reports the canonical post-climax phase and permits awakening without a model
