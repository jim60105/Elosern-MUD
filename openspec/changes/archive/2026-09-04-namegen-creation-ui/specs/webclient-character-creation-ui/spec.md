# webclient-character-creation-ui — Delta Spec

## MODIFIED Requirements

### Requirement: The creation panel is an exact read-only creation-mode panel
The production presentation registry SHALL register `creation` schema version 4. Its available
payload SHALL contain exactly `schema_version`, `available`, `kind`, `draft`, `presets`, `custom`,
and the optional `proposal`; `available` SHALL be true and `kind` SHALL be `creation`.
`schema_version` SHALL be integer 4. The `proposal` key SHALL be present only while the
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
- **THEN** `creation` reports `available` true, `kind` `creation`, schema version 4, the preset
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
- **WHEN** a `creation` panel payload declares `schema_version` 3 (the pre-sex prior version), 2,
  or any other version
- **THEN** exact-schema validation rejects it on both the presenter and the mirrored browser
  validator rather than accepting a stale shape

### Requirement: Creation presentation derives finite controls from immutable registries
The `presets` array SHALL contain at most 8 preset cards, each with exactly `key` (1..64), `display_name` (1..128), `race` (1..64), `race_description` (1..512), nullable `subrace`, `emphasis` (1..256), and `background` (1..256), derived from `PLAYER_PRESET_REGISTRY` and the race registry rather than duplicated literals. The `custom` object SHALL contain exactly `name`, `adult`, `races`, `subraces`, `profiles`, `affinity`, and `sex`. `name` SHALL contain exactly `min_length` 1 and `max_length` 64, mirroring the deterministic display-name bound (the shared entity-key contract). `adult` SHALL contain exactly `age_minimum` 18, `age_maximum` 10000, `apparent_age_minimum` 18, and `apparent_age_maximum` 10000. `races` SHALL be a list of at most 8 race options, each with exactly `key` (1..64), `description` (1..512), and `subraces` (a list of subrace keys or a single null). `subraces` SHALL map at most 16 subrace keys to exactly `display_name_zh`, `common_name_zh`, and `specialty`, each 1..256 code points. `profiles` SHALL contain at most 16 entries, one per race/subrace combination, each with exactly `race`, `subrace` (null or a key), `budget`, and `axes`; each axis SHALL contain exactly `axis`, `label`, `explanation`, `minimum`, and `maximum`, with `axis` from `hp`, `mp`, `sp`, `atk_phys`, `agility`, `defense`, or `magic_power`, integer `budget`/`minimum`/`maximum` within JavaScript-safe range, and the seven-axis set matching `resolve_starting_profile`. `affinity` SHALL map each race key (`human`, `beastfolk`, `elf`) to exactly `maximum` (integer `2`, `1`, and `0` respectively) and `elements` (exactly the eight lore element choices, each with `key` and `label`, derived from `ELEMENT_REGISTRY`). `sex` SHALL be a nonempty list of at most 8 sex options in `SEX_VALUES` order, each with exactly `key` (1..64 code points, one of the `SEX_VALUES` members) and `label` (1..64 code points of server-owned Traditional Chinese text derived server-side, never duplicated in the browser), covering every `SEX_VALUES` member exactly once. The `custom` descriptor SHALL NOT contain persona, skill, equipment, inventory, starting-magic, or import-only fields merely because a character-card schema defines them; persona prose values appear only inside `draft.persona` and the transient `proposal` payload, never in control metadata.

#### Scenario: Preset cards render from registry data
- **WHEN** the creation panel ships for a pending character
- **THEN** each preset card names the registry preset key and the registry-derived display name, race, race description, subrace, emphasis, and background with no duplicated string literal

#### Scenario: Custom descriptor carries server-advertised bounds and profiles
- **WHEN** the custom descriptor ships for human, beastfolk, and elf
- **THEN** every race option carries its registry description and subrace list, every (race, subrace) profile carries the exact allocatable axes and budget from `resolve_starting_profile`, the adult fields advertise a minimum of 18, `name` advertises `min_length` 1 and `max_length` 64, and `affinity` advertises the race-dependent maximum (human 2, beastfolk 1, elf 0) with the eight element choices

#### Scenario: Custom descriptor advertises server-labelled sex options
- **WHEN** the custom descriptor ships for a pending character
- **THEN** `custom.sex` lists every `SEX_VALUES` member exactly once in registry order, each carrying the server-owned Traditional Chinese label (女性 for `female`, 男性 for `male`, 其他 for `other`) with no label literal duplicated in browser code

#### Scenario: Custom descriptor omits import-only fields
- **WHEN** the custom descriptor is inspected
- **THEN** it contains no persona, skill, equipment, inventory, starting-magic, or import-schema field

