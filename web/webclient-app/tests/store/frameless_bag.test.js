// make-inventory-drawer-frameless: the store-level frameless 背包 contract.
// Both 背包 rows (the exploration root's and the services sub-dock root's)
// open the bag drawer as a client-local drawer open: the router's frame
// stack, current frame, breadcrumb, and sub-dock are unchanged by the open,
// no hosted service surface is recorded, and closing the bag (the single
// close entry every HudDrawer route funnels into) pops nothing and moves
// nothing. Hosted 公會／商店 pushes and every other drawer's close teardown
// keep their current behavior.
import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useElosernStore } from "../../stores/elosern.js";
import ServiceMenu from "../../lib/service_menu.js";
import { SERVICES_PANEL_SAMPLE } from "../../stories/fixtures.js";
import * as fx from "./protocol_fixtures.js";

function snapshotWithServices(revision = 1, wallet = 3240) {
  return {
    protocol_version: 1,
    presentation_epoch: fx.EPOCH_A,
    revision,
    mode: "exploration",
    panels: {
      status: fx.statusPanel(),
      exploration: fx.explorationPanel(),
      context_actions: fx.explorationActions(),
      services: {
        ...SERVICES_PANEL_SAMPLE,
        player: { ...SERVICES_PANEL_SAMPLE.player, wallet },
      },
    },
    layout_version: 1,
    server_time: fx.serverTime(),
  };
}

function trailTitles(router) {
  return router.trail().map((menu) => (menu && menu.title) || null);
}

