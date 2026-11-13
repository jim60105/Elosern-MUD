<script setup>
// GalleryImagePage (change gallery-image-page; gallery window design D5,
// after the prototype page in docs/design/gallery-window/). The gallery
// window's right page: one selected image of the selected subject. Portrait
// layout — the art fills the page height at 9:16 and the facts sit beside it
// — with the ribbon, the subject name, an optional 描述 letter, the fact
// cells of the quest detail's condition row, and a pinned DetailFooter.
// A scene subject (change gallery-landscape-page) takes the landscape layout
// — the 16:9 art above, the name and description left, the facts right — and
// says whether its image is the stored card (生成圖) or, with no card, the
// subject's committed tile artwork (官方內建圖).
//
// The footer's buttons are `galleryFooter` of the selection and the subject's
// committed capabilities, never a comparison of subject kinds. The page emits
// `press(key)` and never dispatches; the window maps keys to actions.
//
// 刪除 takes two steps: the first press arms a confirmation (focus moves to
// 取消), only 確認刪除 emits `press("delete")`, and 取消, Escape inside the
// page or a different selection disarm without emitting. The host sets
// `disabled` while an action is in flight: every button then emits nothing,
// which is also what stops a second delete before the commit removes the
// card. When the commit removes the focused card, the host moves focus.
import { computed, nextTick, ref, watch } from "vue";

import ArtworkPreview from "./ArtworkPreview.vue";
import DetailFooter from "./DetailFooter.vue";
import { GALLERY_OFFICIAL_LABEL, galleryDate } from "./gallery-copy.js";
import { bundledArtwork, galleryFooter, galleryRibbon, pageShape } from "./gallery-window-model.js";

