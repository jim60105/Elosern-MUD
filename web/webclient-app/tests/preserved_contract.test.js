// H1 (webclient-hud-01-shell-and-scene, design D6): the preserved DOM
// contract. These identifiers the keyboard router, the public façades and
// the OOB bridge depend on — `#action-dock` (with `data-mode`, `tabindex`
// and the listbox composite role), `#elosern-action-live`,
// `#elosern-offline-overlay`, `#inputfield` inside its `.inputfieldwrapper`
// wrapper (H5, webclient-hud-05-overlays-and-command-line, task 1.2: the
// command line is permanently present, so the field survives in every mode
// matrix that renders the command-line anchor), `#narrative-unread`,
// `data-testid="narrative-feed"`, `data-testid="action-dock"`, and the
// `action-*` / `target-*` item keys — are preserved unchanged by the stage
// restructure. The `layout_store.js` `REQUIRED_COMPONENTS` entry
// `command-drawer` is the one preserved layout-store identifier (the layout
// store's bounded wrapper still names the command-line component
// `command-drawer`; H5 retires the drawer's open/closed DOM state, not the
// layout-store key). A regression fails at the unit gate rather than in the
// browser suite (task 1.2), and the mounted AppClient keeps the dock contract
// intact in every committed mode (task 1.4).
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../AppClient.vue";
import AppShell from "../components/AppShell.vue";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";

const PRESERVED_IDS = [
  "elosern-action-live",
  "elosern-offline-overlay",
  "inputfield",
  "narrative-unread",
];

