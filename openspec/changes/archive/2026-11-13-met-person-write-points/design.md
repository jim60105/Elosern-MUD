# Design: met-person record write points

## Context

- `web/webclient/actions/exploration_actions.py::_look_adapter` calls
  `actor.at_look(target)`; Evennia's `DefaultObject.at_look(target)` calls
  `target.at_desc(looker=self)`; the text `look` command goes through the same
  `at_look`. `typeclasses/npcs.py::NPC` defines no `at_desc` today.
- Talk: `_talk_open_adapter` (gates: presence, schedule, dialogue host,
  possession context) then `open_or_refresh_dialogue(actor, npc, ...)`;
  `_talk_scripted_adapter` and `_talk_freeform_adapter` (~line 1215) speak to
  a present host; `commands/talk.py::CmdTalk` imports
  `open_or_refresh_dialogue`. `open_or_refresh_dialogue` itself is also used by
  `world/quests/story_dialogue.py:345` (NPC addresses the player) and
  `refresh_dialogue_phase`, so the write must NOT live inside it.
- Services: browser mutations admit the provider in
  `service_actions._resolve_target` via `require_service_mutation`; text
  provider commands use `commands/npc_services.resolve_selected_provider`
  (read-only by contract; the listing command also uses it).
- Invite: `_party_invite_adapter` re-verifies the gate, then
  `npc.run_npc_exchange(..., path="party_invite")`;
  `commands/invite.py::CmdInvite.func` runs
  `npc.run_npc_exchange(message, caller, client, path="invite")`.

## Goals / Non-Goals

**Goals:** exactly the four player-initiated families write.

**Non-Goals:** changing any gate, message or outcome of those flows.

## Decisions

1. Look: add to `NPC`:
   ```python
   def at_desc(self, looker=None, **kwargs):
       super().at_desc(looker=looker, **kwargs)
       if looker is not None:
           from world.rules.met_people import record_person_interaction
           record_person_interaction(looker, self)
   ```
   Monsters are not `NPC` instances, so they never reach it.
2. Talk: call `record_person_interaction(actor, npc)` immediately before
   `open_or_refresh_dialogue` in `_talk_open_adapter`; after the presence and
   schedule gates in `_talk_scripted_adapter` and `_talk_freeform_adapter`;
   in `CmdsTalk.func` after its presence, schedule and possession-context
   gates, before the keyword and host branches. Not in
   `open_or_refresh_dialogue`: the story-scene refresh
   (`world.quests.story_dialogue`) and `refresh_dialogue_phase` call it for
   NPC-initiated contact too.
3. Services: in `_resolve_target` after a successful
   `require_service_mutation`. Text: list callers with
   `rg -n "resolve_selected_provider\(" commands`; add the call after a
   non-None provider in every caller that then invokes a domain mutation API
   (buy, sell, guild register/accept/abandon/turn-in, exam request); do not
   add it to the read-only listing command. Leave `resolve_selected_provider`
   itself read-only.
4. Invite: after the gate checks and before `run_npc_exchange` in both entry
   points, so a declined or failed exchange still records the attempt.
5. `record_person_interaction` already ignores generic NPCs and never raises;
   call sites add no try/except.

## Risks / Trade-offs

- [A future talk entry point forgets the call] → the requirement's scenarios
  cover each existing entry point; new entry points must add a test.
