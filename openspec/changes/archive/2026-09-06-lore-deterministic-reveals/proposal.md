# Proposal: lore-deterministic-reveals

## Why

The knowledge codex is fully implemented — the eight-category registry mapping, the append-only
store, the deterministic listing, the per-category cards, and the `lore` command. But
`record_lore_reveal()` has exactly one caller in the whole codebase: the LLM `reveal_lore` dialogue
intent in `world/rules/npc_intents.py`.

So a player who never speaks to a generative NPC has a permanently empty codex, and with every
generative profile failing the codex can never gain a single entry. That violates the project's
headline invariant that the deterministic game stays fully playable when all LLM and image services
are offline, and it makes the codex UI a guaranteed empty shell.

## What Changes

- Three deterministic reveal sources, all offline-reachable, all routed through the existing sole
  writer so the append-only and repeat-is-a-no-op semantics are unchanged:
  - **Arrival**: entering a room resolving to a registered anchor reveals that `anchor` entry;
    entering a wilderness room resolving to a registered region reveals that `region` entry.
  - **First defeat**: a committed `target_defeated` event for a monster of a registered tier reveals
    that `monster` entry.
  - **Origin**: character creation reveals the chosen `race` and `nation` entries; guild registration
    reveals the registrant's `guild` rank entry.
- Reveals are best-effort with respect to gameplay: a reveal failure SHALL NOT fail the arrival, the
  combat settlement, the creation, or the registration that triggered it. A corrupt codex record
  degrades the reveal, not the game.
- Reveals stay silent by default: no message interrupts combat or movement. The codex simply gains
  the entry, which the player discovers in the codex surface.

## Capabilities

### New Capabilities

(None.)

### Modified Capabilities

- `lore-knowledge`: the codex gains deterministic reveal sources alongside the dialogue intent, with
  the offline-reachability guarantee and the non-blocking failure rule.

## Impact

- `world/quests/room_observation.py` (or the shared room-arrival observation point): the anchor and
  region reveal.
- The `target_defeated` consumption path already read by the DEFEAT planner: the monster-tier reveal.
- `world/rules/character_creation.py` and `world/rules/guild.py`: the origin reveals.
- `world/rules/lore_knowledge.py`: unchanged as the sole writer; possibly a small helper for
  best-effort reveal with facade logging.
- No change to the `lore` command, the card renderer, or the category mapping.
