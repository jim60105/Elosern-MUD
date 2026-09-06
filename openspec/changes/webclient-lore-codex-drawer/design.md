## Context

`LoreDrawer.vue` carries the codex name but renders guild quest prose; the codex trigger sits in the
quest drawer. `webclient-lore-codex-panel` supplies the read model.

Parent design: `docs/superpowers/specs/2026-09-06-quest-issuer-model-design.md` §9.2 and §9.3.

## Goals / Non-Goals

**Goals:**

- A working codex surface reachable from anywhere in the HUD.
- Non-disclosure preserved end to end: the drawer shows no more than the panel ships.
- The codex stops depending on the quest drawer.

**Non-Goals:**

- No search or filter beyond category selection; the corpus is a few dozen entries.
- No "new discovery" badge or notification — reveals are silent by design.
- No change to the title codex, which is a different system.

## Decisions

### D1: A drawer, not an overlay

The codex is a reference surface consulted alongside play, like the skill book and the bag, not a
full-screen mode like the map or settings. The store's drawer machinery already gives it focus
trapping, Escape handling, and mutual exclusion with overlays for free.

The four existing `.cmdutil` icons open overlays; this one opening a drawer is fine — `openHudDrawer`
already accepts `lore`, so no store change is needed at all.

### D2: `.cmdutil`, not the exploration dock

The codex is not an exploration action and has no target, so a dock row would be wrong. The utility
strip is where cross-cutting reference surfaces already live: the skill lineage and the title codex
are both there, and the world codex is the same kind of thing.

### D3: All navigation is local

The panel ships every discovered entry and its rendered card, so category and entry selection are
pure client state. No loading state, no fetch action, no second protocol surface. This is the whole
reason the panel ships the corpus whole.

### D4: Land before the quest drawer split

Both changes edit `AppClient.vue` and the frozen contract audit §2.3, and this one edits
`QuestBoard.vue`, which the other deletes. Landing this first makes the button removal a two-line
edit; the reverse order would make it a conflict against a deleted file.

## Risks / Trade-offs

- **Two adjacent codex icons** → 稱號冊 and 圖鑑 sit side by side and are genuinely different systems.
  Mitigated by requiring distinct glyphs and distinct accessible labels, pinned by a browser test.
  If it still reads as confusing in use, renaming one is a follow-up, not a blocker.
- **The drawer is empty until `lore-deterministic-reveals` lands** → With only the LLM reveal source,
  an offline player sees the honest empty state. That is correct behavior for an empty codex, and
  the reveal sources change fixes the cause rather than the symptom.
- **Deleting `LoreDrawer.vue` removes a surface some test may target** → Its retired testids are
  removed from the audit in the same edit, so the frozen contract test stays green.
