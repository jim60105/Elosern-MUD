## Purpose

Defines the party core: the bounded, persistent, single-writer membership binding between a player and up to four NPC companions (`world/rules/party.py` owns `player.db.party` and `npc.db.party_member`), the AI-judged `invite` / `leave` command surfaces with the fixed offline threshold fallback, the wired auto-leave rule that ends a party when affinity drops below the invite threshold, and the deletion-purge path that never lets a removed NPC consume a companion slot.

## Requirements

### Requirement: Party membership is bounded, persistent, and single-writer

`world/rules/party.py` SHALL be the sole writer of party membership: `player.db.party` holds the list of companion NPC dbids (at most 4) and each companion's `npc.db.party_member` holds the player's dbid. `join_party(npc, player)` SHALL require an NPC target, co-location (same room), no existing binding, and a party below the 4-companion bound; `leave_party(npc, player, reason)` SHALL remove the binding regardless of the reason. Both SHALL commit the player-side and NPC-side writes atomically, SHALL restore both entities' in-process caches on failure, SHALL be idempotent under re-application, and SHALL survive reloads.

#### Scenario: A valid join binds both sides
- **WHEN** a player invites a co-located NPC with 2 companions already
- **THEN** the NPC appears in `player.db.party`, the NPC's `party_member` is the player, and the party size is 3

#### Scenario: The party bound is four companions
- **WHEN** a player with 4 companions invites a fifth NPC
- **THEN** the join is rejected with a full-party outcome and no binding changes

#### Scenario: A remote NPC cannot join
- **WHEN** a player invites an NPC in another room
- **THEN** the join is rejected and no binding changes

#### Scenario: A duplicate join is a no-op
- **WHEN** a join is attempted for an NPC already bound to the player
- **THEN** the join is rejected and no binding changes

#### Scenario: A failed join restores both entities
- **WHEN** the NPC-side write fails after the player-side write applied
- **THEN** both database and in-process values return to their pre-join state and no partial binding is observable

#### Scenario: Membership survives a reload
- **WHEN** a player with companions disconnects and reconnects
- **THEN** `player.db.party` and each companion's `party_member` are unchanged

### Requirement: The invite command proposes a party through the AI-judged dialogue seam

The character cmdset SHALL provide `invite <npc> [訊息]` (aliases 邀請, 組隊) that resolves a local NPC target (absent or ambiguous targets produce Traditional Chinese errors, mirroring `talk`), preflights the deterministic gate (an NPC with an eligible free-form dialogue surface — an `LLMNPC` — not already a companion, party not full), and then sends the player's invitation message through the guarded dialogue seam with the NPC's affinity context; a webclient action SHALL offer the same flow with the injected client. The reply's speech SHALL be shown to the player. A `party_invite {accept: true}` intent SHALL be verified and applied through `join_party` (rechecking co-location, binding, and the 4-companion bound) and the player SHALL be notified of the joined companion; `accept: false` SHALL notify of the refusal and change nothing; any illegal or unverifiable intent SHALL keep the speech and change nothing. When the dialogue layer is disabled, unreachable, or retry-exhausted, the invitation SHALL degrade to a fixed threshold decision (`affinity >= 70`, the 羈絆 stage floor) with deterministic accept/reject lines; the AI, when present, SHALL NOT be bound by that threshold.

#### Scenario: A co-located NPC is invited and joins
- **WHEN** a player invites a co-located NPC and the dialogue reply carries `party_invite` with `accept: true`
- **THEN** the player sees the NPC's speech and a join notification, and the membership binding exists

#### Scenario: The NPC declines through the AI
- **WHEN** a player invites an NPC and the dialogue reply carries `party_invite` with `accept: false`
- **THEN** the player sees the NPC's refusal speech and no binding is created

#### Scenario: An illegal party intent keeps the speech
- **WHEN** the reply's intent is not a valid `party_invite` payload
- **THEN** the speech is shown, the intent is discarded, and no binding is created

#### Scenario: Offline invitations fall back to the fixed threshold
- **WHEN** the dialogue layer is unavailable and the NPC's affinity is 70 or higher
- **THEN** the invitation succeeds with a deterministic acceptance line and the binding is created; below 70 it is refused with a deterministic rejection line

#### Scenario: The AI is not bound by the threshold
- **WHEN** the dialogue layer is available and the NPC's affinity is below 70
- **THEN** the decision is entirely the reply's `party_invite` value — the threshold never overrides it

#### Scenario: An AI decline is never overridden by the threshold
- **WHEN** the dialogue layer is available, the reply's intent is `party_invite` with `accept: false`, and the NPC's affinity is 70 or higher
- **THEN** the refusal stands, the threshold is not consulted, and no binding is created

