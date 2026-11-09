// The reference-drawer layer (H4): the drawer chrome's derived head copy and
// the drawer close route. The shop window (webclient-shop-window) owns its
// WindowFrame chrome, like the party window.
// The quest drawer's counter honesty rules live in quest-drawer-model.js. Extracted verbatim from AppClient.vue so
// the SFC stays a passive renderer.
import { computed } from "vue";

export function useDrawers(store, { panel, panelAvailable }) {
  // H4 (task 7.4): the reference drawer layer. The drawer title/subtitle is
  // derived from the single open-drawer name the store publishes.
  const DRAWER_TITLES = {
    letters: "信件",
    quest: "手帳",
  };
  const drawerTitle = computed(() => DRAWER_TITLES[store.view.hudDrawer] || "");
  // The drawer head glyph (webclient-drawer-frame-unification): a
  // `dock-icons.js` registry key per drawer — the same key the navigation
  // control that opens it draws, so the header and its opener agree.
  const DRAWER_ICONS = {
    letters: "letters",
    quest: "quests",
  };
  const drawerIcon = computed(() => DRAWER_ICONS[store.view.hudDrawer] || null);
  // No reference drawer stands an art column (webclient-party-status-tab):
  // the handbook (with its codex tab) and the shop are not the
  // player, so they take the whole workspace width, and the character's
  // status moved into the party window, which owns its WindowFrame chrome
  // and carries portraits in its rail, nameplate and status hero.

  // A drawer opener (the 信件 tool) opens its reference drawer through the
  // store's single open-drawer entry point: at most one focus-trapped surface
  // is open at a time and the existing drawer teardown rules apply unchanged.
  // The world codex is the handbook's 圖鑑 tab (handbook-codex-tab), opened
  // through the handbook route request instead.
  function onOpenDrawer(name) {
    store.openHudDrawer(name);
  }

  // The drawer chrome's close entry (Escape / close control / scrim): route
  // through the store's single close entry.
  function onHudDrawerClose() {
    store.closeHudDrawer();
  }

  return {
    drawerTitle,
    drawerIcon,
    onHudDrawerClose,
    onOpenDrawer,
  };
}
