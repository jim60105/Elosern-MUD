# Spec Delta

## MODIFIED Requirements

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
- **THEN** practice sends exactly one `explore.practice` booking intent `{actor_id, skill}` for the book's member and shows the booking feedback, and the passive row offers no casting mutation

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
- **THEN** practice is a single booking control with its own payload, feedback and shared submission lock independently of casting, and it opens no duration sub-screen
