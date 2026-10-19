// webclient-drawer-content-polish: drawer content hierarchy, honest art
// placement and empty states. No reference drawer stands a portrait column
// (the character's status moved into the party window, whose 狀態 hero names
// the viewed member from supplied fields only); an available-empty list
// shows the shared EmptyState while an unavailable panel keeps its registry
// reason; lineage rows carry their supplied root-node names; an unknown item
// stays neutral.

import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../AppClient.vue";
import EmptyState from "../components/EmptyState.vue";
import PartyBagTab from "../components/PartyBagTab.vue";
import PartyStatusTab from "../components/PartyStatusTab.vue";
import LineagePanel from "../components/LineagePanel.vue";
import LoreCodexDrawer from "../components/LoreCodexDrawer.vue";
import PartyWindow from "../components/PartyWindow.vue";
import QuestDrawer from "../components/QuestDrawer.vue";
import { glyphPath } from "../components/dock-icons.js";
import { useElosernStore } from "../stores/elosern.js";
import {
  CHARACTER_PANEL_SAMPLE,
  LORE_CODEX_PANEL_EMPTY_SAMPLE,
  LORE_CODEX_PANEL_UNAVAILABLE_SAMPLE,
  PARTY_INTERACT_TARGETS_SAMPLE,
  PARTY_PANEL_EMPTY_SAMPLE,
  QUEST_LOG_PANEL_EMPTY_SAMPLE,
  QUEST_LOG_PANEL_UNAVAILABLE_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  CHARACTER_PANEL_TITLED_SAMPLE,
} from "../stories/fixtures.js";
import { PARTY_BAG_INVENTORY_SAMPLE } from "../stories/fixtures/party_panels.js";
import * as fx from "./store/protocol_fixtures.js";

describe("EmptyState", () => {
  it("draws a decorative glyph, the headline and the guidance, and no control of its own", () => {
    const w = mount(EmptyState, { props: { glyph: "quests", headline: "目前沒有任務紀錄", guidance: "接取的任務會列在這裡。" } });
    expect(w.get(".empty-state__glyph").attributes("aria-hidden")).toBe("true");
    expect(w.get(".empty-state__glyph path").attributes("d")).toBe(glyphPath("quests"));
    expect(w.get(".empty-state__headline").text()).toBe("目前沒有任務紀錄");
    expect(w.get(".empty-state__guidance").text()).toBe("接取的任務會列在這裡。");
    expect(w.find("button").exists()).toBe(false);
    expect(w.find(".empty-state__actions").exists()).toBe(false);
  });
});

