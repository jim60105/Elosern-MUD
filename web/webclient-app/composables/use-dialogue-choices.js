// The dialogue choice list's wiring (webclient-dialogue-choices-overlay
// D3/D4/D7/D8): when the list is shown, where its exit rows come from, and
// where focus goes around it. The list itself (DialogueChoices.vue) is
// passive; every dispatch goes through the store's single entry.
import { computed, nextTick, ref, watch } from "vue";

// The committed scene overview's exit items: the overview is the router's
// root frame in dialogue (webclient-talk-open-dock D1), and its `sections`
// geometry names how many leading items are exits, in reading order.
export function overviewExits(menu) {
  const items = Array.isArray(menu?.items) ? menu.items : [];
  const sections = Array.isArray(menu?.sections) ? menu.sections : [];
  let start = 0;
  for (const section of sections) {
    const count = Math.max(0, section.count || 0);
    if (section.key === "exits") {
      return items.slice(start, start + count);
    }
    start += count;
  }
  return [];
}

export function useDialogueChoices(store, shellRef, dialogueVM) {
  // The window's reader state (design D3), reported by `reading-change`.
  // True until the window says otherwise: a reconnect inside a conversation
  // shows the last page complete, so the choices show at once.
  const readingComplete = ref(true);
  function onReadingChange(complete) {
    readingComplete.value = !!complete;
  }

  // Design D4: the list shows only in dialogue with the panel available,
  // once the line is fully read, and never while an action is in flight (a
  // pick or free speech awaiting its reply).
  const choicesShown = computed(
    () =>
      store.view.mode === "dialogue" &&
      !!dialogueVM.value &&
      readingComplete.value &&
      store.view.dispatch.inFlight == null,
  );

  const dialogueExits = computed(() => overviewExits(store.view.rootMenu));

  // `↦ 移動…` then an exit row: the same payload and echo descriptor the
  // overview's exit chip submits (design D8).
  function onDialogueMove(item) {
    if (!item || !item.actionId) {
      return;
    }
    store.dispatchAction(item.actionId, item.payload || {}, item.commandDisplay || null);
  }

  // Design D7: park focus on the message page before an activation, so the
  // list's removal on the next render never drops it.
  function beforeChoiceActivate() {
    shellRef.value?.focusMessagePage?.();
  }

  // Design D7: when the list appears while focus sits on the message window
  // (its page, anywhere in the message region) or on the body, the list
  // takes it, first row active. Focus elsewhere (a drawer, an overlay, the
  // command field) is never stolen.
  watch(
    choicesShown,
    async (shown) => {
      if (!shown) {
        return;
      }
      await nextTick();
      const list = document.querySelector('[data-anchor="choices"] [data-testid="dialogue-choices"]');
      const active = document.activeElement;
      const onWindow =
        !active ||
        active === document.body ||
        active === document.documentElement ||
        !active.isConnected ||
        !!active.closest?.('[data-anchor="band-message"]');
      if (list && onWindow) {
        list.focus({ preventScroll: true });
      }
    },
    { flush: "post" },
  );

  return {
    readingComplete,
    onReadingChange,
    choicesShown,
    dialogueExits,
    onDialogueMove,
    beforeChoiceActivate,
  };
}
