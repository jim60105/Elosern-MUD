<script setup>
// CodexDetail (handbook-primitives, design D4): the detail column shared by
// the handbook's titles and codex tabs, after the approved prototype's
// `.hb-detail` (docs/design/handbook-codex-titles/TitlesTabProto.vue). Top
// to bottom: the hero band (a round medal holding the grade gem when the
// entry has a grade, else its emblem; a dashed silhouette ring when locked;
// the optional nameplate beside it; the stamp), then the quest detail's
// ribbon, title and gold subtitle, the sections, and the shared DetailFooter
// pinned at the bottom. The `hero` slot replaces the default hero face
// (the codex tab puts art there). It renders a view model only and owns no
// state; footer presses are re-emitted as `press(key)`.
import { ref } from "vue";
import DetailFooter from "../DetailFooter.vue";
import GradeGem from "../GradeGem.vue";
import CodexEmblem from "./CodexEmblem.vue";

defineProps({
  // { id, name, ribbon, emblem, grade, locked, stamp: { kind, label } | null,
  //   subtitle, sections: [{ label, text }], nameplate }, or null.
  detail: { type: Object, default: null },
  // DetailFooter props ({ reason, reasonTone, reasonRole, buttons }), or null
  // for no footer.
  footer: { type: Object, default: null },
});

const emit = defineEmits(["press"]);

const footerRef = ref(null);

function focus(key) {
  footerRef.value?.focus(key);
}

defineExpose({ focus });
</script>

<template>
  <article v-if="detail" :key="detail.id" class="codex-detail" data-testid="handbook__detail" :data-detail-id="detail.id">
    <div class="codex-detail__scroll">
      <div class="codex-detail__hero">
        <slot name="hero" :detail="detail">
          <div class="codex-detail__face">
            <span
              class="codex-detail__medal"
              :class="{ 'is-locked': detail.locked }"
              :data-locked="detail.locked ? 'true' : undefined"
            >
              <GradeGem v-if="detail.grade" :grade="detail.grade" size="lg" />
              <span v-else class="codex-detail__emblem"><CodexEmblem :name="detail.emblem" :stroke-width="1.1" /></span>
            </span>
            <p v-if="detail.nameplate" class="codex-detail__nameplate">{{ detail.nameplate }}</p>
          </div>
        </slot>
        <span
          v-if="detail.stamp"
          class="codex-detail__stamp"
          :class="`codex-detail__stamp--${detail.stamp.kind}`"
          data-testid="handbook__stamp"
          :data-stamp="detail.stamp.kind"
        >{{ detail.stamp.label }}</span>
      </div>

      <header class="codex-detail__head">
        <span class="codex-detail__ribbon" data-testid="handbook__ribbon">
          <span v-if="detail.emblem" class="codex-detail__ribbon-glyph"><CodexEmblem :name="detail.emblem" /></span>
          {{ detail.ribbon }}
        </span>
        <h3 class="codex-detail__title" :class="{ 'is-locked': detail.locked }">{{ detail.name }}</h3>
        <p v-if="detail.subtitle" class="codex-detail__subtitle">{{ detail.subtitle }}</p>
      </header>

      <section
        v-for="(section, index) in detail.sections ?? []"
        :key="`${index}:${section.label}`"
        class="codex-detail__section"
        data-testid="handbook__section"
      >
        <h4 class="codex-detail__label">{{ section.label }}</h4>
        <p class="codex-detail__text">{{ section.text }}</p>
      </section>
    </div>
    <DetailFooter v-if="footer" ref="footerRef" v-bind="footer" @press="(key) => emit('press', key)" />
  </article>
  <div v-else class="codex-detail codex-detail--empty" data-testid="handbook__detail-empty"></div>
</template>

<style scoped>
/* The column, scroll, head, ribbon, title and subtitle copy QuestDetail's
   `.quest-detail`, `__scroll`, `__hero`, `__ribbon`, `__title` and
   `__objective`; the hero band, medal, stamp, sections and nameplate copy the
   prototype's `.hb-hero`, `.hb-stamp`, `.hb-letter`, `.hb-label` and
   `.hb-plate__text`. */
.codex-detail {
  position: relative;
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  min-width: 0;
  min-height: 0;
  height: 100%;
  box-sizing: border-box;
  font-family: var(--f-sans);
  background:
    radial-gradient(90% 60% at 100% 0%, rgba(169, 50, 42, 0.08), transparent 70%),
    #121418;
  animation: codex-detail-in var(--motion-reveal) ease-out;
}

.codex-detail--empty {
  grid-template-rows: 1fr;
  place-items: center;
  animation: none;
}

