<script setup>
// DreamPanel: the collaborative dream of the cloud throne, staged as an AVG
// scene rather than a form. The artwork is the subject: a keepsake card (the
// 念頭 the player would carry out right now, plus the exits) sits in the
// art's empty sky, a reply bar docks to the top of a 2/3-width message band,
// and the band's right third stays open onto the goddess.
//
// Flow (every state is derived from the server-authored panel plus a few
// local refs; committed state is never gated by presentation):
//   arrival  — first mount with no exchange yet: the opening types as narration
//   turn     — the player may reply (`can_input`)
//   pending  — the goddess is answering: the player's words are echoed
//   reveal   — a live `completed` increase: scene narration, then her line
//   failure  — generation failed, nothing consumed: the reply bar is refilled
//   cap      — six exchanges spent: the reply bar becomes an end bar
// The 念頭 sheet (draft / confirm) and the awaken check are modal layers on
// top. Escape never awakens by itself: it closes the top layer, or moves
// focus to the 醒來 row.
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { createFocusTrap } from "./focus-trap.js";
import { useTypewriter } from "../composables/use-typewriter.js";
import { effectiveCps } from "../lib/message_reveal.js";

const props = defineProps({ state: { type: Object, required: true }, store: { type: Object, required: true } });

const MAX_SUMMARY = 2000;
const EXCHANGES = 6;
const GAUGE_STEPS = 5;
const tagFields = [
  { key: "themes", label: "想探索的主題" },
  { key: "atmosphere", label: "嚮往的氛圍" },
  { key: "participants", label: "希望登場的人物", hint: "只是創作偏好，不會改變人物的實際狀態。" },
  { key: "emphasis", label: "想多描寫的部分" },
  { key: "exclusions", label: "不想出現的內容", exclude: true },
];

const stage = ref(null);
const page = ref(null);
const replyInput = ref(null);
const awakenRow = ref(null);
const sheetEl = ref(null);
const summaryInput = ref(null);
const confirmEl = ref(null);
const confirmStay = ref(null);
const rows = ref(null);

const message = ref("");
const lastSent = ref("");
const direction = ref("");
const thread = ref("");
const tags = reactive(Object.fromEntries(tagFields.map(({ key }) => [key, []])));
const tagDrafts = reactive(Object.fromEntries(tagFields.map(({ key }) => [key, ""])));
const threadFilter = ref("");
const sheetOpen = ref(false);
const confirmOpen = ref(false);
const refusal = ref("");
const toast = ref("");
const announcement = ref("");
const artFailed = ref(false);
const bloom = ref(false);
const arrival = ref(false);
// The authoritative direction, thread and preference snapshot most recently
// copied into the local editor. A local edit that differs from it is the
// player's own and is never overwritten by a later publication.
const synced = reactive({ direction: "", thread: "", tags: JSON.stringify(tagFields.map(() => [])) });

let rootTrap = null;
let layerTrap = null;
let toastTimer = null;

// Mirrors the store's dispatch guard, so a control never looks usable while
// the dispatch it would make is refused.
const transportLocked = computed(() => {
  const view = props.store.view;
  return !view.connected || !!view.mutationsLocked || (view.phase != null && view.phase !== "active")
    || !!view.dispatch.inFlight || !!view.dispatch.beatLocked;
});
const savedDirection = computed(() => (props.state.direction_parts || []).join(""));
const summary = computed(() => direction.value.trim());
const summaryLength = computed(() => Array.from(direction.value.trim()).length);
const summaryTooLong = computed(() => summaryLength.value > MAX_SUMMARY);
const tagsSnapshot = () => JSON.stringify(tagFields.map(({ key }) => tags[key]));
const directionDirty = computed(() => direction.value.trim() !== synced.direction.trim() || thread.value !== synced.thread
  || tagsSnapshot() !== synced.tags);
const dirty = computed(() => !!message.value.trim() || directionDirty.value);
const atCap = computed(() => props.state.remaining === 0);
const ordinal = computed(() => Math.max(0, Math.min(GAUGE_STEPS - 1, props.state.track.ordinal)));
const knownThread = computed(() => props.state.thread_choices.find((choice) => choice.id === thread.value));
const threadLabel = computed(() => !thread.value ? "一段新的故事"
  : knownThread.value ? "延續：" + knownThread.value.label : "先前選定的故事線");
const visibleThreads = computed(() => {
  const needle = threadFilter.value.trim();
  return needle ? props.state.thread_choices.filter((choice) => choice.label.includes(needle)) : props.state.thread_choices;
});
const provenance = computed(() => {
  if (!summary.value) return "";
  if (directionDirty.value) return "已改寫・未記下";
  return props.state.draft_preferences ? "已記下" : "取自你剛才的話";
});
const overlayOpen = computed(() => sheetOpen.value || confirmOpen.value);

// ---- beats: what the message band is presenting ----
const beats = ref([]);
const beatIndex = ref(0);
let revealedCompleted = props.state.completed;
function responseBeats() {
  return [
    props.state.scene && { kind: "narration", text: props.state.scene },
    props.state.dialogue && { kind: "line", text: props.state.dialogue },
  ].filter(Boolean);
}
const beat = computed(() => {
  if (props.state.pending) return { kind: "echo", text: lastSent.value ? `你：「${lastSent.value}」` : "你的話語飄向王座……" };
  if (props.state.failure) return { kind: "notice", text: "夢境一時模糊，女神沒有回應。這次不算數，再說一次吧。" };
  return beats.value[beatIndex.value] || { kind: "narration", text: "" };
});
const beatUnits = computed(() => Array.from(beat.value.text));
const typewriter = useTypewriter({
  units: () => beatUnits.value.length,
  cps: () => effectiveCps(props.store.view.motionLevel, props.store.view.textSpeed),
});
const shownText = computed(() => beatUnits.value.slice(0, typewriter.typed.value).join(""));
const moreToRead = computed(() => typewriter.typing.value || beatIndex.value < beats.value.length - 1);
const speaking = computed(() => beat.value.kind === "line" || props.state.pending);

// Every change of the presented beat either types (a live reveal or the
// next beat) or shows in full (echo, notice, reconnect, re-read).
let typeNext = false;
let presenting = false;
watch(() => [beat.value.kind, beat.value.text], () => {
  if (presenting) return;
  const animate = typeNext;
  typeNext = false;
  if (animate) typewriter.start(0); else typewriter.complete();
}, { flush: "sync" });
function present(list, animate) {
  presenting = true;
  beats.value = list;
  beatIndex.value = animate ? 0 : Math.max(0, list.length - 1);
  presenting = false;
  if (animate) typewriter.start(0); else typewriter.complete();
}
function advance() {
  if (typewriter.typing.value) { typewriter.complete(); return; }
  if (beatIndex.value < beats.value.length - 1) {
    typeNext = true;
    beatIndex.value += 1;
    page.value?.scrollTo?.({ top: 0 });
    return;
  }
  focusHome();
}
function reread() {
  if (beatIndex.value > 0) beatIndex.value -= 1;
  // The control disappears on the first beat; keep focus on the page.
  page.value?.focus();
}

