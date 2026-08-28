<script setup>
// InventoryPanel (H4, webclient-hud-04-reference-drawers, tasks 6.1/6.2/6.5;
// relocate-inventory-drawer-essentials; redesign-inventory-item-grid;
// realign-inventory-drawer-layout): the 背包 · 裝備 drawer body — the
// redesign's three-section stack rendered directly on the transparent drawer
// body (no panel-card wrapper): the `裝備` section (the read-only equipment
// doll built from the committed `character` panel), an `物品` section whose
// tracked heading carries the shipped listing size as its tag over the
// responsive grid of native-button item tiles driven by the committed
// `services` panel's presentation metadata, and a `金錢` section rendering
// the committed wallet as one labelled row with grouped integer copper. One
// non-interactive inspector is shared by pointer hover and keyboard focus;
// selection is client-local, resets when the committed panel data is
// replaced, and no action is dispatched on click.
import { computed, nextTick, ref, watch } from "vue";
import EquipmentDoll from "./EquipmentDoll.vue";
import { formatCopper } from "./character-identity.js";
import { itemIconPath, unknownItemPath, kindLabel, rarityLabel } from "./item-icons.js";

const props = defineProps({
  // The committed `services` v2 panel payload (or the unavailable form).
  services: { type: Object, required: true },
  // The committed `character` v4 panel payload (or the unavailable form). A
  // completely missing panel arrives as `null`; the doll mounts only when a
  // committed character panel exists (never fabricating empty slots for a
  // missing panel).
  character: { type: Object, required: false, default: null },
  // The drawer-layer wallet figure for the `金錢` section: the exact
  // validated integer copper the drawer head subtitle already renders
  // (owned by `AppClient`, read from the available `character` panel).
  // `services.inventory.wallet` is deliberately never used, so head and
  // body can never disagree. Absent (null) renders no row — never a zero.
  wallet: { type: Number, required: false, default: null },
});

// The registry-owned unavailable form (available: false) carries only the
// reason — no rows, no default wallet value.
const unavailable = computed(() => props.services?.available === false);
const inventory = computed(() => (unavailable.value ? null : (props.services?.inventory ?? null)));
const bagVisible = computed(() => !unavailable.value && inventory.value !== null);

// The equipment doll renders only when the bag itself is available (the
// services panel is not in its unavailable form) AND the inventory section
// is present AND a committed character panel exists. A missing character
// panel (`null`) or an absent inventory section must not fabricate an
// equipment state (no empty-slot boxes, no rows, no count).
const dollVisible = computed(
  () => !unavailable.value && inventory.value !== null && props.character !== null,
);

// The full bag: every committed row.
const rows = computed(() => {
  const inv = inventory.value;
  return inv && Array.isArray(inv.rows) ? inv.rows : [];
});

// The 32-row ceiling note (task 6.2): only when the listing is at the
// bound, state the ceiling in words.
const INVENTORY_ROW_CEILING = 32;
const atCeiling = computed(() => rows.value.length === INVENTORY_ROW_CEILING);

// The 金錢 section (realign-inventory-drawer-layout, design D3): renders the
// committed wallet figure `AppClient` passes in — the exact validated
// character-panel integer the head subtitle draws — as one labelled row.
// It shows only while the bag is available AND the prop carries a
// committed non-negative integer; absent otherwise (never a fabricated
// zero balance).
const walletVisible = computed(
  () => bagVisible.value && Number.isInteger(props.wallet) && props.wallet >= 0,
);

// Client-local transient selection (redesign-inventory-item-grid): the single
// source shared by pointer hover and keyboard focus. It is never persisted;
// a panel replacement (new `services` or `services.inventory` reference)
// clears the selection when the held item no longer exists, so stale
// inventory metadata is never presented. Clicking a tile only updates this
// local selection — no OOB action is dispatched and no state is mutated.
const selectedKey = ref(null);
watch(
  [() => props.services, () => props.services?.inventory],
  () => {
    // Every committed panel replacement resets the client-local selection so
    // stale inventory metadata is never presented (design: "every panel
    // replacement resets selection").
    selectedKey.value = null;
  },
);

