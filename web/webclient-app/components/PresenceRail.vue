<script setup>
// PresenceRail (exploration-presence-rail; scene overview redesign §4.1): who
// and what is in the room, on the stage floor, right-aligned and inset left
// of the right-hand island column, mirroring the player standee on the left.
// Interact targets are gold medallions (the shared avatar renderer's real
// portrait crop, else the name's first grapheme), present
// entities without an interact descriptor are dashed muted medallions, and
// objects follow a thin separator as steel lozenges. Each entry has a name
// plate. At most six slots show; beyond six the sixth is `＋N`.
//
// One keyboard composite with one tab stop: DOM focus rests on the rail,
// which names its active entry through `aria-activedescendant`. ←/→ wrap,
// Home/End jump, Enter/Space activate (a held repeat never does). Hovering
// or focusing an entry lifts it and feeds the shared readout (`hover`).
// Passive: `activate(key)` is the only intent; the store decides what the
// entry does (open the verb card or the overflow card, or submit a look).
// An empty room renders no element at all.
import { computed, nextTick, ref, useId, watch } from "vue";
import AvatarArtwork from "./AvatarArtwork.vue";
import { portraitFor } from "./party-helpers.js";
import { railReadout, railSlots } from "./presence-rail.js";

const props = defineProps({
  // The committed rail entries (`store.view.presenceEntries`).
  entries: { type: Array, default: () => [] },
  // The committed `art` panel, for the portrait catalog.
  artPanel: { type: Object, default: null },
  // The EFFECTIVE motion level: at `off` entries appear and go at once.
  motionLevel: { type: String, default: "full" },
});

const emit = defineEmits(["activate", "hover", "tab"]);

const railRef = ref(null);
const idPrefix = useId();
const slots = computed(() => railSlots(props.entries));
const activeIndex = ref(0);
const focused = ref(false);
// The rendered items: every slot, with the separator standing before the
// first object slot (when anything precedes it).
const items = computed(() => {
  const out = [];
  slots.value.forEach((slot, index) => {
    if (slot.presence === "object" && index > 0 && slots.value[index - 1].presence !== "object") {
      out.push({ key: "presence-separator", separator: true });
    }
    out.push({ key: slot.key, slot, index });
  });
  return out;
});

watch(
  () => slots.value.length,
  (length) => {
    if (activeIndex.value > length - 1) {
      activeIndex.value = Math.max(0, length - 1);
    }
  },
);

function slotId(index) {
  return `${idPrefix}-slot-${index}`;
}

// The canonical descriptor the slot's committed reference names, or null for
// a slot that carries no reference at all (an object, the overflow chip, or an
// entity the art view does not admit). The reference itself is the admission
// fact, so an unadmitted slot is expected absence and a dangling one is a
// local failure — never a silently missing medallion.
function portrait(slot) {
  if (slot.presence === "object" || slot.presence === "more") {
    return null;
  }
  return portraitFor(props.artPanel, slot.portraitRef);
}

// The id the entry's own focusable/active-descendant node references for the
// medallion's compact failure explanation (see AvatarArtwork): the rail is a
// single-tab-stop composite, so the medallion never nests a second focusable
// control.
function failureTextId(index) {
  return `${slotId(index)}-failure`;
}

function readout(index) {
  emit("hover", railReadout(slots.value[index] || null));
}

function setActive(index) {
  activeIndex.value = index;
  readout(index);
}

function activate(index) {
  const slot = slots.value[index];
  if (slot) {
    emit("activate", slot.key);
  }
}

function onKeydown(event) {
  if (event.ctrlKey || event.altKey || event.metaKey) {
    return;
  }
  const count = slots.value.length;
  const key = event.key;
  if (key === "Tab") {
    emit("tab", { event, backward: !!event.shiftKey });
    return;
  }
  if (count === 0) {
    return;
  }
  if (key === "ArrowRight" || key === "ArrowLeft") {
    event.preventDefault();
    event.stopPropagation();
    const step = key === "ArrowRight" ? 1 : -1;
    setActive((activeIndex.value + step + count) % count);
    return;
  }
  if (key === "Home" || key === "End") {
    event.preventDefault();
    event.stopPropagation();
    setActive(key === "Home" ? 0 : count - 1);
    return;
  }
  if ((key === "Enter" || key === " ") && !event.shiftKey) {
    event.preventDefault();
    event.stopPropagation();
    if (!event.repeat) {
      activate(activeIndex.value);
    }
  }
}

function onFocus() {
  focused.value = true;
  readout(activeIndex.value);
}

