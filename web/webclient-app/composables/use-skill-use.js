// The 技能-tab use surface (skillbook-authoritative-casting D6,
// webclient-party-skill-tab): the tab's 施放 binding, its lock, its selection
// request, and the DOM-focus hand-over to the action dock once the store has
// closed the party window and mounted the dock-owned casting flow. The store
// owns every state transition; this group only binds them to the view.
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

  // The 技能 tab's selection rides `party.view_member` (the one selection
  // action): the server stores it for the viewed member, clears that
  // member's unread dot (tab `skills`), and republishes the character panel
  // with that skill's lineage and ladder. `skill_key` is null when no
  // registered active row is selected. Returns the admitted request id, or
  // null when the shared dispatch gate refused it (the tab retries).
  function onViewSkill(payload) {
    if (!payload || !Number.isSafeInteger(payload.member_id) || payload.member_id <= 0) {
      return null;
    }
    const skillKey = typeof payload.skill_key === "string" && payload.skill_key !== "" ? payload.skill_key : null;
    return store.dispatchAction("party.view_member", {
      member_id: payload.member_id,
      tab: "skills",
      skill_key: skillKey,
      item_key: null,
    });
  }

  // The dock flow takes DOM focus after the party window has unmounted, so
  // focus never lands on <body> or behind a trap.
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

  return { onSkillUse, onViewSkill, skillUseDockShown, skillUseLocked };
}
