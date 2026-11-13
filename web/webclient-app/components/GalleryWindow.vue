<script setup>
// GalleryWindow (change gallery-window-component; gallery window design D8,
// D9). The gallery as its own book-style window on the shared drawer chrome
// (seal `gallery`, title 圖庫, close, focus trap, Escape, motion): a labelled
// vertical category rail, the subject wall with its inline tray, and the
// selected image's page. The four existing editors open from the page footer
// (and the tray's 生成新圖 tile), teleported to the body as before.
//
// Every mutation leaves through the one `dispatch` entry and respects the
// connected, locked and one-in-flight gates. The window renders committed
// facts only: a pressed rail tab is marked while its `gallery.category.select`
// is in flight, but the wall keeps the committed groups until the next panel.
// Image selection is client-local and follows the committed subject.
//
// Focus: a commit that removes the focused wall tile returns focus to the
// rail's selected tab; Escape in the tray returns to the owner tile (the wall
// stops it there) and a further Escape closes the window, restoring its
// opener (HudDrawer).
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";

import EmptyState from "./EmptyState.vue";
import GalleryBindingDrawer from "./GalleryBindingDrawer.vue";
import GalleryFaceRectModal from "./GalleryFaceRectModal.vue";
import GalleryGenerateDrawer from "./GalleryGenerateDrawer.vue";
import GalleryImagePage from "./GalleryImagePage.vue";
import GalleryStageTransformModal from "./GalleryStageTransformModal.vue";
import GalleryWall from "./GalleryWall.vue";
import HudDrawer from "./HudDrawer.vue";
import IconTabs from "./IconTabs.vue";
import { GALLERY_CATEGORY_GLYPHS, GALLERY_CATEGORY_LABELS, galleryOfficialEditorCard } from "./gallery-copy.js";
import { initialImage } from "./gallery-window-model.js";
import { artworkGeometry } from "../lib/artwork.js";

const props = defineProps({
  model: { type: Object, default: null }, // committed gallery panel
  disabled: { type: Boolean, default: false }, // connected/locked/in-flight gate
  dispatch: { type: Function, default: null }, // (actionId, payload) -> requestId | null
  result: { type: Object, default: null }, // store.view.lastActionResult
  revision: { type: Number, default: 0 },
});
const emit = defineEmits(["close", "character", "log"]);

const UNAVAILABLE = "圖庫目前無法使用。";
const wallId = `gallery-window-${useId()}-wall`;

const root = ref(null);
const rail = ref(null);
const wall = ref(null);

// ---- committed facts --------------------------------------------------------

const available = computed(() => props.model?.available === true);
const locked = computed(() => props.disabled || !available.value);
const categories = computed(() => (available.value ? props.model.categories || [] : []));
const groups = computed(() => (available.value ? props.model.groups || [] : []));
const cards = computed(() => (available.value ? props.model.cards || [] : []));
const officialEntries = computed(() => (available.value ? props.model.official_entries || [] : []));
const hasSubject = computed(() => available.value && props.model.selected != null);
const categoryLabel = computed(() => (available.value ? GALLERY_CATEGORY_LABELS[props.model.category] ?? props.model.category : ""));

const subjectRow = computed(() => {
  if (!hasSubject.value) return null;
  for (const group of groups.value) {
    const subject = group.subjects.find((row) => row.subject_key === props.model.selected);
    if (subject) return { subject, group };
  }
  return null;
});

// ---- the minute clock -------------------------------------------------------

// The relative dates tick only while the window is mounted (open).
const now = ref(Date.now());
let clock = null;
onMounted(() => {
  now.value = Date.now();
  clock = setInterval(() => { now.value = Date.now(); }, 60_000);
});

// ---- client-local image selection -------------------------------------------

const selectedImage = ref(null);
const selectedCard = computed(() => cards.value.find((row) => row.image_id === selectedImage.value) || null);
const selectedEntry = computed(() => officialEntries.value.find((row) => row.identity === selectedImage.value) || null);
const selection = computed(() => {
  if (selectedCard.value) return { type: "card", row: selectedCard.value };
  if (selectedEntry.value) return { type: "official", row: selectedEntry.value };
  return { type: "empty" };
});

// ---- the editor lifecycle (moved from GalleryPanel) -------------------------

const editor = ref(null);
const entryEditor = ref(null);
const pending = ref(null);
const rejected = ref(false);
let opener = null;

// A newly committed subject (or availability) closes every editor and opens
// on the subject's own image.
watch([() => props.model?.selected, available], () => {
  closeEditor();
  selectedImage.value = initialImage(cards.value, officialEntries.value);
}, { immediate: true });

