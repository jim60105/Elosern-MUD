<script setup>
// CodexTabProto (prototype of LoreCodexTab): the Handbook's 圖鑑 tab over the
// proposed `lore_codex` v2 payload. Rail = the eight categories (discovered
// count badge); middle = the MHW tile wall, grouped (monsters by threat tier),
// with silhouette placeholders that never select; right = the quest detail's
// language (hero art band, seal ribbon, display title, gold subtitle, labelled
// sections) plus the two-stage research track for monsters. Fields the server
// lists in `locked_fields` draw a dashed 擊敗後解鎖 box, never their values.
import { computed, ref, useId, watch } from "vue";
import IconTabs from "../../../web/webclient-app/components/IconTabs.vue";
import EmptyState from "../../../web/webclient-app/components/EmptyState.vue";
import GradeGem from "../../../web/webclient-app/components/GradeGem.vue";
import CodexEmblem from "./CodexEmblem.vue";
import TileWall from "./TileWall.vue";

const props = defineProps({
  codex: { type: Object, required: true },
  initialCategory: { type: String, default: "monster" },
  initialEntry: { type: String, default: null },
});

const uid = useId();
const FIELD_LABELS = {
  published_appearance_zh: "外觀",
  published_description_zh: "概要",
  published_ecology_zh: "生態",
  habitat_tags: "棲地",
  variants: "已知變種",
  threat_tier: "威脅",
  description: "記述",
  terrain_flavor_zh: "地貌",
  capital_name_zh: "首都",
};

const categories = computed(() => props.codex.categories);
const categoryKey = ref(props.initialCategory);
const category = computed(() => categories.value.find((c) => c.key === categoryKey.value) ?? categories.value[0]);

const railTabs = computed(() =>
  categories.value.map((c) => ({
    key: c.key,
    label: c.label,
    count: c.discovered,
    controls: `codex-${uid}-wall`,
  })),
);

const groups = computed(() =>
  category.value.groups.map((group) => ({
    key: group.key,
    label: group.label,
    items: group.slots.map((slot, index) =>
      slot.placeholder
        ? { id: `${group.key}:?${index}`, selectable: false, label: "未記錄", slot }
        : {
            id: slot.key,
            selectable: true,
            label: slot.stage ? `${slot.title}，${slot.stage === "defeated" ? "已擊敗" : "已目擊"}` : slot.title,
            slot,
          },
    ),
  })),
);

const discoveredSlots = computed(() =>
  category.value.groups.flatMap((g) => g.slots).filter((slot) => !slot.placeholder),
);

const selectedKey = ref(props.initialEntry);
watch(
  [categoryKey, discoveredSlots],
  () => {
    if (!discoveredSlots.value.some((slot) => slot.key === selectedKey.value)) {
      selectedKey.value = discoveredSlots.value[0]?.key ?? null;
    }
  },
  { immediate: true },
);
const entry = computed(() => discoveredSlots.value.find((slot) => slot.key === selectedKey.value) ?? null);

const field = (name) => entry.value?.card.find((f) => f.name === name)?.value ?? null;
const locked = (name) => entry.value?.locked_fields.includes(name) ?? false;
const isMonster = computed(() => category.value.key === "monster");

const subtitle = computed(() => {
  if (!entry.value) return "";
  return field("published_description_zh") ?? field("published_appearance_zh") ?? "";
});

// Sections other than the monster layout: every card field in panel order.
const plainSections = computed(() =>
  (entry.value?.card ?? []).map((f) => ({ name: f.name, label: FIELD_LABELS[f.name] ?? "資料", value: f.value })),
);

const artFailed = ref(new Set());
const heroArt = computed(() => (entry.value?.art && !artFailed.value.has(entry.value.art) ? entry.value.art : null));
function onArtError(src) {
  artFailed.value = new Set([...artFailed.value, src]);
}
</script>

