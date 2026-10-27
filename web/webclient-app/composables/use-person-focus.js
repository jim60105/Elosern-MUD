// The presence rail's and the person focus's wiring (exploration-presence-rail
// design D2/D3/D4/D5): whether the rail stands on the stage, the centred
// card's rows (the verb card or the overflow card) through ChoiceCard, the
// one stage actor in `actor-right` (the dialogue host, else the person in
// focus), the message window's speaker line, focus restoration to the
// opener when a card closes, and the departed flash. The Tab chain across the
// exploration zones is use-room-actions.js's (exploration-room-actions). The
// card's state is the store's client-local slice
// (`store.view.presenceCard`); this composable owns no state of its own but
// the template refs.
//
// A target the rendered actor-left lineup already draws is represented once:
// `AppClient.vue` joins it by identity to the displayed figures, leaves
// `actor-right` empty for it and lights that figure through the companion
// speaking signal (reuse-lineup-person-focus D1/D2). Nothing about the card's
// lifecycle changes here: a committed target that leaves the room still clears
// the derived `focusTarget` at once, while the store's own commit-time
// settlement remains the only owner of closing the card and flashing the
// departure.
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
  // Only positions 1 through 9 advertise a digit shortcut (slice U). A later
  // row carries no badge at all — it stays reachable by arrows and scrolling,
  // never by a second numbering scheme and never by a digit that would
  // activate a different row.
  return index < 9 ? String(index + 1) : null;
}

// The verb card's rows: `verbMenuFor`'s rows (its own back row dropped) with
// digit badges and their group identity, then the trailing `✕ 返回` row.
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
      // The row's group identity and its real heading (a grouped card).
      group: item.group || null,
      groupLabel: item.groupLabel || null,
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
  // The interaction card itself: its rows and the mapping they draw.
  const cardRef = ref(null);

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
  // A room card (the wait or suggestions card, exploration-room-actions)
  // takes the stage the same way.
  const railShown = computed(() => railMounted.value && !cardOpen.value && !store.view.roomCard);

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

  // The standee in focus (design D3): the canonical descriptor its committed
  // exploration reference names, or null for the dialogue silhouette
  // treatment. The reference itself is the admission fact, so an unadmitted
  // target is expected absence and a dangling one is a local failure.
  const focusPortrait = computed(() => {
    const key = focusTarget.value?.portrait_ref;
    return key == null ? null : (panel("art")?.portrait_catalog?.[key]?.artwork ?? null);
  });

  function onRailActivate(key) {
    store.activatePresence(key);
  }

  // The card element's mapping token: the DOM copy of the mapping the rows
  // were drawn from. Reading it at activation time is what makes an
  // activation name what the player saw, not what the store has just
  // published.
  function renderedMappingToken() {
    if (typeof document === "undefined") {
      return null;
    }
    const el = document.querySelector('[data-anchor="choices"] [data-testid="presence-card"]');
    return el ? el.getAttribute("data-mapping-token") : null;
  }

  // The card's mapping as published for the rows currently drawn.
  const cardMappingToken = computed(() =>
    card.value ? (store.view.presenceMapping?.token ?? null) : null,
  );

  // The render that drew a mapping acknowledges it: a store-held digit press
  // (focus elsewhere) validates against the mapping the card shows.
  watch(
    cardMappingToken,
    (token) => {
      store.acknowledgePresenceMapping(token);
    },
    { flush: "post" },
  );

  function onCardPick(key) {
    if (!card.value) {
      return;
    }
    if (card.value.kind === "verbs") {
      store.activatePresenceVerb(key, renderedMappingToken());
    } else {
      store.activatePresence(key, renderedMappingToken());
    }
  }

  function onCardBack() {
    store.closePresenceCard();
  }

  // The entry a service flow was opened from, while the card still owns it.
  function serviceOriginKey() {
    const origin = store.view.presenceCard?.serviceOrigin;
    return personFocus.value && origin ? origin : null;
  }

  // Closing a service flow returns focus to its originating entry while the
  // actor, the card and that entry remain valid (slice U). Otherwise the
  // card's first valid row takes it; when the card itself is gone the
  // existing rail/compass fallback owns focus and this does nothing. Focus
  // that belongs to another valid surface is never stolen.
  async function returnToServiceOrigin() {
    const origin = serviceOriginKey();
    if (!origin || store.view.hudDrawer) {
      return false;
    }
    await nextTick();
    if (serviceOriginKey() !== origin || typeof document === "undefined") {
      return false;
    }
    const cardEl = cardRef.value?.$el ?? null;
    if (!cardEl) {
      return false;
    }
    const active = document.activeElement;
    const insideCard = !!active && (active === cardEl || cardEl.contains(active));
    const lost =
      !active || active === document.body || active === document.documentElement || !active.isConnected;
    if (!insideCard && !lost) {
      return false;
    }
    // A flow opened by a different acting body returns to the card's first
    // valid row instead of that entry.
    cardRef.value?.focusRow(store.presenceServiceOriginValid?.() === false ? null : origin);
    store.claimPresenceServiceOrigin();
    return true;
  }

  // The service drawer the card's own entry opened has closed: hand focus
  // back to that entry.
  watch(
    () => store.view.hudDrawer,
    (next, previous) => {
      if (next || !previous) {
        return;
      }
      void returnToServiceOrigin();
    },
  );

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
      // A room card that replaced the presence card owns focus now.
      if (next || !previous || store.view.mode !== "exploration" || store.view.roomCard) {
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

  function railElement() {
    return document.querySelector('[data-anchor="presence"] [data-testid="presence-rail"]');
  }

  return {
    railRef,
    cardRef,
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
    cardMappingToken,
    speaker,
    onRailActivate,
    onCardPick,
    onCardBack,
    returnToServiceOrigin,
  };
}
