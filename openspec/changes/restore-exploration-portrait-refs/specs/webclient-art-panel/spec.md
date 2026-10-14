# Spec Delta

## MODIFIED Requirements

### Requirement: Worker completion pushes a targeted art panel update

Canonical requirement ID: `webclient-art-panel::worker-completion-pushes-a-targeted-art-panel-update`.

When an art-worker asset or gallery job settles and emits `asset_completed`,
the `world/art/` settle path SHALL emit a bounded server-side notification
carrying only the completed subject key. The presentation layer SHALL publish
all qualifying freshly rendered panels together in one affected-panel
`ui_update` at a newer revision per session per notification.

#### Scenario: A done scene reaches sessions currently showing that scene

- **WHEN** a scene subject completes while connected sessions currently render that scene and neither their selected gallery nor roster portraits references it
- **THEN** each such session receives one newer art panel update with the done URL and no gallery or roster changes, except any required mode-coherence companion panel

#### Scenario: A late completion never replaces the current panel

- **WHEN** a subject completes after the session moved to a different scene or the entity left and no current art, selected-gallery, or roster reference names that subject
- **THEN** no update is published, revision is unchanged, and the completed subject does not replace the currently rendered scene or portrait

#### Scenario: Reconnect resolves current status from the store

- **WHEN** a browser reconnects after an asset or gallery completion notification was missed
- **THEN** the full snapshot renders current art, gallery cards/pending/error state, and roster portraits from the store without replaying the missed push

#### Scenario: A settled gallery job refreshes all three referencing panels together

- **WHEN** a gallery job settles successfully for the session's selected subject and both art's catalog and an owned roster row also reference that subject
- **THEN** one newer update includes art, gallery, and roster, the gallery's pending row is replaced by its canonical stored card, and both portrait panels carry the current resolved value without a full snapshot

#### Scenario: A selected gallery refreshes without an art or roster match

- **WHEN** a settled gallery job's subject equals a session's rendered selected gallery but is absent from its current art scene/catalog and roster portraits
- **THEN** that session receives one newer update containing gallery and not art or roster, with settled card/error facts and recomputed filter counts

#### Scenario: An off-room roster sibling refreshes without an art or gallery match

- **WHEN** a completion subject appears only in an owned non-current roster character's portrait while that character is outside the current puppet's room and another gallery subject is selected
- **THEN** the session receives one newer roster update containing its current owned rows and freshly resolved sibling portrait, with no art or gallery update

#### Scenario: Unavailable art cannot suppress a selected gallery or roster match

- **WHEN** art renders its unavailable form while an available gallery or roster payload references the completed subject
- **THEN** one newer update carries the matching available panels without art

#### Scenario: A changed selection cannot be restored by late completion

- **WHEN** subject A completes after the session selected subject B and A remains on the rail but neither current art nor roster references A
- **THEN** no update is published, gallery remains selected on B, and no pending/card state for A replaces B's displayed gallery

#### Scenario: A subject leaving art can still refresh an owned roster portrait

- **WHEN** a portrait completion arrives after its character left the current scene but an owned roster row still references that subject
- **THEN** roster refreshes from current state while art is omitted if it no longer references the subject

#### Scenario: Failed gallery settlement removes the stale spinner truthfully

- **WHEN** a selected subject's gallery job settles failed and emits its completion notification
- **THEN** a newer gallery update removes that job's pending row, renders the canonical failed row and error state with recomputed counts, creates no card or default, and any qualifying art/roster values follow their existing resolver fallback behavior

#### Scenario: Per-session selections and failures stay isolated

- **WHEN** live webclient sessions have different selected subjects or one session raises while processing a completion
- **THEN** each healthy session is evaluated against only its own current context, nonmatching galleries are not published, and one session's failure neither stops other eligible sessions nor reaches the worker

#### Scenario: Ineligible sessions receive no completion push

- **WHEN** the notification is processed for a non-WebClient transport, a puppet-less session, or a session without an attached coordinator
- **THEN** that session receives no update, and notification handling does not attach a coordinator or change canonical state to make it eligible

#### Scenario: Each eligible session re-renders independently

- **WHEN** a completion notification is processed for each connected WebClient session with an active puppet and an already-attached coordinator
- **THEN** the presentation layer independently re-renders `art`, `gallery`, and `roster` from that session's current canonical state and current owned presentation selection

#### Scenario: Each available panel qualifies independently

- **WHEN** freshly rendered panels are evaluated against the completed subject key
- **THEN** art qualifies when its current scene subject or any portrait-catalog entry references that key, gallery when its rendered `selected` equals that key, and roster when any rendered character row's portrait subject key equals that key
- **AND** gallery rail membership alone does not qualify a gallery update, and roster qualification is not limited to the current puppet or characters present in its room

#### Scenario: Publication proceeds without art and omits unavailable panels

- **WHEN** art does not qualify or is unavailable while another panel qualifies
- **THEN** the update publishes anyway, unavailable panels are omitted independently without suppressing another qualifying panel, and existing mode-coherence companion panels remain permitted
- **AND** when no panel qualifies nothing is published and revision does not advance

#### Scenario: Late completions gate on fresh references only

- **WHEN** a completion notification is evaluated for staleness
- **THEN** it is gated on the freshly rendered current references — not remembered selections, rooms, sent payloads, or completed image identities — a completion for an old room, vanished entity, or no-longer-selected gallery does not replace that panel's current content or restore an old selection, and a different panel still referencing the same subject remains eligible

#### Scenario: Completion rendering is pure presentation

- **WHEN** completion rendering runs
- **THEN** it mutates no canonical state, selects no card, and sets no default, while room or present-entity-set changes continue to replace the art payload through ordinary presentation updates

#### Scenario: Delivery stays reactor-side and leak-free

- **WHEN** the completion notification is delivered
- **THEN** it remains on the existing reactor-side notification path, not the worker thread, exposes no output paths, prompts, or worker internals, and the `world/art/` package remains free of any `web/` import

#### Scenario: A missed notification is repaired, not replayed

- **WHEN** a completion notification is missed by a session
- **THEN** reconnect's current-store full snapshot repairs the view without replaying the missed push

#### Scenario: A current exploration portrait completion refreshes nullable descriptors
- **WHEN** the completed subject appears in the freshly rendered current portrait catalog, the session is exploring, and its available exploration descriptors previously had null refs because that portrait lacked real imagery
- **THEN** one newer update includes qualifying art/gallery/roster panels and the freshly rendered exploration panel, whose admitted target/entity refs now name the real catalog image, without another gameplay or focus action

#### Scenario: Scene completion does not refresh unrelated exploration descriptors
- **WHEN** only the current scene references the completed subject and no current portrait-catalog value names it
- **THEN** the completion adds no exploration panel solely for that scene, preserving targeted publication

#### Scenario: A portrait completion outside exploration keeps existing publication
- **WHEN** the session is outside exploration or its exploration panel is unavailable
- **THEN** qualifying art/gallery/roster publication continues without a fabricated exploration panel

#### Scenario: Late portrait completion cannot revive a departed target
- **WHEN** the entity left or the session changed room before a portrait completion and no current art/gallery/roster reference qualifies
- **THEN** no stale exploration descriptor is published and no revision is advanced for that completion
