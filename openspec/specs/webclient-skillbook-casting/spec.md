## Purpose

Provide authoritative graphical skill use from SkillBook through the existing field settlement and combat-initiation rules, with accessible target selection, truthful availability and a verified redesigned browsing surface.

## Requirements

### Requirement: Skill use has an exact on-demand versioned read model

The production OOB registry SHALL expose `skill_use` at schema version 1. Its available form SHALL contain exactly `schema_version`, `available: true`, `kind: "skill_use"`, `skill`, and the selected numeric `scale`. `skill` SHALL contain exactly `key`, `label`, `description`, `target_spec`, `usable_out_of_combat`, `cost`, `enabled`, `disabled_reason`, `targets`, `openings`, and optional `freeform_scales`.

#### Scenario: Selected preview is a read-only bounded replacement
- **WHEN** an owned active skill is selected for field use
- **THEN** the browser receives one complete version-1 `skill_use` replacement with canonical costs, targets, opening consequences and availability, and no trait, resource, proficiency, session or clock state changes

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

### Requirement: Preview selection is session-scoped and never executes gameplay

`explore.skill_preview` SHALL accept exactly required `skill_key` (1..64 characters under the existing skill-key validator) and optional `scale` from the existing numeric closed scale set, defaulting to 1.0. It SHALL publish a freshly computed `skill_use` panel before its result and SHALL perform no roll, cast, practice award, world-clock creation/advance or combat creation.

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
- **THEN** it MAY select only the skill/scale pair in ephemeral presentation state, only an owned registered active skill is selectable, and a disabled but owned active skill is still inspectable

#### Scenario: Invalid preview keys reject safely
- **WHEN** an unowned, unknown or passive key, an invalid mode or a missing presentation session is submitted
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

### Requirement: Field previews share existing deterministic target and scale rules

Field previews SHALL be side-effect-free and apply the same field permission, ownership/active kind, lineage entitlement, adjusted resources, action capability, effect-handler/context, timing, target shape, presence, alive, range and faction checks as current submission.

#### Scenario: Preview does not reject a valid damage opening under a room-only context
- **WHEN** an owned field-permitted damaging SINGLE skill can open combat against a present living monster
- **THEN** its monster opening uses candidate-combat validation and is enabled when current initiation would succeed, without creating a combat record

#### Scenario: Lower allowed scale becomes affordable
- **WHEN** an entitled synthetic field-eligible scalable skill is unaffordable at 1 but affordable at an advertised lower rung
- **THEN** selecting that rung publishes its adjusted cost and legal choices and permits the ordinary final confirmation without changing the scale entitlement rules

#### Scenario: Non-entitled skill exposes no scaling feature
- **WHEN** a skill is ineligible for scaling or the actor lacks its current mastery entitlement
- **THEN** the panel omits `freeform_scales`, the browser renders no scale control/hint, and a forged scaled submission is rejected by existing deterministic gates

#### Scenario: Ordinary candidates keep room targeting
- **WHEN** a preview lists ordinary candidates
- **THEN** it uses existing room targeting with no invented enemy/ally restriction

#### Scenario: Monster openings reuse the initiation preflight
- **WHEN** a preview offers a living co-located monster opening
- **THEN** it uses the same unpersisted candidate battlefield, explicit field-availability gate and preflight as actual initiation

#### Scenario: Missing context disables rather than fabricates
- **WHEN** required effect context is missing
- **THEN** the choice is disabled and never fabricated

#### Scenario: Target specs present their server-authoritative shape
- **WHEN** a preview covers each target spec
- **THEN** NONE exposes no targets, SELF displays the authenticated actor binding, and SINGLE/AREA offer server identities and disabled reasons

#### Scenario: Monster openings stay separate rows
- **WHEN** a preview lists living monster openings alongside ordinary candidates
- **THEN** the monster openings remain separate from ordinary candidates

#### Scenario: Scale choices follow the entitlement and reorder availability
- **WHEN** a skill's existing entitlement advertises `freeform_scales`
- **THEN** scale choices appear in ascending canonical order with server costs and availability is recomputed at the selected allowed scale, and otherwise no selector or scaling hint appears

### Requirement: Field cast payloads express one authoritative target shape

`explore.cast` SHALL accept required `skill_key`, optional bounded `scale` defaulting to 1.0, and at most one of `target_ids` or `opening_target_id`. IDs SHALL be positive JavaScript-safe integers excluding booleans; `target_ids` SHALL be a nonempty unique list of at most 64 IDs. NONE/SELF SHALL submit neither target field, with SELF bound server-side to the authenticated puppet.

#### Scenario: NONE and SELF contain no target authority
- **WHEN** the player confirms a NONE cast and separately a SELF cast
- **THEN** each request carries its skill and any chosen allowed scale with neither target field nor an actor field, and SELF binds only the session puppet

