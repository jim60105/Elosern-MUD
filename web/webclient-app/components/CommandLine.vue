<script setup>
// Command line (H5, webclient-hud-05-overlays-and-command-line;
// webclient-collapsible-command-line design D1/D3/D4): the collapsible
// command-line bar filling HudFrame's 44px `command-line` anchor on the
// message region's top edge. The component stays mounted so `#inputfield`
// stays in the DOM inside `.inputfieldwrapper` (preserving the unsent draft,
// history-walk backup, and Tab-completion cycle while the anchor is
// collapsed with `display:none`). The bar renders, in this order: a `›`
// prompt chevron, `#inputfield` with its send control inside `.inputfieldwrapper`,
// the hint cluster (`↑↓ 歷史 · Tab 補全` —
// both affordances implemented, webclient-align-02-quickbar-shortcuts: Tab
// completes the draft before the caret over session history and the committed
// exploration panel's exit/target names; unique → full completion, many → longest-common-prefix then
// Tab/Shift+Tab cycle, none → untouched), and the 上一筆/下一筆 history controls
// (the pointer path to the same walk state the ArrowUp/ArrowDown keys drive).
// Overlay and drawer openers live in the top navigation bar's tool group.
//
// Preserved contract: the `#inputfield` field inside its `.inputfieldwrapper`
// wrapper does not move. The single send implementation is preserved
// byte-for-byte in behaviour: Enter without Shift sends exactly one command
// (regardless of how focus arrived), Shift+Enter inserts a newline, a
// send the field accepts clears the draft and emits `sent` (so the shell
// collapses the line and returns focus to `#action-dock`), and a rejected
// send (offline, mutations locked, or a mutation in flight) preserves the
// typed text and leaves the line open.
import { computed, nextTick, ref, watch } from "vue";
import NarrativeMarkup from "../lib/narrative_markup.js";

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
  // The action client's in-flight mutation flag (webclient-input-narrative):
  // a free-form send blocked by an in-flight mutation keeps the typed speech.
  inFlight: { type: Boolean, default: false },
  // The client-local text-to-HTML narrative preference: when off, the
  // prompt line (and the feed/full-log lines) render as literal text — the
  // preference chooses whether the pipeline runs, never what it permits.
  textToHtml: { type: Boolean, default: true },
  // Extra Tab-completion candidates: the committed exploration panel's exit
  // labels and interact-target display names (webclient-align-02, design
  // decision "Tab candidate set" — already-committed panel data only, zero
  // protocol change). Unavailable/absent panel → empty list.
  completionCandidates: { type: Array, default: () => [] },
});

const emit = defineEmits(["submit", "sent", "focus-parent", "focus-lost"]);

const field = ref(null);
const draft = ref("");

// Tab-completion cycle state (webclient-align-02): null = not cycling;
// otherwise the current candidate list and a cursor where -1 is the
// longest-common-prefix rung and 0..n-1 the candidate rungs (Tab advances,
// Shift+Tab reverses, both wrap). Any manual edit, send, or
// history walk resets it — the cycle never resurrects stale candidates.
let completion = null;

function resetCompletion() {
  completion = null;
}

// The candidate set: session history + the committed exploration panel
// names, deduplicated case-insensitively with first-seen order (history
// oldest-first, then panel rows — the cycle follows this stable order).
const candidateList = computed(() => {
  const seen = new Set();
  const out = [];
  for (const value of [...props.history, ...props.completionCandidates]) {
    const text = String(value ?? "");
    if (text === "") {
      continue;
    }
    const key = text.toLowerCase();
    if (!seen.has(key)) {
      seen.add(key);
      out.push(text);
    }
  }
  return out;
});

// A candidate-source change (history commit, mode switch, a fresh committed
// exploration panel) drops any in-flight cycle: cycling must never offer a
// completion the current committed sources no longer contain. The watch keys
// on canonicalized content, not array identity, so equal re-snapshots do not
// disturb the cycle.
watch(
  () => JSON.stringify(candidateList.value),
  resetCompletion,
);

