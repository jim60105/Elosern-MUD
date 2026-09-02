// H4 (webclient-hud-04-reference-drawers, task 7.7): the reference-drawer
// layer contract. Asserts (1) no reference surface is in the DOM while every
// drawer is closed, (2) each reference surface is reachable in at most two
// actions from the dock root (the store's single openHudDrawer call is one
// action), and (3) across the whole drawer layer the wallet renders exactly
// twice per opening of the inventory drawer — its shared header subtitle and
// the single row of its `金錢` body section, both from the committed
// character panel — and nowhere else (relocate-inventory-drawer-essentials;
// realign-inventory-drawer-layout).
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../AppClient.vue";
import {
  CHARACTER_PANEL_SAMPLE,
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  SERVICES_PANEL_UNAVAILABLE_SAMPLE,
  SKILLS_SLICE_SAMPLE,
} from "../stories/fixtures.js";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";

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
  });

  // The closed reference-drawer name -> the body's root testid.
  const REFERENCE_SURFACES = {
    skill: "skill-book",
    inventory: "inventory-panel",
    shop: "shop-panel",
    quest: "quest-board",
    lore: "lore-drawer",
    status: "character-status-drawer",
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
  });

  it("renders the wallet exactly once per inventory-drawer opening — subtitle + 金錢 row — and nowhere else", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    // Prime the transport and commit both panels: the character panel owns
    // the wallet (3240 copper); the services panel's own inventory wallet
    // carries a different value (1200), proving both drawer-layer renderings
    // are sourced only from the committed character panel — the services-side
    // wallet is never rendered anywhere (realign-inventory-drawer-layout D3:
    // head and body read one figure and can never disagree).
    store.beginTransport(1);
    store.setConnected(true);
    store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          panels: {
            character: CHARACTER_PANEL_SAMPLE,
            services: {
              ...SERVICES_PANEL_SAMPLE,
              inventory: { ...SERVICES_PANEL_SAMPLE.inventory, wallet: 1200 },
            },
          },
        }),
      ],
    );
    await wrapper.vm.$nextTick();
    store.openHudDrawer("inventory");
    await wrapper.vm.$nextTick();
    // Location 1 — the shared head subtitle (relocate-inventory-drawer-
    // essentials): thousands-grouped integer copper from the character panel
    // (3,240 — never the services-side 1,200).
    const subtitles = wrapper.findAll(".hud-drawer__subtitle");
    expect(subtitles).toHaveLength(1);
    expect(subtitles[0].text()).toBe("錢袋 3,240 銅");
    // Location 2 — the single row of the `金錢` body section: the exact same
    // committed figure, grouped integer copper.
    const drawer = wrapper.get('[data-testid="hud-drawer"]');
    const walletNodes = drawer.findAll('[data-testid="inventory-panel__wallet-value"]');
    expect(walletNodes).toHaveLength(1);
    expect(walletNodes[0].text()).toBe("3,240");
    // Nothing else in the drawer carries a wallet-classed node, and the
    // services-side figure is never rendered.
    expect(drawer.findAll("[class*='__wallet']")).toHaveLength(1);
    expect(wrapper.text()).not.toContain("1,200");
    // Every other drawer renders no balance of its own — neither a wallet
    // node nor a `錢袋` line (the character-status drawer included).
    for (const name of ["skill", "shop", "quest", "lore", "status"]) {
      store.openHudDrawer(name);
      await wrapper.vm.$nextTick();
      const other = wrapper.get('[data-testid="hud-drawer"]');
      expect(other.findAll('[data-testid="inventory-panel__wallet-value"]').length, name).toBe(0);
      expect(other.findAll("[class*='__wallet']").length, name).toBe(0);
      expect(other.text(), name).not.toContain("錢袋");
    }
  });

  // The character panel is an exact-schema v5 payload: the
  // `SKILLS_SLICE_SAMPLE` skill rows carry a `shorthands` field the
  // character-panel active-row schema does not register, so it is stripped
  // before committing. The other exact fields (traits, equipment, disguise,
  // guild, wallet, persona, intimate) come from the already-valid
  // `CHARACTER_PANEL_SAMPLE`.
  function characterPanelWithSkillSlice() {
    return {
      schema_version: 7,
      available: true,
      kind: "character",
      traits: CHARACTER_PANEL_SAMPLE.traits,
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
      persona: CHARACTER_PANEL_SAMPLE.persona,
      intimate: CHARACTER_PANEL_SAMPLE.intimate,
    };
  }

  it("gives the skill drawer its skill glyph, skill-count subtitle, and cast-syntax footer", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    // Prime the transport so the snapshot's generation 1 is the current one
    // (mirrors the resync test's `connect()`); without it the reducer
    // rejects the snapshot as `stale_generation`.
    store.beginTransport(1);
    store.setConnected(true);
    // Populate the character panel with the deterministic skill fixture
    // (actives=11, passives=3 per SKILLS_SLICE_SAMPLE).
    store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          panels: {
            character: characterPanelWithSkillSlice(),
            services: SERVICES_PANEL_SAMPLE,
          },
        }),
      ],
    );
    store.openHudDrawer("skill");
    await wrapper.vm.$nextTick();
    // The composed drawer head: the `skills` glyph + the 主動 11 · 被動 3
    // subtitle (the fixture's own row counts, not invented data).
    const icon = wrapper.find(".hud-drawer__icon");
    expect(icon.exists()).toBe(true);
    expect(icon.find("path").attributes("d")).toBe(
      "M12 3l1.9 5.6L19.5 10l-5.6 1.9L12 17l-1.9-5.1L4.5 10l5.6-1.4L12 3Z",
    );
    expect(wrapper.get(".hud-drawer__subtitle").text()).toBe("主動 11 · 被動 3");
    // The footer states the client's own `/cast` syntax as static copy.
    expect(wrapper.get('[data-testid="skill-book-cast-hint"]').text()).toBe(
      "施放入口：cast <技法>[@威力]=<代號>",
    );
    // The inventory drawer carries the reference's `inventory` backpack glyph
    // (align-drawer-chrome-symbols; the string shared with `items`) and its
    // header wallet subtitle (relocate-inventory-drawer-essentials); the
    // remaining four drawers keep the icon-less / footer-less chrome.
    store.openHudDrawer("inventory");
    await wrapper.vm.$nextTick();
    const invIcon = wrapper.find(".hud-drawer__icon");
    expect(invIcon.exists()).toBe(true);
    expect(invIcon.find("path").attributes("d")).toBe("M4 8h16v11H4zM8 8V6a4 4 0 0 1 8 0v2");
    expect(wrapper.find('[data-testid="hud-drawer__title"].hud-drawer__title').exists()).toBe(true);
    expect(wrapper.get(".hud-drawer__subtitle").text()).toBe("錢袋 3,240 銅");
    expect(wrapper.find('[data-testid="skill-book-cast-hint"]').exists()).toBe(false);
  });

  it("leaves the skill drawer subtitle empty when the character panel is missing or unavailable", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    // Panel missing: the drawer opens before any snapshot commits, so the
    // subtitle is empty (the degrade-without-inventing-data contract).
    store.openHudDrawer("skill");
    await wrapper.vm.$nextTick();
    expect(wrapper.find(".hud-drawer__subtitle").exists()).toBe(false);
    // A committed `ui_snapshot` (an epoch/mode change) tears down the open
    // drawer, so close it, commit the unavailable panel, then re-open.
    store.closeHudDrawer({});
    store.beginTransport(1);
    store.setConnected(true);
    // The exact unavailable form: schema_version + available:false + a
    // bounded reason.
    store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          panels: {
            character: {
              schema_version: 7,
              available: false,
              reason: { code: "character_missing", message: "character not created" },
            },
          },
        }),
      ],
    );
    await wrapper.vm.$nextTick();
    store.openHudDrawer("skill");
    await wrapper.vm.$nextTick();
    // Panel unavailable: still no subtitle, but the head icon and the
    // static footer hint are client-local chrome — they render regardless
    // of the panel's availability.
    expect(wrapper.find(".hud-drawer__subtitle").exists()).toBe(false);
    expect(wrapper.find(".hud-drawer__icon").exists()).toBe(true);
    expect(wrapper.find('[data-testid="skill-book-cast-hint"]').exists()).toBe(true);
  });

  it("leaves the inventory drawer subtitle blank when the character panel is unavailable", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    // Prime the transport and commit the character panel in its registry-
    // owned unavailable form (a bounded reason, no wallet field).
    store.beginTransport(1);
    store.setConnected(true);
    store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          panels: {
            character: {
              schema_version: 7,
              available: false,
              reason: { code: "no_puppet", message: "你已離開角色" },
            },
            services: SERVICES_PANEL_SAMPLE,
          },
        }),
      ],
    );
    await wrapper.vm.$nextTick();
    store.openHudDrawer("inventory");
    await wrapper.vm.$nextTick();
    // No balance and no zero: the header keeps the reference `inventory`
    // backpack glyph but renders no wallet subtitle
    // (relocate-inventory-drawer-essentials: an unavailable panel renders no
    // balance at all), and the body renders no `金錢` row either
    // (realign-inventory-drawer-layout).
    const icon = wrapper.find(".hud-drawer__icon");
    expect(icon.exists()).toBe(true);
    expect(icon.find("path").attributes("d")).toBe("M4 8h16v11H4zM8 8V6a4 4 0 0 1 8 0v2");
    expect(wrapper.find(".hud-drawer__subtitle").exists()).toBe(false);
    expect(wrapper.find('[data-testid="inventory-panel__wallet-value"]').exists()).toBe(false);
  });

  it("renders no wallet subtitle when the services panel is unavailable", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    // The services panel commits its registry-owned unavailable form (no
    // inventory section, no wallet): the bag fabricates no wallet.
    store.beginTransport(1);
    store.setConnected(true);
    store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          panels: {
            services: SERVICES_PANEL_UNAVAILABLE_SAMPLE,
            character: CHARACTER_PANEL_SAMPLE,
          },
        }),
      ],
    );
    await wrapper.vm.$nextTick();
    store.openHudDrawer("inventory");
    await wrapper.vm.$nextTick();
    // The bag body renders only the registry-owned reason; the header keeps
    // the bag glyph but renders no wallet subtitle (no balance, no zero).
    expect(wrapper.find('[data-testid="inventory-panel__unavailable"]').exists()).toBe(true);
    const icon = wrapper.find(".hud-drawer__icon");
    expect(icon.exists()).toBe(true);
    expect(wrapper.find(".hud-drawer__subtitle").exists()).toBe(false);
  });

  it("renders no wallet subtitle when the services inventory section is absent", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    // The reduced services payload (SERVICES_PANEL_MINIMAL_SAMPLE) carries no
    // inventory section: the bag shows its honest absent message and the
    // header renders no wallet subtitle.
    store.beginTransport(1);
    store.setConnected(true);
    store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          panels: {
            services: SERVICES_PANEL_MINIMAL_SAMPLE,
            character: CHARACTER_PANEL_SAMPLE,
          },
        }),
      ],
    );
    await wrapper.vm.$nextTick();
    store.openHudDrawer("inventory");
    await wrapper.vm.$nextTick();
    expect(wrapper.find('[data-testid="inventory-panel__absent"]').exists()).toBe(true);
    const icon = wrapper.find(".hud-drawer__icon");
    expect(icon.exists()).toBe(true);
    expect(wrapper.find(".hud-drawer__subtitle").exists()).toBe(false);
  });

  // add-persona-edit-surface: one drawer persona edit submits exactly one
  // character.persona.update envelope through the single store dispatch.
  it("submits one character.persona.update envelope per drawer persona edit", async () => {
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
          },
        }),
      ],
    );
    await wrapper.vm.$nextTick();
    store.openHudDrawer("status");
    await wrapper.vm.$nextTick();
    await wrapper.get('[data-testid="character-status-drawer__persona-edit--life_story"]').trigger("click");
    await wrapper
      .get('[data-testid="character-status-drawer__persona-input--life_story"]')
      .setValue("  我在渡口寫下的新生平。  ");
    await wrapper.get('[data-testid="character-status-drawer__persona-submit--life_story"]').trigger("click");
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
    // The completion publication refreshes the character panel at the
    // result's revision; the drawer reflects the new text with no reload.
    const refreshed = {
      ...CHARACTER_PANEL_SAMPLE,
      persona: { ...CHARACTER_PANEL_SAMPLE.persona, life_story: "我在渡口寫下的新生平。" },
    };
    const update = store.receive(
      1,
      "ui_update",
      [fx.update({ revision: 2, panels: { character: refreshed } })],
      {},
    );
    expect(update.accepted).toBe(true);
    await wrapper.vm.$nextTick();
    expect(
      wrapper.get('[data-testid="character-status-drawer__persona-value--life_story"]').text()
    ).toBe("我在渡口寫下的新生平。");
    // A blank submit clears: the same action carries text null.
    await wrapper.get('[data-testid="character-status-drawer__persona-edit--habit"]').trigger("click");
    await wrapper.get('[data-testid="character-status-drawer__persona-input--habit"]').setValue("   ");
    await wrapper.get('[data-testid="character-status-drawer__persona-submit--habit"]').trigger("click");
    expect(sender.sent.actions).toHaveLength(2);
    expect(sender.sent.actions[1].payload).toEqual({ field: "habit", text: null });
  });
});
