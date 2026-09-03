## Purpose

The browser's graphical character-creation surface: a read-only `creation` panel
derived from immutable registries, a server-owned wizard draft so the browser
reconnects at any saved stage, four exact allowlisted creation action adapters,
a keyboard-first creation dock with confirmation screens, the server-
authoritative adult gate, and the atomic exploration hand-off after activation.

## Requirements

### Requirement: The creation panel is an exact read-only creation-mode panel
The production presentation registry SHALL register `creation` schema version 3. Its available
payload SHALL contain exactly `schema_version`, `available`, `kind`, `draft`, `presets`, `custom`,
and the optional `proposal`; `available` SHALL be true and `kind` SHALL be `creation`.
`schema_version` SHALL be integer 3. The `proposal` key SHALL be present only while the
authenticated session holds a transient concept proposal and SHALL carry exactly the shape defined
by the transient-fill contract (the base `revision`/`race`/`subrace`/`allocations`/`persona` keys
plus the optional `display_name`, `age`, `apparent_age`, `background`, and `affinity_elements`
transient-fill keys); the presenter SHALL render it from an immutable session snapshot copy. The
presenter SHALL derive every finite control and preview from immutable registries and the
deterministic starting-profile resolver, SHALL emit no live object reference and no filesystem
path, and SHALL NOT mutate `creation_pending`, the wizard draft, the session proposal slot, traits,
identity attributes, location, or world time. The whole panel SHALL use the registered common
unavailable form outside `creation` mode and when the global prerequisite fails; a failure confined
to one field, preset, or profile SHALL NOT fabricate a value.

#### Scenario: A pending character receives the creation panel
- **WHEN** a puppeted WebClient session with `creation_pending` true receives a full snapshot
- **THEN** `creation` reports `available` true, `kind` `creation`, schema version 3, the preset
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

#### Scenario: A schema version 2 payload is rejected
- **WHEN** a `creation` panel payload declares `schema_version` 2 or any other version
- **THEN** exact-schema validation rejects it on both the presenter and the mirrored browser
  validator rather than accepting a stale shape


### Requirement: Creation presentation derives finite controls from immutable registries
The `presets` array SHALL contain at most 8 preset cards, each with exactly `key` (1..64), `display_name` (1..128), `race` (1..64), `race_description` (1..512), nullable `subrace`, `emphasis` (1..256), and `background` (1..256), derived from `PLAYER_PRESET_REGISTRY` and the race registry rather than duplicated literals. The `custom` object SHALL contain exactly `name`, `adult`, `races`, `subraces`, `profiles`, and `affinity`. `name` SHALL contain exactly `min_length` 1 and `max_length` 64, mirroring the deterministic display-name bound (the shared entity-key contract). `adult` SHALL contain exactly `age_minimum` 18, `age_maximum` 10000, `apparent_age_minimum` 18, and `apparent_age_maximum` 10000. `races` SHALL be a list of at most 8 race options, each with exactly `key` (1..64), `description` (1..512), and `subraces` (a list of subrace keys or a single null). `subraces` SHALL map at most 16 subrace keys to exactly `display_name_zh`, `common_name_zh`, and `specialty`, each 1..256 code points. `profiles` SHALL contain at most 16 entries, one per race/subrace combination, each with exactly `race`, `subrace` (null or a key), `budget`, and `axes`; each axis SHALL contain exactly `axis`, `label`, `explanation`, `minimum`, and `maximum`, with `axis` from `hp`, `mp`, `sp`, `atk_phys`, `agility`, `defense`, or `magic_power`, integer `budget`/`minimum`/`maximum` within JavaScript-safe range, and the seven-axis set matching `resolve_starting_profile`. `affinity` SHALL map each race key (`human`, `beastfolk`, `elf`) to exactly `maximum` (integer `2`, `1`, and `0` respectively) and `elements` (exactly the eight lore element choices, each with `key` and `label`, derived from `ELEMENT_REGISTRY`). The `custom` descriptor SHALL NOT contain persona, skill, equipment, inventory, starting-magic, or import-only fields merely because a character-card schema defines them; persona prose values appear only inside `draft.persona` and the transient `proposal` payload, never in control metadata.

