import { describe, expect, it, vi } from "vitest";
import { flushPromises } from "@vue/test-utils";
import GmEntityView from "../components/GmEntityView.vue";
import GmNpcDialogueTab from "../components/GmNpcDialogueTab.vue";
import GmNpcMemoryTab from "../components/GmNpcMemoryTab.vue";
import {
  DIALOGUE_DETAIL,
  DIALOGUE_PAGE,
  MEMORY_DETAIL,
  MEMORY_ITEM,
  NPC_DETAIL,
  RECALL_RESULT,
  SNAPSHOT_ITEM,
  errorWith,
  fakeApi,
  listPage,
  mountWith,
} from "./runtime-helpers.js";

const SNAPSHOT_DETAIL = {
  id: "t_snapshot_1",
  kind: "snapshots",
  label: "t_capability",
  dbref: null,
  sections: [
    {
      key: "identity",
      title: "情境快照",
      type: "ledger",
      rows: [{ key: "能力", label: "能力", value: "t_capability", mono: true }],
    },
  ],
};

function memoryApi(overrides = {}) {
  return fakeApi({
    "/state/memories": listPage([MEMORY_ITEM], "cursor-1"),
    "/state/memories/31": MEMORY_DETAIL,
    "/state/snapshots": listPage([SNAPSHOT_ITEM]),
    "/state/snapshots/t_snapshot_1": SNAPSHOT_DETAIL,
    "/state/npc/12/recall": RECALL_RESULT,
    ...overrides,
  });
}

describe("GmNpcMemoryTab", () => {
  it("retracts and supersedes with same-owner choices, refreshed history/generation and no polling", async () => {
    const timer=vi.spyOn(globalThis,"setInterval");
    const boundary=memoryApi({
      "/state/memories":listPage([MEMORY_ITEM,{...MEMORY_ITEM,id:"32"}]),
      "/console/status":{tick:42,baseline_tick:42,will_snapshot:false},
      "/console/retract_memory":{target:"#12",state:{generation:9},snapshot:{taken:false,save_id:null}},
      "/console/supersede_memory":{target:"#12",state:{generation:11},snapshot:{taken:false,save_id:null}},
    });
    const wrapper=mountWith(GmNpcMemoryTab,{props:{npcDbref:"12",api:boundary}});
    await flushPromises();
    await wrapper.get("[data-block='memories'] button[aria-expanded]").trigger("click"); await flushPromises();
    await wrapper.get("[data-action='retract']").trigger("click"); await flushPromises();
    await wrapper.get("[data-confirm]").trigger("click"); await flushPromises();
    expect(boundary.calls.find(call=>call.path==="/console/retract_memory").body).toEqual({target:"#12",memory_id:31});
    expect(wrapper.text()).toContain("記憶世代 9");
    expect(boundary.calls.filter(call=>call.path==="/state/memories/31?owner=%2312")).toHaveLength(2);
    const selector=wrapper.get("[data-block='memories'] .gm-list__extra select");
    expect(selector.findAll("option").map(node=>node.element.value)).toEqual(["","32"]);
    await selector.setValue("32");
    await wrapper.get("[data-action='supersede']").trigger("click"); await flushPromises();
    await wrapper.get("[data-confirm]").trigger("click"); await flushPromises();
    expect(boundary.calls.find(call=>call.path==="/console/supersede_memory").body).toEqual({target:"#12",memory_id:31,replacement_id:32});
    expect(wrapper.text()).toContain("記憶世代 11");
    expect(timer).not.toHaveBeenCalled();
    timer.mockRestore();
  });

  it("loads the owner-scoped memory list and the newest-ten snapshot page", async () => {
    const boundary = memoryApi();
    const wrapper = mountWith(GmNpcMemoryTab, { props: { npcDbref: "12", api: boundary } });
    await flushPromises();
    expect(boundary.calls.map((call) => call.path)).toEqual([
      "/state/memories?owner=%2312&limit=50",
      "/state/snapshots?owner=%2312&limit=10",
    ]);
    expect(wrapper.get("table").text()).toContain("observation");
    expect(wrapper.text()).toContain("最新十筆");
    // The tab carries its own manual refresh (the entity header reloads the
    // summary/raw tabs, not this collection pair).
    await wrapper.get(".gm-memory__refresh").trigger("click");
    await flushPromises();
    expect(boundary.calls.map((call) => call.path)).toEqual([
      "/state/memories?owner=%2312&limit=50",
      "/state/snapshots?owner=%2312&limit=10",
      "/state/memories?owner=%2312&limit=50",
      "/state/snapshots?owner=%2312&limit=10",
    ]);
  });

  it("restarts pagination when a filter changes and follows the cursor otherwise", async () => {
    const boundary = memoryApi();
    const wrapper = mountWith(GmNpcMemoryTab, { props: { npcDbref: "12", api: boundary } });
    await flushPromises();
    await wrapper.get("input[name='tier']").setValue("core");
    await flushPromises();
    const filtered = boundary.calls.at(-1).path;
    expect(filtered).toContain("tier=core");
    expect(filtered).not.toContain("cursor");
    await wrapper.get(".gm-pager__more").trigger("click");
    await flushPromises();
    expect(boundary.calls.at(-1).path).toContain("cursor=cursor-1");
    expect(wrapper.text()).toContain("第 2 頁");
  });

  it("expands a memory's complete revision history and a snapshot's sections", async () => {
    const boundary = memoryApi();
    const wrapper = mountWith(GmNpcMemoryTab, { props: { npcDbref: "12", api: boundary } });
    await flushPromises();
    await wrapper.get("[data-block='memories'] button[aria-expanded]").trigger("click");
    await flushPromises();
    expect(boundary.calls.at(-1).path).toBe("/state/memories/31?owner=%2312");
    const revisions = wrapper.get("[data-section='revisions']");
    expect(revisions.text()).toContain("修訂");
    expect(revisions.text()).toContain("active");
    await wrapper.get("[data-block='snapshots'] button[aria-expanded]").trigger("click");
    await flushPromises();
    expect(boundary.calls.at(-1).path).toBe("/state/snapshots/t_snapshot_1?owner=%2312");
    // Both detail panes render an ``identity`` section; scope to the snapshot's.
    expect(
      wrapper.get("[data-block='snapshots'] [data-section='identity']").text(),
    ).toContain("t_capability");
  });

  it("posts the recall query and renders the authoritative selections", async () => {
    const boundary = memoryApi();
    const wrapper = mountWith(GmNpcMemoryTab, { props: { npcDbref: "12", api: boundary } });
    await flushPromises();
    await wrapper.get("textarea").setValue("合成記憶");
    // The filter bar is the component's first form; the recall form is its own.
    await wrapper.get(".gm-recall").trigger("submit");
    await flushPromises();
    const posted = boundary.calls.at(-1);
    expect(posted.method).toBe("post");
    expect(posted.path).toBe("/state/npc/12/recall");
    expect(posted.body).toEqual({
      query: "合成記憶",
      thread: null,
      include_superseded: false,
      include_inactive: false,
    });
    const result = wrapper.get("[data-testid='gm-recall-result']");
    expect(result.text()).toContain("記憶世代");
    expect(result.text()).toContain("核心");
    expect(result.text()).toContain("BM25 0.500");
    expect(result.text()).toContain("最終 0.750");
    expect(result.text()).toContain("沒有入選的記憶");
  });

  it("refuses an over-long query before it is sent", async () => {
    const boundary = memoryApi();
    const wrapper = mountWith(GmNpcMemoryTab, { props: { npcDbref: "12", api: boundary } });
    await flushPromises();
    const before = boundary.calls.length;
    await wrapper.get("textarea").setValue("x".repeat(2001));
    expect(wrapper.get(".gm-recall__warning").text()).toContain("超過 2000 字元");
    await wrapper.get(".gm-recall").trigger("submit");
    await flushPromises();
    expect(boundary.calls).toHaveLength(before);
  });

  it("shows the server's diagnostic code when recall is refused", async () => {
    const boundary = memoryApi({
      "/state/npc/12/recall": errorWith("query_too_long", "查詢文字超過 2000 字元上限。", 400),
    });
    const wrapper = mountWith(GmNpcMemoryTab, { props: { npcDbref: "12", api: boundary } });
    await flushPromises();
    await wrapper.get("textarea").setValue("合成");
    await wrapper.get(".gm-recall").trigger("submit");
    await flushPromises();
    expect(wrapper.get(".gm-error code").text()).toBe("query_too_long");
  });
});

