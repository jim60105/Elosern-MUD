# Design: Companion field item use

## Context

See proposal.md. `use_item(actor, item_key, target=None)` (exploration facade) resolves through `resolve_item_use(request, in_combat=False, ...)` against the actor's own inventory and advances six seconds; `_inventory_use_adapter` rejects in an active session with `COMBAT_ITEM_COMMAND_REQUIRED`; `CmdUseItem` routes active-session use to `submit_player_item_use(self.caller, ...)` (commander entry only).

## Goals / Non-Goals

**Goals:** explicit user for the field facade, the action and the text command; combat parity through the existing actor command path.

**Non-Goals:** cross-member consumption (the user's own bag only), new item effects, in-combat graphical use (the bag tab saves a draft through `combat.command`).

## Decisions

- **Wrapper** `use_member_item` authorizes then calls `use_item(member, ...)`; target tokens are resolved relative to the member's room by the adapter's existing `_resolve_inventory_target` (now passed the member).
- **Text combat routing**: `使用 ... = <成員>` in a session builds the same actor item command `combat command <token> item <key>[=<target>]` builds and submits it through the same facade (`submit_player_item_use` is generalized to take the actor or the existing actor-command facade is reused; the implementation chooses the existing facade, never a second resolution path).
- **Combat check** uses `party_in_combat(acting, user)` so the field path is refused whenever the acting figure or the user is in a session.
- **Order of parsing**: the `= <成員>` suffix is split first (`rhs`), then the existing `item [target]` parse runs on the left side.

## Risks / Trade-offs

- [`=` already used by other commands for targets] → `使用` previously had no `=`; targets stay space-separated, so the suffix is unambiguous.

## Migration Plan

Pre-release clean cutover; revert the implementation commit.

## Verification and documentation ownership

EvenniaTest: companion potion (independent numbers: MP 40 of 120, potion +30 → 70), SELF on the user, six-second advance once with the present party settled, knocked-out/absent/forged rejections, commander-bag unchanged, in-session action rejection; command tests for text parity and draft-entry parity in combat; Vitest payload. Update both command documents; `tests/test_command_docs.py`; shard contract; `tools.contract_gate`.
