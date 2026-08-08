## Context

The guild economy (change 16) already ships a complete, atomic turn-in: `turn_in_quest(actor, staff, quest_id)` in `world/rules/guild.py` validates registration + local `GuildStaff` host + a parsed `COMPLETED` record + a registered offer at the staff's branch + absence from `db.guild_reward_claims`, and commits wallet/inventory/merit/ACQUIRE progress/claims in one transaction with full snapshot restore. Player surfaces today:

- Text command `guild turnin <quest_id>` (aliases `guild 回報` / `回報任務` / `guild turn-in`).
- Webclient service action `guild.quest_turnin` (services panel button).
- Scripted dialogue `talk 職員` / `talk 職員 <keyword>`: pure text from the immutable `guild_staff` table (`world/onboarding/guide_dialogue.py`), which teaches `guild turnin` but performs nothing.

Dialogue resolution is a single read-only service in `world/rules/dialogue.py`; `talk_response()` is shared by `CmdsTalk` (`commands/talk.py`) and the webclient adapter `_talk_scripted_adapter` (`web/webclient/actions/exploration_actions.py`, which also validates the keyword id against the table so chips and server stay in sync). The `OnboardingGuide` host (South Gate guard) already has a stateful exception: known keywords update `guide_progress`. Quest records are three-state (`IN_PROGRESS`/`COMPLETED`/`FAILED`); "reported" is tracked separately by `guild_reward_claims`.

## Goals / Non-Goals

**Goals:**
- Let a player hand in a completed guild quest through conversation with the guild staff, in both the text client and the webclient.
- Keep `turn_in_quest` as the sole settlement writer; dialogue adds a call surface, never new state.
- Keyword-less lookups, the no-understanding line, and the immutable dialogue-table registry stay unchanged.
- Full offline determinism: no LLM, no new registries, no new persistence.

**Non-Goals:**
- No change to the quest state machine (no `READY_TO_TURN_IN` state); `COMPLETED` + `guild_reward_claims` remains the contract.
- No change to the `guild turnin` command, the services panel, or the `guild.quest_turnin` adapter.
- No dialogue-driven turn-in for other NPCs or quest sources; scope is the `guild_staff` host.
- No per-quest dynamic keyword chips in the webclient dialogue menu (the chip set stays table-driven and bounded by `MAX_SCRIPTED_KEYWORDS`).
- No migration/backward-compatibility work (project unreleased, 0 users).

## Decisions

### D1: One new `回報` action keyword on the `guild_staff` table; listing without a quest id, turn-in with one
`talk <guild-staff> 回報` (or the webclient chip) returns the deterministic reportable-quest listing; `talk <guild-staff> 回報 <quest_id>` performs the turn-in. Rationale: state-changing dialogue must name the exact quest id, matching the existing explicit-key style of `guild accept <key>` / `guild turnin <quest_id>`; a keyword that silently turned in "the only completed quest" would surprise a player with multiple completed quests and hide the reward preview. Alternatives considered: auto-turn-in when exactly one reportable quest exists (rejected: implicit state change and inconsistent behavior across counts); per-quest dynamic chips (rejected: breaks the immutable table + bounded-keyword protocol and the adapter's `keyword_ids` validation).

### D2: The listing is a read-only service in `world/rules/guild.py`; the dialogue layer only renders it
`reportable_quest_summary(actor, npc) -> str | None` in `world/rules/guild.py` first enforces the same local-host rule as every guild service command: `resolve_local_service_host(actor, GuildStaff)` resolves the unique staff in the actor's room, and the talked-to NPC must be that host; an absent or ambiguous host yields the standard Traditional Chinese rejection line. For the unique host it builds the reportable set by intersecting `read_records(actor)` (state `COMPLETED`), `get_guild_offer(record.definition_key, branch_key)` (offer registered at the staff's branch), and `parse_reward_claims(actor)` (quest id not claimed), sorted deterministically by `(accepted_tick, quest_id)`. `None` means "not a registered member", letting the caller fall back to the authored register-first line. Putting the set logic beside `turn_in_quest` keeps the single-writer boundary visible and reuses the exact same rejection conditions, so the listing can never offer a quest that `turn_in_quest` would reject.

