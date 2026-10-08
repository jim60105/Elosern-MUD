## Purpose
The deterministic companion possession writer, entry gates, exit-path cleanup, and autonomy silencing.

## Requirements

### Requirement: Possession is a mirrored, single-writer, transactional binding
`world/rules/possession.py` SHALL be the sole writer of `player.db.possession` (a mapping `{npc_dbid, since_tick}`) and `npc.db.possessed_by` (the owning player's dbid), written only through `enter_possession(player, npc)` and `release_possession(player, npc, reason)` inside one `transaction.atomic()` with snapshot/restore of both in-process surfaces, a stable `reason` code on every error type, and an idempotent `release_possession`.

#### Scenario: Enter mirrors both surfaces atomically
- **WHEN** `enter_possession` succeeds for a bound, co-located companion
- **THEN** `player.db.possession` names the NPC's dbid with the current world tick and the NPC's `db.possessed_by` names the player, and one info event names both parties

#### Scenario: A failed write restores both in-process surfaces
- **WHEN** the possession write raises after the transaction opened
- **THEN** `PossessionWriteError` is raised, both in-process attributes read their pre-write values, and no half-binding is observable

#### Scenario: Release is idempotent
- **WHEN** `release_possession` runs against a player holding no possession
- **THEN** it succeeds without error and writes nothing

#### Scenario: In-process surfaces follow the party.py cache discipline
- **WHEN** a possession write is rolled back
- **THEN** it never remains readable in-process (the idmapper-cache discipline of
  `world/rules/party.py`), and `restore_possession_surfaces` is the exported restore helper

#### Scenario: Every error type carries a stable reason code
- **WHEN** possession raises `PossessionGateError` or `PossessionWriteError`
- **THEN** the error carries a stable `reason` code

#### Scenario: The enter and release orders are documented
- **WHEN** the possession lifecycle is documented
- **THEN** the enter order reads gates → mirrored write → puppet-transfer hook → cmdset-mount
  hook → boundary info event, and release is exactly reversed

#### Scenario: The puppet hooks ship as named no-op seams
- **WHEN** this capability ships the non-puppet steps
- **THEN** the two hook calls exist as named no-op seam call sites (`_transfer_puppet`,
  `_mount_cmdset`) that the `companion-possession-transition` change replaces

#### Scenario: Enter and release each emit one facade info event
- **WHEN** an enter or a release completes
- **THEN** it emits one facade info event with `char` and possession context

### Requirement: Entry gates are deterministic, stable-coded, and precede all generative work
`enter_possession` SHALL refuse, in this order and each with its own stable reason — before any LLM or dialogue work — `not_bound`, `not_co_located`, `in_combat`, `dialogue_open`, `already_possessing`. Each refusal writes no state. Fixed Traditional Chinese messages ride the reason table.

#### Scenario: Every gate names its reason with zero writes
- **WHEN** each of the five gate conditions is provoked individually
- **THEN** the matching `PossessionGateError` reason surfaces with its fixed message and neither possession attribute changes

#### Scenario: One account possesses at most one NPC
- **WHEN** the account's character A possesses companion X, and (through a second session or another character) a possession of Y is attempted
- **THEN** `already_possessing` refuses the second possession

#### Scenario: The bound and co-location gates
- **WHEN** the target is not a live bound companion of this player, or is not co-located
- **THEN** `not_bound` or `not_co_located` refuses accordingly

#### Scenario: The combat gate reuses the party helper
- **WHEN** either side is in an active combat session
- **THEN** `in_combat` refuses, using the same `is_in_active_session` helper the party-adjustment
  boundary uses

#### Scenario: The dialogue gate checks for an open session
- **WHEN** the NPC has an open dialogue session
- **THEN** `dialogue_open` refuses

#### Scenario: The already-possessing gate scans the account's own characters only
- **WHEN** the player already possesses another NPC, or this account's characters already possess
  any NPC
- **THEN** `already_possessing` refuses, scanned over the account's own characters only

### Requirement: Every exit path releases the possession
Dismissal, auto-leave, and deletion SHALL release first. `release_for_party_change` SHALL run the full possession release — never an attribute-only clear while a session could still hold the puppet. `release_on_disconnect(account)` SHALL scan the account's characters for `db.possession` and run the same full release per hit, idempotently.

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

#### Scenario: Dismissal refuses a possessed companion
- **WHEN** the `leave` command or `leave_party` is invoked on a possessed companion
- **THEN** it is refused with the fixed handback-first message (`REASON_HANDBACK_FIRST`, gate + defense-in-depth inside `leave_party` itself)

#### Scenario: Auto-leave releases before opening the affinity atomic
- **WHEN** the affinity auto-leave hook runs
- **THEN** it calls `possession.release_for_party_change(npc, player)` as its first step BEFORE opening the affinity write's atomic block (release-then-commit — a database transaction cannot make puppet/session side effects atomic), so a release failure aborts before any affinity delta is written ("affinity below threshold but still possessed" unreachable)

#### Scenario: A failed commit after release converges idempotently
- **WHEN** the attribute commit itself fails after a successful release
- **THEN** the bounded recovery state is "possession recorded, not yet dismissed" and every leg is idempotent so 歸位 or the next negative delta converges

#### Scenario: Deletion purge releases the full possession first
- **WHEN** `purge_npc_memberships` runs for a possessed companion
- **THEN** it runs the same full release unconditionally before unwinding the binding

#### Scenario: Disconnect release lands on the disconnect-only lifecycle point
- **WHEN** `release_on_disconnect` is wired up with the transition change
- **THEN** its caller lands on `Account.at_post_disconnect` (the disconnect-only lifecycle point — `at_post_unpuppet` fires on every deliberate unpuppet, including possession's own release of A, and must NOT run this)

#### Scenario: The handback seam precedes the attribute clear
- **WHEN** `release_for_party_change` runs the full release
- **THEN** it runs the documented handback seam (the transition change's unpuppet-B/re-puppet-A
  ladder; a no-op in this change because no session ever puppets the NPC until then) and the
  mirrored attribute clear

### Requirement: The possess command surface is localized and documented
The character cmdset SHALL mount `possess` (aliases `附身`, English alias retained) taking one bound-companion target, and `unpossess` (aliases `歸位`), both localized in shape (Traditional Chinese messages, stable reason mapping). `possess` runs `enter_possession` and surfaces its gate lines; `unpossess` runs `release_possession(player, npc, "handback")`.

#### Scenario: The command pair resolves targets and reports gate lines
- **WHEN** the player runs 附身 on an absent, ambiguous, or unbound target
- **THEN** the fixed Traditional Chinese refusal shows and no possession state changes

#### Scenario: 歸位 releases the current possession
- **WHEN** the player runs 歸位 while possessing
- **THEN** the possession attributes clear and the fixed release line shows

#### Scenario: Both commands are documented
- **WHEN** the curated docs manifest is checked
- **THEN** both commands appear in `docs/game/command-reference.md` and `docs/game/commands.md`,
  keeping `tests/test_command_docs.py` green

### Requirement: A possessed NPC is autonomy-silent and unreachable by dialogue
An NPC with `db.possessed_by` set SHALL be autonomy-silent: `world/rules/service_gate.py::schedule_silenced(npc)` SHALL return true for it as the predicate's OR-ed second trigger, so `settle_npc_schedules` moves or re-states nothing for it; `LLMNPC.at_talked_to` (and the freeform dialogue seam behind it) SHALL refuse the possessed self with the fixed 「他現在無法回應你。」line and write no dialogue, memory, or affinity state.

#### Scenario: The possessed companion's schedule stays silent
- **WHEN** a possessed guard-type companion crosses a full authored shift window
- **THEN** no entry settles, no event names it, and its state is unchanged

#### Scenario: Talking to the possessed self is refused without state
- **WHEN** the player (on character A) talks freely to companion B while possessing B
- **THEN** the fixed refusal line shows and no dialogue session, memory append, or affinity change occurs

#### Scenario: Possessed-companion combat still credits the owner's quest
- **WHEN** the possessed companion lands the killing blow on a quest-tracked monster
- **THEN** the owning player's quest progresses exactly as if the companion fought unpossessed

#### Scenario: The silence trigger rides the single service-gate site
- **WHEN** `schedule_silenced(npc)` evaluates a possessed NPC
- **THEN** possession is the predicate's OR-ed second trigger at the same single site the
  place-bound travel trigger lives

#### Scenario: Possessed-companion exploration keeps crediting the owner
- **WHEN** a possessed companion produces exploration results
- **THEN** they keep crediting the owning player's quests exactly as for any bound companion —
  a ratified feature: possession moves the camera, not the ownership
