## MODIFIED Requirements

### Requirement: The creation panel is an exact read-only creation-mode panel
The production presentation registry SHALL register `creation` schema version 9. Its available
payload SHALL contain exactly `schema_version`, `available`, `kind`, `draft`, `presets`, `custom`, `portrait`,
and the optional `proposal`; `available` SHALL be true and `kind` SHALL be `creation`. The whole
panel SHALL use the registered common unavailable form outside `creation` mode and when the global
prerequisite fails.

#### Scenario: A pending character receives the creation panel
- **WHEN** a puppeted WebClient session with `creation_pending` true receives a full snapshot
- **THEN** `creation` reports `available` true, `kind` `creation`, schema version 9, the preset
  cards, the custom-form descriptor, and the current server-persisted draft while a before/after
  comparison of canonical game state is unchanged

#### Scenario: Activated and combat characters do not receive the creation panel
- **WHEN** the active puppet is not creation-pending or is in an active combat session
- **THEN** `creation` uses its schema-valid unavailable form and contains no preset card, field,
  draft, or proposal

#### Scenario: Creation presentation stays read-only
- **WHEN** the creation panel is built for a pending character with a saved draft, a pending session
  proposal, and a disguise-independent empty trait set
- **THEN** `creation_pending`, the wizard draft, the session proposal slot, identity attributes,
  traits, and world time are byte-for-byte unchanged and no skill, equipment, inventory, or
  import-schema field is exposed

#### Scenario: A stale schema version is rejected
- **WHEN** a `creation` panel payload declares a `schema_version` other than 9
- **THEN** exact-schema validation rejects it on both the presenter and the mirrored browser
  validator rather than accepting a stale shape

#### Scenario: Schema version ships as the integer 6
- **WHEN** an available `creation` panel payload ships
- **THEN** `schema_version` carries the integer 9

#### Scenario: The proposal key mirrors the transient session proposal
- **WHEN** the authenticated session holds a transient concept proposal
- **THEN** the payload carries the `proposal` key with exactly the shape defined by the
  transient-fill contract — the base `revision`/`race`/`subrace`/`allocations`/`persona` keys plus
  the optional `display_name`, `age`, `apparent_age`, `background`, and `affinity_elements`
  transient-fill keys — and the presenter renders it from an immutable session snapshot copy
- **AND** when the session holds no transient concept proposal, the `proposal` key is absent

#### Scenario: Controls and previews derive from immutable sources
- **WHEN** the presenter builds the panel
- **THEN** every finite control and preview is derived from immutable registries and the
  deterministic starting-profile resolver

#### Scenario: The payload carries no live reference or path
- **WHEN** the presenter emits the `creation` payload
- **THEN** it contains no live object reference and no filesystem path

#### Scenario: Presentation mutates no game state
- **WHEN** the presenter builds and emits the panel
- **THEN** `creation_pending`, the wizard draft, the session proposal slot, traits, identity
  attributes, location, and world time are unchanged

#### Scenario: A partial failure fabricates no value
- **WHEN** a failure is confined to one field, preset, or profile
- **THEN** the panel does not fabricate a value

### Requirement: Creation presentation derives finite controls from immutable registries
The presenter SHALL derive bounded, exact-shape preset cards and custom controls from `PLAYER_PRESET_REGISTRY`, the race registry and the starting-profile resolver, never duplicated literals. Presets SHALL carry `artwork` and custom controls SHALL carry `silhouettes` under the schemas below.

#### Scenario: Preview additions preserve exact control shapes
- **WHEN** finite creation controls are serialized
- **THEN** `presets` contains at most 8 cards, each with exactly `key` (1..64), `display_name` (1..128), `race` (1..64), `race_description` (1..512), nullable `subrace`, `emphasis` (1..256), `background` (1..256), and `artwork`
- **AND** `custom` contains exactly `name`, `age`, `races`, `subraces`, `profiles`, `affinity`, `sex`, and `silhouettes`

#### Scenario: Preset cards render from registry data
- **WHEN** the creation panel ships for a pending character
- **THEN** each preset card names the registry preset key and the registry-derived display name, race, race description, subrace, emphasis, and background with no duplicated string literal

