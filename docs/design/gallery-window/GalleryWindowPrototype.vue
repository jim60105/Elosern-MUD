<script setup>
// GalleryWindowPrototype (Design/GalleryWindow): the portrait gallery as its
// own book-style window. A vertical rail of five categories (我的角色, 隊友,
// 人物, 魔物, 背景), the subject wall with an inline image tray, and the
// selected image's page: aspect-true art, facts, and the action footer.
// Scenes are landscape and offer neither a face frame nor a stage transform.
// Reference only, synthetic fixtures; not imported by the app.
import { computed, ref } from "vue";
import HudDrawer from "../../../web/webclient-app/components/HudDrawer.vue";
import IconTabs from "../../../web/webclient-app/components/IconTabs.vue";
import DetailFooter from "../../../web/webclient-app/components/DetailFooter.vue";
import EmptyState from "../../../web/webclient-app/components/EmptyState.vue";
import GalleryWall from "./GalleryWall.vue";

const props = defineProps({
  gallery: { type: Object, required: true },
  category: { type: String, default: "mine" },
  subject: { type: String, default: null },
  image: { type: String, default: null },
  // { [categoryKey]: reason } for categories that are not open yet.
  disabled: { type: Object, default: () => ({}) },
});

const wallId = "gallery-proto-wall";
const tabs = computed(() =>
  props.gallery.categories.map((row) => ({
    ...row,
    controls: wallId,
    disabled: row.key in props.disabled,
    reason: props.disabled[row.key] ?? null,
  })),
);

const category = ref(props.category);
const groups = computed(() => props.gallery.groups[category.value] ?? []);
const expandedGroup = ref(null);
const subjects = computed(() =>
  groups.value.filter((group) => !group.collapsible || group.key === expandedGroup.value).flatMap((group) => group.slots),
);
const categoryRow = computed(() => props.gallery.categories.find((row) => row.key === category.value));

const firstImage = (subject) =>
  (subject?.cards.find((card) => card.isDefault) ?? subject?.cards[0] ?? subject?.official[0])?.id ?? null;

const lastIntent = ref(null);
const subjectKey = ref(null);
const imageId = ref(null);
function selectSubject(key) {
  subjectKey.value = key;
  imageId.value = firstImage(subjects.value.find((row) => row.key === key));
}
function expandGroup(key) {
  expandedGroup.value = key;
  selectSubject(subjects.value[0]?.key ?? null);
  lastIntent.value = `gallery.group.select ${key}`;
}
function selectCategory(key) {
  if (key in props.disabled) return;
  category.value = key;
  expandedGroup.value = groups.value.find((group) => group.collapsible)?.key ?? null;
  const current = subjects.value.find((row) => row.current) ?? subjects.value[0];
  selectSubject(current?.key ?? null);
}
selectCategory(category.value);
if (props.subject) selectSubject(props.subject);
if (props.image) imageId.value = props.image;

const subject = computed(() => subjects.value.find((row) => row.key === subjectKey.value) ?? null);
const image = computed(() => {
  const row = subject.value;
  if (!row) return null;
  return [...row.cards, ...row.official].find((item) => item.id === imageId.value) ?? null;
});
const shape = computed(() => (category.value === "scene" ? "landscape" : "portrait"));

const ribbon = computed(() => {
  const label = categoryRow.value?.label ?? "";
  const group = groups.value.find((row) => row.label && row.slots.some((slot) => slot.key === subject.value?.key));
  return group ? `${label}・${group.label}` : label;
});