#### Scenario: Ordinary AREA uses explicit unique identities
- **WHEN** the player toggles two permitted non-monster candidates and confirms
- **THEN** one `explore.cast` carries their two identities in presenter order, no shorthand and no opening anchor, and both follow existing AREA resolution

#### Scenario: Monster AREA uses an anchor rather than a guessed subset
- **WHEN** the player confirms an advertised AREA monster opening
- **THEN** one request carries the anchor identity only, and the server determines the current complete monster line-up

#### Scenario: Tampered shape cannot execute
- **WHEN** a request includes both target forms, duplicate IDs, a shorthand, a boolean scale or an actor override
- **THEN** it receives `malformed_payload`, no adapter executes and no game state changes

#### Scenario: Ordinary SINGLE and AREA submit server-provided identities
- **WHEN** an ordinary SINGLE or ordinary AREA cast is confirmed
- **THEN** SINGLE submits exactly one server-provided ID and AREA submits distinct selected ordinary IDs in presenter order

#### Scenario: Monster openings submit only an anchor
- **WHEN** a monster-opening SINGLE or AREA cast is confirmed
- **THEN** it submits exactly one server-provided `opening_target_id`, never a browser-expanded roster

#### Scenario: Malformed or unauthorized payloads reject without adapter invocation
- **WHEN** a payload carries actor/context/cost fields, unknown fields, shorthands, simultaneous target forms, duplicate or empty IDs or malformed scale values
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

### Requirement: Field submissions revalidate and preserve deterministic routing

After existing dispatcher stale/duplicate checks, `explore.cast` SHALL reject current non-exploration mode or an active combat session, re-resolve referenced identities only from the actor's current accessible co-located candidates, and repeat current domain checks immediately before mutation. It SHALL NOT trust preview labels or globally accept remote/hidden entities.

#### Scenario: Current revision does not protect a vanished target
- **WHEN** a matching-revision SINGLE request arrives after its target moved away or died
- **THEN** current re-resolution/validation rejects it with a safe stable reason and no resource, roll, clock or combat change

#### Scenario: Field mode cannot bypass an active session
- **WHEN** combat began after the field preview and a modified client submits `explore.cast`
- **THEN** the field action rejects without submitting a combat round or settling a field cast

#### Scenario: Damage aimed elsewhere spends nothing
- **WHEN** a damaging field skill is submitted with no target, the actor or a non-monster target
- **THEN** the action rejects with the existing damage-requires-monster-target reason before spending resources or accessing/advancing the world clock

#### Scenario: Healing a monster still starts combat
- **WHEN** an enabled field-permitted healing skill targets a living co-located monster anchor
- **THEN** combat starts with that healing cast as the opening action under the existing rules

#### Scenario: AREA opening rechecks room occupants
- **WHEN** a living room monster set changes between preview and an admitted AREA opening whose anchor remains valid
- **THEN** the server revalidates and engages the current deterministic living monster set, and the committed view reports that actual set without using a stale client-expanded list

#### Scenario: Current ownership and context override a prior enabled row
- **WHEN** a formerly enabled skill loses ownership, field permission, scale entitlement, resources or required effect context before submission
- **THEN** current domain validation rejects before mutation with the corresponding stable reason

#### Scenario: Ordinary lists cannot smuggle a monster
- **WHEN** an ordinary browser target list contains a living co-located monster
- **THEN** it rejects before field settlement, because monster use requires the explicit anchor

#### Scenario: Any permitted effect on a monster anchor starts combat
- **WHEN** a living co-located monster anchor receives any permitted skill effect, including healing or support
- **THEN** combat initiates

#### Scenario: Anchor engagement follows the skill shape
- **WHEN** an admitted monster opening resolves
- **THEN** SINGLE engages the anchor alone and AREA engages all current living room monsters in deterministic order

#### Scenario: Damage without an opening never touches state
- **WHEN** a damaging cast arrives without a valid monster opening
- **THEN** it rejects before resource, roll, session or clock access

#### Scenario: Non-damaging ordinary casts settle in the field
- **WHEN** a non-damaging ordinary NONE/SELF/SINGLE/AREA cast is admitted
- **THEN** it uses existing field settlement

#### Scenario: AREA filtering keeps its shipped semantics
- **WHEN** safely re-resolved AREA candidates are filtered
- **THEN** existing AREA candidate filtering remains unchanged, including rejection when none survive, and an identity that cannot be safely re-resolved rejects

#### Scenario: Nothing is broadened
- **WHEN** field submissions are validated
- **THEN** no field permission, effect-context or target rule is broadened

### Requirement: Cast settlement is atomic and publishes the complete committed view