describe("GmNpcDialogueTab", () => {
  it("groups epochs by player and expands one player's frames with call links", async () => {
    const boundary = fakeApi({
      "/state/dialogue": DIALOGUE_PAGE,
      "/state/dialogue/t_player_a": DIALOGUE_DETAIL,
    });
    const wrapper = mountWith(GmNpcDialogueTab, { props: { npcDbref: "12", api: boundary } });
    await flushPromises();
    expect(boundary.calls[0].path).toBe("/state/dialogue?owner=%2312&limit=50");
    expect(wrapper.get("table").text()).toContain("t_player_a");
    await wrapper.get(".gm-list__extra button").trigger("click");
    await flushPromises();
    expect(boundary.calls.at(-1).path).toBe("/state/dialogue/t_player_a?owner=%2312");
    expect(wrapper.get("[data-section='epochs']").text()).toContain("第 1 紀元");
    // The frame's recorded call id opens the retained S2 drawer, not a new tab.
    await wrapper.get("[data-section='epochs'] button").trigger("click");
    expect(wrapper.emitted("open-call")[0]).toEqual(["cd".repeat(16)]);
  });
});

describe("NPC tab integration", () => {
  it("switches between the entity summary, raw data and both narrative tabs", async () => {
    const boundary = fakeApi({
      "/state/npcs/12": NPC_DETAIL,
      "/state/object/12/raw": { raw: {} },
      "/state/memories": listPage([]),
      "/state/snapshots": listPage([]),
      "/state/dialogue": listPage([]),
    });
    const wrapper = mountWith(GmEntityView, { props: { kind: "npcs", id: "12", api: boundary } });
    await flushPromises();
    const tabs = wrapper.findAll("[role='tab']");
    await tabs[2].trigger("click");
    await flushPromises();
    expect(boundary.calls.map((call) => call.path)).toEqual([
      "/state/npcs/12",
      "/state/memories?owner=%2312&limit=50",
      "/state/snapshots?owner=%2312&limit=10",
    ]);
    expect(wrapper.text()).toContain("召回預覽");
    await tabs[3].trigger("click");
    await flushPromises();
    expect(boundary.calls.at(-1).path).toBe("/state/dialogue?owner=%2312&limit=50");
    expect(wrapper.text()).toContain("對話紀元");
  });
});
