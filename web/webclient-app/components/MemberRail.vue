<script>
// The 空位 entry's selection value, outside the member id space (party
// member ids are positive integers).
export const EMPTY_SLOT = "empty";
</script>

<script setup>
// MemberRail (webclient-window-primitives, design §6/§9): the party window's
// and the shop's vertical member list. Entries keep the given order (the
// commander first, then companions in party order) and carry the portrait,
// the name, a ▼ 倒地 shape-and-text marker for a knocked-out member, and the
// session unread-unlock dot, whose meaning is spoken in the entry's
// accessible name. A dashed 空位 entry ends the rail while a slot is free.
//
// Selection follows activation, not focus (the IconTabs contract): the
// arrow keys, Home and End move a roving focus with wraparound; Enter,
// Space or a click selects. The selected entry carries `aria-current`.
// Selecting the 空位 entry emits `select(EMPTY_SLOT)`.
import { computed, nextTick, ref, watch } from "vue";
import { glyphAttrs, glyphPath } from "./dock-icons.js";

const props = defineProps({
  // [{ id, name, portrait (image URL | null), knockedOut, unread }]
  members: { type: Array, required: true },
  // The selected member id, EMPTY_SLOT, or null.
  selected: { type: [Number, String], default: null },
  emptySlot: { type: Boolean, default: false },
  // The member whose selection was requested but not yet adopted by the
  // server (webclient-party-window-member-tab): marked busy, never selected.
  pending: { type: [Number, String], default: null },
  ariaLabel: { type: String, default: "隊伍成員" },
});

const emit = defineEmits(["select"]);

const keys = computed(() => {
  const ids = props.members.map((member) => member.id);
  return props.emptySlot ? [...ids, EMPTY_SLOT] : ids;
});
const hasKey = (key) => key != null && keys.value.includes(key);

// The roving stop: the last focused entry, else the selected one, else the
// first, so the rail stays reachable when the selection is null or gone.
const focusKey = ref(props.selected);
const rovingKey = computed(() => {
  if (hasKey(focusKey.value)) return focusKey.value;
  if (hasKey(props.selected)) return props.selected;
  return keys.value[0] ?? null;
});

watch(
  () => props.selected,
  (value) => {
    focusKey.value = value;
  },
);

const initialOf = (name) => Array.from(name ?? "")[0] ?? "";

function accessibleName(member) {
  let name = member.name;
  if (member.knockedOut) name += "，倒地";
  if (member.unread) name += "，有新解鎖的技能";
  return name;
}

const buttons = new Map();
function setButton(key, el) {
  if (el) buttons.set(key, el);
  else buttons.delete(key);
}

function select(key) {
  if (!hasKey(key) || key === props.selected) return;
  emit("select", key);
}

async function focusEntry(key) {
  focusKey.value = key;
  await nextTick();
  buttons.get(key)?.focus();
}

function keyOf(event) {
  const el = event.target?.closest?.("[data-rail-index]");
  if (!el) return null;
  return keys.value[Number(el.dataset.railIndex)] ?? null;
}

function onKeydown(event) {
  if (event.altKey || event.ctrlKey || event.metaKey) return;
  const current = keyOf(event);
  if (current == null) return;
  const index = keys.value.indexOf(current);
  const last = keys.value.length - 1;
  let target = null;
  switch (event.key) {
    case "ArrowDown":
      target = index >= last ? 0 : index + 1;
      break;
    case "ArrowUp":
      target = index <= 0 ? last : index - 1;
      break;
    case "Home":
      target = 0;
      break;
    case "End":
      target = last;
      break;
    case "Enter":
    case " ":
      // Selected here, once; the click this keydown would synthesize is
      // cancelled (and Space's keyup click below).
      event.preventDefault();
      select(current);
      return;
    default:
      return;
  }
  event.preventDefault();
  focusEntry(keys.value[target]);
}

function onFocusin(event) {
  const key = keyOf(event);
  if (key != null) focusKey.value = key;
}

function onFocusout(event) {
  if (!event.currentTarget.contains(event.relatedTarget)) {
    focusKey.value = props.selected;
  }
}
</script>

<template>
  <nav
    class="member-rail"
    data-testid="member-rail"
    :aria-label="ariaLabel"
    @keydown="onKeydown"
    @focusin="onFocusin"
    @focusout="onFocusout"
  >
    <button
      v-for="(member, index) in members"
      :key="member.id"
      :ref="(el) => setButton(member.id, el)"
      type="button"
      class="member-rail__entry"
      :class="{ 'is-active': member.id === selected, 'is-down': member.knockedOut, 'is-pending': member.id === pending }"
      :data-rail-index="index"
      :data-testid="`member-rail__entry--${member.id}`"
      :tabindex="member.id === rovingKey ? 0 : -1"
      :aria-current="member.id === selected ? 'true' : undefined"
      :aria-busy="member.id === pending ? 'true' : undefined"
      :aria-label="accessibleName(member)"
      @click="select(member.id)"
      @keyup.space.prevent
    >
      <span class="member-rail__avatar" aria-hidden="true">
        <img v-if="member.portrait" class="member-rail__portrait" :src="member.portrait" alt="" />
        <template v-else>{{ initialOf(member.name) }}</template>
      </span>
      <span class="member-rail__name">{{ member.name }}</span>
      <span v-if="member.knockedOut" class="member-rail__down" data-testid="member-rail__down">
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path :d="glyphPath('knocked_out')" stroke="currentColor" stroke-width="1.6" v-bind="glyphAttrs('knocked_out')" />
        </svg>倒地
      </span>
      <span v-if="member.unread" class="member-rail__dot" data-testid="member-rail__dot" aria-hidden="true"></span>
    </button>
    <button
      v-if="emptySlot"
      :ref="(el) => setButton(EMPTY_SLOT, el)"
      type="button"
      class="member-rail__entry member-rail__entry--empty"
      :class="{ 'is-active': selected === EMPTY_SLOT }"
      :data-rail-index="members.length"
      data-testid="member-rail__entry--empty"
      :tabindex="rovingKey === EMPTY_SLOT ? 0 : -1"
      :aria-current="selected === EMPTY_SLOT ? 'true' : undefined"
      aria-label="空位"
      @click="select(EMPTY_SLOT)"
      @keyup.space.prevent
    >
      <span class="member-rail__avatar" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none">
          <path :d="glyphPath('plus')" stroke="currentColor" stroke-width="1.6" v-bind="glyphAttrs('plus')" />
        </svg>
      </span>
      <span class="member-rail__name">空位</span>
    </button>
  </nav>
