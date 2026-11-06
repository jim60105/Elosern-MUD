## MODIFIED Requirements

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
  bounded text fields) accepted only through the custom-save payload, and the accepted `sex`

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
