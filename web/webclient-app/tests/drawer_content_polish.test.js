// webclient-drawer-content-polish: drawer content hierarchy, honest art
// placement and empty states. A drawer stands the current character's
// portrait only when that character is its subject; the status hero names
// the committed character from supplied fields only; an available-empty list
// shows the shared EmptyState while an unavailable panel keeps its registry
// reason; lineage rows carry their supplied root-node names; an unknown item
// stays neutral.

import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../AppClient.vue";
import CharacterStatusDrawer from "../components/CharacterStatusDrawer.vue";
import EmptyState from "../components/EmptyState.vue";
import InventoryPanel from "../components/InventoryPanel.vue";
import LineagePanel from "../components/LineagePanel.vue";
import LoreCodexDrawer from "../components/LoreCodexDrawer.vue";
import PartyDrawer from "../components/PartyDrawer.vue";
import QuestLog from "../components/QuestLog.vue";
import { glyphPath } from "../components/dock-icons.js";
import { useElosernStore } from "../stores/elosern.js";
import {
  CHARACTER_PANEL_SAMPLE,
  LORE_CODEX_PANEL_EMPTY_SAMPLE,
  LORE_CODEX_PANEL_UNAVAILABLE_SAMPLE,
  PARTY_INTERACT_TARGETS_SAMPLE,
  QUEST_LOG_PANEL_EMPTY_SAMPLE,
  QUEST_LOG_PANEL_UNAVAILABLE_SAMPLE,
  SERVICES_PANEL_PRESENTATION_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  SERVICES_PANEL_UNAVAILABLE_SAMPLE,
  STATUS_PANEL_TITLED_SAMPLE,
} from "../stories/fixtures.js";
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
    const w = mount(QuestLog, { props: { questLog: QUEST_LOG_PANEL_EMPTY_SAMPLE, services: SERVICES_PANEL_SAMPLE } });
    const empty = w.get('[data-testid="quest-log__empty"]');
    expect(empty.classes()).toContain("empty-state");
    expect(w.find('[data-testid="quest-log__unavailable"]').exists()).toBe(false);

    await w.setProps({ questLog: QUEST_LOG_PANEL_UNAVAILABLE_SAMPLE });
    expect(w.find('[data-testid="quest-log__empty"]').exists()).toBe(false);
    expect(w.find(".empty-state").exists()).toBe(false);
    const reason = w.get('[data-testid="quest-log__unavailable"]');
    expect(reason.text()).toBe(QUEST_LOG_PANEL_UNAVAILABLE_SAMPLE.reason.message);
    // No invented quest row or action.
    expect(w.find("button").exists()).toBe(false);
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

  it("shows the bag's empty guidance in place of an empty grid, and only the reason when unavailable", () => {
    const services = structuredClone(SERVICES_PANEL_SAMPLE);
    services.inventory.rows = [];
    const empty = mount(InventoryPanel, { props: { services, character: CHARACTER_PANEL_SAMPLE, wallet: CHARACTER_PANEL_SAMPLE.wallet } });
    expect(empty.get('[data-testid="inventory-panel__empty"]').classes()).toContain("empty-state");
    expect(empty.find('[data-testid="inventory-panel__grid"]').exists()).toBe(false);
    const unavailable = mount(InventoryPanel, { props: { services: SERVICES_PANEL_UNAVAILABLE_SAMPLE, character: CHARACTER_PANEL_SAMPLE } });
    expect(unavailable.find(".empty-state").exists()).toBe(false);
    expect(unavailable.find('[data-testid="inventory-panel__unavailable"]').exists()).toBe(true);
  });

  it("adds the party's empty guidance above the unchanged 空位 row with its invite control", () => {
    const w = mount(PartyDrawer, {
      props: { slots: [], combatParticipants: [], interactTargets: PARTY_INTERACT_TARGETS_SAMPLE, mode: "exploration" },
    });
    const empty = w.get('[data-testid="party-drawer__empty"]');
    expect(empty.find("button").exists()).toBe(false);
    const row = w.get('[data-testid="party-drawer__empty-row"]');
    expect(row.find('[data-testid="party-drawer__invite-btn"]').exists()).toBe(true);
    expect(empty.element.compareDocumentPosition(row.element) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    const unavailable = mount(PartyDrawer, { props: { slots: [], available: false, reason: "隊伍資訊目前無法顯示" } });
    expect(unavailable.find(".empty-state").exists()).toBe(false);
    expect(unavailable.get('[data-testid="party-drawer__unavailable"]').text()).toBe("隊伍資訊目前無法顯示");
  });
});

