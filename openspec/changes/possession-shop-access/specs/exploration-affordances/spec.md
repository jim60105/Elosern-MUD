# Spec Delta

## REMOVED Requirements

### Requirement: The canonical affordance vocabulary is shared and read-only
**Reason**: The possessed-shop and guild-navigation scenarios are superseded by the approved decision. The CLI forbids retiring scenario names within a MODIFIED block, so this requirement is replaced as a whole with all unrelated scenarios preserved below.
**Migration**: Use the replacement shared-vocabulary requirement below and update active traceability references at spec synchronization. No runtime compatibility path or saved-data migration is needed.

## ADDED Requirements

### Requirement: The shared read-only affordance vocabulary supports possessed shop access
A shared module (`web/webclient/presentation/affordances.py`) SHALL own the canonical
affordance rules for a puppeted player in exploration mode. Every emitted entry SHALL be an
`AffordanceView` that is exactly one of two shapes: an **action entry** (action code, label,
params, freeform, navigation false, enabled, nullable disabled_reason) or a **navigation entry**
(surface, label, navigation true, enabled, nullable disabled_reason). Exact field sets and
emission rules are scenario-pinned.

#### Scenario: The exploration panel and the context form share one vocabulary
- **WHEN** the same room is presented to the same puppeted actor through both the `exploration`
  panel and the `context_actions` exploration form
- **THEN** both surfaces enumerate the same eligible targets and the same non-talk actions with
  identical ids, labels, gates, and disabled states; every target that has talk entries in the
  context form carries exactly one 交談 `explore.talk_open` affordance in the panel with the same
  enabled state and possession reason; and both serializations are unchanged before and after a
  canonical-state comparison

#### Scenario: A dead monster stays visible as a disabled entry
- **WHEN** a present Monster is dead
- **THEN** the vocabulary contains its `explore.engage` action entry with `enabled` false and a
  stable `target_dead` disabled reason, exactly as the v1 panel rendered it

#### Scenario: A navigation entry carries no dispatcher code
- **WHEN** an unpossessed actor sees a guild or shop host, or a possessed actor sees a shop host
- **THEN** the vocabulary contains a navigation entry with `surface` `"guild"`/`"shop"` as applicable,
  `navigation` true, and no `action_id` and no `params`, and no `ui_action` registry lookup exists for it

#### Scenario: Possess entries mirror the deterministic gates
- **WHEN** a bound companion stands beside the player while a combat session is active
- **THEN** the vocabulary carries that companion's `explore.possess` entry disabled with the
  combat gate's stable code, and the same entry is enabled once combat ends

#### Scenario: Release is offered exactly once, only while possessing
- **WHEN** the actor possesses a companion and the vocabulary is emitted
- **THEN** exactly one `explore.possess_release` entry is present, and no unpossessed-emission
  vocabulary contains it

#### Scenario: The possessed actor keeps engage disabled and normal shop access
- **WHEN** the puppeted actor is a possessed NPC and a live monster and an available shop host are present
- **THEN** the engage entry remains visible disabled with `possessed_engage` and its fixed message,
  while the shop navigation entry is enabled with no possession-specific disabled reason

#### Scenario: The possessed actor has no guild navigation entry
- **WHEN** the puppeted actor is a possessed NPC and a guild host is present
- **THEN** neither the exploration panel nor the context vocabulary emits a guild opener, disabled guild row, or synthetic guild refusal message

#### Scenario: Possessed shop navigation retains ordinary service gates
- **WHEN** a possessed actor is beside a merchant whose service is off-anchor or has a malformed binding
- **THEN** the shop entry carries the same disabled state and fixed service-gate message as without possession

#### Scenario: An available delivery is offered for the bound recipient
- **WHEN** the puppeted actor holds an active `DELIVER` stage bound to a co-located recipient and
  holds the objective's item
- **THEN** the vocabulary contains one `explore.deliver` action entry for that recipient, enabled,
  carrying validator-normalized params naming the recipient identity and the item key

#### Scenario: A delivery the actor cannot perform is not invented
- **WHEN** the bound recipient is co-located but the actor no longer holds the objective's item
- **THEN** the vocabulary contains that delivery entry disabled with a stable reason code and a safe
  Traditional Chinese message, and no enabled delivery entry exists

#### Scenario: No delivery entry exists without an active bound stage
- **WHEN** the actor has no active `DELIVER` stage bound to any co-located entity
- **THEN** the vocabulary contains no `explore.deliver` entry

#### Scenario: The conversation-opening code is allowlisted but never emitted
- **WHEN** the vocabulary is emitted for a room holding a scripted host and an `LLMNPC`
- **THEN** it contains the hosts' `explore.talk_scripted` and `explore.talk_freeform` entries and no
  `explore.talk_open` entry, `explore.talk_open` is a member of `ACTION_CODE_ALLOWLIST`, and it is
  absent from `SUGGESTIBLE_ACTION_IDS`

