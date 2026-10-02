## MODIFIED Requirements

### Requirement: Worker completion pushes a targeted art panel update

Canonical requirement ID: `webclient-art-panel::worker-completion-pushes-a-targeted-art-panel-update`.

When an art-worker asset or gallery job settles and emits `asset_completed`,
the `world/art/` settle path SHALL emit a bounded server-side notification
carrying only the completed subject key. For each connected WebClient session
with an active puppet and an already-attached coordinator, the presentation
layer SHALL independently re-render `art`, `gallery`, and `roster` from that
session's current canonical state and current owned presentation selection.
Each available panel SHALL qualify independently: art when its current scene
subject or any portrait-catalog entry references the completed subject key;
gallery when its rendered `selected` equals that key; roster when any rendered
character row's portrait subject key equals that key. Gallery rail membership
alone SHALL NOT qualify a gallery update, and roster qualification SHALL NOT be
limited to the current puppet or characters present in its room.

The presentation layer SHALL publish all qualifying freshly rendered panels
together in one affected-panel `ui_update` at a newer revision per session per
notification, even when art does not qualify or is unavailable. Unavailable
panels SHALL be omitted independently without suppressing another qualifying
panel. When no panel qualifies it SHALL publish nothing and SHALL NOT advance
revision. Existing mode-coherence companion panels SHALL remain permitted.
A non-WebClient session, a session with no active puppet, or a session with no
attached coordinator SHALL receive no completion push.

Late completions SHALL be gated on the freshly rendered current references,
not remembered selections, rooms, sent payloads, or completed image identities.
A completion for an old room, vanished entity, or no-longer-selected gallery
SHALL NOT replace that panel's current content or restore an old selection;
a different panel still referencing the same subject SHALL remain eligible.
Room or present-entity-set changes SHALL continue to replace the art payload
through ordinary presentation updates. Completion rendering SHALL NOT mutate
canonical state, select a card, or set a default. Failed gallery settlement
notifications SHALL refresh truthful pending/error rows under the same rules
without fabricating a portrait or card. Each session SHALL remain isolated so
its rendering/publication failure cannot stop the other sessions or propagate
back into the worker. Delivery SHALL remain on the existing reactor-side
notification path, not the worker thread.

The notification SHALL NOT expose output paths, prompts, or worker internals,
and the `world/art/` package SHALL remain free of any `web/` import. A missed
notification SHALL be repaired by reconnect's current-store full snapshot,
without replaying the missed push.

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