describe("H1 preserved DOM contract (design D6)", () => {
  let store;

  function mountAppShell() {
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    return mount(AppShell, { attachTo: host });
  }

  function mountAppClient() {
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    return mount(AppClient, { attachTo: host });
  }

  // The full eight-lore-element catalog the affinity validator requires
  // (exactly `CREATION_AFFINITY_ELEMENTS`).
  function affinityElements() {
    return [
      { key: "fire", label: "火" },
      { key: "water", label: "水" },
      { key: "wind", label: "風" },
      { key: "earth", label: "土" },
      { key: "lightning", label: "雷" },
      { key: "ice", label: "冰" },
      { key: "light", label: "光" },
      { key: "dark", label: "暗" },
    ];
  }

  // A minimal valid `creation` panel (the exact schema v4 shape the
  // protocol validator accepts — a slotless panel carries no proposal key).
  function creationPanel() {
    return {
      schema_version: 4,
      available: true,
      kind: "creation",
      draft: null,
      presets: [
        {
          key: "traveler",
          display_name: "旅人",
          race: "human",
          race_description: "穩健的人類",
          subrace: null,
          emphasis: "均衡",
          background: "出身霧骨渡口的旅人",
        },
      ],
      custom: {
        name: { min_length: 1, max_length: 64 },
        adult: {
          age_minimum: 18,
          age_maximum: 10000,
          apparent_age_minimum: 18,
          apparent_age_maximum: 10000,
        },
        races: [
          { key: "human", description: "人類", subraces: null },
          { key: "beastfolk", description: "獸族", subraces: null },
          { key: "elf", description: "精靈", subraces: null },
        ],
        subraces: {},
        profiles: [
          {
            race: "human",
            subrace: null,
            budget: 60,
            axes: [
              { axis: "hp", label: "生命", explanation: "生命上限", minimum: 0, maximum: 100 },
              { axis: "mp", label: "魔力", explanation: "魔力上限", minimum: 0, maximum: 100 },
              { axis: "sp", label: "耐力", explanation: "耐力上限", minimum: 0, maximum: 100 },
              { axis: "atk_phys", label: "攻擊", explanation: "物理攻擊", minimum: 0, maximum: 100 },
              { axis: "agility", label: "敏捷", explanation: "敏捷", minimum: 0, maximum: 100 },
              { axis: "defense", label: "防禦", explanation: "防禦力", minimum: 0, maximum: 100 },
              { axis: "magic_power", label: "魔力", explanation: "魔法傷害", minimum: 0, maximum: 100 },
            ],
          },
        ],
        // The affinity catalog is exactly the eight lore elements (the
        // validator requires the full set, not a subset), with the per-race
        // `maximum` matching the race bound.
        affinity: {
          human: { maximum: 2, elements: affinityElements() },
          beastfolk: { maximum: 1, elements: affinityElements() },
          elf: { maximum: 0, elements: affinityElements() },
        },
        // The server-labelled sex vocabulary (v4, namegen-creation-ui).
        sex: [
          { key: "female", label: "女性" },
          { key: "male", label: "男性" },
          { key: "other", label: "其他" },
        ],
      },
    };
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("AppShell keeps its preserved identifiers after the stage restructure", async () => {
    const wrapper = mountAppShell();
    await wrapper.vm.$nextTick();

    // The shell-level identifiers the restructure must not move: the live
    // region, the offline overlay, and the feed's unread marker render always.
    for (const id of ["elosern-action-live", "elosern-offline-overlay", "narrative-unread"]) {
      expect(wrapper.find(`#${id}`).exists(), `#${id} must survive`).toBe(true);
    }
    expect(wrapper.find('[data-testid="narrative-feed"]').exists()).toBe(true);
    // H5 (task 1.2): the command line is permanently present — the bar is
    // always rendered (no open/closed state), so `#inputfield` inside its
    // `.inputfieldwrapper` survives without any opening action.
    expect(wrapper.find('[data-testid="command-line"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="action-live-region"]').exists()).toBe(true);

    // The preserved `#inputfield` field lives inside the always-present
    // command line; focusing it is a side-effect-free claim (no drawer state
    // to toggle, design D1).
    const inputfield = wrapper.find("#inputfield");
    expect(inputfield.exists(), "#inputfield must survive").toBe(true);
    expect(inputfield.element.closest(".inputfieldwrapper")).not.toBeNull();
    wrapper.vm.focusCommandField();
    await wrapper.vm.$nextTick();
    expect(document.activeElement).toBe(inputfield.element);
    wrapper.unmount();
  });

  it("AppClient keeps #action-dock (data-mode, tabindex, listbox role) in exploration mode", async () => {
    const wrapper = mountAppClient();
    await wrapper.vm.$nextTick();
    store.beginTransport(1);
    store.setConnected(true);
    const res = store.receive(1, "ui_snapshot", [
      fx.snapshot({
        mode: "exploration",
        panels: {
          status: fx.statusPanel(),
          context_actions: fx.explorationActions(),
          // Declarative frames resolve from the committed `exploration`
          // panel (webclient-declarative-frame-stack): the protocol-reachable
          // exploration state always carries it, so the root frame renders
          // its G2 rows here.
          exploration: fx.explorationPanel(),
          local_map: fx.localMapPanel(),
        },
      }),
    ]);
    expect(res.accepted).toBe(true);
    await wrapper.vm.$nextTick();

    const dock = wrapper.find("#action-dock");
    expect(dock.exists(), "#action-dock must render in exploration").toBe(true);
    expect(dock.attributes("data-mode")).toBe("exploration");
    expect(dock.attributes("tabindex")).toBe("0");
    // The listbox composite role on the dock's menu (the preserved focus
    // target the keyboard router keeps using).
    expect(wrapper.find('[role="listbox"]').exists()).toBe(true);
    // A representative preserved item key on the exploration root frame.
    expect(wrapper.find('[data-item-key="character"]').exists()).toBe(true);
    wrapper.unmount();
  });

  it("AppClient keeps the combat target-* item keys in combat mode", async () => {
    const wrapper = mountAppClient();
    await wrapper.vm.$nextTick();
    store.beginTransport(1);
    store.setConnected(true);
    const res = store.receive(1, "ui_snapshot", [
      fx.snapshot({
        mode: "combat",
        panels: {
          status: fx.statusPanel(),
          // Carry a `basic_attack` skill so the target selection frame has
          // participants to present (the preserved `target-*` item keys).
          context_actions: fx.combatActions({
            skills: [
              {
                category: "innate_gift",
                label: "先天的",
                groups: [
                  {
                    group: "攻擊",
                    label: "攻擊",
                    skills: [
                      {
                        key: "basic_attack",
                        label: "攻擊",
                        description: "普通攻擊，無消耗。",
                        cost: {},
                        target_spec: "single",
                        element: null,
                        enabled: true,
                        disabled_reason: null,
                        targets: [7, 8],
                        shorthands: [],
                      },
                    ],
                  },
                ],
              },
            ],
          }),
        },
      }),
    ]);
    expect(res.accepted).toBe(true);
    await wrapper.vm.$nextTick();

    const dock = wrapper.find("#action-dock");
    expect(dock.exists(), "#action-dock must render in combat").toBe(true);
    expect(dock.attributes("data-mode")).toBe("combat");
    expect(dock.attributes("tabindex")).toBe("0");

    // Navigate the keyboard router from the combat root frame to the target
    // selection frame: focus the "attack" opener and confirm it, which pushes
    // the participant (target) menu.
    store.focusItemByKey("attack");
    store.focusConfirm();
    await wrapper.vm.$nextTick();
    // The combat target selection frame renders the preserved participant tokens.
    expect(wrapper.find('[data-item-key="target-7"]').exists()).toBe(true);
    expect(wrapper.find('[data-item-key="target-8"]').exists()).toBe(true);
    wrapper.unmount();
  });

  it("AppClient keeps #action-dock visible in creation mode (the creation form)", async () => {
    const wrapper = mountAppClient();
    await wrapper.vm.$nextTick();
    store.beginTransport(1);
    store.setConnected(true);
    const res = store.receive(1, "ui_snapshot", [
      fx.snapshot({
        mode: "creation",
        panels: {
          status: fx.statusPanel(),
          creation: creationPanel(),
        },
      }),
    ]);
    expect(res.accepted).toBe(true);
    await wrapper.vm.$nextTick();

    const dock = wrapper.find("#action-dock");
    expect(dock.exists()).toBe(true);
    expect(dock.attributes("data-mode")).toBe("creation");
    expect(wrapper.find('[data-testid="action-dock"]').exists()).toBe(true);
    wrapper.unmount();
  });
});
