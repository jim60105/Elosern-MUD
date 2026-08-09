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
carrying the `GuildStaff` component with a `branch_key`; (2) a `GuildQuestOffer` for `quest_key`
is registered at that branch (`get_guild_offer(quest_key, branch_key)`); and (3) the player is a
registered guild member whose canonical rank exists and is within the offer's quest rank band,
using the same canonical eligibility check the guild board applies. Any verification failure SHALL
return `applied=False` with a documented reason, preserve the speech, and change no state. The AI
SHALL NOT be able to assign a quest the NPC's branch does not hold, waive a registration or rank
gate, or choose the branch or offer identity.

#### Scenario: A staff NPC of the registered branch can offer the quest
- **WHEN** the speaking NPC is an `NPC` carrying `GuildStaff` with a branch at which `quest_key`
  is a registered offer, and the player is a registered member whose canonical rank is within the
  offer's quest rank band
- **THEN** verification passes and the intent proceeds to application

#### Scenario: An NPC without the branch's offer cannot assign the quest
- **WHEN** the speaking NPC is not an `NPC`, lacks `GuildStaff`, or `get_guild_offer(quest_key,
  branch_key)` does not resolve, or the player is unregistered / rankless / below the quest band
  / carries malformed registration data
- **THEN** the applier returns `applied=False`, the speech is preserved, and no state changes

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
