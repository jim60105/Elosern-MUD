<script setup>
// The rite arrival card (prototype): the new card in the `choices` anchor.
// It replaces the generic landmark card on a rite landmark: the archetype
// art in a band (no art: a quiet ink band, never substitute art), the
// landmark, the district's lit state, the guardian's name and form, how many
// of its stories were experienced, and 退開 / 走近. The art band is 16:5 so the
// whole card fits the travel stage's `choices` span at 1451x790. It renders no scene prose.
// Enter approaches, Escape steps back; Tab stays inside the card.
import { onMounted, ref } from "vue";

const props = defineProps({
  district: { type: Object, required: true },
  guardian: { type: Object, required: true },
  art: { type: String, default: null },
  lit: { type: Boolean, default: false },
  seen: { type: Number, default: 0 },
  total: { type: Number, default: 2 },
  // True when the card was reopened from the place card, not by an arrival.
  revisit: { type: Boolean, default: false },
});
const emit = defineEmits(["approach", "leave"]);
const go = ref(null);

function onKeydown(event) {
  if (event.ctrlKey || event.altKey || event.metaKey) return;
  if (event.key === "Enter") {
    event.preventDefault();
    event.stopPropagation();
    if (!event.repeat) emit("approach");
  } else if (event.key === "Escape") {
    event.preventDefault();
    event.stopPropagation();
    if (!event.repeat) emit("leave");
  } else if (event.key === "Tab") {
    // Two controls: Tab toggles between them.
    event.preventDefault();
    event.stopPropagation();
    const buttons = [...event.currentTarget.querySelectorAll("button")];
    const next = buttons[(buttons.indexOf(document.activeElement) + 1) % buttons.length];
    next?.focus();
  } else if (event.key !== " ") {
    event.stopPropagation();
  }
}

onMounted(() => go.value?.focus({ preventScroll: true }));
</script>

<template>
  <section class="choice-card rite-arrival" role="dialog" aria-modal="true" :aria-label="district.landmark" tabindex="-1" @keydown="onKeydown">
    <span class="choice-card__corners" aria-hidden="true"></span>
    <div class="rite-arrival__art" :class="{ 'is-empty': !art }">
      <img v-if="art" :src="art" alt="" />
      <p class="rite-arrival__kicker"><span class="rite-arrival__gem" aria-hidden="true"></span>{{ revisit ? "地標儀式" : "抵達地標" }}</p>
    </div>
    <div class="rite-arrival__body">
      <h2 class="rite-arrival__title">{{ district.landmark }}</h2>
      <p class="rite-arrival__district" :data-lit="lit ? 'true' : 'false'">
        <span aria-hidden="true">{{ lit ? "◆" : "◇" }}</span>
        {{ district.name }}{{ lit ? "已探明" : "尚未探明" }}
      </p>
      <div class="rite-arrival__guardian">
        <p class="rite-arrival__guardian-name">{{ guardian.name }}</p>
        <p class="rite-arrival__guardian-form">{{ guardian.form }}</p>
      </div>
      <div class="rite-arrival__foot">
        <p class="rite-arrival__seen">已體驗 {{ seen }} / {{ total }}</p>
        <button type="button" class="rite-arrival__btn" @click="emit('leave')"><span>退開</span><kbd aria-hidden="true">Esc</kbd></button>
        <button ref="go" type="button" class="rite-arrival__btn rite-arrival__btn--primary" @click="emit('approach')">
          <span>走近</span><kbd aria-hidden="true">Enter</kbd>
        </button>
      </div>
    </div>
  </section>
</template>

