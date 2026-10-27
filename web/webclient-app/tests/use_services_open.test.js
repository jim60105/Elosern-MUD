// npc-targeted-service-flows: the selected provider's correlated read
// (`use-services-open.js`). One `services.open {npc_id}` per opening, and only
// that request's own `{npc_id, services}` result is ever adopted — a foreign,
// substituted, stale or rejected answer never becomes a surface, and a slot
// that was targeted keeps its provider until the drawer closes or reselects.
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
    if (view.dispatch.inFlight) return null;
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

function shopRead(providerId = SHOP_PROVIDER) {
  return { npc_id: providerId, services: SERVICES_PANEL_SHOP_ROWS_SAMPLE };
}

describe("useServicesOpen", () => {
  it("dispatches one read for the selected provider and adopts its own result", async () => {
    const { view, sent, openServices, slots } = setup();
    openServices("shop", SHOP_PROVIDER);
    expect(sent).toEqual([
      {
        requestId: "session:1",
        actionId: "services.open",
        payload: { npc_id: SHOP_PROVIDER },
      },
    ]);
    // In flight: the slot is targeted, with no surface and no refusal yet.
    expect(slots.value.shop).toMatchObject({
      providerId: SHOP_PROVIDER,
      requestId: "session:1",
      snapshot: null,
      refusal: null,
    });
    deliver(view, "session:1", shopRead());
    await nextTick();
    expect(slots.value.shop.snapshot).toEqual(SERVICES_PANEL_SHOP_ROWS_SAMPLE);
    expect(slots.value.shop.requestId).toBeNull();
    // Re-opening the same provider renders the committed snapshot again.
    expect(openServices("shop", SHOP_PROVIDER)).toBeNull();
    expect(sent).toHaveLength(1);
  });

  it("keeps the targeted provider but drops a foreign, substituted or over-wrapped result", async () => {
    const { view, sent, openServices, slots } = setup();
    openServices("counter", 61);
    deliver(view, "session:1", { npc_id: 62, services: SERVICES_PANEL_MINIMAL_SAMPLE });
    await nextTick();
    expect(slots.value.counter).toMatchObject({ providerId: 61, snapshot: null });
    expect(slots.value.counter.refusal).toMatchObject({ code: "service_rejected" });

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
    expect(slots.value.counter.snapshot).toBeNull();
    expect(slots.value.counter.refusal).not.toBeNull();

    openServices("counter", 61);
    deliver(view, "session:3", {
      npc_id: 61,
      services: SERVICES_PANEL_MINIMAL_SAMPLE,
      extra: null,
    });
    await nextTick();
    expect(slots.value.counter.snapshot).toBeNull();
    expect(sent).toHaveLength(3);
  });

  it("discards a late result after the transport epoch changed", async () => {
    const { view, sent, openServices, slots } = setup();
    openServices("shop", SHOP_PROVIDER);
    const request = sent[0].requestId;
    view.epoch = "epoch-2";
    await nextTick();
    deliver(view, request, shopRead());
    await nextTick();
    expect(slots.value.shop).toBeUndefined();
    // A retired epoch re-reads nothing on its own.
    expect(sent).toHaveLength(1);
  });

  it("discards a late result after the puppet generation changed", async () => {
    const { view, sent, openServices, slots } = setup();
    openServices("shop", SHOP_PROVIDER);
    const request = sent[0].requestId;
    view.generation = 2;
    await nextTick();
    deliver(view, request, shopRead());
    await nextTick();
    expect(slots.value.shop).toBeUndefined();
    expect(sent).toHaveLength(1);
  });

  it("drops a slot closed while its read was still in flight", async () => {
    const { view, sent, openServices, closeServices, slots } = setup();
    openServices("shop", SHOP_PROVIDER);
    closeServices("shop");
    deliver(view, sent[0].requestId, shopRead());
    await nextTick();
    expect(slots.value.shop).toBeUndefined();
    // A settled read for a closed slot never starts another one.
    expect(sent).toHaveLength(1);
  });

  it("retargets a slot and never adopts the previous provider's answer", async () => {
    const { view, sent, openServices, slots } = setup();
    openServices("shop", SHOP_PROVIDER);
    openServices("shop", 77);
    deliver(view, sent[0].requestId, shopRead());
    await nextTick();
    expect(slots.value.shop).toMatchObject({ providerId: 77, snapshot: null });
    deliver(view, sent[1].requestId, {
      npc_id: 77,
      services: { ...SERVICES_PANEL_MINIMAL_SAMPLE },
    });
    await nextTick();
    expect(slots.value.shop.providerId).toBe(77);
    expect(slots.value.shop.snapshot).toEqual(SERVICES_PANEL_MINIMAL_SAMPLE);
  });

  it("repeats the same provider after a committed revision and keeps a refusal in place", async () => {
    const { view, sent, openServices, slots } = setup();
    openServices("shop", SHOP_PROVIDER);
    deliver(view, "session:1", shopRead());
    await nextTick();
    expect(slots.value.shop.snapshot).toEqual(SERVICES_PANEL_SHOP_ROWS_SAMPLE);

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
    // the slot keeps its identity, so the drawer states the refusal instead of
    // rendering another provider's surface.
    deliver(view, "session:2", undefined, {
      outcome: "rejected",
      code: "no_such_target",
      message: "這裡沒有這個對象。",
    });
    await nextTick();
    expect(slots.value.shop.snapshot).toBeNull();
    expect(slots.value.shop).toMatchObject({
      providerId: SHOP_PROVIDER,
      refusal: { code: "no_such_target", message: "這裡沒有這個對象。" },
    });
  });

  it("replays an opening the single-action store refused while another action was in flight", async () => {
    const { view, sent, openServices, slots } = setup();
    view.dispatch.inFlight = { requestId: "session:0" };
    openServices("shop", SHOP_PROVIDER);
    expect(sent).toHaveLength(0);
    expect(slots.value.shop).toBeUndefined();

    // The other action settles (result delivered, gate released): the
    // remembered opening reads its provider.
    deliver(view, "session:0", undefined, { outcome: "success" });
    view.dispatch.inFlight = null;
    await nextTick();
    expect(sent).toEqual([
      {
        requestId: "session:1",
        actionId: "services.open",
        payload: { npc_id: SHOP_PROVIDER },
      },
    ]);
    expect(slots.value.shop).toMatchObject({ providerId: SHOP_PROVIDER });
  });

  it("cancels a remembered opening when the drawer closes or reselects", async () => {
    const { view, sent, openServices, closeServices } = setup();
    view.dispatch.inFlight = { requestId: "session:0" };
    openServices("shop", SHOP_PROVIDER);
    closeServices("shop");
    deliver(view, "session:0", undefined, { outcome: "success" });
    view.dispatch.inFlight = null;
    await nextTick();
    expect(sent).toHaveLength(0);
  });

  it("clears a slot when it is opened without a usable provider", async () => {
    const { view, sent, openServices, closeServices, slots } = setup();
    openServices("shop", SHOP_PROVIDER);
    deliver(view, "session:1", shopRead());
    await nextTick();
    expect(slots.value.shop.snapshot).toEqual(SERVICES_PANEL_SHOP_ROWS_SAMPLE);
    openServices("shop", null);
    expect(slots.value.shop).toBeUndefined();
    expect(sent).toHaveLength(1);
    closeServices("counter");
    expect(slots.value.counter).toBeUndefined();
  });
});
