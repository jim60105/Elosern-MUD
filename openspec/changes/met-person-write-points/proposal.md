# Proposal: met-person record write points

## Batch:

Gallery window programme, stage 2 ("The met-person record": "Written by
exactly four player-initiated interactions").

- depends-on: met-person-record
- conflict: `web/webclient/actions/exploration_actions.py` (talk, invite
  adapters), `web/webclient/actions/service_actions.py`, `commands/talk.py`,
  `commands/invite.py`, the service text commands, `typeclasses/npcs.py`.
  No other programme change edits these files.

## Why

The record exists but nothing writes it. The design names exactly four
player-initiated interactions that write it: talk, look, using one of the
NPC's services, and inviting it to the party. NPC-initiated contact writes
nothing.

## What Changes

- Calls to `world.rules.met_people.record_person_interaction(actor, npc)` at:
  - look: `typeclasses.npcs.NPC.at_desc(looker=...)` (Evennia's `at_look`
    calls it for both the webclient look action and the text look command);
  - talk: after the gates pass in `_talk_open_adapter`,
    `_talk_scripted_adapter`, `_talk_freeform_adapter` and `CmdTalk.func`;
  - services: after `require_service_mutation` admits the provider in
    `service_actions._resolve_target`, and in each text provider command that
    performs a mutation after `resolve_selected_provider` returns a provider;
  - invite: after the deterministic gate passes in `_party_invite_adapter`
    and `CmdInvite.func`, before the exchange starts.
- `world/quests/story_dialogue.py` and `refresh_dialogue_phase` (NPC- or
  system-initiated) write nothing.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `met-person-record`: adds the four write points.

## Impact

- Code: the files under conflict above.
- Tests: `world/rules/tests/test_met_people.py` (integration cases) or the
  existing adapter/command test modules beside each call site.
- Estimate: 5 hours (seven call sites 1.5 h, integration tests per family
  3 h, gates 0.5 h).
