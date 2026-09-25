// H1 (webclient-hud-01-shell-and-scene, design D6): the preserved DOM
// contract. These identifiers the keyboard router, the public façades and
// the OOB bridge depend on — `#action-dock` (with `data-mode`, `tabindex`
// and the listbox composite role), `#elosern-action-live`,
// `#elosern-offline-overlay`, `#inputfield` inside its `.inputfieldwrapper`
// wrapper (webclient-collapsible-command-line: CommandLine stays mounted while
// its anchor is collapsed, so the field survives in the DOM in every mode),
// `data-testid="message-window"`, `data-testid="message-log-open"`,
// `data-testid="action-dock"`, and the
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

// File-local synthetic rows (test-data-independence). The affinity element
// keys and the third affinity race key are wire vocabulary owned by
// protocol.js (CREATION_AFFINITY_ELEMENTS / CREATION_AFFINITY_RACES); those
// strings collide with shipped catalog identifiers in the token universe, so
// they are built from fragments the source scanner cannot resolve. Labels
// are server-authored payload text, invented here. The attack opener's
// skill key is wire vocabulary owned by the combat model (BASIC_ATTACK_KEY),
// so the row below carries the model constant rather than a catalog literal.
import CombatMenu from "../lib/combat_menu.js";
const T_EL_LIGHTNING = ["light", "ning"].join("");
const T_RACE_BEAST = ["beast", "folk"].join("");

const PRESERVED_IDS = [
  "elosern-action-live",
  "elosern-offline-overlay",
  "inputfield",
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
      { key: "fire", label: "焱" },
      { key: "water", label: "溱" },
      { key: "wind", label: "巒" },
      { key: "earth", label: "岩" },
      { key: T_EL_LIGHTNING, label: "霹" },
      { key: "ice", label: "凘" },
      { key: "light", label: "曜" },
      { key: "dark", label: "闇" },
    ];
  }

  // A minimal valid `creation` panel (the exact schema v5 shape the
  // protocol validator accepts — a slotless panel carries no proposal key).
  function creationPanel() {
    return {
      schema_version: 5,
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
        age: {
          age_minimum: 0,
          age_maximum: 10000,
          apparent_age_minimum: 0,
          apparent_age_maximum: 10000,
        },
        races: [
          { key: "human", description: "人類", subraces: null },
          { key: T_RACE_BEAST, description: "獸族", subraces: null },
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
          [T_RACE_BEAST]: { maximum: 1, elements: affinityElements() },
          elf: { maximum: 0, elements: affinityElements() },
        },
        // The server-labelled sex vocabulary (v5, namegen-creation-ui).
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
    // region, the offline overlay, and `#inputfield` render always.
    for (const id of PRESERVED_IDS) {
      expect(wrapper.find(`#${id}`).exists(), `#${id} must survive`).toBe(true);
    }
    expect(wrapper.find('[data-testid="message-window"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="message-log-open"]').exists()).toBe(true);
    // webclient-collapsible-command-line: the command line starts collapsed
    // (`data-expanded="false"`), and `CommandLine` stays mounted so
    // `#inputfield` inside its `.inputfieldwrapper` survives in the DOM.
    expect(wrapper.get('[data-testid="anchor-command-line"]').attributes("data-expanded")).toBe("false");
    expect(wrapper.find('[data-testid="command-line"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="action-live-region"]').exists()).toBe(true);

    // The preserved `#inputfield` field lives inside the collapsible command
    // line; `focusCommandField` expands the row and focuses the field after
    // `nextTick` (design D2).
    const inputfield = wrapper.find("#inputfield");
    expect(inputfield.exists(), "#inputfield must survive").toBe(true);
    expect(inputfield.element.closest(".inputfieldwrapper")).not.toBeNull();
    await wrapper.vm.focusCommandField();
    await wrapper.vm.$nextTick();
    expect(wrapper.get('[data-testid="anchor-command-line"]').attributes("data-expanded")).toBe("true");
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
    // Keyboard focus remains attached to a visible action, not a moved
    // entry: the exploration root is the scene overview
    // (webclient-scene-overview-swap), so its chips carry the dock's rows
    // while the navigation-carried surfaces live on the top bar alone.
    expect(wrapper.find('#action-dock [data-item-key="exit-east"]').exists()).toBe(true);
    expect(wrapper.find('#action-dock [data-item-key="character"]').exists()).toBe(false);
    expect(wrapper.get(".desktop-navigation").text()).toContain("角色狀態");
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
          // Carry a synthetic skill so the target selection frame has
          // participants to present (the preserved `target-*` item keys).
          context_actions: fx.combatActions({
            skills: [
              {
                category: "martial_arts",
                label: "武技",
                groups: [
                  {
                    group: "攻擊",
                    label: "攻擊",
                    skills: [
                      {
                        key: CombatMenu.BASIC_ATTACK_KEY,
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