#### Scenario: Custom descriptor carries server-advertised bounds and profiles
- **WHEN** the custom descriptor ships under synthetic race and affinity registries
- **THEN** every race option carries its registry display name, description and subrace list, every (race, subrace) profile carries the exact allocatable axes and budget from `resolve_starting_profile`, the age and name fields retain their schema bounds, and `affinity` advertises each race’s declared maximum and registered element choices

#### Scenario: Custom descriptor advertises server-labelled sex options
- **WHEN** the custom descriptor ships for a pending character
- **THEN** `custom.sex` lists every `SEX_VALUES` member exactly once in registry order, each carrying the server-owned Traditional Chinese label with no label literal duplicated in browser code

#### Scenario: Custom descriptor omits import-only fields
- **WHEN** the custom descriptor is inspected
- **THEN** it contains no persona, skill, equipment, inventory, starting-magic, or import-schema field

#### Scenario: The name descriptor mirrors the display-name bound
- **WHEN** the `custom.name` descriptor ships
- **THEN** it contains exactly `min_length` 1 and `max_length` 64, mirroring the deterministic
  display-name bound (the shared entity-key contract)

#### Scenario: The age descriptor carries the exact range bounds
- **WHEN** the `custom.age` descriptor ships
- **THEN** it contains exactly `age_minimum` 0, `age_maximum` 10000, `apparent_age_minimum` 0,
  and `apparent_age_maximum` 10000

#### Scenario: Race options carry their exact fields
- **WHEN** the `custom.races` list ships
- **THEN** it is a list of at most 8 race options, each with exactly `key` (1..64),
  `display_name_zh` (non-empty 1..128), `description` (1..512), and `subraces` (a list of subrace
  keys or a single null)

#### Scenario: The subraces map carries bounded localized fields
- **WHEN** the `custom.subraces` map ships
- **THEN** it maps at most 16 subrace keys to exactly `display_name_zh`, `common_name_zh`, and
  `specialty`, each 1..256 code points

#### Scenario: Profiles carry the exact seven-axis shape
- **WHEN** the `custom.profiles` list ships
- **THEN** it contains at most 16 entries, one per race/subrace combination, each with exactly
  `race`, `subrace` (null or a key), `budget`, and `axes`; each axis contains exactly `axis`,
  `label`, `explanation`, `minimum`, `maximum`, `point_cap`, and `value_at_cap`, with `axis` from `hp`, `mp`, `sp`, `atk_phys`,
  `agility`, `defense`, or `magic_power`, integer `budget`/`minimum`/`maximum`/`point_cap`/`value_at_cap` within
  JavaScript-safe range, and the seven-axis set matching `resolve_starting_profile`

#### Scenario: Point bounds are independent of lore bounds
- **WHEN** either exact validator reads an axis
- **THEN** it requires a nonnegative `point_cap` and a `value_at_cap` within `minimum` and `maximum`, equal to `minimum` for zero cap
- **AND** preview interpolates from `minimum` to `value_at_cap` with half-up rounding before subrace modifiers

#### Scenario: The affinity map carries race maxima and element choices
- **WHEN** the `custom.affinity` map ships
- **THEN** it maps each advertised race key to exactly `maximum` (that race’s declared integer bound) and `elements` (the registered element choices, each with `key` and `label`, derived from `ELEMENT_REGISTRY`)

#### Scenario: The sex descriptor lists every server value once
- **WHEN** the `custom.sex` list ships
- **THEN** it is a nonempty list of at most 8 sex options in `SEX_VALUES` order, each with exactly
  `key` (1..64 code points, one of the `SEX_VALUES` members) and `label` (1..64 code points of
  server-owned Traditional Chinese text derived server-side, never duplicated in the browser),
  covering every `SEX_VALUES` member exactly once

#### Scenario: Persona prose never enters control metadata
- **WHEN** the `custom` descriptor ships for a character-card-capable schema
- **THEN** it contains no persona, skill, equipment, inventory, starting-magic, or import-only
  fields merely because a character-card schema defines them, and persona prose values appear only
  inside `draft.persona` and the transient `proposal` payload, never in control metadata