<style>
.rite-arrival.choice-card {
  position: relative;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  align-self: center;
  width: min(100%, calc(560px * var(--ui-scale)));
  max-height: 100%;
  padding: 0;
  overflow: hidden auto;
  background:
    radial-gradient(120% 60% at 50% 100%, rgba(185, 154, 96, 0.08), transparent 70%),
    linear-gradient(180deg, rgba(20, 20, 25, 0.98), rgba(11, 12, 16, 0.98));
  border: 1px solid rgba(185, 154, 96, 0.5);
  border-radius: var(--radius);
  box-shadow: var(--shadow-lg), 0 0 0 100vmax rgba(6, 7, 10, 0.34), inset 0 0 0 1px rgba(0, 0, 0, 0.55);
  outline: none;
  pointer-events: auto;
}
.rite-arrival__art {
  position: relative;
  flex: none;
  aspect-ratio: 16 / 5;
  overflow: hidden;
  border-radius: var(--radius) var(--radius) 0 0;
  background:
    radial-gradient(80% 120% at 50% 110%, rgba(185, 154, 96, 0.14), transparent 70%),
    linear-gradient(180deg, #1b1a20, #0e0f13);
}
.rite-arrival__art img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center 45%;
}
.rite-arrival__art.is-empty {
  aspect-ratio: auto;
  height: calc(64px * var(--ui-scale));
}
.rite-arrival__art.is-empty::before {
  content: "";
  position: absolute;
  left: 12%;
  right: 12%;
  top: 58%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(228, 200, 142, 0.35), transparent);
}
.rite-arrival__art::after {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(180deg, rgba(12, 13, 17, 0) 38%, rgba(12, 13, 17, 0.97));
}
.rite-arrival__kicker {
  position: absolute;
  left: calc(22px * var(--ui-scale));
  top: calc(16px * var(--ui-scale));
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: calc(8px * var(--ui-scale));
  margin: 0;
  padding: calc(4px * var(--ui-scale)) calc(10px * var(--ui-scale));
  border: 1px solid rgba(228, 200, 142, 0.35);
  border-radius: var(--radius-sm);
  background: rgba(12, 13, 17, 0.62);
  font: var(--text-xs)/1 var(--f-sans);
  letter-spacing: 0.3em;
  color: var(--gold-300);
}
.rite-arrival__gem {
  width: calc(7px * var(--ui-scale));
  height: calc(7px * var(--ui-scale));
  background: var(--gold-400);
  transform: rotate(45deg);
}
.rite-arrival__body {
  position: relative;
  z-index: 1;
  display: grid;
  gap: calc(8px * var(--ui-scale));
  margin-top: calc(-38px * var(--ui-scale));
  padding: 0 calc(26px * var(--ui-scale)) calc(16px * var(--ui-scale));
}
.rite-arrival__art.is-empty + .rite-arrival__body {
  margin-top: calc(4px * var(--ui-scale));
}
.rite-arrival__title {
  margin: 0;
  font: var(--text-3xl)/1.2 var(--f-display);
  letter-spacing: 0.06em;
  color: var(--paper-50);
  text-shadow: 0 2px 8px #000;
}
.rite-arrival__district {
  margin: 0;
  font: var(--text-sm)/1.3 var(--f-sans);
  letter-spacing: 0.08em;
  color: var(--paper-300);
}
.rite-arrival__district[data-lit="true"] {
  color: var(--gold-400);
}
.rite-arrival__guardian {
  display: grid;
  gap: calc(4px * var(--ui-scale));
  padding-left: calc(14px * var(--ui-scale));
  border-left: 2px solid rgba(185, 154, 96, 0.55);
}
.rite-arrival__guardian-name {
  margin: 0;
  font: var(--text-lg)/1.3 var(--f-display);
  letter-spacing: 0.12em;
  color: var(--gold-300);
}
.rite-arrival__guardian-form {
  margin: 0;
  font: var(--text-md)/var(--lh-narrative) var(--f-serif);
  color: var(--paper-200);
}
.rite-arrival__foot {
  display: flex;
  align-items: center;
  gap: calc(10px * var(--ui-scale));
  margin-top: calc(4px * var(--ui-scale));
}
.rite-arrival__seen {
  margin: 0 auto 0 0;
  font: var(--text-sm)/1.3 var(--f-sans);
  color: var(--paper-500);
}
.rite-arrival__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: calc(12px * var(--ui-scale));
  min-width: calc(120px * var(--ui-scale));
  min-height: calc(38px * var(--ui-scale));
  padding: 0 calc(18px * var(--ui-scale));
  border: 1px solid var(--ink-600);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--paper-200);
  font: var(--text-md)/1 var(--f-sans);
  letter-spacing: 0.16em;
  cursor: pointer;
}
.rite-arrival__btn--primary {
  min-width: calc(160px * var(--ui-scale));
  border-color: var(--gold-600);
  background: rgba(185, 154, 96, 0.14);
  color: var(--paper-50);
}
.rite-arrival__btn kbd {
  font: var(--text-xs)/1 var(--f-sans);
  letter-spacing: 0.04em;
  color: var(--gold-300);
  padding: calc(3px * var(--ui-scale)) calc(6px * var(--ui-scale));
  border: 1px solid rgba(228, 200, 142, 0.35);
  border-radius: calc(3px * var(--ui-scale));
}
.rite-arrival__btn:hover,
.rite-arrival__btn:focus-visible {
  border-color: var(--gold-400);
  background: var(--gold-glow);
  outline: none;
}
.rite-arrival__btn:focus-visible {
  box-shadow: 0 0 0 1px var(--gold-400), var(--focus);
}
</style>