// ---- lifecycle ----
onMounted(() => {
  if (props.state.completed === 0 && !props.state.scene && !props.state.dialogue) {
    arrival.value = true;
    present([{ kind: "narration", text: props.state.opening }], true);
  } else {
    present(responseBeats().length ? responseBeats() : [{ kind: "narration", text: props.state.opening }], false);
  }
  rootTrap = createFocusTrap(stage.value, { initialFocusEl: initialFocus(), openerEl: document.activeElement });
  rootTrap.enter();
});
onUnmounted(() => { layerTrap = null; rootTrap?.restore(); rootTrap = null; clearTimeout(toastTimer); });

function initialFocus() {
  if (arrival.value) return page.value;
  if (atCap.value) return rows.value?.querySelector(summary.value ? "[data-row='confirm']" : "[data-row='edit']");
  return props.state.can_input ? replyInput.value : page.value;
}
function focusHome() {
  const target = atCap.value ? rows.value?.querySelector("[data-row='confirm']")
    : props.state.can_input && !transportLocked.value ? replyInput.value : page.value;
  target?.focus();
}

watch(() => props.state.session_id, () => { message.value = ""; lastSent.value = ""; });
watch(() => props.state.scene_art, () => { artFailed.value = false; });
watch(() => props.state.completed, (completed) => {
  // Only a live increase animates; a reconnect or same-count republish
  // keeps what is on screen.
  if (completed <= revealedCompleted) { revealedCompleted = completed; return; }
  revealedCompleted = completed;
  arrival.value = false;
  present(responseBeats(), true);
  const plate = `女神的興奮：${props.state.track.level}。`;
  announcement.value = [props.state.scene, props.state.dialogue && `王座上的女神說：${props.state.dialogue}`, plate,
    completed >= EXCHANGES ? "六次交談已盡。" : `尚可交談 ${EXCHANGES - completed} 次。`].filter(Boolean).join("\n");
  if (completed >= EXCHANGES) {
    bloom.value = true;
    nextTick(() => rows.value?.querySelector(summary.value ? "[data-row='confirm']" : "[data-row='edit']")?.focus());
  }
});
watch(() => props.state.pending, (pending) => {
  if (pending) {
    announcement.value = "女神正在回應。";
    if (document.activeElement === replyInput.value) page.value?.focus();
  }
});
watch(() => props.state.failure, (failure) => {
  if (!failure) return;
  announcement.value = "夢境一時模糊，女神沒有回應。這次不算數。";
  // Nothing was consumed: hand the player's words back for a retry.
  if (!message.value.trim() && lastSent.value) message.value = lastSent.value;
  nextTick(() => { if (props.state.can_input) replyInput.value?.focus(); });
});
watch(() => JSON.stringify([props.state.session_id, props.state.draft_preferences, props.state.direction_parts]), () => {
  const authoritative = savedDirection.value;
  // `dream say` republishes the authored direction on every exchange, so a
  // field the player has not edited follows it; an edited one keeps theirs.
  if (!direction.value.trim() || direction.value.trim() === synced.direction.trim()) direction.value = authoritative;
  synced.direction = authoritative;
  const draft = props.state.draft_preferences || {};
  const serverThread = draft.thread_id || "";
  if (thread.value === synced.thread) thread.value = serverThread;
  synced.thread = serverThread;
  const unedited = tagsSnapshot() === synced.tags;
  const serverTags = tagFields.map(({ key }) => Array.isArray(draft[key]) ? [...draft[key]] : []);
  if (unedited) tagFields.forEach(({ key }, index) => { tags[key] = serverTags[index]; });
  synced.tags = JSON.stringify(serverTags);
}, { immediate: true });

// ---- actions ----
function directionPayload() {
  const values = Object.fromEntries(tagFields.flatMap(({ key }) => tags[key].length ? [[key, [...tags[key]]]] : []));
  if (!summary.value && !thread.value && !Object.keys(values).length) return "";
  return { ...values, kind: thread.value ? "thread_direction" : "new_story", thread_id: thread.value || null, summary: summary.value };
}
function dispatch(action, extra = {}) {
  return props.store.dispatchAction("dream." + action,
    { session_id: props.state.session_id, revision: props.state.revision, ...extra }, null);
}
function say() {
  if (transportLocked.value || !props.state.can_input || !message.value.trim()) return;
  const units = Array.from(message.value);
  const request = dispatch("say", { message_parts: [units.slice(0, MAX_SUMMARY).join(""), units.slice(MAX_SUMMARY).join("")] });
  if (request) { lastSent.value = message.value.trim(); message.value = ""; }
}
async function confirm() {
  if (transportLocked.value) return;
  refusal.value = "";
  if (!summary.value || summaryTooLong.value) {
    refusal.value = summaryTooLong.value ? "念頭最多 2000 字，請再精簡一些。" : "念頭還是空的。寫下一句想帶走的話，或直接醒來。";
    if (!sheetOpen.value) await openSheet();
    summaryInput.value?.focus();
    return;
  }
  dispatch("confirm", { direction: directionPayload() });
}
function draft() {
  if (transportLocked.value) return;
  refusal.value = "";
  if (summaryTooLong.value) {
    refusal.value = "念頭最多 2000 字，請再精簡一些。";
    if (!sheetOpen.value) openSheet();
    return;
  }
  const request = dispatch("draft", { direction: directionPayload() });
  if (!request) return;
  if (sheetOpen.value) closeSheet();
  // The toast confirms what the server committed: it waits for the newer
  // revision to carry a saved draft, and a refused draft shows nothing.
  draftRevision = props.state.revision;
}
let draftRevision = null;
watch(() => props.state.revision, (revision) => {
  if (draftRevision === null || revision <= draftRevision) return;
  draftRevision = null;
  if (props.state.draft_preferences) showToast("念頭已記下，夢仍在繼續。");
});
function requestAwaken() {
  if (transportLocked.value) return;
  if (!dirty.value) { dispatch("awaken"); return; }
  openConfirm();
}
function awaken() {
  if (transportLocked.value) return;
  dispatch("awaken");
}
function showToast(text) {
  toast.value = text;
  announcement.value = text;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.value = ""; }, 2600);
}