function onBlur() {
  focused.value = false;
  emit("hover", null);
}

function onEnter(index) {
  setActive(index);
}

function onLeave() {
  if (focused.value) {
    readout(activeIndex.value);
  } else {
    emit("hover", null);
  }
}

function onClick(index) {
  railRef.value?.focus({ preventScroll: true });
  setActive(index);
  activate(index);
}

function focus() {
  railRef.value?.focus({ preventScroll: true });
}

// Focus the rail with the slot holding `key` active (the opener of a card
// that just closed); false when no slot carries it.
function focusEntry(key) {
  const index = slots.value.findIndex((slot) => slot.key === key);
  if (index < 0) {
    return false;
  }
  activeIndex.value = index;
  void nextTick(() => focus());
  focus();
  return true;
}

defineExpose({ focus, focusEntry });
</script>

<template>
  <div
    v-if="slots.length > 0"
    ref="railRef"
    class="presence-rail"
    role="listbox"
    aria-label="在場"
    aria-orientation="horizontal"
    tabindex="0"
    data-testid="presence-rail"
    :data-motion-level="motionLevel"
    :aria-activedescendant="slotId(activeIndex)"
    @keydown="onKeydown"
    @focus="onFocus"
    @blur="onBlur"
  >
    <TransitionGroup name="presence-entry" :css="motionLevel !== 'off'">
      <template v-for="item in items" :key="item.key">
        <span
          v-if="item.separator"
          class="presence-rail__sep"
          data-testid="presence-rail-separator"
          aria-hidden="true"
        ></span>
        <div
          v-else
          :id="slotId(item.index)"
          class="presence-rail__entry"
          :class="[
            `presence-rail__entry--${item.slot.presence}`,
            { 'presence-rail__entry--active': item.index === activeIndex },
          ]"
          role="option"
          :aria-selected="item.index === activeIndex ? 'true' : 'false'"
          :aria-label="item.slot.presence === 'more' ? `其餘 ${item.slot.count} 項` : item.slot.label"
          :aria-describedby="failureTextId(item.index)"
          data-testid="presence-entry"
          :data-entry-key="item.slot.key"
          :data-presence="item.slot.presence"
          @mouseenter="onEnter(item.index)"
          @mouseleave="onLeave"
          @click="onClick(item.index)"
        >
          <span class="presence-rail__digit" aria-hidden="true">{{ item.index + 1 }}</span>
          <span v-if="item.slot.presence === 'object'" class="presence-rail__gem" aria-hidden="true"></span>
          <span
            v-else-if="item.slot.presence === 'more'"
            class="presence-rail__medal presence-rail__medal--more"
            aria-hidden="true"
          >＋{{ item.slot.count }}</span>
          <span
            v-else
            class="presence-rail__medal"
            :class="{ 'presence-rail__medal--dashed': item.slot.presence === 'bystander' }"
          >
            <!-- The medallion itself is decorative, but its compact failure
                 explanation must stay in the accessibility tree: the entry
                 references it through `aria-describedby`, so it cannot sit in
                 an `aria-hidden` subtree. Every painted child here is itself
                 `aria-hidden`, so this exposes only that bounded sentence. -->
            <AvatarArtwork
              :artwork="portrait(item.slot)"
              :panel="artPanel"
              :has-reference="item.slot.portraitRef !== null && item.slot.portraitRef !== undefined"
              :name="item.slot.label"
              :failure-text-id="failureTextId(item.index)"
              face-test-id="presence-entry-face"
              initial-test-id="presence-entry-initial"
            />
          </span>
          <span class="presence-rail__name" data-testid="presence-entry-name">{{ item.slot.label }}</span>
        </div>
      </template>
    </TransitionGroup>
  </div>
</template>

<style>
.presence-rail {
  display: flex;
  align-items: flex-end;
  gap: calc(14px * var(--ui-scale));
  padding: calc(8px * var(--ui-scale)) calc(12px * var(--ui-scale)) calc(4px * var(--ui-scale));
  border-radius: var(--radius);
  outline: none;
  pointer-events: auto;
}

.presence-rail:focus-visible {
  box-shadow: 0 0 0 1px var(--gold-500);
  background: rgba(10, 11, 14, 0.35);
}

/* Entries fade in and out as the panel changes; a leaving entry is lifted
   out of flow so the rest close up at once. */
.presence-entry-enter-active,
.presence-entry-leave-active {
  transition: opacity var(--motion-reveal) var(--ease-standard);
}
.presence-entry-leave-active {
  position: absolute;
}
.presence-entry-enter-from,
.presence-entry-leave-to {
  opacity: 0;
}

