// webclient-dialogue-stage-actors (design D4/D6): the command region
// collapses in dialogue mode. The dock stays the same mounted element with
// its ordinary exploration root (the overview reset of C9b), hidden by the
// stage CSS; the store's keyboard entry claims only `/` and the dialogue
// picks' digits, so no key moves the hidden router, pushes or pops a frame,
// or emits a `ui_action`. The dock renders no dialogue form and no dialogue
// legend variant.
import { h } from "vue";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import ActionDock from "../components/ActionDock.vue";
import SceneOverview from "../components/SceneOverview.vue";
import ExplorationMenu from "../lib/exploration_menu.js";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";

const DIALOGUE_PANEL = {
  schema_version: 2,
  available: true,
  kind: "dialogue",
  host: { identity: 41, display_name: "灰婆婆", portrait_ref: null },
  bond_stage: "親睦",
  line: "「渡河要五枚銅板。」",
  choices: [
    { keyword_id: "fare", label: "「就五枚，走嗎？」" },
    { keyword_id: "smell", label: "含糊帶過氣味" },
  ],
};

describe("the command region collapses in dialogue mode (store keys)", () => {
  let store;
  let sender;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
    store.beginTransport(1);
    store.setConnected(true);
    store.setLoggedIn(true);
    const panels = {
      status: fx.statusPanel(),
      exploration: fx.explorationPanel(),
      local_map: fx.localMapPanel(),
    };
    expect(store.receive(1, "ui_snapshot", [fx.snapshot({ panels })], {}).accepted).toBe(true);
    expect(
      store.receive(
        1,
        "ui_snapshot",
        [fx.snapshot({ revision: 4, mode: "dialogue", panels: { ...panels, dialogue: DIALOGUE_PANEL } })],
        {},
      ).accepted,
    ).toBe(true);
    expect(store.view.mode).toBe("dialogue");
  });

  it("claims no navigation, confirm, toggle, or back key: the hidden router never moves", () => {
    const focusBefore = store.view.focus.key;
    const depthBefore = store.router.depth();
    for (const key of ["ArrowRight", "ArrowLeft", "ArrowUp", "ArrowDown", "Enter", " ", "Escape"]) {
      expect(store.focusPress(key, false), key).toBe(false);
    }
    expect(store.view.focus.key).toBe(focusBefore);
    expect(store.router.depth()).toBe(depthBefore);
    expect(store.view.dockDepth).toBe(1);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("still claims `/`, which opens the command line", () => {
    const before = store.view.drawerRequest;
    expect(store.focusPress("/", false)).toBe(true);
    expect(store.view.drawerRequest).toBe(before + 1);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("keeps the exploration overview as the dock's only frame and shows it again on leaving", () => {
    expect(store.view.dockDepth).toBe(1);
    expect(store.view.rootMenu.items.map((item) => item.key)).toContain("exit-east");
    store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          revision: 5,
          panels: { status: fx.statusPanel(), exploration: fx.explorationPanel(), local_map: fx.localMapPanel() },
        }),
      ],
      {},
    );
    expect(store.view.mode).toBe("exploration");
    expect(store.view.dockDepth).toBe(1);
    // Back in exploration the router owns the arrows again.
    expect(store.focusPress("ArrowRight", false)).toBe(true);
  });
});

describe("the collapsed dock keeps its ordinary form", () => {
  const ROOT_ITEMS = [
    { key: "exit-east", label: "西風酒館", enabled: true },
    { key: "target-7", label: "店長", enabled: true },
    { key: "wait", label: "等待／休息", enabled: true },
  ];
  const VIEW = { dockDepth: 1, dockTrail: [], activeSubDock: null };
  const OVERVIEW = ExplorationMenu.overviewMenu(fx.explorationPanel(), {
    currentNode: "room:42",
    suggestions: null,
  });
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  it("renders the overview and the single ordinary legend, never a dialogue form", () => {
    wrapper = mount(ActionDock, {
      props: { mode: "dialogue", rootItems: ROOT_ITEMS, view: VIEW },
      slots: { default: () => [h(SceneOverview, { menu: OVERVIEW })] },
    });
    expect(wrapper.find('[data-pane-kind="commands"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="scene-overview"]').exists()).toBe(true);
    const legends = wrapper.findAll('[data-testid="action-dock-description"]');
    expect(legends).toHaveLength(1);
    expect(legends[0].text()).toBe("數字鍵 1–9 ‧ Enter 執行 ‧ Esc 返回");
    expect(wrapper.text()).not.toContain("對話選項");
    expect(wrapper.text()).not.toContain("指令列自由對話");
  });
});
