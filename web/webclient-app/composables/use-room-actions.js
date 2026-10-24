// The room actions' wiring (exploration-room-actions design D1/D3/D4/D5/D6;
// redesign-rest-entry design D1/D3/D5/D7): the place card's 查看房間 and 休息,
// the 建議 pill, the suggestions card through ChoiceCard, the two-layer rest
// entry (the TimeChoiceCard tiles, then the shared shell around the wait or
// sleep form), focus return to the opener, the readout feed of the buttons
// and the pill, and the exploration screen's Tab chain (compass → rail →
// 查看房間 → 休息 → 建議).
//
// The open card is the store's client-local slice (`store.view.roomCard`, a
// sibling of the presence card), so a commit can close it atomically and the
// rail, the compass, and the digits all know a card is open. The rest entry
// is the room card kind "wait". This composable holds only what the view
// alone knows: which layer of the rest entry shows (`waitStep`: null for the
// tiles, "wait" or "sleep" for that second-layer form), the tile the player
// came from (`lastTile`, focused again on a step back), whether the tiles are
// being returned to (no replayed entrance), and which control opened the
// card.
import { computed, nextTick, ref, watch } from "vue";
import { BACK_ROW } from "./use-person-focus.js";
import { pillReadout } from "../components/exploration-readout.js";
import stableStringify from "../lib/stable_stringify.js";

// The one reason the locked rest entry or dream answer states (a mutation in
// flight or awaiting its declared revision, or the session not live).
export const WAIT_LOCKED_REASON = "上一個行動尚未完成，請稍候。";

export const SUGGESTIONS_GENERATING_NOTE = "AI 正在構思建議…";
export const SUGGESTIONS_DEGRADED_NOTE = "AI 建議目前不可用";
export const SUGGESTIONS_EMPTY_NOTE = "現在沒有什麼值得做的動作";
const DISMISS_ACTION = "options.dismiss";

function digitBadge(index) {
  return index < 9 ? String(index + 1) : "·";
}

// The suggestions card's content from the store's `suggestionsCard`
// (`{status, items}`): the card rows (label and optional hint), keyed by
// action code and parameters so a suggestions-only update keeps the active
// row on a card that survives; the 清除建議 row with its trash-can badge; the
// trailing `✕ 返回`; and the muted notes for the generating, degraded, and
// empty states. `builderKeys` maps each row key back to the builder row.
export function suggestionsCardContent(content) {
  const items = (content && content.items) || [];
  const status = content ? content.status : null;
  const builderKeys = {};
  const used = new Set();
  const rows = [];
  let dismiss = null;
  let cards = 0;
  for (const item of items) {
    if (!item.actionId) {
      // The builder's generating and empty lines are notes, not rows.
      continue;
    }
    if (item.actionId === DISMISS_ACTION) {
      dismiss = item;
      continue;
    }
    const base = `card:${item.actionId}:${stableStringify(item.payload || {})}`;
    let key = base;
    for (let n = 2; used.has(key); n += 1) {
      key = `${base}#${n}`;
    }
    used.add(key);
    builderKeys[key] = item.key;
    rows.push({
      key,
      label: item.label,
      hint: item.hint || null,
      badge: digitBadge(cards),
      kind: "verb",
      enabled: true,
      testId: "suggestions-card-row",
    });
    cards += 1;
  }
  const notes = [];
  if (status === "generating") {
    notes.push(SUGGESTIONS_GENERATING_NOTE);
  } else if (status === "degraded") {
    notes.push(SUGGESTIONS_DEGRADED_NOTE);
    if (cards === 0) {
      notes.push(SUGGESTIONS_EMPTY_NOTE);
    }
  }
  let trailingIndex;
  if (dismiss) {
    builderKeys.dismiss = dismiss.key;
    trailingIndex = rows.length;
    rows.push({
      key: "dismiss",
      label: "清除建議",
      badge: "",
      icon: "trash",
      kind: "dismiss",
      enabled: true,
      testId: "suggestions-card-dismiss",
    });
  } else {
    trailingIndex = rows.length;
  }
  rows.push(BACK_ROW);
  return { rows, notes, trailingIndex, builderKeys, count: cards };
}