<template>
  <div class="hb-codex" data-testid="handbook__codex">
    <IconTabs
      class="hb-codex__rail"
      orientation="vertical"
      aria-label="圖鑑分類"
      show-labels
      :tabs="railTabs"
      :model-value="categoryKey"
      @update:model-value="(key) => (categoryKey = key)"
    >
      <template #icon="{ tab }">
        <CodexEmblem :name="tab.key" />
      </template>
    </IconTabs>

    <div :id="`codex-${uid}-wall`" class="hb-wall" role="tabpanel" :aria-label="category.label">
      <header class="hb-wall__head">
        <span class="hb-wall__kicker">{{ category.label }}</span>
        <span class="hb-wall__rule" aria-hidden="true"></span>
        <span class="hb-wall__n">
          <b>{{ category.discovered }}</b> / {{ category.total }}
        </span>
      </header>
      <TileWall :groups="groups" :selected-id="selectedKey" :aria-label="`${category.label}條目`" @select="(id) => (selectedKey = id)">
        <template #tile="{ item, selected }">
          <div v-if="item.slot.placeholder" class="hb-tile hb-tile--unknown">
            <span class="hb-tile__q" aria-hidden="true">？</span>
          </div>
          <div v-else class="hb-tile" :class="{ 'is-selected': selected, 'is-sighted': item.slot.stage === 'sighted' }">
            <img
              v-if="item.slot.art && !artFailed.has(item.slot.art)"
              class="hb-tile__art"
              :src="item.slot.art"
              alt=""
              @error="onArtError(item.slot.art)"
            />
            <span v-else class="hb-tile__emblem"><CodexEmblem :name="category.key" :stroke-width="1.3" /></span>
            <span class="hb-tile__name">{{ item.slot.title }}</span>
            <span v-if="item.slot.stage" class="hb-tile__stage" :class="`hb-tile__stage--${item.slot.stage}`" aria-hidden="true">
              <svg viewBox="0 0 12 12"><path d="M6 1 11 6 6 11 1 6Z" /></svg>
            </span>
          </div>
        </template>
      </TileWall>
      <p class="hb-wall__legend" aria-hidden="true" v-if="isMonster">
        <span class="hb-legend hb-legend--defeated"><svg viewBox="0 0 12 12"><path d="M6 1 11 6 6 11 1 6Z" /></svg>已擊敗</span>
        <span class="hb-legend hb-legend--sighted"><svg viewBox="0 0 12 12"><path d="M6 1 11 6 6 11 1 6Z" /></svg>僅目擊</span>
        <span class="hb-legend hb-legend--unknown">？未記錄</span>
      </p>
    </div>

    <article v-if="entry" :key="entry.key" class="hb-detail" data-testid="handbook__codex-detail">
      <div class="hb-detail__scroll">
        <div class="hb-hero" :class="{ 'hb-hero--emblem': !heroArt }">
          <img v-if="heroArt" class="hb-hero__art" :src="heroArt" alt="" @error="onArtError(heroArt)" />
          <span v-else class="hb-hero__emblem"><CodexEmblem :name="category.key" :stroke-width="0.9" /></span>
          <span
            v-if="entry.stage"
            class="hb-stamp"
            :class="`hb-stamp--${entry.stage}`"
          >{{ entry.stage === "defeated" ? "已擊敗" : "目擊" }}</span>
        </div>

        <header class="hb-head">
          <span class="hb-ribbon">
            <span class="hb-ribbon__glyph"><CodexEmblem :name="category.key" /></span>
            {{ category.label }}<template v-if="field('threat_tier')"> ・ {{ field("threat_tier") }}</template>
          </span>
          <h3 class="hb-title">{{ entry.title }}</h3>
          <p v-if="subtitle" class="hb-subtitle">{{ subtitle }}</p>
        </header>

        <section v-if="isMonster" class="hb-research" aria-label="研究進度">
          <h4 class="hb-label">研究</h4>
          <ol class="hb-track">
            <li class="is-on"><span class="hb-track__pip"></span>目擊<small>外觀・威脅</small></li>
            <li :class="{ 'is-on': entry.stage === 'defeated' }">
              <span class="hb-track__pip"></span>擊敗<small>概要・生態・棲地・變種</small>
            </li>
          </ol>
        </section>

        <template v-if="isMonster">
          <div class="hb-cols">
            <section class="hb-cell">
              <h4 class="hb-label">外觀</h4>
              <p class="hb-text">{{ field("published_appearance_zh") }}</p>
            </section>
            <section class="hb-cell">
              <h4 class="hb-label">棲地</h4>
              <div v-if="locked('habitat_tags')" class="hb-locked">
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M8 11V8a4 4 0 0 1 8 0v3M5.5 11h13v9.5h-13zM12 14.5v2.5" stroke="currentColor" stroke-width="1.6" /></svg>
                擊敗後解鎖
              </div>
              <ul v-else class="hb-tags">
                <li v-for="tag in field('habitat_tags')" :key="tag">{{ tag }}</li>
              </ul>
            </section>
          </div>

          <section class="hb-letter">
            <h4 class="hb-label">生態</h4>
            <div v-if="locked('published_ecology_zh')" class="hb-locked hb-locked--block">
              <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M8 11V8a4 4 0 0 1 8 0v3M5.5 11h13v9.5h-13zM12 14.5v2.5" stroke="currentColor" stroke-width="1.6" /></svg>
              擊敗一次後，這裡會記下牠的習性與危害。
            </div>
            <p v-else class="hb-letter__text">{{ field("published_ecology_zh") }}</p>
          </section>

          <section>
            <h4 class="hb-label">已知變種</h4>
            <div v-if="locked('variants')" class="hb-locked">
              <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M8 11V8a4 4 0 0 1 8 0v3M5.5 11h13v9.5h-13zM12 14.5v2.5" stroke="currentColor" stroke-width="1.6" /></svg>
              擊敗後解鎖
            </div>
            <ul v-else class="hb-variants">
              <li v-for="variant in field('variants')" :key="variant.name">
                <GradeGem :grade="variant.grade" size="sm" :label="`危險等級 ${variant.grade}`" />
                <span>{{ variant.name }}</span>
                <small>危險等級 {{ variant.grade }}</small>
              </li>
            </ul>
          </section>
        </template>

        <template v-else>
          <section v-for="section in plainSections" :key="section.name" class="hb-letter">
            <h4 class="hb-label">{{ section.label }}</h4>
            <p class="hb-letter__text">{{ section.value }}</p>
          </section>
        </template>
      </div>
    </article>

    <div v-else class="hb-detail hb-detail--empty">
      <EmptyState glyph="lore" headline="尚未記錄任何條目" guidance="旅途中遭遇的事物會記錄於此。" />
    </div>
  </div>
