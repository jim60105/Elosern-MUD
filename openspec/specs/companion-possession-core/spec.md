## Purpose
The deterministic companion possession writer, entry gates, exit-path cleanup, and autonomy silencing.

## Requirements

### Requirement: Possession is a mirrored, single-writer, transactional binding
`world/rules/possession.py` SHALL be the sole writer of `player.db.possession` (a mapping `{npc_dbid, since_tick}`) and `npc.db.possessed_by` (the owning player's dbid), written only through `enter_possession(player, npc)` and `release_possession(player, npc, reason)` inside one `transaction.atomic()` with snapshot/restore of both in-process surfaces (the idmapper-cache discipline of `world/rules/party.py`: a rolled-back write must never remain readable in-process — `restore_possession_surfaces` is the exported restore helper) and a stable `reason` code on every error type (`PossessionGateError`, `PossessionWriteError`). The enter order SHALL be documented as gates → mirrored write → puppet-transfer hook → cmdset-mount hook → boundary info event, and release exactly reversed; this capability ships the non-puppet steps with the two hook calls as named no-op seam call sites (`_transfer_puppet`, `_mount_cmdset`) that the `companion-possession-transition` change replaces. `release_possession` SHALL be idempotent: no possession present clears and succeeds as a no-op. Every enter and release emits one facade info event with `char` and possession context.

#### Scenario: Enter mirrors both surfaces atomically
- **WHEN** `enter_possession` succeeds for a bound, co-located companion
- **THEN** `player.db.possession` names the NPC's dbid with the current world tick and the NPC's `db.possessed_by` names the player, and one info event names both parties

#### Scenario: A failed write restores both in-process surfaces
- **WHEN** the possession write raises after the transaction opened
- **THEN** `PossessionWriteError` is raised, both in-process attributes read their pre-write values, and no half-binding is observable

#### Scenario: Release is idempotent
- **WHEN** `release_possession` runs against a player holding no possession
- **THEN** it succeeds without error and writes nothing

### Requirement: Entry gates are deterministic, stable-coded, and precede all generative work
`enter_possession` SHALL refuse, in this order and each with its own stable reason — before any LLM or dialogue work — `not_bound` (target is not a live bound companion of this player), `not_co_located`, `in_combat` (either side in an active combat session, the same `is_in_active_session` helper the party-adjustment boundary uses), `dialogue_open` (the NPC has an open dialogue session), `already_possessing` (the player already possesses another NPC, or this account's characters already possess any NPC — scanned over the account's own characters only). Each refusal writes no state. Fixed Traditional Chinese messages ride the reason table.

#### Scenario: Every gate names its reason with zero writes
- **WHEN** each of the five gate conditions is provoked individually
- **THEN** the matching `PossessionGateError` reason surfaces with its fixed message and neither possession attribute changes

#### Scenario: One account possesses at most one NPC
- **WHEN** the account's character A possesses companion X, and (through a second session or another character) a possession of Y is attempted
- **THEN** `already_possessing` refuses the second possession

### Requirement: Every exit path releases the possession
Dismissal, auto-leave, and deletion SHALL release first: the `leave` command and `leave_party` SHALL refuse a possessed companion with the fixed handback-first message (`REASON_HANDBACK_FIRST`, gate + defense-in-depth inside `leave_party` itself); the affinity auto-leave hook SHALL call `possession.release_for_party_change(npc, player)` as its first step BEFORE opening the affinity write's atomic block (release-then-commit — a database transaction cannot make puppet/session side effects atomic), so a release failure aborts before any affinity delta is written ("affinity below threshold but still possessed" unreachable); if the attribute commit itself fails after a successful release, the bounded recovery state is "possession recorded, not yet dismissed" and every leg is idempotent so 歸位 or the next negative delta converges. `purge_npc_memberships` SHALL run the same full release unconditionally before unwinding the binding. `release_for_party_change` SHALL run the full possession release — the documented handback seam (the transition change's unpuppet-B/re-puppet-A ladder; a no-op in this change because no session ever puppets the NPC until then) and the mirrored attribute clear — never an attribute-only clear while a session could still hold the puppet. `release_on_disconnect(account)` SHALL scan the account's characters for `db.possession` and run the same full release per hit, idempotently; its caller lands with the transition change on `Account.at_post_disconnect` (the disconnect-only lifecycle point — `at_post_unpuppet` fires on every deliberate unpuppet, including possession's own release of A, and must NOT run this).