#### Scenario: Preset cards render from registry data
- **WHEN** the creation panel ships for a pending character
- **THEN** each preset card names the registry preset key and the registry-derived display name, race, race description, subrace, emphasis, and background with no duplicated string literal

#### Scenario: Custom descriptor carries server-advertised bounds and profiles
- **WHEN** the custom descriptor ships for human, beastfolk, and elf
- **THEN** every race option carries its registry description and subrace list, every (race, subrace) profile carries the exact allocatable axes and budget from `resolve_starting_profile`, the adult fields advertise a minimum of 18, `name` advertises `min_length` 1 and `max_length` 64, and `affinity` advertises the race-dependent maximum (human 2, beastfolk 1, elf 0) with the eight element choices

#### Scenario: Custom descriptor omits import-only fields
- **WHEN** the custom descriptor is inspected
- **THEN** it contains no persona, skill, equipment, inventory, starting-magic, or import-schema field

### Requirement: The server owns the persisted creation wizard draft
The deterministic core SHALL provide a creation-wizard draft service that is the sole writer of the pending character's draft. The draft SHALL persist across logout, login, server reload, and WebSocket reconnect and SHALL store exactly the server-accepted mode and values: for `preset` mode, the stage `preset_selected` and the accepted `preset_key`; for `custom` mode, the stage `custom_filled`, `display_name`, `age`, `apparent_age`, `race`, `subrace`, the `allocations` (one entry per `ALLOCATABLE_AXES` axis), the optional `affinity_elements` (bounded by the race-dependent maximum, elf `none`), an optional bounded `background` text, and a required nullable `persona` block (`personality`, `life_story`, `habit` bounded text fields) accepted only through the custom-save payload. No concept stage exists. Saving a custom draft SHALL validate every accepted value through the existing deterministic preflight before persisting (including a required, registered, race-compatible subrace, a bounded optional background, and the nullable persona block) and SHALL store the submitted persona verbatim with no carry-over or comparison against any earlier value. Activation SHALL re-validate the draft and the actor's ownership and pending state inside one deterministic `transaction.atomic()` block, call the existing all-or-nothing activation service (which persists the persona block and any player background into `entity.db.persona` in the import-card shape when present), and clear the draft in the same transaction so a completed character never retains a draft and two concurrent activations cannot both apply. A reset SHALL clear the draft idempotently. No value SHALL be accepted from a client control the server did not declare, and an incomplete or skipped draft SHALL NOT activate. The draft SHALL NOT set canonical identity attributes, traits, or `creation_pending` on the character; a rejected or cancelled save SHALL leave the canonical identity attributes, the trait set, and any previously validated draft unchanged.

#### Scenario: A saved draft survives reconnect
- **WHEN** a pending character saves a validated custom draft (including the saved `affinity_elements`, an accepted background, and a persona block), disconnects, and logs in again
- **THEN** the creation panel rebuilds from the persisted draft and the browser resumes at the saved stage without re-typing accepted values, including the affinity set, background text, and persona block

#### Scenario: Activation clears the draft atomically
- **WHEN** `creation.activate` commits successfully
- **THEN** the draft (including any background and persona block) is cleared in the same transaction that flips `creation_pending` to false, and no subsequent snapshot returns the draft

#### Scenario: A draft-clear write failure rolls back activation
- **WHEN** a write failure is injected into the draft-clearing step of the activation transaction
- **THEN** the whole activation rolls back, the character remains pending with its prior draft and trait state, and no canonical identity or mechanical state is written

#### Scenario: Concurrent activation applies exactly once
- **WHEN** two live sessions submit `creation.activate` for the same pending character around the same time
- **THEN** the first commit flips `creation_pending` to false and clears the draft, the second fails its re-checked pending or ownership validation, and the character activates exactly once

#### Scenario: Invalid draft input is rejected without mutation
- **WHEN** a custom draft is saved with a name containing a markup delimiter, an underage value, an unknown race, an incompatible or missing subrace, an over-bound background, a malformed persona block, allocations outside the profile bounds or budget, or an affinity set that violates the race-dependent maximum
- **THEN** the save is rejected with a stable reason, no value is persisted, and the character remains pending with its prior draft unchanged

