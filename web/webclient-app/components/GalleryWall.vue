<script setup>
// GalleryWall (change gallery-wall-component; gallery window design D4/D9,
// after the prototype docs/design/gallery-window/GalleryWall.vue). The
// gallery window's centre: the selected category's committed groups drawn as
// aspect-true subject tiles (9:16 portraits, 16:9 scenes), and — when the
// selected subject's committed capabilities allow more than one card — an
// inline tray of that subject's images directly under its row.
//
// Two roving listboxes. The wall is one listbox with one tab stop: the arrow
// keys, Home and End move focus in reading order across groups (Up/Down by
// the measured column count, as TileWall does) and Enter, Space or a click
// select a subject. The tray is a second listbox with its own tab stop
// directly after the wall; Escape inside it returns focus to the owner tile.
//
// The tray must sit between two rows of the owner's group, yet a listbox may
// own only options and groups. So the wall is drawn in two runs: the first
// run (inside the wall listbox) ends with the owner's row, the tray follows as
// a sibling listbox, and the rest of the wall continues in a second run that
// the wall listbox adopts through `aria-owns`. Both runs share one grid
// template, so the split is invisible.
//
// A paged category (people) commits one group expanded and the others
// collapsed to a count. While any committed group is collapsed, every
// labelled heading is a button with `aria-expanded`, and a collapsed one asks
// for its expansion (`expand-group`). Those buttons are ordinary tab stops
// outside the wall listbox: the listbox role moves from the run onto the tile
// sets, each a named group of options, so the headings never sit inside it.
//
// The wall emits; it never dispatches. It renders committed facts only.
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";

import ArtworkPreview from "./ArtworkPreview.vue";
import EmptyState from "./EmptyState.vue";
import { GALLERY_OFFICIAL_LABEL, galleryCardName, galleryOfficialName } from "./gallery-copy.js";
import { GENERATE_TILE, tileShape, trayInsertIndex, trayItems, trayOpen, wallTiles } from "./gallery-window-model.js";

const props = defineProps({
  groups: { type: Array, required: true },
  selectedSubject: { type: String, default: null },
  cards: { type: Array, default: () => [] },
  officialEntries: { type: Array, default: () => [] },
  capabilities: { type: Object, default: null },
  selectedImage: { type: String, default: null },
  panel: { type: Object, default: null },
  ariaLabel: { type: String, required: true },
  pendingSubject: { type: String, default: null },
  pendingGroup: { type: String, default: null },
});
const emit = defineEmits(["select-subject", "select-image", "generate", "focus-lost", "expand-group"]);

const uid = useId();
const wallId = `${uid}-wall`;
const trayId = `${uid}-tray`;
const restId = (key) => `${uid}-rest-${key}`;
const setId = (key) => `${uid}-set-${key}`;

const OFFICIAL_RUN_LABEL = `${GALLERY_OFFICIAL_LABEL}（唯讀）`;

// ---- the wall's tiles and the tray's placement ------------------------------

const tiles = computed(() => wallTiles(props.groups));
const tileKeys = computed(() => tiles.value.map((tile) => tile.subject.subject_key));

const owner = computed(() => tiles.value.find((tile) => tile.subject.subject_key === props.selectedSubject) ?? null);
const trayShown = computed(() => owner.value !== null && trayOpen(props.capabilities));
const ownerKey = computed(() => (trayShown.value ? owner.value.subject.subject_key : null));

// The measured column count of the owner's group grid (null until measured;
// the tray then follows the owner itself until the first measure lands).
const columns = ref(null);

function groupShape(group) {
  return group.subjects.some((subject) => tileShape(subject.kind) === "landscape") ? "landscape" : "portrait";
}

// Headings are buttons while any committed group is collapsed (people).
const collapsible = computed(() => props.groups.some((group) => !group.expanded));

function groupCounts(group) {
  if (!group.expanded) return { kind: "count", text: `共 ${group.count}` };
  if (group.seen !== null && group.total !== null) return { kind: "seen", text: `${group.seen} / ${group.total}` };
  // Beside collapsed places, the expanded one carries its count too.
  if (collapsible.value) return { kind: "count", text: `共 ${group.count}` };
  return null;
}

function groupName(group) {
  const counts = group.label === null ? null : groupCounts(group);
  return group.label === null ? props.ariaLabel : counts ? `${group.label}，${counts.text}` : group.label;
}

// The wall's parts: one per group, split after the owner's row when the tray
// is open. `head` is false for the continuation of a split group.
const parts = computed(() => {
  const all = props.groups.map((group) => ({
    key: group.key,
    group,
    head: true,
    subjects: group.expanded ? group.subjects : [],
  }));
  if (!trayShown.value) return { first: all, rest: [] };
  const groupIndex = all.findIndex((part) => part.key === owner.value.groupKey);
  const part = all[groupIndex];
  const ownerIndex = part.subjects.findIndex((subject) => subject.subject_key === ownerKey.value);
  const insert = trayInsertIndex(ownerIndex, columns.value ?? 1, part.subjects.length);
  const first = [...all.slice(0, groupIndex), { ...part, subjects: part.subjects.slice(0, insert + 1) }];
  const tail = part.subjects.slice(insert + 1);
  const rest = [
    ...(tail.length ? [{ ...part, key: `${part.key}:rest`, head: false, subjects: tail }] : []),
    ...all.slice(groupIndex + 1),
  ];
  return { first, rest };
});

