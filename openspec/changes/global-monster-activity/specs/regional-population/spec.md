# Spec Delta

## MODIFIED Requirements

### Requirement: Population lifecycle replays loss and site boundaries chronologically
Population settlement SHALL merge presence, site, recovery and activity boundaries chronologically, applying lawful arrivals and site-before-regional births before contacts and idle departures without exposing future state to earlier decisions.

#### Scenario: Later loss starts a new episode
- **WHEN** L is3, local population2 has due110, a wave restores3 at110, and a previously recorded later loss occurs118 with delay10
- **THEN** the118 boundary creates a new due128; recording that loss while an older episode was pending cannot consume its later deficit

#### Scenario: Cancellation before later loss
- **WHEN** explicit restoration ends an older episode before a pending future loss makes local density deficient again
- **THEN** that later occurrence starts a new delayed episode, with identical outcomes under equal interval partitioning

#### Scenario: Site recovery cannot affect earlier waves
- **WHEN** a zone has a wave due110 and an overlapping site's recovery is due140 during [100,160]
- **THEN** births and due state equal settlement through [100,125] then [125,160], and the140 site members do not occupy the110 headroom

#### Scenario: Actual movement preserves both budgets
- **WHEN** living home owners depart repeatedly or wait in transit while a foreign visitor enters their zone
- **THEN** each still consumes its own home ceiling once, the visitor consumes local headroom, and movement gives no defeat/site-clear credit or unlimited replacements