</template>

<style scoped>
/* The approved prototype's `.pm-rail` / `.pm-avatar`
   (docs/design/party-member-management/prototype.css). The active entry
   opens into the list column beside it, like the IconTabs vertical rail. */
.member-rail {
  --member-rail-line: rgba(185, 154, 96, 0.28);
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  min-height: 0;
  overflow-y: auto;
  box-sizing: border-box;
  padding: var(--sp-4) 0 var(--sp-4) var(--sp-2);
  background: rgba(0, 0, 0, 0.28);
  border-right: calc(1px * var(--ui-scale)) solid var(--member-rail-line);
  scrollbar-width: none;
}

.member-rail__entry {
  position: relative;
  display: grid;
  justify-items: center;
  gap: calc(2px * var(--ui-scale));
  flex: none;
  box-sizing: border-box;
  margin-right: calc(-1px * var(--ui-scale));
  padding: var(--sp-2) calc(2px * var(--ui-scale));
  color: var(--paper-500);
  font: var(--text-xs) var(--f-sans);
  background: transparent;
  border: calc(1px * var(--ui-scale)) solid transparent;
  border-right: 0;
  border-radius: var(--radius) 0 0 var(--radius);
  cursor: pointer;
  transition: color var(--motion-fast) ease, background-color var(--motion-fast) ease;
}

.member-rail__entry:hover {
  color: var(--paper-100);
  background: rgba(255, 255, 255, 0.03);
}

.member-rail__entry:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.member-rail__entry.is-active {
  color: var(--gold-300);
  background: var(--member-rail-active-bg, #15171c);
  border-color: var(--member-rail-line);
}

.member-rail__entry.is-active::before {
  content: "";
  position: absolute;
  left: calc(-1px * var(--ui-scale));
  top: 22%;
  bottom: 22%;
  width: calc(3px * var(--ui-scale));
  background: var(--seal-500);
  border-radius: 0 calc(2px * var(--ui-scale)) calc(2px * var(--ui-scale)) 0;
  box-shadow: 0 0 calc(8px * var(--ui-scale)) var(--seal-glow);
}

.member-rail__avatar {
  display: grid;
  place-items: center;
  flex: none;
  box-sizing: border-box;
  width: calc(40px * var(--ui-scale));
  height: calc(40px * var(--ui-scale));
  overflow: hidden;
  color: var(--paper-100);
  font: var(--text-md) var(--f-serif);
  background: radial-gradient(circle at 50% 30%, #3a332a, #16181c);
  border: calc(1px * var(--ui-scale)) solid var(--gold-600);
  border-radius: 50%;
}

.member-rail__portrait {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center top;
}

.member-rail__entry.is-active .member-rail__avatar {
  border-color: var(--gold-400);
  box-shadow: 0 0 calc(8px * var(--ui-scale)) rgba(228, 200, 142, 0.35);
}

.member-rail__entry.is-pending {
  color: var(--paper-300);
  opacity: 0.7;
}

.member-rail__entry.is-pending .member-rail__avatar {
  border-style: dashed;
}

.member-rail__entry.is-down .member-rail__avatar {
  filter: grayscale(0.8) brightness(0.7);
}

.member-rail__name {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.member-rail__down {
  display: flex;
  align-items: center;
  gap: calc(1px * var(--ui-scale));
  color: var(--seal-400);
  font-size: var(--text-xs);
}

.member-rail__down svg,
.member-rail__entry--empty .member-rail__avatar svg {
  width: 1em;
  height: 1em;
}

.member-rail__dot {
  position: absolute;
  top: calc(6px * var(--ui-scale));
  right: calc(8px * var(--ui-scale));
  width: calc(9px * var(--ui-scale));
  height: calc(9px * var(--ui-scale));
  border-radius: 50%;
  background: var(--seal-500);
  box-shadow: 0 0 calc(6px * var(--ui-scale)) var(--seal-glow);
}

.member-rail__entry--empty .member-rail__avatar {
  color: var(--paper-700);
  font-size: var(--text-lg);
  background: none;
  border-style: dashed;
}

@media (prefers-reduced-motion: reduce) {
  .member-rail__entry {
    transition: none;
  }
}
</style>
