# Proposal: quest-record-issuer-key

## Why

`quest-issuance-registry` landed the issuer model, but a stored `QuestRecord` still cannot say which
commission it was accepted under. When one definition is issued both by a guild branch and by a
private character — the normal case once world commissions exist, and already possible today across
two guild branches — nothing in the record determines which reward and which settlement mode govern
it. Reward settlement, the quest-log read model, and the drawer all need that answer, so the record
must carry it.

## What Changes

- `QuestRecord` gains a required `issuer_key` field, validated against the shared issuer-key grammar
  on every read.
- `to_storage` / `from_storage` / `_RECORD_FIELDS` / `validate_record_runtime` carry and check the
  field. The field is **required**, not optional-with-default: the project has no released users and
  owes no migration, so a quest-log entry written before this change fails the strict reader and is
  recreated in development databases. **BREAKING** for existing development save data only.
- `accept_quest(actor, definition_key)` becomes `accept_quest(actor, definition_key, issuer_key)`;
  it validates that `resolve_issuance(definition_key, issuer_key)` returns an issuance before
  creating the record, so a record can never point at a commission that does not exist.
- `accept_guild_offer` passes `guild:<branch_key>` derived from the resolved staff host's
  `GuildStaff.branch_key`, keeping the guild acceptance path behaviorally identical.
- The dialogue `offer_quest` applier passes the same guild-derived key; widening that gate to
  non-guild speakers is out of scope here.

## Capabilities

### New Capabilities

(None.)

### Modified Capabilities

- `quest-lifecycle`: `QuestRecord`'s persisted field set gains `issuer_key`, and `accept_quest`'s
  contract gains the issuer argument and the resolve-before-create precondition.
- `guild-quest-board`: board acceptance now names the issuing branch as an issuer key when
  delegating to the quest lifecycle.

## Impact

- `world/quests/runtime.py`: dataclass, `_RECORD_FIELDS`, `to_storage`, `from_storage`,
  `validate_record_runtime`, `accept_quest`.
- `world/rules/guild_offers.py`: `accept_guild_offer` derives and passes the guild issuer key.
- `world/rules/npc_intents.py`: the `offer_quest` applier passes the guild issuer key.
- Six direct `QuestRecord(...)` construction sites plus the quest test fixtures gain the field:
  `world/quests/tests/test_describe.py`, `world/quests/tests/test_quests_observability.py`,
  `world/rules/tests/test_service_view.py`, `world/rules/tests/test_titles.py`,
  `web/webclient/presentation/tests/test_objectives_panel.py`.
- Existing development quest logs become unreadable and must be recreated; no migration is written.