### Requirement: The server owns the persisted creation wizard draft
The deterministic core SHALL provide a creation-wizard draft service that is the sole writer of the pending character's draft. The draft SHALL persist across logout, login, server reload, and WebSocket reconnect and SHALL store exactly the server-accepted mode and values: for `preset` mode, the stage `preset_selected` and the accepted `preset_key`; for `custom` mode, the stage `custom_filled`, `display_name`, `age`, `apparent_age`, `race`, `subrace`, the `allocations` (one entry per `ALLOCATABLE_AXES` axis), the optional `affinity_elements` (bounded by the race-dependent maximum, elf `none`), an optional bounded `background` text, a required nullable `persona` block (`personality`, `life_story`, `habit` bounded text fields) accepted only through the custom-save payload, and the accepted `sex` — a concrete `SEX_VALUES` member normalized at save time from the payload's optional or null `sex` (an absent or null value becomes `DEFAULT_SEX`, an unknown member is rejected). No concept stage exists. Saving a custom draft SHALL validate every accepted value through the existing deterministic preflight before persisting (including a required, registered, race-compatible subrace, a bounded optional background, the nullable persona block, and the sex normalization above) and SHALL store the submitted persona verbatim with no carry-over or comparison against any earlier value. Activation SHALL re-validate the draft and the actor's ownership and pending state inside one deterministic `transaction.atomic()` block, call the existing all-or-nothing activation service (which persists the persona block and any player background into `entity.db.persona` in the import-card shape when present, and persists the accepted `sex` on the character entity), and clear the draft in the same transaction so a completed character never retains a draft and two concurrent activations cannot both apply. A reset SHALL clear the draft idempotently. No value SHALL be accepted from a client control the server did not declare, and an incomplete or skipped draft SHALL NOT activate. The draft SHALL NOT set canonical identity attributes, traits, or `creation_pending` on the character; a rejected or cancelled save SHALL leave the canonical identity attributes, the trait set, and any previously validated draft unchanged.

#### Scenario: A saved draft survives reconnect
- **WHEN** a pending character saves a validated custom draft (including the saved `affinity_elements`, an accepted background, a persona block, and an accepted `sex`), disconnects, and logs in again
- **THEN** the creation panel rebuilds from the persisted draft and the browser resumes at the saved stage without re-typing accepted values, including the affinity set, background text, persona block, and the saved sex selection

#### Scenario: An omitted sex is normalized into the draft
- **WHEN** a custom draft saves with a payload that omits `sex` or sends it null
- **THEN** the persisted draft stores `DEFAULT_SEX` as a concrete `SEX_VALUES` member and the panel rebuild carries that value

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
- **WHEN** a custom draft is saved with a name containing a markup delimiter, an underage value, an unknown race, an incompatible or missing subrace, an over-bound background, a malformed persona block, allocations outside the profile bounds or budget, an affinity set that violates the race-dependent maximum, or a `sex` outside `SEX_VALUES`
- **THEN** the save is rejected with a stable reason, no value is persisted, and the character remains pending with its prior draft unchanged

#### Scenario: A pre-version draft is treated as absent
- **WHEN** the draft service loads a stored draft whose `DRAFT_VERSION` predates the sex-carrying version
- **THEN** it is treated as no saved draft rather than partially accepted, and the browser resumes at the initial stage

#### Scenario: Reset is idempotent
- **WHEN** `creation.reset` succeeds on a pending character with and without a saved draft
- **THEN** the draft is absent in both cases, the character remains pending, and a repeated reset reports the same success