#### Scenario: Preset race keys resolve to custom race options
- **WHEN** a preset card's race key is checked against the custom descriptor
- **THEN** every preset race key resolves to a custom race option and its display name is reused
  for preset/confirmation display without changing action keys

### Requirement: The server owns the persisted creation wizard draft
The deterministic core SHALL provide a creation-wizard draft service that is the sole writer of the pending character's draft. The draft SHALL persist across logout, login, server reload, and WebSocket reconnect and SHALL store exactly the server-accepted mode and values. Saving a custom draft SHALL validate every accepted value through the existing deterministic preflight before persisting, and an incomplete or skipped draft SHALL NOT activate.

#### Scenario: A saved draft survives reconnect
- **WHEN** a pending character saves a validated custom draft (including the saved `affinity_elements`, an accepted background, a persona block, and an accepted `sex`), disconnects, and logs in again
- **THEN** the creation panel rebuilds from the persisted draft and the browser resumes at the saved stage without re-typing accepted values, including the affinity set, background text, persona block, and the saved sex selection

#### Scenario: An omitted sex is normalized into the draft
- **WHEN** a custom draft saves with a payload that omits `sex` or sends it null
- **THEN** the persisted draft stores the race-permitted default — `DEFAULT_SEX` when the selected race
  permits that member, otherwise that race's single permitted sex — as a concrete `SEX_VALUES`
  member, and the panel rebuild carries that value

#### Scenario: Activation clears the draft atomically
- **WHEN** `creation.activate` commits successfully
- **THEN** the draft (including any background, persona block, and accepted sex) is cleared in the same transaction that flips `creation_pending` to false, and no subsequent snapshot returns the draft

#### Scenario: A draft-clear write failure rolls back activation
- **WHEN** a write failure is injected into the draft-clearing step of the activation transaction
- **THEN** the whole activation rolls back, the character remains pending with its prior draft and trait state, and no canonical identity or mechanical state is written

#### Scenario: Concurrent activation applies exactly once
- **WHEN** two live sessions submit `creation.activate` for the same pending character around the same time
- **THEN** the first commit flips `creation_pending` to false and clears the draft, the second fails its re-checked pending or ownership validation, and the character activates exactly once

#### Scenario: Invalid draft input is rejected without mutation
- **WHEN** a custom draft is saved with a name containing a markup delimiter, an out-of-range age value, an unknown race, an incompatible or missing subrace, an over-bound background, a malformed persona block, allocations outside the profile bounds or budget, an affinity set that violates the race-dependent maximum, or a `sex` outside `SEX_VALUES` or outside the selected race's declared set
- **THEN** the save is rejected with a stable reason, no value is persisted, and the character remains pending with its prior draft unchanged

#### Scenario: A pre-version draft is treated as absent
- **WHEN** the draft service loads a stored draft whose `DRAFT_VERSION` predates the sex-carrying version
- **THEN** it is treated as no saved draft rather than partially accepted, and the browser resumes at the initial stage

#### Scenario: Reset is idempotent
- **WHEN** `creation.reset` succeeds on a pending character with and without a saved draft
- **THEN** the draft is absent in both cases, the character remains pending, and a repeated reset reports the same success

#### Scenario: The preset-mode draft stores exactly its accepted values
- **WHEN** a preset draft saves
- **THEN** it stores the stage `preset_selected` and the accepted `preset_key`

#### Scenario: The custom-mode draft stores exactly its accepted values
- **WHEN** a custom draft saves
- **THEN** it stores the stage `custom_filled`, `display_name`, `age`, `apparent_age`, `race`,
  `subrace`, the `allocations` (one entry per `ALLOCATABLE_AXES` axis), the optional
  `affinity_elements` (bounded by the race-dependent maximum, elf `none`), an optional bounded
  `background` text, a required nullable `persona` block (`personality`, `life_story`, `habit`
  bounded text fields) accepted only through the custom-save payload, and the accepted `sex`; a newly saved custom elf draft also stores `allocation_policy_version: 1`

#### Scenario: An unknown sex member is rejected at save time
- **WHEN** a custom draft saves with a `sex` that names a member outside `SEX_VALUES`, or a
  `SEX_VALUES` member the selected race does not permit