const ownsRest = computed(() => (parts.value.rest.length ? parts.value.rest.map((part) => restId(part.key)).join(" ") : undefined));

// The wall's runs in DOM order: the wall listbox, the tray, and the rest of
// the wall that the listbox adopts. Only the first run carries the role.
const runs = computed(() => [
  { kind: "wall", key: "first", parts: parts.value.first },
  ...(trayShown.value ? [{ kind: "tray", key: `tray:${ownerKey.value}` }] : []),
  ...(parts.value.rest.length ? [{ kind: "wall", key: "rest", parts: parts.value.rest }] : []),
]);

// The tile sets in DOM order, across both runs. With collapsible headings
// the first set carries the wall listbox, which adopts every later set.
const tileSets = computed(() => [...parts.value.first, ...parts.value.rest].filter((part) => part.subjects.length));

function runAttrs(run) {
  if (run.key !== "first") return { class: "gwall__run gwall__run--rest" };
  if (collapsible.value) return { class: "gwall__run" };
  // With every group collapsed there is no option, so no empty listbox.
  if (!tileKeys.value.length) return { class: "gwall__run", id: wallId, role: "group", "aria-label": props.ariaLabel };
  return { class: "gwall__run", id: wallId, role: "listbox", "aria-label": props.ariaLabel, "aria-owns": ownsRest.value };
}

// In collapsible mode a part's tiles sit in two wrappers: the outer one is the
// wall listbox on the first set (plain elsewhere), the inner one names the
// group. Without collapsible headings the run is the listbox and both stay
// plain.
function tilesAttrs(part) {
  if (!collapsible.value || tileSets.value[0]?.key !== part.key) return { class: "gwall__tiles" };
  const owned = tileSets.value.slice(1).map((set) => setId(set.key));
  return {
    class: "gwall__tiles",
    id: wallId,
    role: "listbox",
    "aria-label": props.ariaLabel,
    "aria-owns": owned.length ? owned.join(" ") : undefined,
  };
}

function setAttrs(part) {
  if (!collapsible.value) return { class: "gwall__set" };
  return { class: "gwall__set", id: setId(part.key), role: "group", "aria-label": groupName(part.group) };
}

function sectionAttrs(part) {
  const base = { id: restId(part.key), class: ["gwall__group", { "gwall__group--continued": !part.head }] };
  if (collapsible.value) return base;
  return { ...base, role: "group", "aria-label": groupName(part.group) };
}

// Only a collapsed heading asks for its expansion; the expanded one is inert.
function expandGroup(group) {
  if (!group.expanded) emit("expand-group", group.key);
}

// ---- element registry -----------------------------------------------------

const root = ref(null);
const trayEl = ref(null);
const notchX = ref(null);
const reach = ref(null);
const tileEls = new Map();
const trayEls = new Map();

function setTileEl(key, el) {
  if (el) tileEls.set(key, el);
  else tileEls.delete(key);
}
function setTrayEl(id, el) {
  if (el) trayEls.set(id, el);
  else trayEls.delete(id);
}

// ---- tile names -------------------------------------------------------------

function tileLabel(subject) {
  let name = subject.display_name;
  if (subject.is_current) name += "，操作中";
  if (subject.card_count > 1) name += `（${subject.card_count} 張）`;
  return name;
}

const STATUS_TEXT = { pending: "生成中", failed: "生成失敗" };

function trayLabel(item) {
  if (item.kind === "generate") return "生成新圖";
  if (item.kind === "official") return galleryOfficialName(item.row);
  let name = galleryCardName(item.row);
  if (item.row.is_default) name += "，預設";
  if (STATUS_TEXT[item.row.status]) name += `，${STATUS_TEXT[item.row.status]}`;
  return name;
}

// ---- the wall listbox: one roving tab stop ---------------------------------

const focusKey = ref(null);
const rovingKey = computed(() => {
  const keys = tileKeys.value;
  if (focusKey.value && keys.includes(focusKey.value)) return focusKey.value;
  if (props.selectedSubject && keys.includes(props.selectedSubject)) return props.selectedSubject;
  return keys[0] ?? null;
});

// The resolved track count of a grid, or null while it is unresolved (a
// hidden or not yet laid out grid reports its `repeat(auto-fill, …)` source).
function trackCount(grid) {
  const tracks = grid ? getComputedStyle(grid).gridTemplateColumns ?? "" : "";
  if (!tracks || tracks.includes("(")) return null;
  return tracks.split(" ").filter(Boolean).length || null;
}

function columnsOf(el) {
  return trackCount(el?.parentElement) ?? columns.value ?? 1;
}

async function focusTile(key) {
  if (!key) return;
  focusKey.value = key;
  await nextTick();
  tileEls.get(key)?.focus();
}

function selectSubject(key) {
  focusKey.value = key;
  emit("select-subject", key);
}

function isWallTile(el) {
  return !!el?.closest?.('[data-testid="gallery-subject"]') && root.value?.contains(el);
}

function onWallKeydown(event) {
  // The tray handles its own keys; only a wall tile drives the wall.
  if (!isWallTile(event.target)) return;
  const keys = tileKeys.value;
  const index = keys.indexOf(rovingKey.value);
  if (index < 0) return;
  const cols = columnsOf(tileEls.get(keys[index]));
  const moves = {
    ArrowRight: index + 1,
    ArrowLeft: index - 1,
    ArrowDown: index + cols,
    ArrowUp: index - cols,
    Home: 0,
    End: keys.length - 1,
  };
  if (event.key in moves) {
    event.preventDefault();
    focusTile(keys[Math.max(0, Math.min(keys.length - 1, moves[event.key]))]);
  } else if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    selectSubject(keys[index]);
  }
}

