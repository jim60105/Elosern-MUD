// webclient-avg-stage-shell (design D4): the player's standing portrait lives
// in the stage's `actor-left` anchor, standing on the bottom band, not in the
// backdrop slot; the `actor-right` anchor stays empty in this change.
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import AppClient from "../AppClient.vue";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";

describe("the player portrait stands in the actor-left anchor", () => {
  let store, wrapper;
  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    store.setSender(fx.createFakeSender());
    wrapper = mount(AppClient, { attachTo: document.body });
    store.beginTransport(1);
    store.setConnected(true);
  });
  afterEach(() => { wrapper.unmount(); document.body.replaceChildren(); });

  it("renders the reference artwork in actor-left outside creation mode", async () => {
    const panels = { status: fx.statusPanel(), exploration: fx.explorationPanel(), context_actions: fx.explorationActions() };
    const response = store.receive(1, "ui_snapshot", [fx.snapshot({ panels, revision: 1 })]);
    expect(response.accepted).toBe(true);
    await wrapper.vm.$nextTick();

    const actorLeft = wrapper.get('[data-testid="anchor-actor-left"]');
    expect(actorLeft.find('[data-testid="reference-artwork"]').exists()).toBe(true);
    // No focusable element: the portrait anchor is non-interactive art.
    expect(actorLeft.findAll("button, a, input, textarea, select, [tabindex]").length).toBe(0);
    // Exactly one stage portrait, and none left behind in the backdrop.
    expect(wrapper.findAll('[data-testid="elosern-stage"] [data-testid="reference-artwork"]').length).toBe(1);
    expect(wrapper.find(".stage-portrait").exists()).toBe(false);
    // actor-right is reserved (C10 hosts the dialogue actor there).
    expect(wrapper.get('[data-testid="anchor-actor-right"]').element.children.length).toBe(0);
  });
});
