## MODIFIED Requirements

### Requirement: The gallery has an offline interactive storyboard
The gallery component Storybook families SHALL include an interactive storyboard
under Data/GalleryPanel covering browse, generation, pending and failure, binding, face editing,
stage transform editing/reset/save/rejection, default selection and delete confirmation.
A frame guide SHALL reference the four existing design images, state each transition and
recovery path and distinguish fixture publications from live behavior. The stage editor SHALL
reuse existing local assets without requiring a new reference image.

#### Scenario: The storyboard runs without game or AI services
- **WHEN** the player opens the built Storybook gallery storyboard offline
- **THEN** the real components expose every documented frame with deterministic fixtures and no game-server or AI-service requests

#### Scenario: Context changes invalidate an editor
- **WHEN** the selected subject changes, its card disappears or the panel becomes unavailable
- **THEN** stale drafts are discarded and cannot dispatch against the replacement context

#### Scenario: An unrelated pending job does not complete a submission
- **WHEN** another pending row is published before this editor's correlated result
- **THEN** the editor remains open and a rejected result preserves its draft

## ADDED Requirements

### Requirement: Stage transforms affect full figures and never avatar cover crops
Stage and drawer full-figure portraits SHALL render contain/bottom-aligned with bottom-center origin, applying frame-relative translation followed by scale in the declared transform list. Missing/null stage SHALL render identity. Positive y SHALL move down; offsets SHALL remain independent of scale. The ground anchor SHALL stay fixed, the figure shadow SHALL follow the figure and existing overflow-visible behavior SHALL remain. Stage edits SHALL be immediate and SHALL NOT change the portrait source key or trigger crossfade. Gallery/detail cards, roster avatars and party-strip cover crops SHALL remain face-rect driven. Existing inline stage placeholders SHALL remain unchanged.

#### Scenario: A child stays on the same ground line
- **WHEN** stage scale changes from 1.0 to 0.6 with x and y zero
- **THEN** the full figure scales around 50% 100%, its feet anchor and ground ellipse remain fixed, and no new source crossfade occurs

#### Scenario: Translation uses frame dimensions at every scale
- **WHEN** x is 0.1 and y is -0.2 at scales 0.6 and 2.0 in the same frame
- **THEN** both render offsets of 10% frame width and -20% frame height; custom properties carry the exact triple and enlarged figures are not newly clipped

#### Scenario: Null stage and cover crop remain unchanged
- **WHEN** stage is missing/null or a nonidentity triple is supplied to a cover-mode avatar
- **THEN** stage mode normalizes missing/null to identity and cover mode uses the same faceObjectPosition with no stage transform

### Requirement: The stage editor previews a local triple against a static adult reference
The selected completed card SHALL expose 比例調整 opening a dedicated accessible modal with a fixed 3:4 preview and paired range/number controls 比例 [0.2, 2.0], 水平/垂直 [-0.5, 0.5], all step 0.01. Controls SHALL synchronize and clamp locally; drag SHALL map captured pointer deltas to preview-frame fractions, preserving scale and clamping offsets. 重設 SHALL locally restore identity. The current card SHALL use the same contain/bottom transform as live stage. Its adult reference SHALL be a static, noninteractive, aria-hidden CSS mask of existing /art/defaults/man.webp, fill #17191f, contain/bottom-centered with no stroke/text/ground ellipse, identity scale and left translation of half its own displayed width. Both feet lines SHALL coincide. Preview edits/reset SHALL send no request and create no image.

#### Scenario: Slider and number edits synchronize
- **WHEN** scale range changes to 0.6 and horizontal number changes to 0.1
- **THEN** both control pairs and the local preview agree, with no network action

#### Scenario: Drag uses frame fractions and clamps
- **WHEN** the captured pointer moves 30px right and 40px up in a 300px by 400px frame
- **THEN** x increases 0.1, y decreases 0.1, scale is unchanged and repeated movement cannot exceed either offset bound

#### Scenario: Reset does not save
- **WHEN** 重設 is activated on a nonidentity draft
- **THEN** local values become `{scale: 1.0, x: 0.0, y: 0.0}` and no action is dispatched

#### Scenario: Adult comparison stays static
- **WHEN** scale and offsets of the current card change in a 3:4 preview containing the 9:16 reference
- **THEN** the reference remains bottom-aligned at scale 1.0, approximately 75% of frame width and translated left by half that displayed width, with no editable transform dependency

### Requirement: Stage saves reuse correlated lifecycle and accessible gallery chrome
Save SHALL be disabled until the current image loads and while mutation admission is disabled/pending. Image failure SHALL leave the adult reference and truthful error text, with save disabled. 儲存調整 SHALL submit exactly one stage triple through gallery.stage.update using the committed subject/card identity. Only its own successful result and committed presentation revision SHALL close the editor; rejection SHALL retain the draft and offer the log link. Context invalidation SHALL discard stale drafts. Dialog semantics, shared focus trap, visible gold focus, Escape/cancel/scrim close and opener restore SHALL match gallery editors. Numeric keyboard controls SHALL cover drag functionality. Ink/gold/serif chrome and scaled geometry SHALL follow existing tokens; motion preferences SHALL be respected without interpolating figure transforms or using red for normal selection.

#### Scenario: Save waits for image load
- **WHEN** the image has not loaded or its load fails
- **THEN** save cannot submit and truthful loading/failure feedback is present; failure renders only the reference in the preview

#### Scenario: Save closes only on its correlated revision
- **WHEN** save emits one triple and an unrelated update or successful result arrives without its declared revision
- **THEN** the editor remains open and locked until its own success and revision both commit

#### Scenario: Rejection preserves editable intent
- **WHEN** the submitted action is rejected
- **THEN** the same local triple remains visible with textual rejection feedback and 查看伺服器訊息, and the player can edit again once unlocked

#### Scenario: Keyboard and cancel restore focus without writes
- **WHEN** the player tabs through the dialog, edits numbers and presses Escape or 取消
- **THEN** focus stays trapped until close, then returns to 比例調整 and no save is dispatched

#### Scenario: Non-card and stale contexts cannot save
- **WHEN** a row is pending/failed, or the selected subject changes, the card disappears or the panel becomes unavailable
- **THEN** no stage mutation can target that context and any stale editor draft is discarded

### Requirement: Stage transform stories document visual and state behavior offline
The offline showcase SHALL include the new modal family registered in the frozen component manifest, stage-transform states in Core/ReferenceArtwork and a gallery storyboard editing/save/rejection journey. Stories SHALL use deterministic existing local assets, preserve the ink/gold/serif diorama and instrument styling, and distinguish fixture publication from live behavior. Identity, child scale, offset/boundary, loading, failed-load, pending/disabled, rejection, keyboard focus and reduced-motion states SHALL be represented without game or AI services.

#### Scenario: Showcase covers the complete editor offline
- **WHEN** Storybook is built and showcase coverage runs with no game or AI server
- **THEN** the registered modal and stage artwork stories exist, the documented states are reachable and the new required family passes manifest coverage without removing existing requirements
