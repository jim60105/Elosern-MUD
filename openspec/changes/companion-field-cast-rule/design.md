# Design: Companion field casting rule and text suffix

## Context

See proposal.md. `cast_in_field(actor, skill_key, *, targets, opening_target, scale, context)` normalizes a single monster target to an opening anchor, refuses damaging skills without an anchor, and settles through `settle_out_of_combat_cast(ActionRequest(actor=actor, ...))`. `_step6_skill_practice` awards `request.actor`. `CmdCast` parses `cast <skill>[@<scale>][=<target>]` and delegates to the combat session when one is active.

## Goals / Non-Goals

**Goals:** a member-explicit wrapper with no duplicated resolution; text parity; stable rejections.

**Non-Goals:** WebClient payloads (`companion-field-cast-actions`), unlock wording (`party-unlock-notices`).

## Decisions

- **Wrapper, not fork.** `cast_as_member` authorizes, then calls `cast_in_field(member, ...)`. The settlement scope from `party-field-settlement-scope` makes the commander and other present members settle with the cast.
- **Companion openings are allowed** (user decision of 2026-10-18). `cast_in_field(member, ...)` already routes a monster anchor to `initiate_field_combat(actor=member, ...)`; the initiation resolves the commander, builds the session over the commander's party (the possessed or commanded companion is a party participant) and seeds the skill as the companion's opening draft entry, so the v7 rule "an encounter-starting selection may seed the initiating character's draft entry" applies to the companion. Costs and practice are charged when that entry resolves in the round, once; no command time is charged (combat time).
- **Text suffix** is parsed off the end of the argument string (`\s+由\s+(?P<member>\S.*)$`) before the existing `=`/`@` parsing; the member resolves through `resolve_member_token`. In an active session the command builds the same actor skill command that `combat command <actor-token> skill ...` builds and submits it through the same facade, so draft semantics stay identical.

## Risks / Trade-offs

- [`由` appearing inside a target display name] → The suffix must be the final whitespace-separated `由 <name>` pair; ambiguity rejects via the member token resolver.

## Migration Plan

Pre-release; additive. Revert the implementation commit.

## Verification and documentation ownership

EvenniaTest with a synthetic heal and SELF buff: actor MP charged, target healed, SELF on the caster, XP on the caster (independent expected numbers: caster MP 20 with cost 8 ends at 12), six-second advance settles the party once, knocked-out/absent/non-member/unowned refusals, companion opening creating one commander-owned session with the companion's draft entry and no resource change before resolution, forged/absent caster rejected before any session. Command tests for suffix parsing out of and in combat. Update both command documents; `tests/test_command_docs.py`; shard contract; `tools.contract_gate`.
