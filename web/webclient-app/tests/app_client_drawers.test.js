// H4 (webclient-hud-04-reference-drawers, task 7.7): the reference-drawer
// layer contract. Asserts (1) no reference surface is in the DOM while every
// drawer is closed, (2) each reference surface is reachable in at most two
// actions from the dock root (the store's single openHudDrawer call is one
// action), and (3) across the whole drawer layer the party purse renders
// exactly once — the party window's header, from the committed
// `party_inventory` panel — and nowhere else (webclient-party-bag-retire).
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../AppClient.vue";
import StatusPanel from "../components/StatusPanel.vue";
import {
  CHARACTER_PANEL_SAMPLE,
  QUEST_LOG_PANEL_SAMPLE,
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  SERVICES_PANEL_UNAVAILABLE_SAMPLE,
  SKILLS_SLICE_SAMPLE,
  PARTY_MEMBER_PANEL_SAMPLE,
} from "../stories/fixtures.js";
import { resetQuestDrawerMemory } from "../components/quest-drawer-memory.js";
import { resetPartyWindowMemory } from "../components/party-window-memory.js";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";
import {
  PARTY_PANEL_EMPTY_SAMPLE,
  PARTY_PANEL_FULL_SAMPLE,
  PARTY_PANEL_SAMPLE,
  PARTY_BAG_INVENTORY_SAMPLE,
  PARTY_WINDOW_PANEL_SAMPLE,
} from "../stories/fixtures/party_panels.js";
import { CHARACTER_SKILL_COMPANION_SAMPLE } from "../stories/fixtures/skill_tab_panels.js";

