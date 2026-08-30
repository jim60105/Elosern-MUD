// title-epithet-nomination (composition contract): the 異名提名 ballot menu
// mounts from the committed `title_ballot` panel, dispatches its numbered
// accept and decline intents through the SAME single store dispatch entry as
// the shop/quest surfaces (one deliberate activation, one envelope), and the
// answering server-side consumption — a `title_ballot` panel update with zero
// candidates — unmounts the menu immediately.
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../AppClient.vue";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";

function ballotCandidate(index) {
  return {
    index,
    display: `異名${index}`,
    basis: `第${index}條事蹟引用。`,
  };
}

function ballotPanel(count) {
  return {
    schema_version: 1,
    available: true,
    kind: "title_ballot",
    candidates: Array.from({ length: count }, (_, i) => ballotCandidate(i + 1)),
  };
}

describe("ballot menu composition (title-epithet-nomination)", () => {
  let store;
  let sender;
  let wrapper;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });

  function mountApp() {
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    wrapper = mount(AppClient, { attachTo: host });
    return wrapper;
  }

  async function commitSnapshot(ballot, revision) {
    const panels = {
      status: fx.statusPanel(),
      exploration: fx.explorationPanel(),
      context_actions: fx.explorationActions(),
    };
    if (ballot !== null) {
      panels.title_ballot = ballot;
    }
    const result = store.receive(
      1,
      "ui_snapshot",
      [fx.snapshot({ panels, revision })],
      {},
    );
    expect(result.accepted).toBe(true);
    await wrapper.vm.$nextTick();
  }

  async function openExploration(ballot) {
    store.beginTransport(1);
    store.setConnected(true);
    await commitSnapshot(ballot, 1);
  }

  function lastEnvelope() {
    return sender.sent.actions[sender.sent.actions.length - 1];
  }

  it("mounts the menu with one accept button per candidate from the committed panel", async () => {
    mountApp();
    await openExploration(ballotPanel(3));
    const menu = wrapper.get('[data-testid="title-ballot-menu"]');
    expect(menu.text()).toContain("2. 異名2");
    expect(menu.text()).toContain("「第3條事蹟引用。」");
    expect(wrapper.findAll(".title-ballot__accept")).toHaveLength(3);
    expect(wrapper.find('[data-testid="title-ballot-menu__decline"]').exists()).toBe(true);
  });

  it("does not mount for the idle zero-candidate or absent panel forms", async () => {
    mountApp();
    await openExploration(ballotPanel(0));
    expect(wrapper.find('[data-testid="title-ballot-menu"]').exists()).toBe(false);
    await commitSnapshot(null, 2);
    expect(wrapper.find('[data-testid="title-ballot-menu"]').exists()).toBe(false);
  });

  it("接受 2 dispatches exactly one title.accept envelope through the store", async () => {
    mountApp();
    await openExploration(ballotPanel(2));
    await wrapper.get('[data-testid="title-ballot-menu__accept--2"]').trigger("click");
    expect(sender.sent.actions).toHaveLength(1);
    expect(lastEnvelope().action_id).toBe("title.accept");
    expect(lastEnvelope().payload).toEqual({ index: 2 });
    expect(lastEnvelope().protocol_version).toBe(1);
    // The input echo replays the typed command (catalog resolves the index).
    const echo = store.narrative.filter((line) => line.kind === "in").map((l) => l.text);
    expect(echo).toContain("title accept 2");
  });

  it("the ballot panel update after answering unmounts the menu immediately", async () => {
    mountApp();
    await openExploration(ballotPanel(1));
    await wrapper.get('[data-testid="title-ballot-menu__accept--1"]').trigger("click");
    const result = store.receive(
      1,
      "ui_action_result",
      [fx.actionResult({ request_id: "session:1", presentation_revision: 2 })],
      {},
    );
    expect(result.accepted).toBe(true);
    const update = store.receive(
      1,
      "ui_update",
      [fx.update({ revision: 2, panels: { title_ballot: ballotPanel(0) } })],
      {},
    );
    expect(update.accepted).toBe(true);
    await wrapper.vm.$nextTick();
    expect(wrapper.find('[data-testid="title-ballot-menu"]').exists()).toBe(false);
  });

  it("放棄 dispatches exactly one empty title.decline envelope", async () => {
    mountApp();
    await openExploration(ballotPanel(3));
    await wrapper.get('[data-testid="title-ballot-menu__decline"]').trigger("click");
    expect(sender.sent.actions).toHaveLength(1);
    expect(lastEnvelope().action_id).toBe("title.decline");
    expect(lastEnvelope().payload).toEqual({});
    const echo = store.narrative.filter((line) => line.kind === "in").map((l) => l.text);
    expect(echo).toContain("title decline");
  });
});
