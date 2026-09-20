// The surface-interaction group of the composed Elosern store: the router
// submit handlers for the exploration and services surfaces, the dialogue
// caption/borrow seam, the creation-reset entry, and the keyboard-entry
// adapters (focusPress and friends).

import KeyboardRouter from "../../lib/keyboard_router.js";
import ServiceMenu from "../../lib/service_menu.js";
import { classifyPane } from "../../components/dock-panes.js";
import { dialogueViewModel } from "../dialogue-view.js";

export function applyInteraction(ctx) {
  // The caption digit activation (webclient-align-11-dialogue-ux, design D3):
  // while the committed `dialogue` panel is available, digits 1–4 address the
  // caption's scripted picks (the same ONE derived source the feed renders,
  // stores/dialogue-view.js), dispatching through the store's single
  // dispatchAction entry exactly like a pointer click on a pick. The free and
  // exit rows take no digit slot; an unavailable panel or an out-of-range
  // digit is unclaimed and falls through to the dock/command-line path.
  function handleCaptionDialoguePick(slot) {
    const rs = ctx.reducer.getState();
    if (rs.mode !== "dialogue") {
      return false;
    }
    const vm = dialogueViewModel((rs.panels && rs.panels.dialogue) || null);
    if (!vm) {
      return false;
    }
    const pick = vm.picks[slot];
    if (!pick || !pick.actionId) {
      return false;
    }
    ctx.dispatchAction(pick.actionId, pick.payload || {}, pick.commandDisplay || null);
    return true;
  }
  // Whether the caption variant claims digits right now: committed dialogue
  // mode with an available panel rendering at least one pick. While it
  // presents, the dock's own root rows are NOT digit-claimed (design D3 risk
  // note); an out-of-range digit is unclaimed and keeps command-line
  // semantics like any missing dock row.
  ctx.captionDialoguePresented = function captionDialoguePresented() {
    const rs = ctx.reducer.getState();
    if (rs.mode !== "dialogue") {
      return false;
    }
    const vm = dialogueViewModel((rs.panels && rs.panels.dialogue) || null);
    return !!(vm && vm.picks.length > 0);
  };

  // The free-dialogue borrow (the `→` key and the trailing free row): the
  // SAME path the exploration 互動 → 自由對話 row uses — set the guarded
  // freeform target to the committed host identity and request command-field
  // focus (the field is permanently present, design D1). Dispatches nothing.
  ctx.borrowDialogueCommand = function borrowDialogueCommand() {
    const rs = ctx.reducer.getState();
    const vm = dialogueViewModel((rs.panels && rs.panels.dialogue) || null);
    if (!vm) {
      return false;
    }
    ctx.freeformTarget = vm.host.identity;
    ctx.lastTarget = String(vm.host.identity);
    ctx.drawerRequest += 1;
    ctx.publishView();
    return true;
  };

  ctx.handleExplorationItem = function handleExplorationItem(item) {
    const rs = ctx.reducer.getState();
    if (!ctx.dockOnExplorationForm(rs)) {
      return false;
    }
    // A client-local drawer-open row (the frameless 背包 row, the
    // `openCharacter` precedent): open the drawer without pushing a frame,
    // switching the sub-dock, or recording a service surface.
    if (item.openDrawer === "inventory") {
      ctx.openHudDrawer("inventory");
      return true;
    }
    if (item.openSubmenu && ctx.EXPLORATION_SUBMENU_PUSHES[item.openSubmenu]) {
      // Declarative push (webclient-declarative-frame-stack): the frame is
      // ONLY the descriptor — the submenu content resolves at access time,
      // so a later commit reaches this open frame without any re-push.
      ctx.pushExplorationFrame(ctx.EXPLORATION_SUBMENU_PUSHES[item.openSubmenu], item.key);
      ctx.publishView();
      return true;
    }
    if (item.openCharacter) {
      ctx.setActiveSubDock("character");
      // H4 (task 4.2): the Character root opens the character-status drawer
      // (the re-homed character surface). The sub-dock flag is kept so the
      // dock's routing stays intact; the drawer is the new home of the
      // surface.
      ctx.openHudDrawer("status");
      return true;
    }
    if (item.openServiceSubmenu) {
      ctx.setActiveSubDock("services");
      // H4 (task 4.3): record the service surface at push time (design D2)
      // so the frame-hosting watcher routes to the matching reference drawer.
      // The submenu key maps to a service surface: "guild" / "shop" are
      // surfaces; "quests" is the guild's quest log (guild surface).
      const subKey = item.openServiceSubmenu;
      const surface =
        subKey === "quests" ? "guild" : (subKey === "guild" ? "guild" : subKey);
      ctx.setServiceSurface(surface);
      // Push the declarative service submenu (guild: register/board/quests/
      // exam; shop: 貨架/販賣) — the frame is ONLY the descriptor; content
      // resolves from the committed services panel at access time.
      ctx.pushFrame({ source: "services." + subKey, params: {} }, item.key);
      ctx.publishView();
      return true;
    }
    // A back row returns to the parent menu: pop exactly one router level
    // (the parent's focus key is its own frame state; the copy-driven dock
    // re-sync is gone — the parent frame re-resolves on the next read).
    if (item.goBack) {
      ctx.inStackMutation = true;
      try {
        ctx.router.popMenu();
      } finally {
        ctx.inStackMutation = false;
      }
      ctx.publishView();
      return true;
    }
    // An interact target row: push the target's declarative affordance frame.
    // The subject travels as the descriptor's `{identity}` — the SAME
    // server-authored identity the row carries — so the open frame follows
    // the committed panel (identity loss pops it; no client-local copy of
    // the selection is kept for exploration surfaces).
    if (item.openTarget != null) {
      ctx.pushExplorationFrame({ source: "exploration.target", params: { identity: item.openTarget } }, item.key);
      ctx.publishView();
      return true;
    }
    // The "talk-scripted" item opens the scripted-keyword menu for the target
    // of the CURRENT frame (G2: finite keyword buttons, not free text). The
    // identity comes from the open target frame's descriptor — one source,
    // never a second client-local selection.
    if (item.openKeywords) {
      const current = ctx.router.currentDescriptor();
      const identity = current && current.params ? current.params.identity : null;
      if (identity !== null && identity !== undefined) {
        ctx.pushExplorationFrame({ source: "exploration.keywords", params: { identity } }, item.key);
      }
      ctx.publishView();
      return true;
    }
    // The rest-duration item (openRestForm): opens the bounded custom-duration
    // form before any OOB action (webclient-exploration-menu: the form is the
    // sole local UI exception — confirm opens the form, no dispatch yet).
    if (item.openRestForm) {
      ctx.restFormRequest += 1;
      ctx.publishView();
      return true;
    }
    // A free-form dialogue item: open the command drawer for the selected
    // target; the typed speech submits as explore.talk_freeform with the
    // target's npc_id (the guarded dialogue seam, webclient-exploration-menu).
    if (item.freeform) {
      ctx.freeformTarget = item.npcId;
      ctx.lastTarget = String(item.npcId);
      ctx.drawerRequest += 1;
      ctx.publishView();
      return true;
    }
    // A real OOB exploration action (explore.move / look / wait / engage /
    // talk_scripted / talk_freeform): one dispatch through the single entry.
    // The item's server-authored `commandDisplay` descriptor is passed through
    // so the CommandEcho catalog resolves exactly one display line.
    if (item.actionId) {
      ctx.dispatchAction(item.actionId, item.payload || {}, item.commandDisplay || null);
      return true;
    }
    return false;
  };

  // Router submit for a services sub-dock item (the re-homed services surface):
  // board/quests/stock/sell/quest-N open bounded submenus, the 放棄 row opens the
  // explicit confirmation screen, and the action rows (register / accept / turnin /
  // exam / buy / sell) dispatch their `guild.*`/`shop.*` action. Returns true
  // when the item belonged to the services sub-dock.
  ctx.handleServiceItem = function handleServiceItem(item) {
    const rs = ctx.reducer.getState();
    if (!ctx.dockOnExplorationForm(rs) || ctx.activeSubDock.value !== "services") {
      return false;
    }
    // A client-local drawer-open row (the services root's frameless 背包
    // row): open the drawer without pushing a frame or recording a service
    // surface (the exploration-root branch above is the same interception).
    if (item.openDrawer === "inventory") {
      ctx.openHudDrawer("inventory");
      return true;
    }
    // A bounded services submenu (board / quests / stock / sell / quest-N):
    // push the declarative submenu frame; the per-quest detail pane (詳情 /
    // 放棄 / 回報) resolves per-index through the registry.
    if (item.openSubmenu) {
      // H4 (task 4.3): record the service surface at push time — the guild
      // frames (board / quests / quest-detail) route to the 任務 drawer and
      // the shop frames (stock / sell) route to the 商店 drawer.
      const subKey = item.openSubmenu;
      let descriptor = null;
      if (
        subKey === "guild" ||
        subKey === "shop" ||
        subKey === "board" ||
        subKey === "quests" ||
        subKey === "stock" ||
        subKey === "sell"
      ) {
        ctx.setServiceSurface(ctx.SERVICE_SURFACE_FOR_SOURCE["services." + subKey]);
        descriptor = { source: "services." + subKey, params: {} };
      } else if (subKey.startsWith("quest-")) {
        ctx.setServiceSurface("guild");
        // The quest-detail frame names its quest by the row INDEX the guild
        // quest rows carry (`quest-<i>`); the resolver re-reads that row from
        // the committed panel at every access (a vanished index pops it).
        const questIndex = Number(subKey.split("-")[1]);
        if (Number.isInteger(questIndex) && questIndex >= 0) {
          descriptor = { source: "services.quest-detail", params: { questIndex } };
        }
      }
      if (descriptor) {
        ctx.pushFrame(descriptor, item.key);
        ctx.publishView();
        return true;
      }
    }
    // The quest-detail 放棄 row: push the explicit confirmation menu (the
    // `.services-confirm` screen renders behind it; no mutation is sent yet).
    if (item.confirmActionId) {
      // H4 (task 4.3): the abandon confirmation frame belongs to the guild
      // (quest) surface.
      ctx.setServiceSurface("guild");
      // The confirmation frame names its quest by the CURRENT quest-detail
      // frame's index (the row the 放棄 belongs to) — the resolver composes
      // the same confirm menu from that row's server-authored fields on
      // every access. Falling back to index 0 only when no quest-detail
      // frame is current (unreachable through the UI; the row only exists
      // inside a quest-detail frame).
      const current = ctx.router.currentDescriptor();
      const questIndex =
        current && current.source === "services.quest-detail" && current.params
          ? current.params.questIndex
          : 0;
      ctx.pushFrame({ source: "services.confirm", params: { questIndex } }, item.key);
      ctx.publishView();
      return true;
    }
    // A bounded trade row (a stock/sell row carrying a `quantity` {min,max}):
    // open the local quantity form; the typed quantity is validated against the
    // bounds before the `shop.buy` / `shop.sell` dispatch.
    if (item.quantity) {
      ctx.openQuantityForm(item);
      return true;
    }
    // A services action row (guild.register / quest_accept / quest_turnin /
    // exam_start / shop.buy / shop.sell): dispatch the exact OOB action,
    // forwarding the row's server-authored display descriptor (buy/sell rows
    // carry `itemLabel`; the guild rows resolve from the payload alone).
    if (item.actionId) {
      ctx.dispatchAction(item.actionId, item.payload || {}, item.commandDisplay || null);
      return true;
    }
    return false;
  };

  // Open the destructive-reset confirmation (the creation dock's reset button
  // never dispatches `creation.reset` directly): the confirm stage renders the
  // `creation-confirm` screen and the router carries the confirm menu.
  ctx.requestCreationReset = function requestCreationReset() {
    if (!ctx.creation) {
      return false;
    }
    ctx.openCreationConfirm("reset", null, ctx.creation.view);
    ctx.publishView();
    return true;
  };

  ctx.focusPress = function focusPress(key, repeat) {
    // The bounded services quantity form (a local UI exception) captures its
    // own keys before the keyboard router: digits and Backspace edit the
    // bounded quantity, Enter submits a valid quantity (or keeps the form open
    // when the value is out of bounds), and Escape closes it.
    const q = ctx.quantityForm.value;
    if (q && q.open) {
      if (key >= "0" && key <= "9") {
        ServiceMenu.quantityInput(q.state, key);
        ctx.publishView();
        return true;
      }
      if (key === "Backspace") {
        ServiceMenu.quantityBackspace(q.state);
        ctx.publishView();
        return true;
      }
      if (key === "Escape") {
        q.open = false;
        ctx.publishView();
        return true;
      }
      if (key === "Enter") {
        const value = ServiceMenu.validateQuantity(q.state);
        if (value !== null) {
          ctx.dispatchAction(
            q.actionId,
            { item_key: q.itemKey, quantity: value },
            q.itemLabel ? { itemLabel: q.itemLabel } : null
          );
          q.open = false;
        }
        ctx.publishView();
        return true;
      }
      // Any other key while the form is open is consumed locally.
      return true;
    }
    // The dock's positional row picks (webclient-align-01-dock-chrome): the
    // legend `數字鍵 1-4 · Enter 執行 · Esc 返回` names the first four rows
    // of the current dock frame as reachable by the top-row number keys. A
    // digit moves the frame's focus onto its row (1-indexed, rendered
    // order) and activates it through the same confirm path Enter uses
    // (disabled rows show their explanation, in-flight rows stay locked,
    // repeats are suppressed by the router's guard). Focus moving is the
    // consumption signal: a digit whose row does not exist (a frame with
    // fewer rows, or the pre-session empty stack) is unclaimed and falls
    // through to the text / command-history path. Implemented entirely
    // through the frozen router façade members — the UMD source is not
    // edited (design D1).
    if (key === "1" || key === "2" || key === "3" || key === "4") {
      // A held or repeated digit is suppressed exactly like a held Enter
      // (the router's Enter repeat branch is the reference): the first
      // press already picked its row, and re-confirming on every
      // auto-repeat keydown could double-submit the instant the mutation
      // lock releases mid-hold.
      if (repeat) {
        return true;
      }
      const slot = Number(key) - 1;
      // The caption retarget (webclient-align-11-dialogue-ux, design D3):
      // while the dialogue caption presents picks, digits address the
      // caption's scripted picks, not the dock rows underneath. A panel with
      // no picks (or an unavailable one) keeps the dock digits untouched.
      if (ctx.captionDialoguePresented()) {
        return handleCaptionDialoguePick(slot);
      }
      if (ctx.router.depth() === 0) {
        return false;
      }
      const menu = ctx.router.currentMenu();
      // The slots address the RENDERED rows, not the raw item list: the
      // exit-outlet pane never renders the `back` cell (the breadcrumb
      // chevron owns the close control), so its row order excludes `back`
      // — the same rule DockMenu's outletRows applies (same classifier,
      // one source of truth). Every other pane renders `back` as an
      // ordered row, so its slot is real there.
      const items = menu && menu.items ? menu.items : [];
      const slots =
        classifyPane({ items }) === "outlet"
          ? items.filter((i) => i && i.key !== "back")
          : items;
      const item = slots[slot];
      if (!item) {
        return false;
      }
      const itemKey = item.key !== undefined ? item.key : item.label;
      if (!ctx.router.focusItemByKey(itemKey)) {
        return false;
      }
      // The activation itself may decline (disabled, locked, or the
      // held-repeat guard) after the focus moved; the key was still
      // consumed, exactly as a focused Enter that shows an explanation.
      ctx.router.confirm({ source: "keyboard" });
      return true;
    }
    return ctx.router.press(key, !!repeat);
  };

  ctx.focusConfirm = function focusConfirm(source) {
    return ctx.router.confirm({ source: source || "keyboard" });
  };

  ctx.focusEscape = function focusEscape() {
    // The Escape-key operation through the preserved public key-entry adapter
    // (`press` is a frozen façade member; the internal `escape` function is
    // not on the frozen instance surface). H3's breadcrumb back chevron and
    // the creation cancel-confirm both route through this same path.
    return ctx.router.press(KeyboardRouter.ESCAPE);
  };

  ctx.focusItemByKey = function focusItemByKey(key) {
    return ctx.router.focusItemByKey(key);
  };

  // Both navigation bars use the committed root's intents. Reference entries
  // live only in the top bar, so activating one must not focus a hidden row.
  ctx.tabToRootAndConfirm = function tabToRootAndConfirm(itemKey, source) {
    if (ctx.router.isMutationInFlight() || ctx.router.isAwaitingRevision()) return;
    while (ctx.router.depth() > 1) {
      if (!ctx.router.popMenu()) return;
    }
    const navigationItem = ctx.view.value.navigationItems.find((item) => item.key === itemKey);
    if (navigationItem) {
      if (!navigationItem.enabled) return;
      ctx.onRouterEvent("submit", { item: navigationItem, itemKey });
    } else if (ctx.router.focusItemByKey(itemKey)) {
      ctx.focusConfirm(source || "pointer");
    }
    ctx.publishView();
  };
}