- **THEN** the save rejects — normalization at save time only maps an absent or null value to the
  race-permitted default, yielding a concrete `SEX_VALUES` member

#### Scenario: No concept stage exists
- **WHEN** the draft stages are enumerated
- **THEN** no concept stage exists between preset selection and custom fill

#### Scenario: Preflight covers every accepted custom value
- **WHEN** a custom draft save runs its preflight validation
- **THEN** it checks a required, registered, race-compatible subrace, a bounded optional
  background, the nullable persona block, and the race-aware sex normalization before persisting

#### Scenario: The persona is stored verbatim with no carry-over
- **WHEN** a custom draft saves a persona block after an earlier draft held a different one
- **THEN** the submitted persona is stored verbatim with no carry-over or comparison against any
  earlier value

#### Scenario: Activation revalidates inside one atomic transaction
- **WHEN** activation runs
- **THEN** the draft and the actor's ownership and pending state are re-validated inside one
  deterministic `transaction.atomic()` block and the existing all-or-nothing activation service is
  called, clearing the draft in the same transaction so a completed character never retains a
  draft and two concurrent activations cannot both apply

#### Scenario: Activation persists persona and sex canonically
- **WHEN** the activation service commits a draft carrying a persona block, a player background,
  and an accepted sex
- **THEN** the persona block and any player background persist into `entity.db.persona` in the
  import-card shape when present, and the accepted `sex` persists on the character entity

#### Scenario: Undeclared client controls are not accepted
- **WHEN** a draft write would take a value from a client control the server did not declare
- **THEN** no value is accepted from it

#### Scenario: The draft service writes no canonical state
- **WHEN** a draft saves, is rejected, or is cancelled
- **THEN** the draft sets no canonical identity attributes, traits, or `creation_pending` on the
  character, and the canonical identity attributes, the trait set, and any previously validated
  draft remain unchanged

#### Scenario: Superseded elf allocation resumes incomplete
- **WHEN** an otherwise valid stored custom elf draft lacks the current allocation policy marker
- **THEN** the read-only panel carries the same custom draft fields with stage `custom_needs_allocation` and `allocations: null`, never exposing the storage marker
- **AND** the browser resumes at allocation with confirmation blocked and the other fields and portrait retained
- **AND** activation without a new save is rejected even before presentation and with a matching fingerprint

#### Scenario: Fresh allocation restores confirmation
- **WHEN** the player saves a complete valid allocation after resuming
- **THEN** the server returns `custom_filled` with the accepted seven points and the new draft may be explicitly confirmed

### Requirement: The creation dock is keyboard-first, form-capable, and confirmation-protected
In `creation` mode the action dock SHALL present preset cards and the custom form rather
than exploration or service menus, keyboard-first: Arrow keys SHALL navigate finite lists
and buttons, Tab and Shift+Tab SHALL move focus through text/numeric fields, Enter SHALL
activate the focused control or submit a complete server-declared form, and Escape SHALL
pop exactly one menu level without discarding the saved server wizard draft.

#### Scenario: Custom form completes without typed commands
- **WHEN** a player uses arrows and Tab/Shift+Tab to choose race and subrace, reviews the
  allocation briefing, types name, ages, allocations, and an optional background into the
  fields, picks a sex from the select, confirms, and activates
- **THEN** the flow submits exactly `creation.custom` once with the expected payload
  (including the required subrace, the chosen sex, and any background), then
  `creation.activate` once, and the exploration snapshot follows

#### Scenario: The custom form cannot submit without a subrace
- **WHEN** a player leaves the subrace unselected in the custom form and confirms
- **THEN** the form reports the missing subrace against the subrace field and sends no
  `creation.custom` mutation

#### Scenario: The sex select renders server-declared options only
- **WHEN** the custom form renders with a panel whose `custom.sex` carries the three labelled options
- **THEN** the select below the name field offers exactly those server keys and labels in order with `DEFAULT_SEX` preselected on a fresh form, and no option label is hardcoded in the browser bundle

