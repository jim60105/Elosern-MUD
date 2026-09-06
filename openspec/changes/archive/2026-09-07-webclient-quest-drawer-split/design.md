## Context

`QuestBoard.vue` is 496 lines and reads one panel. After `webclient-quest-log-panel` there are two
panels with different availability rules.

Parent design: `docs/superpowers/specs/2026-09-06-quest-issuer-model-design.md` §9.1.

## Goals / Non-Goals

**Goals:**

- The component boundary equals the data boundary.
- A player away from a clerk sees their quests.
- No quest is presented twice.

**Non-Goals:**

- No change to the `services` payload.
- No change to the drawer's name, its dock tab, or its hosted-frame routing.
- No codex button (moved to `.cmdutil` by `webclient-lore-codex-drawer`).

## Decisions

### D1: Two components in one drawer, not two drawers

Two drawers would force the player to switch surfaces to compare "what I hold" against "what I can
turn in here", which is exactly the comparison the counter exists for. One drawer with two stacked
surfaces keeps them visible together while keeping the components separate.

### D2: The counter loses the quest list, the book keeps the counter actions

The alternative placement — counter lists the actionable quests, book lists the rest — was rejected:
abandon is enabled for every in-progress quest, so nearly every quest would appear in both surfaces.

Instead, actions that belong to a quest travel with the quest row, and the counter keeps only what is
genuinely the counter's own: registration, the board of quests you do not yet hold, and rank. This
also matches the stated product rule that only accepting, browsing the board, turning in, claiming,
and examining require a clerk.

### D3: `quest_id` is the single merge point

One join, in one component, between two panels. The book never synthesizes a descriptor and never
enables one the counter disabled — it mirrors the counter-side descriptor exactly, including its
label and disabled reason, so host gating stays owned by the server presenter.

### D4: Sequenced after the codex drawer

Both changes edit `AppClient.vue`'s drawer body and the frozen contract audit §2.3. The codex drawer
also removes the `世界圖鑑` button from `QuestBoard.vue`, which this change deletes; landing the codex
drawer first means that removal is a small edit rather than a conflict against a deleted file.

## Risks / Trade-offs

- **Merging two panels in the client** → Confined to one join by `quest_id` in one component, and
  pinned by tests for all four combinations of panel availability.
- **Stale counter descriptors** → Both panels are pushed on the same mutation seams, and the row's
  presented state changes only when a commit lands, following the existing tracking-control rule.
- **Retired testids** → Removed from the audit in the same edit that adds the new ones, so
  `tests/test_webclient_frozen_contract.py` stays green rather than accumulating dead identifiers.
- **The delivery control depends on `quest-deliver-action`** → If that change has not landed, the
  control is simply never rendered because no affordance exists; the book degrades honestly rather
  than showing a dead button.