describe("H4 reference-drawer layer (task 7.7)", () => {
  let store;
  let wrapper;

  function mountAppClient() {
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    wrapper = mount(AppClient, { attachTo: host });
    return wrapper;
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    resetQuestDrawerMemory();
    resetPartyWindowMemory();
  });

  // The closed reference-drawer name -> the body's root testid.
  const REFERENCE_SURFACES = {
    shop: "shop-window",
    quest: "quest-drawer",
    lore: "lore-codex-drawer",
    party: "party-window",
  };

  it("renders no reference surface in the DOM while every drawer is closed", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    // The drawer chrome mounts only while a drawer is open (HudDrawer v-if).
    expect(wrapper.find('[data-testid="hud-drawer"]').exists()).toBe(false);
    for (const testid of Object.values(REFERENCE_SURFACES)) {
      expect(wrapper.find(`[data-testid="${testid}"]`).exists(), testid).toBe(false);
    }
  });

  it("makes each reference surface reachable in at most two actions from the dock root", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    for (const [name, testid] of Object.entries(REFERENCE_SURFACES)) {
      // One deliberate openHudDrawer call = one action (within the 2-action bound).
      store.openHudDrawer(name);
      await wrapper.vm.$nextTick();
      expect(store.view.hudDrawer).toBe(name);
      expect(wrapper.find(`[data-testid="${testid}"]`).exists(), name).toBe(true);
    }
    // The retired character-status drawer's name opens the party window on
    // its 狀態 tab (webclient-party-status-tab) in the same one action.
    store.closeHudDrawer();
    store.openHudDrawer("status");
    await wrapper.vm.$nextTick();
    expect(store.view.hudDrawer).toBe("party");
    expect(wrapper.get('[data-testid="party-window"]').attributes("data-tab")).toBe("status");
    // The retired skill-book drawer's name opens it on 技能
    // (webclient-party-skill-tab) in the same one action.
    store.closeHudDrawer();
    store.openHudDrawer("skill");
    await wrapper.vm.$nextTick();
    expect(store.view.hudDrawer).toBe("party");
    expect(wrapper.get('[data-testid="party-window"]').attributes("data-tab")).toBe("skills");
    expect(wrapper.find('[data-testid="skill-book"]').exists()).toBe(false);
  });

  // webclient-party-bag-retire: the retired bag drawer's wallet became the
  // party purse, rendered once in the party window's header from the
  // committed `party_inventory` panel and nowhere else in the drawer layer.
  function commitPurse(partyInventory) {
    store.beginTransport(1);
    store.setConnected(true);
    store.receive(1, "ui_snapshot", [
      fx.snapshot({
        panels: {
          character: CHARACTER_PANEL_SAMPLE,
          party: PARTY_WINDOW_PANEL_SAMPLE,
          party_inventory: partyInventory,
          services: SERVICES_PANEL_SAMPLE,
        },
      }),
    ]);
  }

  it("renders the party purse exactly once, in the party window header, and nowhere else", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    commitPurse(PARTY_BAG_INVENTORY_SAMPLE);
    await wrapper.vm.$nextTick();
    // The 背包 opener lands on the party window's bag tab.
    store.openHudDrawer("inventory");
    await wrapper.vm.$nextTick();
    expect(store.view.hudDrawer).toBe("party");
    expect(wrapper.find('[data-testid="party-bag-tab"]').exists()).toBe(true);
    const purses = wrapper.findAll('[data-testid="party-window__purse"]');
    expect(purses).toHaveLength(1);
    expect(purses[0].text()).toBe("1,240 銅");
    // The tab body carries no balance of its own (no 金錢 row).
    expect(wrapper.get('[data-testid="party-bag-tab"]').text()).not.toContain("1,240");
    expect(wrapper.get('[data-testid="party-bag-tab"]').text()).not.toContain("金錢");
    expect(wrapper.text()).not.toContain("錢袋");
    // Every other drawer renders no balance of its own.
    // The 狀態 tab body carries no balance either (webclient-party-status-tab).
    store.openHudDrawer("status");
    await wrapper.vm.$nextTick();
    expect(wrapper.get('[data-testid="party-status-tab"]').text()).not.toContain("1,240");
    expect(wrapper.findAll('[data-testid="party-window__purse"]')).toHaveLength(1);
    // Nor does the 技能 tab body (webclient-party-skill-tab).
    store.openHudDrawer("skill");
    await wrapper.vm.$nextTick();
    expect(wrapper.get('[data-testid="party-skill-tab"]').text()).not.toContain("1,240");
    expect(wrapper.findAll('[data-testid="party-window__purse"]')).toHaveLength(1);
    for (const name of ["shop", "quest", "lore"]) {
      store.openHudDrawer(name);
      await wrapper.vm.$nextTick();
      const other = wrapper.get('[data-testid="hud-drawer"]');
      expect(other.findAll('[data-testid="party-window__purse"]').length, name).toBe(0);
      expect(other.findAll("[class*='__wallet']").length, name).toBe(0);
      expect(other.text(), name).not.toContain("錢袋");
      expect(other.text(), name).not.toContain("1,240");
    }
  });

  it("renders no purse and no zero when the party_inventory panel is unavailable", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    commitPurse({ schema_version: 1, available: false, reason: { code: "inventory_unavailable", message: "背包目前無法顯示。" } });
    await wrapper.vm.$nextTick();
    store.openHudDrawer("inventory");
    await wrapper.vm.$nextTick();
    expect(wrapper.find('[data-testid="party-window__purse"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="party-window__tab-unavailable"]').text()).toBe("背包目前無法顯示。");
    expect(wrapper.find(".drawer-header__subtitle").exists()).toBe(false);
  });

  // The character panel is an exact-schema v9 payload: the
  // `SKILLS_SLICE_SAMPLE` skill rows carry a `shorthands` field the
  // character-panel active-row schema does not register, so it is stripped
  // before committing. The other exact fields (member_id, traits, conditions,
  // equipment, disguise, guild, wallet) come from the already-valid
  // `CHARACTER_PANEL_SAMPLE`.
  function characterPanelWithSkillSlice() {
    return {
      schema_version: 9,
      available: true,
      kind: "character",
      member_id: CHARACTER_PANEL_SAMPLE.member_id,
      traits: CHARACTER_PANEL_SAMPLE.traits,
      conditions: CHARACTER_PANEL_SAMPLE.conditions,
      actives: SKILLS_SLICE_SAMPLE.actives.map(
        (category) => ({
          ...category,
          groups: category.groups.map(
            (group) => ({
              ...group,
              skills: group.skills.map(({ shorthands, ...row }) => row),
            }),
          ),
        })),
      passives: SKILLS_SLICE_SAMPLE.passives,
      equipment: CHARACTER_PANEL_SAMPLE.equipment,
      disguise: CHARACTER_PANEL_SAMPLE.disguise,
      guild: CHARACTER_PANEL_SAMPLE.guild,
      wallet: CHARACTER_PANEL_SAMPLE.wallet,
      selected_skill: SKILLS_SLICE_SAMPLE.selected_skill,
    };
  }

  // The commander viewed (the empty party's viewed member is the character
  // panel's member), optionally unread.
  function commanderParty(unread = false) {
    return {
      ...PARTY_PANEL_EMPTY_SAMPLE,
      slots: PARTY_PANEL_EMPTY_SAMPLE.slots.map((row) => ({ ...row, unread })),
    };
  }

  function commitSkills(party = commanderParty(), character = characterPanelWithSkillSlice()) {
    store.beginTransport(1);
    store.setConnected(true);
    store.receive(1, "ui_snapshot", [fx.snapshot({ panels: { character, services: SERVICES_PANEL_SAMPLE, party } })]);
  }

  it("opens the 技能 tab with its glyph and honest counts, one window title, and no cast-syntax footer", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    commitSkills();
    store.openHudDrawer("skill");
    await wrapper.vm.$nextTick();
    // The 技能 tab carries the `skills` glyph; the segment states the
    // panel's own active/passive row counts (主動 11 ‧ 被動 3).
    const skillTab = wrapper.get('[data-testid="icon-tabs__tab--skills"]');
    expect(skillTab.find("path").attributes("d")).toBe(
      "M12 3l1.9 5.6L19.5 10l-5.6 1.9L12 17l-1.9-5.1L4.5 10l5.6-1.4L12 3Z",
    );
    expect(wrapper.get('[data-testid="party-skill-tab__segment--active"]').text()).toBe("主動 11");
    expect(wrapper.get('[data-testid="party-skill-tab__segment--passive"]').text()).toBe("被動 3");
    expect(wrapper.findAll(".drawer-header__title")).toHaveLength(1);
    expect(wrapper.find(".drawer-header__subtitle").exists()).toBe(false);
    // The retired cast-syntax footer and the book's key hint are gone;
    // graphical 施放 / 排入修煉 live in the tab's action bar.
    expect(wrapper.find('[data-testid="skill-book-cast-hint"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="skill-book-key-hint"]').exists()).toBe(false);
    expect(wrapper.text()).not.toContain("cast <技法>");
    expect(wrapper.find('[data-testid="action-bar__btn--practice"]').exists()).toBe(true);
  });

  it("states the unavailable character panel's reason and invents no counts", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    commitSkills(commanderParty(), {
      schema_version: 9,
      available: false,
      reason: { code: "character_missing", message: "character not created" },
    });
    store.openHudDrawer("skill");
    await wrapper.vm.$nextTick();
    expect(wrapper.get('[data-testid="party-window__tab-unavailable"]').text()).toBe("character not created");
    expect(wrapper.find('[data-testid="party-skill-tab__segment"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="action-bar"]').exists()).toBe(false);
  });

  it("opening the 技能 tab on an unread member sends one party.view_member with tab skills", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    const sender = fx.createFakeSender();
    store.setSender(sender);
    commitSkills(commanderParty(true));
    store.openHudDrawer("skill");
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    const requests = () => sender.sent.actions.filter((envelope) => envelope.action_id === "party.view_member");
    // The committed selection is on screen, so the one request names it.
    expect(requests()).toHaveLength(1);
    expect(requests()[0].payload).toEqual({
      member_id: SKILLS_SLICE_SAMPLE.member_id,
      tab: "skills",
      skill_key: SKILLS_SLICE_SAMPLE.selected_skill.key,
      item_key: null,
    });
  });

  it("sends nothing on opening when the member is read and the selection is committed", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    const sender = fx.createFakeSender();
    store.setSender(sender);
    commitSkills(commanderParty(false));
    store.openHudDrawer("skill");
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    expect(sender.sent.actions.filter((envelope) => envelope.action_id === "party.view_member")).toHaveLength(0);
  });

  it("casts for the viewed companion: one preview with its actor_id, then the window hands over to the dock", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    const sender = fx.createFakeSender();
    store.setSender(sender);
    store.beginTransport(1);
    store.setConnected(true);
    store.receive(1, "ui_snapshot", [
      fx.snapshot({
        mode: "exploration",
        panels: {
          status: fx.statusPanel(),
          exploration: fx.explorationPanel(),
          context_actions: fx.explorationActions(),
          local_map: fx.localMapPanel(),
          party: PARTY_WINDOW_PANEL_SAMPLE,
          character: CHARACTER_SKILL_COMPANION_SAMPLE,
        },
      }),
    ]);
    store.openHudDrawer("skill");
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    const companion = CHARACTER_SKILL_COMPANION_SAMPLE.member_id;
    const heal = CHARACTER_SKILL_COMPANION_SAMPLE.selected_skill.key;
    expect(wrapper.get('[data-testid="party-skill-tab__row"][aria-selected="true"]').attributes("data-key")).toBe(heal);
    await wrapper.get('[data-testid="action-bar__btn--cast"]').trigger("click");
    const preview = sender.sent.actions.at(-1);
    expect(preview.action_id).toBe("explore.skill_preview");
    expect(preview.payload).toEqual({ actor_id: companion, skill_key: heal });
    // The preview commits for that caster: the window closes before the
    // dock-owned flow mounts.
    store.receive(1, "ui_update", [
      fx.update({
        revision: 2,
        panels: {
          skill_use: {
            schema_version: 2,
            available: true,
            kind: "skill_use",
            actor_id: companion,
            scale: 1,
            skill: {
              key: heal,
              label: "治癒之光",
              description: "合成用的治療技能。",
              target_spec: "single",
              usable_out_of_combat: true,
              cost: { mp: 8 },
              enabled: true,
              disabled_reason: null,
              targets: [{ identity: companion, label: "蕾娜", enabled: true, disabled_reason: null }],
              openings: [],
            },
          },
        },
      }),
    ]);
    store.receive(1, "ui_action_result", [fx.actionResult({ request_id: preview.request_id, presentation_revision: 2 })]);
    await wrapper.vm.$nextTick();
    expect(store.view.hudDrawer).toBe(null);
    expect(wrapper.find('[data-testid="party-window"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="skill-use-dock"]').exists()).toBe(true);
    expect(sender.sent.actions.filter((envelope) => envelope.action_id === "explore.cast")).toHaveLength(0);
  });

  // add-persona-edit-surface, moved to the party window's 成員 tab by
  // webclient-party-window-member-tab: one persona edit submits exactly one
  // character.persona.update envelope through the single store dispatch.
  it("submits one character.persona.update envelope per 成員-tab persona edit", async () => {
    const sender = fx.createFakeSender();
    store.setSender(sender);
    mountAppClient();
    await wrapper.vm.$nextTick();
    store.beginTransport(1);
    store.setConnected(true);
    store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          panels: {
            status: fx.statusPanel(),
            exploration: fx.explorationPanel(),
            context_actions: fx.explorationActions(),
            character: CHARACTER_PANEL_SAMPLE,
            party: PARTY_PANEL_EMPTY_SAMPLE,
            party_member: PARTY_MEMBER_PANEL_SAMPLE,
          },
        }),
      ],
    );
    await wrapper.vm.$nextTick();
    // The 狀態 tab carries no persona; the 成員 tab owns the editor.
    store.openHudDrawer("status");
    await wrapper.vm.$nextTick();
    expect(wrapper.find('[data-testid="party-status-tab"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="action-bar__btn--persona-edit"]').exists()).toBe(false);
    await wrapper.get('[data-testid="icon-tabs__tab--member"]').trigger("click");
    await wrapper.vm.$nextTick();
    await wrapper.get('[data-testid="action-bar__btn--persona-edit"]').trigger("click");
    await wrapper.get('[data-testid="party-member-tab__persona-edit--life_story"]').trigger("click");
    await wrapper
      .get('[data-testid="party-member-tab__persona-input--life_story"]')
      .setValue("  我在渡口寫下的新生平。  ");
    await wrapper.get('[data-testid="party-member-tab__persona-submit--life_story"]').trigger("click");
    expect(sender.sent.actions).toHaveLength(1);
    const envelope = sender.sent.actions[0];
    expect(envelope.action_id).toBe("character.persona.update");
    expect(envelope.payload).toEqual({ field: "life_story", text: "我在渡口寫下的新生平。" });
    expect(envelope.protocol_version).toBe(1);
    // Settle the first dispatch so the single in-flight slot frees for the
    // next edit (the server result settles the mutation).
    const result = store.receive(
      1,
      "ui_action_result",
      [fx.actionResult({ request_id: "session:1", presentation_revision: 2 })],
      {},
    );
    expect(result.accepted).toBe(true);
    // The completion publication refreshes the `party_member` panel at the
    // result's revision (character v8 no longer carries persona); the tab
    // reflects the new text with no reload.
    const refreshed = {
      ...PARTY_MEMBER_PANEL_SAMPLE,
      commander: {
        ...PARTY_MEMBER_PANEL_SAMPLE.commander,
        persona: {
          ...PARTY_MEMBER_PANEL_SAMPLE.commander.persona,
          life_story: "我在渡口寫下的新生平。",
        },
      },
    };
    const update = store.receive(
      1,
      "ui_update",
      [fx.update({ revision: 2, panels: { party_member: refreshed } })],
      {},
    );
    expect(update.accepted).toBe(true);
    await wrapper.vm.$nextTick();
    expect(
      wrapper.get('[data-testid="party-member-tab__persona-value--life_story"]').text()
    ).toBe("我在渡口寫下的新生平。");
    // A blank submit clears: the same action carries text null.
    await wrapper.get('[data-testid="party-member-tab__persona-edit--habit"]').trigger("click");
    await wrapper.get('[data-testid="party-member-tab__persona-input--habit"]').setValue("   ");
    await wrapper.get('[data-testid="party-member-tab__persona-submit--habit"]').trigger("click");
    expect(sender.sent.actions).toHaveLength(2);
    expect(sender.sent.actions[1].payload).toEqual({ field: "habit", text: null });
  });

  // quest-drawer-book-tab: the quest drawer away from any clerk. The real
  // player route — the 任務 top-navigation entry opens the quest drawer
  // without a frame push — lands on the quest book with the counter tab
  // disabled and naming the missing clerk, and tracking dispatches with no
  // guild host present.
  it("opens the quest book away from any clerk and tracks from the detail", async () => {
    const sender = fx.createFakeSender();
    store.setSender(sender);
    mountAppClient();
    await wrapper.vm.$nextTick();
    store.beginTransport(1);
    store.setConnected(true);
    const received = store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          panels: {
            status: fx.statusPanel(),
            exploration: fx.explorationPanel(),
            context_actions: fx.explorationActions(),
            services: SERVICES_PANEL_MINIMAL_SAMPLE,
            quest_log: QUEST_LOG_PANEL_SAMPLE,
          },
        }),
      ],
      {},
    );
    expect(received.accepted).toBe(true);
    await wrapper.vm.$nextTick();
    // The player route uses the top navigation, with no clerk in this session.
    await wrapper.get(".desktop-navigation").findAll("button")
      .find((button) => button.text() === "任務").trigger("click");
    expect(store.view.hudDrawer).toBe("quest");
    await wrapper.vm.$nextTick();
    // The quest drawer owns its scrolling regions: the drawer body is flush.
    expect(wrapper.get(".hud-drawer__body").classes()).toContain("hud-drawer__body--flush");
    const body = wrapper.get('[data-testid="quest-drawer"]');
    expect(body.attributes("data-tab")).toBe("book");
    expect(body.find('[data-testid="quest-drawer__row--q_1042"]').exists()).toBe(true);
    expect(body.get('[data-testid="quest-drawer__counter-absent"]').text()).toBe("需在公會職員面前才能辦理");
    expect(body.find('[data-testid="quest-drawer__counter"]').exists()).toBe(false);
    // Away from any clerk only tracking is offered, and it dispatches once.
    await body.get('[data-testid="quest-drawer__row--q_2077"]').trigger("click");
    expect(body.find('[data-testid="quest-drawer__abandon"]').exists()).toBe(false);
    await body.get('[data-testid="quest-drawer__track"]').trigger("click");
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0].action_id).toBe("guild.quest_track");
    expect(sender.sent.actions[0].payload).toEqual({ quest_id: "q_2077", tracked: true });
  });

  // quest-drawer-book-tab: in front of a clerk the book and the counter are
  // two first-level tabs, and no accepted quest appears in both (the counter
  // lists none of the holder's records).
  it("hosts the book and the counter as tabs without listing a quest twice", async () => {
    const sender = fx.createFakeSender();
    store.setSender(sender);
    mountAppClient();
    await wrapper.vm.$nextTick();
    store.beginTransport(1);
    store.setConnected(true);
    const received = store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          panels: {
            status: fx.statusPanel(),
            exploration: fx.explorationPanel(),
            context_actions: fx.explorationActions(),
            services: SERVICES_PANEL_SAMPLE,
            quest_log: QUEST_LOG_PANEL_SAMPLE,
          },
        }),
      ],
      {},
    );
    expect(received.accepted).toBe(true);
    await wrapper.vm.$nextTick();
    store.openHudDrawer("quest");
    await wrapper.vm.$nextTick();
    const body = wrapper.get('[data-testid="quest-drawer"]');
    expect(body.findAll('[data-testid^="quest-drawer__row--"]').map((n) => n.attributes("data-testid"))).toEqual([
      "quest-drawer__row--q_1042",
      "quest-drawer__row--q_2077",
    ]);
    expect(body.find('[data-testid="quest-drawer__counter"]').exists()).toBe(false);
    // The matched counter abandon reaches the wire only after confirmation.
    await body.get('[data-testid="quest-drawer__abandon"]').trigger("click");
    expect(sender.sent.actions).toHaveLength(0);
    await body.get('[data-testid="quest-drawer__abandon-confirm-yes"]').trigger("click");
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({ action_id: "guild.quest_abandon", payload: { quest_id: "q_1042" } });

    await body.get('[data-testid="quest-drawer__top-tabs"] [data-tab-key="counter"]').trigger("click");
    // The counter tab lists board offers only: no row is a held quest.
    const counter = body.get('[data-testid="quest-drawer__counter"]');
    const held = QUEST_LOG_PANEL_SAMPLE.rows.map((row) => row.quest_id);
    const offered = counter.findAll('[data-testid^="quest-drawer__row--"]').map((n) => n.attributes("data-quest-id"));
    const boardKeys = SERVICES_PANEL_SAMPLE.guild.board.map((row) => row.definition_key);
    expect(offered.length).toBeGreaterThan(0);
    expect(offered.every((id) => boardKeys.includes(id))).toBe(true);
    expect(offered.some((id) => held.includes(id))).toBe(false);
  });

  it("renders companions on stage and keeps the drawer reachable", async () => {
    mountAppClient();
    store.beginTransport(1);
    store.setConnected(true);
    store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          mode: "exploration",
          panels: {
            status: fx.statusPanel(),
            party: {
              schema_version: 3,
              available: true,
              general_quota: { used: 1, limit: 4 },
              viewed_member_id: 101,
              slots: [
                {
                  identity: 42,
                  display_name: "影行者",
                  portrait_ref: null,
                  hp_current: 80,
                  hp_maximum: 100,
                  mp_current: 30,
                  mp_maximum: 50,
                  sp_current: 12,
                  sp_maximum: 40,
                  role: "commander",
                  knocked_out: false,
                  unread: false,
                  bond_stage: null,
                  membership: null,
                },
                {
                  identity: 101,
                  display_name: "蕾娜",
                  portrait_ref: null,
                  hp_current: 180,
                  hp_maximum: 220,
                  mp_current: 60,
                  mp_maximum: 80,
                  sp_current: 24,
                  sp_maximum: 40,
                  role: "companion",
                  knocked_out: false,
                  unread: false,
                  bond_stage: "親睦",
                  membership: { general: true, temporary_commissions: [] },
                },
              ],
            },
          },
        }),
      ],
    );
    await wrapper.vm.$nextTick();

    expect(wrapper.findAll('[data-anchor="actor-left"] [data-testid="companion-figure"]')).toHaveLength(2);
    store.openHudDrawer("party");
    await wrapper.vm.$nextTick();
    expect(store.view.hudDrawer).toBe("party");
    expect(wrapper.find('[data-testid="party-window"]').exists()).toBe(true);
    expect(wrapper.get('.drawer-header__title').text()).toBe("隊伍");
    expect(wrapper.get('[data-testid="party-window__quota"]').text()).toBe("同伴 1 / 4");
  });

  it("keeps a solo figure for unavailable party and hides the lineup in creation", async () => {
    mountAppClient();
    store.beginTransport(1);
    store.setConnected(true);

    // Unavailable party panel
    store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          mode: "exploration",
          panels: {
            status: fx.statusPanel(),
            party: {
              schema_version: 3,
              available: false,
              reason: { code: "party_unavailable", message: "隊伍資訊目前無法顯示" },
            },
          },
        }),
      ],
    );
    await wrapper.vm.$nextTick();
    expect(wrapper.findAll('[data-testid="companion-figure"]')).toHaveLength(1);

    // Creation mode
    store.receive(
      1,
      "ui_update",
      [
        fx.update({
          revision: 2,
          mode: "creation",
          panels: {
            party: PARTY_PANEL_EMPTY_SAMPLE,
          },
        }),
      ],
    );
    await wrapper.vm.$nextTick();
    expect(wrapper.find('[data-testid="companion-lineup"]').exists()).toBe(false);
  });

  it("closes open party drawer when party panel becomes unavailable or mode switches to creation", async () => {
    mountAppClient();
    store.beginTransport(1);
    store.setConnected(true);

    // Initial state with available party panel
    store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          mode: "exploration",
          panels: {
            status: fx.statusPanel(),
            party: PARTY_PANEL_SAMPLE,
          },
        }),
      ],
    );
    await wrapper.vm.$nextTick();

    // Open party drawer
    store.openHudDrawer("party");
    await wrapper.vm.$nextTick();
    expect(store.view.hudDrawer).toBe("party");
    expect(wrapper.find('[data-testid="party-window"]').exists()).toBe(true);

    // Commit an update where party panel becomes unavailable
    store.receive(
      1,
      "ui_update",
      [
        fx.update({
          revision: 2,
          panels: {
            party: {
              schema_version: 3,
              available: false,
              reason: { code: "party_unavailable", message: "隊伍資訊目前無法顯示" },
            },
          },
        }),
      ],
    );
    await wrapper.vm.$nextTick();

    // The party drawer must be closed and unmounted
    expect(store.view.hudDrawer).toBe(null);
    expect(wrapper.find('[data-testid="party-window"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="hud-drawer"]').exists()).toBe(false);
  });

 it("closing shop drawer by Escape, close button, and scrim pops nothing, dispatches nothing, and restores focus", async () => {
   mountAppClient();
   const sender = fx.createFakeSender();
   store.setSender(sender);
   store.beginTransport(1);
   store.setConnected(true);
   store.receive(
     1,
     "ui_snapshot",
     [
       fx.snapshot({
         mode: "exploration",
         panels: {
           status: fx.statusPanel(),
           services: SERVICES_PANEL_SAMPLE,
           exploration: fx.explorationPanel({
             interact: [
               {
                 identity: 7,
                 display_name: "店長",
                 portrait_ref: null,
                 affordances: [
                   { kind: "action", action_id: "explore.talk_open", label: "交談", enabled: true, disabled_reason: null },
                   { kind: "navigate", surface: "shop", label: "商店", enabled: true, disabled_reason: null },
                 ],
               },
             ],
           }),
         },
       }),
     ],
   );
   await wrapper.vm.$nextTick();

   // The rail's 店長 entry opens the client-local verb card
   // (exploration-presence-rail): no router frame.
   expect(store.activatePresence("target-7").handled).toBe(true);
   await wrapper.vm.$nextTick();
   await wrapper.vm.$nextTick();
   const card = wrapper.get('[data-anchor="choices"] [data-testid="presence-card"]').element;

   const depthBefore = store.router.depth();
   const trailBefore = store.router.trail();

   const closeRoutes = {
     "close button": async () => {
       await wrapper.get('[data-testid="hud-drawer-close"]').trigger("click");
     },
     "Escape": async () => {
       await wrapper.get('[data-testid="hud-drawer"]').trigger("keydown", { key: "Escape" });
     },
     "scrim": async () => {
       await wrapper.get('[data-testid="hud-drawer-scrim"]').trigger("click");
     },
   };

   for (const [name, closeAction] of Object.entries(closeRoutes)) {
     const actionsCountBefore = sender.sent.actions.length;

     // The verb card's service-shop row
     expect(store.activatePresenceVerb("service-shop").handled).toBe(true);
     await wrapper.vm.$nextTick();

     expect(store.view.hudDrawer, name).toBe("shop");
     expect(wrapper.find('[data-testid="shop-window"]').exists(), name).toBe(true);
     expect(store.router.depth(), name).toBe(depthBefore);
     expect(store.view.activeSubDock, name).toBe(null);

     await closeAction();
     await wrapper.vm.$nextTick();

     expect(store.view.hudDrawer, name).toBe(null);
     expect(wrapper.find('[data-testid="hud-drawer"]').exists(), name).toBe(false);
     expect(store.router.depth(), name).toBe(depthBefore);
     expect(store.router.trail(), name).toEqual(trailBefore);
     expect(store.view.activeSubDock, name).toBe(null);
     expect(sender.sent.actions.length, name).toBe(actionsCountBefore);
     // The card stays open under the drawer and takes focus back.
     expect(store.view.presenceCard, name).toMatchObject({ kind: "verbs", identity: 7 });
     expect(document.activeElement, name).toBe(card);
   }
});

 it("closing quest drawer by Escape, close button, and scrim pops nothing, dispatches nothing, and restores focus", async () => {
   mountAppClient();
   const sender = fx.createFakeSender();
   store.setSender(sender);
   store.beginTransport(1);
   store.setConnected(true);
   store.receive(
     1,
     "ui_snapshot",
     [
       fx.snapshot({
         mode: "exploration",
         panels: {
           status: fx.statusPanel(),
           services: SERVICES_PANEL_SAMPLE,
           exploration: fx.explorationPanel({
             interact: [
               {
                 identity: 7,
                 display_name: "店長",
                 portrait_ref: null,
                 affordances: [
                   { kind: "action", action_id: "explore.talk_open", label: "交談", enabled: true, disabled_reason: null },
                   { kind: "navigate", surface: "guild", label: "公會服務", enabled: true, disabled_reason: null },
                 ],
               },
             ],
           }),
         },
       }),
     ],
   );
   await wrapper.vm.$nextTick();

   // The rail's 店長 entry opens the client-local verb card
   // (exploration-presence-rail): no router frame.
   expect(store.activatePresence("target-7").handled).toBe(true);
   await wrapper.vm.$nextTick();
   await wrapper.vm.$nextTick();
   const card = wrapper.get('[data-anchor="choices"] [data-testid="presence-card"]').element;

   const depthBefore = store.router.depth();
   const trailBefore = store.router.trail();

   const closeRoutes = {
     "close button": async () => {
       await wrapper.get('[data-testid="hud-drawer-close"]').trigger("click");
     },
     "Escape": async () => {
       await wrapper.get('[data-testid="hud-drawer"]').trigger("keydown", { key: "Escape" });
     },
     "scrim": async () => {
       await wrapper.get('[data-testid="hud-drawer-scrim"]').trigger("click");
     },
   };

   for (const [name, closeAction] of Object.entries(closeRoutes)) {
     const actionsCountBefore = sender.sent.actions.length;

     // The verb card's service-guild row
     expect(store.activatePresenceVerb("service-guild").handled).toBe(true);
     await wrapper.vm.$nextTick();

     expect(store.view.hudDrawer, name).toBe("quest");
     expect(wrapper.find('[data-testid="quest-drawer"]').exists(), name).toBe(true);
     expect(store.router.depth(), name).toBe(depthBefore);
     expect(store.view.activeSubDock, name).toBe(null);

     await closeAction();
     await wrapper.vm.$nextTick();

     expect(store.view.hudDrawer, name).toBe(null);
     expect(wrapper.find('[data-testid="hud-drawer"]').exists(), name).toBe(false);
     expect(store.router.depth(), name).toBe(depthBefore);
     expect(store.router.trail(), name).toEqual(trailBefore);
     expect(store.view.activeSubDock, name).toBe(null);
     expect(sender.sent.actions.length, name).toBe(actionsCountBefore);
     // The card stays open under the drawer and takes focus back.
     expect(store.view.presenceCard, name).toMatchObject({ kind: "verbs", identity: 7 });
     expect(document.activeElement, name).toBe(card);
   }
 });

  it("rescues focus when a same-code adverse condition becomes equipment-only", async () => {
    const w = mountAppClient();
    store.beginTransport(1);
    store.setConnected(true);
    store.setLoggedIn(true);

    const harmfulStatus = fx.statusPanel({
      resources: {
        hp: { current: 100, maximum: 100 },
        mp: { current: 50, maximum: 50 },
        sp: { current: 40, maximum: 40 },
      },
      conditions: [{ code: "poison", label: "中毒", provenance: { kind: "non_equipment", equipment_sources: [] }, severity: "harmful" }],
});
    store.receive(1, "ui_snapshot", [fx.snapshot({
      revision: 1,
      mode: "exploration",
      panels: { status: harmfulStatus },
    })], {});
    await w.vm.$nextTick();

    const chip = w.get('[data-testid="status-panel__condition--poison"]');
    chip.element.focus();
    expect(document.activeElement).toBe(chip.element);

    const equipmentStatus = fx.statusPanel({
      resources: {
        hp: { current: 100, maximum: 100 },
        mp: { current: 50, maximum: 50 },
        sp: { current: 40, maximum: 40 },
      },
      conditions: [{
        code: "poison", label: "中毒", severity: "harmful",
        provenance: { kind: "equipment", equipment_sources: [{ item_key: "t_a", label: "合成護符" }] },
      }],
    });
    store.receive(1, "ui_snapshot", [fx.snapshot({
      revision: 2,
      mode: "exploration",
      panels: { status: equipmentStatus },
    })], {});
    await w.vm.$nextTick();

    expect(w.get('[data-testid="status-panel"]').isVisible()).toBe(false);
    expect(document.activeElement?.id).toBe("action-dock");
  });

  it("keeps dialogue and creation gates above independent critical attention", async () => {
    const w = mountAppClient();
    store.beginTransport(1);
    store.setConnected(true);
    store.setLoggedIn(true);
    const status = fx.statusPanel({
      conditions: [{ code: "t_critical", label: "合成警告", severity: "critical",
        provenance: { kind: "non_equipment", equipment_sources: [] } }],
    });
    for (const [revision, mode] of [[1, "dialogue"], [2, "creation"], [3, "exploration"]]) {
      expect(store.receive(1, "ui_snapshot", [fx.snapshot({ revision, mode, panels: { status } })], {}).accepted).toBe(true);
      await w.vm.$nextTick();
      if (mode === "dialogue") expect(w.findComponent(StatusPanel).props("visible")).toBe(false);
      if (mode === "creation") expect(w.get('[data-testid="elosern-stage"]').attributes("data-elosern-mode")).toBe("creation");
      if (mode === "exploration") expect(w.findComponent(StatusPanel).props("visible")).toBe(true);
    }
  });

  it("joins the committed string status identity for possession and clears dialogue companion focus", async () => {
    mountAppClient();
    store.beginTransport(1);
    store.setConnected(true);
    const roster = {
      schema_version: 3, available: true,
      // The row's portrait IS the complete canonical descriptor: an owned
      // character with no real candidate and no terminal yet.
      characters: [{ identity: 1, name: "測試主角", current: true, pending: false, portrait: {
        subject_id: "portrait:character:1",
        revision: "1".repeat(64),
        generation_subject: "portrait:character:1",
        generation_state: "missing",
        attempts: [],
        terminal: null,
        retention_sources: [],
      } }],
      max_characters: 5, can_create: true, switch_locked: false, lock_reason: null,
    };
    store.receive(1, "ui_snapshot", [fx.snapshot({ panels: {
      party: PARTY_PANEL_FULL_SAMPLE, roster,
      status: fx.statusPanel({ actor: { identity: "1" } }),
    } })]);
    await wrapper.vm.$nextTick();
    const ids = () => wrapper.findAll('[data-testid="companion-figure"]').map((slot) => slot.attributes("data-identity"));
    expect(ids()).toEqual(["1", "101", "102", "103", "104"]);
    store.receive(1, "ui_update", [fx.update({ revision: 2, panels: {
      status: fx.statusPanel({ actor: { identity: "102" } }),
      possession_banner: { schema_version: 1, available: true, host_name: "測試宿主", since_tick: 1 },
    } })]);
    await wrapper.vm.$nextTick();
    expect(ids()).toEqual(["102", "101", "1", "103", "104"]);
    store.receive(1, "ui_update", [fx.update({ revision: 3, mode: "dialogue", panels: {
      status: fx.statusPanel({ actor: { identity: "102" } }),
      dialogue: { schema_version: 2, available: true, kind: "dialogue",
        host: { identity: 103, display_name: "測試同行", portrait_ref: null },
        bond_stage: null, line: "測試台詞。", choices: [] },
    } })]);
    await wrapper.vm.$nextTick();
    const speaker = wrapper.get('[data-slot="3"]');
    expect(speaker.element.style.zIndex).toBe("6");
    expect(speaker.get('[data-testid="stage-actor"]').attributes("data-speaking")).toBe("true");
    expect(wrapper.find('[data-anchor="actor-right"] [data-testid="stage-actor"]').exists()).toBe(false);
    store.receive(1, "ui_update", [fx.update({ revision: 4, mode: "exploration", panels: {
      status: fx.statusPanel({ actor: { identity: "1" } }),
      possession_banner: { schema_version: 1, available: false, reason: { code: "unavailable", message: "無附身" } },
    } })]);
    await wrapper.vm.$nextTick();
    expect(ids()).toEqual(["1", "101", "102", "103", "104"]);
    expect(speaker.element.style.zIndex).toBe("2");
    expect(speaker.get('[data-testid="stage-actor"]').attributes("data-speaking")).toBe("false");
  });

  it("with an available empty party, renders only the controlled standing figure", async () => {
    mountAppClient();
    store.beginTransport(1);
    store.setConnected(true);
    store.setLoggedIn(true);

    store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          revision: 1,
          mode: "exploration",
          panels: {
            party: PARTY_PANEL_EMPTY_SAMPLE,
            status: fx.statusPanel(),
          },
        }),
      ],
      {},
    );
    await wrapper.vm.$nextTick();

    expect(store.partyAvailable).toBe(true);
    expect(wrapper.findAll('[data-testid="companion-figure"]')).toHaveLength(1);
  });

  it("with an empty party, the 角色狀態 opener opens the party window on the commander's 狀態 tab", async () => {
    mountAppClient();
    store.beginTransport(1);
    store.setConnected(true);
    store.setLoggedIn(true);

    // Commit empty-but-available party panel before opening drawer (proves reactivity)
    store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          revision: 1,
          mode: "exploration",
          panels: {
            party: PARTY_PANEL_EMPTY_SAMPLE,
            exploration: fx.explorationPanel(),
            context_actions: fx.explorationActions(),
            status: fx.statusPanel(),
            character: fx.characterPanel ? fx.characterPanel() : CHARACTER_PANEL_SAMPLE,
          },
        }),
      ],
      {},
    );
    await wrapper.vm.$nextTick();

    // The 角色狀態 opener (webclient-party-status-tab).
    store.tabToRootAndConfirm("character", "pointer");
    await wrapper.vm.$nextTick();
    expect(store.view.hudDrawer).toBe("party");
    expect(wrapper.find('[data-testid="hud-drawer"][data-drawer-key="status"]').exists()).toBe(false);
    const tab = wrapper.get('[data-testid="party-status-tab"]');
    expect(tab.attributes("data-member")).toBe(String(CHARACTER_PANEL_SAMPLE.member_id));
    expect(tab.get('[data-testid="party-status-tab__name"]').text()).toBe("影行者");
    expect(tab.find('[data-testid="party-status-tab__trait--defense"]').exists()).toBe(true);
    // Only the 角色狀態 entry is current while the window shows 狀態.
    const current = wrapper.findAll('.desktop-navigation [aria-current="page"]').map((node) => node.text());
    expect(current).toEqual(["角色狀態"]);
    await wrapper.get('[data-testid="icon-tabs__tab--bag"]').trigger("click");
    await wrapper.vm.$nextTick();
    expect(wrapper.findAll('.desktop-navigation [aria-current="page"]').map((node) => node.text())).toEqual(["背包"]);
  });
});
