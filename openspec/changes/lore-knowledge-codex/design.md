# Design: lore-knowledge-codex

## Context

The dialogue intent whitelist (`npc-dialogue` main spec) lists eight kinds; `reveal_lore` is
whitelisted for extraction shape only and every application returns `applied=False`
(`world/rules/npc_intents.py::_FORWARD_DECLARED_KINDS`). The lore registries (`world/lore/` —
races, nations, wilderness regions, monsters, elements, magic, anchors, guild) are immutable
frozen-dataclass data synced into the DB at startup; they carry player-readable fields
(`display_name_zh`, `description`, `terrain_flavor_zh`, ...) but nothing in the game surfaces
them.

The design `2026-08-09-dialogue-quests-lore-design.md` (O4/O5) fixes the semantics: `reveal_lore`
unlocks a codex entry — the player gains an append-only `lore_discovered` record, and a `lore`
command lists and renders only discovered entries. Unknown entries are never exposed (same
philosophy as map knowledge: unknown nodes are not sent).

## Goals / Non-Goals

Goals:

- Give `reveal_lore` a real deterministic surface: exact payload, registry verification,
  append-only codex write.
- Provide a player-facing `lore` command that lists and renders discovered entries only.
- Keep the codex purely deterministic and offline-playable.

Non-Goals:

- Revealing map knowledge or quest hints through the codex (map knowledge has its own writer).
- A WebClient codex panel (documented future seam; the text command is the current surface).
- Affinity or reward effects from lore reveal (the speech is the reward).
- Any change to the other six active intent kinds or to `offer_quest` (owned by
  `dialogue-offer-quest`).

## Decisions

### D1: A dedicated `world/rules/lore_knowledge.py` module as the sole writer

`record_lore_reveal(player, category, key)` is the only API that writes
`player.db.lore_discovered` (a namespaced `category:key` set, append-only; repeat reveals are
no-ops; unknown category rejects). Readers (`list_discovered`, `lore_card`) are pure.

Alternatives considered:

- Writing directly in `npc_intents.py` — works but spreads the storage contract; a dedicated
  module mirrors `map_knowledge.py` (the project's established knowledge-writer pattern) and keeps
  the write path reviewable.
- A registry entry in `world/lore/` — lore is immutable by convention; the codex is player state,
  so it belongs in `world/rules/`.

### D2: Closed category-to-registry mapping + per-registry key verification

`CODE_CATEGORIES` is a bounded mapping from each codex category to exactly one immutable lore
registry (race→`RACE_REGISTRY`, nation→`NATION_REGISTRY`, region→`WILDERNESS_REGION_REGISTRY`,
monster→`MONSTER_TIER_REGISTRY`, element→`ELEMENT_REGISTRY`, magic→`MAGIC_TIER_REGISTRY`,
anchor→`ANCHOR_REGISTRY`, guild→`GUILD_RANK_REGISTRY`). A payload's `category` must be in the
mapping and `key` must resolve in that registry; anything else discards the intent and keeps the
speech. Category allowlist and resolvability are deterministic-applier checks, not extraction
checks — an unverifiable reveal must keep the speech rather than exhaust retries into silence.

Alternatives considered:

- A single flat namespaced key (`"race:ciaran"`) — less structured, and the two-field shape makes
  the card renderer's registry lookup explicit; the design doc specifies `{category, key}`.

### D3: Per-category card rendering with registry-specific fields

`lore_card(category, key)` renders one entry as a player-facing card using each registry's
canonical display fields (e.g. race description and flavor fields, region `terrain_flavor_zh`),
never raw dataclass dumps. Rendering is a pure function over registry data; a missing entry raises
a named error that the command maps to the not-found line.

### D4: The `lore` command surfaces only discovered knowledge

`lore` lists discovered entries grouped by category in deterministic order; `lore <category> <key>`
renders one discovered card. Unknown or undiscovered targets share one not-found line so registry
existence is never leaked. The command is mounted on the character cmdset, and the command-docs
drift contract is updated in the same change.

### D5: Whitelist bookkeeping

`reveal_lore` is removed from `_FORWARD_DECLARED_KINDS`, leaving the tuple empty; the npc-dialogue
main spec gains the delta (payload shape + executability) and the now-obsolete
not-yet-executable scenario is removed with its reason recorded in the delta.

## Risks / Trade-offs

- [A category's registry content changes shape] → registries are frozen dataclasses; the card
  renderer's per-category field mapping is covered by per-category tests that fail loudly.
- [The codex set grows without bound] → `lore_discovered` is bounded by the registries' finite
  key counts; no unbounded growth path exists.
- [Two capabilities editing the same spec] → `dialogue-offer-quest` and `lore-knowledge-codex`
  both modify `npc-dialogue`; they are sequential per the design's slicing, and each delta syncs
  the full current requirement block.

## Migration Plan

Not applicable — unreleased project, zero users, no backward compatibility or data migration.

## Open Questions

None blocking. Whether the codex later gains a WebClient panel is a documented future seam; the
text command and the pure renderer are the hooks it would extend.
