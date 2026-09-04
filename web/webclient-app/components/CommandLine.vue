<script setup>
// Command line (H5, webclient-hud-05-overlays-and-command-line, design
// D1/D2/D4/D5/D13): the persistent command line — a single always-rendered
// bar filling H1's 46px `command-line` anchor. No open/closed state: the
// input field is present in the DOM, visible and focusable without any
// opening action (design D1). The bar renders, in this order: the mode's
// quick-word chips, a `›` prompt chevron, the `#inputfield` inside its
// preserved `.inputfieldwrapper`, the hint cluster (`↑↓ 歷史` only — the
// draft's `Tab 補全` is dropped because the client implements no
// completion, design D5), the 上一筆/下一筆 history controls (the pointer
// path to the same walk state the ArrowUp/ArrowDown keys drive, design D5),
// and the utility controls that open the settings and help overlays (design
// D10).
//
// Preserved contract: the `#inputfield` field inside its `.inputfieldwrapper`
// wrapper does not move. The single send implementation is preserved
// byte-for-byte in behaviour: Enter without Shift sends exactly one command
// (regardless of how focus arrived), Shift+Enter inserts a newline, a
// successful send clears the field and keeps focus, and a rejected send
// (offline or mutations locked) preserves the typed text.
import { ref } from "vue";
import NarrativeMarkup from "../lib/narrative_markup.js";
import QuickWordChips from "./QuickWordChips.vue";

const props = defineProps({
  // The server-transformed prompt line (e.g. a room name). Rendered through
  // the preserved NarrativeMarkup pipeline; scaled by `--prose-scale`.
  prompt: { type: String, default: "" },
  // The command-history slice.
  history: { type: Array, default: () => [] },
  // The transport state (the store's connected flag).
  connected: { type: Boolean, default: true },
  // The store's mutation-lock flag: a rejected send preserves the typed
  // speech (webclient-desktop-shell).
  mutationsLocked: { type: Boolean, default: false },
  // The committed mode, forwarded to the quick-word chip sets (design D4).
  mode: { type: String, default: "exploration" },
  // The action client's in-flight mutation flag (webclient-input-narrative):
  // a free-form send blocked by an in-flight mutation keeps the typed speech.
  inFlight: { type: Boolean, default: false },
  // The client-local text-to-HTML narrative preference: when off, the
  // prompt line (and the feed/full-log lines) render as literal text — the
  // preference chooses whether the pipeline runs, never what it permits.
  textToHtml: { type: Boolean, default: true },
});

const emit = defineEmits(["submit", "focus-parent", "open-overlay", "focus-lost"]);

const field = ref(null);
const draft = ref("");

// Command-history walk state: null = not walking; otherwise the index into
// `props.history`, with the unsent draft preserved across the walk and
// restored when the walk returns past its most recent entry.
let historyIndex = null;
let draftBackup = "";

function resetHistoryWalk() {
  historyIndex = null;
  draftBackup = "";
}