</template>

<style scoped>
.hb-codex {
  display: grid;
  grid-template-columns: calc(68px * var(--ui-scale)) minmax(calc(360px * var(--ui-scale)), 0.82fr) minmax(0, 1.18fr);
  min-height: 0;
  height: 100%;
}

.hb-codex__rail {
  position: relative;
  z-index: 1;
}

/* ---- Wall column: the quest list's surface and head. */
.hb-wall {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  min-height: 0;
  overflow-y: auto;
  padding: var(--sp-4);
  background: #15171c;
  border-right: 1px solid rgba(185, 154, 96, 0.28);
  scrollbar-width: thin;
  scrollbar-color: var(--ink-600) transparent;
}

.hb-wall__head {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
}

.hb-wall__kicker {
  color: var(--gold-400);
  font: var(--text-md) var(--f-display);
  letter-spacing: 0.12em;
}

.hb-wall__rule {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.28), transparent);
}

.hb-wall__n {
  color: var(--paper-500);
  font: var(--text-xs) var(--f-num);
  font-variant-numeric: tabular-nums;
}

.hb-wall__n b {
  color: var(--gold-300);
  font-size: var(--text-md);
  font-weight: 500;
}

.hb-wall__legend {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-4);
  margin: auto 0 0;
  padding-top: var(--sp-3);
  color: var(--paper-500);
  font-size: var(--text-xs);
  border-top: 1px dashed rgba(185, 154, 96, 0.14);
}

.hb-legend {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);
}

.hb-legend svg {
  width: 0.9em;
  height: 0.9em;
}

/* ---- Tiles */
.hb-tile {
  position: relative;
  display: grid;
  aspect-ratio: 1;
  overflow: hidden;
  background: radial-gradient(circle at 50% 38%, #3d3526, #15130f 72%);
  border: 1px solid var(--gold-600);
  border-radius: var(--radius-sm);
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.5);
  transition: border-color var(--motion-fast) ease, transform var(--motion-fast) ease;
}

.hb-tile:hover {
  border-color: var(--gold-400);
}

.hb-tile.is-selected {
  border-color: var(--seal-400);
  box-shadow: inset 0 0 0 1px var(--seal-500), 0 0 14px var(--seal-glow);
}

.hb-tile__art {
  grid-area: 1 / 1;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center 30%;
}