function longestCommonPrefix(values) {
  if (!values.length) {
    return "";
  }
  let prefix = values[0];
  for (const value of values.slice(1)) {
    while (!value.toLowerCase().startsWith(prefix.toLowerCase())) {
      prefix = prefix.slice(0, -1);
    }
  }
  return prefix;
}

function caretStart() {
  const el = field.value;
  if (!el || typeof el.selectionStart !== "number") {
    return draft.value.length;
  }
  return el.selectionStart;
}

function placeCaretEnd() {
  const el = field.value;
  if (!el) {
    return;
  }
  nextTick(() => {
    el.setSelectionRange(el.value.length, el.value.length);
  });
}

// Tab inside the field: complete the draft text BEFORE the caret (the
// change design's caret-relative prefix rule); completion replaces the whole
// field — MUD-line semantics, no tokenization. Focus and text are unchanged
// when nothing matches.
function completeDraft(backward) {
  const prefix = draft.value.slice(0, caretStart());
  if (prefix.trim() === "") {
    resetCompletion();
    return;
  }
  if (!completion) {
    const lowered = prefix.toLowerCase();
    const matches = candidateList.value.filter((c) => c.toLowerCase().startsWith(lowered));
    if (!matches.length) {
      return;
    }
    if (matches.length === 1) {
      draft.value = matches[0];
      placeCaretEnd();
      return;
    }
    completion = { matches, index: -1 };
    // The LCP is over the MATCHES (every match already starts with the
    // typed prefix, so the field text only ever grows).
    draft.value = longestCommonPrefix(matches);
    placeCaretEnd();
    return;
  }
  const n = completion.matches.length;
  // Rungs: -1 = LCP, then 0..n-1 candidates; Tab steps forward, Shift+Tab
  // reverses, both wrap around the ring.
  const rungs = n + 1;
  const pos = completion.index + 1;
  completion.index = (backward ? pos - 1 + rungs : pos + 1) % rungs - 1;
  draft.value =
    completion.index === -1
      ? longestCommonPrefix(completion.matches)
      : completion.matches[completion.index];
  placeCaretEnd();
}

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
  // when the send is actually dispatched and emit `sent` so the shell
  // collapses the line and returns focus to `#action-dock` (design D3).
  if (props.connected && !props.mutationsLocked && !props.inFlight) {
    draft.value = "";
    emit("sent");
  }
  resetHistoryWalk();
  resetCompletion();
  return true;
}

// The single shared history-walk step (design D5): the ArrowUp/ArrowDown
// keys and the 上一筆/下一筆 buttons drive this same state — one walk, two
// input paths. Neither path submits.
function walkHistory(direction) {
  const history = props.history;
  resetCompletion();
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
  if (event.key === "Tab") {
    // Always claimed while candidates could match or the draft is being
    // completed: the default Tab would move focus out of the field, which
    // the requirement forbids (focus stays put even on a no-match draft).
    event.preventDefault();
    completeDraft(event.shiftKey);
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

function onHistoryUp() {
  walkHistory("up");
}

function onHistoryDown() {
  walkHistory("down");
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
  <div id="command-line-bar" class="cmdline" aria-label="指令列" data-testid="command-line">
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
          @input="draft = $event.target.value; resetCompletion()"
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
      <span class="hint">↑↓ 歷史 · Tab 補全</span>
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
    </div>
  </div>
</template>

<style scoped>
.cmdline {
  box-sizing: border-box;
  height: 100%;
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

/* Constrained width (design D5): the hint cluster is the first element dropped;
   the field, the send control, and the history controls are never dropped.
   Implemented as always-on flexbox degradation (no mobile breakpoint is
   shipped, design D1/D5). */
.cmdline .hint {
  flex-shrink: 3;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
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
</style>