// ---- layers ----
async function openLayer(open, container, initial) {
  const opener = document.activeElement;
  open.value = true;
  await nextTick();
  // A close in the same tick leaves nothing to trap.
  if (!open.value || !container.value) return;
  layerTrap = createFocusTrap(container.value, { initialFocusEl: initial(), openerEl: opener });
  layerTrap.enter();
}
function closeLayer(open) {
  open.value = false;
  const trap = layerTrap;
  layerTrap = null;
  nextTick(() => trap?.restore());
}
function openSheet() { threadFilter.value = ""; return openLayer(sheetOpen, sheetEl, () => summaryInput.value); }
function closeSheet() { refusal.value = ""; closeLayer(sheetOpen); }
function openConfirm() { return openLayer(confirmOpen, confirmEl, () => confirmStay.value); }
function closeConfirm() { closeLayer(confirmOpen); }
function revertSummary() { direction.value = savedDirection.value; summaryInput.value?.focus(); }

function addTag(key) {
  const value = tagDrafts[key].trim();
  if (value && !tags[key].includes(value)) tags[key] = [...tags[key], value];
  tagDrafts[key] = "";
}
function onTagKeydown(event, key) {
  if (event.isComposing) return;
  if (event.key === "Enter") { event.preventDefault(); addTag(key); }
  else if (event.key === "Backspace" && !tagDrafts[key] && tags[key].length) tags[key] = tags[key].slice(0, -1);
}
function removeTag(key, value) { tags[key] = tags[key].filter((item) => item !== value); }

// ---- keyboard ----
const isTextField = (el) => el && (el.tagName === "TEXTAREA" || (el.tagName === "INPUT" && el.type !== "radio"));
function onReplyKeydown(event) {
  if (event.isComposing) return;
  if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); say(); }
}
function onPageKeydown(event) {
  if ((event.key === "Enter" || event.key === " ") && !event.repeat && event.target === page.value) {
    event.preventDefault();
    advance();
  }
}
function onPageClick() {
  if (globalThis.getSelection?.()?.toString()) return;
  advance();
}
function onRowsKeydown(event) {
  if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
  const buttons = Array.from(rows.value.querySelectorAll("button"));
  const index = buttons.indexOf(document.activeElement);
  if (index < 0) return;
  event.preventDefault();
  buttons[(index + (event.key === "ArrowDown" ? 1 : buttons.length - 1)) % buttons.length].focus();
}
function onKeydown(event) {
  // An IME composition (Traditional Chinese input) owns its own keys.
  if (event.isComposing) return;
  if (event.key === "Tab") { (layerTrap || rootTrap)?.onKeydown(event); return; }
  event.stopPropagation();
  if (event.key === "Escape") {
    event.preventDefault();
    if (confirmOpen.value) closeConfirm();
    else if (sheetOpen.value) closeSheet();
    else if (isTextField(event.target)) page.value?.focus();
    else { awakenRow.value?.focus(); announcement.value = "再按 Enter 醒來，或繼續交談。"; }
    return;
  }
  if (sheetOpen.value && event.key === "Enter" && (event.ctrlKey || event.metaKey)) { event.preventDefault(); confirm(); return; }
  if (!overlayOpen.value && !isTextField(event.target) && !event.ctrlKey && !event.metaKey && !event.altKey && /^[123]$/.test(event.key)) {
    event.preventDefault();
    rows.value?.querySelectorAll("button")[Number(event.key) - 1]?.click();
  }
}
</script>

