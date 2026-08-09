# Dialogue Quest Offers and Lore Knowledge — Design

**Date:** 2026-08-09
**Status:** Approved
**Scope:** Activating the two forward-declared NPC intents `offer_quest` and `reveal_lore`
(master design §7.4), the direct quest-assignment path, and the lore-knowledge codex.

This document is a slice of the master design
(`docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`, §7.4 intent whitelist). Where this
document conflicts with the master design, the master design wins unless this document explicitly
amends it.

---

## 1. Product Context

The dialogue intent whitelist has grown to eight kinds. `party_invite`, `adjust_relation`,
`request_guild_exam`, `give_item`, `take_item`, and `none` are active with deterministic appliers;
`offer_quest` and `reveal_lore` remain in `world/rules/npc_intents.py:32` as
`_FORWARD_DECLARED_KINDS = ("offer_quest", "reveal_lore")` — whitelisted upstream but with no
deterministic capability surface. Any attempt to apply either returns `applied=False` today.

This change activates both kinds through existing deterministic APIs: quest assignment reuses the
registered guild-offer surface and the quest-runtime acceptance transaction; lore reveal introduces
a player codex of discovered world-knowledge entries. Both keep the accepted failure mode —
illegal or unverifiable intents discard only the intent and preserve the speech.

---

## 2. Design Decisions

| # | Decision | Rationale |
|---|---|---|
| O1 | **`offer_quest` assigns directly.** Verification passes → the quest record is created immediately; the speech is the notification. No pending-offer step. | Owner decision: shortest flow that still runs every eligibility check. |
| O2 | **The verification surface is the registered guild offer.** The NPC must carry the `GuildStaff` component with a branch, `(definition_key, branch)` must exist in `GUILD_OFFER_REGISTRY`, and the player's canonical guild rank must be within the quest's rank band; duplicate-quest rejection is delegated to the quest runtime. | No new authorization source: branch offers are the only legal quest source. |
| O3 | **Application reuses the acceptance transaction shape.** `accept_quest(player, definition_key)` plus `apply_affinity_change(npc, player, GUILD, +1)` commit in one atomic transaction with attribute snapshots and rollback, mirroring `accept_guild_offer`. | A dialogue-assigned quest is economically and statefully identical to a board-accepted one. |
| O4 | **`reveal_lore` unlocks a codex.** `player.db.lore_discovered` is an append-only set of namespaced keys; a new `lore` command lists and renders discovered entries. Payload is `{category, key}` with a declared codex-eligible category allowlist; the key is validated against that registry. | The player gains a durable, re-readable knowledge base; fully deterministic and offline-playable. |
| O5 | **Speech is always preserved.** Any verification or application failure discards only the intent; the speech is shown unchanged. Existing intent kinds and the `none` no-op are untouched. | §7.4's accepted failure mode is unchanged. |

---

## 3. System Design

### 3.1 offer_quest

`world/rules/npc_intents.py` gains `_apply_offer_quest`:

- Payload is exactly `{"quest_key": str}` (bounded); extra or missing fields reject.
- Verification, in order:
  1. `npc` carries the `GuildStaff` component with a `branch_key`;
  2. `get_guild_offer(definition_key, branch_key)` resolves (offer registered at that branch);
  3. the player's canonical guild rank is within the offer's quest rank band (reusing the rank
     check that `list_guild_offers` applies);
  4. the quest runtime's own duplicate/eligibility checks run inside the transaction.
- Application: `with transaction.atomic(): record = accept_quest(player, definition_key)`,
  then `apply_affinity_change(npc, player, AffinitySource.GUILD, 1)`; quest-log and relations
  snapshots restore on failure exactly as `accept_guild_offer` does. Success returns
  `IntentOutcome(applied=True)`.

### 3.2 reveal_lore

New module `world/rules/lore_knowledge.py`:

```python
CODE_CATEGORIES = ("race", "nation", "region", "monster", "element", "magic", "anchor", "guild")

def record_lore_reveal(player, category: str, key: str) -> None:
    """Sole writer of player.db.lore_discovered; append-only; repeat reveals are no-ops."""

def list_discovered(player) -> tuple[tuple[str, str], ...]:
    """Deterministic sorted listing of discovered (category, key) pairs."""

def lore_card(category: str, key: str) -> dict[str, str]:
    """Render one registry entry as a player-facing card (display name, description, flavor fields)."""
```

