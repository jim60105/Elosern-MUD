<script setup>
// Quick-word chips (H5, webclient-hud-05-overlays-and-command-line, design
// D4/D5; rebadged by webclient-align-02-quickbar-shortcuts): the command
// line's verb chips. Each chip renders the draft structure — a visible
// zh-TW label plus a letter badge — and activating it writes the badge
// letter plus a trailing space into the field and focuses it, never
// submitting: the badge letter IS the installed command word (the server
// alias pinned by commands.tests.test_localized's QuickbarLetterPinningTests),
// so what the badge teaches is what every transport receives. The draft's
// 走/問 chips stay dropped because this game has no `go`/`ask` commands
// (movement is by exit name through the dock's 移動 frame; NPC keyword talk
// is 交談).
//
// The chip sets and badge letters come from the shared quickbar table
// (lib/quick_chips.js): badge ⇔ inserted text ⇔ client keybinding are one
// source, pinned server-side against the installed cmdset.
//
// Both mode groups are rendered; the inactive group is hidden by the stage
// root's `data-elosern-mode` gate with `display:none` (never dimmed), so
// hidden chips leave the accessibility tree and the tab order (REDESIGN.md
// §0.1).
import { glyphPath } from "./dock-icons.js";
import { EXPLORATION_CHIPS, COMBAT_CHIPS } from "../lib/quick_chips.js";

const props = defineProps({
  // The committed mode (exploration / combat / creation).
  mode: { type: String, default: "exploration" },
});

const emit = defineEmits(["insert"]);

function insert(chip) {
  // A chip prepares, it does not send: the emitted text is exactly the
  // badge letter (the field path owns the trailing space).
  emit("insert", chip.letter);
}

// Map each chip's verb to the stable glyph key in the shared dock icon
// table (H3 webclient-hud-03-action-dock). 交談 is this client's own D4
// addition with no reference icon, so it reuses the dock's `character`
// person-silhouette glyph; every other verb maps onto a concept the table
// already covers.
const VERB_GLYPH = {
  看: "look",
  拿: "get",
  說: "interact",
  交談: "character",
  等待: "wait",
  施法: "suggestions",
};

function chipGlyph(verb) {
  return glyphPath(VERB_GLYPH[verb]);
}
</script>

<template>
  <div class="qwc" aria-label="快捷詞" data-testid="quick-word-chips">
    <div class="qwc__group qwc-exploration" data-testid="quick-word-chips-exploration">
      <button
        v-for="chip in EXPLORATION_CHIPS"
        :key="chip.verb"
        type="button"
        class="qwc__chip"
        :data-verb="chip.verb"
        :data-letter="chip.letter"
        :data-testid="`quick-word-chip-${chip.verb}`"
        @click="insert(chip)"
      >
        <svg
          v-if="chipGlyph(chip.verb)"
          class="qwc__chip-icon"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden="true"
        >
          <path :d="chipGlyph(chip.verb)" stroke="currentColor" stroke-width="1.8" />
        </svg>
        <span class="qwc__chip-label">{{ chip.verb }}</span>
        <b class="qwc__chip-badge" data-testid="quick-chip-badge">{{ chip.letter }}</b>
      </button>
    </div>
    <div class="qwc__group qwc-combat" data-testid="quick-word-chips-combat">
      <button
        v-for="chip in COMBAT_CHIPS"
        :key="chip.verb"
        type="button"
        class="qwc__chip qwc__chip--combat"
        :data-verb="chip.verb"
        :data-letter="chip.letter"
        :data-testid="`quick-word-chip-${chip.verb}`"
        @click="insert(chip)"
      >
        <svg
          v-if="chipGlyph(chip.verb)"
          class="qwc__chip-icon"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden="true"
        >
          <path :d="chipGlyph(chip.verb)" stroke="currentColor" stroke-width="1.8" />
        </svg>
        <span class="qwc__chip-label">{{ chip.verb }}</span>
        <b class="qwc__chip-badge" data-testid="quick-chip-badge">{{ chip.letter }}</b>
      </button>
    </div>
  </div>
</template>

<style>
/* Mode gating (design D4): both groups render; the stage root's
   data-elosern-mode gate hides the inactive group with display:none so it
   leaves the accessibility tree and the tab order. The gate must live at
   the stage root, so this block is unscoped. */
.elosern-stage[data-elosern-mode="exploration"] .qwc-combat,
.elosern-stage[data-elosern-mode="creation"] .qwc-exploration,
.elosern-stage[data-elosern-mode="creation"] .qwc-combat {
  display: none;
}
.elosern-stage[data-elosern-mode="combat"] .qwc-exploration {
  display: none;
}

.qwc {
  display: flex;
  gap: 6px;
  flex: none;
}

.qwc__group {
  display: flex;
  gap: 6px;
}

.qwc__chip {
  box-sizing: border-box;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  color: var(--paper-300);
  background: var(--ink-820);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.qwc__chip-icon {
  flex: none;
}

.qwc__chip-badge {
  /* The draft's key badge: the kbd treatment (mono, --ink-780 ground,
     2px bottom border) the change-01 legend established for <kbd>. */
  font-family: var(--f-mono);
  font-size: var(--text-xs);
  line-height: 1;
  padding: 2px 4px;
  color: var(--paper-300);
  background: var(--ink-780);
  border-bottom: 2px solid var(--ink-700);
  border-radius: 2px;
}

.qwc__chip:hover {
  color: var(--paper-100);
  border-color: var(--gold-400);
}

.qwc__chip:focus-visible {
  outline: none;
  color: var(--paper-100);
  border-color: var(--gold-400);
  box-shadow: 0 0 0 1px var(--gold-400);
}

.qwc__chip--combat {
  border-color: rgba(207, 68, 68, 0.5);
  color: var(--seal-400);
}
</style>
