## MODIFIED Requirements

### Requirement: The scene payload resolves only validated archetypes with truthful placeholders
The art panel scene SHALL resolve through `world.art.presenter.resolve_scene` from the current room's
validated `scene_archetype` and SHALL contain the subject key, asset status, same-origin media URL,
aspect ratio, and alternative text for a `done` record, or a truthful placeholder kind and
explanatory label otherwise. The scene SHALL render as the client's full-bleed stage backdrop with
cover-style cropping, and SHALL display its label and alternative text as text outside the bitmap.
When the current scene is pending and a prior scene is already rendered, the client SHALL retain that
prior image visibly dimmed and labelled `目前場景圖片生成中`; without a prior image, and for failed or
invalid assets, it SHALL render the current mode's gradient stage together with the scene placeholder
label. The panel SHALL NOT silently present old art as current, SHALL NOT expose `out_path` or the
store root, and SHALL derive its URL only from a validated stored identity.

#### Scenario: Done scene serves the same-origin media URL
- **WHEN** a room's scene archetype has a `done` asset record with an existing validated output
- **THEN** the scene payload carries the asset status, the same-origin `/art/...` URL, 16:9 aspect,
  and meaningful alternative text, and never an absolute filesystem path

#### Scenario: Pending scene retains a labelled prior image
- **WHEN** the current scene is pending and a prior scene image is already rendered
- **THEN** the backdrop keeps that prior image dimmed with the explicit `目前場景圖片生成中` label and the
  pending status rather than presenting it as current art

#### Scenario: Failed, missing, or invalid scene uses the gradient stage and placeholder label
- **WHEN** the scene asset is failed, missing, scheduler-disabled, or its output file is absent
- **THEN** the backdrop renders the current mode's gradient stage with the truthful placeholder label as
  text and no URL, and no stale image is substituted

### Requirement: Art degradation never blocks gameplay or leaks rejected content
With the worker command fixed to fail and every LLM profile unavailable, movement, dialogue, combat,
quests, and services SHALL proceed through their deterministic paths while every art state degrades
to the approved placeholders. The scheduler disabled, worker unavailable or timed out, missing file
for a done record, invalid output identity, OOB disconnect during completion, and browser image load
failure SHALL each degrade presentation only and log bounded diagnostics. A browser image load
failure SHALL show fallback text/placeholder and SHALL NOT repeatedly fetch without a new URL or
user reload. OOB errors SHALL contain no traceback, local path, unescaped player content, or rejected
prompt content. A missing/pending/failed scene SHALL degrade to a single truthful placeholder label
on the stage backdrop, identified by a stable `data-testid` hook, with the mode gradient as the
rendered stage. Because a snapshot refresh or a Vue re-render can open a transient double-node window
under a loaded runner, the browser acceptance test SHALL gate its placeholder-count assertion on the
shared bounded wait helper (the committed art-panel store state plus a DOM-readiness descriptor,
within one bounded deadline) rather than a single raw `.count()` sample, so the assertion observes the
single visible placeholder node deterministically.

#### Scenario: Offline art never blocks play
- **WHEN** the worker command is fixed to fail and the scheduler is disabled
- **THEN** the player can move, talk, fight, trade, and turn in quests while the stage shows only the
  gradient and its placeholder label, and no gameplay action waits on a job

#### Scenario: Image load failure degrades to fallback
- **WHEN** a rendered scene URL fails to load in the browser
- **THEN** the backdrop shows its fallback gradient and placeholder label and does not repeatedly refetch the same URL

#### Scenario: Rejected content stays out of every error surface
- **WHEN** an art or presentation error occurs
- **THEN** no OOB message or panel payload contains a traceback, filesystem path, rejected prompt, or
  underage subject data

#### Scenario: The missing-scene placeholder gate observes a single node
- **WHEN** the art panel is available with a missing scene and a snapshot refresh or Vue re-render
  opens a transient double-node window under a loaded runner
- **THEN** the acceptance test's bounded gate keeps polling the scene backdrop's placeholder
  `data-testid` hook until it observes exactly one visible placeholder node, so the assertion is
  deterministic rather than a single raw `.count()` sample

### Requirement: Art panel browser acceptance is keyboard-first, accessible, and desktop-bounded
The scene full view SHALL open by click on the backdrop's scene control or Enter on that focused
control and SHALL close on Escape; the portrait SHALL have its own accessible full-view control. The
scene label and alternative text SHALL remain visible as text outside the bitmap, alternative text
SHALL be meaningful, and no required information SHALL exist only inside an image. Server-authored
labels SHALL be inserted as text, not trusted HTML, and reduced-motion preference SHALL disable
nonessential transitions. The stage backdrop and the 3:4 portrait SHALL remain usable at both
1440x900 and 1280x720 without the backdrop covering the scene label, the HUD islands, or required
status.

#### Scenario: Keyboard-only full view opens and closes
- **WHEN** the player focuses the scene control and presses Enter, then Escape
- **THEN** the full view opens on Enter and closes on Escape with focus restored

#### Scenario: Both supported viewports keep art usable
- **WHEN** the stage renders at 1440x900 and at 1280x720
- **THEN** the backdrop, the scene label and alternative text, the portrait presentation, and the status text remain visible and non-overlapping

#### Scenario: Player-authored text is not executed as markup
- **WHEN** a display name or label contains HTML-like player text
- **THEN** the browser renders it as literal text and creates no element or script from it
