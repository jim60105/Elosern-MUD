## Context

See `proposal.md` — Why.

The divergence was measured, not estimated. Comparing every codex item row against `ITEM_REGISTRY` gives: 5 display names differ, 2 rarities differ, 17 summaries differ substantively, 39 more differ only by the registry's trailing 。, and one shop offer price differs. No registry key is missing from the codex, so the orphan set this change sweeps is empty today.

Rarity is not a free edit. `world/rules/equipment_effects.py` checks every authored adjustment against the budget column for the item's registered rarity at load time, so rarity decides what an entry may carry. 修女聖袍's codex numbers — 防禦 -4、快感 +20%、治療 +10%、露出偏向 +1 — need the `rare` soft-percent ceiling of 20; at its current `uncommon` the ceiling is 15 and the entry would be refused at startup. 聖女聖袍's 快感 +30% likewise needs `legendary`.

`equipment-effects` also carries a Church-of-Light doctrine requirement over both vestments: non-negative exposure bias and pleasure gain, at least one of healing or an immunity, no suppression, with ordinary combat trade-offs permitted. Both corrected entries satisfy it — each keeps a positive healing value and its negative defence is exactly the permitted trade-off.

## Goals / Non-Goals

**Goals:**
- Make the shipped 58 entries say what the codex says, so the later slices extend a catalog that is already true.
- Remove the four retired race names from player-visible text.
- Establish the removal procedure and the closure guarantee that make deleting a catalogued item safe, and run the sweep once.

**Non-Goals:**
- **New game-data contract tests.** Nothing added here asserts that a named item carries a particular summary, name, rarity, or price. The one thing worth specifying — that a dangling reference fails closed — is a mechanics assertion provable with synthetic data.
- Adding any item. All 48 additions belong to the three slices that follow.
- Changing any item key. Renames here are display-name only, so no stored inventory, kit, preset, quest, or shop reference moves.
- Touching the 39 summaries that differ only by the trailing 。. The registry ends a summary with 。 and the codex tables do not; that is a table-cell convention on the document's side, and the migration adds the period rather than treating it as a difference.

## Decisions

**A separate change that runs first, rather than folding the fixes into the additions.** The drift spans all three mechanical shapes — an inspect-only material, several equipment pieces, no usable items — so it does not decompose along the same lines as the additions. Folding it in would mean each later slice quietly retuning shipped items while claiming to be additive, and would leave the catalog half-migrated for as long as the sequence takes. Doing it first is also the cheapest ordering: every later slice then edits a file whose existing entries are final.

**The rarity corrections carry their rulebook numbers with them.** An earlier draft of this work treated 修女聖袍 and 聖女聖袍 as intentional codex-versus-rulebook divergences to leave alone, on the strength of the codex's own "the rulebook is authoritative for tuned values" clause. That reading was too broad. Rarity is not a tuned value — it is registry-owned identity that decides what the rulebook may authorise, and the codex is the source of truth for identity. Once the rarity is corrected, the codex's adjustments become authorable, and leaving the old numbers would mean the registry says `rare` while the entry is still budgeted as though it were not. So the two move together. `silver_feather_earring` stays as it is: the codex's accessory table has no exposure-bias column, so it is silent there rather than disagreeing.

**Summaries are replaced wholesale, not edited.** Several codex summaries are substantially longer and carry setting content the registry never had — what the Church vestments actually look like, who gave the silver feather and when, why the elven village goods are shop stock rather than relics. Every one of them fits the existing 128-code-point bound with the trailing 。 added, the longest reaching 109. There is no truncation decision to make.

**The orphan sweep runs even though it finds nothing.** Running it now and recording the empty result is what turns "the registry happens to match" into "the registry is known to match", and it is the only opportunity to build the removal procedure against a case where nothing breaks. The requirement it establishes is the durable part: every surface that can name an item key must fail closed on an undefined one. That is what makes a future deletion a mechanical exercise instead of a hunt.

**The design document's stale line is prose, not contract.** `docs/superpowers/specs/2026-08-29-equipment-combat-effects-design.md` lists two items by their old names in a descriptive sentence. It is corrected here because renaming without it would leave the architectural source of truth naming items that no longer exist under those titles, but nothing normative changes.

## Risks / Trade-offs

- **A rarity change is a live balance change, not cosmetics.** → It is: 修女聖袍 becomes a stronger piece and 聖女聖袍 stronger still. Both are the codex's intended values and both stay inside their new rarities' ceilings, which the loader enforces. The project is pre-release, so no player's build is disturbed.
- **Renaming a shipped item changes text a player may have seen.** → No key moves, so inventories, kits, presets, quests, and shop offers all keep resolving. The only observable change is the displayed name, and the four retired race names make the current text worse than the new text.
- **The empty orphan sweep could give false confidence.** → The requirement is written against behavior — a dangling reference must fail closed — and is tested with synthetic data on each of the five reference surfaces. That coverage is what protects the next deletion, not the fact that today's sweep found nothing.
- **Two Church items move within a requirement that names them.** → The doctrine requirement's conditions were checked against the corrected numbers before the change was written: both keep a positive healing value, neither carries suppression, and the negative defence values are the trade-off the requirement already permits.

## Migration Plan

Not applicable. Pre-release, and no item key changes, so nothing stored can be orphaned by this change.
