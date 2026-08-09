## Why

The `reveal_lore` intent is whitelisted in the dialogue layer but has no executable surface: every
extraction returns `applied=False` with no state change, and the rich immutable world knowledge in
`world/lore/` registries is invisible in-game — players have no durable, re-readable knowledge
base. The design (`docs/superpowers/specs/2026-08-09-dialogue-quests-lore-design.md`, O4/O5)
defines the capability surface: a player codex of discovered registry entries, unlocked by the
dialogue intent and browsable through a `lore` command.

## What Changes

- Add `world/rules/lore_knowledge.py` (new):
  - `CODE_CATEGORIES` allowlist of codex-eligible registries (`race`, `nation`, `region`,
    `monster`, `element`, `magic`, `anchor`, `guild`);
  - `record_lore_reveal(player, category, key)` — the sole writer of
    `player.db.lore_discovered` (append-only, repeat reveals are no-ops, unknown category
    rejects);
  - `list_discovered(player)` — deterministic sorted listing of discovered `(category, key)`
    pairs;
  - `lore_card(category, key)` — per-category player-facing card rendering (display name,
    description, registry-specific flavor fields), never raw dataclass dumps.
- Add `_apply_reveal_lore` to `world/rules/npc_intents.py`: payload is exactly
  `{"category": str, "key": str}` (bounded); verification checks the category allowlist and key
  resolvability in that registry; application calls `record_lore_reveal`; no affinity gain (the
  speech is the reward); repeat reveal is a no-op success.
- Remove `reveal_lore` from `_FORWARD_DECLARED_KINDS` (the tuple becomes empty — no
  forward-declared intent kinds remain).
- Add the `lore` command: `lore` lists discovered entries grouped by category; `lore <category>
  <key>` renders one discovered entry's card; unknown or undiscovered targets produce the same
  not-found line, never revealing registry existence.
- Update `docs/game/commands.md` / `docs/game/command-reference.md` for the new command (kept
  green by the command-docs drift contract).

## Capabilities

### New Capabilities
- `lore-knowledge`: The player codex — the append-only discovered-knowledge store, its sole writer
  and readers, per-category card rendering, and the `lore` command surface.

### Modified Capabilities
- `npc-dialogue`: The intent-whitelist requirement changes — `reveal_lore` becomes executable with
  the exact payload `{"category", "key"}`; the "whitelisted but not-yet-executable" scenario is
  removed because no forward-declared kinds remain.

## Impact

- `world/rules/npc_intents.py`: new applier; `_FORWARD_DECLARED_KINDS` becomes empty.
- New `world/rules/lore_knowledge.py`: sole writer + readers + card renderer.
- New `commands/lore.py` (mounted on the character cmdset): player view surface.
- `world/lore/` registries: read-only; consumed for card rendering only.
- `docs/game/commands.md`, `docs/game/command-reference.md`, `tests/test_command_docs.py`:
  new-command documentation.
- WebClient exploration/service menus: no change (a codex panel is a documented future seam).
- No backward compatibility or migration work: the project is unreleased with zero users.
