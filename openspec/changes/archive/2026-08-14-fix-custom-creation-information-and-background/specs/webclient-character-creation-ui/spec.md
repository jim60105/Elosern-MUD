## MODIFIED Requirements

### Requirement: The server owns the persisted creation wizard draft
The deterministic core SHALL provide a creation-wizard draft service that is the sole writer of the pending character's draft. The draft SHALL persist across logout, login, server reload, and WebSocket reconnect and SHALL store exactly the server-accepted mode and values: for `preset` mode, the stage `preset_selected` and the accepted `preset_key`; for `custom` mode, the stage `custom_filled`, `display_name`, `age`, `apparent_age`, `race`, `subrace`, the six `allocations`, and an optional bounded `background` text; and for the concept path, the stage `concept_filled`, `race`, `subrace`, `allocations`, and an optional persona block (`personality`, `life_story`, `habit` bounded text fields) accepted only from the deterministic concept-apply service. Saving a custom draft SHALL validate every accepted value through the existing deterministic preflight before persisting (including a required, registered, race-compatible subrace and a bounded optional background), and SHALL preserve the concept draft's persona block only when the submitted race equals the concept draft's race, clearing it otherwise. Activation SHALL re-validate the draft and the actor's ownership and pending state inside one deterministic `transaction.atomic()` block, call the existing all-or-nothing activation service (which persists the persona block and any player background into `entity.db.persona` in the import-card shape when present), and clear the draft in the same transaction so a completed character never retains a draft and two concurrent activations cannot both apply. A reset SHALL clear the draft idempotently. No value SHALL be accepted from a client control the server did not declare, and an incomplete or skipped draft SHALL NOT activate. The draft SHALL NOT set canonical identity attributes, traits, or `creation_pending` on the character; a rejected or cancelled save SHALL leave the canonical identity attributes, the trait set, and any previously validated draft unchanged. Persona prose content SHALL NOT be exposed in any panel payload beyond the non-content background indicator.

#### Scenario: A saved draft survives reconnect
- **WHEN** a pending character saves a validated custom draft (including an accepted background), disconnects, and logs in again
- **THEN** the creation panel rebuilds from the persisted draft and the browser resumes at the saved stage without re-typing accepted values, including the background text

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
- **WHEN** a custom draft is saved with a name containing a markup delimiter, an underage value, an unknown race, an incompatible or missing subrace, an over-bound background, or allocations outside the profile bounds or budget
- **THEN** the save is rejected with a stable reason, no value is persisted, and the character remains pending with its prior draft unchanged

#### Scenario: Reset is idempotent
- **WHEN** `creation.reset` succeeds on a pending character with and without a saved draft
- **THEN** the draft is absent in both cases, the character remains pending, and a repeated reset reports the same success

### Requirement: Creation actions are exact, allowlisted, and server-authoritative
The production action registry SHALL register exactly `creation.preset`, `creation.custom`, `creation.concept`, `creation.activate`, and `creation.reset` for this delivery unit in addition to the three combat and seven service adapters and no unrelated gameplay adapter. `creation.preset` SHALL accept exactly `preset_key` (a 1..64-character non-empty string that exists in the player-preset registry). `creation.custom` SHALL accept exactly `display_name` (1..64 characters), `age` and `apparent_age` (integers in 0..10000 excluding booleans; the deterministic creation service independently enforces the adult minimum on every submission), `race` (a 1..64-character registry key), `subrace` (a 1..64-character registry key belonging to the race; the deterministic service rejects a missing or incompatible subrace), `allocations` (an object containing exactly `hp`, `mp`, `sp`, `atk_phys`, `agility`, and `defense`, each an integer in 0..10000 excluding booleans), and an optional `background` (a string of at most the declared persona-field bound; a missing value is treated as an empty background). `creation.concept` SHALL accept exactly `concept` (a non-empty string of at most the declared bound), SHALL run the guarded `character_creation` generative layer with the injected client, and SHALL call the deterministic concept-apply service to save the `concept_filled` draft (including its server-owned persona block). `creation.activate` and `creation.reset` SHALL each accept exactly an empty payload. Every adapter SHALL obtain the account from the authenticated session's puppet, SHALL reject any actor/account/session/puppet/calculated-stat/unknown field, SHALL validate through the existing deterministic creation service (`preflight_character_creation`, `activate_player_character`, and the creation-wizard draft service), and SHALL NOT assign `.db`, traits, identity attributes, or `creation_pending` directly. No action SHALL route an action ID or payload through the text command parser.

#### Scenario: Preset selection reaches the deterministic registry
- **WHEN** a pending character submits `creation.preset` with a shipped preset key
- **THEN** the adapter validates the key against the immutable preset registry, saves the `preset_selected` draft, and refreshes the `creation` panel

#### Scenario: Preset selection is a two-step confirmation in the browser
- **WHEN** a browser player chooses a preset card and then confirms it
- **THEN** the flow submits `creation.preset` with the preset key and then `creation.activate`, sharing the same deterministic activation service the `character preset <key>` command uses while keeping the browser confirmation step explicit

#### Scenario: Custom submission runs the existing preflight
- **WHEN** a pending character submits `creation.custom` with a complete valid custom request including a registered subrace and an optional bounded background
- **THEN** the adapter builds the request and validates it through `preflight_character_creation`, saves the `custom_filled` draft, and reports success

#### Scenario: A missing or incompatible subrace is rejected before activation
- **WHEN** a client submits `creation.custom` with no `subrace`, an empty `subrace`, or a subrace key that does not belong to the submitted race
- **THEN** the deterministic service rejects with a stable reason and no draft, trait, or identity value changes

