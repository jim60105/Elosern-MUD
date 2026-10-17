# Design: 給 and 取回 member transfer commands

## Context

See proposal.md. `CmdGive` inherits Evennia's give with `rhs_split = ("=", " to ")` and `NumberedTargetCommand` (accepts `給 2 個 X = Y`). It resolves the target with `caller.search(self.rhs)` and handles quest delivery through `advance_deliveries_for_transfer`.

## Goals / Non-Goals

**Goals:** text parity for both directions with identical rejection semantics; no regression for non-member gives and quest deliveries.

**Non-Goals:** changing `交付`, `拿`, `丟`; a WebClient surface (the bag tab is a later change).

## Decisions

- **Routing test first.** Before the legacy search, `CmdGive` tries `resolve_member_token(caller, rhs)`; a match routes to the rule, a `not_party_member` result falls through to the legacy path (so NPC merchants, quest targets and other players keep today's behaviour). Alternative: always route through the rule; rejected because it would break quest deliveries to non-members.
- **Item token.** Both commands accept the registry key or the held display name, resolved against the giver's canonical inventory (same fallback rule `_search_held` uses), then pass the key to the rule. Quantity defaults to 1.
- **取回 receiver** is `resolve_commander(caller)`, never the caller, so a possessed companion retrieving still fills the commander's bag.
- **Messages** come only from the rule's fixed message table; success lines: 「你把 {n} 個{物品}交給了{成員}。」 and 「你從{成員}那裡取回了 {n} 個{物品}。」.

## Risks / Trade-offs

- [A companion who is also a quest delivery target] → `給` to a member no longer advances the delivery; `交付` remains the explicit delivery command. Recorded as a planning gap.

## Migration Plan

Pre-release; revert the implementation commit.

## Verification and documentation ownership

`EvenniaCommandTest`/`EvenniaTest`: member give, non-member give unchanged (delivery still advances), `取回` success, possession retrieval to commander, in-combat refusal, equipped/locked/unknown member refusals with zero writes. Update both command documents and run `tests/test_command_docs.py`; shard contract; `tools.contract_gate`.