// Leaving the wall returns its tab stop to the selected tile, which always
// precedes the tray, so the tray stays directly after the wall in tab order.
// A window blur keeps the stop where it is.
function onWallFocusout(event) {
  if (isWallTile(event.relatedTarget)) return;
  if (typeof document.hasFocus === "function" && !document.hasFocus()) return;
  focusKey.value = null;
}

// ---- the tray listbox -------------------------------------------------------

const items = computed(() => (trayShown.value ? trayItems(props.cards, props.officialEntries) : []));
const runItems = computed(() => items.value.filter((item) => item.kind !== "official"));
const officialItems = computed(() => items.value.filter((item) => item.kind === "official"));

const trayFocusId = ref(null);
const trayRovingId = computed(() => {
  const ids = items.value.map((item) => item.id);
  if (trayFocusId.value && ids.includes(trayFocusId.value)) return trayFocusId.value;
  if (props.selectedImage && ids.includes(props.selectedImage)) return props.selectedImage;
  return ids[0] ?? null;
});

async function focusTrayItem(id) {
  trayFocusId.value = id;
  await nextTick();
  trayEls.get(id)?.focus();
}

function activate(item) {
  trayFocusId.value = item.id;
  if (item.kind === "generate") emit("generate");
  else emit("select-image", item.id);
}

function focusOwnerTile() {
  if (ownerKey.value) focusTile(ownerKey.value);
}

function onTrayKeydown(event) {
  const list = items.value;
  const index = list.findIndex((item) => item.id === trayRovingId.value);
  if (event.key === "Escape") {
    // Back to the owner tile; nothing closes, and the window never sees it.
    event.stopPropagation();
    event.preventDefault();
    focusOwnerTile();
    return;
  }
  if (index < 0) return;
  const moves = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: list.length - 1 };
  if (event.key in moves) {
    event.preventDefault();
    event.stopPropagation();
    focusTrayItem(list[Math.max(0, Math.min(list.length - 1, moves[event.key]))].id);
  } else if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    event.stopPropagation();
    activate(list[index]);
  }
}

function onTrayFocusout(event) {
  if (trayEl.value?.contains(event.relatedTarget)) return;
  if (typeof document.hasFocus === "function" && !document.hasFocus()) return;
  trayFocusId.value = null;
}

// ---- measuring: columns and the notch -------------------------------------

function ownerGrid() {
  if (!ownerKey.value) return null;
  return tileEls.get(ownerKey.value)?.parentElement ?? null;
}

function placeNotch() {
  const tile = ownerKey.value ? tileEls.get(ownerKey.value) : null;
  if (!tile || !trayEl.value) {
    notchX.value = null;
    reach.value = null;
    return;
  }
  const tileBox = tile.getBoundingClientRect();
  const trayBox = trayEl.value.getBoundingClientRect();
  notchX.value = tileBox.left + tileBox.width / 2 - trayBox.left;
  // How far above the tray the owner tile starts: a tray taller than the
  // wall scrolls into view with its owner still showing above it.
  reach.value = Math.max(0, trayBox.top - tileBox.top);
}

async function measure() {
  const count = trackCount(ownerGrid());
  if (count !== null) {
    if (count !== columns.value) {
      columns.value = count;
      await nextTick();
    }
  }
  placeNotch();
}

const trayStyle = computed(() => (notchX.value === null ? undefined : {
  "--tray-notch-x": `${notchX.value}px`,
  "--tray-reach": `${reach.value}px`,
}));

function scrollBehavior() {
  const level = document.documentElement?.dataset?.motion;
  const reduce = typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  return reduce || level === "off" || level === "reduced" ? "auto" : "smooth";
}

// Opening a tray (or moving it to another owner) scrolls it into view; a
// re-measure alone never scrolls.
async function revealTray() {
  if (!ownerKey.value) return;
  await measure();
  trayEl.value?.scrollIntoView?.({ block: "nearest", behavior: scrollBehavior() });
}
watch(ownerKey, revealTray, { flush: "post" });

watch(() => [props.groups, props.selectedSubject, props.capabilities], () => measure(), { flush: "post" });

let observer = null;
onMounted(() => {
  revealTray();
  if (typeof ResizeObserver === "function" && root.value) {
    observer = new ResizeObserver(() => measure());
    observer.observe(root.value);
  }
});
onBeforeUnmount(() => observer?.disconnect());

// ---- focus across commits ---------------------------------------------------

// Runs before the DOM patch, while the focused element still stands. If the
// focused tile's subject (or the focused tray's owner) is absent from the new
// groups, the wall reports the loss once; the host moves focus.
watch(() => props.groups, (next) => {
  const active = document.activeElement;
  if (!root.value || !active || !root.value.contains(active)) return;
  const key = active.closest('[data-testid="gallery-subject"]')?.dataset.subjectKey
    ?? active.closest("[data-owner-key]")?.dataset.ownerKey;
  if (!key) return;
  if (!wallTiles(next).some((tile) => tile.subject.subject_key === key)) {
    focusKey.value = null;
    trayFocusId.value = null;
    reportedLoss = true;
    nextTick(() => { reportedLoss = false; });
    emit("focus-lost");
  }
});