#### Scenario: The name-roll button dispatches and backfills by request id
- **WHEN** a player clicks the `creation-roll-name` button and a success result carrying that submitted request id arrives with `data.display_name`
- **THEN** exactly one `creation.roll_name` payload `{race, subrace, sex}` was dispatched, the button was disabled while in flight, and the display-name input is backfilled with the rolled name which the player can then edit

#### Scenario: The custom tab stays pinned through in-flight name-roll republishes
- **WHEN** a player pointer-selects the custom tab and clicks `creation-roll-name`, the
  name-roll dispatch is admitted and synchronously publishes the store view, and a
  success result carrying the submitted request id and `data.display_name` commits
- **THEN** the presented tab remains the custom tab for the whole in-flight window,
  including the dispatch publish, result settlement, and dispatch-gate release; the
  display-name input receives the rolled name, the button re-enables, and subsequent
  unchanged-stage republishes do not replace the custom tab with the preset tab

#### Scenario: A failed or foreign roll result never rewrites the name field
- **WHEN** the in-flight roll settles with a non-success outcome or a result whose request id does not match the submitted one
- **THEN** the in-flight state settles, the button re-enables, and the display-name input keeps whatever the player typed

#### Scenario: The allocation briefing renders before the fields
- **WHEN** the custom form renders race and subrace with a resolvable profile
- **THEN** it displays the profile budget, the seven-axis count, each axis's zero-through-point-cap range,
  and the rule that the total must equal the budget above the allocation inputs

#### Scenario: Form action buttons respond to pointer clicks
- **WHEN** a player clicks the confirm, reset, cancel, or concept-apply button with the
  pointer
- **THEN** the button runs the identical action the keyboard Enter would run, obeying the
  shared disabled/in-flight/awaiting-revision gate, and no unclaimed keydown reaches the
  bridge's fall-through text path for clicks or for keys the form owns

#### Scenario: The form claims its keys without breaking native input
- **WHEN** a player types or presses Tab, modifier, or IME-composition keys while the custom form owns focus
- **THEN** native focus movement, text input, and Chinese IME continue to work (no
  `preventDefault` on those keys), the form's capture-phase pre-emption claims those keys
  (so no unclaimed keydown reaches the bridge), and a held or repeated Enter submits at most
  once

#### Scenario: A pointer click and a keyboard Enter cannot double-submit
- **WHEN** a player activates a form button by pointer while the same button also receives a
  keyboard-synthesized Enter
- **THEN** exactly one `creation.*` mutation is emitted per deliberate activation, with the
  in-flight / awaiting-revision gate and the pointer bridge's primary-single-activation
  check suppressing the duplicate

#### Scenario: Activation and reset require confirmation
- **WHEN** the player focuses activation or the custom reset but has not confirmed
- **THEN** no mutation is sent and Escape returns exactly one menu level without activating
  or clearing the draft

#### Scenario: An in-flight concept apply shows a prominent waiting state
- **WHEN** a player submits a concept and the generative layer has not yet settled
- **THEN** the concept tab shows a large spinner with an explicit waiting message, the
  concept input and apply button are disabled so no second concept is submitted, and the
  waiting state clears exactly when a fresh proposal is applied or a non-success result
  bearing the submitted request id settles the request

#### Scenario: A synchronously failed dispatch never sticks the waiting state
- **WHEN** a concept dispatch is admitted but its transport send fails synchronously (the
  store releases its mutation gate without ever emitting an action result), or the gate
  releases while no proposal has arrived
- **THEN** the waiting state clears with the concept tab restored to an editable form, and
  an apply rejected by the single-in-flight gate never enters the waiting state at all

#### Scenario: The concept tab stays pinned through in-flight republishes
- **WHEN** a concept apply is in flight and the store commits panel updates or draft
  re-syncs whose stage signal would otherwise mirror onto the presented tab
- **THEN** the presented tab remains the concept tab for the whole in-flight window, and
  the waiting state clears without ever being replaced by the preset tab

#### Scenario: A proposal-only panel refresh never navigates the dock
- **WHEN** a concept apply completes and the store commits a `creation` panel with no draft
  and a `proposal` slot