function escapeHtml(value) {
  return String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// The prompt line is a server-transformed stream rendered through the
// preserved NarrativeMarkup pipeline (the Phase-0 audit's preserved contract):
// the same token stream the feed and full-log surfaces render, serialized
// here to an HTML string for `v-html`. When the `text2html` preference is
// off the line renders as literal text (the preference chooses whether the
// pipeline runs, never what it permits). The `--prose-scale` token
// multiplies the prompt line's font size (design D13).
function promptHtml() {
  const text = props.prompt == null ? "" : String(props.prompt);
  if (text === "") {
    return "";
  }
  if (!props.textToHtml) {
    return escapeHtml(text);
  }
  const tokens = NarrativeMarkup.tokenize(text);
  let html = "";
  for (const token of tokens) {
    if (token.kind === "text") {
      html += escapeHtml(token.value);
    } else if (token.kind === "break") {
      html += "<br>";
    } else if (token.kind === "open") {
      const attrs = [];
      if (Array.isArray(token.classes) && token.classes.length) {
        attrs.push(`class="${token.classes.join(" ")}"`);
      }
      if (token.style) {
        const styleParts = [];
        if (token.style.color) {
          styleParts.push(`color:${token.style.color}`);
        }
        if (token.style.backgroundColor) {
          styleParts.push(`background-color:${token.style.backgroundColor}`);
        }
        if (styleParts.length) {
          attrs.push(`style="${styleParts.join(";")}"`);
        }
      }
      html += `<span${attrs.length ? " " + attrs.join(" ") : ""}>`;
    } else if (token.kind === "close") {
      html += "</span>";
    }
  }
  return html;
}

function submit() {
  const text = draft.value;
  if (text.trim() === "") {
    return false;
  }
  emit("submit", text);
  // Preserve the typed speech when the send is rejected (disconnected,
  // mutations locked, or another mutation in flight); clear the draft only
  // when the send is actually dispatched (webclient-input-narrative: a blocked
  // borrowed send keeps the speech, never loses it).
  if (props.connected && !props.mutationsLocked && !props.inFlight) {
    draft.value = "";
  }
  resetHistoryWalk();
  return true;
}

// The single shared history-walk step (design D5): the ArrowUp/ArrowDown
// keys and the 上一筆/下一筆 buttons drive this same state — one walk, two
// input paths. Neither path submits.
function walkHistory(direction) {
  const history = props.history;
  if (direction === "up") {
    if (!history.length) {
      return;
    }
    if (historyIndex === null) {
      draftBackup = draft.value;
      historyIndex = history.length - 1;
    } else if (historyIndex > 0) {
      historyIndex -= 1;
    }
    draft.value = history[historyIndex];
    return;
  }
  if (historyIndex === null) {
    return;
  }
  if (historyIndex < history.length - 1) {
    historyIndex += 1;
    draft.value = history[historyIndex];
  } else {
    draft.value = draftBackup;
    resetHistoryWalk();
  }
}

function onKeyDown(event) {
  if (event.key === "Enter") {
    if (event.shiftKey) {
      return; // newline: the textarea's default behavior
    }
    event.preventDefault();
    submit();
    return;
  }
  if (event.key === "Escape") {
    event.preventDefault();
    resetHistoryWalk();
    emit("focus-parent");
    return;
  }
  if (event.key === "ArrowUp") {
    walkHistory("up");
    event.preventDefault();
    return;
  }
  if (event.key === "ArrowDown") {
    walkHistory("down");
    event.preventDefault();
  }
}

// The shell's `/` focus claim (design D2) and the dock's free-form borrow
// (design D6) both route through this one exposed method.
function focusField() {
  field.value?.focus();
}

function onChipInsert(verb) {
  // A chip prepares, it does not send: write the verb plus a trailing space
  // and focus the field (design D4).
  draft.value = String(verb) + " ";
  focusField();
}

function onHistoryUp() {
  walkHistory("up");
}

function onHistoryDown() {
  walkHistory("down");
}

function onOpenOverlay(name) {
  // The utility controls (design D10): 設定/說明 open the overlays through
  // the store's overlay slice (design D8).
  emit("open-overlay", name);
}

// The borrowed free-form dialogue release rule (design D6): the borrow is
// released whenever focus leaves the field for any reason other than that
// dock's own successful send — the parent clears the pending freeform
// target so a later ordinary command is never captured as dialogue speech.
function onFieldBlur() {
  emit("focus-lost");
}

defineExpose({ focusField });
</script>

<template>
  <div class="cmdline" aria-label="指令列" data-testid="command-line">
    <QuickWordChips :mode="mode" @insert="onChipInsert" />
    <div class="cmdfield" data-testid="command-line-input">
      <span v-if="!prompt" class="pt cmdfield__prompt" data-testid="command-line-prompt">›</span>
      <span v-else class="pt cmdfield__prompt" data-testid="command-line-prompt">
        <span v-html="promptHtml()" class="cmdfield__prompt-html"></span>
      </span>
      <div class="inputfieldwrapper">
        <textarea
          ref="field"
          id="inputfield"
          class="inputfield"
          data-testid="command-line-input-field"
          aria-label="指令輸入"
          spellcheck="false"
          rows="1"
          :value="draft"
          @input="draft = $event.target.value"
          @keydown="onKeyDown"
          @blur="onFieldBlur"
        ></textarea>
        <button
          type="button"
          class="inputsend"
          aria-label="送出指令"
          data-testid="command-line-send"
          @click="submit()"
        >
          ›
        </button>
      </div>
      <span class="hint">↑↓ 歷史</span>
      <span class="hist">
        <button
          type="button"
          aria-label="上一筆"
          data-testid="command-line-history-up"
          @click="onHistoryUp"
        >
          <svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9">
            <path d="M18 15l-6-6-6 6" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>
        <button
          type="button"
          aria-label="下一筆"
          data-testid="command-line-history-down"
          @click="onHistoryDown"
        >
          <svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9">
            <path d="M6 9l6 6 6-6" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>
      </span>
      <span class="cmdutil">
        <button
          type="button"
          class="cmdutil__btn"
          aria-label="技能系譜"
          data-testid="command-line-lineage"
          @click="onOpenOverlay('lineage')"
        >
          <svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <circle cx="12" cy="5" r="2.2" />
            <circle cx="5.5" cy="18.5" r="2.2" />
            <circle cx="18.5" cy="18.5" r="2.2" />
            <path d="M12 7.2v4.3M12 11.5 6.6 16.6M12 11.5l5.4 5.1" stroke-linecap="round" />
          </svg>
        </button>
        <button
          type="button"
          class="cmdutil__btn"
          aria-label="稱號冊"
          data-testid="command-line-codex"
          @click="onOpenOverlay('codex')"
        >
          <svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z" stroke-linecap="round" stroke-linejoin="round" />
            <path d="M5 17h14" stroke-linecap="round" />
            <path d="m12 7 .9 1.9 2.1.3-1.5 1.5.4 2-1.9-1-1.9 1 .4-2L9 9.2l2.1-.3z" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>
        <button
          type="button"
          class="cmdutil__btn"
          aria-label="設定"
          data-testid="command-line-settings"
          @click="onOpenOverlay('settings')"
        >
          <svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <circle cx="12" cy="12" r="3" />
            <path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9L17 7M7 17l-2.1 2.1" stroke-linecap="round" />
          </svg>
        </button>
        <button
          type="button"
          class="cmdutil__btn"
          aria-label="說明"
          data-testid="command-line-help"
          @click="onOpenOverlay('help')"
        >
          <svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <circle cx="12" cy="12" r="10" />
            <path d="M9.5 9a2.5 2.5 0 1 1 3.7 2.2c-.7.4-.7 1.3-.7 2.3M12 16h.01" stroke-linecap="round" />
          </svg>
        </button>
      </span>
    </div>
  </div>
</template>

<style scoped>
.cmdline {
  box-sizing: border-box;
  height: 46px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  background: var(--panel);
}

.cmdfield {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--panel-solid);
  border: var(--line);
  border-radius: var(--radius-sm);
  padding: 0 10px;
  height: 34px;
}