// Focus keeper. A tile that crosses between the wall's runs (the owner's row
// moves when the selection or the column count changes) is remounted, and a
// tray item can leave the tray, so a patch may drop focus to the document.
// Before the patch, remember what held focus; after it, if focus fell out of
// the wall, put it back: the same tile, else the same tray item, else the
// tray's roving item, else the current or previous owner tile. A focus loss
// the wall has already reported (focus-lost) is left to the host.
let reportedLoss = false;
watch([parts, items], () => {
  const active = document.activeElement;
  if (reportedLoss || !root.value || !active || !root.value.contains(active)) return;
  const tileKey = active.closest('[data-testid="gallery-subject"]')?.dataset.subjectKey ?? null;
  const itemId = active.closest('[data-testid="gallery-tray-item"]')?.dataset.itemId ?? null;
  const previousOwner = active.closest("[data-owner-key]")?.dataset.ownerKey ?? null;
  const headKey = active.closest("[data-group-key]")?.dataset.groupKey ?? null;
  nextTick(() => {
    if (root.value?.contains(document.activeElement)) return;
    if (headKey) {
      // A heading whose section crossed between the runs is remounted. It is
      // found in the patched DOM: a moved section mounts its new heading
      // before (or after) the old one unmounts, so no element map can tell.
      // A heading that is gone falls through to the owner tile or the wall's
      // tab stop below.
      const heading = [...(root.value?.querySelectorAll("[data-group-key]") ?? [])].find((el) => el.dataset.groupKey === headKey);
      if (heading) {
        heading.focus();
        return;
      }
    }
    if (tileKey) {
      if (tileKeys.value.includes(tileKey)) focusTile(tileKey);
      return;
    }
    if (trayShown.value && ownerKey.value === previousOwner) {
      const id = trayEls.has(itemId) ? itemId : trayRovingId.value;
      if (id) {
        focusTrayItem(id);
        return;
      }
    }
    if (ownerKey.value) focusTile(ownerKey.value);
    else if (previousOwner && tileKeys.value.includes(previousOwner)) focusTile(previousOwner);
    // A vanished heading with no tray to fall back on: the wall's tab stop.
    else if (headKey && rovingKey.value) focusTile(rovingKey.value);
  });
}, { flush: "pre" });

defineExpose({
  focusOwner() {
    const key = props.selectedSubject && tileKeys.value.includes(props.selectedSubject)
      ? props.selectedSubject
      : rovingKey.value;
    return focusTile(key);
  },
  focusFirst() {
    return focusTile(tileKeys.value[0] ?? null);
  },
});
</script>


