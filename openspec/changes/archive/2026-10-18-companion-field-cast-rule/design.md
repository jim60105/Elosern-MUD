# Design: Companion field casting rule and text suffix

## Context

See proposal.md. `cast_in_field(actor, skill_key, *, targets, opening_target, scale, context)` normalizes a single monster target to an opening anchor, refuses damaging skills without an anchor, and settles through `settle_out_of_combat_cast(ActionRequest(actor=actor, ...))`. `_step6_skill_practice` awards `request.actor`. `CmdCast` parses `cast <skill>[@<scale>][=<target>]` and delegates to the combat session when one is active.

## Goals / Non-Goals

**Goals:** a member-explicit wrapper with no duplicated resolution; text parity; stable rejections.

**Non-Goals:** WebClient payloads (`companion-field-cast-actions`), unlock wording (`party-unlock-notices`).

## Decisions

- **Wrapper, not fork.** `cast_as_member` authorizes, then calls `cast_in_field(member, ...)`. The settlement scope from `party-field-settlement-scope` makes the commander and other present members settle with the cast.
- **Companion openings** are allowed (user decision of 2026-10-18) but owned by `companion-field-combat-opening`, because `engage_group`, `_candidate_record`, `_prepare_opening` and `submit_opening_action` all assume the initiator is the commander. This change only routes a companion's monster target to `cast_in_field`'s existing initiation branch; until the next change lands that branch returns the existing `NOT_A_PLAYER` session rejection (a forward-declared seam, tested as such).
- **Text suffix** is parsed off the end of the argument string (`\s+由\s+(?P<member>\S.*)$`) before the existing `=`/`@` parsing; the member resolves through `resolve_member_token`. In an active session the command builds the same actor skill command that `combat command <actor-token> skill ...` builds and submits it through the same facade, so draft semantics stay identical.

## Risks / Trade-offs

- [`由` appearing inside a target display name] → The suffix must be the final whitespace-separated `由 <name>` pair; ambiguity rejects via the member token resolver.

## Migration Plan

Pre-release; additive. Revert the implementation commit.

## Verification and documentation ownership

EvenniaTest with a synthetic heal and SELF buff: actor MP charged, target healed, SELF on the caster, XP on the caster (independent expected numbers: caster MP 20 with cost 8 ends at 12), six-second advance settles the party once, knocked-out/absent/non-member/unowned refusals, companion monster target reaching the initiation seam (pinned rejection until the opening change), forged/absent caster rejected before any session. Command tests for suffix parsing out of and in combat. Update both command documents; `tests/test_command_docs.py`; shard contract; `tools.contract_gate`.