#### Scenario: Reset is idempotent
- **WHEN** `creation.reset` succeeds on a pending character with and without a saved draft
- **THEN** the draft is absent in both cases, the character remains pending, and a repeated reset reports the same success

### Requirement: Creation actions are exact, allowlisted, and server-authoritative
The production action registry SHALL register exactly `creation.preset`, `creation.custom`, `creation.concept`, `creation.activate`, and `creation.reset` for this delivery unit in addition to the three combat and seven service adapters and no unrelated gameplay adapter. `creation.preset` SHALL accept exactly `preset_key` (a 1..64-character non-empty string that exists in the player-preset registry). `creation.custom` SHALL accept exactly `display_name` (1..64 characters), `age` and `apparent_age` (integers in 0..10000 excluding booleans; the deterministic creation service independently enforces the adult minimum on every submission), `race` (a 1..64-character registry key), `subrace` (a 1..64-character registry key belonging to the race; the deterministic service rejects a missing or incompatible subrace), `allocations` (an object containing exactly `hp`, `mp`, `sp`, `atk_phys`, `agility`, and `defense`, each an integer in 0..10000 excluding booleans), optional `affinity_elements` (an array of at most 8 lowercase element keys, each a lore element; the deterministic creation service enforces the race-dependent maximum and rejects a player-supplied set on an elf), optional `background` (a string of at most the declared persona-field bound; a missing value is treated as an empty background), and a required `persona` (null or an object containing exactly `personality`, `life_story`, and `habit`, each a non-empty string of at most the declared persona-field bound; the browser convention ships null when all three fields are empty). `creation.concept` SHALL accept exactly `concept` (a non-empty string of at most the declared bound) and SHALL run the guarded `character_creation` generative layer with the injected client, storing a validated proposal only in the session-scoped transient slot with zero persistent writes. `creation.activate` and `creation.reset` SHALL each accept exactly an empty payload. Every adapter SHALL obtain the account from the authenticated session's puppet, SHALL reject any actor/account/session/puppet/calculated-stat/unknown field, SHALL validate through the existing deterministic creation service (`preflight_character_creation`, `activate_player_character`, and the creation-wizard draft service), and SHALL NOT assign `.db`, traits, identity attributes, or `creation_pending` directly. No action SHALL route an action ID or payload through the text command parser.

#### Scenario: Preset selection reaches the deterministic registry
- **WHEN** a pending character submits `creation.preset` with a shipped preset key
- **THEN** the adapter validates the key against the immutable preset registry, saves the `preset_selected` draft, and refreshes the `creation` panel

#### Scenario: Preset selection is a two-step confirmation in the browser
- **WHEN** a browser player chooses a preset card and then confirms it
- **THEN** the flow submits `creation.preset` with the preset key and then `creation.activate`, sharing the same deterministic activation service the `character preset <key>` command uses while keeping the browser confirmation step explicit

#### Scenario: Custom submission runs the existing preflight
- **WHEN** a pending character submits `creation.custom` with a complete valid custom request including a registered subrace, an optional bounded background, a persona block or null, and `affinity_elements` within the race-dependent maximum
- **THEN** the adapter builds the request and validates it through `preflight_character_creation`, saves the `custom_filled` draft including the submitted persona, and reports success

#### Scenario: A missing or incompatible subrace is rejected before activation
- **WHEN** a client submits `creation.custom` with no `subrace`, an empty `subrace`, or a subrace key that does not belong to the submitted race
- **THEN** the deterministic service rejects with a stable reason and no draft, trait, or identity value changes

#### Scenario: An overlong display name is rejected before the deterministic service
- **WHEN** a client submits `creation.custom` with a `display_name` longer than 64 characters
- **THEN** the adapter rejects it structurally without invoking the deterministic service

#### Scenario: An over-bound background is rejected
- **WHEN** a client submits `creation.custom` with a `background` longer than the declared persona-field bound
- **THEN** the adapter or deterministic service rejects it before activation and the character remains pending