// The committed row currently driving the inspector (hover or focus).
const activeRow = computed(() => {
  if (!selectedKey.value) {
    return null;
  }
  return rows.value.find((r) => r.item_key === selectedKey.value) || null;
});

// The tile's local SVG: the closed icon map for a non-null presentation
// (unmapped keys fall back to the neutral unknown-item icon), or the
// neutral unknown-item icon when `presentation` is null.
function tileIconPath(row) {
  if (row.presentation) {
    return itemIconPath(row.presentation.icon_key) || unknownItemPath();
  }
  return unknownItemPath();
}

// The inspector spells the committed kind and rarity words (never invented).
function kindWord(row) {
  return row.presentation ? kindLabel(row.presentation.kind) : null;
}

function rarityWord(row) {
  return row.presentation ? rarityLabel(row.presentation.rarity) : null;
}

// ---- Inspector (task 1.2): one transient, non-interactive surface shared
// by pointer hover and keyboard focus. It shows only the committed display
// name, kind word, rarity word, held count, equipped state, and summary —
// it never invents numeric stats or comparison values.
const panelEl = ref(null);
const inspectorEl = ref(null);
const inspectorStyle = ref({});

function onTileEnter(event) {
  selectedKey.value = event.currentTarget.dataset.key;
}

function onTileLeave(event) {
  // Pointer leave clears the hover selection only when keyboard focus is
  // elsewhere; a focused tile keeps driving the inspector.
  const focused = document.activeElement;
  if (focused && focused.dataset && focused.dataset.key) {
    if (focused.dataset.key !== selectedKey.value) {
      selectedKey.value = focused.dataset.key;
    }
    return;
  }
  if (selectedKey.value === event.currentTarget.dataset.key) {
    selectedKey.value = null;
  }
}

function onTileFocus(event) {
  selectedKey.value = event.currentTarget.dataset.key;
}

function onTileBlur(event) {
  const focused = document.activeElement;
  if (focused && focused.dataset && focused.dataset.key) {
    selectedKey.value = focused.dataset.key;
    return;
  }
  if (selectedKey.value === event.currentTarget.dataset.key) {
    selectedKey.value = null;
  }
}

function onTileClick(event) {
  // Presentational selection only — no action is dispatched.
  selectedKey.value = event.currentTarget.dataset.key;
}

// Keep the inspector contained in the drawer body: positioned below the
// anchor tile, flipping above when it would leave the panel's visible
// bounds, and clamped horizontally.
watch(selectedKey, () => {
  if (!selectedKey.value) {
    inspectorStyle.value = {};
    return;
  }
  nextTick(() => {
    const panel = panelEl.value;
    const tip = inspectorEl.value;
    if (!panel || !tip) {
      return;
    }
    const anchor = panel.querySelector(`[data-testid="inventory-panel__tile--${selectedKey.value}"]`);
    if (!anchor) {
      return;
    }
    const panelRect = panel.getBoundingClientRect();
    const anchorRect = anchor.getBoundingClientRect();
    const tipW = tip.offsetWidth;
    const tipH = tip.offsetHeight;
    const pad = 8;
    let left = anchorRect.left + anchorRect.width / 2 - panelRect.left - tipW / 2;
    left = Math.max(pad, Math.min(left, panelRect.width - tipW - pad));
    let top = anchorRect.bottom - panelRect.top + pad;
    if (top + tipH > panelRect.height - pad) {
      top = Math.max(pad, anchorRect.top - panelRect.top - tipH - pad);
    }
    inspectorStyle.value = { left: `${left}px`, top: `${top}px` };
  });
});
</script>

