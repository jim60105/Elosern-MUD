// The server-owned contextual sleep surface (align-sleep-handoff-and-owner-
// dream): the complete companion list, exact party label, owner-only dream
// question and retained continuation. The browser derives no eligibility and
// sends one action per decision.
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../AppClient.vue";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";

function sleepHandoffPanel(overrides = undefined) {
  return {
    schema_version: 1,
    available: true,
    owner_id: 42,
    controlled_body_id: 42,
    transition_id: "42:v:1",
    selection: {
      available: true,
      rows: [
        {
          kind: "possess",
          identity: 2,
          name: "同伴",
          reserve_percent: 100,
          stage: "normal",
          label: "接手 同伴（精神儲備 100%）",
          enabled: true,
          reason: null,
        },
        {
          kind: "possess",
          identity: 3,
          name: "沉睡者",
          reserve_percent: 5,
          stage: "sleeping",
          label: "接手 沉睡者（精神儲備 5%）",
          enabled: false,
          reason: "沉睡中，無法行動",
        },
      ],
    },
    party: { label: "全員一起睡眠", enabled: true, reason: null },
    controlled_sleep: { sleep_id: "sleep-1", revision: 0 },
    owner_sleep: {
      sleep_id: "sleep-1",
      revision: 0,
      generation: 1,
      dream_pending: true,
      continuation: "none",
      continuation_available: true,
      continuation_reason: null,
    },
    ...(overrides || {}),
  };
}

describe("AppClient sleep handoff (align-sleep-handoff-and-owner-dream)", () => {
  let store;
  let wrapper;
  let sender;
  let revision;

  async function settle() {
    for (let i = 0; i < 4; i += 1) {
      await nextTick();
    }
  }

  async function mountWith(panel = sleepHandoffPanel()) {
    wrapper = mount(AppClient, { attachTo: document.body });
    store.beginTransport(1);
    store.setConnected(true);
    store.setLoggedIn(true);
    revision = 1;
    const result = store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          revision,
          mode: "exploration",
          panels: {
            status: fx.statusPanel(),
            exploration: fx.explorationPanel(),
            local_map: fx.localMapPanel(),
            context_actions: fx.explorationActions(),
            sleep_handoff: panel,
          },
        }),
      ],
      {},
    );
    expect(result.accepted).toBe(true);
    await settle();
  }

  const card = () => wrapper.find('[data-anchor="choices"] [data-testid="sleep-handoff-card"]');
  const question = () => wrapper.find('[data-anchor="choices"] [data-testid="dream-question"]');
  const rows = () => card().findAll('[role="menuitem"]');

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  it("opens automatically with every companion, one disabled reason and the exact final party label", async () => {
    await mountWith();
    expect(card().exists()).toBe(true);
    expect(sender.sent.actions).toHaveLength(0);
    const labels = rows().map((row) => row.text());
    expect(labels.some((text) => text.includes("接手 同伴（精神儲備 100%）"))).toBe(true);
    expect(
      labels.some((text) =>
        text.includes("接手 沉睡者（精神儲備 5%）沉睡中，無法行動"),
      ),
    ).toBe(true);
    expect(labels[labels.length - 1]).toContain("返回");
    expect(labels[labels.length - 2]).toContain("全員一起睡眠");
  });

  it("dispatches one exact possess action for an enabled companion", async () => {
    await mountWith();
    await rows()[0].trigger("click");
    await settle();
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({
      action_id: "explore.possess",
      payload: { npc_id: 2 },
    });
  });

  it("does not dispatch a disabled companion", async () => {
    await mountWith();
    await rows()[1].trigger("click");
    await settle();
    expect(sender.sent.actions).toHaveLength(0);
    expect(card().exists()).toBe(true);
  });

  it("dispatches the party choice exactly once", async () => {
    await mountWith();
    const party = rows().find((row) =>
      row.text().includes("全員一起睡眠"),
    );
    await party.trigger("click");
    await settle();
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({
      action_id: "explore.sleep_party",
      payload: {},
    });
  });

  it("cancel keeps zero time, then reveals the owner-only question", async () => {
    await mountWith();
    await card().get('[data-row-key="back"]').trigger("click");
    await settle();
    expect(card().exists()).toBe(false);
    expect(question().exists()).toBe(true);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("yes answers enter with the exact sleep identity", async () => {
    await mountWith();
    await card().get('[data-row-key="back"]').trigger("click");
    await settle();
    await question().get('[data-testid="question-card-yes"]').trigger("click");
    await settle();
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({
      action_id: "explore.sleep_dream",
      payload: {
        sleep_id: "sleep-1",
        revision: 0,
        generation: 1,
        decision: "enter",
      },
    });
  });

  it("no and close both answer decline", async () => {
    for (const control of ["no", "close"]) {
      setActivePinia(createPinia());
      store = useElosernStore();
      sender = fx.createFakeSender();
      store.setSender(sender);
      await mountWith();
      await card().get('[data-row-key="back"]').trigger("click");
      await settle();
      await question().get(`[data-testid="question-card-${control}"]`).trigger("click");
      await settle();
      expect(sender.sent.actions).toHaveLength(1);
      expect(sender.sent.actions[0]).toMatchObject({
        action_id: "explore.sleep_dream",
        payload: { decision: "decline" },
      });
      wrapper.unmount();
      wrapper = null;
      document.body.innerHTML = "";
    }
  });

  it("shows the question directly when every companion is already asleep", async () => {
    const panel = sleepHandoffPanel({
      selection: {
        available: false,
        rows: [
          {
            kind: "possess",
            identity: 3,
            name: "沉睡者",
            reserve_percent: 5,
            stage: "sleeping",
            label: "接手 沉睡者（精神儲備 5%）",
            enabled: false,
            reason: "沉睡中，無法行動",
          },
        ],
      },
      party: { label: "全員一起睡眠", enabled: false, reason: "在場成員都已入睡或已完全恢復" },
    });
    await mountWith(panel);
    expect(card().exists()).toBe(false);
    expect(question().exists()).toBe(true);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("offers the retained continuation after a decline with an awake companion", async () => {
    const panel = sleepHandoffPanel({
      owner_sleep: {
        sleep_id: "sleep-1",
        revision: 0,
        generation: 1,
        dream_pending: false,
        continuation: "none",
        continuation_available: true,
        continuation_reason: null,
      },
    });
    await mountWith(panel);
    const continuation = rows().find((row) =>
      row.text().includes("繼續睡眠"),
    );
    expect(continuation).toBeDefined();
    await continuation.trigger("click");
    await settle();
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({
      action_id: "explore.sleep_continue",
      payload: { sleep_id: "sleep-1", revision: 0 },
    });
  });

  it("locks every row while another action is in flight", async () => {
    await mountWith();
    store.dispatchAction("explore.look", { room: true });
    await settle();
    expect(rows()[0].attributes("aria-disabled")).toBe("true");
    await rows()[0].trigger("click");
    await settle();
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0].action_id).toBe("explore.look");
  });
});