#### Scenario: A concept submission delivers a transient proposal
- **WHEN** a pending character submits `creation.concept` with a bounded concept and the guarded layer returns a valid proposal
- **THEN** the adapter stores the proposal in the session-scoped transient slot with zero persistent writes, returns the applied outcome, and refreshes the `creation` panel carrying the proposal

#### Scenario: An abnormal puppet cannot reach a write path
- **WHEN** an adapter is dispatched with a puppet that has no accessible owning account, is not a `PlayerCharacter`, or is not in `account.characters`
- **THEN** the adapter rejects with a stable ownership/creation reason before any deterministic write and no draft, trait, or identity value changes

#### Scenario: An unknown field cannot sneak past activation
- **WHEN** a client submits any creation action carrying an actor, account, session, skills, equipment, starting-magic, or calculated-stat field
- **THEN** exact-schema validation rejects the request without invoking the adapter or the deterministic service

#### Scenario: A skipped or incomplete draft cannot activate
- **WHEN** `creation.activate` is submitted while no valid draft exists or the draft stage is incomplete
- **THEN** the adapter rejects before `activate_player_character`, the character remains pending, and no trait or identity is written

#### Scenario: An over-bound affinity set on an elf is rejected
- **WHEN** a client submits `creation.custom` with `race == "elf"` and a non-empty `affinity_elements`
- **THEN** the deterministic service rejects the request before persistence and no draft or identity value changes

### Requirement: Creation actions reject stale, duplicate, and tampered input without mutation
Every creation action SHALL pass the existing dispatcher's epoch, base revision, in-flight, and request-ID checks before adapter invocation; a `presentation_epoch` or `base_revision` that does not equal the newest values issued for the live session SHALL return the dispatcher's `stale` outcome with a fresh full snapshot and SHALL invoke no adapter. A duplicate live request ID SHALL return its cached result without re-executing. A tampered `preset_key`, `race`, `subrace`, or allocation that fails current deterministic revalidation SHALL be rejected with a stable code and Traditional Chinese message, and no draft, trait, identity, or `creation_pending` value SHALL change. A pending character that is already activated between render and submit SHALL be rejected as already-complete without opening a second activation.

#### Scenario: Stale revision cannot double-activate
- **WHEN** `creation.activate` is rendered at revision N and submitted with an older `base_revision`
- **THEN** the dispatcher returns outcome `stale`, calls no adapter, and emits a full snapshot without changing the draft or activating

#### Scenario: Duplicate activation executes once
- **WHEN** the same live request ID for `creation.activate` is delivered twice
- **THEN** `activate_player_character` runs once, the character activates once, and the duplicate receives the cached first result

#### Scenario: Unknown preset cannot be selected
- **WHEN** a tampered `preset_key` is submitted for `creation.preset`
- **THEN** the adapter rejects before saving any draft and the character remains pending with its prior draft unchanged

#### Scenario: Already-activated request is rejected
- **WHEN** a creation action is admitted but the character is no longer creation-pending at commit
- **THEN** the adapter rejects with a stable already-complete reason and performs no write

### Requirement: The adult gate is server-authoritative for both age fields
The creation service SHALL reject missing, malformed, `age < 18`, and `apparent_age < 18` values through the existing deterministic creation validation on every `creation.custom` submission, independently for each field. The creation panel SHALL advertise the 18 minimum to the player, but client-side constraints, hidden or removed age fields, altered HTML constraints, and direct `creation.activate` calls SHALL NOT permit an underage or malformed record to activate. A rejected underage request SHALL leave the character pending with no trait or identity written.

#### Scenario: Underage actual age is permanently rejected
- **WHEN** a client sends `age=17` with an adult apparent age through `creation.custom`, including when client-side validation is disabled
- **THEN** the deterministic service rejects the request, the character remains pending, and no trait or identity is written

#### Scenario: Underage apparent age is rejected independently
- **WHEN** a client sends `apparent_age=17` with an adult actual age through `creation.custom`
- **THEN** the deterministic service rejects the request, the character remains pending, and no trait or identity is written

#### Scenario: Missing age fields cannot activate
- **WHEN** `creation.custom` omits either age field or sends a non-integer, boolean-like, or oversized value
- **THEN** exact-schema validation or the deterministic service rejects before activation and the character remains pending