<template>
  <div ref="root" class="gwall" :class="{ 'gwall--paged': collapsible }" data-testid="gallery-wall" @keydown="onWallKeydown" @focusout="onWallFocusout">
    <EmptyState v-if="!groups.length" class="gwall__empty" glyph="gallery" headline="此分類目前沒有可顯示的圖像" />
    <template v-for="run in groups.length ? runs : []" :key="run.key">
      <div
        v-if="run.kind === 'tray'"
        :id="trayId"
        :ref="(el) => (trayEl = el)"
        class="gtray"
        :class="`gtray--${tileShape(owner.subject.kind)}`"
        role="listbox"
        :aria-label="`${owner.subject.display_name}的圖片`"
        :data-owner-key="ownerKey"
        data-testid="gallery-tray"
        :style="trayStyle"
        @keydown="onTrayKeydown"
        @focusout="onTrayFocusout"
      >
        <span class="gtray__notch" aria-hidden="true"></span>
        <div class="gwall__grid gtray__grid" :class="`gwall__grid--${tileShape(owner.subject.kind)}`">
          <div
            v-for="item in runItems"
            :key="item.id"
            :ref="(el) => setTrayEl(item.id, el)"
            role="option"
            class="gtile gtile--image"
            :class="[
              `gtile--${tileShape(owner.subject.kind)}`,
              item.kind === 'generate' ? 'gtile--new' : `is-${item.row.status}`,
              { 'is-selected': item.id === selectedImage },
            ]"
            data-testid="gallery-tray-item"
            :data-item-kind="item.kind"
            :data-item-id="item.id"
            :tabindex="item.id === trayRovingId ? 0 : -1"
            :aria-selected="String(item.id === selectedImage)"
            :aria-label="trayLabel(item)"
            @click="activate(item)"
            @focus="trayFocusId = item.id"
          >
            <template v-if="item.kind === 'generate'">
              <span class="gtile__plus" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none"><path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" /></svg>
              </span>
              <span class="gtile__new-text">生成新圖</span>
            </template>
            <template v-else>
              <ArtworkPreview
                v-if="item.row.status === 'card'"
                class="gtile__art"
                :artwork="item.row.artwork"
                :panel="panel"
                :view-subject-id="item.id"
                alt=""
              />
              <span v-else class="gtile__status" :data-status="item.row.status">
                <svg v-if="item.row.status === 'pending'" class="gtile__spin" data-mark="spinner" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <circle cx="12" cy="12" r="8.5" stroke="currentColor" stroke-opacity="0.25" stroke-width="1.6" />
                  <path d="M12 3.5a8.5 8.5 0 0 1 8.5 8.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                </svg>
                <svg v-else data-mark="warning" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M12 3.8 21.2 19.6H2.8z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
                  <path d="M12 9.6v4.8M12 16.8v.4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                </svg>
                <span class="gtile__status-text">{{ STATUS_TEXT[item.row.status] }}</span>
              </span>
              <span v-if="item.row.is_default" class="gtile__crown">
                <svg data-mark="crown" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3 8l4.5 4L12 5l4.5 7L21 8l-2 11H5z" /></svg>預設
              </span>
            </template>
          </div>
        </div>
        <div v-if="officialItems.length" class="gtray__official" role="group" :aria-label="OFFICIAL_RUN_LABEL" data-testid="gallery-tray-official">
          <p class="gtray__label" aria-hidden="true">
            <span>{{ GALLERY_OFFICIAL_LABEL }}</span>
            <span class="gtray__readonly">
              <svg viewBox="0 0 24 24" fill="none"><path d="M7 11V8a5 5 0 0 1 10 0v3M5.5 11h13v9.5h-13z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" /></svg>唯讀
            </span>
            <span class="gwall__rule"></span>
          </p>
          <div class="gwall__grid gtray__grid" :class="`gwall__grid--${tileShape(owner.subject.kind)}`">
            <div
              v-for="item in officialItems"
              :key="item.id"
              :ref="(el) => setTrayEl(item.id, el)"
              role="option"
              class="gtile gtile--image gtile--official"
              :class="[`gtile--${tileShape(owner.subject.kind)}`, { 'is-selected': item.id === selectedImage }]"
              data-testid="gallery-tray-item"
              data-item-kind="official"
              :data-item-id="item.id"
              :tabindex="item.id === trayRovingId ? 0 : -1"
              :aria-selected="String(item.id === selectedImage)"
              :aria-label="trayLabel(item)"
              @click="activate(item)"
              @focus="trayFocusId = item.id"
            >
              <ArtworkPreview class="gtile__art" :artwork="item.row.artwork" :panel="panel" :view-subject-id="item.id" alt="" />
            </div>
          </div>
        </div>
      </div>

      <div v-else v-bind="runAttrs(run)">
        <section v-for="part in run.parts" :key="part.key" v-bind="sectionAttrs(part)">
          <h3 v-if="part.head && part.group.label !== null && collapsible" class="gwall__head gwall__head--toggle">
            <button
              type="button"
              class="gwall__toggle"
              :class="{ 'is-busy': part.group.key === pendingGroup }"
              data-testid="gallery-group-head"
              :data-group-key="part.group.key"
              :aria-expanded="String(part.group.expanded)"
              :aria-busy="part.group.key === pendingGroup ? 'true' : undefined"
              :aria-label="groupName(part.group)"
              @click="expandGroup(part.group)"
            >
              <svg class="gwall__chevron" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M9 6l6 6-6 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
              <span class="gwall__label">{{ part.group.label }}</span>
              <span class="gwall__rule" aria-hidden="true"></span>
              <span class="gwall__n" data-count="count">共 <b>{{ part.group.count }}</b></span>
              <span v-if="part.group.key === pendingGroup" class="gwall__toggle-busy" aria-hidden="true"></span>
            </button>
          </h3>
          <h3 v-else-if="part.head && part.group.label !== null" class="gwall__head" aria-hidden="true">
            <span class="gwall__label">{{ part.group.label }}</span>
            <span class="gwall__rule"></span>
            <span v-if="groupCounts(part.group)" class="gwall__n" :data-count="groupCounts(part.group).kind">
              <template v-if="groupCounts(part.group).kind === 'seen'"><b>{{ part.group.seen }}</b> / {{ part.group.total }}</template>
              <template v-else>共 <b>{{ part.group.count }}</b></template>
            </span>
          </h3>
          <div v-if="part.subjects.length" v-bind="tilesAttrs(part)"><div v-bind="setAttrs(part)">
          <div class="gwall__grid" :class="`gwall__grid--${groupShape(part.group)}`">
            <div
              v-for="subject in part.subjects"
              :key="subject.subject_key"
              :ref="(el) => setTileEl(subject.subject_key, el)"
              role="option"
              class="gtile"
              :class="[
                `gtile--${tileShape(subject.kind)}`,
                {
                  'is-selected': subject.subject_key === selectedSubject,
                  'is-open': subject.subject_key === ownerKey,
                  'is-busy': subject.subject_key === pendingSubject,
                },
              ]"
              data-testid="gallery-subject"
              :data-subject-key="subject.subject_key"
              :tabindex="subject.subject_key === rovingKey ? 0 : -1"
              :aria-selected="String(subject.subject_key === selectedSubject)"
              :aria-expanded="subject.subject_key === ownerKey ? 'true' : undefined"
              :aria-controls="subject.subject_key === ownerKey ? trayId : undefined"
              :aria-busy="subject.subject_key === pendingSubject ? 'true' : undefined"
              :aria-label="tileLabel(subject)"
              @click="selectSubject(subject.subject_key)"
              @focus="focusKey = subject.subject_key"
            >
              <ArtworkPreview
                v-if="subject.artwork"
                class="gtile__art"
                :artwork="subject.artwork"
                :panel="panel"
                :view-subject-id="subject.subject_key"
                alt=""
              />
              <span v-else class="gtile__blank" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none">
                  <path d="M12 3.5c2.5 0 4 1.9 4 4.3S14.5 12.5 12 12.5 8 10.2 8 7.8 9.5 3.5 12 3.5zM4.5 20.5c.8-4 3.8-6.2 7.5-6.2s6.7 2.2 7.5 6.2" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" />
                </svg>
                <span>尚無圖片</span>
              </span>
              <span v-if="subject.is_current" class="gtile__current">操作中</span>
              <span v-if="subject.card_count > 1" class="gtile__count" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none"><path d="M8.5 4.5h10v13M5.5 7.5h10v12h-10z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" /></svg>{{ subject.card_count }}
              </span>
              <span class="gtile__name">{{ subject.display_name }}</span>
              <span v-if="subject.subject_key === pendingSubject" class="gtile__busy" aria-hidden="true"></span>
            </div>
          </div>
          </div></div>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
