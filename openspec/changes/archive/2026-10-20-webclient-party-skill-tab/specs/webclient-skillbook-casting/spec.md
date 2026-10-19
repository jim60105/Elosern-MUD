# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: SkillBook use shares one keyboard owner and preserves practice`
- TO: `### Requirement: Skill tab use shares one keyboard owner and preserves practice`
- FROM: `### Requirement: SkillBook redesign is apply-owned and availability is truthful`
- TO: `### Requirement: The skill tab follows the approved prototype and availability is truthful`

## MODIFIED Requirements

### Requirement: Skill tab use shares one keyboard owner and preserves practice

The party window's 技能 tab SHALL offer discoverable active-skill use by the viewed member without typing keys. In exploration, 施放 SHALL obtain the authoritative preview for the viewed member and transfer target/scale/final-confirmation control to the existing action-dock navigation owner, closing the party window before the dock becomes interactive. No drawer-hosted dock renderer, parallel router/focus model or new exploration root entry SHALL be introduced.

#### Scenario: Opening and cancelling use executes no skill
- **WHEN** a keyboard-only player opens use, navigates targets and cancels back to the 技能 tab
- **THEN** only read-only preview requests may have been sent, no `explore.cast` or text command is emitted, and focus returns to a valid invoking row without a second focus owner

#### Scenario: Combat book use reuses the combat entry
- **WHEN** the 技能 tab is open during an existing combat session
- **THEN** 施放 and 排入修煉 are disabled with their committed reasons, and no `explore.skill_preview`, `explore.cast`, `explore.practice` or automatic combat command is emitted; combat casting stays on the command card

#### Scenario: Post-handoff combat selection uses combat descriptors
- **WHEN** combat selection continues on the command card
- **THEN** subsequent combat selection uses current combat descriptors

#### Scenario: Practice and passive inspection retain their behavior
- **WHEN** the player practices an active skill and then browses a passive skill
- **THEN** practice sends exactly one `explore.practice` booking intent `{actor_id, skill}` for the viewed member and shows the booking feedback, and the passive row offers no casting mutation

#### Scenario: Keys drive the dock's real choices
- **WHEN** the keyboard player navigates the field-use flow
- **THEN** arrows navigate real choices, Enter confirms, Space toggles ordinary AREA selection, and Escape/back cancels one selection level without casting and ultimately returns to the 技能 tab with the invoking skill focus restored if still valid

#### Scenario: NONE and SELF confirm explicitly
- **WHEN** a NONE or SELF cast is at the confirmation step
- **THEN** explicit final confirmation is required

#### Scenario: Non-exploration modes never enable field use
- **WHEN** 施放 is activated outside exploration
- **THEN** other modes do not enable field use, and passive/unknown rows remain read-only for casting

#### Scenario: Practice keeps its own bounded surface
- **WHEN** casting and practice coexist in the 技能 tab
- **THEN** practice is a single booking control with its own payload, feedback and shared submission lock independently of casting, and it opens no duration sub-screen

### Requirement: The skill tab follows the approved prototype and availability is truthful

The 技能 tab SHALL follow the approved party member management prototype (`docs/design/party-member-management/tabs/SkillTab.vue`) for layout and styling, and SHALL convey field capability and current availability truthfully.

#### Scenario: Badge cannot imply combat-only or current permission
- **WHEN** a field-permitted skill is currently disabled and an otherwise similar skill is not field-permitted
- **THEN** the tab distinguishes capability from present availability in Traditional Chinese, shows no misleading `combat` badge and offers no enabled field confirmation for either disabled case

#### Scenario: Concrete design is verified in the live client
- **WHEN** the 技能 tab and casting flow render under `.elosern-root` at 1451x790 and 2560x1440
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
- **WHEN** the 技能 tab renders its controls and content
- **THEN** every control has an accessible name and visible focus, and long lists/details remain reachable without clipping actionable content

#### Scenario: Player docs describe graphical use without changing mechanics
- **WHEN** relevant player docs are updated
- **THEN** they describe graphical use, targeting/scales/cancellation and monster initiation without changing text cast syntax or field mechanics