// A selected image that a newer panel no longer lists is replaced by the same
// rule, and an editor drafted against that image closes without sending. The
// generate drawer belongs to the subject, not the image, so it stays. An
// empty page adopts the first image that appears.
watch([cards, officialEntries], () => {
  if (selectedImage.value !== null && !selectedCard.value && !selectedEntry.value) {
    if (entryEditor.value || (editor.value && editor.value !== "generate")) closeEditor();
    selectedImage.value = initialImage(cards.value, officialEntries.value);
  } else if (selectedImage.value === null) {
    selectedImage.value = initialImage(cards.value, officialEntries.value);
  }
});

// The pressed rail tab, marked until the next committed panel (or a rejected
// request); the wall keeps showing committed groups meanwhile.
const pendingCategory = ref(null);
watch(() => props.model, () => { pendingCategory.value = null; });

watch(() => [props.result, props.revision], () => {
  const request = pending.value;
  const result = props.result;
  if (!request || result?.requestId !== request.id) return;
  if (result.outcome !== "success") {
    pending.value = null;
    rejected.value = true;
    if (request.category) pendingCategory.value = null;
  } else if (result.presentationRevision != null && props.revision >= result.presentationRevision) {
    const name = request.editor;
    const current = request.official ? entryEditor.value : editor.value;
    pending.value = null;
    if (name && name === current) closeEditor();
  }
});

// The subject whose selection is in flight: the wall marks its tile busy.
const pendingSubject = computed(() => pending.value?.subject ?? null);

function openEditor(name) {
  if (locked.value || pending.value || !hasSubject.value || (name !== "generate" && selectedCard.value?.status !== "card")) return;
  opener = document.activeElement;
  rejected.value = false;
  entryEditor.value = null;
  editor.value = name;
}

function openOfficialEditor(name) {
  if (locked.value || pending.value || !selectedEntry.value) return;
  opener = document.activeElement;
  rejected.value = false;
  editor.value = null;
  entryEditor.value = name;
}

function closeEditor() {
  if (!editor.value && !entryEditor.value) return;
  editor.value = null;
  entryEditor.value = null;
  pending.value = null;
  rejected.value = false;
  const target = opener;
  void nextTick().then(() => {
    if (target?.isConnected) target.focus();
    else rail.value?.focusSelected();
  });
}

function sendOfficial(action, extra = {}, editorName = null) {
  if (locked.value || pending.value || !props.dispatch || !selectedEntry.value) return;
  const payload = { subject_key: props.model.selected, identity: selectedEntry.value.identity, ...extra };
  const id = props.dispatch(action, payload);
  if (id) {
    rejected.value = false;
    pending.value = { id, editor: editorName, official: true };
  }
}

function sameRect(left, right) {
  return !!left && !!right && ["x", "y", "w", "h"].every((field) => Math.abs(left[field] - right[field]) < 1e-9);
}

// An official row's committed rectangle lives in its descriptor's own exact
// candidate; the editor seeds from that and nothing else.
function officialRect(entry) {
  return artworkGeometry(entry?.artwork)?.face_rect ?? null;
}

function isIdentityStage(value) {
  return !!value && value.scale === 1 && value.x === 0 && value.y === 0;
}

// The committed official row carries the catalog's own rectangle and no stage,
// so the shared editors are seeded from those facts and can never show a stored
// personal override. An UNTOUCHED save must therefore not cross the wire: it
// would silently overwrite a stored override with the seed. Only a real edit
// dispatches, and only for the component the player edited; 清除個人調整 is the
// truthful way to drop an override the editors cannot display.
function submitOfficialGeometry(component, value) {
  const entry = selectedEntry.value;
  if (!entry) {
    closeEditor();
    return;
  }
  const untouched = component === "face_rect" ? sameRect(value, officialRect(entry)) : isIdentityStage(value);
  if (untouched) {
    closeEditor();
    return;
  }
  sendOfficial("gallery.official.geometry.set", { [component]: value }, component === "face_rect" ? "face" : "stage");
}

