import { describe, expect, it } from "vitest";
import { flushPromises } from "@vue/test-utils";
import RuntimeHomeView from "../views/RuntimeHomeView.vue";
import RuntimeListView from "../views/RuntimeListView.vue";
import RuntimeSearchView from "../views/RuntimeSearchView.vue";
import { errorWith, fakeApi, listPage, mountWith, stubRouter } from "./runtime-helpers.js";

const NPC_ITEM = {
  id: "12",
  kind: "npcs",
  dbref: 12,
  label: "合成守衛",
  fields: [
    { key: "職業", label: "職業", value: "公會櫃檯" },
    { key: "稱號", label: "稱號", value: "合成頭銜" },
    { key: "所在房間", label: "所在房間", value: "合成廣場" },
  ],
};

describe("RuntimeHomeView", () => {
  it("lists the whole runtime navigation tree with real hrefs", () => {
    const wrapper = mountWith(RuntimeHomeView);
    expect(wrapper.get(".gm-runtime-home__search").attributes("href")).toBe("/gm/runtime/search");
    const entries = wrapper.findAll(".gm-runtime-home__entry");
    expect(entries.map((node) => node.attributes("href"))).toEqual([
      "/gm/runtime/accounts",
      "/gm/runtime/characters",
      "/gm/runtime/npcs",
      "/gm/runtime/monsters",
      "/gm/runtime/rooms",
      "/gm/runtime/quests",
      "/gm/runtime/narrative",
      "/gm/runtime/art",
    ]);
    expect(entries.map((node) => node.get(".gm-runtime-home__label").text())).toEqual([
      "帳號",
      "玩家角色",
      "NPC",
      "魔物",
      "房間",
      "任務",
      "敘事紀錄",
      "美術資產",
    ]);
    expect(wrapper.get(".gm-runtime-home__note").text()).toContain("不會自動輪詢");
  });
});

describe("RuntimeListView", () => {
  it("loads one page of summaries with the kind's filter vocabulary", async () => {
    const boundary = fakeApi({ "/state/npcs": listPage([NPC_ITEM], null) });
    const wrapper = mountWith(RuntimeListView, { props: { kind: "npcs", query: {} }, api: boundary });
    await flushPromises();
    expect(boundary.calls[0].path).toBe("/state/npcs?limit=50");
    expect(wrapper.get("h2").text()).toBe("NPC");
    expect(wrapper.findAll("th").map((node) => node.text())).toEqual([
      "名稱",
      "職業",
      "稱號",
      "所在房間",
    ]);
    expect(wrapper.get(".gm-list__name a").attributes("href")).toBe("/gm/runtime/npcs/12");
    expect(wrapper.get(".gm-pager__more").text()).toBe("已到最後一頁");
    // The kind's own filter vocabulary, not a generic one.
    expect(wrapper.get("input[name='location']").exists()).toBe(true);
  });

  it("carries the URL filters into the request and restarts on a change", async () => {
    const boundary = fakeApi({ "/state/monsters": listPage([]) });
    const wrapper = mountWith(RuntimeListView, {
      props: { kind: "monsters", query: { species: "t_whale" } },
      api: boundary,
    });
    await flushPromises();
    expect(boundary.calls[0].path).toBe("/state/monsters?species=t_whale&limit=50");
    await wrapper.get("input[name='region']").setValue("t_bramble_wold");
    await flushPromises();
    expect(boundary.calls.at(-1).path).toBe(
      "/state/monsters?species=t_whale&region=t_bramble_wold&limit=50",
    );
  });

  it("asks for the required filter instead of issuing a request that must fail", async () => {
    const boundary = fakeApi({ "/state/quests": listPage([]) });
    const wrapper = mountWith(RuntimeListView, { props: { kind: "quests", query: {} }, api: boundary });
    await flushPromises();
    expect(boundary.calls).toHaveLength(0);
    expect(wrapper.get(".gm-list-view__hint").text()).toContain("擁有角色");
    await wrapper.get("input[name='owner']").setValue("#5");
    await flushPromises();
    expect(boundary.calls[0].path).toBe("/state/quests?owner=%235&limit=50");
  });

  it("surfaces a list failure with its diagnostic code", async () => {
    const boundary = fakeApi({
      "/state/rooms": errorWith("invalid_cursor", "分頁游標不正確或與目前的查詢條件不符。", 400),
    });
    const wrapper = mountWith(RuntimeListView, { props: { kind: "rooms", query: { cursor: "x" } }, api: boundary });
    await flushPromises();
    expect(wrapper.get(".gm-error code").text()).toBe("invalid_cursor");
  });
});

describe("RuntimeSearchView", () => {
  const RESULTS = {
    query: "t_source",
    results: [
      { kind: "object", id: "7", label: "t_source", dbref: 7, matched: "object_key", link: { kind: "object", id: "7", label: "t_source" } },
      { kind: "narrative", id: "event:t_source", label: "t_event", dbref: null, matched: "source_id", link: { kind: "narrative", id: "event:t_source", label: "t_event" } },
    ],
  };

  async function searchView(handlers, query = "t_source") {
    const router = stubRouter();
    await router.push({ name: "runtime-search", query: query ? { q: query } : {} });
    await router.isReady();
    const boundary = fakeApi(handlers);
    const wrapper = mountWith(RuntimeSearchView, { router, api: boundary });
    await flushPromises();
    return { wrapper, boundary, router };
  }

  it("runs the query carried in the URL and shows which rule matched", async () => {
    const { wrapper, boundary } = await searchView({ "/state/search": RESULTS });
    expect(boundary.calls[0].path).toBe("/state/search?q=t_source");
    const tiers = wrapper.findAll(".gm-search__tier").map((node) => node.text());
    expect(tiers).toEqual(["物件鍵", "來源識別"]);
    const links = wrapper.findAll(".gm-search__link");
    expect(links.map((node) => node.attributes("href"))).toEqual([
      "/gm/runtime/object/7/raw",
      "/gm/runtime/narrative/event%3At_source",
    ]);
    expect(wrapper.text()).toContain("精確 #dbref → 物件鍵 → 任務編號 → 來源識別");
  });

  it("submits a new query into the URL and reports an empty result set honestly", async () => {
    const { wrapper, boundary, router } = await searchView({ "/state/search": { query: "x", results: [] } });
    await wrapper.get("input[name='q']").setValue("#12");
    await wrapper.get("form").trigger("submit");
    await flushPromises();
    expect(router.currentRoute.value.query.q).toBe("#12");
    expect(boundary.calls.at(-1).path).toBe("/state/search?q=%2312");
    expect(wrapper.get(".gm-search__empty").text()).toContain("沒有符合");
  });

  it("does not run an empty query and shows the server's code when refused", async () => {
    const empty = await searchView({ "/state/search": { query: "", results: [] } }, "");
    expect(empty.boundary.calls).toHaveLength(0);
    const refused = await searchView({ "/state/search": errorWith("invalid_query", "請輸入查詢文字。") });
    expect(refused.wrapper.get(".gm-error code").text()).toBe("invalid_query");
    expect(refused.wrapper.get(".gm-error").text()).toContain("請輸入查詢文字");
  });
});