<template>
  <section ref="stage" class="dream-scene" :class="{ 'dream-scene--arrival': arrival, 'dream-scene--no-art': !state.scene_art || artFailed }"
    role="dialog" aria-modal="true" aria-labelledby="dream-title" tabindex="-1" data-testid="dream-panel"
    :data-state="state.pending ? 'pending' : state.failure ? 'failure' : atCap ? 'cap' : arrival ? 'arrival' : 'turn'"
    :style="{ '--dream-ordinal': ordinal }" @keydown="onKeydown">
    <img v-if="state.scene_art && !artFailed" class="dream-scene__art" :src="state.scene_art" alt="雲海之上的純白王座與王座上的女神" decoding="async" @error="artFailed = true" />
    <div class="dream-scene__veil" aria-hidden="true"></div>
    <div v-if="bloom" class="dream-scene__bloom" aria-hidden="true" @animationend="bloom = false"></div>
    <div v-if="$slots.storyTools" class="dream-scene__story-tools"><slot name="storyTools" /></div>

    <div class="dream-scene__main" :inert="overlayOpen || undefined">
      <header class="dream-crest">
        <h2 id="dream-title">雲上王座之夢</h2>
        <p>夢中無晝夜</p>
      </header>

      <nav class="dream-keepsake dream-glass" :class="{ 'dream-keepsake--promoted': atCap }" aria-labelledby="dream-keepsake-title">
        <span class="dream-corners" aria-hidden="true"></span>
        <div class="dream-keepsake__head">
          <h3 id="dream-keepsake-title">此刻的念頭</h3>
          <span v-if="provenance" class="dream-keepsake__chip">{{ provenance }}</span>
        </div>
        <blockquote v-if="summary" class="dream-keepsake__preview" :title="summary">{{ summary }}</blockquote>
        <p v-else class="dream-keepsake__empty">念頭尚未成形。和女神談談，或親手寫下。</p>
        <p class="dream-keepsake__target">歸屬：{{ threadLabel }}</p>
        <div ref="rows" class="dream-choice" role="group" aria-label="念頭與醒來" @keydown="onRowsKeydown">
          <button class="ui-btn dream-choice__row" type="button" data-row="edit" :disabled="transportLocked" @click="openSheet">
            <span class="dream-choice__badge" aria-hidden="true">1</span>{{ summary ? "改寫念頭…" : "寫下念頭…" }}
          </button>
          <button class="ui-btn dream-choice__row dream-choice__row--carry" :class="{ 'ui-btn--primary': atCap }" type="button" data-row="confirm" :disabled="transportLocked"
            :aria-disabled="!summary || undefined" :aria-describedby="!summary ? 'dream-confirm-reason' : undefined" @click="confirm">
            <span class="dream-choice__badge" aria-hidden="true">2</span>帶著這個念頭醒來
            <span v-if="!summary" id="dream-confirm-reason" class="dream-choice__reason">尚無念頭</span>
          </button>
          <button class="ui-btn dream-choice__row" type="button" data-row="draft" :disabled="transportLocked" @click="draft">
            <span class="dream-choice__badge" aria-hidden="true">3</span>{{ atCap ? "記下念頭" : "記下念頭，繼續作夢" }}
          </button>
          <button ref="awakenRow" class="ui-btn ui-btn--ghost dream-choice__row" type="button" data-row="awaken" :disabled="transportLocked" @click="requestAwaken">
            <span class="dream-choice__badge dream-choice__badge--seal" aria-hidden="true">✕</span>醒來
          </button>
        </div>
      </nav>

      <div class="dream-reply-zone">
        <p v-if="!store.view.connected" class="dream-reply__caption" role="status">與夢的聯繫中斷了，正在重新連結……你寫下的字句都會保留。</p>
        <p v-else-if="!atCap && state.remaining === 1" class="dream-reply__caption">夢將抵達盡頭 · 最後一次交談</p>
        <p v-else-if="!atCap && state.track.converging" class="dream-reply__caption">夢將抵達盡頭</p>
        <div v-if="atCap && !state.pending" class="dream-reply dream-glass dream-reply--ended">
          <p>六次交談已盡，女神靜候你的決定。</p>
          <div class="dream-pips" role="meter" aria-valuemin="0" :aria-valuemax="EXCHANGES" :aria-valuenow="state.remaining" :aria-valuetext="`尚可交談 ${state.remaining} 次，共 ${EXCHANGES} 次`">
            <i v-for="n in EXCHANGES" :key="n" class="dream-pip dream-pip--spent"></i>
          </div>
        </div>
        <form v-else class="dream-reply dream-glass" :class="{ 'dream-reply--failed': state.failure }" data-testid="dream-reply" @submit.prevent="say">
          <span class="dream-reply__tag" aria-hidden="true">你</span>
          <textarea ref="replyInput" v-model="message" class="dream-reply__input" rows="1" maxlength="4000" aria-label="對女神說的話"
            :disabled="!state.can_input || transportLocked" :placeholder="state.pending ? '女神正在回應……' : '對女神說些什麼……'"
            @keydown="onReplyKeydown" @input="typewriter.typing.value && typewriter.complete()" />
          <div class="dream-pips" role="meter" aria-valuemin="0" :aria-valuemax="EXCHANGES" :aria-valuenow="state.remaining" :aria-valuetext="`尚可交談 ${state.remaining} 次，共 ${EXCHANGES} 次`">
            <i v-for="n in EXCHANGES" :key="n" class="dream-pip"
              :class="{ 'dream-pip--spent': n <= state.completed, 'dream-pip--next': n === state.completed + 1 && (message.trim() || state.pending) }"></i>
            <span class="dream-pips__count">尚餘 {{ state.remaining }}</span>
          </div>
          <button class="ui-btn ui-btn--primary ui-btn--sm dream-reply__send" type="submit" aria-keyshortcuts="Enter"
            :disabled="transportLocked || !state.can_input || !message.trim()">{{ state.failure ? "再說一次" : "訴說" }}</button>
        </form>
      </div>

      <section class="dream-window" aria-label="夢境對話">
        <header class="dream-plate" :class="{ 'dream-plate--quiet': !speaking }">
          <span class="dream-plate__name">王座上的女神</span>
          <span class="dream-gauge" role="meter" aria-valuemin="0" :aria-valuemax="GAUGE_STEPS - 1" :aria-valuenow="ordinal" :aria-valuetext="`女神的興奮：${state.track.level}`">
            <i v-for="n in GAUGE_STEPS" :key="n" class="dream-gauge__seg" :class="{ 'dream-gauge__seg--lit': n <= ordinal + 1 }"></i>
          </span>
          <span class="dream-plate__level">{{ state.track.level }}</span>
          <span v-if="state.pending" class="dream-plate__breath"><i></i><i></i><i></i>正在回應</span>
        </header>
        <div ref="page" class="dream-page" tabindex="0" aria-describedby="dream-keys" data-testid="dream-page"
          @keydown="onPageKeydown" @click="onPageClick">
          <p class="dream-page__beat" :class="`dream-page__beat--${beat.kind}`">{{ shownText }}</p>
        </div>
        <footer class="dream-strip">
          <button v-if="beatIndex > 0 && !state.pending && !state.failure" class="ui-btn ui-btn--ghost ui-btn--sm" type="button" @click="reread">重讀</button>
          <span id="dream-keys" class="dream-strip__keys">{{ moreToRead && !state.pending ? "Enter 繼續" : "Esc 前往醒來" }}</span>
          <span class="dream-strip__marker" aria-hidden="true">{{ moreToRead && !state.pending ? "▼" : "■" }}</span>
        </footer>
      </section>
    </div>

    <p v-if="toast" class="dream-toast" role="status">{{ toast }}</p>
    <p class="dream-live" aria-live="polite">{{ announcement }}</p>

    <template v-if="sheetOpen">
      <div class="dream-sheet__scrim" aria-hidden="true" @click="closeSheet"></div>
      <aside ref="sheetEl" class="dream-sheet dream-glass" role="dialog" aria-modal="true" aria-labelledby="dream-sheet-title" data-testid="dream-sheet">
        <span class="dream-corners" aria-hidden="true"></span>
        <header class="dream-sheet__head">
          <div><h3 id="dream-sheet-title">整理念頭</h3><p>醒來後，故事會朝這個方向慢慢展開。</p></div>
          <button class="ui-btn ui-btn--ghost ui-btn--sm" type="button" @click="closeSheet">返回</button>
        </header>
        <div class="dream-sheet__body">
          <label class="dream-field">
            <span class="dream-field__label">想帶走的念頭 <em v-if="provenance">{{ provenance }}</em></span>
            <textarea ref="summaryInput" v-model="direction" rows="4" :disabled="transportLocked" placeholder="寫下你希望故事接下來的走向。"
              :aria-invalid="summaryTooLong || undefined" />
          </label>
          <div class="dream-field__foot">
            <button v-if="direction !== savedDirection && savedDirection" class="dream-link" type="button" @click="revertSummary">還原為剛才的話</button>
            <span class="dream-field__counter" :class="{ 'dream-field__counter--over': summaryTooLong }">{{ summaryLength }} / {{ MAX_SUMMARY }}</span>
          </div>
          <p v-if="refusal" class="dream-field__error" role="alert">{{ refusal }}</p>

          <fieldset class="dream-threads">
            <legend>這個念頭屬於……</legend>
            <input v-if="state.thread_choices.length > 8" v-model="threadFilter" class="dream-threads__filter" type="search" placeholder="搜尋故事線" aria-label="搜尋故事線" />
            <div class="dream-threads__list">
              <label class="dream-threads__option"><input v-model="thread" type="radio" name="dream-thread" value="" :disabled="transportLocked" /><span>一段新的故事</span></label>
              <label v-if="thread && !knownThread" class="dream-threads__option"><input v-model="thread" type="radio" name="dream-thread" :value="thread" /><span>先前選定的故事線（已不在清單中）</span></label>
              <label v-for="choice in visibleThreads" :key="choice.id" class="dream-threads__option" :title="choice.label">
                <input v-model="thread" type="radio" name="dream-thread" :value="choice.id" :disabled="transportLocked" /><span>{{ choice.label }}</span>
              </label>
              <p v-if="threadFilter && !visibleThreads.length" class="dream-threads__empty">沒有相符的故事線</p>
            </div>
          </fieldset>

          <section class="dream-tags" aria-labelledby="dream-tags-title">
            <h4 id="dream-tags-title">細節（皆可留空）</h4>
            <div v-for="field in tagFields" :key="field.key" class="dream-tags__row" :class="{ 'dream-tags__row--exclude': field.exclude }">
              <span :id="`dream-tag-${field.key}`" class="dream-tags__label">{{ field.label }}</span>
              <div class="dream-tags__box">
                <span v-for="value in tags[field.key]" :key="value" class="dream-tags__chip">{{ value }}<button type="button" :aria-label="`移除「${value}」`" @click="removeTag(field.key, value)">×</button></span>
                <input v-model="tagDrafts[field.key]" type="text" :aria-labelledby="`dream-tag-${field.key}`" placeholder="輸入後按 Enter"
                  :disabled="transportLocked" @keydown="onTagKeydown($event, field.key)" @blur="addTag(field.key)" />
              </div>
              <small v-if="field.hint" class="dream-tags__hint">{{ field.hint }}</small>
            </div>
          </section>
        </div>
        <footer class="dream-sheet__foot">
          <p>記下：私下保存，夢仍繼續。帶著醒來：結束夢境，故事將朝此展開。</p>
          <div>
            <button class="ui-btn" type="button" :disabled="transportLocked" @click="draft">記下念頭</button>
            <button class="ui-btn ui-btn--primary" type="button" :disabled="transportLocked" @click="confirm">帶著這個念頭醒來</button>
          </div>
        </footer>
      </aside>
    </template>

    <template v-if="confirmOpen">
      <div class="dream-sheet__scrim" aria-hidden="true" @click="closeConfirm"></div>
      <div ref="confirmEl" class="dream-confirm dream-glass" role="alertdialog" aria-modal="true" aria-labelledby="dream-confirm-title" aria-describedby="dream-confirm-body" data-testid="dream-confirm">
        <span class="dream-corners" aria-hidden="true"></span>
        <h3 id="dream-confirm-title">就此醒來？</h3>
        <div id="dream-confirm-body">
          <p v-if="message.trim()">尚未說出口的話會隨夢消散。</p>
          <p v-if="directionDirty">尚未記下的改寫會隨夢消散。</p>
          <p v-if="!state.draft_preferences && savedDirection">你最後說的話會自動留作念頭草稿。</p>
        </div>
        <div class="dream-confirm__actions">
          <button ref="confirmStay" class="ui-btn" type="button" @click="closeConfirm">回到夢中</button>
          <button class="ui-btn ui-btn--ghost" type="button" :disabled="transportLocked" @click="awaken">醒來</button>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.dream-scene {
  /* The excitement ordinal (0–4); the inline style binds the server value. */
  --dream-ordinal: 0;
  --dream-gutter: calc(40px * var(--ui-scale));
  --dream-band-w: 66.667%;
  --dream-glass: linear-gradient(180deg, rgba(16, 18, 22, 0.86), rgba(11, 13, 16, 0.93));
  --dream-halo: 0 calc(10px * var(--ui-scale)) calc(36px * var(--ui-scale)) calc(-14px * var(--ui-scale)) rgba(255, 250, 238, 0.6);
  position: fixed; isolation: isolate; inset: var(--header-h) 0 var(--workspace-bottom); z-index: var(--z-surface-modal);
  overflow: hidden; background: #dcdcda; color: var(--paper-100); font-family: var(--f-sans);
}
.dream-scene:focus { box-shadow: none; outline: none; }
.dream-scene p, .dream-scene h2, .dream-scene h3, .dream-scene h4, .dream-scene blockquote { margin: 0; }
.dream-scene__art { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: 68% 62%; }
/* The pale fallback keeps the art's luminance so the chrome reads the same
   without it; the rose aura deepens with the goddess's excitement. */