const footer = computed(() => {
  const row = subject.value;
  const item = image.value;
  if (!row) return null;
  const button = (key, label, tone = "plain", extra = {}) => ({ key, label, tone, testid: `gallery-proto__${key}`, ...extra });
  if (!item) return { buttons: [button("generate", "生成新圖", "primary")] };
  if (item.bundled) return { buttons: [button("generate", "生成新圖", "primary")] };
  if (item.official) {
    return {
      buttons: [button("clear", "清除個人調整", "ghost"), button("face", "臉框"), button("stage", "舞台位置"), button("default", "設為預設", "primary")],
    };
  }
  if (item.status === "pending") return { reason: "生成中，完成後會自動出現。", buttons: [] };
  if (item.status === "failed") return { reason: item.label, reasonTone: "danger", buttons: [button("delete", "刪除", "danger"), button("generate", "重新生成", "primary")] };
  if (row.kind === "scene") return { buttons: [button("delete", "刪除", "danger"), button("generate", "重新生成", "primary", { spacerBefore: true })] };
  if (row.kind === "monster") {
    return { buttons: [button("face", "臉框"), button("stage", "舞台位置"), button("generate", "重新生成", "primary")] };
  }
  return {
    buttons: [
      button("delete", "刪除", "danger"),
      button("face", "臉框", "plain", { spacerBefore: true }),
      button("stage", "舞台位置"),
      button("binding", "綁定裝備"),
      button("default", item.isDefault ? "目前預設" : "設為預設", "primary", { enabled: !item.isDefault }),
    ],
  };
});
function press(key) {
  lastIntent.value = `gallery.${key} ${subject.value?.key ?? ""}${image.value ? ` ${image.value.id}` : ""}`;
}
</script>

