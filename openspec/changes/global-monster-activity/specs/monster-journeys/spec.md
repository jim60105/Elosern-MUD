# Spec Delta

## ADDED Requirements

### Requirement: Activity ordering protects encounters across deferred time
Activity settlement SHALL process all due facts chronologically in stable identity order, apply lawful arrivals and births before contacts and idle departures, and honor encounter protection at actual occurrence times.

#### Scenario: Same tick contact precedence
- **WHEN** lawful arrivals, births and an idle departure become due together
- **THEN** arrival and existing site-before-regional births complete before contact evaluation, which precedes idle departures

#### Scenario: Historical protection
- **WHEN** terminal clock catch-up passes an earlier active battle after the session closes
- **THEN** participants never wander and outside groups neither depart into nor arrive inside the protected cell; a lawful escaped member can leave from its real departure tick

#### Scenario: Newly due facts
- **WHEN** an earlier arrival schedules a decision within the same long advance
- **THEN** that decision is processed at its own tick and equal elapsed partitions preserve positions, sequence, counts and physiology