#### Scenario: Inviting an already-bound companion reports a clear result
- **WHEN** a player invites an NPC that is already a companion
- **THEN** the invite is rejected before any dialogue call with a Traditional Chinese message and no state changes

#### Scenario: A non-dialogue NPC cannot be invited
- **WHEN** a player invites a present NPC without an eligible free-form dialogue surface
- **THEN** the invite is rejected before any dialogue call with a Traditional Chinese message and no state changes

#### Scenario: A party filled after the AI accepted is surfaced to the player
- **WHEN** the AI replies `accept: true` but the party became full before `join_party` ran
- **THEN** the NPC's speech is shown, the join is rejected with the full-party reason, and the player receives the fixed Traditional Chinese full-party message

#### Scenario: A full party blocks the invite before the AI call
- **WHEN** a player with 4 companions invites a fifth NPC
- **THEN** the invite is rejected with a full-party error and no dialogue call is made

#### Scenario: The invite command surface is documented
- **WHEN** the command reference is inspected
- **THEN** `invite` and its aliases and syntax appear in `docs/game/command-reference.md`

### Requirement: The leave command dismisses a companion without affinity change

The character cmdset SHALL provide `leave <npc>` (alias 解散) that resolves a bound companion (absent, ambiguous, or unbounded targets produce Traditional Chinese errors) and dismisses it through `leave_party(npc, player, reason="dismissed")`. Dismissal SHALL NOT change affinity in either direction and SHALL notify the player. A webclient action SHALL offer the same flow.

#### Scenario: Dismissal removes the binding
- **WHEN** a player dismisses a bound companion
- **THEN** `player.db.party` and the NPC's `party_member` are cleared and the player is notified

#### Scenario: Dismissal keeps affinity unchanged
- **WHEN** a player dismisses a companion with a 信賴-stage record
- **THEN** the NPC's affinity value is unchanged

#### Scenario: An unbounded target is rejected
- **WHEN** a player runs `leave` on an NPC that is not a companion
- **THEN** the command reports the Traditional Chinese error and no state changes

#### Scenario: The leave command surface is documented
- **WHEN** the command reference is inspected
- **THEN** `leave` and its alias appear in `docs/game/command-reference.md`

### Requirement: Companions auto-leave when affinity drops below the invite threshold

The auto-leave recheck hook installed by `affinity-system` SHALL be wired: after every negative affinity delta, when the NPC is a bound companion and the NPC's affinity toward the player drops below the invite threshold (70), the hook SHALL call `leave_party(npc, player, reason="affinity_below_threshold")` as part of the affinity write's transaction — a failed leave SHALL roll back the entire negative-delta operation so "affinity below threshold but still bound" is unreachable — and the write API SHALL return the auto-leave notification line, which the caller SHALL send to the player only after its own transaction commits. The writer SHALL never send the notification itself. A negative delta that leaves affinity at or above the threshold SHALL NOT end the party.

#### Scenario: Below-threshold affinity ends the party
- **WHEN** a bound companion's affinity drops from 70 to 69 through a negative delta
- **THEN** the party binding is removed with the auto-leave reason, the write API returns the notification line, and the caller notifies the player only after the write commits

#### Scenario: At-threshold affinity keeps the party
- **WHEN** a bound companion's affinity drops to exactly 70 through a negative delta
- **THEN** the party binding remains

#### Scenario: A failed auto-leave rolls back the affinity write
- **WHEN** the leave write fails after the affinity value was lowered below the threshold
- **THEN** the affinity value and both party attributes return to their pre-delta values, the companion remains bound, and no notification is sent

#### Scenario: Non-companions are unaffected by the hook
- **WHEN** a negative delta applies to an NPC that is not a companion
- **THEN** no party call or notification occurs

### Requirement: Deleting an NPC purges its party bindings

When an NPC is deleted (instance reclamation, scene teardown, or any `delete()`), the typeclass deletion hook SHALL invoke the party module's purge API, which SHALL remove the NPC's dbid from every player's `db.party` and clear the NPC's `party_member` in one transaction. A party API encountering a stale dbid (an NPC that no longer exists) SHALL treat it as an absent companion — never a crash — and a player's companion capacity SHALL never be permanently consumed by a deleted NPC.

#### Scenario: Deleting a companion frees its slot
- **WHEN** a bound companion NPC is deleted
- **THEN** the player's `db.party` no longer contains the NPC's dbid, the party size shrinks, and a fifth invitation becomes possible

#### Scenario: A stale dbid reads as an absent companion
- **WHEN** a party API encounters a party entry whose NPC no longer exists
- **THEN** the API treats it as absent without raising and the player's remaining companions stay intact