.cmdfield:focus-within {
  border-color: var(--gold-400);
  box-shadow: 0 0 0 1px var(--gold-400);
}

/* The prompt chevron and the prompt line are prose-scale targets (design
   D13): the `--prose-scale` token multiplies their sizes, never the
   general UI text. */
.cmdfield .pt {
  font-family: var(--f-mono);
  color: var(--seal-400);
  font-size: calc(16px * var(--prose-scale));
  flex: none;
}

.cmdfield__prompt-html {
  font-family: var(--f-mono);
  font-size: calc(13px * var(--prose-scale));
  color: var(--paper-500);
}

.inputfieldwrapper {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: stretch;
  gap: 0;
}

.inputfield {
  box-sizing: border-box;
  flex: 1 1 auto;
  resize: none;
  height: 34px;
  max-height: 34px;
  padding: 0 8px;
  font-family: var(--f-mono);
  font-size: var(--text-sm);
  color: var(--paper-50);
  background: transparent;
  border: 0;
  outline: none;
}

.inputsend {
  box-sizing: border-box;
  flex: none;
  width: 34px;
  height: 34px;
  margin: 0;
  display: grid;
  place-items: center;
  font-family: var(--f-mono);
  font-size: 14px;
  color: var(--paper-50);
  background: var(--seal-600);
  border: 1px solid var(--seal-400);
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.inputsend:hover {
  background: var(--seal-500);
}

.hint {
  flex: none;
  font-size: 11px;
  color: var(--paper-700);
  white-space: nowrap;
}

/* Constrained width (design D5): the hint cluster is the first element
   dropped, then the chip cluster scrolls; the field, the history controls
   and the utility controls are never dropped. Implemented as always-on
   flexbox degradation (no mobile breakpoint is shipped, design D1/D5). */
.cmdline .hint {
  flex-shrink: 3;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
}
.cmdline .qwc {
  flex-shrink: 1;
  min-width: 0;
  overflow-x: auto;
}

.hist {
  flex: none;
  display: flex;
  gap: 2px;
}

.hist button {
  width: 26px;
  height: 26px;
  display: grid;
  place-items: center;
  color: var(--paper-500);
  background: transparent;
  border: 0;
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.hist button:hover {
  background: var(--ink-700);
  color: var(--paper-100);
}

.hist .ic {
  width: 16px;
  height: 16px;
}

.cmdutil {
  flex: none;
  display: flex;
  gap: 4px;
}

.cmdutil__btn {
  /* The draft `.hist button` treatment (webclient-align-01-dock-chrome):
     transparent ground, 26×26, 6px radius, hover `--ink-700`. Positions,
     functions, labels, and accessibility attributes are unchanged. */
  width: 26px;
  height: 26px;
  display: grid;
  place-items: center;
  color: var(--paper-500);
  background: transparent;
  border: 0;
  border-radius: 6px;
  cursor: pointer;
}

.cmdutil__btn:hover {
  background: var(--ink-700);
  color: var(--paper-100);
}

.cmdutil__btn .ic {
  width: 15px;
  height: 15px;
}
</style>
