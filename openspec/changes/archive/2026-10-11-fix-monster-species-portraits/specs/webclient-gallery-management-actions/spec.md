# Spec Delta

## MODIFIED Requirements

### Requirement: Generation routes one request through the service seam

`gallery.generate` SHALL accept exactly `subject_key`, `fields` (a possibly
empty list of distinct ids from the closed catalog `appearance`,
`weapon_main`, `weapon_off`, `armor`, `accessories`), and `custom_prompt` (bounds pinned by the
prompt-validator scenario below).
A successful adapter call SHALL invoke
`request_gallery_image` exactly once and SHALL return outcome `success` with the
minted `image_id` in the result's bounded `data` slot.

#### Scenario: A character request mints one pending image

- **WHEN** `gallery.generate` carries `fields: ["appearance", "armor"]` and bounded free text for the puppet
- **THEN** one gallery job is queued, the result data carries the minted `image_id`, and the panel re-render lists exactly one pending row

#### Scenario: Monster generation is field-free and replace-shaped

- **WHEN** `gallery.generate` names a monster visual-species subject with empty fields and empty free text
- **THEN** the request succeeds, and when its job settles the subject holds exactly one card (the cap's replace semantics), with no binding affordances offered by the panel's capability flags

#### Scenario: A monster request carrying fields is refused naming the capability

- **WHEN** `gallery.generate` names a monster visual-species subject with a non-empty `fields` list
- **THEN** the result is `rejected` with a stable capability-naming code and nothing is queued

#### Scenario: Prompt text bounds follow the shared printable-text validator

- **WHEN** a `custom_prompt` is validated
- **THEN** it is text of at most 512 code points, control-character-free; whitespace-only is legal
  and normalizes to empty; and printable text follows the shared backend validator — every Unicode
  C or Z category except ASCII space is rejected

#### Scenario: Bad fields or prompts fail the schema without the adapter

- **WHEN** field ids are unknown or duplicated, or the prompt is oversized or non-printable
- **THEN** the kind-neutral payload schema fails with `malformed_payload`, without invoking the
  adapter

#### Scenario: Domain codes remain the defensive typed-error mapping

- **WHEN** an adapter is invoked directly or the service adds a stricter refusal
- **THEN** the `unknown_field`, `prompt_too_long`, and `invalid_prompt` domain codes remain the
  defensive mapping of typed service errors

#### Scenario: Typed rejections map to stable localized codes

- **WHEN** the service rejects a generation request with a typed error
- **THEN** it maps to stable codes with bounded zh-TW messages — at minimum `unknown_field`,
  `prompt_too_long`, and the kind-capability refusals naming the undeclared capability

#### Scenario: An unreachable image server keeps the request successful

- **WHEN** the image server is unreachable when a generation request is admitted
- **THEN** the adapter does not probe service connectivity, the request stays successful (§12.3.1),
  and the failure surfaces later as the panel's failed row

#### Scenario: Direct retired-tier requests refuse before writing
- **WHEN** a client names a threat-tier monster subject for generation, default selection, delete, placement or subject selection
- **THEN** the domain returns a stable invalid-subject rejection, with no card, job, preference or file write


### Requirement: Personal official-selection and override adapters reject official-file mutation authoritatively
The production `ui_action` layer SHALL add adapters for the personal official-art preference surface —
selecting an official image identity, clearing the personal official selection, setting an official
image's personal geometry triple (face rectangle and stage), and clearing one geometry override —
each bound to one exact payload validator.

#### Scenario: Selection adapter writes only the preference
- **WHEN** a client dispatches official-select with a valid identity inside an eligible entity-context subject reference
- **THEN** the gallery preference API writes only that entity preference; one gallery/art/roster update publishes and no official or runtime image file changes

#### Scenario: An out-of-reference identity is refused
- **WHEN** a selection or geometry request names an official identity outside the selected subject's content reference, an unindexed identity, or a malformed triple
- **THEN** the adapter refuses with its stable code, no partial write occurs, and the panels re-render truthfully

#### Scenario: Existing mutation adapters refuse official targets
- **WHEN** `gallery.card.delete`, the generate drawer, or the stage-transform action is dispatched with an official identity where a card `image_id` belongs
- **THEN** the stable `official_read_only` rejection returns, no file, card, or preference changes, and one bounded adapter warning event is emitted

#### Scenario: Client-side hiding never weakens the backend
- **WHEN** a client bypasses the hidden affordances and dispatches an official-mutation payload directly
- **THEN** the backend rejects it exactly as if the UI had shown it

#### Scenario: Preference adapters re-resolve identities and map typed errors
- **WHEN** a preference adapter handles a request
- **THEN** it re-resolves every client-supplied identity through the public `world/art/gallery.py`
  preference API and the startup official catalog (never a direct record write, never a
  caller-supplied path), and maps typed backend errors to stable codes with bounded localized
  messages exactly like the existing seven adapters

#### Scenario: Every existing mutation adapter rejects official targets
- **WHEN** any of `gallery.card.delete`, generation, default-setting, face-rect, stage, or binding
  is requested naming an official identity
- **THEN** it is rejected with the stable code `official_read_only` and zero side effects

#### Scenario: The frontend hides official-mutation affordances
- **WHEN** the client renders official-art surfaces
- **THEN** it hides or disables the corresponding affordances, while the backend rejection holds for
  direct requests regardless of client state
#### Scenario: Bare species rows have no personal write target
- **WHEN** a personal official selection, clear or geometry action names a species rail subject with no entity context
- **THEN** it rejects with entity_required and no shared species preference or individual preference is changed

