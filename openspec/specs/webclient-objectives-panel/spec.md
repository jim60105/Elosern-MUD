# webclient-objectives-panel Specification

## Purpose
The tracked-objectives read model — shape, describe-seam reuse, host independence, availability forms, push timing on quest/tracking seams, and read-only isolation.

## Requirements
### Requirement: The objectives panel discloses the tracked active quests host-independently
The presentation registry SHALL register an `objectives` panel at schema version 1. Its available
form SHALL contain exactly `schema_version`, `available`, and `rows`, where `rows` is an ordered
list — in quest-log order — of at most three entries, one per the holder's quest records with
`tracked` true and state `in_progress`. Each row SHALL contain exactly `quest_id`,
`display_name`, `objective_line`, `stage_index`, `stage_total`, `stage_progress`,
`objective_quantity`, `reward_copper`, and `deadline_line`: `quest_id` and `display_name` SHALL
equal the record's and its definition's values bounded by the shared identifier and display-name
bounds; `objective_line` SHALL be the deterministic single-line objective prose rendered by the
quest describe seam for the record's current stage; `stage_index` and `stage_total` SHALL be
integers giving the current stage's zero-based index and the definition's stage count;
`stage_progress` and `objective_quantity` SHALL be the record's progress and the current
objective's quantity; `reward_copper` SHALL be the offer's integer copper reward, or `null` when
no live offer exists; and `deadline_line` SHALL be the deterministic remaining-deadline prose or
`null`. The panel SHALL be available for any puppeted explorer holding quests regardless of
whether any local service host is present. An empty tracked set SHALL be an available form with
`rows` exactly `[]`, and the registered common unavailable form SHALL keep the shared field set,
reason, and semantics. The presenter SHALL be read-only — it SHALL NOT accept, abandon, fulfil,
fail, advance, or re-track any quest — and a corrupt quest log SHALL degrade the panel to the
shared unavailable form rather than emit a partial list.

#### Scenario: Tracked quests serialize with describe-seam prose
- **WHEN** a holder with one tracked in-progress quest at stage index 1, progress 2 of quantity 5,
  an 80-copper offer, and a deadline receives a full snapshot
- **THEN** `objectives.rows` carries one row with the definition display name, the
  `describe_objective` line, `stage_index` 1, `stage_total` 2, `stage_progress` 2,
  `objective_quantity` 5, `reward_copper` 80, and the deadline line

#### Scenario: The tracker works outside the guild hall
- **WHEN** a holder with a tracked quest stands in a room with no `GuildStaff` host and receives a
  full snapshot
- **THEN** `objectives` is available with the tracked row while `services.guild` may be null

#### Scenario: Untracked and terminal records are absent
- **WHEN** a holder's log carries untracked active records beside tracked ones, plus completed or
  failed records
- **THEN** only `tracked` `in_progress` records appear in `rows`, in quest-log order

#### Scenario: No tracked quests is an available empty list
- **WHEN** a puppeted explorer with no tracked quests receives a full snapshot
- **THEN** `objectives` is available with `rows` exactly `[]`

#### Scenario: A corrupt quest log degrades to the unavailable form
- **WHEN** the holder's quest log fails runtime validation
- **THEN** `objectives` uses the shared unavailable form and no partial row list is emitted

#### Scenario: Validation rejects row-shape drift
- **WHEN** a candidate objectives payload carries a fourth row, an unknown or missing row key, a
  negative progress, a non-integer `reward_copper`, or an over-bound line
- **THEN** the server validator rejects it and the client mirror rejects it identically

### Requirement: Objectives presentation stays current across quest and tracking seams
The coordinator SHALL push the `objectives` panel — together with the `services` panel it pairs
with — after the quest write seams (accept, abandon, fulfil, fail, and stage-progress
transitions) and after the tracking operation, so a committed `rows` list never shows a retired
quest, a superseded stage progress, or a tracking state the record no longer carries. The
client-side panel allowlists (UMD protocol mirror and Vue store mirror) SHALL name `objectives`
in lockstep with the server registry under the three-list agreement contract.

#### Scenario: Tracking a quest re-pushes the tracker rows
- **WHEN** the holder tracks a quest while connected
- **THEN** the coordinator pushes an update whose `objectives.rows` includes that quest and whose
  `services` payload reports the row's `tracked` true

#### Scenario: Progress transitions refresh the row
- **WHEN** a deterministic progress transition advances a tracked quest's current stage
- **THEN** the next committed payload carries the row's new `stage_progress`

#### Scenario: Fulfilment removes the row
- **WHEN** a tracked quest is fulfilled or abandoned
- **THEN** the next committed payload omits that `quest_id`