### D3: The dynamic response hooks into the existing shared dialogue chain, which becomes actor-aware
The shared entry used by both `CmdsTalk` and the webclient `explore.talk_scripted` adapter is `world.rules.onboarding.talk_response(npc, character, keyword)`, which forwards non-guide hosts to `world.rules.dialogue.dialogue_response(npc, keyword)`. The dynamic branch therefore lives in `dialogue_response`, which gains an `actor` parameter: when the host's `dialogue_key` is `guild_staff` and the keyword is exactly `回報`, it returns `reportable_quest_summary(actor, npc)` or falls back to the static table line when the summary is `None` (unregistered player). `onboarding.talk_response` forwards the character as `actor`, and the existing callers (the web adapter, `CmdsTalk`, tests) are updated for the signature. Both surfaces thereby share one deterministic resolution with no adapter or payload change, mirroring the existing `OnboardingGuide` exception pattern: a documented dialogue action that is read-only in its keyword-less form.

### D4: Turn-in stays a thin command over a rules-layer entry that enforces the sole-host rule
A new `dialogue_turn_in(actor, npc, quest_id) -> dict` in `world/rules/guild.py` reuses `resolve_local_service_host` and requires the talked-to NPC to be that unique staff, then delegates to the existing `turn_in_quest(actor, staff, quest_id)`, which already re-validates the staff component, room locality, record, offer, and claims atomically. `CmdsTalk` splits a trailing quest id off the keyword (`talk 職員 回報 <quest_id>` → keyword `回報`, argument `<quest_id>`), guards on a `guild_staff` dialogue host, calls `dialogue_turn_in`, and renders the same success/rejection prose as `CmdGuildTurnIn` (including the onboarding-completion line). The webclient adapter needs no argument form: its `回報` chip returns the listing, and quest selection happens through the input line or the existing services panel.

### D5: Guidance prose teaches the dialogue path; docs follow the command-surface contract
The `guild_staff` greeting and `任務`/`工會` responses name `talk 職員 回報 <任務編號>` alongside `guild turnin`; the new `回報` keyword response carries the register-first guidance used as the static fallback. Because `talk`'s syntax changes (an optional quest-id argument on the `回報` keyword), `docs/game/commands.md` and `docs/game/command-reference.md` are updated in the same change to keep `tests/test_command_docs.py` green.

## Risks / Trade-offs

- [A keyword that performs a state-changing turn-in could surprise players who only wanted information] → The `回報` label is action-typed, turn-in requires an explicit quest id, and the keyword-less form only lists. Webclient players additionally have the services-panel button, which remains the primary one-click surface.
- [Dialogue turn-in could bypass the sole-local-staff rule that `guild turnin` enforces] → Both the listing and `dialogue_turn_in` resolve the unique local `GuildStaff` host with the same `resolve_local_service_host` helper the commands use and require the talked-to NPC to be that host; an ambiguous room yields the standard rejection line.
- [`dialogue_response` gains an `actor` parameter, touching every caller] → The signature change is confined to `world/rules/onboarding.py` (the forward), `CmdsTalk`, and the dialogue tests; the web adapter already passes the actor. All call sites are updated in the same change.
- [Listing and turn-in could drift apart (offer unregistered, claim added between render and turn-in)] → They share the same predicates in `world/rules/guild.py`, and `turn_in_quest` re-validates atomically at the point of write, so a stale listing simply gets the standard rejection message.
- [Dialogue tables were "no state change" by contract] → The exception is documented in the `scripted-dialogue` delta spec and mirrors the existing `OnboardingGuide` exemption; keyword-less and unknown-keyword behavior is unchanged.
- [Multiple completed quests make the listing long] → Bounded naturally: quest log and board are already bounded lists, and the listing is capped at the same style of deterministic order; explicit quest-id selection keeps output one line per quest.