#### Scenario: The vocabulary exposes exactly two view shapes
- **WHEN** any vocabulary is serialized
- **THEN** every action entry carries exactly `action_id`, `label`, `params`, `freeform`,
  `navigation` (false), `enabled`, and nullable `disabled_reason`, with `action_id` one member of
  `ACTION_CODE_ALLOWLIST`, which contains exactly `explore.move`, `explore.look`,
  `explore.talk_open`, `explore.talk_scripted`, `explore.talk_freeform`, `explore.party_invite`,
  `explore.party_leave`, `explore.engage`, `explore.wait`, `explore.possess`,
  `explore.possess_release`, and `explore.deliver`; and every navigation entry carries exactly
  `surface` (`"guild"` or `"shop"`), `label`, `navigation` (true), `enabled`, and nullable
  `disabled_reason`, with no `action_id` and no `params`

#### Scenario: The panel's interact group is a label, not an action code
- **WHEN** the exploration panel renders its interact group
- **THEN** the vocabulary contains no `explore.interact` entry, because the group is a label over
  per-target affordances, not an action

#### Scenario: Engagement is monsters-only
- **WHEN** present NPCs, companions, and monsters are enumerated
- **THEN** no NPC or companion `explore.engage` entry exists; one engage entry is emitted once per
  present `Monster`

#### Scenario: A navigation entry is a dock surface-opener
- **WHEN** a guild or shop navigation entry is emitted
- **THEN** it is a dock surface-opener with no dispatcher action code and SHALL never be dispatched
  as a `ui_action`

#### Scenario: Move and look entries track presence
- **WHEN** exits and objects are present in the room
- **THEN** `explore.move` is emitted once per present, traversable Exit with a bounded localized
  label, and `explore.look` is emitted per present non-exit object with `{"target_id": int}`

#### Scenario: Talk entries track hosts, keywords, and NPCs
- **WHEN** a present dialogue host with a resolved `ScriptedDialogue` component and a present
  `LLMNPC` are enumerated
- **THEN** `explore.talk_scripted` is emitted once per authored keyword of the dialogue host and
  `explore.talk_freeform` once per present `LLMNPC`

#### Scenario: Party entries follow the existing binding rules
- **WHEN** party and companion bindings are enumerated
- **THEN** `explore.party_invite` follows the existing party-bound and full-party rules and
  `explore.party_leave` follows the companion-bound rule

#### Scenario: Surface navigation names only the exact local host
- **WHEN** guild and shop hosts are considered
- **THEN** guild/shop navigation entries are emitted only for the exact local host, with guild navigation omitted while possessed, and the idle baseline follows the idle-baseline requirement below

#### Scenario: Possess entries mirror the deterministic entry gates
- **WHEN** a bound companion is present
- **THEN** `explore.possess` is emitted once per present bound companion with `params
  {"npc_id": int}`: `enabled` true when `world/rules/possession.py`'s deterministic entry gates
  pass for that companion, otherwise a disabled entry carrying the gate's stable reason code and
  fixed message

#### Scenario: Disabled states are stable and localized
- **WHEN** any entry is emitted in a disabled state
- **THEN** it carries a stable disabled code and a safe Traditional Chinese message

#### Scenario: The vocabulary module is side-effect free
- **WHEN** the vocabulary module emits any entry
- **THEN** nothing in the module mutates traits, knowledge, dialogue, quests, inventory, combat
  sessions, party, or world time

#### Scenario: The possessed actor's talk entries stay visible disabled
- **WHEN** the puppeted actor IS a possessed NPC and talk-entry hosts are present
- **THEN** the talk entries are emitted disabled with stable possession-refusal codes and safe
  Traditional Chinese messages; possession talk refusals remain visible disabled entries

#### Scenario: Schedule-blocked hosts stay in the vocabulary
- **WHEN** a dialogue host sits inside its schedule gate's blocked window
- **THEN** it SHALL NOT be omitted from the vocabulary; the vocabulary preserves the v1 panel's
  emission semantics, and schedule-gate exclusion applies only to suggestion eligibility (the
  suggestion-eligibility requirement below)

#### Scenario: An unresolvable dialogue table yields no talk entries
- **WHEN** a dialogue host's authored dialogue table cannot be resolved
- **THEN** the vocabulary has no talk entries for it; no validator-normalized params exist for a
  keywordless host, and the version-1 panel's disabled `dialogue_unavailable` affordance is a panel
  serialization degradation, not a vocabulary entry

#### Scenario: The panel serializes host talk entries as one 交談 affordance
- **WHEN** the `exploration` panel serializes a conversable host's talk entries
- **THEN** it renders its per-keyword `explore.talk_scripted` entries and its `explore.talk_freeform`
  entry as one 交談 `explore.talk_open` affordance derived from the same host, presence, and
  possession gates, while the `context_actions` form, suggestion eligibility, and the deterministic
  fallback keep consuming the per-keyword and free-form entries unchanged