const props = defineProps({
  // The committed v4 panel.
  panel: { type: Object, required: true },
  // The committed subject row of `selected`.
  subject: { type: Object, default: null },
  groupLabel: { type: String, default: null },
  categoryLabel: { type: String, required: true },
  // { type: "card", row } | { type: "official", row } | { type: "empty" }
  selection: { type: Object, default: null },
  now: { type: Number, required: true },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(["press"]);

const DELETE_WARNING = "刪除後無法復原。";
const STATUS_LINE = { pending: "生成中", failed: "生成失敗" };
// The landscape (scene) vocabulary (change gallery-landscape-page): the page
// says whether the image in effect is the stored card or the bundled one.
const GENERATED_LABEL = "生成圖";
const BUNDLED_LABEL = "官方內建圖";
const GENERATED_NOTE = "只保留一張；刪除後回到官方內建圖。";
const BUNDLED_NOTE = "尚未生成專屬圖片。";

const capabilities = computed(() => props.panel?.capabilities ?? null);
const type = computed(() => (props.selection?.type === "card" || props.selection?.type === "official" ? props.selection.type : "empty"));
const row = computed(() => (type.value === "empty" ? null : props.selection.row));
const status = computed(() => (type.value === "card" ? row.value.status : null));

// Layout and labelling vocabulary follow the subject's kind; the buttons stay
// capability-driven (galleryFooter).
const shape = computed(() => pageShape(props.subject?.kind));
const landscape = computed(() => shape.value === "landscape");
const generated = computed(() => landscape.value && status.value === "card");
const bundled = computed(() => (type.value === "empty" ? bundledArtwork(props.subject) : null));

// The selection's identity: re-committing the same image keeps an armed
// confirmation; any other image disarms it. An empty selection is keyed by
// its subject, so another subject's bundled image mounts afresh.
const selectionKey = computed(() => {
  if (type.value === "card") return `card:${row.value.image_id}`;
  if (type.value === "official") return `official:${row.value.identity}`;
  return `empty:${props.subject?.subject_key ?? ""}`;
});

// ---- facts ----------------------------------------------------------------

const ribbon = computed(() => galleryRibbon(props.categoryLabel, props.groupLabel));
const name = computed(() => props.subject?.display_name ?? null);

const imageLabel = computed(() => {
  if (type.value === "official") return GALLERY_OFFICIAL_LABEL;
  if (generated.value) return GENERATED_LABEL;
  if (type.value === "card") return row.value.label;
  return bundled.value ? BUNDLED_LABEL : "尚無圖片";
});

const imageNote = computed(() => {
  if (type.value === "official") {
    // Only a subject whose personal official preferences are declared can
    // adjust anything; the others keep official images strictly read-only.
    return capabilities.value?.supports_personal_official_preferences ? "唯讀，只能調整個人的臉框與舞台位置。" : "唯讀。";
  }
  if (generated.value) return GENERATED_NOTE;
  if (type.value === "card" && capabilities.value?.max_cards === 1) return "只保留一張，重新生成會替換原圖。";
  if (bundled.value) return BUNDLED_NOTE;
  return null;
});

const date = computed(() => (
  status.value === "card" || status.value === "failed" ? galleryDate(row.value.created_at, props.now) : null
));

const stateCell = computed(() => {
  if (type.value !== "card" || capabilities.value?.max_cards !== null) return null;
  if (STATUS_LINE[status.value]) return { line: STATUS_LINE[status.value], crown: false, note: null };
  if (row.value.is_default) return { line: "目前預設", crown: true, note: "沒有符合的綁定條件時顯示這張。" };
  return { line: "備用圖片", crown: false, note: null };
});

const chips = computed(() => (type.value === "card" ? row.value.chips ?? [] : []));

const conditions = computed(() => {
  if (type.value !== "card") return [];
  const warning = (props.panel?.binding_warnings ?? []).find((entry) => entry.image_id === row.value.image_id);
  return warning?.conditions ?? [];
});

const description = computed(() => props.panel?.description ?? null);

// ---- art ------------------------------------------------------------------

const art = computed(() => {
  if (type.value === "official") return { kind: "image", artwork: row.value.artwork, id: row.value.identity };
  if (status.value === "card") return { kind: "image", artwork: row.value.artwork, id: row.value.image_id };
  if (bundled.value) return { kind: "image", artwork: bundled.value, id: props.subject.subject_key };
  return { kind: status.value ?? "empty" };
});
// A card keeps its committed row label as the image's accessible name, even
// where the 圖片 cell reads 生成圖.
const altLabel = computed(() => (type.value === "card" ? row.value.label : imageLabel.value));
const artAlt = computed(() => (name.value ? `${name.value}・${altLabel.value}` : altLabel.value));

// ---- footer and the two-step deletion -------------------------------------

const root = ref(null);
const footerRef = ref(null);
const armedKey = ref(null);
const base = computed(() => galleryFooter(props.selection, capabilities.value));
const armed = computed(() => (
  !props.disabled
  && armedKey.value === selectionKey.value
  && base.value.buttons.some((button) => button.key === "delete")
));

// Another image disarms. Runs before the patch, while the focused footer
// button still stands: if focus was in the footer, it moves to the new
// footer's first button instead of falling to the document.
watch(selectionKey, (next, previous) => {
  armedKey.value = null;
  // One empty page to another keeps the same footer, so focus stays.
  if (next.startsWith("empty:") && previous.startsWith("empty:")) return;
  if (root.value?.querySelector("footer")?.contains(document.activeElement)) {
    nextTick(() => root.value?.querySelector("footer button")?.focus());
  }
});

// A busy host disarms, so the page never comes back already armed.
watch(() => props.disabled, (busy) => {
  if (busy) armedKey.value = null;
});

const footer = computed(() => {
  if (armed.value) {
    return {
      reason: DELETE_WARNING,
      reasonTone: "danger",
      reasonRole: "alert",
      reasonTestid: "gallery-page__delete-warning",
      buttons: [
        { key: "confirm-delete", label: "確認刪除", tone: "danger", testid: "gallery-page__confirm-delete" },
        { key: "cancel", label: "取消", tone: "plain", testid: "gallery-page__cancel" },
      ],
    };
  }
  const buttons = props.disabled
    ? base.value.buttons.map((button) => ({ ...button, enabled: false }))
    : base.value.buttons;
  return { reason: base.value.note, reasonTone: "plain", reasonRole: null, reasonTestid: "gallery-page__note", buttons };
});

async function focusButton(key) {
  await nextTick();
  footerRef.value?.focus(key);
}

function disarm() {
  armedKey.value = null;
  focusButton("delete");
}

function onPress(key) {
  if (key === "delete") {
    armedKey.value = selectionKey.value;
    focusButton("cancel");
  } else if (key === "cancel") {
    disarm();
  } else if (key === "confirm-delete") {
    // The delete button stands again until the commit removes the card.
    disarm();
    emit("press", "delete");
  } else {
    emit("press", key);
  }
}

function onKeydown(event) {
  if (event.key !== "Escape" || !armed.value) return;
  event.preventDefault();
  event.stopPropagation();
  disarm();
}
</script>

<template>
  <article
    ref="root"
    class="gpage"
    :class="`gpage--${shape}`"
    data-testid="gallery-page"
    :data-selection="type"
    :data-shape="shape"
    @keydown="onKeydown"
  >
    <div :key="selectionKey" class="gpage__body">
      <figure
        class="gpage__art"
        :class="[`gpage__art--${art.kind}`, { 'gpage__art--official': type === 'official' || bundled !== null }]"
        data-testid="gallery-page__art"
      >
        <ArtworkPreview
          v-if="art.kind === 'image'"
          class="gpage__figure"
          :artwork="art.artwork"
          :panel="panel"
          :view-subject-id="art.id"
          :alt="artAlt"
        />
        <figcaption v-else class="gpage__placeholder" :data-status="art.kind">
          <svg v-if="art.kind === 'pending'" class="gpage__spin" data-mark="spinner" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <circle cx="12" cy="12" r="8.5" stroke="currentColor" stroke-opacity="0.25" stroke-width="1.4" />
            <path d="M12 3.5a8.5 8.5 0 0 1 8.5 8.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
          </svg>
          <svg v-else-if="art.kind === 'failed'" data-mark="warning" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M12 3.8 21.2 19.6H2.8z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" />
            <path d="M12 9.6v4.8M12 16.8v.4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
          </svg>
          <svg v-else data-mark="blank" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M12 3.5c2.5 0 4 1.9 4 4.3S14.5 12.5 12 12.5 8 10.2 8 7.8 9.5 3.5 12 3.5zM4.5 20.5c.8-4 3.8-6.2 7.5-6.2s6.7 2.2 7.5 6.2" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" />
          </svg>
          <span>{{ art.kind === "empty" ? "尚無圖片" : STATUS_LINE[art.kind] }}</span>
        </figcaption>
        <span v-if="type === 'card' && row.is_default && !landscape" class="gpage__badge gpage__badge--crown" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="currentColor"><path d="M3 8l4.5 4L12 5l4.5 7L21 8l-2 11H5z" /></svg>預設
        </span>
        <span v-if="type === 'official'" class="gpage__badge gpage__badge--lock" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none"><path d="M7 11V8a5 5 0 0 1 10 0v3M5.5 11h13v9.5h-13z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" /></svg>唯讀
        </span>
      </figure>

      <div class="gpage__facts" data-testid="gallery-page__facts">
        <header class="gpage__head">
          <span class="gpage__ribbon" data-testid="gallery-page__ribbon">{{ ribbon }}</span>
          <h3 v-if="name" class="gpage__title" data-testid="gallery-page__title">{{ name }}</h3>
        </header>

        <section v-if="description !== null" class="gpage__letter" data-testid="gallery-page__letter">
          <h4 class="gpage__label">描述</h4>
          <p class="gpage__prose">{{ description }}</p>
        </section>

        <div class="gpage__cond">
          <section class="gpage__cell" data-testid="gallery-page__cell" data-cell="image">
            <h4 class="gpage__label">圖片</h4>
            <p class="gpage__line">{{ imageLabel }}</p>
            <p v-if="imageNote" class="gpage__text">{{ imageNote }}</p>
          </section>
          <section v-if="date" class="gpage__cell" data-testid="gallery-page__cell" data-cell="time">
            <h4 class="gpage__label">生成時間</h4>
            <p class="gpage__line">{{ date.relative }}</p>
            <p v-if="date.exact" class="gpage__text"><time :datetime="date.iso">{{ date.exact }}</time></p>
          </section>
          <section v-if="stateCell" class="gpage__cell" data-testid="gallery-page__cell" data-cell="status">
            <h4 class="gpage__label">狀態</h4>
            <p class="gpage__line" :data-status="status">
              <svg v-if="stateCell.crown" data-mark="crown" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3 8l4.5 4L12 5l4.5 7L21 8l-2 11H5z" /></svg>
              {{ stateCell.line }}
            </p>
            <p v-if="stateCell.note" class="gpage__text">{{ stateCell.note }}</p>
          </section>
          <section v-if="chips.length" class="gpage__cell" data-testid="gallery-page__cell" data-cell="chips">
            <h4 class="gpage__label">標記</h4>
            <ul class="gpage__chips">
              <li v-for="chip in chips" :key="chip">{{ chip }}</li>
            </ul>
          </section>
          <section v-if="conditions.length" class="gpage__cell gpage__cell--wide" data-testid="gallery-page__cell" data-cell="conditions">
            <h4 class="gpage__label">綁定條件</h4>
            <ul class="gpage__chips gpage__chips--wide">
              <li v-for="line in conditions" :key="line">{{ line }}</li>
            </ul>
          </section>
        </div>
      </div>
    </div>

    <DetailFooter ref="footerRef" testid="gallery-page__footer" v-bind="footer" @press="onPress" />
  </article>
</template>

<style scoped>
/* After the prototype's `.gpage` rules and the quest detail's condition row
   (QuestDetail `.quest-detail__cond`). */
.gpage {
  --gpage-line: rgba(185, 154, 96, 0.28);
  --gpage-hair: calc(1px * var(--ui-scale));
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  min-width: 0;
  min-height: 0;
  height: 100%;
  box-sizing: border-box;
  color: var(--paper-200);
  font-family: var(--f-sans);
  background:
    radial-gradient(90% 60% at 100% 0%, rgba(169, 50, 42, 0.08), transparent 70%),
    radial-gradient(70% 50% at 0% 100%, rgba(185, 154, 96, 0.05), transparent 70%),
    var(--ink-900);
}

/* Portrait: the art column is as tall as the page body at 9:16, capped so the
   facts column always keeps a readable width. The body is a size container
   so the art can size from its height without a layout cycle. The entry
   uses --motion-base, which reduced and off motion set to zero. */
.gpage__body {
  container-type: size;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
  gap: var(--sp-6);
  min-height: 0;
  box-sizing: border-box;
  padding: var(--sp-5) var(--sp-4) var(--sp-5) var(--sp-6);
  animation: gpage-in var(--motion-base) var(--ease-enter);
}

@keyframes gpage-in {
  from {
    opacity: 0;
    transform: translateX(calc(calc(6px * var(--ui-scale)) * var(--motion-travel)));
  }
}

.gpage__art {
  position: relative;
  display: grid;
  align-self: start;
  width: min(calc(100cqh * 9 / 16), 52cqw);
  aspect-ratio: 9 / 16;
  margin: 0;
  overflow: hidden;
  background: radial-gradient(circle at 50% 30%, #2f2a20, #0f0e0c 75%);
  border: var(--gpage-hair) solid var(--gold-600);
  border-radius: var(--radius-sm);
  box-shadow:
    inset 0 0 0 var(--gpage-hair) rgba(0, 0, 0, 0.55),
    0 calc(10px * var(--ui-scale)) calc(30px * var(--ui-scale)) rgba(0, 0, 0, 0.55);
}

/* A soft vignette seats the figure in the frame. */
.gpage__art::after {
  content: "";
  position: absolute;
  inset: 0;
  background:
    linear-gradient(180deg, transparent 70%, rgba(8, 9, 11, 0.45)),
    radial-gradient(120% 90% at 50% 40%, transparent 65%, rgba(8, 9, 11, 0.35));
  pointer-events: none;
}

/* Official images are read-only: the double border of their tray tiles. */
.gpage__art--official {
  border: calc(3px * var(--ui-scale)) double var(--gold-500);
}

.gpage__art--pending,
.gpage__art--empty {
  background:
    repeating-linear-gradient(135deg, rgba(185, 154, 96, 0.05) 0 calc(6px * var(--ui-scale)), transparent calc(6px * var(--ui-scale)) calc(12px * var(--ui-scale))),
    radial-gradient(circle at 50% 40%, #2c271d, #14120e 74%);
  border-style: dashed;
  box-shadow: none;
}

.gpage__art--failed {
  background: radial-gradient(circle at 50% 40%, #3a1f20, #15100f 74%);
  border-color: var(--seal-600);
  box-shadow: none;
}

.gpage__figure {
  grid-area: 1 / 1;
}

.gpage__placeholder {
  grid-area: 1 / 1;
  place-self: center;
  display: grid;
  justify-items: center;
  gap: var(--sp-3);
  padding: 0 var(--sp-3);
  color: var(--paper-400);
  font: var(--text-sm) / 1.4 var(--f-serif);
  letter-spacing: 0.08em;
  text-align: center;
}

.gpage__placeholder svg {
  width: calc(48px * var(--ui-scale));
  height: calc(48px * var(--ui-scale));
  color: var(--paper-700);
}

.gpage__placeholder[data-status="pending"] svg {
  color: var(--gold-400);
}

.gpage__placeholder[data-status="failed"],
.gpage__placeholder[data-status="failed"] svg {
  color: var(--seal-400);
}

.gpage__spin {
  animation: gpage-spin var(--motion-spin) linear infinite;
}

@keyframes gpage-spin {
  to {
    transform: rotate(360deg);
  }
}

.gpage__badge {
  position: absolute;
  top: var(--sp-2);
  left: var(--sp-2);
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);
  padding: calc(2px * var(--ui-scale)) var(--sp-2);
  font: var(--text-xs) / 1.4 var(--f-display);
  letter-spacing: 0.08em;
  background: rgba(8, 9, 11, 0.85);
  border-radius: var(--radius-sm);
  pointer-events: none;
}

.gpage__badge svg {
  width: calc(14px * var(--ui-scale));
  height: calc(14px * var(--ui-scale));
}

.gpage__badge--crown {
  color: var(--gold-300);
  border: var(--gpage-hair) solid var(--gold-500);
}

.gpage__badge--lock {
  color: var(--paper-300);
  border: var(--gpage-hair) solid var(--ink-600);
}

/* The facts scroll beside the art; the gutter is always reserved. */
.gpage__facts {
  display: flex;
  flex-direction: column;
  gap: var(--sp-5);
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  padding-right: var(--sp-2);
  scrollbar-width: thin;
  scrollbar-color: var(--ink-600) transparent;
  scrollbar-gutter: stable;
}

.gpage__facts > * {
  flex-shrink: 0;
}

.gpage__head {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding-bottom: var(--sp-4);
  border-bottom: var(--gpage-hair) solid var(--gpage-line);
}

.gpage__ribbon {
  align-self: flex-start;
  padding: calc(3px * var(--ui-scale)) calc(22px * var(--ui-scale)) calc(3px * var(--ui-scale)) var(--sp-3);
  color: var(--paper-50);
  font: var(--text-xs) / 1.4 var(--f-display);
  letter-spacing: 0.12em;
  background: linear-gradient(180deg, var(--seal-600), var(--seal-700));
  clip-path: polygon(0 0, 100% 0, calc(100% - calc(10px * var(--ui-scale))) 50%, 100% 100%, 0 100%);
  box-shadow: inset 0 var(--gpage-hair) 0 rgba(255, 255, 255, 0.12);
}

.gpage__title {
  margin: 0;
  overflow-wrap: anywhere;
  color: var(--paper-50);
  font: var(--text-3xl) / 1.25 var(--f-display);
  letter-spacing: 0.04em;
  text-shadow: 0 calc(2px * var(--ui-scale)) calc(12px * var(--ui-scale)) rgba(0, 0, 0, 0.6);
}

/* Prose only: the codex's and the quest client's letter box. */
.gpage__letter {
  padding: var(--sp-4) var(--sp-5) var(--sp-5);
  background: linear-gradient(135deg, rgba(185, 154, 96, 0.09), rgba(185, 154, 96, 0.02) 60%);
  border: var(--gpage-hair) solid var(--gpage-line);
  border-left: calc(3px * var(--ui-scale)) solid var(--gold-500);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.gpage__prose {
  margin: 0;
  color: var(--paper-200);
  font: var(--text-sm) / 1.9 var(--f-serif);
}

/* Facts: unboxed cells under a ruled label, two to a row. */
.gpage__cond {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--sp-5) var(--sp-6);
}

.gpage__cell {
  min-width: 0;
}

.gpage__cell--wide {
  grid-column: 1 / -1;
}

.gpage__label {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin: 0 0 var(--sp-2);
  color: var(--gold-500);
  font: var(--text-xs) / 1.4 var(--f-display);
  letter-spacing: 0.18em;
}

.gpage__label::after {
  content: "";
  flex: 1;
  height: var(--gpage-hair);
  background: linear-gradient(90deg, var(--gpage-line), transparent);
}

.gpage__line {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin: 0 0 var(--sp-1);
  overflow-wrap: anywhere;
  color: var(--paper-50);
  font: var(--text-md) / 1.5 var(--f-serif);
}

.gpage__line svg {
  flex: none;
  width: 1.1em;
  height: 1.1em;
  color: var(--gold-400);
}

/* The exact instant breaks between its date and its time, never inside a
   word. */
.gpage__text time {
  word-break: keep-all;
}

.gpage__line[data-status="failed"] {
  color: var(--seal-400);
}

.gpage__text {
  margin: 0;
  color: var(--paper-400);
  font-size: var(--text-sm);
  line-height: 1.7;
}

/* Short enumerations: the quest reward cells. */
.gpage__chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.gpage__chips li {
  padding: var(--sp-1) var(--sp-3);
  color: var(--paper-200);
  font-size: var(--text-sm);
  background: rgba(0, 0, 0, 0.3);
  border: var(--gpage-hair) solid var(--ink-700);
  border-radius: var(--radius-sm);
}

.gpage__chips--wide li {
  padding: var(--sp-2) var(--sp-4);
  color: var(--paper-100);
  border-left: calc(2px * var(--ui-scale)) solid var(--gold-600);
}

/* ---- landscape (scenes; change gallery-landscape-page) ---------------------
   The 16:9 art sits above; under it the name and the description take the
   left column ("head", "letter") and the fact cells the right one ("facts").
   The art is capped by the body height so the whole page reads without
   scrolling at the reference viewport; the facts keep their scroller and
   reserved gutter only as a fallback. */
.gpage--landscape .gpage__body {
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: auto minmax(0, 1fr);
  gap: var(--sp-5);
  padding: var(--sp-5) var(--sp-5) var(--sp-4) var(--sp-6);
}

.gpage--landscape .gpage__art {
  justify-self: center;
  width: min(100cqw, calc(48cqh * 16 / 9));
  aspect-ratio: 16 / 9;
}

.gpage--landscape .gpage__facts {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(0, 1fr);
  grid-template-rows: auto 1fr;
  grid-template-areas:
    "head facts"
    "letter facts";
  align-content: start;
  gap: var(--sp-3) var(--sp-6);
}

.gpage--landscape .gpage__head {
  grid-area: head;
  gap: var(--sp-1);
  padding-bottom: var(--sp-3);
}

.gpage--landscape .gpage__title {
  font-size: var(--text-2xl);
}

.gpage--landscape .gpage__letter {
  grid-area: letter;
  align-self: start;
  padding: var(--sp-3) var(--sp-4) var(--sp-4);
}

.gpage--landscape .gpage__prose {
  line-height: 1.8;
}

.gpage--landscape .gpage__cond {
  grid-area: facts;
  grid-template-columns: minmax(0, 1fr);
  align-content: start;
  gap: var(--sp-4);
  padding-left: var(--sp-5);
  border-left: var(--gpage-hair) solid var(--gpage-line);
}

/* The narrow facts column breaks a note at its punctuation, never inside a
   word such as 官方內建圖, unless a phrase cannot fit at all. */
.gpage--landscape .gpage__cond .gpage__text {
  word-break: keep-all;
  overflow-wrap: anywhere;
}
</style>