/* The wall: a scroller whose gutter is always reserved, so a wall that grows
   past one page never reflows its tiles when the scrollbar appears. */
.gwall {
  --gwall-gap: var(--sp-2);
  --gwall-line: rgba(185, 154, 96, 0.28);
  --gwall-hair: calc(1px * var(--ui-scale));
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  height: 100%;
  box-sizing: border-box;
  overflow-y: auto;
  padding: var(--sp-4) var(--sp-4) var(--sp-6);
  background:
    radial-gradient(ellipse at 50% 0%, rgba(185, 154, 96, 0.06), transparent 60%),
    var(--ink-860);
  border-right: var(--gwall-hair) solid var(--gwall-line);
  scrollbar-width: thin;
  scrollbar-color: var(--ink-600) transparent;
  scrollbar-gutter: stable;
}

.gwall__empty {
  margin: auto;
}

.gwall__run {
  display: flex;
  flex-direction: column;
  gap: var(--sp-5);
}

/* A paged category reads as one list of places: the collapsed headings sit
   close together, like the prototype's place list. */
.gwall--paged .gwall__run {
  gap: var(--sp-2);
}

/* The rest of a split wall: its first part continues the owner's group right
   under the tray, while a new group keeps the usual spacing. */
.gwall__run--rest > .gwall__group:first-child:not(.gwall__group--continued) {
  margin-top: var(--sp-3);
}

.gwall__group {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  min-width: 0;
}

.gwall__head {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  margin: 0;
  color: var(--gold-400);
  font: var(--text-md) / 1.4 var(--f-display);
  letter-spacing: 0.12em;
}

.gwall__label {
  flex: none;
}

/* ---- collapsible headings (a paged category's places) ---- */

/* A place heading is a full-width toggle: a chevron that turns down on the
   expanded place, the label, the rule and the count. The expanded place
   reads in gold with a seal-gold edge; a collapsed one stays quiet until
   hovered. Shape (the chevron's turn) carries the state beside colour. */
.gwall__head--toggle {
  display: block;
}

.gwall__toggle {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  width: 100%;
  min-height: calc(44px * var(--ui-scale));
  box-sizing: border-box;
  padding: var(--sp-2) var(--sp-3);
  overflow: hidden;
  color: var(--paper-300);
  font: var(--text-md) / 1.4 var(--f-display);
  letter-spacing: 0.12em;
  text-align: left;
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.06), rgba(0, 0, 0, 0.2));
  border: var(--gwall-hair) solid rgba(185, 154, 96, 0.22);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition:
    color var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard),
    background-color var(--motion-fast) var(--ease-standard);
}

.gwall__toggle:hover {
  color: var(--gold-300);
  border-color: var(--gold-500);
  background-color: rgba(185, 154, 96, 0.1);
}

.gwall__toggle:focus-visible {
  outline: calc(2px * var(--ui-scale)) solid var(--gold-400);
  outline-offset: calc(2px * var(--ui-scale));
}

.gwall__toggle[aria-expanded="true"] {
  color: var(--gold-300);
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.18), rgba(185, 154, 96, 0.03) 70%);
  border-color: var(--gold-500);
  box-shadow: inset calc(3px * var(--ui-scale)) 0 0 var(--gold-400);
  cursor: default;
}

.gwall__chevron {
  flex: none;
  width: calc(16px * var(--ui-scale));
  height: calc(16px * var(--ui-scale));
  color: var(--gold-500);
  transition: transform var(--motion-fast) var(--ease-standard);
}

.gwall__toggle[aria-expanded="true"] .gwall__chevron {
  color: var(--gold-300);
  transform: rotate(90deg);
}

.gwall__toggle .gwall__n {
  color: var(--paper-400);
}

/* A place whose expansion is in flight: the tiles' sweeping bar along the
   heading's bottom edge, beside aria-busy. */
.gwall__toggle.is-busy {
  border-color: var(--gold-400);
}

.gwall__toggle-busy {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: calc(3px * var(--ui-scale));
  overflow: hidden;
  background: rgba(228, 200, 142, 0.25);
  pointer-events: none;
}

.gwall__toggle-busy::after {
  content: "";
  position: absolute;
  inset: 0;
  width: 40%;
  background: var(--gold-400);
  animation: gtile-busy var(--motion-pending) linear infinite;
}

/* The expanded place's tiles hang directly under its heading. */
.gwall__head--toggle + .gwall__tiles {
  margin-top: calc(-1 * var(--sp-1));
}

.gwall__rule {
  flex: 1;
  height: var(--gwall-hair);
  background: linear-gradient(90deg, var(--gwall-line), transparent);
}

.gwall__n {
  flex: none;
  color: var(--paper-500);
  font: var(--text-xs) / 1.4 var(--f-num);
  letter-spacing: 0.04em;
}

.gwall__n b {
  color: var(--gold-300);
  font-weight: 500;
}

.gwall__grid {
  --gwall-min: calc(92px * var(--ui-scale));
  position: relative;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(var(--gwall-min), 1fr));
  gap: var(--gwall-gap);
}

.gwall__grid--landscape {
  --gwall-min: calc(176px * var(--ui-scale));
}

