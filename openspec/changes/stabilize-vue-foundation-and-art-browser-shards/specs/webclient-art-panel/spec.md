## MODIFIED Requirements

### Requirement: Art degradation never blocks gameplay or leaks rejected content
With the worker command fixed to fail and every LLM profile unavailable, movement, dialogue, combat,
quests, and services SHALL proceed through their deterministic paths while every art state degrades
to the approved placeholders. The scheduler disabled, worker unavailable or timed out, missing file
for a done record, invalid output identity, OOB disconnect during completion, and browser image load
failure SHALL each degrade presentation only and log bounded diagnostics. A browser image load
failure SHALL show fallback text/placeholder and SHALL NOT repeatedly fetch without a new URL or
user reload. OOB errors SHALL contain no traceback, local path, unescaped player content, or rejected
prompt content. A missing/pending/failed scene SHALL degrade to a single
`.art-panel__scene-placeholder` node inside the `.art-panel__scene-frame`. Because a snapshot
refresh or a Vue re-render can open a transient double-node window under a loaded runner, the browser
acceptance test SHALL gate its placeholder-count assertion on the shared bounded wait helper (the
committed art-panel store state plus a DOM-readiness descriptor, within one bounded deadline) rather
than a single raw `.count()` sample, so the assertion observes the single visible placeholder node
deterministically.

#### Scenario: Offline art never blocks play
- **WHEN** the worker command is fixed to fail and the scheduler is disabled
- **THEN** the player can move, talk, fight, trade, and turn in quests while the art panel shows only
  placeholders and no gameplay action waits on a job

#### Scenario: Image load failure degrades to fallback
- **WHEN** a rendered scene URL fails to load in the browser
- **THEN** the panel shows its fallback text/placeholder and does not repeatedly refetch the same URL

#### Scenario: Rejected content stays out of every error surface
- **WHEN** an art or presentation error occurs
- **THEN** no OOB message or panel payload contains a traceback, filesystem path, rejected prompt, or
  underage subject data

#### Scenario: The missing-scene placeholder gate observes a single node
- **WHEN** the art panel is available with a missing scene and a snapshot refresh or Vue re-render
  opens a transient double-node window under a loaded runner
- **THEN** the acceptance test's bounded gate keeps polling the scoped selector
  `.art-panel__scene-frame .art-panel__scene-placeholder` until it observes exactly one visible
  placeholder node, so the assertion is deterministic rather than a single raw `.count()` sample
