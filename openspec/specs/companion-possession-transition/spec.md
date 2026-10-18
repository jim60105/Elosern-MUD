## Purpose
Puppet transfer with lock grant/revocation, cmdset mount/unmount, the verify-then-recover ladder at every hop, the disconnect hook wiring, and entranced rendering.

## Requirements

### Requirement: Entering possession transfers the puppet with a verify-then-recover ladder
`_transfer_puppet` SHALL, in order: retire the acting session's in-flight action sequence and bump its presentation epoch; additively grant `puppet:id(<account>)` on the NPC without replacing its default lock rule; puppet the NPC on the acting session; and verify `get_puppet(session) is npc`. On any refused or unverified hop the ladder SHALL re-puppet A on the session, strip the lock grant, clear the possession mirrors, and surface a fixed 「此刻無法附身於他。」line.

#### Scenario: A verified possession swap leaves B puppeted and A released
- **WHEN** `enter_possession` runs for a gate-passing companion on a live session
- **THEN** the session's puppet is the NPC, the NPC's lock list contains the account grant alongside its default rule, and A's sessions are empty

#### Scenario: The verification step covers silent refusal
- **WHEN** the hop verifies `get_puppet(session) is npc`
- **THEN** the check exists because `puppet_object` may refuse silently

#### Scenario: A silent refusal leaves the world exactly as it was
- **WHEN** `puppet_object` refuses B without raising (lock or capability refusal)
- **THEN** A is re-puppeted on the session, the grant is stripped, the possession attributes are cleared, and the fixed refusal line shows

#### Scenario: The epoch retires before the swap
- **WHEN** the acting session carries an in-flight action sequence at possession start
- **THEN** the sequence is retired and the presentation epoch bumped before the NPC puppet is attempted, and a completion Deferred started for A's panel can never publish into B's session

#### Scenario: The retire/epoch hop performs the coordinator reset
- **WHEN** `_transfer_puppet` runs the retire/epoch hop
- **THEN** it performs `retire_sequence` plus the coordinator reset that `reset_client_sequence` performs — `send_unpuppet_transition` only signals the browser and bumps nothing — and the contract is that a completion for A can never publish after the swap

#### Scenario: The verified hop releases A through the OOC 離開角色 path
- **WHEN** the possession hop is verified
- **THEN** A's original puppet is released through the same unpuppet path OOC 離開角色 uses, so `at_post_unpuppet` fires for A exactly once (including the accepted epithet rest-point nomination)

#### Scenario: The hop calls the landed session-level helpers
- **WHEN** `_transfer_puppet` performs the retire/epoch hop
- **THEN** it calls `web/webclient/actions/dispatcher.py::retire_sequence` and `web/webclient/presentation/ingress.py::send_unpuppet_transition` rather than re-implement their sequencing

### Requirement: The possessed NPC carries a trimmed character act cmdset
`_mount_cmdset` SHALL mount on the puppeted NPC a freshly derived character act cmdset — the movement/look/examine/act surface plus `unpossess` (歸位) — minus an explicit denylist: the switcher/play/quell command family and the character-panel commands whose presenters read PlayerCharacter-only state. `_unmount_cmdset` SHALL rebuild the NPC's default cmdset.

#### Scenario: 歸位 is reachable while possessing
- **WHEN** the possessed NPC's mounted cmdset is inspected
- **THEN** `unpossess` and 歸位 resolve within it

#### Scenario: The switcher family is absent while possessing
- **WHEN** the mounted cmdset is inspected for the switch/play/quell family
- **THEN** none of them resolve

#### Scenario: Release restores the NPC's own cmdset
- **WHEN** possession releases
- **THEN** the NPC's cmdset is rebuilt from its default and the mounted copy is gone

#### Scenario: The switcher family is denylisted for its retire logic
- **WHEN** the denylist's scope is justified
- **THEN** the switcher/play/quell command family is excluded because its retire logic assumes the session puppet is the caller's own character

