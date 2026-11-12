# Spec Delta

Archive handoff: after syncing this delta, re-list canonical IDs and annotate every new or changed substantive requirement test. Existing requirement headings are intentionally unchanged; historical titles do not preserve superseded mode or dice behavior.

## MODIFIED Requirements

### Requirement: Threat remains an observed soft preference
Threat SHALL use observed incoming damage and successful opposing healing/control impact, normalized by current faction capacity and decayed with event age. Only profiles valuing threat SHALL use it in preference. Unknown or unobserved events SHALL contribute zero and mandatory legality/target restrictions SHALL remain authoritative.

#### Scenario: Seal overrides focus
- **WHEN** the strongest observed focus/threat favors an opponent outside applicable seal restrictions
- **THEN** the conflicting target is excluded regardless of utility score

#### Scenario: Current eligibility
- **WHEN** historical recipients die, escape, disappear or change faction
- **THEN** their old identifiers confer no permission to target them

#### Scenario: Existing strategy determines threat participation
- **WHEN** identical settled observations are added for deliberation profiles using highest_effective_power and lowest_hp
- **THEN** the former averages its static-power and observed-threat target ranks, while the latter remains unchanged by threat; empty positive history retains the static rank and reflex metric ordering remains unchanged

### Requirement: Completed coordination is reproducible and intelligence scaled
Completed deliberation SHALL add i*w_focus*observed_focus to damage, baseline healing, preference and intelligence-scaled finishing/control/cost/waste. Same-process replay SHALL require identical initial observations, state, scope and tuning. Traces SHALL record the initial observation snapshot.

#### Scenario: Replay and restart
- **WHEN** a recorded observation snapshot is replayed, then the real server restarts
- **THEN** same-process replay repeats the choice; restarted gameplay begins empty and session ID alone does not claim replay

#### Scenario: Real teamwork
- **WHEN** two synthetic pack-hunter monsters act through the production round and another profile values support or a single-target opening
- **THEN** coordination begins only after resolution and profile distinctions remain without new mechanics