describe("frameless 背包 drawer (store contract)", () => {
  let store;

  function openSession() {
    store.beginTransport(1);
    store.setConnected(true);
    const result = store.receive(1, "ui_snapshot", [snapshotWithServices()], {});
    expect(result.accepted).toBe(true);
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    store.setSender(fx.createFakeSender());
  });

  it("the exploration-root 背包 row opens the bag drawer with the router unchanged", () => {
    openSession();
    const depthBefore = store.router.depth();
    const trailBefore = trailTitles(store.router);
    const currentBefore = store.router.currentMenu();
    expect(store.focusItemByKey("inventory")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
    expect(store.view.hudDrawer).toBe("inventory");
    // The open touched nothing: no push, no sub-dock switch, no surface.
    expect(store.router.depth()).toBe(depthBefore);
    expect(trailTitles(store.router)).toEqual(trailBefore);
    // Declarative frames re-resolve per access (webclient-declarative-frame-
    // stack): the open is unchanged in content (deep-equal), not in object
    // identity — the drawer-open row must not mutate the frame.
    expect(store.router.currentMenu()).toEqual(currentBefore);
    expect(store.view.activeSubDock).toBe(null);
    expect(store.currentFrameIsServiceFrame()).toBe(false);
  });

  it("the services-root 背包 row opens the bag drawer without switching the dock, survives a services commit, and guild navigation still hosts afterwards", () => {
    openSession();
    // The store-constructed case (the standalone services root is not
    // mounted in production): the services sub-dock is active with its root
    // frame current, and its 背包 row is the raw model row.
    store.setActiveSubDock("services");
    store.router.pushFrame({ source: "services.root", params: {} });
    const depthBefore = store.router.depth();
    const trailBefore = trailTitles(store.router);
    expect(store.focusItemByKey("inventory")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
    expect(store.view.hudDrawer).toBe("inventory");
    expect(store.router.depth()).toBe(depthBefore);
    expect(trailTitles(store.router)).toEqual(trailBefore);
    expect(store.router.currentMenu().title).toBe("服務");
    expect(store.view.activeSubDock).toBe("services");
    // A services commit while the bag drawer is open records no hosted
    // surface and never switches (or re-hosts) the drawer.
    const result = store.receive(1, "ui_snapshot", [snapshotWithServices(2, 3300)], {});
    expect(result.accepted).toBe(true);
    expect(store.view.hudDrawer).toBe("inventory");
    expect(store.router.depth()).toBe(depthBefore);
    expect(trailTitles(store.router)).toEqual(trailBefore);
    // Closing leaves the dock where it is (the close must not silently
    // switch back to the exploration root).
    expect(store.closeHudDrawer({ popFrame: true })).toBe(true);
    expect(store.view.hudDrawer).toBe(null);
    expect(store.router.depth()).toBe(depthBefore);
    expect(trailTitles(store.router)).toEqual(trailBefore);
    expect(store.view.activeSubDock).toBe("services");
    // Normal 公會 navigation afterwards still pushes and hosts as before
    // (surface recorded at push time: the 任務板 row maps to the guild
    // surface, so its frame opens the 任務 drawer).
    expect(store.focusItemByKey("guild")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
    expect(store.router.depth()).toBe(depthBefore + 1);
    expect(store.focusItemByKey("board")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
    expect(store.router.depth()).toBe(depthBefore + 2);
    expect(store.router.currentMenu().title).toBe("任務板");
    expect(store.view.hudDrawer).toBe("quest");
  });

  it("公會 and 商店 activations still push and host their drawers (regression)", () => {
    openSession();
    // 公會: the exploration root's 任務 row pushes the guild quest-log
    // frame and the frame-hosting watcher opens the 任務 drawer.
    const depthBefore = store.router.depth();
    expect(store.focusItemByKey("quests")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
    expect(store.router.depth()).toBe(depthBefore + 1);
    expect(store.view.hudDrawer).toBe("quest");
    // 商店: the services root's 商店 row pushes the shop frame and hosts
    // the 商店 drawer (fresh session: back to the exploration root).
    setActivePinia(createPinia());
    store = useElosernStore();
    store.setSender(fx.createFakeSender());
    openSession();
    store.setActiveSubDock("services");
    store.router.pushFrame({ source: "services.root", params: {} });
    expect(store.focusItemByKey("shop")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
    expect(store.router.currentMenu().title).toBe("商店");
    // The 貨架 row records the shop surface at push time, so the frame-
    // hosting watcher opens the 商店 drawer beside its rows.
    expect(store.focusItemByKey("stock")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
    expect(store.router.currentMenu().title).toBe("貨架");
    expect(store.view.hudDrawer).toBe("shop");
  });

  it("closing the bag pops nothing and leaves the router exactly as the open found it", () => {
    openSession();
    const depthBefore = store.router.depth();
    const trailBefore = trailTitles(store.router);
    expect(store.focusItemByKey("inventory")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
    expect(store.view.hudDrawer).toBe("inventory");
    // The single close entry (every HudDrawer route funnels here with
    // popFrame: true) pops nothing and restores nothing to change.
    expect(store.closeHudDrawer({ popFrame: true })).toBe(true);
    expect(store.view.hudDrawer).toBe(null);
    expect(store.router.depth()).toBe(depthBefore);
    expect(trailTitles(store.router)).toEqual(trailBefore);
    expect(store.router.currentMenu().title).toBe("探索");
    expect(store.view.activeSubDock).toBe(null);
  });

  it("closing the bag over a current service frame leaves the router and the dock alone", () => {
    openSession();
    // The defensive state the frameless exclusion in AppClient also guards:
    // a service-titled frame is current while the bag drawer is open (no
    // production handler records a service surface for this state).
    store.setActiveSubDock("services");
    store.router.pushFrame({ source: "services.shop", params: {} });
    expect(store.currentFrameIsServiceFrame()).toBe(true);
    expect(store.openHudDrawer("inventory")).toBe(true);
    const depthBefore = store.router.depth();
    const trailBefore = trailTitles(store.router);
    expect(store.closeHudDrawer({ popFrame: true })).toBe(true);
    expect(store.view.hudDrawer).toBe(null);
    // No pop, no clear + re-home: the close left both alone.
    expect(store.router.depth()).toBe(depthBefore);
    expect(trailTitles(store.router)).toEqual(trailBefore);
    expect(store.router.currentMenu().title).toBe("商店");
    expect(store.view.activeSubDock).toBe("services");
  });

  it("the scoped exemption does not regress the other drawers' close teardown", () => {
    openSession();
    // 任務 (hosted): closing with popFrame pops one level AND clears the
    // services sub-dock + re-homes the exploration root, as today.
    expect(store.focusItemByKey("quests")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
    expect(store.view.hudDrawer).toBe("quest");
    const depthAtServiceFrame = store.router.depth();
    expect(store.closeHudDrawer({ popFrame: true })).toBe(true);
    expect(store.router.depth()).toBe(depthAtServiceFrame - 1);
    expect(store.view.activeSubDock).toBe(null);
    expect(store.router.currentMenu().title).toBe("探索");
  });

  it("opening an overlay over the bag closes the bag without touching the router or dock", () => {
    openSession();
    const depthBefore = store.router.depth();
    const trailBefore = trailTitles(store.router);
    expect(store.focusItemByKey("inventory")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
    expect(store.view.hudDrawer).toBe("inventory");
    // The overlay's mutual-exclusion close (closeHudDrawer({}) from
    // openOverlay) funnels through the same frameless early return.
    expect(store.openOverlay("help")).toBe(true);
    expect(store.view.hudDrawer).toBe(null);
    expect(store.view.hudOverlay).toBe("help");
    expect(store.router.depth()).toBe(depthBefore);
    expect(trailTitles(store.router)).toEqual(trailBefore);
    expect(store.view.activeSubDock).toBe(null);
  });

  it("the frameless 狀態 drawer close keeps clearing its character sub-dock (regression)", () => {
    openSession();
    // The 角色狀態 row opens the frameless status drawer with the character
    // sub-dock active; its close still clears the sub-dock and re-homes.
    expect(store.focusItemByKey("character")).toBe(true);
    expect(store.focusConfirm()).toBe(true);
    expect(store.view.hudDrawer).toBe("status");
    expect(store.view.activeSubDock).toBe("character");
    expect(store.closeHudDrawer({ popFrame: true })).toBe(true);
    expect(store.view.hudDrawer).toBe(null);
    expect(store.view.activeSubDock).toBe(null);
    expect(store.router.depth()).toBe(1);
    expect(store.router.currentMenu().title).toBe("探索");
  });
});