describe("available-empty versus unavailable drawer lists", () => {
  it("replaces the quest book's empty guidance with the registered reason", async () => {
    const w = mount(QuestDrawer, { props: { questLog: QUEST_LOG_PANEL_EMPTY_SAMPLE, services: SERVICES_PANEL_SAMPLE } });
    const empty = w.get('[data-testid="quest-drawer__empty"]');
    expect(empty.classes()).toContain("empty-state");
    expect(w.find('[data-testid="quest-drawer__unavailable"]').exists()).toBe(false);

    await w.setProps({ questLog: QUEST_LOG_PANEL_UNAVAILABLE_SAMPLE });
    expect(w.find('[data-testid="quest-drawer__empty"]').exists()).toBe(false);
    expect(w.find(".empty-state").exists()).toBe(false);
    const reason = w.get('[data-testid="quest-drawer__unavailable"]');
    expect(reason.text()).toBe(QUEST_LOG_PANEL_UNAVAILABLE_SAMPLE.reason.message);
    // No invented quest row or action: only the tab controls remain.
    expect(w.findAll('[data-testid^="quest-drawer__row--"]')).toHaveLength(0);
    expect(w.find('[data-testid="quest-drawer__actions"]').exists()).toBe(false);
    expect(w.findAll("button").every((button) => button.attributes("role") === "tab")).toBe(true);
  });

  it("keeps the codex's empty guidance and its unavailable reason distinct", () => {
    const empty = mount(LoreCodexDrawer, { props: { codex: LORE_CODEX_PANEL_EMPTY_SAMPLE } });
    expect(empty.get('[data-testid="lore-codex-drawer__empty"]').classes()).toContain("empty-state");
    const unavailable = mount(LoreCodexDrawer, { props: { codex: LORE_CODEX_PANEL_UNAVAILABLE_SAMPLE } });
    expect(unavailable.find(".empty-state").exists()).toBe(false);
    expect(unavailable.get('[data-testid="lore-codex-drawer__unavailable"]').text()).toBe(
      LORE_CODEX_PANEL_UNAVAILABLE_SAMPLE.reason.message,
    );
  });

  // webclient-party-bag-retire: the bag is the party window's 背包 tab.
  it("shows the bag tab's empty guidance in place of empty rows, and only the reason when unavailable", () => {
    const empty = mount(PartyBagTab, { props: { partyInventory: { ...PARTY_BAG_INVENTORY_SAMPLE, rows: [] }, memberId: 101 } });
    expect(empty.get('[data-testid="party-bag-tab__empty"]').classes()).toContain("empty-state");
    expect(empty.find('[data-testid="party-bag-tab__rows"]').exists()).toBe(false);
    const unavailable = mount(PartyBagTab, {
      props: { partyInventory: { schema_version: 1, available: false, reason: { code: "inventory_unavailable", message: "背包目前無法顯示。" } }, memberId: 101 },
    });
    expect(unavailable.find(".empty-state").exists()).toBe(false);
    expect(unavailable.get('[data-testid="party-window__tab-unavailable"]').text()).toBe("背包目前無法顯示。");
  });

  // webclient-party-window-member-tab: the party window replaced the party
  // drawer. An available, empty party is the commander plus the 空位 entry,
  // whose invite control is the only call to action; no guidance prose.
  it("presents an empty party as the commander and the 空位 invite, without guidance prose", async () => {
    const w = mount(PartyWindow, {
      attachTo: document.body,
      props: { party: PARTY_PANEL_EMPTY_SAMPLE, interactTargets: PARTY_INTERACT_TARGETS_SAMPLE, memoryScope: "polish" },
    });
    expect(w.findAll('[data-testid^="member-rail__entry--"]').map((n) => n.attributes("data-testid"))).toEqual([
      "member-rail__entry--42",
      "member-rail__entry--empty",
    ]);
    expect(w.find(".empty-state").exists()).toBe(false);
    await w.get('[data-testid="member-rail__entry--empty"]').trigger("click");
    expect(w.get('[data-testid="action-bar__btn--invite"]').attributes("aria-disabled")).toBeUndefined();
    w.unmount();
    const unavailable = mount(PartyWindow, {
      attachTo: document.body,
      props: { party: { schema_version: 3, available: false, reason: { code: "party_unavailable", message: "隊伍資訊目前無法顯示" } }, memoryScope: "polish" },
    });
    expect(unavailable.find(".empty-state").exists()).toBe(false);
    expect(unavailable.get('[data-testid="party-window__unavailable"]').text()).toBe("隊伍資訊目前無法顯示");
    unavailable.unmount();
    document.body.replaceChildren();
  });
});

describe("the 狀態 tab hero", () => {
  const COMMANDER = PARTY_PANEL_EMPTY_SAMPLE.slots[0];
  const mountHero = (props) =>
    mount(PartyStatusTab, { props: { member: COMMANDER, character: CHARACTER_PANEL_TITLED_SAMPLE, ...props } });

  it("names the viewed member with its composed title and guild rank", () => {
    const w = mountHero();
    const hero = w.get('[data-testid="party-status-tab__hero"]');
    expect(hero.get('[data-testid="party-status-tab__name"]').text()).toBe(COMMANDER.display_name);
    expect(hero.get('[data-testid="party-status-tab__title"]').text()).toBe(CHARACTER_PANEL_TITLED_SAMPLE.full_title);
    expect(hero.get('[role="img"]').attributes("aria-label")).toBe(`公會階級 ${CHARACTER_PANEL_TITLED_SAMPLE.guild.rank}`);
    // The window title lives only in the shared header.
    expect(w.text()).not.toContain("角色狀態");
  });

  it("omits every value the payload does not supply", () => {
    const w = mountHero({
      character: { ...CHARACTER_PANEL_SAMPLE, guild: { ...CHARACTER_PANEL_SAMPLE.guild, rank: null } },
    });
    const hero = w.get('[data-testid="party-status-tab__hero"]');
    expect(hero.find('[data-testid="party-status-tab__title"]').exists()).toBe(false);
    expect(hero.find('[data-testid="party-status-tab__guild"]').exists()).toBe(false);
    expect(hero.get('[data-testid="party-status-tab__name"]').text()).toBe(COMMANDER.display_name);
  });

  it("renders no character value from an unavailable character panel", () => {
    const w = mountHero({ character: { schema_version: 9, available: false, kind: "character", reason: { code: "x", message: "角色無法顯示" } } });
    expect(w.find('[data-testid="party-status-tab__title"]').exists()).toBe(false);
    expect(w.find('[data-testid="party-status-tab__guild"]').exists()).toBe(false);
    expect(w.get('[data-testid="party-window__tab-unavailable"]').text()).toBe("角色無法顯示");
  });
});