<template>
  <HudDrawer open title="圖庫" icon="gallery" drawer-key="gallery" body-flush>
    <section class="gwin" :class="`gwin--${shape}`" aria-label="圖庫">
      <IconTabs
        class="gwin__rail"
        orientation="vertical"
        aria-label="圖庫分類"
        show-labels
        :tabs="tabs"
        :model-value="category"
        @update:model-value="selectCategory"
      />

      <GalleryWall
        :id="wallId"
        :key="category"
        :groups="groups"
        :subject-key="subjectKey"
        :image-id="imageId"
        :shape="shape"
        :expanded-group="expandedGroup"
        :aria-label="categoryRow?.label ?? '圖庫'"
        @select-subject="selectSubject"
        @select-image="(id) => (imageId = id)"
        @generate="press('generate')"
        @expand-group="expandGroup"
      />

      <article v-if="subject" :key="`${subject.key}:${imageId}`" class="gpage">
        <div class="gpage__scroll">
          <div class="gpage__art" :class="{ 'gpage__art--empty': !image || image.status !== 'card' && !image.official }">
            <img v-if="image && (image.official || image.status === 'card')" :src="image.url" :alt="`${subject.name}・${image.label}`" />
            <p v-else-if="image" class="gpage__art-note">{{ image.status === "pending" ? "生成中…" : "生成失敗" }}</p>
            <p v-else class="gpage__art-note">尚無圖片</p>
          </div>
          <div class="gpage__facts">
            <header class="gpage__head">
              <span class="gpage__ribbon">{{ ribbon }}</span>
              <h3 class="gpage__title">{{ subject.name }}</h3>
            </header>
            <!-- Prose is a letter (the codex's 描述 box); facts are plain
                 labelled cells, as in the quest detail. -->
            <section v-if="subject.sentence" class="gpage__letter">
              <h4 class="gpage__label">描述</h4>
              <p class="gpage__prose">{{ subject.sentence }}</p>
            </section>
            <!-- One fact per cell on the quest detail's two-column grid
                 (`.quest-detail__cond`): a ruled label, one line, one note. -->
            <div class="gpage__cond">
              <section class="gpage__cell">
                <h4 class="gpage__label">圖片</h4>
                <template v-if="image">
                  <p class="gpage__line">{{ image.label }}</p>
                  <p v-if="image.official" class="gpage__text">唯讀，只能調整個人的臉框與舞台位置。</p>
                  <p v-else-if="image.bundled" class="gpage__text">尚未生成專屬圖片。</p>
                  <p v-else-if="subject.kind === 'scene'" class="gpage__text">只保留一張；刪除後回到官方內建圖。</p>
                  <p v-else-if="subject.maxCards === 1" class="gpage__text">只保留一張，重新生成會替換原圖。</p>
                </template>
                <template v-else>
                  <p class="gpage__line">尚無圖片</p>
                  <p class="gpage__text">生成一張來記錄它的模樣。</p>
                </template>
              </section>
              <section v-if="image && !image.official && !image.bundled" class="gpage__cell">
                <h4 class="gpage__label">生成時間</h4>
                <p class="gpage__line">{{ image.date }}</p>
                <p v-if="image.exact" class="gpage__text">{{ image.exact }}</p>
              </section>
              <section v-if="image && !image.official && subject.kind === 'character'" class="gpage__cell">
                <h4 class="gpage__label">狀態</h4>
                <p class="gpage__line">
                  <svg v-if="image.isDefault" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3 8l4.5 4L12 5l4.5 7L21 8l-2 11H5z" /></svg>
                  {{ image.status === "pending" ? "生成中" : image.status === "failed" ? "生成失敗" : image.isDefault ? "目前預設" : "備用圖片" }}
                </p>
                <p v-if="image.isDefault" class="gpage__text">沒有符合的綁定條件時顯示這張。</p>
              </section>
              <section v-if="image?.chips?.length" class="gpage__cell">
                <h4 class="gpage__label">標記</h4>
                <ul class="gpage__chips"><li v-for="chip in image.chips" :key="chip">{{ chip }}</li></ul>
              </section>
              <section v-if="image?.conditions?.length" class="gpage__cell gpage__cell--wide">
                <h4 class="gpage__label">綁定條件</h4>
                <ul class="gpage__chips gpage__chips--wide"><li v-for="line in image.conditions" :key="line">{{ line }}</li></ul>
              </section>
            </div>
            <p v-if="lastIntent" class="gpage__intent" role="status">送出 {{ lastIntent }}</p>
          </div>
        </div>
        <DetailFooter v-if="footer" v-bind="footer" @press="press" />
      </article>
      <div v-else class="gpage gpage--empty">
        <EmptyState glyph="gallery" headline="尚無記錄" guidance="旅途中遇見的對象會出現在這裡" />
      </div>
    </section>
  </HudDrawer>
</template>

<style scoped>
/* The book body of the quest drawer and the codex tab: rail, wall, page. */
.gwin {
  display: grid;
  grid-template-columns: calc(84px * var(--ui-scale)) minmax(calc(360px * var(--ui-scale)), 0.82fr) minmax(0, 1.18fr);
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

.gwin__rail {
  --icon-tabs-tab-h: calc(56px * var(--ui-scale));
  position: relative;
  z-index: 1;
  border-right: 1px solid rgba(185, 154, 96, 0.28);
}

.gpage {
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  min-width: 0;
  min-height: 0;
  background:
    radial-gradient(90% 60% at 100% 0%, rgba(169, 50, 42, 0.08), transparent 70%),
    #121418;
  animation: gpage-in var(--motion-reveal) ease-out;
}

.gpage--empty {
  grid-template-rows: 1fr;
  place-items: center;
  animation: none;
}

@keyframes gpage-in {
  from {
    opacity: 0;
    transform: translateX(6px);
  }
}

/* Portrait: the art fills the page height at 9:16, the facts sit beside it. */
.gpage__scroll {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: var(--sp-6);
  min-height: 0;
  padding: var(--sp-5) var(--sp-6);
}

.gpage__art {
  display: grid;
  place-items: center;
  height: 100%;
  min-height: 0;
  aspect-ratio: 9 / 16;
  overflow: hidden;
  background: radial-gradient(circle at 50% 30%, #2f2a20, #0f0e0c 75%);
  border: 1px solid var(--gold-600);
  border-radius: var(--radius-sm);
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.55);
}

.gpage__art img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.gpage__art--empty {
  border-style: dashed;
  box-shadow: none;
}

.gpage__art-note {
  margin: 0;
  color: var(--paper-500);
  font-size: var(--text-sm);
}

/* Landscape: the 16:9 art sits above; under it the name and the description
   take the left column and the fact cells the right one, so the whole page
   reads without scrolling. */
.gwin--landscape .gpage__scroll {
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: auto minmax(0, 1fr);
  gap: var(--sp-4);
}

.gwin--landscape .gpage__art {
  width: 60%;
  height: auto;
  aspect-ratio: 16 / 9;
}

.gwin--landscape .gpage__facts {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr);
  grid-template-areas:
    "head cond"
    "letter cond"
    "intent intent";
  align-content: start;
  gap: var(--sp-3) var(--sp-6);
}

.gwin--landscape .gpage__head {
  grid-area: head;
}

.gwin--landscape .gpage__letter {
  grid-area: letter;
}

.gwin--landscape .gpage__cond {
  grid-area: cond;
  grid-template-columns: 1fr;
  gap: var(--sp-4);
}

.gwin--landscape .gpage__intent {
  grid-area: intent;
}

.gpage__facts {
  max-height: 100%;
}

.gwin--landscape .gpage__cond {
  grid-template-columns: 1fr;
}

.gpage__facts {
  display: flex;
  flex-direction: column;
  gap: var(--sp-5);
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--ink-600) transparent;
  scrollbar-gutter: stable;
}