<template>
  <aside ref="panelEl" class="inventory-panel" data-testid="inventory-panel">
    <p
      v-if="unavailable"
      class="inventory-panel__unavailable"
      data-testid="inventory-panel__unavailable"
      :data-reason-code="services.reason?.code"
    >
      {{ services.reason?.message }}
    </p>

    <p v-else-if="inventory === null" class="inventory-panel__absent" data-testid="inventory-panel__absent">
      背包目前是空的。
    </p>

    <template v-if="bagVisible">
      <!-- The 裝備 section: the equipment doll (moved here from the
           character-status drawer) — it reads the committed `character`
           panel's equipment rows itself and renders its registered
           unavailable message when that panel is in its unavailable form.
           It mounts before the held-item listing and only when the bag is
           available, the inventory section is present, and a committed
           character panel exists. -->
      <section v-if="dollVisible" class="inventory-panel__block">
        <EquipmentDoll :character="character" />
      </section>

      <!-- The 物品 section: the mock's tracked heading tagged with the
           shipped listing size (never a total of untruncated holdings —
           the ceiling sentence already states the bound), over the held-
           item grid (redesign-inventory-item-grid): responsive native-
           button tiles driven by the committed presentation metadata; a
           null presentation renders the neutral unknown-item tile. -->
      <section class="inventory-panel__block" data-testid="inventory-panel__section--items">
        <h4 class="inventory-panel__heading" data-testid="inventory-panel__heading--items">物品<span
          class="inventory-panel__heading-tag"
          data-testid="inventory-panel__items-count"
        >{{ rows.length }}</span></h4>
        <div class="inventory-panel__grid" data-testid="inventory-panel__grid">
          <button
            v-for="row in rows"
            :key="row.item_key"
            type="button"
            class="inventory-panel__tile"
            :data-key="row.item_key"
            :data-testid="`inventory-panel__tile--${row.item_key}`"
            :data-rarity="row.presentation?.rarity || 'unknown'"
            :data-equipped="String(!!row.equipped)"
            :data-unknown="String(!row.presentation)"
            :aria-label="row.display_name"
            :aria-describedby="selectedKey === row.item_key ? 'inventory-panel-inspector' : undefined"
            @pointerenter="onTileEnter"
            @pointerleave="onTileLeave"
            @focus="onTileFocus"
            @blur="onTileBlur"
            @click="onTileClick"
          >
            <svg class="inventory-panel__icon" aria-hidden="true" width="26" height="26" viewBox="0 0 24 24" fill="none">
              <path :d="tileIconPath(row)" stroke="currentColor" stroke-width="1.6" />
            </svg>
            <span v-if="row.equipped" class="inventory-panel__equipped" :data-testid="`inventory-panel__equipped--${row.item_key}`" aria-hidden="true">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none">
                <path d="M5 13l4 4L19 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
            <span v-if="!row.presentation" class="inventory-panel__unknown" :data-testid="`inventory-panel__unknown--${row.item_key}`">未知</span>
            <span v-if="!row.presentation" class="inventory-panel__name" :data-testid="`inventory-panel__name--${row.item_key}`">{{ row.display_name }}</span>
            <span class="inventory-panel__count" :data-testid="`inventory-panel__count--${row.item_key}`">{{ row.held }}</span>
          </button>
        </div>

        <p v-if="atCeiling" class="inventory-panel__ceiling" data-testid="inventory-panel__ceiling">
          背包清單以上限 32 項為限，僅顯示已載入的項目。
        </p>
      </section>

      <!-- The 金錢 section: one mock `.statrow`-styled row (錢袋 / integer
           copper) carrying the same committed wallet figure the head
           subtitle renders; absent — never a zero — when the figure is
           not a committed non-negative integer. -->
      <section v-if="walletVisible" class="inventory-panel__block" data-testid="inventory-panel__section--wallet">
        <h4 class="inventory-panel__heading" data-testid="inventory-panel__heading--wallet">金錢</h4>
        <div class="inventory-panel__statrow">
          <span class="inventory-panel__statrow-label">錢袋 <small class="inventory-panel__statrow-unit">整數銅</small></span>
          <span class="inventory-panel__wallet-value" data-testid="inventory-panel__wallet-value">{{ formatCopper(wallet) }}</span>
        </div>
      </section>
    </template>

    <!-- The single transient item inspector (task 1.2): non-focusable
         `role="tooltip"` surface shared by hover and focus, positioned within
         the drawer body and flipped above/below as needed. -->
    <div
      v-if="activeRow"
      ref="inspectorEl"
      id="inventory-panel-inspector"
      class="inventory-panel__inspector"
      data-testid="inventory-panel__inspector"
      role="tooltip"
      :style="inspectorStyle"
    >
      <div class="inventory-panel__inspector-head">
        <span class="inventory-panel__inspector-name" data-testid="inventory-panel__inspector-name">{{ activeRow.display_name }}</span>
        <span
          v-if="rarityWord(activeRow)"
          class="inventory-panel__inspector-rarity"
          :data-rarity="activeRow.presentation?.rarity"
          data-testid="inventory-panel__inspector-rarity"
        >
          {{ rarityWord(activeRow) }}
        </span>
      </div>
      <div v-if="kindWord(activeRow)" class="inventory-panel__inspector-kind" data-testid="inventory-panel__inspector-kind">
        {{ kindWord(activeRow) }}
      </div>
      <div v-if="activeRow.presentation && activeRow.presentation.summary" class="inventory-panel__inspector-summary" data-testid="inventory-panel__inspector-summary">
        {{ activeRow.presentation.summary }}
      </div>
      <div class="inventory-panel__inspector-meta">
        <span class="inventory-panel__inspector-held" data-testid="inventory-panel__inspector-held">{{ activeRow.held }}</span>
        <span class="inventory-panel__inspector-equipped" data-testid="inventory-panel__inspector-equipped">
          {{ activeRow.equipped ? "裝備中" : "未裝備" }}
        </span>
      </div>
    </div>
  </aside>
