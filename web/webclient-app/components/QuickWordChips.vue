<script setup>
// Quick-word chips (H5, webclient-hud-05-overlays-and-command-line, design
// D4/D5): the command line's verb chips. Each chip's visible label IS the
// literal command it inserts; activating a chip writes the verb plus a
// trailing space into the field and focuses it, never submitting — a
// prepared command still travels through the field's single send path. The
// v1 sets are drawn from the server's installed command set: the draft's
// 走/問 chips are dropped because this game has no `go`/`ask` commands
// (movement is by exit name through the dock's 移動 frame; NPC keyword talk
// is 交談).
//
// Both mode groups are rendered; the inactive group is hidden by the stage
// root's `data-elosern-mode` gate with `display:none` (never dimmed), so
// hidden chips leave the accessibility tree and the tab order (REDESIGN.md
// §0.1). No mnemonic key badge: the draft's letter badges are dropped
// because the client binds no key to them and the label already is the verb.
const props = defineProps({
  // The committed mode (exploration / combat / creation).
  mode: { type: String, default: "exploration" },
});

const emit = defineEmits(["insert"]);

// The v1 sets (design D4): exploration = 看/拿/說/交談/等待 (the installed
// command keys: 看/說/拿, the 交談 alias of talk, the 等待 key of skip),
// combat = 說/施法 (the 施法 alias of cast).
const EXPLORATION_CHIPS = ["看", "拿", "說", "交談", "等待"];
const COMBAT_CHIPS = ["說", "施法"];

function insert(verb) {
  emit("insert", verb);
}
</script>

<template>
  <div class="qwc" aria-label="快捷詞" data-testid="quick-word-chips">
    <div class="qwc__group qwc-exploration" data-testid="quick-word-chips-exploration">
      <button
        v-for="verb in EXPLORATION_CHIPS"
        :key="verb"
        type="button"
        class="qwc__chip"
        :data-verb="verb"
        :data-testid="`quick-word-chip-${verb}`"
        @click="insert(verb)"
      >
        {{ verb }}
      </button>
    </div>
    <div class="qwc__group qwc-combat" data-testid="quick-word-chips-combat">
      <button
        v-for="verb in COMBAT_CHIPS"
        :key="verb"
        type="button"
        class="qwc__chip qwc__chip--combat"
        :data-verb="verb"
        :data-testid="`quick-word-chip-${verb}`"
        @click="insert(verb)"
      >
        {{ verb }}
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
  padding: 4px 10px;
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  color: var(--paper-300);
  background: var(--ink-820);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  cursor: pointer;
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
