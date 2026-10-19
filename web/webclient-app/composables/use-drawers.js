// The reference-drawer layer (H4): the drawer chrome's derived head copy, the
// skill subtitle, the member reference, and the drawer close route.
// The quest drawer's counter honesty rules live in quest-drawer-model.js. Extracted verbatim from AppClient.vue so
// the SFC stays a passive renderer.
import { computed } from "vue";

export function useDrawers(store, { panel, panelAvailable }) {
  // H4 (task 7.4): the reference drawer layer. The drawer title/subtitle is
  // derived from the single open-drawer name the store publishes.
  const DRAWER_TITLES = {
    letters: "信件",
    skill: "技能書",
    shop: "商店",
    quest: "任務",
    lore: "世界圖鑑",
    status: "角色狀態",
  };
  const drawerTitle = computed(() => DRAWER_TITLES[store.view.hudDrawer] || "");
  // The drawer head glyph (webclient-drawer-frame-unification): a
  // `dock-icons.js` registry key per drawer — the same key the navigation
  // control that opens it draws, so the header and its opener agree.
  const DRAWER_ICONS = {
    letters: "letters",
    skill: "skills",
    shop: "shop",
    quest: "quests",
    lore: "lore",
    status: "character",
  };
  const drawerIcon = computed(() => DRAWER_ICONS[store.view.hudDrawer] || null);
  // The drawer art column (webclient-drawer-content-polish): only a drawer
  // whose subject is the current character stands its portrait beside the
  // content. The codex, the quest log, the skill book and the shop are not
  // the player, so they take the whole workspace width instead of borrowing
  // an unrelated portrait or a stand-in illustration. The party window
  // (webclient-party-window-member-tab) owns its own WindowFrame chrome and
  // carries its art in the 成員 nameplate, so it is not a HudDrawer here.
  const DRAWER_ART_KEYS = new Set(["status"]);
  const drawerHasArt = computed(() => DRAWER_ART_KEYS.has(store.view.hudDrawer));

  // The command line's 圖鑑 utility control (webclient-lore-codex-drawer)
  // opens the codex reference drawer through the store's single open-drawer
  // entry point: at most one focus-trapped surface is open at a time and the
  // existing drawer teardown rules apply unchanged.
  function onOpenDrawer(name) {
    store.openHudDrawer(name);
  }

  // The drawer chrome's close entry (Escape / close control / scrim): route
  // through the store's single close entry.
  function onHudDrawerClose() {
    store.closeHudDrawer();
  }

  // The skill drawer's head subtitle: the owner's active/passive skill counts,
  // counted from the `character` panel exactly the way `SkillBook` counts its
  // rows (the counting logic moved up one level so the drawer head is the
  // single place the counts render). Empty when the drawer is not the skill
  // drawer or the `character` panel is missing/unavailable (degrade without
  // inventing data).
  function skillCount(rows) {
    let count = 0;
    for (const category of rows ?? []) {
      for (const group of category.groups ?? []) {
        count += (group.skills ?? []).length;
      }
    }
    return count;
  }
  const skillBookSubtitle = computed(() => {
    if (store.view.hudDrawer !== "skill" || !panelAvailable("character")) {
      return "";
    }
    const character = panel("character");
    return `主動 ${skillCount(character?.actives)} ‧ 被動 ${skillCount(character?.passives)}`;
  });

  // The member reference the member-scoped drawer controls name
  // (party-member-equipment, companion-field-item-use, party-practice-
  // booking): the controlled figure's identity from the committed `status`
  // panel, which serializes it as a string, converted to the positive safe
  // integer the exact payloads require. Null when that panel is missing or
  // unavailable — the item use, the equipment toggle and 修煉 then stay
  // unavailable instead of naming an invented member, and no other identity
  // (the commander included) is ever substituted.
  const controlledActorId = computed(() => {
    if (!panelAvailable("status")) {
      return null;
    }
    const identity = panel("status")?.actor?.identity;
    if (typeof identity !== "string" || identity.trim() === "") {
      return null;
    }
    const value = Number(identity);
    return Number.isSafeInteger(value) && value > 0 ? value : null;
  });

  // The skill drawer's footer: the book's keyboard guidance (client-local
  // presentation copy). The retired cast-syntax footer is gone: graphical
  // use and practice live in the book itself (skillbook-authoritative-casting).
  const SKILL_BOOK_KEY_HINT = "↑↓ 選擇 ‧ ←→ 收合／展開 ‧ Enter 前往動作 ‧ / 搜尋 ‧ Esc 關閉";

  return {
    SKILL_BOOK_KEY_HINT,
    controlledActorId,
    drawerTitle,
    drawerIcon,
    drawerHasArt,
    onHudDrawerClose,
    onOpenDrawer,
    skillBookSubtitle,
  };
}