// Category and subject selection carry exactly their committed key; every
// other action names the committed selected subject (and, for a card action,
// the selected card). Returns the request id, or null when nothing was sent.
const SELECTION_ACTIONS = ["gallery.category.select", "gallery.subject.select"];
function send(action, extra = {}) {
  if (locked.value || pending.value || !props.dispatch) return null;
  const isSelection = SELECTION_ACTIONS.includes(action);
  if (!isSelection && !hasSubject.value) return null;
  const isCard = !isSelection && action !== "gallery.generate";
  if (isCard && selectedCard.value?.status !== "card") return null;
  const payload = isSelection ? { ...extra } : { subject_key: props.model.selected, ...extra };
  if (isCard) payload.image_id = selectedCard.value.image_id;
  const id = props.dispatch(action, payload);
  if (!id) return null;
  rejected.value = false;
  pending.value = {
    id,
    editor: editor.value,
    category: action === "gallery.category.select" ? extra.category : null,
    subject: action === "gallery.subject.select" ? extra.subject_key : null,
  };
  return id;
}

// ---- the rail -----------------------------------------------------------------

const tabs = computed(() => categories.value.map((category) => ({
  key: category.key,
  label: GALLERY_CATEGORY_LABELS[category.key] ?? category.key,
  glyph: GALLERY_CATEGORY_GLYPHS[category.key] ?? "gallery",
  count: category.count,
  disabled: !category.enabled,
  reason: category.enabled ? null : category.reason,
  controls: wallId,
})));
const railValue = computed(() => pendingCategory.value ?? props.model?.category ?? null);

// A disabled category stays focusable so its committed reason is announced,
// but it never dispatches; neither does the category already shown.
function selectCategory(key) {
  const category = categories.value.find((row) => row.key === key);
  if (!category || !category.enabled || key === props.model.category) return;
  if (send("gallery.category.select", { category: key })) pendingCategory.value = key;
}

// ---- the wall -------------------------------------------------------------------

function selectSubject(key) {
  if (key === props.model.selected) return;
  send("gallery.subject.select", { subject_key: key });
}

function selectImage(id) {
  if (id === selectedImage.value) return;
  closeEditor();
  selectedImage.value = id;
}

// ---- the page footer ------------------------------------------------------------

const PRESSES = {
  delete: () => send("gallery.card.delete"),
  default: () => send("gallery.default.set"),
  face: () => openEditor("face"),
  stage: () => openEditor("stage"),
  binding: () => openEditor("binding"),
  generate: () => openEditor("generate"),
  regenerate: () => openEditor("generate"),
  "official-select": () => sendOfficial("gallery.official.select"),
  "official-clear-selection": () => sendOfficial("gallery.official.clear_selection"),
  "official-geometry-clear": () => sendOfficial("gallery.official.geometry.clear"),
  "official-face": () => openOfficialEditor("face"),
  "official-stage": () => openOfficialEditor("stage"),
};

function onPress(key) {
  PRESSES[key]?.();
}

// ---- focus across commits ---------------------------------------------------------

function rescueToRail() {
  rail.value?.focusSelected();
}

// The wall reports a removed focused tile; the rail's selected tab takes it.
function onFocusLost() {
  rescueToRail();
}

// The wall and the page move focus themselves when they can (the wall's
// focus keeper, the page's footer). A commit can still drop focus to the
// document — a confirmed delete whose replacement selection offers no footer
// button, or the wall remounting on a new category. Focus that was inside the
// window before the commit is then put back: on the owner tile when the focus
// was on the page, else on the rail's selected tab. The check waits one task,
// after the components' own microtask focus moves, and stands down while an
// editor holds focus outside the window.
let focusWasInside = false;
let focusTimer = null;
watch(() => props.model, () => {
  focusWasInside = !!root.value?.contains(document.activeElement);
  const fromPage = !!document.activeElement?.closest?.('[data-testid="gallery-page"]');
  if (!focusWasInside) return;
  clearTimeout(focusTimer);
  focusTimer = setTimeout(() => {
    focusTimer = null;
    if (editor.value || entryEditor.value) return;
    const active = document.activeElement;
    if (active && active !== document.body) return;
    if (fromPage && subjectRow.value && wall.value) wall.value.focusOwner();
    else rescueToRail();
  }, 0);
}, { flush: "pre" });

onBeforeUnmount(() => {
  clearInterval(clock);
  clearTimeout(focusTimer);
});
</script>

