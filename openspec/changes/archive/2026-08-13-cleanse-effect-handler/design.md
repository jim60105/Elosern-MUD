## Context

`world/rules/rulebook/buffs.yaml` today has no field distinguishing a debuff (`poisoned`, `paralysis`,
`fear`) from a non-debuff (`focus`, `conferred_growth_rate`). `BuffHandler.remove()` exists but nothing
calls it from a cast-time effect. This gap was discovered while writing `spell-catalog-light`'s
`purify` spell, not anticipated by the original design doc.

## Goals / Non-Goals

**Goals:**
- `cleanse:status` removes every currently-active buff on the target that is data-classified as a
  debuff.
- The debuff/non-debuff classification lives in `buffs.yaml` as data, not as a hardcoded key list in
  Python — matching this project's established rulebook-as-data philosophy (`buff-handler-integration`,
  `combat-modifier-table`).

**Non-Goals:**
- Does not add selective/targeted cleanse (removing only one named debuff) — `cleanse:status` is
  all-or-nothing for this pass; a future `cleanse:<specific-buff-key>` variant is a natural but
  unbuilt extension.
- Does not retroactively re-classify every existing buff's polarity beyond the three actually needed
  (`poisoned`, `paralysis`, `fear` as debuffs; `focus`, `conferred_growth_rate` as not) — any buff added
  by a later `spell-catalog-*` change's own `buffs.yaml` rows is responsible for setting its own
  `polarity` field.

## Decisions

- **Add a `polarity: debuff | buff` field to each `buffs.yaml` entry**, defaulting to `buff` when
  absent (so `focus`/`conferred_growth_rate` need no edit — only the three actual debuffs gain an
  explicit `polarity: debuff` line). This is the minimal schema addition that makes `cleanse:status`
  a data query (`[b for b in entity.buffs if b.polarity == "debuff"]`) rather than a hardcoded list.
- **Handler lives in `world/rules/buffs.py`**, not `combat.py` — it operates purely on `BuffHandler`
  state, unlike `damage`/`heal` which touch `entity.traits`. Co-locating it with the module that already
  owns `BuffHandler` interaction (`grant_conferred_growth_rate`, etc.) matches existing placement
  precedent better than adding it to `combat.py`.
- **`cleanse:<scope>` mirrors `heal:<shape>`'s grammar shape** (a bare descriptor, no embedded data) for
  consistency across the two sibling gap-filling changes.
- **Cleanse routes through Evennia's dispel hooks, not the bare remove path.** `_remove_buff_keys`
  calls `entity.buffs.remove(key, dispel=True)`, which fires `at_dispel` and then `at_remove`. A
  cleanse is a forced external removal (dispel semantics), the opposite of a natural expiry.
  `RulebookBuff` defines neither hook today (both are base-class no-ops), so this is a recorded
  contract for future buffs that need "cleansed" cleanup — a future hook author knows cleanse reaches
  the dispel path and cannot silently bypass it.

## Risks / Trade-offs

- [Risk] Retroactively adding `polarity` to `buffs.yaml` could be forgotten for a future buff, silently
  making it uncleansable when it should be (or cleansable when it shouldn't). → Mitigation: default to
  `buff` (uncleansable) rather than `debuff` — the safer failure mode is "cleanse doesn't remove
  something it should," not "cleanse removes something beneficial by accident."

## Migration Plan

No data migration for existing entities (buff state is transient/session-scoped, not persisted across
this kind of schema addition in a way that needs backfill). Lands after `skill-effects-typed-model`;
before `spell-catalog-light`.

## Open Questions

None.