- `player.db.lore_discovered` stores namespaced keys (`category:key`), append-only; repeat reveals
  are no-ops; unknown `category` rejects; `key` is validated against the category's registry.
- `lore_card` renders per-category fields (e.g. `race` cards use the race description and flavor
  fields; `region` cards use `terrain_flavor_zh`), never raw dataclass dumps.

New command `lore`:

- `lore` — lists discovered entries grouped by category (undiscovered keys never appear).
- `lore <category> <key>` — renders the card for one discovered entry.
- Unknown or undiscovered targets produce the same not-found line; nothing leaks registry
  existence (same philosophy as map knowledge: unknown nodes are not sent).

`world/rules/npc_intents.py` gains `_apply_reveal_lore`:

- Payload is exactly `{"category": str, "key": str}` (bounded).
- Verification: `category` in `CODE_CATEGORIES` and `key` resolvable in that registry.
- Application: `record_lore_reveal(player, category, key)`; no affinity gain (the speech is the
  reward); repeat reveal is a no-op success.

### 3.3 Whitelist update

Both kinds move out of `_FORWARD_DECLARED_KINDS` (leaving the tuple empty). The `npc-dialogue`
main spec's intent description gains the two active appliers; the forward-declared marker is
removed.

---

## 4. Integration Points

| Integration | Direction |
|---|---|
| `world/rules/npc_intents.py` | Two new appliers; `_FORWARD_DECLARED_KINDS` emptied |
| `world/rules/guild_offers.py` | Offer verification reused; no new API |
| `world/quests/runtime.py` | `accept_quest` transaction reused unchanged |
| `world/lore/` registries | Codex category allowlist + per-category card renderer |
| `world/rules/lore_knowledge.py` (new) | Sole writer of `lore_discovered` |
| `commands/lore.py` (new) | Player view surface; `docs/game/commands.md`, `command-reference.md`, and `tests/test_command_docs.py` updated in the same change |
| WebClient exploration/service menus | Left as a documented seam for a future panel; not part of this change |

---

## 5. Error Handling and Degradation

| Situation | Behavior |
|---|---|
| quest_key has no offer / NPC not GuildStaff / rank below band / quest already active | `applied=False`, speech preserved, no state written |
| category not in allowlist / key unresolvable | Same failure mode |
| Transaction interruption | Snapshot/rollback, same guarantee as `accept_guild_offer` |
| LLM offline | Existing greeting/silence degrade; this change is fully deterministic |

---

## 6. Testing Strategy

| Area | Method |
|---|---|
| Appliers | `EvenniaTest`: every rejection reason, success path (quest created + GUILD +1 in one transaction), duplicate key, rollback on injected failure |
| lore_knowledge | Pure `unittest.TestCase`: append-only set, repeat-reveal no-op, allowlist rejection, deterministic ordering; card rendering per category |
| Command | `lore` listing/view/undiscovered-not-found; command-docs drift contract green |
| Guardrail | Malformed payloads leave the DB untouched (existing pattern) |
| Traceability | New main requirements annotated with `covers_requirement`; `spec_traceability check` passes |

---

## 7. OpenSpec Slicing

Two sequential per-day changes:

| # | Change | Depends on | Content |
|---|---|---|---|
| 1 | `dialogue-offer-quest` | 16 (`guild-economy` offers), 19 (`npc-dialogue` whitelist), 15 (`quest-runtime`) | `_apply_offer_quest`, transaction, tests; npc-dialogue whitelist delta |
| 2 | `lore-knowledge-codex` | 2 (`lore-world-data` registries), 1 | `lore_knowledge.py`, `lore` command, card renderer, `_apply_reveal_lore`, tests |

---

## 8. Out of Scope

- Pending-offer acceptance flows (owner chose direct assignment; a pending-offer variant remains a
  possible future change if dialogue quests ever need a confirmation step).
- Lore display inside the WebClient panels (documented seam).
- Revealing map knowledge or quest hints through the codex (map knowledge has its own writer).
- Any change to `give_item` / `take_item` / `request_guild_exam` / `adjust_relation` /
  `party_invite` behavior.

---

## 9. Open Questions Carried Forward

- None blocking. Whether dialogue-assigned quests should ever require a confirmation step, and
  whether the codex gains a WebClient panel, are deferred decisions with explicit seams.