describe("lineage identity", () => {
  const node = (key, name) => ({ skill_key: key, display_name_zh: name, owned: true, usable: true, ready: false, level: 1, xp_into_level: 1, xp_to_next_level: 9, capped: false, prereq_text_zh: "", depth: 0 });
  const graph = (key, label, owned, total, nodes) => ({ graph_id: key, group_label_zh: label, root_keys: [key], owned_count: owned, total_count: total, consumed: false, nodes, edges: [] });

  it("shows each same-label graph's supplied root name beside its own count", () => {
    // File-local synthetic lineage rows (test-data-independence): invented
    // element prose outside the shipped lore universe, mirroring
    // overlays/lineage_panel.test.js.
    const w = mount(LineagePanel, {
      props: {
        lineage: {
          schema_version: 2, available: true, kind: "lineage", completed_count: 0, total_count: 4,
          graphs: [
            graph("a_root", "焰流", 1, 2, [node("a_root", "焰羽箭")]),
            graph("b_root", "焰流", 2, 3, [node("b_root", "焰潮波")]),
            graph("c_root", "馜流", 1, 1, [node("c_root", "馜流")]),
            graph("d_root", "潮流", 1, 1, []),
          ],
        },
      },
    });
    for (const [key, name, count] of [["a_root", "焰羽箭", "1/2"], ["b_root", "焰潮波", "2/3"]]) {
      const head = w.get(`[data-testid="lineage-graph-toggle-${key}"]`);
      expect(head.get(`[data-testid="lineage-graph-root-${key}"]`).text()).toBe(name);
      // Order inside the row: identity, then the owned/total count; no meter.
      const parts = [...head.element.children].map((el) => el.className.baseVal ?? el.className);
      expect(parts.slice(1)).toEqual(["lineage-graph__identity", "lineage-graph__count"]);
      expect(head.get(".lineage-graph__count").text()).toBe(count);
    }
    // A root name equal to the label, or no node at all, adds no subtitle.
    expect(w.find('[data-testid="lineage-graph-root-c_root"]').exists()).toBe(false);
    expect(w.find('[data-testid="lineage-graph-root-d_root"]').exists()).toBe(false);
    expect(w.find(".lineage-chain__meter").exists()).toBe(false);
  });
});

describe("inventory rarity", () => {
  it("frames a committed rarity and keeps a null presentation neutral", () => {
    const known = PARTY_BAG_INVENTORY_SAMPLE.rows.find((row) => row.presentation?.rarity === "rare");
    const unknown = { ...known, item_key: `${known.item_key}_unknown`, equipped_count: 0, slot: null, toggle: null, presentation: null };
    const w = mount(PartyBagTab, {
      props: { partyInventory: { ...PARTY_BAG_INVENTORY_SAMPLE, rows: [known, unknown] }, memberId: 101 },
    });
    const icon = (key) => w.get(`[data-testid="party-bag-tab__row--${key}"] .party-bag-tab__icon`);
    expect(icon(known.item_key).attributes("data-rarity")).toBe("rare");
    expect(icon(unknown.item_key).attributes("data-rarity")).toBe("unknown");
    // The row keeps its committed name; no rarity or kind is inferred.
    expect(w.get(`[data-testid="party-bag-tab__row--${unknown.item_key}"]`).text()).toContain(known.display_name);
  });
});

describe("drawer art in the client", () => {
  let store;
  let wrapper;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    store.setSender(fx.createFakeSender());
    wrapper = mount(AppClient, { attachTo: document.body });
    store.beginTransport(1);
    store.setConnected(true);
  });
  afterEach(() => {
    wrapper.unmount();
    document.body.replaceChildren();
  });

  it("stands no portrait column beside any reference drawer", async () => {
    const panels = { status: fx.statusPanel(), exploration: fx.explorationPanel(), context_actions: fx.explorationActions() };
    expect(store.receive(1, "ui_snapshot", [fx.snapshot({ panels, revision: 1 })]).accepted).toBe(true);
    await wrapper.vm.$nextTick();
    const seen = {};
    for (const name of ["skill", "shop", "quest", "lore", "status", "party"]) {
      store.openHudDrawer(name);
      await wrapper.vm.$nextTick();
      if (!wrapper.find('[data-testid="hud-drawer"]').exists()) continue;
      seen[name] = wrapper.find(".hud-drawer__art").exists();
      if (seen[name]) {
        // One state line; never a pending claim without a pending payload.
        expect(wrapper.get(".hud-drawer__art").text()).not.toContain("肖像生成中");
      }
      store.closeHudDrawer();
      await wrapper.vm.$nextTick();
    }
    // The party window (its own WindowFrame, reached by the "status" and
    // "party" names) carries the viewed member's portrait in its rail,
    // nameplate and 狀態 hero, never a drawer column; no other drawer is
    // about the player (webclient-party-status-tab).
    expect(Object.keys(seen).sort()).toEqual(["lore", "party", "quest", "shop", "skill", "status"]);
    for (const [name, hasArt] of Object.entries(seen)) {
      expect(hasArt, name).toBe(false);
    }
  });
});
