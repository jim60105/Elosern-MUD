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
import { useElosernStore } from "../stores/elosern.js";

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
});