.gpage__head {
  display: flex;
  flex-direction: column;
}

.gpage__ribbon {
  align-self: flex-start;
  padding: 3px calc(22px * var(--ui-scale)) 3px var(--sp-3);
  color: var(--paper-50);
  font: var(--text-xs) var(--f-display);
  letter-spacing: 0.12em;
  background: linear-gradient(180deg, var(--seal-600), var(--seal-700));
  clip-path: polygon(0 0, 100% 0, calc(100% - 10px) 50%, 100% 100%, 0 100%);
}

.gpage__title {
  margin: var(--sp-1) 0 0;
  color: var(--paper-50);
  font: var(--text-3xl) / 1.25 var(--f-display);
  letter-spacing: 0.04em;
}

/* Prose: the codex's and the quest client's letter box. */
.gpage__letter {
  padding: var(--sp-4) var(--sp-5) var(--sp-5);
  background: linear-gradient(135deg, rgba(185, 154, 96, 0.09), rgba(185, 154, 96, 0.02) 60%);
  border: 1px solid rgba(185, 154, 96, 0.28);
  border-left: 3px solid var(--gold-500);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.gpage__prose {
  margin: 0;
  color: var(--paper-200);
  font: var(--text-sm) / 1.9 var(--f-serif);
}

/* Facts: an unboxed cell under a ruled label, as the quest detail's
   接取條件 and 期限. */
.gpage__cond {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--sp-5) var(--sp-6);
}

.gpage__cell {
  min-width: 0;
}

.gpage__cell--wide {
  grid-column: 1 / -1;
}

.gpage__line svg {
  flex: none;
  width: 1.1em;
  height: 1.1em;
  color: var(--gold-500);
}

.gpage__label {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin: 0 0 var(--sp-2);
  color: var(--gold-500);
  font: var(--text-xs) var(--f-display);
  letter-spacing: 0.18em;
}

.gpage__label::after {
  content: "";
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.28), transparent);
}

.gpage__line {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin: 0 0 var(--sp-1);
  color: var(--paper-50);
  font-size: var(--text-md);
}

.gpage__text {
  margin: 0;
  color: var(--paper-300);
  font-size: var(--text-sm);
  line-height: 1.75;
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
  color: var(--paper-300);
  font-size: var(--text-sm);
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--ink-700);
  border-radius: var(--radius-sm);
}

.gpage__chips--wide li {
  padding: var(--sp-2) var(--sp-4);
  color: var(--paper-100);
}

.gpage__intent {
  margin: 0;
  padding: 2px var(--sp-3);
  color: var(--paper-400);
  font: var(--text-xs) var(--f-mono);
  border: 1px dashed var(--ink-600);
  border-radius: var(--radius-sm);
}

@media (prefers-reduced-motion: reduce) {
  .gpage {
    animation: none;
  }
}
</style>
