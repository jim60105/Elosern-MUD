<script setup>
// CreationPresetWall (creation-preset-card-wall; design §5): the preset
// cards as one row of portrait cards. Exactly one card is expanded at a time:
// its full 9:16 figure stands beside a dossier whose primary button is the
// deliberate selection. Which card is expanded is local browsing state,
// separate from the saved draft: opening a card by pointer, ← / → or its
// ordinal digit sends nothing. Only the primary button, or Enter in wall
// context, emits `choose(card)`, which the overlay routes into the existing
// preset save and activation confirmation.
//
// Every supplied card renders; nothing here knows the shipped roster. Each
// card's server-built `artwork` descriptor goes to ArtworkPreview unchanged
// (no URL is composed here), so the shared loader owns the official image,
// its face-rectangle crop and the alpha-terminal fallback.
import { computed, nextTick, onMounted, ref, watch } from "vue";
import ArtworkPreview from "./ArtworkPreview.vue";
import { useCreationWallInput } from "../composables/use-creation-wall-input.js";

const props = defineProps({
  // The committed panel's preset cards, in server order.
  presets: { type: Array, default: () => [] },
  // The saved draft's preset key (or null): the card expanded on entry.
  draftPresetKey: { type: String, default: null },
  // A mutation is in flight: browsing stays live, choosing is held.
  disabled: { type: Boolean, default: false },
  // Race key -> display name, from the committed custom descriptor.
  raceDisplayName: { type: Function, default: (key) => key },
  // The creation dock stands on its (row-less) preset-list frame, so the
  // keys aimed at the dock browse this wall too.
  dockBrowsing: { type: Boolean, default: false },
});

const emit = defineEmits(["choose"]);

// The availability fact ArtworkPreview judges a position against: the
// overlay mounts the wall only for an available creation panel.
const AVAILABLE_PANEL = Object.freeze({ available: true });

const root = ref(null);
// The rendered card wrappers by key (only the expanded one is focusable).
const cardEls = new Map();
function setCardEl(key, el) {
  if (el) cardEls.set(key, el);
  else cardEls.delete(key);
}
const keys = computed(() => props.presets.map((card) => card.key));

function entryKey() {
  if (props.draftPresetKey && keys.value.includes(props.draftPresetKey)) return props.draftPresetKey;
  return keys.value[0] ?? null;
}

const expandedKey = ref(entryKey());
const expandedIndex = computed(() => keys.value.indexOf(expandedKey.value));

// A republication keeps a surviving local browse selection; a vanished one
// falls back to the surviving draft card, then to the first card.
watch(keys, () => {
  if (!keys.value.includes(expandedKey.value)) expandedKey.value = entryKey();
});

const pad = (n) => String(n).padStart(2, "0");
const total = computed(() => pad(props.presets.length));

function focusExpanded() {
  cardEls.get(expandedKey.value)?.focus({ preventScroll: true });
}

async function open(key, { keepFocus = false } = {}) {
  if (!keys.value.includes(key)) return;
  // The opening button that had focus unmounts as its card expands, so focus
  // that was inside the wall follows to the newly expanded card. A dock-
  // driven change leaves the dock's focus where it is.
  const follow = !keepFocus && !!root.value?.contains(document.activeElement);
  expandedKey.value = key;
  if (follow) {
    await nextTick();
    focusExpanded();
  }
}

function move(delta, fromWall) {
  const index = expandedIndex.value;
  const next = Math.max(0, Math.min(keys.value.length - 1, index + delta));
  if (index >= 0 && next !== index) open(keys.value[next], { keepFocus: !fromWall });
}

function jump(index, fromWall) {
  if (index >= 0 && index < keys.value.length) open(keys.value[index], { keepFocus: !fromWall });
}

function choose() {
  if (props.disabled) return;
  const card = props.presets[expandedIndex.value];
  if (card) emit("choose", card);
}

useCreationWallInput({ root, dockBrowsing: () => props.dockBrowsing, move, jump, choose });

// Preset-mode entry (the overlay mounts the wall) puts focus on the
// expanded card, so the wall's keys work without a pointer.
onMounted(focusExpanded);
</script>

<template>
  <div
    ref="root"
    class="creation-wall"
    role="group"
    aria-label="預設角色"
    data-testid="creation-preset-wall"
  >
    <div
      v-for="(card, index) in presets"
      :key="card.key"
      :ref="(el) => setCardEl(card.key, el)"
      class="creation-wall__card"
      data-testid="creation-preset-card"
      :data-preset-key="card.key"
      :data-expanded="card.key === expandedKey ? 'true' : 'false'"
      :data-selected="draftPresetKey === card.key ? 'true' : 'false'"
      :role="card.key === expandedKey ? 'group' : undefined"
      :aria-label="card.key === expandedKey ? card.display_name : undefined"
      :aria-current="card.key === expandedKey ? 'true' : undefined"
      :tabindex="card.key === expandedKey ? -1 : undefined"
    >
      <div class="creation-wall__art">
        <ArtworkPreview :artwork="card.artwork ?? null" :panel="AVAILABLE_PANEL" :alt="card.display_name" />
      </div>
      <button
        v-if="card.key !== expandedKey"
        type="button"
        class="creation-wall__spine"
        data-testid="creation-preset-open"
        :aria-label="card.display_name"
        @click="open(card.key)"
      >
        <span class="creation-wall__no" aria-hidden="true">{{ pad(index + 1) }}</span>
        <span class="creation-wall__spine-name" aria-hidden="true">{{ card.display_name }}</span>
      </button>
      <section v-else class="creation-wall__dossier">
        <p class="creation-wall__eyebrow">
          預設角色<span class="creation-wall__count">{{ pad(index + 1) }} / {{ total }}</span>
        </p>
        <h3 class="creation-wall__name" data-testid="creation-preset-name">{{ card.display_name }}</h3>
        <p class="creation-wall__race">
          <span>{{ raceDisplayName(card.race) }}</span>
          <span v-if="draftPresetKey === card.key" class="creation-wall__saved">
            <i aria-hidden="true"></i>目前草稿
          </span>
        </p>
        <p v-if="card.race_description" class="creation-wall__lineage">{{ card.race_description }}</p>
        <hr class="creation-wall__ornament" />
        <p class="creation-wall__emphasis">{{ card.emphasis }}</p>
        <p class="creation-wall__background">{{ card.background }}</p>
        <button
          type="button"
          class="ui-btn ui-btn--primary ui-btn--block creation-wall__choose"
          data-testid="creation-preset-choose"
          :disabled="disabled"
          @click="choose"
        >
          以{{ card.display_name }}啟程
        </button>
      </section>
    </div>
  </div>
</template>

<style scoped src="./creation-preset-wall.css"></style>