Ordinary field casts SHALL atomically settle effects, resources, proficiency and every existing settlement side effect with exactly one COMMAND-time advance on success. Monster openings SHALL atomically settle engagement and opening action through the existing field-initiation boundary, accumulating COMBAT time and never additionally charging COMMAND time.

#### Scenario: Utility casting charges time and resources once
- **WHEN** a valid non-damaging field cast commits
- **THEN** effects, resource spend, proficiency and reported command time are committed together, refreshed character/status/other affected panels agree at one revision and output appears only after commit

#### Scenario: Failure restores cache and persistence
- **WHEN** field time advancement or monster opening fails after resolution began
- **THEN** the inherited settlement boundary restores all touched durable/cache surfaces and any engagement registration, and no success output or session remains from the failed action

#### Scenario: Ordinary initiation hands over once
- **WHEN** a field cast commits a nonterminal opening round
- **THEN** one snapshot shows combat mode, current session/participants/status/art/choices and its round record, ordinary narrative output is shown once, and subsequent actions use the existing combat dock

#### Scenario: Instant terminal opening has no stale combat view
- **WHEN** the opening cast ends the encounter immediately
- **THEN** the full snapshot shows settled exploration, clock, resources, monster removal and aftermath-related panels without a fabricated transient combat mode or separate command-time charge

#### Scenario: Duplicate request does not repeat settlement or output
- **WHEN** the same live request ID is delivered twice
- **THEN** the cast, time/resource cost and EventLog output execute once, and the duplicate receives the cached result

#### Scenario: Rejection is inert and exceptions reuse the rollback boundary
- **WHEN** a cast is rejected, or an exception occurs mid-settlement
- **THEN** rejection changes none of the settlement surfaces, and exceptions retain existing durable rollback, Evennia cache restoration and skip-safety cleanup

#### Scenario: Narrative output waits for commit
- **WHEN** EventLogs, notifications or outcomes are produced by a cast
- **THEN** they render only after commit through existing safe offline-capable output

#### Scenario: Every admitted completion publishes the full snapshot first
- **WHEN** an admitted `explore.cast` completes
- **THEN** a full canonical snapshot is published before its matching result, including all mode-relevant panels and any ordinary opening-round record through `combat_beats`

#### Scenario: The browser unlocks only at the declared revision
- **WHEN** the browser awaits a cast completion
- **THEN** it waits for the declared revision before unlocking

#### Scenario: Opening prose pages ordinarily
- **WHEN** field opening prose renders
- **THEN** it uses ordinary narrative paging without adding a new beat-autoplay trigger, and existing combat action playback remains unchanged

#### Scenario: Initiation shows its committed mode directly
- **WHEN** an initiation commits
- **THEN** a nonterminal initiation shows committed combat controls and a terminal initiation shows committed exploration/aftermath directly

### Requirement: SkillBook use shares one keyboard owner and preserves practice

SkillBook SHALL offer discoverable active-skill use without typing keys. In exploration, use SHALL obtain the authoritative preview and transfer target/scale/final-confirmation control to the existing action-dock navigation owner, closing the modal book before the dock becomes interactive. No drawer-hosted dock renderer, parallel router/focus model or new exploration root entry SHALL be introduced.

#### Scenario: Opening and cancelling use executes no skill
- **WHEN** a keyboard-only player opens use, navigates targets and cancels back to the book
- **THEN** only read-only preview requests may have been sent, no `explore.cast` or text command is emitted, and focus returns to a valid invoking row without a second focus owner

#### Scenario: Combat book use reuses the combat entry
- **WHEN** SkillBook use is activated during an existing combat session
- **THEN** the book closes, the existing combat Skills entry receives focus, and no `explore.skill_preview`, `explore.cast` or automatic `combat.cast` is emitted

#### Scenario: Post-handoff combat selection uses combat descriptors
- **WHEN** combat selection continues after book use handed off to the combat Skills entry
- **THEN** subsequent combat selection uses current combat descriptors

#### Scenario: Practice and passive inspection retain their behavior
- **WHEN** the player practices an active skill and then browses a passive skill
- **THEN** practice sends exactly its existing bounded `explore.practice` intent with unchanged feedback, and the passive row offers no casting mutation

#### Scenario: Keys drive the dock's real choices
- **WHEN** the keyboard player navigates the field-use flow
- **THEN** arrows navigate real choices, Enter confirms, Space toggles ordinary AREA selection, and Escape/back cancels one selection level without casting and ultimately returns to the book with the invoking skill focus restored if still valid

#### Scenario: NONE and SELF confirm explicitly
- **WHEN** a NONE or SELF cast is at the confirmation step
- **THEN** explicit final confirmation is required

#### Scenario: Non-exploration modes never enable field use
- **WHEN** book use is activated outside exploration
- **THEN** other modes do not enable field use, and passive/unknown rows remain read-only for casting