### Requirement: Activation is all-or-nothing and hands off to exploration
Successful `creation.activate` SHALL remain all-or-nothing for character state: either the pending gate is removed with the full deterministic initialization committed, or the character stays pending with no partial trait, identity, or progression state. After a committed activation the adapter SHALL reuse the unchanged best-effort relocation to 聖潔王都南門 and the onboarding arrival behavior, and SHALL publish a full `exploration` snapshot so the browser atomically replaces the creation dock. A failed relocation SHALL preserve the activated state and report the existing explanatory degradation rather than reopening creation with a partially mutated character. The creation adapters SHALL NOT publish an affected-panel set that leaves the shell in creation mode after a successful activation.

#### Scenario: Successful activation moves the shell to exploration
- **WHEN** `creation.activate` commits and the South Gate exists
- **THEN** the full snapshot mode is `exploration`, the creation dock unloads, the character stands at the South Gate with the onboarding arrival behavior unchanged, and `creation_pending` is false

#### Scenario: Failed relocation preserves activated state
- **WHEN** `creation.activate` commits but the South Gate relocation fails
- **THEN** the character remains activated, `creation_pending` is false, the player receives the existing degradation notice, and creation is not reopened

#### Scenario: A failed activation transaction leaves the character pending
- **WHEN** a write failure is injected into the activation transaction
- **THEN** the whole activation rolls back, the character remains pending with its prior draft, and no partial trait, identity, or progression state is persisted

### Requirement: Web activation confirms the exact draft shown
The system SHALL ensure the `creation.activate` flow activates the draft whose save was confirmed, and SHALL surface a stable error when the stored draft changed between confirmation and activation.

#### Scenario: Activation after successful save activates the saved draft
- **WHEN** the player confirms after a successful custom save
- **THEN** the character is activated from that saved draft and `creation_pending` becomes false

#### Scenario: Save rejection followed by activation is refused
- **WHEN** the player confirms while the last save was rejected and an older draft remains stored
- **THEN** the activation is refused with a stable code and no character is activated