.presence-rail__sep {
  align-self: center;
  width: 1px;
  height: calc(52px * var(--ui-scale));
  background: linear-gradient(transparent, #8a7550, transparent);
}

.presence-rail__entry {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: calc(4px * var(--ui-scale));
  cursor: pointer;
}

.presence-rail__medal {
  position: relative;
  box-sizing: border-box;
  width: calc(64px * var(--ui-scale));
  height: calc(64px * var(--ui-scale));
  border-radius: 50%;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--gold-500);
  background: radial-gradient(circle at 40% 35%, #3b3326, #16130f);
  box-shadow: 0 calc(6px * var(--ui-scale)) calc(16px * var(--ui-scale)) rgba(0, 0, 0, 0.6);
  font: var(--text-2xl) / 1 var(--f-display);
  color: var(--gold-300);
  transition:
    transform var(--motion-fast) var(--ease-standard),
    box-shadow var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard);
}

/* The shared avatar renderer fills the medallion; its bound zoom anchors the
   face-rect crop against this same clip. */
.presence-rail__medal .avatar-artwork {
  position: absolute;
  inset: 0;
}

.presence-rail__medal--dashed {
  border-style: dashed;
  border-color: #8c826e;
  color: var(--paper-300);
  background: radial-gradient(circle at 40% 35%, #2a2722, #121110);
}

.presence-rail__medal--dashed .avatar-artwork__figure {
  filter: saturate(0.55) brightness(0.85);
}

.presence-rail__medal--more {
  font: var(--text-md) / 1 var(--f-sans);
  border-color: #736b5c;
  color: var(--paper-200);
}

.presence-rail__gem {
  box-sizing: border-box;
  width: calc(36px * var(--ui-scale));
  height: calc(36px * var(--ui-scale));
  margin: calc(14px * var(--ui-scale)) 0;
  transform: rotate(45deg);
  border: 2px solid #9aa3ad;
  background: radial-gradient(circle at 40% 35%, #2c3138, #121519);
  box-shadow: 0 calc(6px * var(--ui-scale)) calc(16px * var(--ui-scale)) rgba(0, 0, 0, 0.6);
  transition:
    border-color var(--motion-fast) var(--ease-standard),
    box-shadow var(--motion-fast) var(--ease-standard);
}

.presence-rail__name {
  max-width: calc(120px * var(--ui-scale));
  padding: 0 calc(6px * var(--ui-scale));
  border-radius: var(--radius-sm);
  background: rgba(10, 11, 14, 0.78);
  font: var(--text-xs) / 1.5 var(--f-sans);
  color: var(--paper-100);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.presence-rail__digit {
  position: absolute;
  top: calc(-4px * var(--ui-scale));
  left: calc(-4px * var(--ui-scale));
  z-index: 1;
  box-sizing: border-box;
  min-width: calc(22px * var(--ui-scale));
  height: calc(22px * var(--ui-scale));
  border-radius: 50%;
  background: var(--ink-900);
  border: 1px solid #736b5c;
  font: var(--text-xs) / calc(20px * var(--ui-scale)) var(--f-sans);
  text-align: center;
  color: var(--paper-300);
  opacity: 0;
  transition: opacity var(--motion-fast) var(--ease-standard);
}

.presence-rail:focus-visible .presence-rail__digit,
.presence-rail__entry:hover .presence-rail__digit {
  opacity: 1;
}

/* Hover and the active entry while the rail holds focus: the medallion
   lifts and brightens; the lozenge brightens; the name plate gains a gold
   underline. The active entry is shown by shape and fill, never colour
   alone. */
.presence-rail:focus .presence-rail__entry--active .presence-rail__medal,
.presence-rail__entry:hover .presence-rail__medal {
  transform: translateY(calc(-4px * var(--ui-scale) * var(--motion-travel, 1)));
  border-color: var(--gold-300);
  box-shadow: 0 0 0 calc(3px * var(--ui-scale)) var(--gold-glow), 0 calc(8px * var(--ui-scale)) calc(20px * var(--ui-scale)) rgba(0, 0, 0, 0.6);
}

.presence-rail:focus .presence-rail__entry--active .presence-rail__gem,
.presence-rail__entry:hover .presence-rail__gem {
  border-color: #dfe7ef;
  box-shadow: 0 0 0 calc(3px * var(--ui-scale)) rgba(200, 215, 230, 0.2);
}

.presence-rail:focus .presence-rail__entry--active .presence-rail__name {
  color: var(--paper-50);
  box-shadow: inset 0 -2px 0 var(--gold-500);
}
</style>
