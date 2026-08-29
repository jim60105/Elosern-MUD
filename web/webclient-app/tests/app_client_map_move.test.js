// complete-ui-command-echo D3/D6: the minimap move surface exercised through
// the real wiring — clicking a movable lattice node in the mounted AppClient
// dispatches `explore.move` and echoes the uniquely matching committed edge
// label (or the destination node's label when the edge match is ambiguous).
// This is the AppClient.onMapMove <-> LocalMap.exitLabelFor integration row;
// the unique/ambiguous/silent rules themselves are pinned by the Node gate
// (web/static/webclient/js/tests/local_map.test.js).
import { beforeEach, describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../AppClient.vue";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";

describe("minimap move echo through AppClient (D6 surface row)", () => {
  let store;
  let sender;
  let wrapper;

  function mountApp() {
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    wrapper = mount(AppClient, { attachTo: host });
  }

  function openSession(localMap) {
    store.beginTransport(1);
    store.setConnected(true);
    const result = store.receive(
      1,
      "ui_snapshot",
      [
        {
          protocol_version: 1,
          presentation_epoch: fx.EPOCH_A,
          revision: 1,
          mode: "exploration",
          panels: {
            status: fx.statusPanel(),
            context_actions: fx.explorationActions(),
            local_map: localMap,
          },
          layout_version: 1,
          server_time: fx.serverTime(),
        },
      ],
      {},
    );
    expect(result.accepted).toBe(true);
  }

  function echoLines() {
    return store.narrative.filter((line) => line.kind === "in").map((line) => line.text);
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });

  it("clicking a movable lattice node echoes the unique traversable edge label", async () => {
    openSession(fx.localMapPanel());
    mountApp();
    await wrapper.find('[data-testid="local-map__node--room:43"]').trigger("click");
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0].action_id).toBe("explore.move");
    expect(sender.sent.actions[0].payload).toEqual({
      exit_ref: "east",
      current_node: "room:42",
    });
    expect(echoLines()).toEqual(["東"]);
    wrapper.unmount();
  });

  it("a parallel-edge (ambiguous) traversal echoes the destination node label, never an arbitrary edge", async () => {
    openSession(
      fx.localMapPanel({
        edges: [
          { source: "room:42", destination: "room:43", label: "東階", known: true, traversable: true },
          { source: "room:42", destination: "room:43", label: "東廊", known: true, traversable: true },
          { source: "room:42", destination: "room:44", label: "北", known: true, traversable: true },
        ],
      }),
    );
    mountApp();
    await wrapper.find('[data-testid="local-map__node--room:43"]').trigger("click");
    expect(sender.sent.actions).toHaveLength(1);
    expect(echoLines()).toEqual(["西風酒館"]);
    wrapper.unmount();
  });
});