</template>

<style scoped>
/* The drawer body is the mock's `.draw .body`: the sections sit directly on
   the transparent drawer body (no panel-card wrapper, no own padding — the
   drawer chrome pads), with the mock's 18px section rhythm. `position:
   relative` remains so the transient inspector positions inside the body. */
.inventory-panel {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 18px;
  box-sizing: border-box;
  font-family: var(--f-sans);
}

/* One mock `section.block`: heading (where it has one) over its content. */
.inventory-panel__block {
  margin: 0;
}

/* The mock's `section.block h4`: small tracked heading with the tag riding
   at the right. */
.inventory-panel__heading {
  margin: 0 0 9px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--paper-500);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.inventory-panel__heading-tag {
  margin-left: auto;
  letter-spacing: 0.03em;
  text-transform: none;
  color: var(--paper-700);
  font-size: 11px;
}

/* The mock's `.statrow`: label left, grouped mono gold value right. */
.inventory-panel__statrow {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--ink-820);
  border: 1px solid var(--ink-700);
  border-radius: 9px;
  padding: 9px 12px;
}

.inventory-panel__statrow-label {
  font-size: 13px;
  color: var(--paper-100);
}

.inventory-panel__statrow-unit {
  color: var(--paper-700);
  margin-left: 6px;
  font-size: 10px;
}

.inventory-panel__wallet-value {
  margin-left: auto;
  font-family: var(--f-mono);
  font-size: 13px;
  color: var(--gold-400);
}

.inventory-panel__unavailable {
  margin: 0;
  padding: var(--sp-1) var(--sp-2);
  color: var(--paper-500);
  font-size: 0.85em;
  border: 1px dashed var(--ink-700);
  border-radius: var(--radius-sm);
}

.inventory-panel__absent {
  margin: 0;
  color: var(--paper-500);
  font-size: 0.85em;
}

/* The responsive held-item grid (the reference's `.itgrid`): auto-fill
   columns with a 58px cell minimum and an 8px gap. */
.inventory-panel__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(58px, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}

/* The item tile (the reference's `.it`): a bounded native button with a
   square aspect, a local SVG icon, a stable lower-corner held count, a
   non-colour equipped check marker, and a per-rarity border treatment. */
.inventory-panel__tile {
  aspect-ratio: 1;
  border-radius: 9px;
  border: 1px solid var(--ink-600);
  background: var(--ink-820);
  display: grid;
  place-items: center;
  position: relative;
  cursor: pointer;
  padding: 0;
  color: var(--paper-300);
  transition: border-color var(--motion-fast) var(--ease-standard), outline-color var(--motion-fast) var(--ease-standard);
}

.inventory-panel__tile:hover,
.inventory-panel__tile:focus-visible {
  border-color: var(--gold-500);
}

