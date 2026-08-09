# Design: dialogue-offer-quest

## Context

The dialogue intent whitelist (`npc-dialogue` main spec) lists eight kinds; `offer_quest` is
whitelisted for extraction shape only and every application returns `applied=False`
(`world/rules/npc_intents.py::_FORWARD_DECLARED_KINDS`). The registered guild offer surface
(`world/rules/guild_offers.py`) already carries the authorization model: offers are frozen
`GuildQuestOffer` values registered per `(definition_key, issuer_branch_key)`, and
`accept_guild_offer(actor, staff, definition_key)` validates board eligibility then delegates
acceptance to `world/quests/runtime.py::accept_quest` in one atomic transaction with snapshots.

The design `2026-08-09-dialogue-quests-lore-design.md` (O1–O3) fixes the semantics: a dialogue
offer is a **direct assignment** — verification passes, the quest record is created immediately,
and the speech is the notification. No pending-offer step.

## Goals / Non-Goals

Goals:

- Give `offer_quest` a real deterministic surface: exact payload, verification, atomic assignment.
- Reuse the guild-offer authorization and the quest-runtime transaction — no new authorization
  source, no second quest-acceptance path.
- Keep the accepted failure mode: any failure discards only the intent and preserves the speech.

Non-Goals:

- Pending-offer acceptance flows (rejected by the owner; a confirmation step is a future change).
- `reveal_lore` activation (owned by `lore-knowledge-codex`).
- Any change to `give_item` / `take_item` / `request_guild_exam` / `adjust_relation` /
  `party_invite` behavior.

## Decisions

### D1: Direct assignment through `accept_quest`, not a new quest API

The applier calls the existing quest-runtime acceptance inside its own atomic block, exactly as
`accept_guild_offer` does: `with transaction.atomic(): accept_quest(...) + apply_affinity_change(
..., GUILD, +1)`, with `quest_log` and `relations_data` snapshots restored on any failure.

Alternatives considered:

- A pending-offer record (`player.db.dialogue_offers`) accepted later via `guild accept` — richer
  but adds a new player surface and a lifecycle; the owner chose the shortest flow.
- A new dedicated `assign_quest` API in `world/quests/` — duplicates `accept_quest` semantics;
  rejected because quest ownership already lives in the runtime.

### D2: Verification is the guild-offer registration surface

Before any write: `npc` carries `GuildStaff` with a `branch_key`; `get_guild_offer(quest_key,
branch_key)` resolves; the player's canonical rank is within the offer's quest rank band (reusing
the same eligibility check `list_guild_offers` applies). Duplicate/eligibility edge cases are
re-checked inside `accept_quest` at commit time.

Alternatives considered:

- Any dialogue-capable NPC issuing any quest — no authorization; rejected (O2: branch offers are
  the only legal quest source).
- Per-NPC quest pools (`npc.db.quests`) — a new data surface; deferred, not needed for this scope.

### D3: Payload shape and whitelist bookkeeping

Payload is exactly `{"quest_key": str}` with a bounded length; extra or missing fields reject
before any verification. `offer_quest` is removed from `_FORWARD_DECLARED_KINDS`, leaving
`("reveal_lore",)` for the sibling change. The npc-dialogue main spec gains the delta (payload
shape + executability scenario) so the whitelist contract and the applier cannot drift.

### D4: The NPC is the issuing host; the branch is the authority

Affinity credit goes to the speaking NPC (`apply_affinity_change(npc, player, GUILD, 1)`),
matching board acceptance's `+1` and keeping the quest economically identical to a board-accepted
one. The offer's branch, not the NPC's dbref, is the authorization identity — any staff of the
branch could issue the same quest, and the offer registry stays the single source of truth.

## Risks / Trade-offs

- [A dialogue NPC could duplicate board acceptance] → `accept_quest` rejects active duplicate
  quests; the same guarantee applies on both paths.
- [An LLM could name a quest the NPC's branch does not hold] → the offer-registry lookup fails
  before any write; speech preserved, intent discarded (the accepted failure mode).
- [Snapshots grow] → identical to `accept_guild_offer`'s existing surface; bounded by quest-log
  and relations-data attribute size.

## Migration Plan

Not applicable — unreleased project, zero users, no backward compatibility or data migration.

## Open Questions

None blocking. Whether dialogue assignment should ever require a confirmation step remains an
explicitly deferred decision with the direct-assignment transaction as the seam.