### Requirement: Creation actions are exact, allowlisted, and server-authoritative
The production action registry SHALL register exactly `creation.preset`, `creation.custom`, `creation.concept`, `creation.roll_name`, `creation.activate`, and `creation.reset` for this delivery unit in addition to the three combat and seven service adapters and no unrelated gameplay adapter. `creation.preset` SHALL accept exactly `preset_key` (a 1..64-character non-empty string that exists in the player-preset registry). `creation.custom` SHALL accept exactly `display_name` (1..64 characters), `age` and `apparent_age` (integers in 0..10000 excluding booleans; the deterministic creation service independently enforces the adult minimum on every submission), `race` (a 1..64-character registry key), `subrace` (a 1..64-character registry key belonging to the race; the deterministic service rejects a missing or incompatible subrace), `allocations` (an object containing exactly `hp`, `mp`, `sp`, `atk_phys`, `agility`, and `defense`, each an integer in 0..10000 excluding booleans), optional `affinity_elements` (an array of at most 8 lowercase element keys, each a lore element; the deterministic creation service enforces the race-dependent maximum and rejects a player-supplied set on an elf), optional `background` (a string of at most the declared persona-field bound; a missing value is treated as an empty background), optional `sex` (null or a `SEX_VALUES` member; a missing value is treated as `DEFAULT_SEX` by the deterministic service), and a required `persona` (null or an object containing exactly `personality`, `life_story`, and `habit`, each a non-empty string of at most the declared persona-field bound; the browser convention ships null when all three fields are empty). `creation.concept` SHALL accept exactly `concept` (a non-empty string of at most the declared bound) and SHALL run the guarded `character_creation` generative layer with the injected client, storing a validated proposal only in the session-scoped transient slot with zero persistent writes. `creation.roll_name` SHALL accept exactly `race` (null or a `RACE_REGISTRY` key), `subrace` (null, or a `SUBRACE_REGISTRY` key whose registry `race_key` equals the submitted race; a null `race` requires a null `subrace`), and `sex` (null or a `SEX_VALUES` member); every value outside those registries SHALL be rejected with a stable validation code through the existing validation-error channel before the roller runs — the roller's bound-pack random fallback SHALL serve only a genuinely unselected race (`race: null`) and SHALL NEVER turn a dirty key into a success — and an admitted payload SHALL draw the name through `roll_name_for_race` using the adapter module's single private unseeded `random.Random()` instance (read only on the roll-name path), SHALL perform zero persistent writes and SHALL NOT refresh any panel, and SHALL return the rolled name as `display_name` inside the result envelope's conditional `data` slot. `creation.activate` and `creation.reset` SHALL each accept exactly an empty payload. Every adapter SHALL obtain the account from the authenticated session's puppet, SHALL reject any actor/account/session/puppet/calculated-stat/unknown field, SHALL validate through the existing deterministic creation service (`preflight_character_creation`, `activate_player_character`, and the creation-wizard draft service) except the read-only `creation.roll_name` roller call, and SHALL NOT assign `.db`, traits, identity attributes, or `creation_pending` directly. No action SHALL route an action ID or payload through the text command parser.

#### Scenario: Preset selection reaches the deterministic registry
- **WHEN** a pending character submits `creation.preset` with a shipped preset key
- **THEN** the adapter validates the key against the immutable preset registry, saves the `preset_selected` draft, and refreshes the `creation` panel

#### Scenario: Preset selection is a two-step confirmation in the browser
- **WHEN** a browser player chooses a preset card and then confirms it
- **THEN** the flow submits `creation.preset` with the preset key and then `creation.activate`, sharing the same deterministic activation service the `character preset <key>` command uses while keeping the browser confirmation step explicit

#### Scenario: Custom submission runs the existing preflight
- **WHEN** a pending character submits `creation.custom` with a complete valid custom request including a registered subrace, an optional bounded background, a persona block or null, `affinity_elements` within the race-dependent maximum, and an optional `sex`
- **THEN** the adapter builds the request and validates it through `preflight_character_creation`, saves the `custom_filled` draft including the submitted persona and the normalized sex, and reports success

#### Scenario: Custom submission without a sex field normalizes to the default
- **WHEN** a pending character submits `creation.custom` with no `sex` key or an explicit null `sex`
- **THEN** the deterministic service accepts the request and the saved draft stores `DEFAULT_SEX`

#### Scenario: A custom submission with an unknown sex is rejected
- **WHEN** a client submits `creation.custom` with a `sex` string outside `SEX_VALUES`
- **THEN** the deterministic service rejects with a stable reason and no draft, trait, or identity value changes

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

#### Scenario: A roll-name submission returns a display name with zero writes
- **WHEN** a pending character submits `creation.roll_name` with a valid race, subrace, and sex (or nulls)
- **THEN** the adapter returns outcome `success` with `data.display_name` from `roll_name_for_race`, no draft, trait, identity, `creation_pending`, or session-slot value changes, and no panel refresh is emitted

#### Scenario: An activated character cannot roll names
- **WHEN** `creation.roll_name` is submitted for an owned character whose `creation_pending` flag is no longer set
- **THEN** the adapter rejects with the established `already_complete` code and Traditional Chinese message, the roller is never invoked, no result `data` slot is emitted, and no panel refresh is published

#### Scenario: An unregistered roll-name race is rejected instead of falling back
- **WHEN** `creation.roll_name` is submitted with a structurally valid 1..64-character `race` key that is not a `RACE_REGISTRY` member
- **THEN** the adapter rejects with a stable validation code and Traditional Chinese message, the roller is never invoked, and no result `data` slot is emitted

