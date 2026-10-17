# Spec Delta

## MODIFIED Requirements

### Requirement: Skill use has an exact on-demand versioned read model

The production OOB registry SHALL expose `skill_use` at schema version 2. Its available form SHALL contain exactly `schema_version`, `available: true`, `kind: "skill_use"`, `actor_id` (the selected caster member), `skill`, and the selected numeric `scale`; costs, targets, openings and availability SHALL be computed for that caster. `skill` SHALL contain exactly `key`, `label`, `description`, `target_spec`, `usable_out_of_combat`, `cost`, `enabled`, `disabled_reason`, `targets`, `openings`, and optional `freeform_scales`.

#### Scenario: Selected preview is a read-only bounded replacement
- **WHEN** an owned active skill is selected for field use
- **THEN** the browser receives one complete version-2 `skill_use` replacement with canonical costs, targets, opening consequences and availability, and no trait, resource, proficiency, session or clock state changes

#### Scenario: Malformed or excessive preview fails safely
- **WHEN** a panel includes an unknown field, wrong version, duplicate identity, dangling opening target reference, more than 64 candidates or an over-budget full envelope
- **THEN** server or mirrored client validation rejects it without silently truncating or authorizing any cast, and the bounded recovery/unavailable path preserves ordinary text play

#### Scenario: Permitted field skill is not currently available
- **WHEN** `usable_out_of_combat` is true but current resources or action capability prevent every confirmation
- **THEN** the preview remains readable with `enabled: false` and the authoritative disabled reason

#### Scenario: Nested definitions are reused and cost is server-adjusted
- **WHEN** the panel's skill, cost and scale fields are constructed
- **THEN** existing bounded skill-key, metadata, resource-cost and freeform-scale definitions are reused, and `cost` is the server-computed adjusted cost at the selected scale

#### Scenario: Target and opening entries are exactly shaped
- **WHEN** targets or openings appear in the panel
- **THEN** each target contains exactly `identity`, `label`, `enabled`, and nullable `disabled_reason`, and each opening additionally contains exactly `target_ids`

#### Scenario: Identities, labels and disabled reasons are bounded
- **WHEN** target identities, labels or disabled reasons are published
- **THEN** identities are positive JavaScript-safe integers excluding booleans, labels are 1..128 characters, and disabled reasons are bounded stable code and Traditional Chinese message objects, required when disabled and null when enabled

#### Scenario: Entry lists are unique and capped without truncation
- **WHEN** lists of targets, openings or opening target IDs are published
- **THEN** each list has unique identities and at most 64 entries, without truncation

#### Scenario: Enabled means a legal confirmation exists
- **WHEN** the panel reports a skill's enabled state at a scale
- **THEN** that state represents the existence of a legal confirmation at that scale, not merely static field permission

#### Scenario: Both sides validate the full envelope
- **WHEN** server or browser handles a `skill_use` panel
- **THEN** it validates exact forms, registered versions, cross-references and the complete envelope's existing byte/depth/global bounds

#### Scenario: Selection or presenter failures use the common unavailable form
- **WHEN** selection is missing, mode is invalid, data is unavailable or the presenter fails
- **THEN** the common unavailable form is used without suppressing other panels or text access

#### Scenario: A companion preview is computed for the companion
- **WHEN** the selection names companion 艾拉 and 治癒之光
- **THEN** `actor_id` is 艾拉's id, `cost` reflects 艾拉's adjusted cost, `enabled` reflects 艾拉's MP, the candidates include 艾拉 herself, and `openings` lists the co-located monster openings validated for 艾拉 as initiator under the commander's party

### Requirement: Preview selection is session-scoped and never executes gameplay

`explore.skill_preview` SHALL accept exactly required `actor_id` (a positive safe-integer party member id reauthorized for the acting purpose), required `skill_key` (1..64 characters under the existing skill-key validator) and optional `scale` from the existing numeric closed scale set, defaulting to 1.0. It SHALL publish a freshly computed `skill_use` panel before its result and SHALL perform no roll, cast, practice award, world-clock creation/advance or combat creation.

#### Scenario: Inspecting a disabled skill spends nothing
- **WHEN** a player selects an owned active skill that cannot currently execute
- **THEN** selection succeeds as presentation work, its reason is readable, and resources, tick, proficiency and combat persistence remain unchanged

#### Scenario: One session cannot change another preview
- **WHEN** one live session selects a skill while another session or puppet has a different selection
- **THEN** only the requesting presentation sequence changes, and a new epoch starts without adopting the prior selection

#### Scenario: Pending scale selection cannot confirm an old preview
- **WHEN** the player selects another allowed scale and its preview result revision is not yet accepted
- **THEN** cast confirmation remains locked and the old cost/target preview cannot be submitted as the new choice

#### Scenario: Preview rides existing session and request checks
- **WHEN** a preview request is processed
- **THEN** it uses the authenticated session actor and the existing epoch, revision, serialization and duplicate-request checks

#### Scenario: Selection is ephemeral and ownership-gated
- **WHEN** the player is in exploration with no active combat session
- **THEN** it MAY select only the actor/skill/scale triple in ephemeral presentation state, only an active skill registered and owned by that actor is selectable, and a disabled but owned active skill is still inspectable