.hb-tile.is-sighted .hb-tile__art {
  filter: saturate(0.45) brightness(0.8);
}

.hb-tile__emblem {
  grid-area: 1 / 1;
  place-self: center;
  width: 46%;
  height: 46%;
  margin-bottom: 18%;
  color: var(--gold-400);
}

.hb-tile__name {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: var(--sp-4) var(--sp-1) var(--sp-1);
  overflow: hidden;
  color: var(--paper-50);
  font: var(--text-xs) / 1.3 var(--f-serif);
  text-align: center;
  white-space: nowrap;
  text-overflow: ellipsis;
  background: linear-gradient(180deg, transparent, rgba(8, 9, 11, 0.92) 60%);
}

.hb-tile__stage {
  position: absolute;
  top: var(--sp-1);
  right: var(--sp-1);
  width: calc(14px * var(--ui-scale));
  height: calc(14px * var(--ui-scale));
  filter: drop-shadow(0 1px 2px #000);
}

.hb-tile__stage svg,
.hb-legend svg {
  display: block;
  width: 100%;
  height: 100%;
}

/* Defeated: a filled gold diamond; sighted: a hollow one. Shape, not colour. */
.hb-tile__stage--defeated path,
.hb-legend--defeated path {
  fill: var(--gold-400);
  stroke: var(--ink-950);
  stroke-width: 1;
}

.hb-tile__stage--sighted path,
.hb-legend--sighted path {
  fill: rgba(11, 13, 16, 0.6);
  stroke: var(--paper-300);
  stroke-width: 1.4;
}

.hb-tile--unknown {
  background: repeating-linear-gradient(45deg, #121418 0 6px, #17191e 6px 12px);
  border: 1px dashed var(--ink-600);
  box-shadow: none;
}

.hb-tile__ghost {
  grid-area: 1 / 1;
  place-self: center;
  width: 54%;
  height: 54%;
  color: var(--ink-700);
}

.hb-tile__q {
  grid-area: 1 / 1;
  place-self: center;
  color: var(--paper-700);
  font: var(--text-xl) var(--f-display);
}

/* ---- Detail column: the quest detail's surface and language. */
.hb-detail {
  position: relative;
  display: grid;
  min-width: 0;
  min-height: 0;
  height: 100%;
  background:
    radial-gradient(90% 60% at 100% 0%, rgba(169, 50, 42, 0.08), transparent 70%),
    #121418;
  animation: hb-in var(--motion-reveal) ease-out;
}

.hb-detail--empty {
  place-items: center;
  animation: none;
}

@keyframes hb-in {
  from {
    opacity: 0;
    transform: translateX(6px);
  }
}

.hb-detail__scroll {
  display: flex;
  flex-direction: column;
  gap: var(--sp-5);
  min-height: 0;
  overflow-y: auto;
  padding: 0 var(--sp-8) var(--sp-6);
  scrollbar-width: thin;
  scrollbar-color: var(--ink-600) transparent;
}

.hb-detail__scroll > * {
  flex-shrink: 0;
}

.hb-hero {
  position: relative;
  display: grid;
  height: calc(230px * var(--ui-scale));
  margin: 0 calc(-1 * var(--sp-8));
  overflow: hidden;
  background: radial-gradient(70% 90% at 50% 60%, #3b3222, #121418 75%);
  border-bottom: 1px solid rgba(185, 154, 96, 0.2);
  -webkit-mask-image: linear-gradient(180deg, #000 70%, transparent);
  mask-image: linear-gradient(180deg, #000 70%, transparent);
}

.hb-hero__art {
  grid-area: 1 / 1;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center 28%;
}

.hb-hero__emblem {
  grid-area: 1 / 1;
  place-self: center;
  width: calc(120px * var(--ui-scale));
  height: calc(120px * var(--ui-scale));
  color: var(--gold-500);
  filter: drop-shadow(0 0 18px rgba(228, 200, 142, 0.25));
}

.hb-stamp {
  position: absolute;
  right: var(--sp-8);
  bottom: calc(46px * var(--ui-scale));
  padding: 2px var(--sp-3);
  font: var(--text-xl) var(--f-display);
  letter-spacing: 0.3em;
  border-radius: var(--radius-sm);
  transform: rotate(-12deg);
  pointer-events: none;
}

.hb-stamp--defeated {
  color: var(--seal-400);
  border: 3px double var(--seal-500);
  background: rgba(11, 13, 16, 0.55);
}

.hb-stamp--sighted {
  color: var(--paper-300);
  border: 2px dashed var(--paper-500);
  background: rgba(11, 13, 16, 0.55);
}

.hb-head {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  margin-top: calc(-34px * var(--ui-scale));
  position: relative;
}

.hb-ribbon {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  padding: 3px calc(22px * var(--ui-scale)) 3px var(--sp-3);
  color: var(--paper-50);
  font: var(--text-xs) var(--f-display);
  letter-spacing: 0.12em;
  background: linear-gradient(180deg, var(--seal-600), var(--seal-700));
  clip-path: polygon(0 0, 100% 0, calc(100% - 10px) 50%, 100% 100%, 0 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12);
}

.hb-ribbon__glyph {
  width: 1.1em;
  height: 1.1em;
  color: var(--gold-300);
}

.hb-title {
  margin: var(--sp-1) 0 0;
  color: var(--paper-50);
  font: var(--text-3xl) / 1.25 var(--f-display);
  letter-spacing: 0.04em;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.6);
}

.hb-subtitle {
  margin: 0;
  color: var(--gold-400);
  font: var(--text-lg) / 1.5 var(--f-serif);
}

.hb-label {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin: 0 0 var(--sp-2);
  color: var(--gold-500);
  font: var(--text-xs) var(--f-display);
  letter-spacing: 0.18em;
}

.hb-label::after {
  content: "";
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.28), transparent);
}

/* Research track: the quest progress pips, two steps, each labelled. */
.hb-track {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--sp-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.hb-track li {
  display: grid;
  gap: var(--sp-1);
  color: var(--paper-500);
  font: var(--text-sm) var(--f-display);
  letter-spacing: 0.1em;
}

.hb-track li small {
  color: var(--paper-500);
  font: var(--text-xs) var(--f-sans);
  letter-spacing: 0;
}

.hb-track li.is-on {
  color: var(--paper-50);
}

.hb-track__pip {
  height: calc(10px * var(--ui-scale));
  background: #0b0d10;
  border: 1px solid var(--ink-600);
  clip-path: polygon(6px 0, 100% 0, calc(100% - 6px) 100%, 0 100%);
}

.hb-track li.is-on .hb-track__pip {
  background: linear-gradient(90deg, var(--gold-600), var(--gold-400));
  border-color: var(--gold-500);
  box-shadow: 0 0 8px var(--gold-glow);
}

.hb-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--sp-6);
}

.hb-cell {
  min-width: 0;
}

.hb-text {
  margin: 0;
  color: var(--paper-300);
  font-size: var(--text-sm);
  line-height: 1.75;
}

.hb-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.hb-tags li {
  padding: 1px var(--sp-3);
  color: var(--paper-200);
  font-size: var(--text-sm);
  border: 1px solid var(--ink-600);
  border-radius: var(--radius-pill);
}

.hb-letter {
  position: relative;
  padding: var(--sp-4) var(--sp-5) var(--sp-5);
  background: linear-gradient(135deg, rgba(185, 154, 96, 0.09), rgba(185, 154, 96, 0.02) 60%);
  border: 1px solid rgba(185, 154, 96, 0.28);
  border-left: 3px solid var(--gold-500);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.hb-letter__text {
  max-width: 40em;
  margin: 0;
  color: var(--paper-200);
  font: var(--text-sm) / 1.9 var(--f-serif);
}

.hb-locked {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  padding: var(--sp-1) var(--sp-3);
  color: var(--paper-500);
  font-size: var(--text-sm);
  border: 1px dashed var(--ink-600);
  border-radius: var(--radius-sm);
}

.hb-locked--block {
  display: flex;
  padding: var(--sp-3);
}

.hb-locked svg {
  flex: none;
  width: 1.1em;
  height: 1.1em;
  color: var(--paper-500);
}

.hb-variants {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.hb-variants li {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  color: var(--paper-50);
  font: var(--text-md) var(--f-serif);
}

.hb-variants small {
  margin-left: auto;
  color: var(--paper-500);
  font: var(--text-xs) var(--f-sans);
}

@media (prefers-reduced-motion: reduce) {
  .hb-detail {
    animation: none;
  }
}
</style>