@keyframes codex-detail-in {
  from {
    opacity: 0;
    transform: translateX(6px);
  }
}

.codex-detail__scroll {
  display: flex;
  flex-direction: column;
  gap: var(--sp-5);
  min-height: 0;
  overflow-y: auto;
  padding: 0 var(--sp-8) var(--sp-6);
  scrollbar-width: thin;
  scrollbar-color: var(--ink-600) transparent;
}

.codex-detail__scroll > * {
  flex-shrink: 0;
}

.codex-detail__hero {
  position: relative;
  display: grid;
  place-items: center;
  height: calc(190px * var(--ui-scale));
  margin: 0 calc(-1 * var(--sp-8));
  overflow: hidden;
  background:
    radial-gradient(40% 70% at 50% 55%, rgba(228, 200, 142, 0.16), transparent 70%),
    radial-gradient(70% 90% at 50% 60%, #2c261b, #121418 75%);
  border-bottom: 1px solid rgba(185, 154, 96, 0.2);
}

.codex-detail__face {
  display: flex;
  align-items: center;
  gap: var(--sp-5);
}

.codex-detail__medal {
  display: grid;
  place-items: center;
  flex: none;
  width: calc(116px * var(--ui-scale));
  height: calc(116px * var(--ui-scale));
  border-radius: 50%;
  background: radial-gradient(circle at 40% 35%, #6a5631, #1a160f 70%);
  border: 3px solid var(--gold-400);
  box-shadow: 0 0 0 7px #121418, 0 0 0 8px var(--gold-600), 0 0 44px rgba(228, 200, 142, 0.25);
}

.codex-detail__medal.is-locked {
  background: repeating-linear-gradient(45deg, #121418 0 7px, #17191e 7px 14px);
  border: 3px dashed var(--ink-600);
  box-shadow: none;
}

.codex-detail__emblem {
  width: 58%;
  height: 58%;
  color: var(--gold-300);
}

.codex-detail__medal.is-locked .codex-detail__emblem,
.codex-detail__medal.is-locked .grade-gem {
  color: var(--paper-700);
  opacity: 0.45;
  filter: grayscale(1);
}

.codex-detail__nameplate {
  margin: 0;
  color: var(--gold-300);
  font: var(--text-xl) var(--f-display);
  letter-spacing: 0.1em;
}

.codex-detail__stamp {
  position: absolute;
  right: var(--sp-8);
  bottom: var(--sp-5);
  padding: 2px var(--sp-3);
  font: var(--text-xl) var(--f-display);
  letter-spacing: 0.3em;
  border-radius: var(--radius-sm);
  transform: rotate(-12deg);
  background: rgba(11, 13, 16, 0.55);
  pointer-events: none;
}

.codex-detail__stamp--equipped {
  color: var(--gold-300);
  border: 3px double var(--gold-500);
}

.codex-detail__stamp--locked {
  color: var(--paper-400);
  border: 2px dashed var(--paper-500);
}

.codex-detail__stamp--pending {
  color: var(--seal-400);
  border: 3px double var(--seal-500);
}

.codex-detail__head {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.codex-detail__ribbon {
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

.codex-detail__ribbon-glyph {
  width: 1.1em;
  height: 1.1em;
  color: var(--gold-300);
}

.codex-detail__title {
  margin: var(--sp-1) 0 0;
  color: var(--paper-50);
  font: var(--text-3xl) / 1.25 var(--f-display);
  letter-spacing: 0.04em;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.6);
}

.codex-detail__title.is-locked {
  color: var(--paper-400);
}

.codex-detail__subtitle {
  margin: 0;
  color: var(--gold-400);
  font: var(--text-lg) / 1.5 var(--f-serif);
}

.codex-detail__section {
  padding: var(--sp-4) var(--sp-5) var(--sp-5);
  background: linear-gradient(135deg, rgba(185, 154, 96, 0.09), rgba(185, 154, 96, 0.02) 60%);
  border: 1px solid rgba(185, 154, 96, 0.28);
  border-left: 3px solid var(--gold-500);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.codex-detail__label {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin: 0 0 var(--sp-2);
  color: var(--gold-500);
  font: var(--text-xs) var(--f-display);
  letter-spacing: 0.18em;
}

.codex-detail__label::after {
  content: "";
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.28), transparent);
}

.codex-detail__text {
  margin: 0;
  color: var(--paper-200);
  font: var(--text-sm) / 1.9 var(--f-serif);
}

@media (prefers-reduced-motion: reduce) {
  .codex-detail {
    animation: none;
  }
}
</style>
