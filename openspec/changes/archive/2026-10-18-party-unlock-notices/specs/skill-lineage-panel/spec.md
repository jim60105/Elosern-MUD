# Spec Delta

## MODIFIED Requirements

### Requirement: A newly usable skill pushes one derived unlock notification
When a per-use or booked-study practice grant makes `can_use_skill` flip from false to true for any
skill whose prerequisite edges consume the granted skill (reverse-edge map), the system
SHALL stage exactly one Traditional-Chinese unlock line through the existing post-commit
notification channel to the commander: the existing line (e.g. 「新法術可用：火焰風暴」) when the
learner is the commander, and 「{成員} 學會了 {技能}」 when the learner is a companion.

#### Scenario: Meeting an edge announces the child node
- **WHEN** practice on `scorching_wave` reaches level 3 for an entity owning `firestorm`
- **THEN** exactly one unlock toast naming 火焰風暴 is pushed, and a second grant at the same level pushes none

#### Scenario: Auto-seed notifies nobody
- **WHEN** an import auto-seed satisfies deep prerequisite edges
- **THEN** no unlock toast is produced

#### Scenario: The channel is the title-grant toast channel
- **WHEN** an unlock line is staged
- **THEN** it rides the same one title-grant toasts ride: `ActionResult.notifications`, delivered by the owning settlement boundary to every client type as a text line

#### Scenario: Unlock state is derived, never persisted
- **WHEN** unlock state is computed
- **THEN** it SHALL be recomputed from proficiency, never persisted

#### Scenario: Staging waits for commit
- **WHEN** a grant's transaction has not yet committed
- **THEN** the unlock line SHALL be staged only after the transaction that applied the grant commits

#### Scenario: Scene-build auto-seed notifies nobody
- **WHEN** a scene-build auto-seed grants practices
- **THEN** the unlock line SHALL NOT fire

#### Scenario: A companion unlock names the companion
- **WHEN** companion 艾拉's practice on 治癒之光 makes 群體治癒 usable during a field cast
- **THEN** the commander receives exactly one line 「艾拉 學會了 群體治癒」 after the cast commits

#### Scenario: Booked study announces unlocks
- **WHEN** a rest settles 艾拉's booking and the study grant makes 群體治癒 usable
- **THEN** the rest summary delivered to the commander includes 「艾拉 學會了 群體治癒」 once, after the advance commits
