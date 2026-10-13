// The presence rail's and the person focus's wiring (exploration-presence-rail
// design D2/D3/D4/D5): whether the rail stands on the stage, the centred
// card's rows (the verb card or the overflow card) through ChoiceCard, the
// one stage actor in `actor-right` (the dialogue host, else the person in
// focus), the message window's speaker line, focus restoration to the
// opener when a card closes, the departed flash, and the Tab chain compass
// → rail → dock footer. The card's state is the store's client-local slice
// (`store.view.presenceCard`); this composable owns no state of its own but
// the template refs.
import { computed, nextTick, ref, watch } from "vue";
import { disabledRowReason } from "../components/dock-exits.js";
import { railOverflow } from "../components/presence-rail.js";
import { departedReadout } from "../components/exploration-readout.js";

export const BACK_ROW = Object.freeze({
  key: "back",
  label: "返回",
  badge: "✕",
  icon: "close",
  kind: "back",
  enabled: true,
  back: true,
  testId: "choice-card-back",
});

function digitBadge(index) {
  return index < 9 ? String(index + 1) : "·";
}

// The verb card's rows: `verbMenuFor`'s rows (its own back row dropped) with
// digit badges, then the trailing `✕ 返回` row.
export function verbCardRows(items) {
  const rows = (items || [])
    .filter((item) => !item.goBack)
    .map((item, index) => ({
      key: item.key,
      label: item.label,
      badge: digitBadge(index),
      kind: "verb",
      enabled: item.enabled !== false,
      reason: disabledRowReason(item),
      testId: "verb-card-row",
    }));
  return [...rows, BACK_ROW];
}

// The overflow card's rows: the entries the rail folded into `＋N`, objects
// marked ◇, then `✕ 返回`.
export function overflowCardRows(entries) {
  const rows = railOverflow(entries).map((entry, index) => ({
    key: entry.key,
    label: entry.presence === "object" ? `◇ ${entry.label}` : entry.label,
    badge: digitBadge(index),
    kind: "verb",
    enabled: true,
    testId: "overflow-card-row",
  }));
  return [...rows, BACK_ROW];
}

export function usePersonFocus(store, { panel, compassRef, onRailHover, showReadoutFlash }) {
  const railRef = ref(null);

  const card = computed(() => (store.view.mode === "exploration" ? store.view.presenceCard : null));
  const cardOpen = computed(() => !!card.value);
  const personFocus = computed(() => card.value?.kind === "verbs");

  // The rail stays mounted under a card (shown again in place, so the opener
  // can take focus back at once); it leaves the stage outside exploration,
  // in an empty room, under a held combat round, and on a degraded root.
  const railMounted = computed(
    () =>
      store.view.mode === "exploration" &&
      (store.view.presenceEntries || []).length > 0 &&
      !store.view.beatHold &&
      !store.view.degradedRoot,
  );
  const railShown = computed(() => railMounted.value && !cardOpen.value);

  // The interact target in focus, read from the committed panel.
  const focusTarget = computed(() => {
    if (!personFocus.value) {
      return null;
    }
    const identity = card.value.identity;
    return (store.view.explorationInteract || []).find((target) => target.identity === identity) || null;
  });

  const cardRows = computed(() => {
    if (!card.value) {
      return [];
    }
    return card.value.kind === "verbs"
      ? verbCardRows(store.view.presenceVerbs)
      : overflowCardRows(store.view.presenceEntries);
  });
  // A new card (another person, or the overflow card turning into a verb
  // card) mounts fresh: its own entrance and its own first active row.
  const cardKey = computed(() =>
    card.value ? `${card.value.kind}-${card.value.identity ?? "more"}` : null,
  );
  const cardCaption = computed(() => (card.value?.kind === "overflow" ? "在場" : null));
  const cardLabel = computed(() =>
    card.value?.kind === "verbs" ? `${card.value.name}：選擇行動` : "其餘在場者與物件",
  );

  // The message window's speaker line while a person is in focus.
  const speaker = computed(() => (personFocus.value ? card.value.name : null));

  // The standee in focus (design D3): its committed portrait entry, or null
  // for the dialogue silhouette treatment.
  const focusPortrait = computed(() => {
    const key = focusTarget.value?.portrait_ref;
    return key == null ? null : (panel("art")?.portrait_catalog?.[key] ?? null);
  });

  function onRailActivate(key) {
    store.activatePresence(key);
  }

  function onCardPick(key) {
    if (!card.value) {
      return;
    }
    if (card.value.kind === "verbs") {
      store.activatePresenceVerb(key);
    } else {
      store.activatePresence(key);
    }
  }

  function onCardBack() {
    store.closePresenceCard();
  }

  // Focus restoration (redesign §4.3/§5.4): when a card closes, focus that
  // sat on it (now removed) or fell out of the layout returns to the rail
  // slot that opened it — the `＋N` slot for a card reached through the
  // overflow card — else the rail, else the compass. Focus the player put
  // elsewhere (a drawer, the command line) stays.
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
    () => store.view.presenceCard,
    async (next, previous) => {
      if (next || !previous || store.view.mode !== "exploration") {
        return;
      }
      await nextTick();
      if (typeof document === "undefined" || !focusLost(document.activeElement)) {
        return;
      }
      const rail = railShown.value ? railRef.value : null;
      if (rail && !rail.focusEntry(previous.openerKey)) {
        rail.focus();
      }
      if (!railElement() || document.activeElement !== railElement()) {
        compassRef.value?.focus();
      }
    },
    { flush: "post" },
  );

  // The departed flash: a fresh notice from the store's commit-time settle.
  watch(
    () => store.view.presenceNotice?.seq,
    (seq, previous) => {
      if (seq && seq !== previous) {
        showReadoutFlash(departedReadout(store.view.presenceNotice.name));
      }
    },
  );

  // The rail's hover feed clears when the rail leaves the stage.
  watch(railShown, (shown) => {
    if (!shown) {
      onRailHover(null);
    }
  });

  // The Tab chain (design D5): compass → rail → dock footer, and back. The
  // rail stands in a stage anchor that precedes the band in DOM order, so the
  // chain is stitched here; a hidden or absent target leaves Tab native.
  function overviewList() {
    return document.querySelector('#action-dock [data-testid="scene-overview"] [role="listbox"]');
  }

  function railElement() {
    return document.querySelector('[data-anchor="presence"] [data-testid="presence-rail"]');
  }

  function moveFocus(event, target) {
    if (!target || target.closest?.('[style*="display: none"]')) {
      return false;
    }
    event.preventDefault();
    target.focus({ preventScroll: true });
    return true;
  }

  function onCompassTab(event) {
    if (event.key !== "Tab" || event.shiftKey || !railShown.value) {
      return;
    }
    moveFocus(event, railElement());
  }

  function onRailTab({ event, backward }) {
    if (backward) {
      const compass = document.querySelector('#action-dock [data-testid="exit-compass"]');
      moveFocus(event, compass);
    } else {
      moveFocus(event, overviewList());
    }
  }

  function onOverviewTab(event) {
    if (event.key !== "Tab" || !event.shiftKey || !railShown.value) {
      return;
    }
    if (event.target !== overviewList()) {
      return;
    }
    moveFocus(event, railElement());
  }

  return {
    railRef,
    railMounted,
    railShown,
    presenceCardOpen: cardOpen,
    personFocus,
    focusTarget,
    focusPortrait,
    cardRows,
    cardKey,
    cardCaption,
    cardLabel,
    speaker,
    onRailActivate,
    onCardPick,
    onCardBack,
    onCompassTab,
    onRailTab,
    onOverviewTab,
  };
}