<template>
  <HudDrawer :open="true" title="圖庫" icon="gallery" drawer-key="gallery" body-flush @close="emit('close')">
    <div v-if="!available" class="gwin gwin--unavailable" data-testid="gallery-window">
      <EmptyState class="gwin__state" glyph="gallery" :headline="model?.reason?.message || UNAVAILABLE" role="status" data-testid="gallery-window__unavailable" />
    </div>
    <section v-else ref="root" class="gwin" aria-label="圖庫" data-testid="gallery-window" :aria-busy="pending ? 'true' : undefined">
      <IconTabs
        ref="rail"
        class="gwin__rail"
        :class="{ 'gwin__rail--pending': pendingCategory !== null }"
        data-testid="gallery-window__rail"
        orientation="vertical"
        aria-label="圖庫分類"
        show-labels
        :tabs="tabs"
        :model-value="railValue"
        @update:model-value="selectCategory"
      />

      <div class="gwin__center">
        <GalleryWall
          :id="wallId"
          ref="wall"
          :key="model.category"
          class="gwin__wall"
          :groups="groups"
          :selected-subject="model.selected"
          :cards="cards"
          :official-entries="officialEntries"
          :capabilities="model.capabilities ?? null"
          :selected-image="selectedImage"
          :panel="model"
          :aria-label="categoryLabel"
          :pending-subject="pendingSubject"
          @select-subject="selectSubject"
          @select-image="selectImage"
          @generate="openEditor('generate')"
          @focus-lost="onFocusLost"
        />
        <p v-if="rejected && !editor && !entryEditor" class="gwin__feedback" role="status" data-testid="gallery-window__feedback">
          <svg class="gwin__feedback-mark" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M12 3.8 21.2 19.6H2.8z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
            <path d="M12 9.6v4.8M12 16.8v.4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
          </svg>
          <span class="gwin__feedback-text">操作未完成。</span>
          <button type="button" class="gwin__feedback-link" @click="emit('log')">查看伺服器訊息</button>
        </p>
      </div>

      <GalleryImagePage
        v-if="subjectRow"
        class="gwin__page"
        :panel="model"
        :subject="subjectRow.subject"
        :group-label="subjectRow.group.label ?? null"
        :category-label="categoryLabel"
        :selection="selection"
        :now="now"
        :disabled="locked || !!pending"
        @press="onPress"
      />
      <div v-else class="gwin__page gwin__page--empty" data-testid="gallery-window__empty-page">
        <EmptyState glyph="gallery" headline="尚無記錄" guidance="旅途中遇見的對象會出現在這裡" />
      </div>
    </section>

    <Teleport to="body">
      <template v-if="available">
        <GalleryGenerateDrawer v-if="editor === 'generate'" :model="model" :preview="selectedCard" :disabled="locked" :rejected="rejected"
          @close="closeEditor" @submit="send('gallery.generate', $event)" @character="emit('character')" @log="emit('log')" />
        <GalleryBindingDrawer v-if="editor === 'binding' && selectedCard" :model="model" :card="selectedCard" :disabled="locked" :rejected="rejected"
          @close="closeEditor" @submit="send('gallery.binding.save', $event)" @select-card="selectImage" @log="emit('log')" />
        <GalleryFaceRectModal v-if="editor === 'face' && selectedCard" :panel="model" :card="selectedCard" :disabled="locked" :rejected="rejected"
          @close="closeEditor" @submit="send('gallery.face_rect.update', $event)" @log="emit('log')" />
        <GalleryStageTransformModal v-if="editor === 'stage' && selectedCard?.status === 'card'" :panel="model" :card="selectedCard" :disabled="locked || !!pending" :rejected="rejected"
          @close="closeEditor" @submit="send('gallery.stage.update', $event)" @log="emit('log')" />
        <GalleryFaceRectModal v-if="entryEditor === 'face' && selectedEntry" :panel="model" :card="galleryOfficialEditorCard(selectedEntry)" :disabled="locked || !!pending" :rejected="rejected"
          @close="closeEditor" @submit="submitOfficialGeometry('face_rect', $event.face_rect)" @log="emit('log')" />
        <GalleryStageTransformModal v-if="entryEditor === 'stage' && selectedEntry" :panel="model" :card="galleryOfficialEditorCard(selectedEntry)" :disabled="locked || !!pending" :rejected="rejected"
          @close="closeEditor" @submit="submitOfficialGeometry('stage', $event.stage)" @log="emit('log')" />
      </template>
    </Teleport>
  </HudDrawer>
</template>

<style scoped>
/* The book body of the codex tab and the quest drawer: rail, wall, page. The
   rail is wider than the codex rail so 我的角色 reads in full under its
   emblem. */