#### Scenario: Invalid preview keys reject safely
- **WHEN** an unowned, unknown or passive key, a forged or absent `actor_id`, an invalid mode or a missing presentation session is submitted
- **THEN** a safe bounded rejection is returned

#### Scenario: Selection lifetime ends with the session
- **WHEN** a reconnect, unpuppet or puppet/epoch replacement occurs
- **THEN** the presentation selection is retired

#### Scenario: Presenters see only copied selection
- **WHEN** presenters publish preview state
- **THEN** they receive only copied presentation selection through read context and recompute current permission on every publication

#### Scenario: A prior preview is never an authorization
- **WHEN** a cast is submitted after an earlier preview
- **THEN** the prior preview never authorizes the later cast

### Requirement: Field cast payloads express one authoritative target shape

`explore.cast` SHALL accept required `actor_id` (the caster member), required `skill_key`, optional bounded `scale` defaulting to 1.0, and at most one of `target_ids` or `opening_target_id`. IDs SHALL be positive JavaScript-safe integers excluding booleans; `target_ids` SHALL be a nonempty unique list of at most 64 IDs. NONE/SELF SHALL submit neither target field, with SELF bound server-side to the reauthorized caster.

#### Scenario: NONE and SELF contain no target authority
- **WHEN** the player confirms a NONE cast and separately a SELF cast
- **THEN** each request carries its caster `actor_id`, its skill and any chosen allowed scale with neither target field, and SELF binds only the reauthorized caster

#### Scenario: Ordinary AREA uses explicit unique identities
- **WHEN** the player toggles two permitted non-monster candidates and confirms
- **THEN** one `explore.cast` carries their two identities in presenter order, no shorthand and no opening anchor, and both follow existing AREA resolution

#### Scenario: Monster AREA uses an anchor rather than a guessed subset
- **WHEN** the player confirms an advertised AREA monster opening
- **THEN** one request carries the anchor identity only, and the server determines the current complete monster line-up

#### Scenario: Tampered shape cannot execute
- **WHEN** a request includes both target forms, duplicate IDs, a shorthand, a boolean scale, a missing `actor_id` or an unknown identity field
- **THEN** it receives `malformed_payload`, no adapter executes and no game state changes

#### Scenario: Ordinary SINGLE and AREA submit server-provided identities
- **WHEN** an ordinary SINGLE or ordinary AREA cast is confirmed
- **THEN** SINGLE submits exactly one server-provided ID and AREA submits distinct selected ordinary IDs in presenter order

#### Scenario: Monster openings submit only an anchor
- **WHEN** a monster-opening SINGLE or AREA cast is confirmed
- **THEN** it submits exactly one server-provided `opening_target_id`, never a browser-expanded roster

#### Scenario: Malformed or unauthorized payloads reject without adapter invocation
- **WHEN** a payload carries context/cost fields, unknown fields, shorthands, simultaneous target forms, duplicate or empty IDs, a non-integer `actor_id` or malformed scale values
- **THEN** it rejects without adapter invocation

#### Scenario: TargetSpec mismatches reject before mutation
- **WHEN** a payload's target fields mismatch its TargetSpec-dependent rules
- **THEN** it rejects before mutation

#### Scenario: The reserved flee skill keeps its route
- **WHEN** the reserved flee skill is used graphically
- **THEN** it retains its existing graphical route

#### Scenario: The browser is limited to allowlisted OOB actions
- **WHEN** the browser submits casting traffic
- **THEN** it sends allowlisted OOB actions only and never synthesizes or executes a text cast command

#### Scenario: A companion opening anchor opens the commander's encounter
- **WHEN** `explore.cast` names companion 艾拉 as caster with an `opening_target_id`
- **THEN** the dispatcher passes only the authenticated puppet, the rules reauthorize 艾拉, and one commander-owned session opens with 艾拉's opening draft entry

## ADDED Requirements

### Requirement: A companion's monster opening uses the same caster-bound confirmation
A preview whose caster is a companion SHALL present its monster openings as the same separate opening rows with the same explicit final opening confirmation the commander's cast uses (開戰並施放), bound to the previewed caster; confirming SHALL send exactly one `explore.cast` carrying that caster's `actor_id` and the `opening_target_id`.

#### Scenario: Confirming opens combat for the caster
- **WHEN** 艾拉 is the previewed caster of 冰錐術 and the player confirms 開戰並施放 on a monster opening
- **THEN** exactly one `explore.cast {actor_id: 艾拉, skill_key, opening_target_id}` is sent, the commander stays the authenticated puppet, and combat opens with 艾拉's cost and practice accounted once when her entry resolves

#### Scenario: Cancelling changes nothing
- **WHEN** the player cancels or presses Escape at the opening confirmation
- **THEN** no action is sent and no session, resource, practice or clock state changes

#### Scenario: A forged or stale caster is refused
- **WHEN** a confirmation arrives naming a caster that is no longer a present party member, or a forged id
- **THEN** it is rejected with `member_not_present` or `not_party_member`, no session opens, and the commander is not used in its place
