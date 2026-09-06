## Purpose

Define the deterministic capability surface for the `offer_quest` dialogue intent: exact payload,
guild-offer verification, direct atomic quest assignment, and the failure semantics.
## Requirements
### Requirement: The offer_quest intent carries exactly one quest_key field

The `offer_quest` intent SHALL carry exactly one payload field, `quest_key`, a non-empty string of
at most 64 code points (shared named constant `MAX_INTENT_KEY_LENGTH`). Missing, empty, longer,
non-text, or extra-field `quest_key` values SHALL be rejected by the per-kind semantic validator
and retried within the budget rather than passed to the engine.

#### Scenario: A valid offer_quest payload passes extraction
- **WHEN** the model returns `{"kind": "offer_quest", "quest_key": "forest_clearing"}` with a
  bounded quest key
- **THEN** the intent passes semantic validation and proceeds to deterministic verification

#### Scenario: A malformed offer_quest payload is rejected and retried
- **WHEN** the model returns `offer_quest` with a missing, empty, non-text, longer-than-bound, or
  extra-field payload
- **THEN** the output is rejected by the per-kind semantic validator and retried rather than passed
  to the engine

### Requirement: The offer_quest intent is verified against the registered guild offer surface

The deterministic applier SHALL verify, before any write, that (1) the speaking NPC is an `NPC`
carrying either the `GuildStaff` component with a `branch_key` or the `QuestIssuer` component,
which is the sole authority for issuing a private commission; (2) the speaker's resolved issuer key
has a registered issuance for `quest_key`; and (3) the eligibility rule of that issuer kind passes.
For a `GuildStaff` speaker the issuance SHALL be a `GuildQuestOffer` registered at that branch
(`get_guild_offer(quest_key, branch_key)`) and the player SHALL be a
registered guild member whose canonical rank exists and is within the offer's quest rank band,
using the same canonical eligibility check the guild board applies. For a `QuestIssuer` speaker the
issuance SHALL be a registered private commission at that speaker's resolved issuer key, and the
existence of that issuance SHALL be the whole eligibility rule — a private commission has no rank
band, so no registration or rank gate applies and none SHALL be invented. A speaker carrying both
components SHALL be resolved by the namespace of the issuance registered for `quest_key`; an
ambiguous case where both kinds hold an issuance for the same key SHALL fail verification rather
than choosing one. A speaker whose carried authority carries malformed identity data (an authored
`issuer_key` that fails the shared issuer-key grammar, or a `branch_key` that does) SHALL fail
verification rather than dispatching through the remaining authority.

Any verification failure SHALL
return `applied=False` with a documented reason, preserve the speech, and change no state. The AI
SHALL NOT be able to assign a quest the speaker does not hold an issuance for, waive a registration
or rank gate, choose the branch, the issuer, or the offer identity, or make an NPC carrying neither
component issue anything.

#### Scenario: A staff NPC of the registered branch can offer the quest
- **WHEN** the speaking NPC is an `NPC` carrying `GuildStaff` with a branch at which `quest_key`
  is a registered offer, and the player is a registered member whose canonical rank is within the
  offer's quest rank band
- **THEN** verification passes and the intent proceeds to application

#### Scenario: An NPC without the branch's offer cannot assign the quest
- **WHEN** the speaking NPC is not an `NPC`, lacks both `GuildStaff` and `QuestIssuer`, or
  `get_guild_offer(quest_key, branch_key)` does not resolve, or the player is unregistered /
  rankless / below the quest band / carries malformed registration data
- **THEN** the applier returns `applied=False`, the speech is preserved, and no state changes

#### Scenario: An authorized commissioner can offer its own private commission
- **WHEN** the speaking NPC carries `QuestIssuer` and a private commission for `quest_key` is
  registered at that speaker's resolved issuer key
- **THEN** verification passes with no registration and no rank check, and the intent proceeds to
  application

#### Scenario: A commissioner cannot offer a commission it does not hold
- **WHEN** the speaking NPC carries `QuestIssuer` but no issuance for `quest_key` is registered at
  its resolved issuer key
- **THEN** the applier returns `applied=False`, the speech is preserved, and no state changes

#### Scenario: An unauthorized NPC cannot issue a private commission
- **WHEN** the speaking NPC carries neither `GuildStaff` nor `QuestIssuer`, even while a private
  commission for `quest_key` is registered elsewhere
- **THEN** the applier returns `applied=False`, the speech is preserved, and no state changes

#### Scenario: An ambiguous dual-component speaker fails verification
- **WHEN** the speaking NPC carries both components and an issuance for `quest_key` is registered
  under both its guild branch and its private issuer key
- **THEN** verification fails, the speech is preserved, and no state changes — the applier does not
  choose an issuer

### Requirement: A verified offer_quest is assigned directly and atomically

On successful verification, the applier SHALL delegate to the quest runtime's `accept_quest(
player, quest_key)` and SHALL additionally call the sole affinity writer with the `guild` source
(`apply_affinity_change(npc, player, "guild", 1)`), both inside one atomic transaction that
snapshots the player's quest-log surface and the NPC's affinity record and restores them on any
exception; the speech is the notification and there is no pending-offer step. The affinity write
SHALL follow the sole writer's budget rules exactly as the board-acceptance path does: a
budget-capped or capped-at-maximum write (applied amount 0) SHALL NOT roll back the quest, and the
applier SHALL report the outcome accordingly. Duplicate-quest rejection SHALL be delegated to the
quest runtime. The AI SHALL NOT create, mutate, or bypass quest records directly.

#### Scenario: A dialogue-assigned quest lands like a board-accepted one
- **WHEN** the verified intent assigns `quest_key`, the quest runtime accepts it, and the affinity
  budget permits the full +1
- **THEN** the player's quest log gains the record and the NPC's affinity rises by exactly 1, all
  in one committed transaction

#### Scenario: A budget-capped affinity write does not roll back the quest
- **WHEN** the quest accepts but the sole affinity writer applies 0 (daily budget exhausted or
  affinity at cap)
- **THEN** the quest record is committed, the applier reports the capped outcome, and no rollback
  occurs — matching the board-acceptance path

#### Scenario: A duplicate or failing acceptance rolls back without partial state
- **WHEN** the quest runtime rejects the acceptance (already-active quest, or any commit exception)
- **THEN** the applier returns `applied=False`, the speech is preserved, the quest log and
  affinity record are restored to their prior state, and no affinity was granted

### Requirement: A verified offer_quest names its issuance when assigning

On successful verification the applier SHALL pass the speaker's resolved issuer key into
`accept_quest`, so the created record names the exact issuance whose reward and settlement mode
govern it. The applier SHALL NOT construct that key by string concatenation and SHALL NOT substitute
a different issuer for a quest key registered under several.

#### Scenario: A guild-assigned record names its branch
- **WHEN** a `GuildStaff` speaker's verified intent is applied
- **THEN** the created record's issuer key is that speaker's guild branch key in canonical form

#### Scenario: A privately assigned record names its commissioner
- **WHEN** a `QuestIssuer` speaker's verified intent is applied
- **THEN** the created record's issuer key is that speaker's resolved issuer key, and the record
  resolves to that commission's reward and settlement mode