.gwin {
  --gwin-line: rgba(185, 154, 96, 0.28);
  --gwin-hair: calc(1px * var(--ui-scale));
  display: grid;
  grid-template-columns: calc(132px * var(--ui-scale)) minmax(calc(360px * var(--ui-scale)), 0.82fr) minmax(0, 1.18fr);
  flex: 1;
  min-width: 0;
  min-height: 0;
  height: 100%;
  color: var(--paper-200);
  font-family: var(--f-sans);
  background:
    radial-gradient(120% 80% at 70% 0%, rgba(185, 154, 96, 0.07), transparent 60%),
    linear-gradient(180deg, #16181dfa, #0e1014fa);
}

.gwin--unavailable {
  grid-template-columns: 1fr;
  place-items: center;
  padding: var(--sp-8) var(--sp-5);
  box-sizing: border-box;
}

.gwin__state {
  width: min(100%, calc(440px * var(--ui-scale)));
  box-sizing: border-box;
}

/* The rail: five labelled categories, each tab tall enough for its emblem
   and label. The active tab opens into the wall's ink. No overflow clip, so
   the tooltip of a disabled tab opens over the wall. */
.gwin__rail {
  --icon-tabs-tab-h: calc(76px * var(--ui-scale));
  --icon-tabs-active-bg: var(--ink-860);
  --icon-tabs-line: var(--gwin-line);
  position: relative;
  z-index: 1;
  padding-top: var(--sp-5);
  background:
    linear-gradient(90deg, rgba(0, 0, 0, 0.34), rgba(0, 0, 0, 0.18));
}

.gwin__rail :deep(.icon-tabs__tab) {
  gap: var(--sp-1);
}

.gwin__rail :deep(.icon-tabs__label) {
  font-family: var(--f-display);
  font-size: var(--text-xs);
  letter-spacing: 0.14em;
}

.gwin__rail :deep(.icon-tabs__tab.is-active .icon-tabs__label) {
  color: var(--gold-300);
  text-shadow: 0 0 calc(8px * var(--ui-scale)) rgba(228, 200, 142, 0.35);
}

.gwin__rail :deep(.icon-tabs__tab.is-active .icon-tabs__icon svg) {
  filter: drop-shadow(0 0 calc(6px * var(--ui-scale)) rgba(228, 200, 142, 0.4));
}

.gwin__rail :deep(.icon-tabs__tab.is-disabled .icon-tabs__label) {
  opacity: 0.5;
}

/* A pressed category waiting for its commit: the seal marker breathes until
   the panel lands (static under reduced and off motion, where the loop
   tokens resolve to zero). */
.gwin__rail--pending :deep(.icon-tabs__tab.is-active::before) {
  animation: gwin-pending var(--motion-pulse) var(--ease-standard) infinite alternate;
}

@keyframes gwin-pending {
  to {
    opacity: 0.35;
  }
}

/* The centre column: the wall scrolls; the rejection line sits under it. */
.gwin__center {
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  min-width: 0;
  min-height: 0;
}

.gwin__wall {
  min-height: 0;
}

.gwin__feedback {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin: 0;
  padding: var(--sp-2) var(--sp-4);
  color: var(--paper-100);
  font-size: var(--text-sm);
  background: linear-gradient(90deg, rgba(169, 50, 42, 0.26), rgba(169, 50, 42, 0.08));
  border-top: var(--gwin-hair) solid rgba(210, 96, 84, 0.5);
  border-right: var(--gwin-hair) solid var(--gwin-line);
  animation: gwin-feedback-in var(--motion-base) var(--ease-enter);
}

@keyframes gwin-feedback-in {
  from {
    opacity: 0;
    transform: translateY(calc(calc(4px * var(--ui-scale)) * var(--motion-travel)));
  }
}

.gwin__feedback-mark {
  flex: none;
  width: calc(18px * var(--ui-scale));
  height: calc(18px * var(--ui-scale));
  color: #ed8a80;
}

.gwin__feedback-text {
  flex: 1;
  min-width: 0;
}

.gwin__feedback-link {
  flex: none;
  min-height: calc(36px * var(--ui-scale));
  padding: 0 var(--sp-3);
  color: var(--gold-300);
  font: inherit;
  font-size: var(--text-xs);
  letter-spacing: 0.06em;
  background: transparent;
  border: var(--gwin-hair) solid var(--gold-600);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background-color var(--motion-fast) var(--ease-standard), color var(--motion-fast) var(--ease-standard);
}

.gwin__feedback-link:hover {
  color: var(--paper-50);
  background: rgba(185, 154, 96, 0.14);
}

.gwin__feedback-link:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.gwin__page {
  min-width: 0;
  min-height: 0;
}

.gwin__page--empty {
  display: grid;
  place-items: center;
  padding: var(--sp-6);
  background:
    radial-gradient(90% 60% at 100% 0%, rgba(169, 50, 42, 0.08), transparent 70%),
    var(--ink-900);
}
</style>