// Whether an element can take focus right now: rendered, enabled, and not
// inside an inert, hidden, or `display: none` ancestor.
function focusable(el) {
  if (!el || !el.isConnected || el.disabled) {
    return false;
  }
  if (el.closest?.('[inert], [hidden], [aria-hidden="true"], [style*="display: none"]')) {
    return false;
  }
  return true;
}

const CHAIN_SELECTORS = Object.freeze({
  compass: '#action-dock [data-testid="exit-compass"]',
  rail: '[data-anchor="presence"] [data-testid="presence-rail"]',
  look: '[data-anchor="map"] [data-testid="place-card-look"]',
  wait: '[data-anchor="map"] [data-testid="place-card-wait"]',
  pill: '#action-dock [data-testid="suggestions-pill"]',
});
const CHAIN_ORDER = Object.freeze(["compass", "rail", "look", "wait", "pill"]);

export function useRoomActions(
  store,
  { panelAvailable, dispatchIntent, skipDisabled, compassRef, onPlaceHover, onPillHover },
) {
  const roomCardRef = ref(null);
  // The rest entry's layer: null (the tiles) | "wait" | "sleep" (that form).
  const waitStep = ref(null);
  // The tile the current second layer was opened from: "wait" | "sleep".
  const lastTile = ref("wait");
  // The tiles are shown again after a step back: no replayed entrance.
  const returning = ref(false);
  // Which control opened the open card: "wait" | "pill" | null.
  const opener = ref(null);

  const roomCard = computed(() => (store.view.mode === "exploration" ? store.view.roomCard : null));
  const roomCardOpen = computed(() => !!roomCard.value);

  // The exploration root is live: the router's root frame is the exploration
  // root and it is not degraded.
  const explorationRootLive = computed(
    () =>
      store.view.mode === "exploration" &&
      !store.view.degradedRoot &&
      store.view.dockSource === "exploration.root",
  );

  // The place card's room actions (design D3): exploration with the panel
  // available.
  const placeActions = computed(() => explorationRootLive.value && panelAvailable("exploration"));

  // The suggestions card's content, and the 建議 pill (hidden while the
  // envelope presents nothing, i.e. `unavailable`, and while a re-homed
  // sub-dock owns the surface).
  const suggestions = computed(() => suggestionsCardContent(store.view.suggestionsCard));
  const pillShown = computed(
    () => placeActions.value && !!store.view.suggestionsCard && !store.view.activeSubDock,
  );
  const pillCount = computed(() =>
    store.view.suggestionsCard && store.view.suggestionsCard.status !== "generating" ? suggestions.value.count : 0,
  );
  const pillLabel = computed(() => (pillCount.value > 0 ? `建議 ${pillCount.value}` : "建議"));

  // The suggestions card's rows; the rest entry renders no rows.
  const roomCardRows = computed(() => (roomCard.value?.kind === "suggestions" ? suggestions.value.rows : []));
  const roomCardNotes = computed(() => (roomCard.value?.kind === "suggestions" ? suggestions.value.notes : []));
  const roomCardTrailing = computed(() =>
    roomCard.value?.kind === "suggestions" ? suggestions.value.trailingIndex : roomCardRows.value.length - 1,
  );
  const roomCardCaption = computed(() => (roomCard.value?.kind === "suggestions" ? "建議" : null));
  const roomCardLabel = computed(() => "建議");
  // The suggestions card through ChoiceCard.
  const roomCardShown = computed(() => roomCardOpen.value && roomCard.value.kind === "suggestions");
  // The rest entry's layers: the tiles, the wait form, the sleep form.
  const tilesShown = computed(() => roomCard.value?.kind === "wait" && waitStep.value === null);
  const waitFormOpen = computed(() => roomCard.value?.kind === "wait" && waitStep.value === "wait");
  const sleepOpen = computed(() => roomCard.value?.kind === "wait" && waitStep.value === "sleep");

  // The tiles' context (redesign-rest-entry design D5): only what the client
  // already holds. The 等待 tile reads the clock part of the committed
  // world-time label; the 睡眠 tile the status panel's fatigue row for the
  // controlled body (`actor.identity`, the possessed body under possession).
  const waitTileTime = computed(() => {
    const label = store.view.statusSlice && store.view.statusSlice.timeLabel;
    return label ? label.split("‧").pop().trim() : null;
  });
  const sleepTileFatigue = computed(() => {
    const status = store.view.panels && store.view.panels.status;
    if (!status || status.available === false || !Array.isArray(status.fatigue) || !status.actor) {
      return null;
    }
    const identity = String(status.actor.identity);
    const row = status.fatigue.find((entry) => entry && String(entry.identity) === identity);
    return row ? { reserve_percent: row.reserve_percent, label: row.label } : null;
  });

  // --- activation -----------------------------------------------------------

  function onPlaceLook() {
    store.activateRoomLook();
  }

  function onPlaceWait() {
    if (store.openRoomCard("wait")) {
      opener.value = "wait";
    }
  }

  function onPill() {
    if (store.openRoomCard("suggestions")) {
      opener.value = "pill";
    }
  }

  function onRoomCardPick(key) {
    if (roomCard.value?.kind !== "suggestions") {
      return;
    }
    const builderKey = suggestions.value.builderKeys[key];
    if (builderKey) {
      store.activateSuggestion(builderKey);
    }
  }

  function onRoomCardBack() {
    store.closeRoomCard();
  }

  // A tile opens its second-layer form (the form autofocuses its duration
  // input). Nothing is opened while the submission gate is locked.
  function onTilePick(key) {
    if (skipDisabled.value || (key !== "wait" && key !== "sleep")) {
      return;
    }
    lastTile.value = key;
    waitStep.value = key;
  }

  // `‹` or Escape on the second layer: back to the tiles, which remount and
  // autofocus the tile the player came from (`initialTile` is `lastTile`).
  function onStepBack() {
    returning.value = true;
    waitStep.value = null;
  }

  // `✕` on either layer: close the whole entry; the kind watcher returns
  // focus to the place card's 休息.
  function onStepClose() {
    store.closeRoomCard();
  }

  // The wait form's two options (redesign-rest-entry design D3): the exact
  // `explore.wait` payloads the retired rows sent, through the single store
  // entry; the entry closes once sent.
  function onWaitDawn() {
    if (skipDisabled.value) {
      return;
    }
    if (dispatchIntent("explore.wait", { daypart: "dawn" }) !== null) {
      store.closeRoomCard();
    }
  }

  function onWaitSubmit(seconds) {
    if (skipDisabled.value) {
      return;
    }
    if (dispatchIntent("explore.wait", { seconds }) !== null) {
      store.closeRoomCard();
    }
  }

  function onSleepRecover() {
    if (skipDisabled.value) {
      return;
    }
    if (dispatchIntent("explore.wait", { sleep: true }) !== null) {
      store.closeRoomCard();
    }
  }

  function onSleepSubmit(seconds) {
    if (skipDisabled.value) {
      return;
    }
    if (
      dispatchIntent("explore.wait", {
        sleep: true,
        sleep_mode: "duration",
        seconds,
      }) !== null
    ) {
      store.closeRoomCard();
    }
  }

  // --- focus ------------------------------------------------------------------

  function elementFor(member) {
    return typeof document === "undefined" ? null : document.querySelector(CHAIN_SELECTORS[member]);
  }

  function focusMember(member) {
    const el = elementFor(member);
    if (!focusable(el)) {
      return false;
    }
    el.focus({ preventScroll: true });
    return document.activeElement === el;
  }

  // A card closing returns focus that sat on it (now removed) or fell out of
  // the layout to the control that opened it, else the compass, else the
  // dock. Focus the player put elsewhere stays.
  function focusLost(active) {
    return (
      !active ||
      active === document.body ||
      active === document.documentElement ||
      !active.isConnected ||
      !!active.closest?.('[data-anchor="choices"]')
    );
  }

  watch(
    () => roomCard.value?.kind ?? null,
    async (kind, previous) => {
      waitStep.value = null;
      lastTile.value = "wait";
      returning.value = false;
      if (kind || !previous) {
        return;
      }
      const from = opener.value;
      opener.value = null;
      await nextTick();
      if (typeof document === "undefined" || store.view.mode !== "exploration" || store.view.presenceCard) {
        return;
      }
      if (!focusLost(document.activeElement)) {
        return;
      }
      if (from && focusMember(from === "pill" ? "pill" : "wait")) {
        return;
      }
      if (compassRef.value) {
        compassRef.value.focus();
        if (document.activeElement && !focusLost(document.activeElement)) {
          return;
        }
      }
      document.getElementById("action-dock")?.focus({ preventScroll: true });
    },
    { flush: "post" },
  );

  // A lock that disables the focused form control on the second layer would
  // strand focus on a dead control (a disabled element receives no keys, so
  // neither the shell's Tab trap nor the form's Escape would act): focus
  // moves to the shell's `‹`, which is never disabled.
  watch(
    skipDisabled,
    async (locked) => {
      if (!locked || !(waitFormOpen.value || sleepOpen.value) || typeof document === "undefined") {
        return;
      }
      await nextTick();
      const active = document.activeElement;
      if (active && active !== document.body && !active.disabled && active.isConnected) {
        return;
      }
      document.querySelector('[data-anchor="choices"] [data-testid="rest-step-back"]')?.focus({ preventScroll: true });
    },
    { flush: "post" },
  );

  // --- readout feed --------------------------------------------------------

  function onPlaceHoverContent(content) {
    onPlaceHover(content);
  }

  function onPillHoverChange(hovered) {
    const content = store.view.suggestionsCard;
    onPillHover(hovered && content ? pillReadout(content.status, pillCount.value) : null);
  }

  watch(placeActions, (shown) => {
    if (!shown) {
      onPlaceHover(null);
    }
  });
  watch(pillShown, (shown) => {
    if (!shown) {
      onPillHover(null);
    }
  });
  // A card covering the screen clears the hover sources it hides.
  watch(roomCardOpen, (open) => {
    if (open) {
      onPlaceHover(null);
      onPillHover(null);
    }
  });

  // --- the Tab chain ---------------------------------------------------------

  // Step to the next (or previous) focusable member of the chain from
  // `member`; a member that is absent, hidden, inert, or disabled is
  // skipped. At either end Tab stays native.
  function step(event, member, backward) {
    const start = CHAIN_ORDER.indexOf(member);
    const delta = backward ? -1 : 1;
    for (let index = start + delta; index >= 0 && index < CHAIN_ORDER.length; index += delta) {
      const el = elementFor(CHAIN_ORDER[index]);
      if (focusable(el)) {
        event.preventDefault();
        el.focus({ preventScroll: true });
        return true;
      }
    }
    return false;
  }

  function isTab(event) {
    return event && event.key === "Tab" && !event.ctrlKey && !event.altKey && !event.metaKey;
  }

  function onCompassTab(event) {
    if (isTab(event)) {
      step(event, "compass", event.shiftKey);
    }
  }

  function onRailTab({ event, backward }) {
    step(event, "rail", backward);
  }

  function onPlaceTab({ event, which, backward }) {
    step(event, which, backward);
  }

  function onPillTab(event) {
    if (isTab(event)) {
      step(event, "pill", event.shiftKey);
    }
  }

  return {
    roomCardRef,
    roomCard,
    roomCardOpen,
    roomCardShown,
    roomCardRows,
    roomCardNotes,
    roomCardTrailing,
    roomCardCaption,
    roomCardLabel,
    tilesShown,
    waitFormOpen,
    sleepOpen,
    lastTile,
    returning,
    waitTileTime,
    sleepTileFatigue,
    placeActions,
    explorationRootLive,
    pillShown,
    pillCount,
    pillLabel,
    onPlaceLook,
    onPlaceWait,
    onPill,
    onRoomCardPick,
    onRoomCardBack,
    onTilePick,
    onStepBack,
    onStepClose,
    onWaitDawn,
    onWaitSubmit,
    onSleepRecover,
    onSleepSubmit,
    onPlaceHover: onPlaceHoverContent,
    onPillHoverChange,
    onCompassTab,
    onRailTab,
    onPlaceTab,
    onPillTab,
  };
}
