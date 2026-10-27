// npc-targeted-service-flows: the selected provider's correlated read
// (`use-services-open.js`). One `services.open {npc_id}` per open, and only
// that request's own `{npc_id, services}` result is ever adopted — a stale,
// foreign, substituted or rejected answer closes the slot instead of showing
// another provider's surface.
import { describe, expect, it } from "vitest";
import { nextTick, reactive } from "vue";
import { useServicesOpen } from "../composables/use-services-open.js";
import {
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_SHOP_ROWS_SAMPLE,
} from "../stories/fixtures.js";

const SHOP_PROVIDER = SERVICES_PANEL_SHOP_ROWS_SAMPLE.shop.provider_id;

function setup() {
  const view = reactive({
    epoch: "epoch-1",
    generation: 1,
    revision: 3,
    lastActionResult: null,
    dispatch: { inFlight: null },
  });
  const sent = [];
  let counter = 0;
  const dispatchIntent = (actionId, payload) => {
    counter += 1;
    const requestId = `session:${counter}`;
    sent.push({ requestId, actionId, payload });
    return requestId;
  };
  const services = useServicesOpen({ view }, { dispatchIntent });
  return { view, sent, ...services };
}

function deliver(view, requestId, data, overrides = {}) {
  view.lastActionResult = {
    requestId,
    epoch: view.epoch,
    outcome: "success",
    data,
    ...overrides,
  };
}

describe("useServicesOpen", () => {
  it("dispatches one read for the selected provider and adopts its own result", async () => {
    const { view, sent, openServices, snapshots } = setup();
    openServices("shop", SHOP_PROVIDER);
    expect(sent).toEqual([
      {
        requestId: "session:1",
        actionId: "services.open",
        payload: { npc_id: SHOP_PROVIDER },
      },
    ]);
    expect(snapshots.value.shop).toBeUndefined();
    deliver(view, "session:1", {
      npc_id: SHOP_PROVIDER,
      services: SERVICES_PANEL_SHOP_ROWS_SAMPLE,
    });
    await nextTick();
    expect(snapshots.value.shop).toEqual(SERVICES_PANEL_SHOP_ROWS_SAMPLE);
    // Re-opening the same provider renders the committed snapshot again.
    expect(openServices("shop", SHOP_PROVIDER)).toBeNull();
    expect(sent).toHaveLength(1);
  });

  it("drops a foreign, substituted or over-wrapped result instead of reopening stale UI", async () => {
    const { view, openServices, snapshots } = setup();
    openServices("counter", 61);
    deliver(view, "session:1", {
      npc_id: 62,
      services: SERVICES_PANEL_MINIMAL_SAMPLE,
    });
    await nextTick();
    expect(snapshots.value.counter).toBeUndefined();

    openServices("counter", 61);
    const substituted = {
      ...SERVICES_PANEL_MINIMAL_SAMPLE,
      // A shipped section naming a different NPC is never the selection.
      guild: {
        provider_id: 62,
        branch_label: "合成公會分行",
        rank_ladder: ["F", "E", "D", "C", "B", "A", "S"],
        registration: {
          registered: false,
          register: {
            action_id: "guild.register",
            label: "註冊為冒險者",
            enabled: true,
            disabled_reason: null,
            quantity: null,
          },
        },
        board: [],
        quests: [],
      },
    };
    deliver(view, "session:2", { npc_id: 61, services: substituted });
    await nextTick();
    expect(snapshots.value.counter).toBeUndefined();

    openServices("counter", 61);
    deliver(view, "session:3", {
      npc_id: 61,
      services: SERVICES_PANEL_MINIMAL_SAMPLE,
      extra: null,
    });
    await nextTick();
    expect(snapshots.value.counter).toBeUndefined();
  });

  it("discards a late result after the transport epoch changed", async () => {
    const { view, sent, openServices, snapshots } = setup();
    openServices("shop", SHOP_PROVIDER);
    const request = sent[0].requestId;
    view.epoch = "epoch-2";
    await nextTick();
    deliver(view, request, {
      npc_id: SHOP_PROVIDER,
      services: SERVICES_PANEL_SHOP_ROWS_SAMPLE,
    });
    await nextTick();
    expect(snapshots.value.shop).toBeUndefined();
    // A retired epoch re-reads nothing on its own.
    expect(sent).toHaveLength(1);
  });

  it("repeats the same provider after a committed revision and drops a refusal", async () => {
    const { view, sent, openServices, snapshots } = setup();
    openServices("shop", SHOP_PROVIDER);
    deliver(view, "session:1", {
      npc_id: SHOP_PROVIDER,
      services: SERVICES_PANEL_SHOP_ROWS_SAMPLE,
    });
    await nextTick();
    expect(snapshots.value.shop).toEqual(SERVICES_PANEL_SHOP_ROWS_SAMPLE);

    // A purchase settled and committed: the open drawer reads the same
    // provider again rather than falling back to the room summary.
    view.revision += 1;
    await nextTick();
    expect(sent).toHaveLength(2);
    expect(sent[1]).toEqual({
      requestId: "session:2",
      actionId: "services.open",
      payload: { npc_id: SHOP_PROVIDER },
    });

    // The provider left or lost its capability: the snapshot is dropped and
    // never replaced by another provider's surface.
    deliver(view, "session:2", undefined, {
      outcome: "rejected",
      code: "no_such_target",
    });
    await nextTick();
    expect(snapshots.value.shop).toBeUndefined();
  });

  it("clears a slot when it is opened without a usable provider", async () => {
    const { view, sent, openServices, closeServices, snapshots } = setup();
    openServices("shop", SHOP_PROVIDER);
    deliver(view, "session:1", {
      npc_id: SHOP_PROVIDER,
      services: SERVICES_PANEL_SHOP_ROWS_SAMPLE,
    });
    await nextTick();
    expect(snapshots.value.shop).toEqual(SERVICES_PANEL_SHOP_ROWS_SAMPLE);
    openServices("shop", null);
    expect(snapshots.value.shop).toBeUndefined();
    expect(sent).toHaveLength(1);
    closeServices("counter");
    expect(snapshots.value.counter).toBeUndefined();
  });
});