#### Scenario: An overlong display name is rejected before the deterministic service
- **WHEN** a client submits `creation.custom` with a `display_name` longer than 64 characters
- **THEN** the adapter rejects it structurally without invoking the deterministic service

#### Scenario: An over-bound background is rejected
- **WHEN** a client submits `creation.custom` with a `background` longer than the declared persona-field bound
- **THEN** the adapter or deterministic service rejects it before activation and the character remains pending

#### Scenario: A concept submission fills the draft through the guarded pipeline
- **WHEN** a pending character submits `creation.concept` with a bounded concept and the guarded layer returns a valid proposal with a matching draft fingerprint
- **THEN** the adapter validates the proposal deterministically, saves the `concept_filled` draft including the server-owned persona block, and refreshes the `creation` panel with pre-filled finite controls and the background-generated indicator

#### Scenario: An abnormal puppet cannot reach a write path
- **WHEN** an adapter is dispatched with a puppet that has no accessible owning account, is not a `PlayerCharacter`, or is not in `account.characters`
- **THEN** the adapter rejects with a stable ownership/creation reason before any deterministic write and no draft, trait, or identity value changes

#### Scenario: An unknown field cannot sneak past activation
- **WHEN** a client submits any creation action carrying an actor, account, session, persona prose, skill, equipment, magic-level, or calculated-stat field
- **THEN** exact-schema validation rejects the request without invoking the adapter or the deterministic service

#### Scenario: A skipped or incomplete draft cannot activate
- **WHEN** `creation.activate` is submitted while no valid draft exists or the draft stage is incomplete
- **THEN** the adapter rejects before `activate_player_character`, the character remains pending, and no trait or identity is written

### Requirement: The creation dock is keyboard-first, form-capable, and confirmation-protected
In `creation` mode the action dock SHALL present preset cards and the custom form rather than exploration or service menus. Arrow keys SHALL navigate finite lists and buttons, Tab and Shift+Tab SHALL move focus through text/numeric fields, Enter SHALL activate the focused control or submit a complete server-declared form, and Escape SHALL pop exactly one menu level without discarding the saved server wizard draft. The custom form SHALL require a subrace selection (no "無子種族" radio is rendered), SHALL display an allocation briefing (total budget, six-axis count, each axis's 0–span, and the sum-must-equal-budget rule) above the allocation fields, and SHALL provide a bounded optional background text field. The form action buttons (confirm, reset, cancel, and concept-apply) SHALL be operable by pointer through the shared focus/disabled/submission gate as well as by keyboard, and SHALL claim every keydown while the form owns focus so no unclaimed keydown reaches the stock plugin handler. The final activation and the destructive custom reset SHALL each require an explicit confirmation panel. Disabled entries SHALL remain focusable with their explanation and SHALL submit nothing. Validation messages SHALL be associated with the field they concern and announced through the accessible live region. A stale revision SHALL preserve typed unsent values locally where safe, refresh server-declared choices, and ask the player to review rather than automatically resubmitting. No canonical service or creation state SHALL be stored in localStorage.

#### Scenario: Custom form completes without typed commands
- **WHEN** a player uses arrows and Tab/Shift+Tab to choose race and subrace, reviews the allocation briefing, types name, ages, allocations, and an optional background into the fields, confirms, and activates
- **THEN** the flow submits exactly `creation.custom` once with the expected payload (including the required subrace and any background), then `creation.activate` once, and the exploration snapshot follows

#### Scenario: The custom form cannot submit without a subrace
- **WHEN** a player leaves the subrace unselected in the custom form and confirms
- **THEN** the form reports the missing subrace against the subrace field and sends no `creation.custom` mutation

#### Scenario: The allocation briefing renders before the fields
- **WHEN** the custom form renders race and subrace with a resolvable profile
- **THEN** it displays the profile budget, the six-axis count, each axis's 0–span range, and the rule that the total must equal the budget above the allocation inputs

#### Scenario: Form action buttons respond to pointer clicks
- **WHEN** a player clicks the confirm, reset, cancel, or concept-apply button with the pointer
- **THEN** the button runs the identical action the keyboard Enter would run, obeying the shared disabled/in-flight/awaiting-revision gate, and no "NO plugin handled this Keydown" is logged for clicks or for keys the form owns

#### Scenario: The form claims its keys without breaking native input
- **WHEN** a player types or presses Tab, modifier, or IME-composition keys while the custom form owns focus
- **THEN** native focus movement, text input, and Chinese IME continue to work (no `preventDefault` on those keys), the keys are claimed at the router layer so no "NO plugin handled this Keydown" is logged, and a held or repeated Enter submits at most once

#### Scenario: A pointer click and a keyboard Enter cannot double-submit
- **WHEN** a player activates a form button by pointer while the same button also receives a keyboard-synthesized Enter
- **THEN** exactly one `creation.*` mutation is emitted per deliberate activation, with the in-flight / awaiting-revision gate and the pointer bridge's primary-single-activation check suppressing the duplicate

#### Scenario: Activation and reset require confirmation
- **WHEN** the player focuses activation or the custom reset but has not confirmed
- **THEN** no mutation is sent and Escape returns exactly one menu level without activating or clearing the draft

#### Scenario: Escape preserves the saved draft
- **WHEN** the player backs out of a submenu or form step after a draft was saved
- **THEN** the saved server draft remains intact and reconnecting or returning renders the same stage

#### Scenario: Stale revision reviews before resubmitting
- **WHEN** a stale `creation.custom` is detected while the player still has typed but unsent values
- **THEN** the browser preserves those values locally, refreshes the server-declared choices, and asks the player to review instead of automatically resubmitting