#### Scenario: An unselected race falls back only to the rule-layer bound packs
- **WHEN** `creation.roll_name` is submitted with `race` and `subrace` both null (the player never chose a race)
- **THEN** the adapter calls `roll_name_for_race(None, ...)` and the result's `data.display_name` is drawn exclusively from the packs bound in `NAME_PACK_BY_RACE` (`fantasy-human`／`fantasy-elf`／`fantasy-orc`), never from `fantasy-dwarf` or `fantasy-halfling`

#### Scenario: A mismatched subrace pair is rejected before the roller
- **WHEN** `creation.roll_name` is submitted with a `subrace` whose registry `race_key` differs from the submitted `race`, a `subrace` absent from `SUBRACE_REGISTRY`, or a non-null `subrace` beside a null `race`
- **THEN** the adapter rejects with a stable validation code, the roller is never invoked, and no result `data` slot is emitted

#### Scenario: An invalid roll-name sex is rejected before the roller
- **WHEN** `creation.roll_name` is submitted with a `sex` string outside `SEX_VALUES`, or with any field exceeding the structural identifier bound, or with an extra field
- **THEN** exact payload validation rejects with a stable code and Traditional Chinese message, the roller is never invoked, and no result `data` slot is emitted

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

### Requirement: The creation dock is keyboard-first, form-capable, and confirmation-protected
In `creation` mode the action dock SHALL present preset cards and the custom form rather
than exploration or service menus. Arrow keys SHALL navigate finite lists and buttons, Tab
and Shift+Tab SHALL move focus through text/numeric fields, Enter SHALL activate the
focused control or submit a complete server-declared form, and Escape SHALL pop exactly one
menu level without discarding the saved server wizard draft. The custom form SHALL require a
subrace selection (no "無子種族" radio is rendered), SHALL display an allocation briefing
(total budget, seven-axis count, each axis's 0–span, and the sum-must-equal-budget rule)
above the allocation fields, SHALL provide a bounded optional background text field, SHALL
render a sex `<select>` directly below the display-name field whose options come verbatim
from `custom.sex` (no browser-side label literals, the `DEFAULT_SEX` key preselected for a
fresh form), and SHALL render a name-roll button carrying test id `creation-roll-name`
adjacent to the display-name input. While a name roll is in flight the button SHALL be
disabled through the shared dispatch gate, and a settled success result carrying the
submitted request id SHALL backfill the display-name input with `data.display_name` (the
player may then freely edit it; the final value is validated only by `creation.custom`);
a non-success or non-matching result SHALL settle the in-flight state without touching the
input. The
form action buttons (confirm, reset, cancel, and concept-apply) SHALL be operable by
pointer through the shared focus/disabled/submission gate as well as by keyboard, and SHALL
pre-empt the keyboard bridge (a capture-phase listener) while the form owns focus, so keys
the form owns are claimed by the form and none reach the bridge's fall-through text path;
the capture listener SHALL be removed when the form closes. While a concept apply is in
flight the concept tab SHALL present a prominent in-progress state — a visible large
spinner with an explicit waiting message — and SHALL disable the concept input and the
concept-apply button until a fresh proposal revision is applied, a result carrying the
submitted request id with a non-success outcome settles the request, or the global
dispatch gate releases without a matching settlement (the safety net for a synchronous
transport failure or a lost mutation; the in-progress state SHALL only ever be entered
after the dispatch was admitted, so a gate-rejected apply never shows it); through the
whole in-flight window no store publish or draft re-sync SHALL move the presented tab — the
tab is pinned while the loading state is alive. The browser SHALL present no other completion
affordance for a settled apply beyond the custom-tab switch (the confirmation toast is
surfaced through the action-feedback queue by the form's apply path, and the failure toast
by the action-feedback result slice — not by any form-embedded banner). The final activation and the
destructive custom reset SHALL each require an explicit confirmation panel. Disabled entries
SHALL remain focusable with their explanation and SHALL submit nothing. Validation messages
SHALL be associated with the field they concern and announced through the accessible live
region. A stale revision SHALL preserve typed unsent values locally where safe, refresh
server-declared choices, and ask the player to review rather than automatically resubmitting.
A committed `creation` panel that carries no draft and only a transient proposal SHALL NOT
reset the creation dock's stage — the panel signature covers presets, races, and the draft
only, so a proposal delivery alone never navigates the player.
No canonical service or creation state SHALL be stored in localStorage.

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

#### Scenario: A failed or foreign roll result never rewrites the name field
- **WHEN** the in-flight roll settles with a non-success outcome or a result whose request id does not match the submitted one
- **THEN** the in-flight state settles, the button re-enables, and the display-name input keeps whatever the player typed

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
