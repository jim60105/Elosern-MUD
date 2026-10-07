import { afterEach, describe, expect, it, vi } from "vitest";
import { flushPromises } from "@vue/test-utils";
import GmEntityView from "../components/GmEntityView.vue";
import { NPC_DETAIL, NPC_RAW, errorWith, fakeApi, mountWith } from "./runtime-helpers.js";

const CALL = "ab".repeat(16);

function api(overrides = {}) {
  const callPath = `/llm/calls/${CALL}`;
  return fakeApi({
    "/state/npcs/12": NPC_DETAIL,
    "/state/object/12/raw": NPC_RAW,
    "/state/npcs/12?owner=%2312": NPC_DETAIL,
    [callPath]: { outcome: null, exchanges: [] },
    ...overrides,
  });
}

describe("GmEntityView", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("loads the curated summary and shows the identifiers above the tabs", async () => {
    const boundary = api();
    const wrapper = mountWith(GmEntityView, { props: { kind: "npcs", id: "12", api: boundary } });
    await flushPromises();
    expect(boundary.calls[0]).toEqual({ method: "get", path: "/state/npcs/12" });
    expect(wrapper.get("h2").text()).toBe("合成守衛");
    expect(wrapper.get(".gm-entity__eyebrow").text()).toContain("NPC");
    expect(wrapper.get(".gm-entity__typeclass").text()).toBe("typeclasses.npcs.NPC");
    expect(wrapper.get(".gm-entity__ids dd").text()).toBe("#12");
    expect(wrapper.findAll("[role='tab']").map((tab) => tab.text())).toEqual([
      "概要",
      "原始資料",
      "記憶",
      "對話",
    ]);
    expect(wrapper.get("[role='tab'][aria-selected='true']").text()).toBe("概要");
    expect(wrapper.findAll(".gm-section").map((node) => node.attributes("data-section"))).toEqual([
      "identity",
      "services",
      "links",
      "memory_trace",
      "persona",
    ]);
    // A failing section stays in its own slot; the rest of the page renders.
    expect(wrapper.get("[data-section='persona']").attributes("data-type")).toBe("empty");
  });

  it("keeps the non-NPC tab set to 概要 and 原始資料", async () => {
    const wrapper = mountWith(GmEntityView, {
      props: {
        kind: "art",
        id: "art:t_subject",
        api: api({ "/state/art/art%3At_subject": { ...NPC_DETAIL, kind: "art", dbref: null, raw: { record: {} } } }),
      },
    });
    await flushPromises();
    expect(wrapper.findAll("[role='tab']").map((tab) => tab.text())).toEqual(["概要", "原始資料"]);
  });

  it("loads the universal raw inventory from the object route for a dbref kind", async () => {
    const boundary = api();
    const wrapper = mountWith(GmEntityView, { props: { kind: "npcs", id: "12", api: boundary } });
    await flushPromises();
    await wrapper.findAll("[role='tab']")[1].trigger("click");
    await flushPromises();
    expect(boundary.calls.at(-1)).toEqual({ method: "get", path: "/state/object/12/raw" });
    const tree = wrapper.get(".gm-json-tree");
    expect(tree.text()).toContain("t_count");
    expect(tree.text()).toContain("⟨set⟩");
    // The root reference links the inspected object itself; the location's
    // reference links the room it stands in.
    expect(tree.findAll("a").map((node) => node.attributes("href"))).toEqual([
      "/gm/runtime/object/12/raw",
      "/gm/runtime/object/3/raw",
    ]);
  });

  it("renders a record-backed raw tab from the detail payload instead", async () => {
    const detail = { ...NPC_DETAIL, kind: "art", dbref: null, raw: { record: { status: "failed" } } };
    const wrapper = mountWith(GmEntityView, {
      props: { kind: "art", id: "art:t_subject", api: api({ "/state/art/art%3At_subject": detail }) },
    });
    await flushPromises();
    await wrapper.findAll("[role='tab']")[1].trigger("click");
    await flushPromises();
    expect(wrapper.get(".gm-json-tree").text()).toContain("failed");
  });

  it("renders only the raw tab for an uncurated object and never calls the detail route", async () => {
    const boundary = fakeApi({ "/state/object/7/raw": { ...NPC_RAW, id: "7", dbref: 7 } });
    const wrapper = mountWith(GmEntityView, { props: { kind: "object", id: "7", api: boundary } });
    await flushPromises();
    expect(wrapper.findAll("[role='tab']").map((tab) => tab.text())).toEqual(["原始資料"]);
    // Only the raw route is asked; ``/state/object/<id>`` (the detail family,
    // which refuses the object kind) is never called.
    expect(boundary.calls).toEqual([{ method: "get", path: "/state/object/7/raw" }]);
    expect(wrapper.get("h2").text()).toBe("合成守衛");
  });

  it("refreshes only when asked and never schedules a timer", async () => {
    const interval = vi.spyOn(globalThis, "setInterval");
    const timeout = vi.spyOn(globalThis, "setTimeout");
    const boundary = api();
    const wrapper = mountWith(GmEntityView, { props: { kind: "npcs", id: "12", api: boundary } });
    await flushPromises();
    expect(boundary.calls).toHaveLength(1);
    await wrapper.get(".gm-entity__actions button").trigger("click");
    await flushPromises();
    expect(boundary.calls).toHaveLength(2);
    expect(interval).not.toHaveBeenCalled();
    // No delayed reload is armed either: the surface is manually refreshed.
    expect(timeout.mock.calls.every(([, delay]) => !delay)).toBe(true);
    expect(wrapper.get(".gm-entity__stamp").text()).toContain("最後載入");
  });

  it("surfaces a precise lookup error with a retry", async () => {
    const boundary = api({ "/state/npcs/99": errorWith("object_not_found", "找不到指定的物件。", 404) });
    const wrapper = mountWith(GmEntityView, { props: { kind: "npcs", id: "99", api: boundary } });
    await flushPromises();
    const error = wrapper.get(".gm-error");
    expect(error.text()).toContain("找不到指定的物件");
    expect(error.get("code").text()).toBe("object_not_found");
    await error.get("button").trigger("click");
    await flushPromises();
    expect(boundary.calls).toHaveLength(2);
  });

  it("opens the retained S2 drawer from a call identifier in a section", async () => {
    const boundary = api();
    const wrapper = mountWith(GmEntityView, {
      props: { kind: "npcs", id: "12", api: boundary },
      attachTo: document.body,
    });
    await flushPromises();
    await wrapper.get("[data-section='memory_trace'] button").trigger("click");
    await flushPromises();
    expect(boundary.calls.at(-1)).toEqual({ method: "get", path: `/llm/calls/${CALL}` });
    expect(wrapper.find("dialog.gm-call-drawer").exists()).toBe(true);
  });

  it("carries the owner identity into a record-backed detail request", async () => {
    const boundary = fakeApi({ "/state/memories/31": NPC_DETAIL });
    mountWith(GmEntityView, {
      props: { kind: "memories", id: "31", owner: "#12", api: boundary },
    });
    await flushPromises();
    expect(boundary.calls).toEqual([{ method: "get", path: "/state/memories/31?owner=%2312" }]);
  });
});
