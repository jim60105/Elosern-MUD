// webclient-party-window-member-tab: the party window in the running client.
// It mounts under the `party` drawer key; a companion figure on the stage
// lineup opens 成員 with that companion (one `party.view_member`, pending
// until the server adopts it); a rail selection sends the open tab; 人物卡
// opens the NPC persona editor; 附身 dispatches its descriptor; the window
// closes with the party panel.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import AppClient from "../AppClient.vue";
import { resetPartyWindowMemory } from "../components/party-window-memory.js";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";
import {
  PARTY_MEMBER_COMPANION_SAMPLE,
  PARTY_MEMBER_PANEL_SAMPLE,
  PARTY_WINDOW_PANEL_SAMPLE,
} from "../stories/fixtures/party_panels.js";

const COMMANDER_VIEW = { ...PARTY_WINDOW_PANEL_SAMPLE, viewed_member_id: 42 };

describe("the party window in AppClient (webclient-party-window-member-tab)", () => {
  let store;
  let wrapper;
  let sender;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    resetPartyWindowMemory();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
    document.body.innerHTML = "";
  });

  async function mountWith(panels, mode = "exploration") {
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    wrapper = mount(AppClient, { attachTo: host });
    store.beginTransport(1);
    store.setConnected(true);
    store.receive(1, "ui_snapshot", [
      fx.snapshot({ mode, panels: { status: fx.statusPanel(), exploration: fx.explorationPanel(), ...panels } }),
    ]);
    await wrapper.vm.$nextTick();
  }

  const viewRequests = () => sender.sent.actions.filter((envelope) => envelope.action_id === "party.view_member");
  const entry = (id) => wrapper.get(`[data-testid="member-rail__entry--${id}"]`);

  it("opens 成員 with the activated lineup companion, pending until the server adopts it", async () => {
    await mountWith({ party: COMMANDER_VIEW, party_member: PARTY_MEMBER_PANEL_SAMPLE });
    const hits = wrapper.findAll('[data-testid="companion-member-hit"]').map((node) => Number(node.attributes("data-identity")));
    // Every companion figure, never the commander's own.
    expect(hits.sort()).toEqual([101, 102, 103]);
    await wrapper.get('[data-testid="companion-member-hit"][data-identity="102"]').trigger("click");
    expect(store.view.hudDrawer).toBe("party");
    expect(wrapper.get('[data-testid="party-window"]').attributes("data-tab")).toBe("member");
    expect(viewRequests()).toHaveLength(1);
    expect(viewRequests()[0].payload).toEqual({ member_id: 102, tab: "member", skill_key: null, item_key: null });
    expect(entry(102).attributes("aria-busy")).toBe("true");
    expect(entry(42).attributes("aria-current")).toBe("true");
    store.receive(1, "ui_action_result", [fx.actionResult({ request_id: viewRequests()[0].request_id, presentation_revision: 2 })]);
    store.receive(1, "ui_update", [
      fx.update({
        revision: 2,
        panels: {
          party: { ...PARTY_WINDOW_PANEL_SAMPLE, viewed_member_id: 102 },
          party_member: { ...PARTY_MEMBER_COMPANION_SAMPLE, member_id: 102, companion: { ...PARTY_MEMBER_COMPANION_SAMPLE.companion, actions: PARTY_MEMBER_COMPANION_SAMPLE.companion.actions.map((a) => ({ ...a, params: { npc_id: 102 } })) } },
        },
      }),
    ]);
    await wrapper.vm.$nextTick();
    expect(entry(102).attributes("aria-current")).toBe("true");
    expect(entry(102).attributes("aria-busy")).toBeUndefined();
  });

  it("opens on 成員 without a request for the already viewed companion, and only in exploration", async () => {
    await mountWith({ party: PARTY_WINDOW_PANEL_SAMPLE, party_member: PARTY_MEMBER_COMPANION_SAMPLE });
    await wrapper.get('[data-testid="companion-member-hit"][data-identity="101"]').trigger("click");
    expect(store.view.hudDrawer).toBe("party");
    expect(viewRequests()).toHaveLength(0);
    wrapper.unmount();
    document.body.innerHTML = "";
    setActivePinia(createPinia());
    store = useElosernStore();
    await mountWith({ party: PARTY_WINDOW_PANEL_SAMPLE }, "dialogue");
    expect(wrapper.find('[data-testid="companion-member-hit"]').exists()).toBe(false);
  });

  it("sends one party.view_member with the open tab for a rail selection, and none while busy", async () => {
    await mountWith({ party: PARTY_WINDOW_PANEL_SAMPLE, party_member: PARTY_MEMBER_COMPANION_SAMPLE });
    store.openHudDrawer("party");
    await wrapper.vm.$nextTick();
    await wrapper.get('[data-testid="icon-tabs__tab--status"]').trigger("click");
    await entry(42).trigger("click");
    expect(viewRequests().map((envelope) => envelope.payload)).toEqual([
      { member_id: 42, tab: "status", skill_key: null, item_key: null },
    ]);
    // The single dispatch slot is busy: the next selection is refused with
    // the busy toast and marks nothing pending.
    await entry(103).trigger("click");
    expect(viewRequests()).toHaveLength(1);
    expect(entry(103).attributes("aria-busy")).toBeUndefined();
    expect(store.view.toasts.some((toast) => toast.title === "目前無法執行此操作，請稍後再試。")).toBe(true);
  });

  it("opens the NPC persona editor from 人物卡 and dispatches 附身 from its descriptor", async () => {
    await mountWith({ party: PARTY_WINDOW_PANEL_SAMPLE, party_member: PARTY_MEMBER_COMPANION_SAMPLE });
    store.openHudDrawer("party");
    await wrapper.vm.$nextTick();
    await wrapper.get('[data-testid="action-bar__btn--possess"]').trigger("click");
    expect(sender.sent.actions.at(-1).action_id).toBe("explore.possess");
    expect(sender.sent.actions.at(-1).payload).toEqual({ npc_id: 101 });
    store.receive(1, "ui_action_result", [fx.actionResult({ request_id: sender.sent.actions.at(-1).request_id, outcome: "rejected", code: "nope", message: "不行。", presentation_revision: 1 })]);
    await wrapper.vm.$nextTick();
    await wrapper.get('[data-testid="action-bar__btn--npc-persona"]').trigger("click");
    await wrapper.vm.$nextTick();
    expect(store.view.hudDrawer).toBe("npc_persona");
  });

  it("closes the window when the party panel becomes unavailable", async () => {
    await mountWith({ party: PARTY_WINDOW_PANEL_SAMPLE, party_member: PARTY_MEMBER_COMPANION_SAMPLE });
    store.openHudDrawer("party");
    await wrapper.vm.$nextTick();
    expect(wrapper.find('[data-testid="party-window"]').exists()).toBe(true);
    store.receive(1, "ui_update", [
      fx.update({ revision: 2, panels: { party: { schema_version: 3, available: false, reason: { code: "party_unavailable", message: "隊伍資訊目前無法顯示" } } } }),
    ]);
    await wrapper.vm.$nextTick();
    expect(store.view.hudDrawer).toBe(null);
    expect(wrapper.find('[data-testid="party-window"]').exists()).toBe(false);
  });
});