### Requirement: The creation dock is keyboard-first, form-capable, and confirmation-protected
In `creation` mode the action dock SHALL present preset cards and the custom form rather
than exploration or service menus. Arrow keys SHALL navigate finite lists and buttons, Tab
and Shift+Tab SHALL move focus through text/numeric fields, Enter SHALL activate the
focused control or submit a complete server-declared form, and Escape SHALL pop exactly one
menu level without discarding the saved server wizard draft. The custom form SHALL require a
subrace selection (no "無子種族" radio is rendered), SHALL display an allocation briefing
(total budget, seven-axis count, each axis's 0–span, and the sum-must-equal-budget rule)
above the allocation fields, and SHALL provide a bounded optional background text field. The
form action buttons (confirm, reset, cancel, and concept-apply) SHALL be operable by
pointer through the shared focus/disabled/submission gate as well as by keyboard, and SHALL
pre-empt the keyboard bridge (a capture-phase listener) while the form owns focus, so keys
the form owns are claimed by the form and none reach the bridge's fall-through text path;
the capture listener SHALL be removed when the form closes. The final activation and the
destructive custom reset SHALL each require an explicit confirmation panel. Disabled entries
SHALL remain focusable with their explanation and SHALL submit nothing. Validation messages
SHALL be associated with the field they concern and announced through the accessible live
region. A stale revision SHALL preserve typed unsent values locally where safe, refresh
server-declared choices, and ask the player to review rather than automatically resubmitting.
No canonical service or creation state SHALL be stored in localStorage.

#### Scenario: Custom form completes without typed commands
- **WHEN** a player uses arrows and Tab/Shift+Tab to choose race and subrace, reviews the
  allocation briefing, types name, ages, allocations, and an optional background into the
  fields, confirms, and activates
- **THEN** the flow submits exactly `creation.custom` once with the expected payload
  (including the required subrace and any background), then `creation.activate` once, and
  the exploration snapshot follows

#### Scenario: The custom form cannot submit without a subrace
- **WHEN** a player leaves the subrace unselected in the custom form and confirms
- **THEN** the form reports the missing subrace against the subrace field and sends no
  `creation.custom` mutation

#### Scenario: The allocation briefing renders before the fields
- **WHEN** the custom form renders race and subrace with a resolvable profile
- **THEN** it displays the profile budget, the seven-axis count, each axis's 0–span range,
  and the rule that the total must equal the budget above the allocation inputs

#### Scenario: Form action buttons respond to pointer clicks
- **WHEN** a player clicks the confirm, reset, cancel, or concept-apply button with the
  pointer
- **THEN** the button runs the identical action the keyboard Enter would run, obeying the
  shared disabled/in-flight/awaiting-revision gate, and no unclaimed keydown reaches the
  bridge's fall-through text path for clicks or for keys the form owns

#### Scenario: The form claims its keys without breaking native input
- **WHEN** a player types or presses Tab, modifier, or IME-composition keys while the
  custom form owns focus
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

### Requirement: Creation browser acceptance is keyboard-only and desktop-bounded
The managed localhost Playwright suite SHALL exercise, using keyboard controls only at
1440x900 and 1280x720: preset selection, confirmation, activation, and the exploration
snapshot; custom finite controls and free-text field focus; reconnect at each saved draft
stage; server rejection of both underage fields despite bypassed client validation; the
destructive reset confirmation; and stale and duplicate submission behavior. Tests SHALL use
deterministic fixtures, SHALL make no remote, LLM, or image-generation request, SHALL assert
the creation dock is the sole action-dock owner in creation mode and re-renders on
exploration (the shared `#action-dock` node may persist with `data-mode` switching), and SHALL
assert no persona/import field is rendered. That shared node is the floating dock panel itself, so
the panel SHALL NOT be remounted at a mode change; in creation mode it SHALL render neither the tab
bar's tabs nor the breadcrumb, because the creation surface is a modal form rather than a router
frame, while keeping its own chrome, its `data-mode="creation"` attribute, and its role as the
surface's documented focus target. Test waits SHALL gate on
deterministic state — polling the committed store view and the creation-surface DOM with a
bounded deadline — rather than on the raw `#action-dock` element becoming visible, so the
suite stays stable under a loaded CI runner.

#### Scenario: Preset journey completes in Chromium
- **WHEN** a seeded pending character uses arrows and Enter to open a preset card, confirms, and activates
- **THEN** the flow submits `creation.preset` then `creation.activate` once each and the refreshed snapshot shows exploration mode with the creation dock removed

#### Scenario: Underage custom journey is rejected end to end
- **WHEN** a browser fills the custom form with `age=17` after disabling the client-side minimum
- **THEN** the server rejects, the character stays pending, and the error is announced without leaving the creation dock

#### Scenario: Reconnect restores the saved stage in Chromium
- **WHEN** the transport disconnects after a validated `creation.custom` save and reconnects
- **THEN** the new-epoch snapshot rebuilds the form at the `custom_filled` stage and no automatic activation is sent

#### Scenario: Minimum viewport retains creation essentials
- **WHEN** the creation dock renders at 1280x720 with a focused disabled control
- **THEN** the player can read the preset cards, the form fields, the disabled explanation, and the confirmation controls without overlap preventing operation

#### Scenario: Creation dock is the sole owner in creation mode and re-renders in exploration
- **WHEN** the browser is in creation mode with the `creation` panel available
- **THEN** exactly one `#action-dock` element is rendered with `data-mode="creation"` (the creation dock is its sole owner), and after activation hands off to exploration no creation-mode dock remains: the shared dock re-renders as `data-mode="exploration"` when `context_actions` is available, so the shared DOM node may persist rather than being fully removed

#### Scenario: The floating dock panel is the persistent node across a mode change
- **WHEN** the browser hands off from creation mode to exploration mode after activation
- **THEN** the same single `#action-dock` panel element persists with its `data-mode` switched from `creation` to `exploration`, and it is not removed and re-created

#### Scenario: Creation mode renders no tab bar and no breadcrumb
- **WHEN** the dock is rendered in creation mode
- **THEN** it renders the creation surface with no root tabs, no count badge, and no breadcrumb line, and the creation form keeps its own key capture exactly as before
