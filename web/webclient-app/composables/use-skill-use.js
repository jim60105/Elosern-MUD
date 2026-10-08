// The SkillBook use surface (skillbook-authoritative-casting D6): the book's
// 施放 binding, its lock, and the DOM-focus hand-over to the action dock once
// the store has closed the book and mounted the dock-owned casting flow. The
// store owns every state transition; this group only binds them to the view.
import { computed, nextTick, watch } from "vue";

export function useSkillUse(store) {
  // 施放 shares the single dispatch lock with every other mutation.
  const skillUseLocked = computed(() => {
    const v = store.view;
    return !v.connected || v.phase !== "active" || v.mutationsLocked || !!v.dispatch?.inFlight;
  });

  function onSkillUse(skillKey) {
    const outcome = store.beginSkillUse(skillKey);
    if (outcome.route === "refused") {
      store.pushToast({ title: "目前無法施放，請稍後再試。", tone: "info" });
    }
  }

  // The dock flow (or the combat 技能 entry) takes DOM focus after the book's
  // drawer has unmounted, so focus never lands on <body> or behind a trap.
  watch(
    () => store.view.dockFocusRequest,
    async (request, previous) => {
      if (!request || request === previous) {
        return;
      }
      await nextTick();
      await nextTick();
      document.getElementById("action-dock")?.focus({ preventScroll: true });
    },
  );

  const skillUseDockShown = computed(() => !!store.view.skillUse);

  return { onSkillUse, skillUseDockShown, skillUseLocked };
}