/* ---- tiles ---- */

.gtile {
  position: relative;
  display: grid;
  aspect-ratio: 9 / 16;
  min-width: 0;
  overflow: hidden;
  color: var(--paper-200);
  background: radial-gradient(circle at 50% 32%, #3a3326, #14120e 74%);
  border: var(--gwall-hair) solid var(--gold-600);
  border-radius: var(--radius-sm);
  box-shadow: inset 0 0 0 var(--gwall-hair) rgba(0, 0, 0, 0.5);
  outline: none;
  cursor: pointer;
  transition:
    border-color var(--motion-fast) var(--ease-standard),
    box-shadow var(--motion-fast) var(--ease-standard),
    transform var(--motion-fast) var(--ease-standard);
}

.gtile--landscape {
  aspect-ratio: 16 / 9;
}

.gtile:hover {
  border-color: var(--gold-400);
}

.gtile:hover .gtile__art {
  filter: brightness(1.08);
}

/* Focus is a gold outline outside the tile, so it never hides the selected
   border and reads on the selected tile too. */
.gtile:focus-visible {
  outline: calc(2px * var(--ui-scale)) solid var(--gold-400);
  outline-offset: calc(2px * var(--ui-scale));
}

/* Selected: a seal border doubled inside (weight, not only colour) and a
   soft glow. */
.gtile.is-selected {
  border-color: var(--seal-400);
  box-shadow:
    inset 0 0 0 calc(2px * var(--ui-scale)) var(--seal-500),
    0 0 calc(14px * var(--ui-scale)) var(--seal-glow);
}

/* The open subject joins its tray: the same seal line, no glow. */
.gtile.is-open {
  box-shadow: inset 0 0 0 calc(2px * var(--ui-scale)) var(--seal-500);
}

.gtile__art {
  grid-area: 1 / 1;
  width: 100%;
  height: 100%;
  transition: filter var(--motion-fast) var(--ease-standard);
}

.gtile__blank {
  grid-area: 1 / 1;
  place-self: center;
  display: grid;
  justify-items: center;
  gap: var(--sp-1);
  padding-bottom: var(--sp-6);
  color: var(--paper-700);
  font: var(--text-xs) / 1.3 var(--f-serif);
}

.gtile__blank svg {
  width: calc(34px * var(--ui-scale));
  height: calc(34px * var(--ui-scale));
}

.gtile__blank span {
  color: var(--paper-500);
}

.gtile__name {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  padding: var(--sp-6) var(--sp-1) var(--sp-1);
  overflow: hidden;
  color: var(--paper-50);
  font: var(--text-xs) / 1.3 var(--f-serif);
  text-align: center;
  white-space: nowrap;
  text-overflow: ellipsis;
  text-shadow: 0 calc(1px * var(--ui-scale)) calc(2px * var(--ui-scale)) rgba(0, 0, 0, 0.8);
  background: linear-gradient(180deg, transparent, rgba(8, 9, 11, 0.9) 62%);
  pointer-events: none;
}

.gtile.is-selected .gtile__name {
  color: var(--gold-300);
}

/* The live character's ribbon hangs down the tile's left edge as a vertical
   swallowtail banner, so it never crowds the count badge on a narrow tile. */
.gtile__current {
  position: absolute;
  top: 0;
  left: var(--sp-1);
  padding: var(--sp-1) calc(3px * var(--ui-scale)) var(--sp-3);
  color: var(--paper-50);
  font: var(--text-xs) / 1.1 var(--f-display);
  letter-spacing: 0.08em;
  writing-mode: vertical-rl;
  background: linear-gradient(180deg, var(--seal-500), var(--seal-700));
  filter: drop-shadow(0 calc(1px * var(--ui-scale)) calc(2px * var(--ui-scale)) rgba(0, 0, 0, 0.6));
  clip-path: polygon(0 0, 100% 0, 100% 100%, 50% calc(100% - var(--sp-2)), 0 100%);
  pointer-events: none;
}

.gtile__count {
  position: absolute;
  top: var(--sp-1);
  right: var(--sp-1);
  display: inline-flex;
  align-items: center;
  gap: calc(2px * var(--ui-scale));
  padding: 0 var(--sp-1);
  color: var(--gold-300);
  font: var(--text-xs) / 1.4 var(--f-num);
  background: rgba(8, 9, 11, 0.82);
  border: var(--gwall-hair) solid var(--gold-600);
  border-radius: var(--radius-sm);
  pointer-events: none;
}

.gtile__count svg {
  width: calc(13px * var(--ui-scale));
  height: calc(13px * var(--ui-scale));
}

/* A subject whose selection is in flight: a sweeping bar along the top edge
   (a shape, beside aria-busy); still at reduced and off motion. */
.gtile__busy {
  position: absolute;
  top: 0;
  right: 0;
  left: 0;
  height: calc(3px * var(--ui-scale));
  overflow: hidden;
  background: rgba(228, 200, 142, 0.25);
  pointer-events: none;
}

.gtile__busy::after {
  content: "";
  position: absolute;
  inset: 0;
  width: 40%;
  background: var(--gold-400);
  animation: gtile-busy var(--motion-pending) linear infinite;
}

@keyframes gtile-busy {
  from {
    transform: translateX(-100%);
  }
  to {
    transform: translateX(250%);
  }
}

.gtile.is-busy {
  border-color: var(--gold-400);
}

/* ---- tray tiles ---- */

.gtile__crown {
  position: absolute;
  top: var(--sp-1);
  left: var(--sp-1);
  display: inline-flex;
  align-items: center;
  gap: calc(2px * var(--ui-scale));
  padding: 0 var(--sp-1);
  color: var(--gold-300);
  font: var(--text-xs) / 1.4 var(--f-display);
  background: rgba(8, 9, 11, 0.85);
  border: var(--gwall-hair) solid var(--gold-500);
  border-radius: var(--radius-sm);
  pointer-events: none;
}

.gtile__crown svg {
  width: calc(13px * var(--ui-scale));
  height: calc(13px * var(--ui-scale));
}

.gtile__status {
  grid-area: 1 / 1;
  place-self: center;
  display: grid;
  justify-items: center;
  gap: var(--sp-2);
  padding: 0 var(--sp-1);
  color: var(--paper-300);
  font: var(--text-xs) / 1.3 var(--f-serif);
  text-align: center;
}

.gtile__status svg {
  width: calc(28px * var(--ui-scale));
  height: calc(28px * var(--ui-scale));
}

.gtile__status[data-status="pending"] svg {
  color: var(--gold-400);
}

.gtile__status[data-status="failed"] {
  color: var(--seal-400);
}

.gtile__spin {
  animation: gtile-spin var(--motion-spin) linear infinite;
}

@keyframes gtile-spin {
  to {
    transform: rotate(360deg);
  }
}

.gtile.is-pending {
  background:
    repeating-linear-gradient(135deg, rgba(185, 154, 96, 0.05) 0 calc(6px * var(--ui-scale)), transparent calc(6px * var(--ui-scale)) calc(12px * var(--ui-scale))),
    radial-gradient(circle at 50% 40%, #2c271d, #14120e 74%);
  border-style: dashed;
}

.gtile.is-failed {
  background: radial-gradient(circle at 50% 40%, #3a1f20, #15100f 74%);
  border-color: var(--seal-600);
}

.gtile--new {
  place-items: center;
  align-content: center;
  gap: var(--sp-2);
  color: var(--paper-400);
  background: rgba(8, 9, 11, 0.35);
  border: var(--gwall-hair) dashed var(--gold-500);
  box-shadow: none;
}

.gtile--new:hover {
  color: var(--gold-300);
  border-color: var(--gold-400);
  background: rgba(185, 154, 96, 0.08);
}

.gtile__plus {
  display: grid;
  place-items: center;
  width: calc(40px * var(--ui-scale));
  height: calc(40px * var(--ui-scale));
  border: var(--gwall-hair) solid currentColor;
  border-radius: 50%;
}

.gtile__plus svg {
  width: calc(20px * var(--ui-scale));
  height: calc(20px * var(--ui-scale));
}

.gtile__new-text {
  font: var(--text-xs) / 1.3 var(--f-display);
  letter-spacing: 0.08em;
}

/* Official images are read-only: a double border (shape, not colour). */
.gtile--official {
  border: calc(3px * var(--ui-scale)) double var(--gold-500);
}

.gtile--official.is-selected {
  border-color: var(--seal-400);
}

/* ---- the tray ---- */

/* The tray bleeds into the wall's padding by its own padding and border, so
   its tiles keep exactly the subject tiles' column width. */
.gtray {
  --gtray-pad: var(--sp-2);
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  margin: calc(var(--gwall-gap) + var(--sp-2)) calc(-1 * (var(--gtray-pad) + var(--gwall-hair))) var(--gwall-gap);
  padding: var(--gtray-pad);
  background: linear-gradient(180deg, rgba(169, 50, 42, 0.22), rgba(169, 50, 42, 0.08));
  border: var(--gwall-hair) solid var(--seal-600);
  border-radius: var(--radius-sm);
  box-shadow: inset 0 0 calc(24px * var(--ui-scale)) rgba(0, 0, 0, 0.45);
  scroll-margin-top: calc(var(--tray-reach, calc(0px * var(--ui-scale))) + var(--sp-3));
  scroll-margin-bottom: var(--sp-4);
  animation: gtray-in var(--motion-base) var(--ease-enter);
}

@keyframes gtray-in {
  from {
    opacity: 0;
    transform: translateY(calc(calc(-6px * var(--ui-scale)) * var(--motion-travel)));
  }
}

/* A notch under the owner tile ties the tray to it. */
.gtray__notch {
  position: absolute;
  top: calc(-7px * var(--ui-scale));
  left: var(--tray-notch-x, calc(48px * var(--ui-scale)));
  width: calc(12px * var(--ui-scale));
  height: calc(12px * var(--ui-scale));
  background: #3a1c1b;
  border-top: var(--gwall-hair) solid var(--seal-600);
  border-left: var(--gwall-hair) solid var(--seal-600);
  transform: translateX(-50%) rotate(45deg);
}

.gtray__official {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.gtray__label {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin: 0;
  color: var(--paper-200);
  font: var(--text-xs) / 1.4 var(--f-display);
  letter-spacing: 0.12em;
}

.gtray__readonly {
  display: inline-flex;
  align-items: center;
  gap: calc(2px * var(--ui-scale));
  padding: 0 var(--sp-2) 0 var(--sp-1);
  color: var(--paper-500);
  letter-spacing: 0.04em;
  border: var(--gwall-hair) solid var(--ink-600);
  border-radius: var(--radius-pill);
}

.gtray__readonly svg {
  width: calc(13px * var(--ui-scale));
  height: calc(13px * var(--ui-scale));
}
</style>