- **THEN** the creation dock's stage is unchanged (the player is not moved to the preset
  stage), and any tab movement comes solely from the overlay's own completion navigation

#### Scenario: The custom form requires a subrace selection
- **WHEN** the custom form is rendered
- **THEN** a subrace selection is required and no "無子種族" radio is rendered

#### Scenario: The custom form fields beyond the keyboard map
- **WHEN** the custom form renders
- **THEN** it displays an allocation briefing (total budget, seven-axis count, each axis's
  zero-through-point-cap, and the sum-must-equal-budget rule) above the allocation fields
- **AND** it provides a bounded optional background text field
- **AND** it renders a sex `<select>` directly below the display-name field whose options come
  verbatim from `custom.sex` (no browser-side label literals, the `DEFAULT_SEX` key preselected
  for a fresh form)
- **AND** it renders a name-roll button carrying test id `creation-roll-name` adjacent to the
  display-name input

#### Scenario: The name-roll button gates in flight and backfills by request id
- **WHEN** a name roll is in flight
- **THEN** the button is disabled through the shared dispatch gate
- **AND** a settled success result carrying the submitted request id backfills the display-name
  input with `data.display_name` — the player may then freely edit it and the final value is
  validated only by `creation.custom`
- **AND** a non-success or non-matching result settles the in-flight state without touching the
  input

#### Scenario: Form action buttons work by pointer and pre-empt the keyboard bridge
- **WHEN** the form action buttons (confirm, reset, cancel, and concept-apply) are presented
- **THEN** they are operable by pointer through the shared focus/disabled/submission gate as
  well as by keyboard
- **AND** they pre-empt the keyboard bridge (a capture-phase listener) while the form owns
  focus, so keys the form owns are claimed by the form and none reach the bridge's fall-through
  text path
- **AND** the capture listener is removed when the form closes

#### Scenario: An in-flight concept apply presents the prominent waiting state
- **WHEN** a concept apply is in flight
- **THEN** the concept tab presents a prominent in-progress state — a visible large spinner
  with an explicit waiting message — and disables the concept input and the concept-apply
  button until a fresh proposal revision is applied, a result carrying the submitted request id
  with a non-success outcome settles the request, or the global dispatch gate releases without a
  matching settlement (the safety net for a synchronous transport failure or a lost mutation)
- **AND** the in-progress state is only ever entered after the dispatch was admitted, so a
  gate-rejected apply never shows it

#### Scenario: The presented tab is pinned through the form's own in-flight request
- **WHEN** a creation form's own admitted request is in its in-flight loading state (concept
  apply or name roll)
- **THEN** no store publish or draft re-sync moves the presented tab — the tab is pinned while
  that loading state is alive

#### Scenario: A settled apply has no completion affordance beyond the custom-tab switch
- **WHEN** a concept apply settles successfully
- **THEN** the browser presents no other completion affordance beyond the custom-tab switch —
  the confirmation toast is surfaced through the action-feedback queue by the form's apply path,
  and the failure toast by the action-feedback result slice, not by any form-embedded banner

#### Scenario: Activation and reset require explicit confirmation panels
- **WHEN** the player triggers the final activation or the destructive custom reset
- **THEN** each requires an explicit confirmation panel

#### Scenario: Accessibility of disabled entries and validation messages
- **WHEN** the dock renders a disabled entry or a field error
- **THEN** disabled entries remain focusable with their explanation and submit nothing, and
  validation messages are associated with the field they concern and announced through the
  accessible live region

#### Scenario: A stale revision preserves typed values without resubmitting
- **WHEN** the dock observes a stale revision
- **THEN** typed unsent values are preserved locally where safe, server-declared choices are
  refreshed, and the player is asked to review rather than the form being automatically resubmitted

#### Scenario: The panel signature ignores proposals for stage navigation
- **WHEN** a committed `creation` panel carries no draft and only a transient proposal
- **THEN** it does not reset the creation dock's stage — the panel signature covers presets,
  races, and the draft only, so a proposal delivery alone never navigates the player

#### Scenario: No creation state lives in localStorage
- **WHEN** the creation surface runs in the browser
- **THEN** no canonical service or creation state is stored in localStorage
