# Design: Party panel v3 and viewed-member selection

## Context

See proposal.md. `party.py` builds v2 rows from `live_companions(owner)` (owner resolved from the possessed NPC's back-reference), with HP from `stored_gauge_pair` and portraits gated by `build_art_view`. `party_actor_selection.py` shows the existing pattern for a session-scoped, read-context-copied combat selection (bound to epoch and puppet, retired on unpuppet).

## Goals / Non-Goals

**Goals:** exact v3 schema; one per-session selection that survives possession and never authorizes; deterministic fallback.

**Non-Goals:** the member-tab detail (`party-member-panel`), any client window (later), changing the combat actor selection.

## Decisions

- **Commander row** uses the player character's own identity, display name (`key`), the same portrait resolution path the art view admits for the commander, and true traits. Alternative: a separate `commander` object outside `slots`; rejected because the rail treats every member uniformly and the design calls it row 0.
- **knocked_out** reuses the `party-member-authority` predicate (companion stored HP at or below 1); always false for the commander row.
- **Selection store** `session.ndb.party_view = PartyViewSelection(commander_id, member_id, tab)`. Unlike the combat actor selection it is *not* retired on unpuppet, because possession unpuppets the owner and the window must stay identical; it is bound to the commander id and dropped with the session. The coordinator copies it into `PresentationContext.party_view`; `resolve_viewed_member(context)` returns the live member when still effective, else the commander.
- **Action** `party.view_member` validates exactly `{member_id, tab}`, authorizes membership only, writes the selection, calls `mark_unlocks_seen` for `tab == "skills"`, and returns success with `affected_panels=("party",)`; each later protocol change appends its viewed-member panel to this tuple.
- **Bounds**: rows ≤ 17 (commander + `PARTY_MAX_SLOTS`), 15 fields per row; the validator keeps the canonical byte bound and a maximal-row fixture proves it.

## Risks / Trade-offs

- [Existing consumers assume companions only] → All JS consumers filter `role === "companion"`; Vitest covers lineup and drawer.
- [Selection on a second browser session] → Per-session by design; each session has its own viewed member.

## Migration Plan

Pre-release clean cutover; revert the implementation commit.

## Verification and documentation ownership

Python: v3 validator accept/reject cases, maximal-row bound, commander-first ordering, possession-identical payload, knocked-out/unread flags, fallback after leave/delete; action schema, forged member, possession persistence, skills-tab clearing. JS: mirror parity, consumer filtering. No command changes. Shard contract if modules are added; `tools.contract_gate`.