#### Scenario: Practice keeps its own bounded surface
- **WHEN** casting and practice coexist in the book
- **THEN** practice keeps its existing bounded drawer sub-screen, payload, feedback and shared submission lock independently of casting

### Requirement: SkillBook redesign is apply-owned and availability is truthful

Before UI implementation, the apply worker SHALL read the game-ui-design and ui skills and `web/webclient-app/AGENTS.md`, and record the concrete visual/interaction design. This proposal SHALL NOT prescribe a mockup, layout, styling or component composition.

#### Scenario: Badge cannot imply combat-only or current permission
- **WHEN** a field-permitted skill is currently disabled and an otherwise similar skill is not field-permitted
- **THEN** the book distinguishes capability from present availability in Traditional Chinese, shows no misleading `combat` badge and offers no enabled field confirmation for either disabled case

#### Scenario: Concrete design is verified in the live client
- **WHEN** the redesigned SkillBook and casting flow render under `.elosern-root` at 1451x790 and 2560x1440
- **THEN** the apply worker records live browser evidence of readable use/practice/detail hierarchy, visible focus and disabled reasons, reachable long content, bounded non-overlapping controls and reduced-motion behavior, rather than relying on Storybook alone

#### Scenario: The recorded design improves while retaining the shipped browsing surface
- **WHEN** the concrete visual/interaction design is recorded
- **THEN** it improves information hierarchy, readable skill detail, discoverability of use and its distinction from practice while retaining active/passive browsing, bounded search, authored category/group ordering, empty/unavailable states, shared opaque drawer/header, no book art column and existing desktop/reduced-motion constraints

#### Scenario: Field availability is worded truthfully in Traditional Chinese
- **WHEN** `usable_out_of_combat: true` is presented
- **THEN** it uses truthful player-facing Traditional Chinese wording such as `可於戰鬥外使用`, or an equally unambiguous affordance, never the literal `combat` badge

#### Scenario: Permission never implies current availability
- **WHEN** availability is conveyed
- **THEN** static permission does not imply current availability, and authoritative disabled reasons and monster-opening consequences are readable and not conveyed by color alone

#### Scenario: Controls are accessible and content reachable
- **WHEN** the redesigned book renders its controls and content
- **THEN** every control has an accessible name and visible focus, and long lists/details remain reachable without clipping actionable content

#### Scenario: Player docs describe graphical use without changing mechanics
- **WHEN** relevant player docs are updated
- **THEN** they describe graphical use, targeting/scales/cancellation and monster initiation without changing text cast syntax or field mechanics

### Requirement: Skill-use lifecycle and acceptance cover canonical recovery

Cast selection SHALL be local until final submission. Transport loss, new epoch/puppet or invalidating mode transition SHALL clear the field flow and prevent stale confirmation. Reconnect SHALL adopt canonical persistence without restoring selection as authorization or automatically resubmitting a cast; an uncertain result SHALL use the existing notice.

#### Scenario: Duplicate names retain distinct targets
- **WHEN** two accessible co-located entities share a display name and the player selects one
- **THEN** the request uses that entity's server identity and only the selected identity is acted on according to the skill shape, with no name-to-key guessing

#### Scenario: Reconnect never retries an uncertain cast
- **WHEN** transport is lost after cast submission but before its result
- **THEN** reconnect shows the canonical settled state and uncertain-outcome notice, clears prior target selection and sends no replacement cast

#### Scenario: New panel invalidates a selection
- **WHEN** a committed preview replacement removes a selected target or scale entitlement
- **THEN** local selection/confirmation is reconciled or cancelled, focus has a valid deterministic destination and no stale confirmation is dispatched

#### Scenario: Offline browser acceptance completes
- **WHEN** focused managed Chromium journeys run at both supported acceptance viewports with AI/image services unavailable
- **THEN** the complete cast and practice matrix remains playable through authoritative OOB menus and deterministic text fallback, with no remote service request

#### Scenario: Panel replacement reconciles local selection
- **WHEN** a panel replacement arrives
- **THEN** it removes vanished targets and invalidates disallowed scale/skill confirmations

#### Scenario: Acceptance fixtures are synthetic and journeys isolated
- **WHEN** acceptance is assembled
- **THEN** it uses synthetic deterministic fixtures and isolated localhost browser journeys with external services unavailable

#### Scenario: The acceptance matrix is complete
- **WHEN** acceptance coverage is enumerated
- **THEN** it covers all four target specs, ordinary AREA and monster AREA, entitled and absent scales, identity ambiguity, cancellation, disabled/stale/tampered/duplicate handling, practice, active-combat handoff, terminal/nonterminal refresh and reconnect

#### Scenario: Tests are traceable and shard-owned
- **WHEN** acceptance tests are registered
- **THEN** they are traceable to the synchronized canonical requirements and registered with exact shard ownership under the repository rules
