// H4 (webclient-hud-04-reference-drawers, task 7.7): the reference-drawer
// layer contract. Asserts (1) no reference surface is in the DOM while every
// drawer is closed, (2) each reference surface is reachable in at most two
// actions from the dock root (the store's single openHudDrawer call is one
// action), and (3) exactly one wallet rendering exists across the whole
// drawer layer (the wallet lives only in CharacterStatusDrawer).
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../AppClient.vue";
import {
  CHARACTER_PANEL_SAMPLE,
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

  it("renders the wallet exactly once across the whole drawer layer", async () => {
    mountAppClient();
    await wrapper.vm.$nextTick();
    store.openHudDrawer("status");
    await wrapper.vm.$nextTick();
    // The wallet line exists in exactly one drawer body (CharacterStatusDrawer);
    // the other bodies render no wallet (the single-wallet invariant).
    expect(wrapper.findAll('[data-testid="character-status-drawer__wallet"]')).toHaveLength(1);
    // No other body (shop, inventory, quest, lore, skill) carries a wallet node.
    const walletNodes = wrapper.findAll("[class*='__wallet']");
    expect(walletNodes).toHaveLength(1);
  });

  // The character panel is an exact-schema v4 payload: the
  // `SKILLS_SLICE_SAMPLE` skill rows carry a `shorthands` field the
  // character-panel active-row schema does not register, so it is stripped
  // before committing. The other exact fields (traits, equipment, disguise,
  // guild, wallet, persona, intimate) come from the already-valid
  // `CHARACTER_PANEL_SAMPLE`.
  function characterPanelWithSkillSlice() {
    return {
      schema_version: 4,
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
      [fx.snapshot({ panels: { character: characterPanelWithSkillSlice() } })],
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
    // The other five drawers keep the head icon-less / footer-less chrome.
    store.openHudDrawer("inventory");
    await wrapper.vm.$nextTick();
    expect(wrapper.find(".hud-drawer__icon").exists()).toBe(false);
    expect(wrapper.find(".hud-drawer__subtitle").exists()).toBe(false);
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
              schema_version: 4,
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
});
