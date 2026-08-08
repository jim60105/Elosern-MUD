## Why

The guild staff NPC's scripted dialogue (`talk 職員`, and the webclient `explore.talk_scripted` keyword chips) is purely informational: it teaches `guild turnin <quest_id>` but never performs the turn-in itself. A player who finishes a quest and reports back to the guild clerk naturally expects to hand the completed quest in through the conversation, yet the dialogue surface offers no such action — turn-in is reachable only via the `guild turnin` text command or the webclient services panel. This gap is the issue "工會系統沒有辦法回報任務(交回完成任務)".

## What Changes

- Add a `回報` (report/turn-in) action keyword to the `guild_staff` dialogue table.
- `talk <guild-staff> 回報` (no quest id) SHALL list, in deterministic order, every reportable quest (a `COMPLETED` record whose definition has a registered offer at the staff's branch and whose quest id is absent from the actor's reward claims), or a "nothing to report" line, or registration guidance for unregistered players. This listing is read-only and causes no state change.
- `talk <guild-staff> 回報 <quest_id>` SHALL turn in that exact quest through the existing `turn_in_quest` deterministic API, keeping its atomic exactly-once settlement, ACQUIRE progress, onboarding hook, and rejection semantics, with player-facing Traditional Chinese success/failure messages consistent with `guild turnin`.
- Both dialogue forms SHALL enforce the same sole-local-staff rule as the guild commands (`resolve_local_service_host`): the talked-to NPC must be the unique `GuildStaff` host in the caller's room, and ambiguous hosts are rejected.
- The webclient `explore.talk_scripted` adapter SHALL serve the same listing when its `回報` chip is tapped (it shares the deterministic dialogue resolution); explicit quest selection remains `talk 職員 回報 <quest_id>` in the input line or the existing services-panel turn-in button.
- Update `guild_staff` guidance prose (greeting, `任務`/`工會` responses) to teach the dialogue turn-in path, and update the `talk` player-command documentation.
- **No state-machine change**: quest records keep the three-state lifecycle and `guild_reward_claims`; this change only adds a dialogue-driven call surface over the existing settlement writer.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `scripted-dialogue`: the no-state-change guarantee gains the `guild_staff` `回報` action keyword — keyword-less lookup stays read-only, while the keyword with a quest id performs an explicit turn-in through the deterministic settlement API.
- `guild-quest-board`: the player-facing guild workflow requirement gains the dialogue turn-in surface (listing + turn-in) in addition to the existing `guild turnin` command, both delegating to the same deterministic APIs.

## Impact

- `world/rules/guild.py`: add the read-only reportable-quest listing and a `dialogue_turn_in` entry point, both enforcing the sole-local-staff rule via `resolve_local_service_host` before delegating to `turn_in_quest`; sole-writer boundary unchanged.
- `world/rules/dialogue.py`: `dialogue_response` gains an `actor` parameter and resolves the dynamic `guild_staff` `回報` response (listing) before the static table fallback; still read-only for keyword-less lookups.
- `world/rules/onboarding.py`: `talk_response` forwards the actor to the rules-level dialogue resolution (call sites in `CmdsTalk`, the web adapter, and tests updated for the signature).
- `commands/talk.py`: parse `回報 [<quest_id>]` on a guild-staff host and call the deterministic dialogue turn-in entry; all other keywords behave as today.
- `world/onboarding/guide_dialogue.py`: `guild_staff` table gains the `回報` keyword and updated guidance prose.
- `web/webclient/actions/exploration_actions.py`: unchanged behavior for chip taps (listing flows through the shared resolution); no payload change.
- Docs: `docs/game/commands.md` and `docs/game/command-reference.md` for the `talk` syntax change (kept green by `tests/test_command_docs.py`).
- Tests: `world/rules/tests/test_dialogue.py`, `world/rules/tests/test_guild_rewards.py`, `commands/tests/` (talk + guild command tests), `web/webclient/actions/tests/` and presentation tests where keyword chips are asserted, plus the `dialogue_response`/`talk_response` call-site updates in existing tests.
- Main specs updated on archive: `openspec/specs/scripted-dialogue/spec.md`, `openspec/specs/guild-quest-board/spec.md`.
