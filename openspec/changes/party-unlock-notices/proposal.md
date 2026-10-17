# Proposal: Party unlock notifications and session unread state

## Why

Design §4.7 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: when any member's practice award unlocks a skill, the commander receives a notification naming the member and the skill (艾拉 學會了 群體治癒); the member rail's unread dot is session-scoped `ndb` state cleared by opening that member's skill tab and dropped on reconnect. Today unlock lines are anonymous strings, the booked-study path (`grant_study_practice_xp`) has no announcement sink at all, and nothing records which member unlocked what.

## What Changes

- Practice sinks carry structured unlock notices (learner, skill key, rendered line) on both entry points; the booked-study stage emits plain `practice_unlock` scheduled events that skip callers render after commit.
- Lines: commander learner keeps 「新法術可用：X」/「新技能可用：X」; companion learner gets 「{成員} 學會了 {技能}」. Delivered to the commander's sessions after commit by every owner: field cast (command and adapter), field item use, combat round delivery, and skip commands/adapters.
- New `world/rules/unlock_notices.py`: `record_unlocks`, `mark_unlocks_seen(session, member_id)`, `unlock_flags(session)`; state lives in `session.ndb` only.
- Read access for presenters is a copied snapshot in the presentation context (consumed by `party-panel-v3-view-member` and `character-skill-growth-fields`).

## Capabilities

### New Capabilities

- `party-unlock-notices`: session-scoped unread marks and recent-unlock sets.

### Modified Capabilities

- `skill-lineage-panel`: the unlock notification covers booked study and names companion learners.

## Impact

- `world/rules/progression/__init__.py` (sink item type), `world/rules/cross_lineage_unlock.py` (line helper), `world/rules/clock.py::_practice_settlement` (scheduled events), `world/rules/time_skip.py::render_skip_summary`, `world/rules/action/resolver.py`, `world/rules/cast_settlement.py`, `world/rules/items/settlement.py`, `world/rules/combat_session/rounds.py::_deliver_after_commit`, `commands/action.py`, `commands/items.py`, `commands/skip.py`, `web/webclient/actions/skill_use_actions.py`, `service_actions.py`, `exploration_actions.py`, `web/webclient/presentation/context.py`.
- Tests: `world/rules/tests/test_unlock_notices.py` (sharded) plus updates to existing unlock-line tests.

## Effort

**6.5 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **12 of 31**.

- depends-on: party-practice-booking
- depends-on: companion-field-item-use
- depends-on: companion-field-cast-actions
- depends-on: shop-party-recipient-seller

### Code and spec conflicts within the new batch

- `party-practice-booking`: shared files `world/rules/clock.py`, `world/rules/time_skip.py`, `commands/skip.py`, `exploration_actions.py` (F; that change first).
- `companion-field-cast-rule` / `companion-field-cast-actions`: shared files `commands/action.py`, `skill_use_actions.py` (F; those first).
- `companion-field-item-use`: shared files `commands/items.py`, `service_actions.py` (F; that first).
- `shop-party-recipient-seller`: shared file `service_actions.py` (F; that first, hence the declared prerequisite).
- `party-panel-v3-view-member`, `character-skill-growth-fields`: read the session snapshot (D); `party-panel-v3-view-member` calls `mark_unlocks_seen` (D).
- `.github/evennia-shards.json`: conditional manifest conflict.

### Active change coordination

No active OpenSpec change.
