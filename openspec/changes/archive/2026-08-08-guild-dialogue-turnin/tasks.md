## 1. Deterministic guild dialogue-turn-in service

- [x] 1.1 Add `reportable_quest_summary(actor, npc) -> str | None` to `world/rules/guild.py`: enforce the sole-local-staff rule with `resolve_local_service_host(actor, GuildStaff)` (the talked-to NPC must be that unique host; absent/ambiguous hosts yield the standard rejection line); for the unique host, intersect `read_records` (state `COMPLETED`), `get_guild_offer(record.definition_key, branch_key)` at the staff's branch, and `parse_reward_claims`; order by `(accepted_tick, quest_id)`; return `None` only for an unregistered player; render the Traditional Chinese listing (task count, per-quest `quest_id` + display name, and the `talk <guild-staff> 回報 <任務編號>` hint) or the "nothing to report" line
- [x] 1.2 Add `dialogue_turn_in(actor, npc, quest_id) -> dict` to `world/rules/guild.py`: resolve the unique local `GuildStaff` host, require the talked-to NPC to be that host, then delegate to `turn_in_quest` so the sole-host rule, atomic settlement, exactly-once claims, ACQUIRE progress, and the onboarding hook are enforced at the rules layer
- [x] 1.3 Add pure-logic tests in `world/rules/tests/test_guild_rewards.py` (or a new `world/rules/tests/test_guild_dialogue_turnin.py`): listing order by `(accepted_tick, quest_id)`, exclusion of in-progress/failed/claimed/offer-less records, `None` for unregistered players, listing parity with the `turn_in_quest` rejection conditions (never list a quest that would be rejected), and rejection of the listing and turn-in when two `GuildStaff` hosts share the room or the talked-to NPC is not the resolved host
- [x] 1.4 Add integration tests: turn-in through the listing (`回報 <quest_id>` semantics) calls `turn_in_quest` and pays the exact reward once, keeps the exactly-once claim, applies ACQUIRE progress and the `introductory_hunt` onboarding hook, and restores all surfaces on an injected failure

## 2. Dialogue table and resolution

- [x] 2.1 Add the `回報` keyword entry (register-first guidance as the authored fallback) to `GUILD_STAFF_RESPONSES` in `world/onboarding/guide_dialogue.py`; update the `guild_staff` greeting and `任務`/`工會` responses to teach `talk 職員 回報 <任務編號>`
- [x] 2.2 Extend `dialogue_response` in `world/rules/dialogue.py` with an `actor` parameter and the guild-staff action branch: for a host whose `dialogue_key` is `guild_staff` with keyword exactly `回報`, return `reportable_quest_summary(actor, npc)` or fall back to the authored line when it returns `None`; every other keyword and host resolves exactly as today; update `talk_response` in `world/rules/onboarding.py` to forward the character as `actor`, and update all call sites and existing dialogue tests for the signature
- [x] 2.3 Extend `CmdsTalk` in `commands/talk.py` to split a trailing quest id off the keyword (`talk 職員 回報 <quest_id>`), guard on a `guild_staff` dialogue host, call `dialogue_turn_in`, and render the same success/rejection prose as `CmdGuildTurnIn` (including the onboarding-completion line); keyword-less `回報` flows through `talk_response` unchanged
- [x] 2.4 Add command tests in `commands/tests/` (talk surface): `talk 職員 回報` listing, `talk 職員 回報 <quest_id>` success and rejection messages, unregistered fallback, `回報` on the guard/other hosts yielding the no-understanding line, ambiguous-staff rejection, and unknown-keyword behavior unchanged
- [x] 2.5 Extend `world/rules/tests/test_dialogue.py` and `world/onboarding/tests/test_onboarding_data.py` for the new/updated `guild_staff` table entries and the dialogue action exception (listing read-only, no state change for keyword-less lookups)

## 3. Webclient surface

- [x] 3.1 Verify and extend `web/webclient/actions/tests/` + presentation tests: the `explore.talk_scripted` adapter with `keyword_id` `回報` returns the deterministic listing text through `talk_response`; the guild-staff target descriptor exposes the `回報` chip within `MAX_SCRIPTED_KEYWORDS`
- [x] 3.2 Add/update browser-level coverage in `web/tests/browser/` (seed a completed unclaimed quest) asserting the `回報` chip renders and its tap reports the listing with no state change

## 4. Docs and contracts

- [x] 4.1 Update the `talk` entry in `tests/test_command_docs.py` `EXPECTED_COMMANDS` (syntax gains `[<quest_id>]` for the guild-staff `回報` keyword), update `docs/game/command-reference.md` (`talk` syntax `talk <npc> <keyword> [<quest_id>]` with the guild-staff `回報` behavior) and the `docs/game/commands.md` row for `talk`; keep `tests/test_command_docs.py` green
- [x] 4.2 Run focused tests (`world.rules.tests.test_guild_rewards`, `world.rules.tests.test_dialogue`, `commands.tests.test_guild_economy_commands`, talk tests, webclient action tests, Node tests) and `uv run --locked python -m compileall -q world typeclasses commands server`
- [x] 4.3 Run `uv run --locked python -m tools.spec_traceability check` and annotate the new/updated tests with `covers_requirement` for the two modified capabilities' requirements
- [x] 4.4 Run the relevant owned domains of the Evennia suite (`world` + `commands` + `web.webclient`) before handoff
