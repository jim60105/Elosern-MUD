// The reference-drawer layer (H4): the drawer chrome's derived head copy, the
// quest-drawer split honesty rules, the skill/inventory subtitles, the wallet
// figure, and the drawer close route. Extracted verbatim from AppClient.vue so
// the SFC stays a passive renderer.
import { computed } from "vue";
import { formatCopper } from "../components/character-identity.js";

export function useDrawers(store, { panel, panelAvailable }) {
  // H4 (task 7.4): the reference drawer layer. The drawer title/subtitle is
  // derived from the single open-drawer name the store publishes.
  const DRAWER_TITLES = {
    skill: "技能書",
    inventory: "背包 · 裝備",
    shop: "商店",
    quest: "任務",
    lore: "世界圖鑑",
    status: "角色狀態",
    party: "同伴 · 隊伍",
  };
  const drawerTitle = computed(() => DRAWER_TITLES[store.view.hudDrawer] || "");

  // The command line's 圖鑑 utility control (webclient-lore-codex-drawer)
  // opens the codex reference drawer through the store's single open-drawer
  // entry point: at most one focus-trapped surface is open at a time and the
  // existing drawer teardown rules apply unchanged.
  function onOpenDrawer(name) {
    store.openHudDrawer(name);
  }

  // The drawer chrome's close entry (Escape / close control / scrim): route
  // through the store's single close entry, popping exactly one menu level
  // when the drawer hosts a service frame (task 4.2).
  function onHudDrawerClose() {
    store.closeHudDrawer({ popFrame: true });
  }

  // quest-drawer-split: the quest drawer hosts the player's quest book
  // (QuestLog, host-free) above the guild counter (GuildCounter, host-gated).
  // The counter mounts only when the guild section is available; an
  // unavailable services panel renders its registry-owned reason verbatim
  // (a read-model failure is never mislabeled as clerk absence) and an
  // available panel with no guild section renders the explicit clerk-needed
  // marker — the away-from-clerk honesty the split exists for.
  const questServicesPanel = computed(() => panel("services") || null);
  const questGuildAvailable = computed(() => {
    const services = questServicesPanel.value;
    return !!services && services.available !== false && services.guild != null;
  });
  const questServicesUnavailable = computed(
    () => questServicesPanel.value?.available === false,
  );

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
    return `主動 ${skillCount(character?.actives)} · 被動 ${skillCount(character?.passives)}`;
  });

  // The inventory drawer's committed wallet figure (relocate-inventory-drawer-
  // essentials; realign-inventory-drawer-layout D3): the validated integer
  // copper from the `character` panel, null when:
  //  - the `services` panel is unavailable or its `inventory` section is
  //    absent (when the bag is unavailable or the section is absent the bag
  //    states its registry-owned reason / absent message and fabricates no
  //    wallet),
  //  - the `character` panel is unavailable or carries no valid non-negative
  //    integer balance (a missing or unavailable panel yields null — no
  //    balance, and never a zero).
  // The head subtitle and the bag's `金錢` row are both derived from this one
  // figure (`services.inventory.wallet` is never read), so the two renderings
  // of the drawer-layer wallet can never disagree.
  const inventoryWalletCopper = computed(() => {
    const services = panel("services");
    const servicesAvailable = !!services && services.available !== false;
    const inventorySection = services ? (services.inventory ?? null) : null;
    if (!servicesAvailable || inventorySection === null) {
      return null;
    }
    if (!panelAvailable("character")) {
      return null;
    }
    const character = panel("character");
    const wallet = character?.wallet;
    if (typeof wallet !== "number" || !Number.isInteger(wallet) || wallet < 0) {
      return null;
    }
    return wallet;
  });

  // The inventory drawer's head subtitle: the committed wallet figure above,
  // formatted as thousands-grouped integer copper (the shared
  // `character-identity.js` formatter, the same one the character head card
  // uses); blank for any other drawer or when the figure is null.
  const inventoryWalletSubtitle = computed(() => {
    if (store.view.hudDrawer !== "inventory") {
      return "";
    }
    const wallet = inventoryWalletCopper.value;
    if (wallet === null) {
      return "";
    }
    return `錢袋 ${formatCopper(wallet)} 銅`;
  });

  const partyReason = computed(() => {
    const p = panel("party");
    return p?.reason?.message || "隊伍資訊目前無法顯示";
  });

  // The skill drawer's footer: the client's own `/cast` syntax as static,
  // client-local presentation copy (no OOB field carries it).
  const SKILL_CAST_HINT = "施放入口：cast <技法>[@威力]=<代號>";

  return {
    SKILL_CAST_HINT,
    drawerTitle,
    inventoryWalletCopper,
    inventoryWalletSubtitle,
    onHudDrawerClose,
    onOpenDrawer,
    partyReason,
    questGuildAvailable,
    questServicesPanel,
    questServicesUnavailable,
    skillBookSubtitle,
  };
}