#### Scenario: Denylist membership is pinned by a test
- **WHEN** denylist membership is verified
- **THEN** it is pinned by a test against the landed `CharacterCmdSet`, not by prose

### Requirement: Releasing possession returns the puppet to the owner with the same ladder
`_release` (inside `release_possession`) SHALL unpuppet the NPC, strip its account lock grant, and re-puppet A on the same session with the same verify-then-recover ladder. If the NPC unpuppets but A's re-puppet silently refuses, the possession attributes SHALL NOT clear, the error SHALL be logged through the observability facade with `step="possession_release"`, and the fixed 「你的身體搖搖欲墜,彷彿從很深的水裡被拉回來。」line SHALL be sent so a 歸位 retry (idempotent attributes) can complete the return.

#### Scenario: A clean release leaves A puppeted and B lock-free
- **WHEN** `release_possession` runs while the session puppets the companion
- **THEN** the session puppets A again, the NPC holds no account grant, and the possession attributes are clear

#### Scenario: A refused return keeps the state and says so
- **WHEN** A's re-puppet silently refuses during release
- **THEN** the possession attributes remain set, the fixed return line shows, and the facade logs the error with `step="possession_release"`

### Requirement: Disconnecting while possessing releases possession through the account disconnect hook
`Account.at_post_disconnect` SHALL call `possession.release_on_disconnect(self)` and `PlayerCharacter.at_post_unpuppet` SHALL NOT gain any possession branch. The hook SHALL contain no possession business logic beyond that single call: `release_on_disconnect` SHALL return without releasing when any live session of the account still puppets an object carrying a `possessed_by` mirror, and SHALL otherwise release every possession reachable through the account's characters and sessions.

#### Scenario: Disconnect drops the puppet and the state together
- **WHEN** the possessing session disconnects
- **THEN** `release_on_disconnect` runs for the account, the NPC is unpuppeted, the grant stripped, both possession attribute mirrors cleared, and A is not force-puppeted anywhere

#### Scenario: A possession-internal unpuppet never triggers the release
- **WHEN** entering possession deliberately unpuppets A, or 歸位 unpuppets B
- **THEN** no disconnect release runs (the hook is not on the unpuppet path) and the intended possession state survives the swap intact

#### Scenario: Reload preserves a live possession
- **WHEN** attributes are saved and re-read without a disconnect (the reload path)
- **THEN** `possession` and `possessed_by` remain set and the NPC's account grant remains granted

#### Scenario: A still-driven possession survives one session's disconnect
- **WHEN** `release_on_disconnect` is called for an account while another of its live sessions still puppets the possessed NPC
- **THEN** no release occurs and the possession mirrors, grant, and puppet remain intact

#### Scenario: The guard unblocks once the last driving session is gone
- **WHEN** the remaining session puppeting the possessed NPC disconnects afterward
- **THEN** `release_on_disconnect` finds no possessed-puppet session, releases fully, and the mirrors and grant are cleared

#### Scenario: The disconnect hook is disconnect-only
- **WHEN** the hook's firing is verified in Evennia 6.1
- **THEN** `Account.at_post_disconnect` fires solely from `ServerSession.disconnect()` and never from `Account.unpuppet_object`'s deliberate unpuppet or a reload

#### Scenario: Cleanup stays off the unpuppet path
- **WHEN** deciding where to wire possession cleanup
- **THEN** `PlayerCharacter.at_post_unpuppet` gains no possession branch, because it fires on every puppet swap, including possession's own release of A, and wiring cleanup there would clear the fresh mirrors mid-possession

#### Scenario: The multisession skip lives in the release helper
- **WHEN** the multisession skip is located
- **THEN** it is owned by `release_on_disconnect` itself, and the skip applies when the possession is actively driven on another session

#### Scenario: Session-and-character scan is the sole discovery mechanism
- **WHEN** `release_on_disconnect` discovers possessions to release
- **THEN** the scan over live sessions and owned characters is the sole discovery mechanism — no account-ownership query over NPC objects, which companion NPCs never satisfy