#### Scenario: Auto-leave releases before the affinity write opens
- **WHEN** a possessed companion's affinity delta is about to drop it below 70
- **THEN** possession release runs and commits first and only then does the affinity/party atomic open, and the notification follows that commit, per the affinity writer's contract

#### Scenario: A failed release aborts the auto-leave write
- **WHEN** `release_for_party_change` raises
- **THEN** no affinity delta or party change is committed and the companion remains bound and possessed with unchanged affinity

#### Scenario: Dismissing a possessed companion is refused
- **WHEN** the player runs `leave` (解散) on the companion they currently possess
- **THEN** the fixed handback-first line is returned and both possession and party attributes are unchanged

#### Scenario: Deletion purge unwinds possession
- **WHEN** a possessed companion NPC is deleted
- **THEN** the purge releases the possession attributes and unwinds the party binding in one transaction, and the player's next read sees no possession

#### Scenario: Disconnect release is account-keyed and idempotent
- **WHEN** `release_on_disconnect` runs twice for the same account
- **THEN** both runs succeed, every `db.possession` mirror under that account is clear after the first, and the second run writes nothing

### Requirement: The possess command surface is localized and documented
The character cmdset SHALL mount `possess` (aliases `附身`, English alias retained) taking one bound-companion target, and `unpossess` (aliases `歸位`), both localized in shape (Traditional Chinese messages, stable reason mapping). `possess` runs `enter_possession` and surfaces its gate lines; `unpossess` runs `release_possession(player, npc, "handback")`. Both commands SHALL appear in `docs/game/command-reference.md` and `docs/game/commands.md` with the curated manifest keeping `tests/test_command_docs.py` green.

#### Scenario: The command pair resolves targets and reports gate lines
- **WHEN** the player runs 附身 on an absent, ambiguous, or unbound target
- **THEN** the fixed Traditional Chinese refusal shows and no possession state changes

#### Scenario: 歸位 releases the current possession
- **WHEN** the player runs 歸位 while possessing
- **THEN** the possession attributes clear and the fixed release line shows

### Requirement: A possessed NPC is autonomy-silent and unreachable by dialogue
An NPC with `db.possessed_by` set SHALL be autonomy-silent: `world/rules/service_gate.py::schedule_silenced(npc)` SHALL return true for it as the predicate's OR-ed second trigger (the same single site the place-bound travel trigger lives), so `settle_npc_schedules` moves or re-states nothing for it; `LLMNPC.at_talked_to` (and the freeform dialogue seam behind it) SHALL refuse the possessed self with the fixed 「他現在無法回應你。」line and write no dialogue, memory, or affinity state. Quest-observer companion credit SHALL NOT change: a possessed companion's combat and exploration results keep crediting the owning player's quests exactly as for any bound companion (ratified feature — possession moves the camera, not the ownership).

#### Scenario: The possessed companion's schedule stays silent
- **WHEN** a possessed guard-type companion crosses a full authored shift window
- **THEN** no entry settles, no event names it, and its state is unchanged

#### Scenario: Talking to the possessed self is refused without state
- **WHEN** the player (on character A) talks freely to companion B while possessing B
- **THEN** the fixed refusal line shows and no dialogue session, memory append, or affinity change occurs

#### Scenario: Possessed-companion combat still credits the owner's quest
- **WHEN** the possessed companion lands the killing blow on a quest-tracked monster
- **THEN** the owning player's quest progresses exactly as if the companion fought unpossessed
