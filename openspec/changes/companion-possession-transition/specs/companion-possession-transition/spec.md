# Delta spec: companion-possession-transition (companion-possession-transition)

New capability: the real control transfer replacing the rules change's two named seams, plus the
disconnect hook wiring and the entrance rendering. Every puppet hop follows verify-then-recover.

## ADDED Requirements

### Requirement: Entering possession transfers the puppet with a verify-then-recover ladder
`_transfer_puppet` SHALL, in order: retire the acting session's in-flight action sequence and bump
its presentation epoch (`retire_sequence` + the coordinator reset that `reset_client_sequence`
performs — `send_unpuppet_transition` only signals the browser and bumps nothing; the contract is
that a completion for A can never publish after the swap); additively grant
`puppet:id(<account>)` on the NPC without replacing its default lock rule; puppet the NPC on the
acting session; and verify `get_puppet(session) is npc` because `puppet_object` may refuse
silently. On any refused or unverified hop the ladder SHALL re-puppet A on the session, strip the
lock grant, clear the possession mirrors, and surface a fixed 「此刻無法附身於他。」line. After the
verified hop, A's original puppet SHALL be released through the same unpuppet path OOC 離開角色
uses, so `at_post_unpuppet` fires for A exactly once (including the accepted epithet rest-point
nomination). The retire/epoch hop SHALL call the landed session-level helpers —
`web/webclient/actions/dispatcher.py::retire_sequence` and
`web/webclient/presentation/ingress.py::send_unpuppet_transition` — rather than re-implement
their sequencing.

#### Scenario: A verified possession swap leaves B puppeted and A released
- **WHEN** `enter_possession` runs for a gate-passing companion on a live session
- **THEN** the session's puppet is the NPC, the NPC's lock list contains the account grant
  alongside its default rule, and A's sessions are empty

#### Scenario: A silent refusal leaves the world exactly as it was
- **WHEN** `puppet_object` refuses B without raising (lock or capability refusal)
- **THEN** A is re-puppeted on the session, the grant is stripped, the possession attributes are
  cleared, and the fixed refusal line shows

#### Scenario: The epoch retires before the swap
- **WHEN** the acting session carries an in-flight action sequence at possession start
- **THEN** the sequence is retired and the presentation epoch bumped before the NPC puppet is
  attempted, and a completion Deferred started for A's panel can never publish into B's session

### Requirement: The possessed NPC carries a trimmed character act cmdset
`_mount_cmdset` SHALL mount on the puppeted NPC a freshly derived character act cmdset — the
movement/look/examine/act surface plus `unpossess` (歸位) — minus an explicit denylist: the
switcher/play/quell command family (whose retire logic assumes the session puppet is the caller's
own character) and the character-panel commands whose presenters read PlayerCharacter-only state.
`_unmount_cmdset` SHALL rebuild the NPC's default cmdset. Denylist membership SHALL be pinned by a
test against the landed `CharacterCmdSet`, not by prose.

#### Scenario: 歸位 is reachable while possessing
- **WHEN** the possessed NPC's mounted cmdset is inspected
- **THEN** `unpossess` and 歸位 resolve within it

#### Scenario: The switcher family is absent while possessing
- **WHEN** the mounted cmdset is inspected for the switch/play/quell family
- **THEN** none of them resolve

#### Scenario: Release restores the NPC's own cmdset
- **WHEN** possession releases
- **THEN** the NPC's cmdset is rebuilt from its default and the mounted copy is gone

### Requirement: Releasing possession returns the puppet to the owner with the same ladder
`_release` (inside `release_possession`) SHALL unpuppet the NPC, strip its account lock grant, and
re-puppet A on the same session with the same verify-then-recover ladder. If the NPC unpuppets but
A's re-puppet silently refuses, the possession attributes SHALL NOT clear, the error SHALL be
logged through the observability facade with `step="possession_release"`, and the fixed
「你的身體搖搖欲墜,彷彿從很深的水裡被拉回來。」line SHALL be sent so a 歸位 retry (idempotent
attributes) can complete the return.

#### Scenario: A clean release leaves A puppeted and B lock-free
- **WHEN** `release_possession` runs while the session puppets the companion
- **THEN** the session puppets A again, the NPC holds no account grant, and the possession
  attributes are clear

#### Scenario: A refused return keeps the state and says so
- **WHEN** A's re-puppet silently refuses during release
- **THEN** the possession attributes remain set, the fixed return line shows, and the facade logs
  the error with `step="possession_release"`

### Requirement: Disconnecting while possessing releases possession through the account disconnect hook
`Account.at_post_disconnect` SHALL call `possession.release_on_disconnect(self)` — the
disconnect-only lifecycle point, verified in Evennia 6.1 to fire solely from
`ServerSession.disconnect()` and never from `Account.unpuppet_object`'s deliberate unpuppet or a
reload — and `PlayerCharacter.at_post_unpuppet` SHALL NOT gain any possession branch (it fires on
every puppet swap, including possession's own release of A; wiring cleanup there would clear the
fresh mirrors mid-possession). NOTHING in possession code SHALL inspect server shutdown state —
reload keeps sessions, so no release fires and Evennia's own re-adoption re-puppets the persisted
possession state (the retained lock grant makes this possible). Possession attributes SHALL
survive a save/reload round-trip intact.

#### Scenario: Disconnect drops the puppet and the state together
- **WHEN** the possessing session disconnects
- **THEN** `release_on_disconnect` runs for the account, the NPC is unpuppeted, the grant
  stripped, both possession attribute mirrors cleared, and A is not force-puppeted anywhere

#### Scenario: A possession-internal unpuppet never triggers the release
- **WHEN** entering possession deliberately unpuppets A, or 歸位 unpuppets B
- **THEN** no disconnect release runs (the hook is not on the unpuppet path) and the intended
  possession state survives the swap intact

#### Scenario: Reload preserves a live possession
- **WHEN** attributes are saved and re-read without a disconnect (the reload path)
- **THEN** `possession` and `possessed_by` remain set and the NPC's account grant remains granted

### Requirement: A possessed character reads as entranced in the room
A `PlayerCharacter` whose `db.possession` mirror is non-null SHALL render in room contents with
the fixed entranced line (呆立入神) appended by its display hook; a null mirror SHALL render
unchanged. The hook SHALL read only the persisted mirror — no session inspection.

#### Scenario: The left-behind body shows entranced
- **WHEN** a room listing includes a character with a live possession mirror
- **THEN** the fixed entranced line renders with the character

#### Scenario: Normal presence after release
- **WHEN** the same character's mirror is cleared
- **THEN** the room listing shows no entranced line
