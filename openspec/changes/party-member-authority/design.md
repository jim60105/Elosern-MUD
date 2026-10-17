# Design: Party member authority boundary

## Context

See proposal.md for motivation. Observed today: `world/rules/combat_session/battlefield.py::authorize_combat_actor` is the only server-side subordinate-actor check, and it is bound to a combat session record. `world/rules/party.py::live_companions` already filters stale dbids, non-NPC entries, backref mismatches and sourceless temporary members, and `combat_companions` treats a companion with stored HP at or below the nonlethal floor (1) as knocked out. Possession stores the owner on `npc.db.possessed_by`; presenters (`status.py`, `character.py`) each re-derive the owner inline.

## Goals / Non-Goals

**Goals:** one pure, read-only boundary every later member-scoped rule calls first; a scope helper the clock-advance callers share; one text resolver the command parsers share.

**Non-Goals:** no change to combat authorization, possession lifecycle, party membership writes, or any mutation. No affinity or bond gate (design §13).

## Decisions

- **Commander resolution.** `resolve_commander(acting)` returns `acting` for a `PlayerCharacter`, and for a possessed, puppeted NPC returns the live owner from `db.possessed_by` when that owner is a `PlayerCharacter`; anything else raises `PartyScopeError("not_party_member")`. Alternative considered: trusting `session.account` puppets; rejected because the deterministic rules must not read transport state.
- **Membership is re-derived, never trusted.** `authorize_member(commander, member_id, purpose, anchor)` accepts an integer dbid only. It resolves the live object, then requires `member is commander` or `member in live_companions(commander)`; otherwise `not_party_member`. Presence requires `member.location is anchor.location` with a non-null location (`member_not_present`). The `act` purpose additionally rejects a companion whose stored HP is at or below 1 (`member_cannot_act`); the `organize` purpose admits it (design §4.1). The commander itself is never "knocked out" by this predicate; defeat aftermath keeps its own rules.
- **Anchor.** The anchor is the commander's room. Per the user's 2026-10-18 decision the whole party (owner body included) follows a possessed traversal (`party-follow-under-possession`), so the possessed companion and the commander are co-located by construction; the room check remains only to exclude a member a failed follow or a non-exit relocation left elsewhere.
- **Ordered scope.** `present_party_scope(acting)` returns a de-duplicated tuple: the commander first, then `live_companions(commander)` in roster order, each kept only when present in the commander's room; possession does not change it. Deterministic ordering keeps clock settlement and snapshot registries reproducible.
- **Text tokens.** `resolve_member_token(acting, token)` compares the stripped token against `npc_display_name` / character key of the commander and effective members (exact match). Zero or multiple matches reject with `not_party_member`; it never falls back to the caller.
- **Combat activity.** `party_in_combat(acting, *members)` returns true when the acting character, the commander or any named member reads an active session (`is_in_active_session`); every combat-barred rule (transfer, booking, field item use) uses it so a possessed figure in a session cannot bypass the bar.
- **Stale possession.** Commander resolution additionally requires `is_player_driven(acting)` (a live puppet session) so a leftover `possessed_by` cannot launder authority.
- **Messages.** `PARTY_SCOPE_MESSAGES` maps each code to one fixed zh-TW line: `not_party_member` 「對方不是你的隊伍成員。」, `member_not_present` 「對方不在這裡。」, `member_cannot_act` 「對方目前無法行動。」.

## Risks / Trade-offs

- [Name collisions in text tokens] → Ambiguity rejects instead of guessing.

## Migration Plan

Pre-release; additive module, no data migration. Revert the implementation commit to roll back.

## Verification and documentation ownership

Pure-logic cases use `unittest.TestCase` with stand-ins; membership, possession and location cases use `EvenniaTest`. The new test module joins exactly one shard. No logging is added (pure reads), so the observability lint is not required; run `uv run --locked python -m tools.contract_gate`.
