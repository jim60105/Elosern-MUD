// webclient-align-02-quickbar-shortcuts: the Tab-completion candidate
// wiring through the real AppClient -> AppShell -> CommandLine chain.
// A committed exploration panel's exit labels and interact-target display
// names must complete inside the command field; an unavailable or absent
// panel contributes no candidates (the client never reads uncommitted state).
import { beforeEach, describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../AppClient.vue";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";

describe("Tab completion candidates through AppClient (align-02 wiring)", () => {
  let store;
  let wrapper;

  let revision = 0;
  let transportBegun = false;
  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    revision = 0;
    transportBegun = false;
  });

  function mountApp() {
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    wrapper = mount(AppClient, { attachTo: host });
    return wrapper;
  }

  function commitPanels(panels) {
    if (!transportBegun) {
      store.beginTransport(1);
      store.setConnected(true);
      transportBegun = true;
    }
    revision += 1;
    const result = store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          revision,
          panels: { status: fx.statusPanel(), ...panels },
        }),
      ],
      {},
    );
    expect(result.accepted).toBe(true);
  }

  async function complete(prefix) {
    // Let the AppClient -> AppShell -> CommandLine prop chain re-render with
    // the freshly committed panel before typing.
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    const input = wrapper.get("textarea#inputfield");
    input.element.value = prefix;
    input.trigger("input");
    // Programmatic value assignment leaves the jsdom caret at 0; real typing
    // leaves it at the end, so place it explicitly.
    input.element.setSelectionRange(prefix.length, prefix.length);
    return new Promise((resolve) => {
      input.element.dispatchEvent(
        new KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true }),
      );
      wrapper.vm.$nextTick().then(() => wrapper.vm.$nextTick()).then(resolve);
    }).then(() => input.element.value);
  }

  it("exit labels and interact-target names from the committed panel complete", async () => {
    mountApp();
    commitPanels({ exploration: fx.explorationPanel() });
    // Fixture move row label: 西風酒館; interact target: 店長.
    expect(await complete("西風")).toBe("西風酒館");
    expect(await complete("店")).toBe("店長");
  });

  it("an absent exploration panel contributes no candidates", async () => {
    mountApp();
    commitPanels({});
    expect(await complete("西風")).toBe("西風", "no panel -> nothing completes");
  });

  it("the candidate source tracks the latest committed panel", async () => {
    // Leaving the room: the fresh commit replaces the exit rows, and the
    // completion set follows the committed state (no stale room's exits).
    mountApp();
    commitPanels({ exploration: fx.explorationPanel() });
    expect(await complete("北岸")).toBe("北岸大道");
    commitPanels({
      exploration: fx.explorationPanel({
        move: [{ exit_ref: "west", label: "南門官道", destination: "room:45", enabled: true, disabled_reason: null }],
      }),
    });
    expect(await complete("北岸")).toBe("北岸", "the departed exit no longer completes");
    expect(await complete("南門")).toBe("南門官道");
  });
});