.inventory-panel__tile:focus-visible {
  outline: 2px solid var(--gold-500);
  outline-offset: 2px;
}

.inventory-panel__icon {
  width: 26px;
  height: 26px;
  color: var(--paper-300);
}

.inventory-panel__count {
  position: absolute;
  bottom: 2px;
  right: 4px;
  font-family: var(--f-mono);
  font-size: 9px;
  color: var(--paper-300);
}

/* The non-colour equipped state: a check glyph, not a colour cue. */
.inventory-panel__equipped {
  position: absolute;
  top: 2px;
  left: 4px;
  width: 10px;
  height: 10px;
  color: var(--gold-400);
}

/* The labelled neutral unknown-item marker and its real name (wrapping for
   long localised labels; the button's accessible name stays complete). */
.inventory-panel__unknown {
  position: absolute;
  top: 2px;
  right: 4px;
  font-size: 9px;
  color: var(--paper-500);
}

.inventory-panel__name {
  position: absolute;
  bottom: 2px;
  left: 4px;
  right: 20px;
  font-size: 9px;
  line-height: 1.15;
  color: var(--paper-300);
  word-break: break-word;
}

/* Per-rarity border treatment: a distinct border pattern as well as a
   distinct colour, so rarity is never colour-only (the inspector spells
   the rarity word). */
.inventory-panel__tile[data-rarity="common"] {
  border-color: var(--ink-600);
  border-style: solid;
}
.inventory-panel__tile[data-rarity="uncommon"] {
  border-color: #7a9a6a;
  border-style: dotted;
}
.inventory-panel__tile[data-rarity="rare"] {
  border-color: #5c86dd;
  border-style: dashed;
}
.inventory-panel__tile[data-rarity="epic"] {
  border-color: #a46ad0;
  border-style: double;
}
.inventory-panel__tile[data-rarity="legendary"] {
  border-color: var(--gold-500);
  border-style: ridge;
}
.inventory-panel__tile[data-rarity="unknown"] {
  border-color: var(--ink-600);
  border-style: solid;
}

.inventory-panel__ceiling {
  margin: 0;
  color: var(--paper-500);
  font-size: 0.8em;
}

/* The single transient item inspector (task 1.2): non-interactive,
   non-focusable, positioned by JS within the drawer body. */
.inventory-panel__inspector {
  position: absolute;
  z-index: 5;
  width: 270px;
  background: var(--panel-solid);
  border: 1px solid var(--ink-600);
  border-radius: 11px;
  box-shadow: var(--shadow);
  padding: 13px 15px;
  font-size: 12.5px;
  pointer-events: none;
  animation: inventory-inspector-in var(--motion-fast) var(--ease-standard);
}

@keyframes inventory-inspector-in {
  from {
    opacity: 0;
    transform: translateY(2px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

.inventory-panel__inspector-head {
  display: flex;
  justify-content: space-between;
  gap: var(--sp-2);
}

.inventory-panel__inspector-name {
  font-size: 14px;
  color: var(--paper-50);
  font-weight: 600;
  min-width: 0;
}

.inventory-panel__inspector-rarity {
  font-size: 11px;
  color: var(--gold-400);
  flex: none;
}

.inventory-panel__inspector-rarity[data-rarity="common"] {
  color: var(--paper-500);
}
.inventory-panel__inspector-rarity[data-rarity="uncommon"] {
  color: #7a9a6a;
}
.inventory-panel__inspector-rarity[data-rarity="rare"] {
  color: #5c86dd;
}
.inventory-panel__inspector-rarity[data-rarity="epic"] {
  color: #a46ad0;
}
.inventory-panel__inspector-rarity[data-rarity="legendary"] {
  color: var(--gold-500);
}

.inventory-panel__inspector-kind {
  font-size: 11px;
  color: var(--paper-500);
  margin-bottom: 7px;
}

.inventory-panel__inspector-summary {
  color: var(--paper-300);
  line-height: 1.5;
  margin-top: 4px;
}

.inventory-panel__inspector-meta {
  display: flex;
  justify-content: space-between;
  color: var(--paper-300);
  font-family: var(--f-mono);
  font-size: 11.5px;
  margin-top: 3px;
}
</style>