.dream-scene__veil { position: absolute; inset: 0; pointer-events: none;
  background: radial-gradient(ellipse 46% 60% at 72% 45%, rgba(214, 120, 140, calc(var(--dream-ordinal) * 0.055)), transparent 70%);
  mix-blend-mode: multiply; transition: background var(--motion-scene) var(--ease-standard); }
.dream-scene--no-art .dream-scene__veil { mix-blend-mode: normal;
  background: radial-gradient(ellipse 46% 60% at 72% 45%, rgba(214, 120, 140, calc(var(--dream-ordinal) * 0.055)), transparent 70%), linear-gradient(180deg, #e9e7e3, #cfd3d6); }
.dream-scene--arrival::after { content: ""; position: absolute; inset: 0; z-index: 5; pointer-events: none; background: #fbfaf7;
  animation: dream-fade-out calc(var(--motion-scene) * 2) var(--ease-standard) forwards; opacity: 0; }
.dream-scene__bloom { position: absolute; inset: 0; z-index: 4; pointer-events: none; background: #fff8f2; opacity: 0;
  animation: dream-bloom calc(var(--motion-flash) + var(--motion-scene)) var(--ease-standard); }
@keyframes dream-fade-out { from { opacity: 1; } to { opacity: 0; } }
@keyframes dream-bloom { 0% { opacity: 0; } 20% { opacity: var(--motion-flash-peak); } 100% { opacity: 0; } }
@keyframes dream-rise { from { opacity: 0; transform: translateY(calc(var(--motion-shift-sm) * var(--motion-travel))); } to { opacity: 1; transform: none; } }
.dream-scene__story-tools { position: absolute; z-index: 6; top: var(--sp-3); right: var(--sp-5); max-width: 40%; padding: var(--sp-2); background: var(--panel); color: var(--paper-300); }
.dream-scene__main { position: absolute; inset: 0; }

/* Ink lacquer glass: legible over near-white art, set into the light by a
   pale halo instead of a dark drop shadow. */
.dream-glass { position: relative; box-sizing: border-box; background: var(--dream-glass);
  backdrop-filter: blur(calc(12px * var(--ui-scale))) saturate(1.05);
  border-top: 1px solid var(--band-edge); box-shadow: var(--dream-halo), inset 0 1px rgba(255, 255, 255, 0.06); }
.dream-corners { position: absolute; inset: calc(6px * var(--ui-scale)); pointer-events: none; --c: var(--gold-500); --l: calc(14px * var(--ui-scale));
  background:
    linear-gradient(var(--c), var(--c)) top left / var(--l) 1px no-repeat, linear-gradient(var(--c), var(--c)) top left / 1px var(--l) no-repeat,
    linear-gradient(var(--c), var(--c)) top right / var(--l) 1px no-repeat, linear-gradient(var(--c), var(--c)) top right / 1px var(--l) no-repeat,
    linear-gradient(var(--c), var(--c)) bottom left / var(--l) 1px no-repeat, linear-gradient(var(--c), var(--c)) bottom left / 1px var(--l) no-repeat,
    linear-gradient(var(--c), var(--c)) bottom right / var(--l) 1px no-repeat, linear-gradient(var(--c), var(--c)) bottom right / 1px var(--l) no-repeat; }

/* ---- crest ---- */
.dream-crest { position: absolute; top: calc(20px * var(--ui-scale)); left: var(--dream-gutter); display: flex; align-items: baseline; gap: var(--sp-3);
  padding: var(--sp-2) var(--sp-8) var(--sp-2) var(--sp-4); background: linear-gradient(90deg, rgba(11, 13, 16, 0.86), rgba(11, 13, 16, 0.72) 80%, transparent);
  border-left: 2px solid var(--gold-500); animation: dream-rise var(--motion-reveal) var(--ease-standard) both; }
.dream-crest h2 { color: var(--gold-300); font-family: var(--f-display); font-size: var(--text-xl); font-weight: 500; letter-spacing: 0.14em; }
.dream-crest p { color: var(--paper-300); font-size: var(--text-xs); letter-spacing: 0.2em; }

/* ---- keepsake card ---- */
.dream-keepsake { position: absolute; top: calc(84px * var(--ui-scale)); left: var(--dream-gutter); display: grid; gap: var(--sp-3);
  width: min(calc(440px * var(--ui-scale)), 32vw); max-height: calc(100% - var(--band-h) - 172px * var(--ui-scale)); overflow-y: auto;
  padding: var(--sp-5) var(--sp-5) var(--sp-4); border-radius: var(--radius-sm);
  animation: dream-rise var(--motion-reveal) var(--ease-standard) both; transition: box-shadow var(--motion-base) var(--ease-standard); }
.dream-keepsake--promoted { border-top-color: var(--gold-400); box-shadow: var(--dream-halo), 0 0 0 1px var(--gold-500), 0 0 calc(28px * var(--ui-scale)) var(--gold-glow); }
.dream-keepsake__head { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: var(--sp-2); }
.dream-keepsake__head h3 { color: var(--gold-300); font-family: var(--f-display); font-size: var(--text-md); font-weight: 500; letter-spacing: 0.1em; }
.dream-keepsake__chip { padding: 0 var(--sp-2); border: 1px solid var(--band-edge-dim); border-radius: var(--radius-pill); color: var(--gold-400); font-size: var(--text-xs); }
.dream-keepsake__preview { display: -webkit-box; overflow: hidden; -webkit-box-orient: vertical; -webkit-line-clamp: 3; line-clamp: 3;
  padding-left: var(--sp-3); border-left: 2px solid var(--gold-500); color: var(--paper-50); font-family: var(--f-serif); font-size: var(--text-md);
  line-height: 1.6; white-space: pre-wrap; overflow-wrap: anywhere; }
.dream-keepsake__empty { color: var(--paper-400); font-size: var(--text-sm); line-height: 1.6; }
.dream-keepsake__target { color: var(--paper-400); font-size: var(--text-xs); overflow-wrap: anywhere; display: -webkit-box; overflow: hidden; -webkit-box-orient: vertical; -webkit-line-clamp: 2; line-clamp: 2; }
.dream-choice { display: grid; gap: var(--sp-1); padding-top: var(--sp-3); border-top: 1px solid var(--band-edge-dim); }
.dream-choice__row { justify-content: flex-start; min-height: calc(40px * var(--ui-scale)); white-space: normal; text-align: left; }
.dream-choice__row.ui-btn:not(.ui-btn--primary) { background: transparent; border-color: transparent; }
.dream-choice__row.ui-btn:not(.ui-btn--primary):hover:enabled, .dream-choice__row.ui-btn:not(.ui-btn--primary):focus-visible { background: var(--panel-hi); border-color: transparent; box-shadow: inset 2px 0 var(--gold-400); }
.dream-choice__row[aria-disabled="true"] { filter: saturate(0.4) brightness(0.8); }
.dream-choice__badge { display: inline-grid; place-items: center; flex: none; width: calc(22px * var(--ui-scale)); height: calc(22px * var(--ui-scale));
  border: 1px solid var(--gold-500); border-radius: 50%; color: var(--gold-400); font-family: var(--f-mono); font-size: var(--text-xs); line-height: 1; }
.ui-btn--primary .dream-choice__badge { border-color: var(--ink-950); color: var(--ink-950); }
.dream-choice__row--carry:not(.ui-btn--primary) { color: var(--gold-300); }
.dream-choice__row--carry:not(.ui-btn--primary) .dream-choice__badge { background: var(--gold-500); border-color: var(--gold-400); color: var(--ink-950); }
.dream-choice__badge--seal { border-color: var(--seal-600); color: var(--seal-400); }
.dream-choice__reason { margin-left: auto; font-size: var(--text-xs); font-weight: 400; opacity: 0.8; }

/* ---- reply bar ---- */
.dream-reply-zone { position: absolute; left: calc(24px * var(--ui-scale)); bottom: calc(var(--band-h) + 10px * var(--ui-scale));
  display: grid; gap: var(--sp-2); width: calc(var(--dream-band-w) - 72px * var(--ui-scale)); }
.dream-reply__caption { justify-self: end; padding: var(--sp-1) var(--sp-3); border-radius: var(--radius-pill); background: rgba(11, 13, 16, 0.78);
  color: var(--gold-300); font-size: var(--text-xs); letter-spacing: 0.08em; }
.dream-reply { display: flex; align-items: center; gap: var(--sp-3); min-height: calc(56px * var(--ui-scale)); padding: var(--sp-2) var(--sp-3) var(--sp-2) var(--sp-4); border-radius: var(--radius-sm); }
.dream-reply--failed { border-top-color: var(--warn); }
.dream-reply--ended p { flex: 1; color: var(--gold-300); font-family: var(--f-serif); font-size: var(--text-md); }
.dream-reply__tag { flex: none; padding-right: var(--sp-3); border-right: 1px solid var(--band-edge-dim); color: var(--gold-400); font-family: var(--f-display); font-size: var(--text-md); }
.dream-reply__input { flex: 1; min-width: 0; box-sizing: border-box; field-sizing: content; min-height: calc(36px * var(--ui-scale)); max-height: calc(132px * var(--ui-scale));
  padding: var(--sp-1) 0; border: 0; background: transparent; color: var(--paper-50); font-family: var(--f-serif); font-size: var(--text-md); line-height: 1.6; resize: none; }
.dream-reply__input:focus { outline: none; box-shadow: none; }
.dream-reply:focus-within { box-shadow: var(--dream-halo), inset 0 0 0 1px var(--gold-500); }
.dream-reply__input::placeholder { color: var(--paper-500); }
.dream-reply__input:disabled { cursor: default; }
.dream-pips { display: flex; flex: none; align-items: center; gap: calc(6px * var(--ui-scale)); }
.dream-pip { display: block; width: calc(9px * var(--ui-scale)); height: calc(9px * var(--ui-scale)); transform: rotate(45deg); background: var(--gold-400);
  box-shadow: 0 0 calc(6px * var(--ui-scale)) var(--gold-glow); transition: background var(--motion-reveal) var(--ease-standard), box-shadow var(--motion-reveal) var(--ease-standard); }
.dream-pip--spent { background: transparent; box-shadow: inset 0 0 0 1px var(--paper-700); }
.dream-pip--next { animation: dream-pulse var(--motion-pulse) ease-in-out infinite; }
@keyframes dream-pulse { 50% { opacity: 0.35; } }
.dream-pips__count { margin-left: var(--sp-2); color: var(--paper-300); font-size: var(--text-xs); font-variant-numeric: tabular-nums; white-space: nowrap; }

/* ---- message band ---- */
.dream-window { position: absolute; left: 0; bottom: 0; box-sizing: border-box; display: grid; grid-template-rows: auto 1fr auto; width: var(--dream-band-w); height: var(--band-h);
  padding: var(--sp-3) calc(96px * var(--ui-scale)) var(--band-pad-bottom) var(--dream-gutter);
  background: linear-gradient(90deg, rgba(11, 13, 16, 0.93) 0 calc(100% - 96px * var(--ui-scale)), transparent),
    var(--band-ornament) center top / calc(30px * var(--ui-scale)) calc(11px * var(--ui-scale)) no-repeat;
  backdrop-filter: blur(calc(12px * var(--ui-scale)));
  mask-image: linear-gradient(90deg, #000 calc(100% - 96px * var(--ui-scale)), transparent);
  box-shadow: inset 0 1px var(--band-edge); }
.dream-plate { display: flex; align-items: center; gap: var(--sp-3); padding-bottom: var(--sp-2); }
.dream-plate__name { position: relative; padding-left: calc(14px * var(--ui-scale)); color: var(--gold-300); font-family: var(--f-display); font-size: var(--text-lg);
  transition: color var(--motion-base) var(--ease-standard); }
.dream-plate__name::before { content: ""; position: absolute; left: 0; top: 50%; width: calc(6px * var(--ui-scale)); height: calc(6px * var(--ui-scale)); transform: translateY(-50%) rotate(45deg); background: var(--gold-400); }
.dream-plate--quiet .dream-plate__name { color: var(--paper-500); }
.dream-gauge { display: flex; gap: calc(4px * var(--ui-scale)); }
.dream-gauge__seg { display: block; width: calc(26px * var(--ui-scale)); height: calc(6px * var(--ui-scale)); box-shadow: inset 0 0 0 1px var(--ink-600);
  transition: background var(--motion-slow) var(--ease-standard), box-shadow var(--motion-slow) var(--ease-standard); }
.dream-gauge__seg--lit { background: var(--gold-500); box-shadow: 0 0 calc(6px * var(--ui-scale)) var(--gold-glow); }
.dream-gauge__seg--lit:nth-child(4) { background: #c98166; }
.dream-gauge__seg--lit:nth-child(5) { background: var(--seal-400); box-shadow: 0 0 calc(8px * var(--ui-scale)) var(--seal-glow); }
.dream-plate__level { color: var(--paper-300); font-size: var(--text-sm); }
.dream-plate__breath { display: inline-flex; align-items: center; gap: calc(5px * var(--ui-scale)); margin-left: auto; color: var(--paper-400); font-size: var(--text-xs); }
.dream-plate__breath i { width: calc(6px * var(--ui-scale)); height: calc(6px * var(--ui-scale)); transform: rotate(45deg); background: var(--gold-400); animation: dream-pulse var(--motion-pending) ease-in-out infinite; }
.dream-plate__breath i:nth-child(2) { animation-delay: calc(var(--motion-pending) / 6); }
.dream-plate__breath i:nth-child(3) { animation-delay: calc(var(--motion-pending) / 3); }
.dream-page { margin-left: calc(-1 * var(--sp-3)); padding-left: var(--sp-3); min-height: 0; overflow-y: auto; cursor: pointer; scrollbar-width: thin; scrollbar-color: var(--ink-600) transparent; }
.dream-page:focus { outline: none; }
.dream-page:focus-visible { box-shadow: inset 2px 0 var(--gold-400); }
.dream-page__beat { max-width: 42em; color: var(--paper-100); font-family: var(--f-serif); font-size: calc(var(--message-text) * var(--prose-scale) * 1.25);
  line-height: 1.75; white-space: pre-wrap; overflow-wrap: anywhere; }
.dream-page__beat--line { color: var(--paper-50); }
.dream-page__beat--narration { color: var(--paper-200); }
.dream-page__beat--echo { color: var(--paper-400); font-size: calc(var(--message-text) * var(--prose-scale)); display: -webkit-box; overflow: hidden; -webkit-box-orient: vertical; -webkit-line-clamp: 3; line-clamp: 3; }
.dream-page__beat--notice { color: var(--paper-300); }
.dream-page__beat--notice::before { content: "◇ "; color: var(--warn); }
.dream-strip { display: flex; align-items: center; gap: var(--sp-3); height: var(--band-strip-h); max-width: 42em; color: var(--paper-500); font-size: var(--text-xs); }
.dream-strip__keys { margin-left: auto; }
.dream-strip__marker { color: var(--gold-400); animation: dream-pulse var(--motion-marker-bob) ease-in-out infinite; }

/* ---- toast + live region ---- */
.dream-toast { position: absolute; z-index: 7; top: calc(24px * var(--ui-scale)); left: 50%; transform: translateX(-50%); padding: var(--sp-2) var(--sp-5);
  border: 1px solid var(--band-edge); border-radius: var(--radius-pill); background: var(--panel); color: var(--gold-300); font-size: var(--text-sm);
  animation: dream-rise var(--motion-reveal) var(--ease-standard) both; }
.dream-live { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }

/* ---- sheet + confirm ---- */
.dream-sheet__scrim { position: absolute; inset: 0; z-index: 8; background: rgba(11, 13, 16, 0.42); animation: dream-fade-in var(--motion-panel) var(--ease-standard) both; }
@keyframes dream-fade-in { from { opacity: 0; } }
@keyframes dream-slide { from { opacity: 0; transform: translateX(calc(-1 * var(--motion-panel-shift) * var(--motion-travel))); } }
.dream-sheet { position: absolute; z-index: 9; top: var(--sp-6); bottom: var(--sp-6); left: calc(32px * var(--ui-scale)); display: grid; grid-template-rows: auto 1fr auto;
  width: min(calc(720px * var(--ui-scale)), 56vw); border-radius: var(--radius-sm); animation: dream-slide var(--motion-panel) var(--ease-standard) both; }
.dream-sheet__head { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--sp-4); padding: var(--sp-6) var(--sp-6) var(--sp-4); border-bottom: 1px solid var(--band-edge-dim); }
.dream-sheet__head h3, .dream-confirm h3 { color: var(--gold-300); font-family: var(--f-display); font-size: var(--text-xl); font-weight: 500; letter-spacing: 0.1em; }
.dream-sheet__head p { margin-top: var(--sp-1); color: var(--paper-400); font-size: var(--text-sm); }
.dream-sheet__body { display: grid; align-content: start; gap: var(--sp-4); min-height: 0; overflow-y: auto; padding: var(--sp-5) var(--sp-6); }
.dream-field { display: grid; gap: var(--sp-2); }
.dream-field__label, .dream-threads legend, .dream-tags h4 { color: var(--gold-400); font-size: var(--text-sm); font-weight: 500; letter-spacing: 0.06em; }
.dream-field__label em { margin-left: var(--sp-2); color: var(--paper-500); font-size: var(--text-xs); font-style: normal; }
.dream-sheet textarea, .dream-sheet input[type="search"], .dream-tags__box { box-sizing: border-box; width: 100%; border: 1px solid var(--ink-600); border-radius: var(--radius-sm); background: var(--ink-900); color: var(--paper-50); }
.dream-sheet textarea { padding: var(--sp-3); font-family: var(--f-serif); font-size: var(--text-md); line-height: 1.6; resize: vertical; }
.dream-sheet textarea[aria-invalid="true"] { border-color: var(--seal-500); }
.dream-field__foot { display: flex; align-items: center; gap: var(--sp-3); margin-top: calc(-1 * var(--sp-2)); color: var(--paper-500); font-size: var(--text-xs); }
.dream-field__counter { margin-left: auto; font-variant-numeric: tabular-nums; }
.dream-field__counter--over { color: var(--seal-400); }
.dream-field__error { padding: var(--sp-2) var(--sp-3); border-left: 2px solid var(--seal-500); background: rgba(124, 32, 38, 0.25); color: var(--paper-100); font-size: var(--text-sm); }
.dream-link { padding: 0; border: 0; background: none; color: var(--gold-400); font: inherit; text-decoration: underline; cursor: pointer; }
.dream-threads { display: grid; gap: var(--sp-2); min-width: 0; margin: 0; padding: var(--sp-4) 0 0; border: 0; border-top: 1px solid var(--band-edge-dim); }
.dream-threads legend { float: left; width: 100%; margin-bottom: var(--sp-2); padding: 0; }
.dream-threads__filter { padding: var(--sp-2) var(--sp-3); font: inherit; font-size: var(--text-sm); }
.dream-threads__list { display: grid; gap: var(--sp-1); max-height: calc(5 * 46px * var(--ui-scale)); overflow-y: auto; }
.dream-threads__option { display: flex; align-items: flex-start; gap: var(--sp-3); padding: var(--sp-2) var(--sp-3); border-radius: var(--radius-sm); color: var(--paper-200); font-size: var(--text-sm); line-height: 1.5; cursor: pointer; }
.dream-threads__option:has(input:checked) { background: var(--panel-hi); box-shadow: inset 2px 0 var(--gold-400); color: var(--paper-50); }
.dream-threads__option input { flex: none; margin-top: 0.3em; accent-color: var(--gold-400); }
.dream-threads__option span { display: -webkit-box; overflow: hidden; -webkit-box-orient: vertical; -webkit-line-clamp: 2; line-clamp: 2; overflow-wrap: anywhere; }
.dream-threads__empty { color: var(--paper-500); font-size: var(--text-sm); }
.dream-tags { display: grid; gap: var(--sp-3); padding-top: var(--sp-4); border-top: 1px solid var(--band-edge-dim); }
.dream-tags__row { display: grid; grid-template-columns: calc(150px * var(--ui-scale)) 1fr; align-items: center; gap: var(--sp-1) var(--sp-3); }
.dream-tags__label { color: var(--paper-200); font-size: var(--text-sm); }
.dream-tags__hint { grid-column: 2; color: var(--paper-500); font-size: var(--text-xs); }
.dream-tags__box { display: flex; flex-wrap: wrap; align-items: center; gap: var(--sp-1); min-height: calc(40px * var(--ui-scale)); padding: var(--sp-1) var(--sp-2); }
.dream-tags__box:focus-within { box-shadow: var(--focus); }
.dream-tags__box input { flex: 1; min-width: calc(120px * var(--ui-scale)); border: 0; background: transparent; color: var(--paper-50); font: inherit; font-size: var(--text-sm); }
.dream-tags__box input:focus { outline: none; box-shadow: none; }
.dream-tags__chip { display: inline-flex; align-items: center; gap: var(--sp-1); padding: 0 var(--sp-1) 0 var(--sp-3); border: 1px solid var(--ink-600); border-radius: var(--radius-pill); background: var(--ink-780); color: var(--paper-100); font-size: var(--text-sm); }
.dream-tags__row--exclude .dream-tags__chip { border-color: var(--seal-700); color: var(--seal-400); }
.dream-tags__chip button { padding: 0 var(--sp-1); border: 0; background: none; color: inherit; font: inherit; cursor: pointer; }
.dream-sheet__foot { display: grid; gap: var(--sp-2); padding: var(--sp-4) var(--sp-6) var(--sp-5); border-top: 1px solid var(--band-edge-dim); }
.dream-sheet__foot p { color: var(--paper-500); font-size: var(--text-xs); }
.dream-sheet__foot div { display: flex; justify-content: flex-end; gap: var(--sp-2); }
.dream-confirm { position: absolute; z-index: 9; top: 40%; left: 30%; transform: translate(-50%, -50%); display: grid; gap: var(--sp-4);
  width: min(calc(440px * var(--ui-scale)), 40vw); padding: var(--sp-6); border-radius: var(--radius-sm); animation: dream-fade-in var(--motion-fast) var(--ease-standard) both; }
.dream-confirm #dream-confirm-body { display: grid; gap: var(--sp-1); color: var(--paper-200); font-size: var(--text-sm); line-height: 1.6; }
.dream-confirm__actions { display: flex; justify-content: flex-end; gap: var(--sp-2); }

@media (max-height: 800px) {
  .dream-keepsake { top: calc(72px * var(--ui-scale)); gap: var(--sp-2); padding: var(--sp-4); max-height: calc(100% - var(--band-h) - 150px * var(--ui-scale)); }
  .dream-keepsake__preview { -webkit-line-clamp: 1; line-clamp: 1; font-size: var(--text-sm); }
  .dream-choice { padding-top: var(--sp-2); gap: 0; }
  .dream-choice__row { min-height: calc(34px * var(--ui-scale)); padding-block: var(--sp-1); }
  .dream-crest { top: var(--sp-3); }
}
</style>
