# Design: Companion-initiated field combat

## Context

See proposal.md. Code facts verified by review: `engage_group` requires a `PlayerCharacter`; `_candidate_record` and `_prepare_opening` build the candidate on the actor; `initiate_field_combat` snapshots the actor's `active_combat`/`dialogue_session`; `submit_opening_action` reads `read_session(actor)` and confirms with `int(actor.pk)` as both commander and actor. `authorize_combat_actor(commander, actor, ...)` already accepts a bound, co-located, eligible companion.

## Goals / Non-Goals

**Goals:** a caster/commander split through initiation with the commander path byte-identical; the same opening confirmation in the client (owned by `companion-field-cast-actions`).

**Non-Goals:** new combat command kinds; any change to required-actor rules; text-client confirmation (the text cast has never had one).

## Decisions

- **Explicit amendment** of the earlier batch decision (`companion_cannot_open`), per the user's 2026-10-18 decision.
- **Signature**: `initiate_field_combat(actor, skill_key, target, scale=1.0)` keeps its name; internally `commander = resolve_commander(actor)` (the actor itself for the commander). Every session-keyed read/write uses `commander`; the opening entry uses `actor` through `authorize_combat_actor(commander, actor, ...)` so forged/stale casters are rejected by the existing guard.
- **Player side** = `commander` + `combat_companions(commander)`; the caster must be among them (else `member_not_present`/`member_cannot_act`).
- **Opening order** `opening_first_actor` = caster key; initiative and required-actor completion are unchanged, so the commander still commands before the round resolves.
- **Rollback snapshots** cover the commander and the caster (session attribute on the commander, dialogue state on both).
- **Possessed caster** (the puppet) and **commanded caster** (commander puppet, companion actor) take the same path.

## Risks / Trade-offs

- [Touching the shared initiation path] → The commander path keeps its existing tests unchanged; companion tests are additive.

## Migration Plan

Pre-release; revert the implementation commit.

## Verification and documentation ownership

EvenniaTest: companion initiator (possessed and commanded) creates one commander-owned session with the caster's opening entry and first-actor key, no command time, cost/practice only at resolution; failed initiation leaves nothing; forged/absent/knocked-out caster rejected before any session; commander initiation unchanged. Command tests for `cast … 由 <成員>` at a monster. Both command documents; observability lint; shard registration; `tools.contract_gate`.