#### Scenario: Possession code never inspects server shutdown state
- **WHEN** a reload keeps sessions alive
- **THEN** nothing in possession code inspects server shutdown state, so no release fires and Evennia's own re-adoption re-puppets the persisted possession state (the retained lock grant makes this possible), and possession attributes survive the save/reload round-trip intact

#### Scenario: Evennia unpuppets the departing session before the hook fires
- **WHEN** the guard runs at disconnect time (ordering verified in Evennia 6.1)
- **THEN** `ServerSession.at_disconnect` has already unpuppeted the departing session before `Account.at_post_disconnect` fires, so the disconnecting session never still puppets anything at guard time and the scan sees only remaining sessions; tests simulating a disconnect SHALL clear the departing session's puppet before invoking the hook

### Requirement: A possessed character reads as entranced in the room
A `PlayerCharacter` whose `db.possession` mirror is non-null SHALL render in room contents with the fixed entranced line (呆立入神) appended by its display hook; a null mirror SHALL render unchanged. The hook SHALL read only the persisted mirror — no session inspection.

#### Scenario: The left-behind body shows entranced
- **WHEN** a room listing includes a character with a live possession mirror
- **THEN** the fixed entranced line renders with the character

#### Scenario: Normal presence after release
- **WHEN** the same character's mirror is cleared
- **THEN** the room listing shows no entranced line

### Requirement: Normal possession release preserves the companion's room presence

A release for `handback` or `party_change` SHALL preserve the companion's occupied pre-release room and party membership at the release boundary, with no off-grid stash or stale logout-location state. An initially co-located companion SHALL remain co-located with its owner and eligible for possession, following, and combat collection under their existing gates. Later membership removal SHALL retain its existing policy. Disconnect and link-dead recovery are outside this requirement.

#### Scenario: 歸位 leaves both party members in the room

- **WHEN** an owner possesses a bound companion in their shared room and performs 歸位 without either figure changing rooms
- **THEN** control returns to the owner, both figures remain in that room and its contents, the same companion remains in the owner's party, both possession bindings are clear, and the companion has no stale logout-location state

#### Scenario: Party-change handback preserves presence before membership removal

- **WHEN** a possession-carrying party change requests handback while the owner and companion share a room
- **THEN** handback returns control to the owner and leaves the companion in that room and still in the party at the release boundary, with both possession bindings clear and no stale logout-location state
- **AND** any subsequent actual membership removal is performed by its existing owning operation and does not stash the companion off-grid

#### Scenario: The released companion can be possessed again

- **WHEN** either normal release reason completes for a co-located pair with membership retained and all other possession gates still passing
- **THEN** a subsequent `possess` of that same companion succeeds without operator repair or an intervening login

#### Scenario: The released companion follows and participates in combat collection

- **WHEN** either normal release reason completes for a co-located pair with membership retained, then the owner moves through a valid exit and ordinary party following runs
- **THEN** the same companion follows into the destination room and is included by the existing combat-companion collection when its other eligibility conditions hold

#### Scenario: Release preserves an intentionally remote companion's position

- **WHEN** a failed follow left the owner's body in another room before a normal release (possessed traversal otherwise brings the whole party along)
- **THEN** the companion remains in its occupied pre-release room, the owner's body stays where the failed follow left it, and release performs no reunion teleport or relaxation of co-location gates

#### Scenario: A failed handback restores the occupied room state

- **WHEN** the owner re-puppet is refused or a later release write fails after the companion unpuppets
- **THEN** the existing failure and recovery contract applies, the original possession remains recoverable, and both persisted and in-process companion location and logout-location state equal their pre-release values
- **AND** a subsequent successful retry leaves the companion in its occupied room with no stale logout-location state

#### Scenario: Repeated release does not move the companion

- **WHEN** a completed normal release is requested again with no active possession
- **THEN** it remains a no-op, with no movement, membership write, or duplicate successful-release event
