<script setup>
// ParticipantFrame (H3 webclient-hud-03-action-dock, tasks 6.1/6.2): the
// combat participant frame mounted in H1's `hud-left` anchor (task 6.3) —
// 我方 / 敵方 groups from the committed `participants[]` slice. Each row
// carries the `token`, `display_name`, the `hp_current / hp_maximum`
// numerals, and the state as an explicit text marker (`已逃離` / `倒地` /
// `已敗退`) alongside any colour (the state is never colour-only).
//
// Portraits resolve through `art.portrait_catalog[portrait_ref]` (task 6.2):
// a missing catalog entry renders the catalog's placeholder card, a `null`
// ref renders no card. No subject key or URL is constructed (the truthful
// data scope: no surface without a backing model).
import { computed } from "vue";

const props = defineProps({
  // The committed `context_actions` combat participants slice.
  participants: { type: Array, default: () => [] },
  // The committed `art` panel (the portrait catalog source).
  artPanel: { type: Object, default: null },
});

// Split the participants into the 我方 (party) and 敵方 (foes) groups,
// preserving the server's order within each group. The combat panel's
// `team` values are `party` and `foes` (see combat_panel TEAMS).
const allies = computed(() => props.participants.filter((p) => p.team === "party"));
const foes = computed(() => props.participants.filter((p) => p.team === "foes"));

// The explicit state marker (task 6.1): the text label rendered beside the
// HP numerals — a non-active participant's state is never conveyed by
// colour alone.
const STATE_MARKERS = {
  fled: "已逃離",
  knocked_out: "倒地",
  defeated: "已敗退",
  active: null,
};

function stateMarker(state) {
  return STATE_MARKERS[state] || "未知狀態";
}

// The portrait for one participant (task 6.2): the catalog entry by
// `portrait_ref`; a missing catalog entry renders the catalog's placeholder
// card, a `null` ref renders no card. No subject key or URL is constructed
// (the truthful-data scope).
function portraitFor(participant) {
  if (participant.portrait_ref === null || participant.portrait_ref === undefined) {
    return null;
  }
  const catalog = (props.artPanel && props.artPanel.portrait_catalog) || {};
  const entry = catalog[participant.portrait_ref];
  // A missing catalog entry renders the catalog's placeholder card.
  return entry || { placeholder: true };
}

// The portrait source: the catalog entry's `url`; a pending/missing entry
// renders the placeholder card (the truthful placeholder label).
function portraitSrc(portrait) {
  if (!portrait) {
    return "";
  }
  if (portrait.url) {
    return portrait.url;
  }
  return "";
}
</script>

<template>
  <div class="participant-frame" data-testid="participant-frame">
    <div v-if="allies.length" class="participant-frame__group">
      <div class="participant-frame__group-label">我方</div>
      <div
        v-for="p in allies"
        :key="p.identity"
        class="participant-frame__row"
        :class="{ 'participant-frame__row--muted': p.state !== 'active' }"
      >
        <span class="participant-frame__token" :class="{ 'participant-frame__token--ally': true }">
          {{ p.token }}
        </span>
        <span class="participant-frame__name">{{ p.display_name }}</span>
        <span class="participant-frame__hp">{{ p.hp_current }}/{{ p.hp_maximum }}</span>
        <span v-if="p.state !== 'active'" class="participant-frame__state">
          {{ stateMarker(p.state) }}
        </span>
        <template v-if="portraitFor(p)">
          <img
            v-if="portraitSrc(portraitFor(p))"
            class="participant-frame__portrait"
            :src="portraitSrc(portraitFor(p))"
            :alt="p.display_name"
          />
          <div
            v-else
            class="participant-frame__portrait-placeholder"
            :data-testid="participant-portrait-placeholder"
          >
            {{ (portraitFor(p).placeholder && portraitFor(p).placeholder.label) || "肖像圖像尚未生成" }}
          </div>
        </template>
      </div>
    </div>
    <div v-if="foes.length" class="participant-frame__group">
      <div class="participant-frame__group-label">敵方</div>
      <div
        v-for="p in foes"
        :key="p.identity"
        class="participant-frame__row"
        :class="{ 'participant-frame__row--muted': p.state !== 'active' }"
      >
        <span class="participant-frame__token" :class="{ 'participant-frame__token--foe': true }">
          {{ p.token }}
        </span>
        <span class="participant-frame__name">{{ p.display_name }}</span>
        <span class="participant-frame__hp">{{ p.hp_current }}/{{ p.hp_maximum }}</span>
        <span v-if="p.state !== 'active'" class="participant-frame__state">
          {{ stateMarker(p.state) }}
        </span>
        <template v-if="portraitFor(p)">
          <img
            v-if="portraitSrc(portraitFor(p))"
            class="participant-frame__portrait"
            :src="portraitSrc(portraitFor(p))"
            :alt="p.display_name"
          />
          <div
            v-else
            class="participant-frame__portrait-placeholder"
            :data-testid="participant-portrait-placeholder"
          >
            {{ (portraitFor(p).placeholder && portraitFor(p).placeholder.label) || "肖像圖像尚未生成" }}
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.participant-frame {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  background: var(--panel);
  border: var(--line);
  border-radius: var(--radius);
  padding: var(--sp-3);
  font-family: var(--f-sans);
}

.participant-frame__group {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.participant-frame__group-label {
  font-size: 10px;
  letter-spacing: 0.08em;
  color: var(--paper-500);
  margin-bottom: 2px;
}

.participant-frame__row {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  padding: 4px 6px;
  border-radius: var(--radius-sm);
}

.participant-frame__row--muted {
  opacity: 0.6;
}

/* The participant token: the draft's `.tok` style — party vs foes colour
   (the state marker text is the non-colour signal, task 6.1). */
.participant-frame__token {
  width: 38px;
  height: 38px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  font-family: var(--f-mono);
  font-size: 13px;
  background: var(--ink-780);
  border: 1px solid var(--ink-600);
  color: var(--paper-100);
  flex: none;
}

.participant-frame__token--ally {
  color: var(--vit-mp);
}

.participant-frame__token--foe {
  color: var(--seal-400);
}

.participant-frame__name {
  font-size: 13px;
  color: var(--paper-50);
  font-weight: 500;
}

.participant-frame__hp {
  font-family: var(--f-mono);
  font-size: 11px;
  color: var(--paper-500);
  margin-left: auto;
}

.participant-frame__state {
  font-size: 10px;
  color: var(--warn);
  white-space: nowrap;
}

.participant-frame__portrait {
  width: 38px;
  height: 38px;
  border-radius: 9px;
  object-fit: cover;
  flex: none;
  border: 1px solid var(--ink-600);
}

/* A missing/pending portrait renders the catalog's placeholder card (task
   6.2): the truthful placeholder label, no invented bitmap. */
.participant-frame__portrait-placeholder {
  width: 38px;
  height: 38px;
  border-radius: 9px;
  flex: none;
  display: grid;
  place-items: center;
  background: var(--ink-780);
  border: 1px dashed var(--ink-600);
  color: var(--paper-500);
  font-size: 9px;
  padding: 4px;
  text-align: center;
  line-height: 1.2;
}
</style>