describe("the character-status hero", () => {
  const mountHero = (props) =>
    mount(CharacterStatusDrawer, { props: { status: STATUS_PANEL_TITLED_SAMPLE, character: CHARACTER_PANEL_SAMPLE, ...props } });

  it("names the committed character with its title and rank above one action row", () => {
    const w = mountHero({ partyAvailable: true });
    const hero = w.get('[data-testid="character-status-drawer__hero"]');
    expect(hero.get('[data-testid="character-status-drawer__name"]').text()).toBe(STATUS_PANEL_TITLED_SAMPLE.actor.name);
    expect(hero.get('[data-testid="character-status-drawer__full-title"]').text()).toBe(STATUS_PANEL_TITLED_SAMPLE.actor.full_title);
    expect(hero.get('[data-testid="character-status-drawer__hero-rank"]').text()).toBe(`公會階級 ${CHARACTER_PANEL_SAMPLE.guild.rank}`);
    const actions = hero.get('[role="group"]');
    expect(actions.findAll("button").map((b) => b.attributes("data-testid"))).toEqual([
      "character-status-drawer__open-skill",
      "character-status-drawer__open-party",
    ]);
    // The drawer title lives only in the shared header.
    expect(w.text()).not.toContain("角色狀態");
  });

  it("omits every value the payload does not supply", () => {
    const w = mountHero({
      status: { ...STATUS_PANEL_TITLED_SAMPLE, actor: { ...STATUS_PANEL_TITLED_SAMPLE.actor, name: " ", full_title: undefined } },
      character: { ...CHARACTER_PANEL_SAMPLE, guild: { ...CHARACTER_PANEL_SAMPLE.guild, rank: null } },
    });
    const hero = w.get('[data-testid="character-status-drawer__hero"]');
    expect(hero.find('[data-testid="character-status-drawer__name"]').exists()).toBe(false);
    expect(hero.find('[data-testid="character-status-drawer__full-title"]').exists()).toBe(false);
    expect(hero.find('[data-testid="character-status-drawer__hero-rank"]').exists()).toBe(false);
    expect(hero.find('[data-testid="character-status-drawer__open-skill"]').exists()).toBe(true);
  });

  it("renders no identity from an unavailable status panel", () => {
    const w = mountHero({ status: { schema_version: 2, available: false, kind: "status", reason: { code: "x", message: "狀態無法顯示" } } });
    expect(w.find('[data-testid="character-status-drawer__name"]').exists()).toBe(false);
    expect(w.find('[data-testid="character-status-drawer__full-title"]').exists()).toBe(false);
  });
});

describe("lineage identity", () => {
  const node = (key, name) => ({ skill_key: key, display_name_zh: name, owned: true, usable: true, level: 1, xp_into_level: 1, xp_to_next_level: 9, capped: false, prereq_text_zh: "" });
  const chain = (key, label, meter, nodes) => ({ root_skill_key: key, element_or_style_zh: label, consumed: false, meter, nodes });

  it("shows each same-label chain's supplied root name beside its own progress", () => {
    const w = mount(LineagePanel, {
      props: {
        lineage: {
          schema_version: 1, available: true, kind: "lineage", completed_count: 0, total_count: 4,
          chains: [
            chain("a_root", "火", 0.4, [node("a_root", "火焰箭")]),
            chain("b_root", "火", 0.8, [node("b_root", "火球術")]),
            chain("c_root", "風", 0.1, [node("c_root", "風")]),
            chain("d_root", "水", 0.2, []),
          ],
        },
      },
    });
    for (const [key, name, pct] of [["a_root", "火焰箭", "40%"], ["b_root", "火球術", "80%"]]) {
      const head = w.get(`[data-testid="lineage-chain-toggle-${key}"]`);
      expect(head.get(`[data-testid="lineage-chain-root-${key}"]`).text()).toBe(name);
      // Order inside the row: identity, then the meter, then the figure.
      const parts = [...head.element.children].map((el) => el.className.baseVal ?? el.className);
      expect(parts.slice(1)).toEqual(["lineage-chain__identity", "lineage-chain__meter", "lineage-chain__percent"]);
      expect(head.get(".lineage-chain__percent").text()).toBe(pct);
    }
    // A root name equal to the label, or no node at all, adds no subtitle.
    expect(w.find('[data-testid="lineage-chain-root-c_root"]').exists()).toBe(false);
    expect(w.find('[data-testid="lineage-chain-root-d_root"]').exists()).toBe(false);
  });
});

describe("inventory rarity", () => {
  it("frames a committed rarity and keeps a null presentation neutral", () => {
    const services = structuredClone(SERVICES_PANEL_PRESENTATION_SAMPLE);
    const known = services.inventory.rows.find((r) => r.presentation?.rarity === "rare");
    const unknown = { ...known, item_key: `${known.item_key}_unknown`, presentation: null, action: null };
    services.inventory.rows = [known, unknown];
    const w = mount(InventoryPanel, { props: { services, character: CHARACTER_PANEL_SAMPLE, wallet: CHARACTER_PANEL_SAMPLE.wallet } });
    expect(w.get(`[data-testid="inventory-panel__tile--${known.item_key}"]`).attributes("data-rarity")).toBe("rare");
    const tile = w.get(`[data-testid="inventory-panel__tile--${unknown.item_key}"]`);
    expect(tile.attributes("data-rarity")).toBe("unknown");
    expect(tile.attributes("data-unknown")).toBe("true");
    expect(tile.text()).toContain("未知");
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

  it("stands the portrait column only beside the character's own drawers", async () => {
    const panels = { status: fx.statusPanel(), exploration: fx.explorationPanel(), context_actions: fx.explorationActions() };
    expect(store.receive(1, "ui_snapshot", [fx.snapshot({ panels, revision: 1 })]).accepted).toBe(true);
    await wrapper.vm.$nextTick();
    const seen = {};
    for (const name of ["skill", "inventory", "shop", "quest", "lore", "status", "party"]) {
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
    expect(seen.status).toBe(true);
    expect(seen.quest).toBe(false);
    for (const [name, hasArt] of Object.entries(seen)) {
      expect(hasArt, name).toBe(["status", "inventory", "party"].includes(name));
    }
  });
});
