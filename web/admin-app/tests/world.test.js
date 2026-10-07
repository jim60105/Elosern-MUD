// Authored world-data browser (gm-portal-s4-world-data §4): link routing,
// field-path links in the JSON tree, reference and referrer rendering, the
// list/detail/source pages and the CSRF-carrying prompt reload.
import { describe, expect, it } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import GmEntityLink from "../components/GmEntityLink.vue";
import GmJsonTree from "../components/GmJsonTree.vue";
import GmProvenanceNote from "../components/GmProvenanceNote.vue";
import GmReferenceList from "../components/GmReferenceList.vue";
import GmSourceText from "../components/GmSourceText.vue";
import { routes } from "../router.js";
import { createGmApi } from "../lib/api.js";
import { linkTarget, targetHref } from "../lib/runtime.js";
import {
  PROMPT_RELOAD_PATH,
  childPath,
  entryPath,
  groupHits,
  referenceLinks,
  registryListPath,
  sourcePath,
  sourceTarget,
  worldHref,
} from "../lib/world.js";
import WorldEntryView from "../views/WorldEntryView.vue";
import WorldHomeView from "../views/WorldHomeView.vue";
import WorldRegistryView from "../views/WorldRegistryView.vue";
import WorldSourceView from "../views/WorldSourceView.vue";
import {
  CRITTER_PAGE,
  MARKED_ENTRY,
  PROMPT_SOURCE,
  RELOAD_DEGRADED,
  RULE_SOURCE,
  WORLD_INVENTORY,
  WORLD_SEARCH,
  WORLD_SOURCES,
} from "../stories/world-fixtures.js";
import { errorWith, fakeApi } from "./runtime-helpers.js";

function worldRouter() {
  return createRouter({ history: createMemoryHistory("/gm/"), routes });
}

async function mountAt(component, path, { api, props = {} } = {}) {
  const router = worldRouter();
  await router.push(path);
  const wrapper = mount(component, { props, global: { plugins: [router], provide: { gmApi: api } } });
  await flushPromises();
  return { wrapper, router };
}

describe("world-data links and paths", () => {
  it("routes a registry descriptor to its entry page with an encoded href", () => {
    const target = linkTarget({ kind: "registry", registry: "t_critters", id: "t_marked" });
    expect(target).toEqual({ name: "world-entry", params: { registry: "t_critters", key: "t_marked" }, query: {} });
    expect(targetHref(target)).toBe("/gm/world/t_critters/t_marked");
    const odd = linkTarget({ kind: "registry", registry: "t_critters", id: "t a#b?c%" });
    expect(targetHref(odd)).toBe("/gm/world/t_critters/t%20a%23b%3Fc%25");
    expect(worldRouter().resolve(odd).params.key).toBe("t a#b?c%");
    expect(linkTarget({ kind: "registry", id: "t_marked" })).toBeNull();
    // Existing link kinds keep their targets.
    expect(targetHref(linkTarget({ kind: "rooms", id: "3" }))).toBe("/gm/runtime/rooms/3");
  });

  it("builds request paths, source targets and the shared field-path shape", () => {
    expect(registryListPath("t_critters", { q: "月光", limit: 25, cursor: "c1" })).toBe(
      "/registry/t_critters?q=%E6%9C%88%E5%85%89&limit=25&cursor=c1",
    );
    expect(entryPath("t_critters", "t_marked")).toBe("/registry/t_critters/t_marked");
    expect(sourcePath("rulebook/commerce/t_rules.yaml")).toBe("/sources/rulebook/commerce/t_rules.yaml");
    expect(worldHref(sourceTarget("rulebook/commerce/t_rules.yaml"))).toBe(
      "/gm/world/sources/rulebook/commerce/t_rules.yaml",
    );
    expect(worldRouter().resolve(sourceTarget("prompts/t_voice.yaml")).name).toBe("world-source");
    expect(childPath("", "stages")).toBe("stages");
    expect(childPath(childPath(childPath("", "stages"), 0), "objective")).toBe("stages[0].objective");
    expect(referenceLinks(MARKED_ENTRY.references)["markings[0].hollow_key"]).toMatchObject({ missing: true });
    expect(groupHits(WORLD_SEARCH.items).map((group) => [group.registry, group.keys.length])).toEqual([
      ["t_critters", 2],
      ["t_trinkets", 1],
    ]);
  });

  it("keeps the reserved source route ahead of registry routes", () => {
    const router = worldRouter();
    expect(router.resolve("/world/sources/prompts/t_voice.yaml").name).toBe("world-source");
    expect(router.resolve("/world/sources").name).toBe("world-sources");
    expect(routes.find((route) => route.name === "world-sources").redirect).toEqual({ name: "world-home" });
    expect(router.resolve("/world/t_critters").name).toBe("world-registry");
    expect(router.resolve("/world/t_critters/t_marked").name).toBe("world-entry");
  });
});

describe("GmEntityLink authored targets", () => {
  it("renders an authored link with the ◇ glyph and a world-data title", () => {
    const wrapper = mount(GmEntityLink, { props: { link: { kind: "registry", registry: "t_hollows", id: "t_hollow_east" } } });
    const anchor = wrapper.get("a");
    expect(anchor.attributes("href")).toBe("/gm/world/t_hollows/t_hollow_east");
    expect(anchor.text()).toContain("◇");
    expect(anchor.attributes("title")).toBe("世界資料：t_hollows ／ t_hollow_east");
  });

  it("renders a missing target as broken text, never a link", () => {
    const wrapper = mount(GmEntityLink, {
      props: { link: { kind: "registry", registry: "t_hollows", id: "t_gone", missing: true } },
    });
    expect(wrapper.find("a").exists()).toBe(false);
    expect(wrapper.get(".gm-entity-link--missing").text()).toContain("目標條目不存在");
  });
});

describe("GmJsonTree field-path links", () => {
  it("links exactly the declared leaves and keeps other values verbatim", () => {
    const wrapper = mount(GmJsonTree, {
      props: { value: MARKED_ENTRY.fields, links: referenceLinks(MARKED_ENTRY.references), openDepth: 4 },
    });
    const linked = wrapper.findAll(".gm-json-tree__row--linked");
    expect(linked.map((row) => row.attributes("data-path"))).toEqual([
      "home_key",
      "roams[0]",
      "roams[1]",
      "markings[0].hollow_key",
    ]);
    expect(linked[0].get("a").attributes("href")).toBe("/gm/world/t_hollows/t_hollow_west");
    expect(linked[3].find("a").exists()).toBe(false);
    expect(linked[3].text()).toContain("t_hollow_gone");
    // An undeclared string leaf is a plain scalar.
    expect(wrapper.text()).toContain('"銀色月光的紋路"');
  });

  it("renders unchanged without a link map", () => {
    const wrapper = mount(GmJsonTree, { props: { value: { home_key: "t_hollow_west" } } });
    expect(wrapper.find(".gm-json-tree__row--linked").exists()).toBe(false);
    expect(wrapper.text()).toContain('"t_hollow_west"');
  });
});

describe("GmReferenceList", () => {
  const outgoing = MARKED_ENTRY.references.map((item) => ({
    registry: item.registry,
    registryLabel: item.registry_label,
    key: item.key,
    label: item.label,
    fieldPath: item.field_path,
    missing: !item.exists,
  }));

  it("shows each target with its field path and marks dangling targets in text", () => {
    const wrapper = mount(GmReferenceList, { props: { items: outgoing, mode: "outgoing" } });
    const rows = wrapper.findAll(".gm-refs__row");
    expect(rows).toHaveLength(4);
    expect(rows[0].text()).toContain("合成窪地");
    expect(rows[0].text()).toContain("home_key");
    expect(rows[0].get("a").attributes("href")).toBe("/gm/world/t_hollows/t_hollow_west");
    expect(rows[3].classes()).toContain("is-missing");
    expect(rows[3].find("a").exists()).toBe(false);
    expect(rows[3].text()).toContain("目標不存在");
  });

  it("previews long incoming groups behind a disclosure", async () => {
    const items = MARKED_ENTRY.referrers[1].items.map((item) => ({ ...item, fieldPath: item.field_path }));
    const wrapper = mount(GmReferenceList, { props: { items, mode: "incoming", previewCount: 8 } });
    expect(wrapper.findAll(".gm-refs__row")).toHaveLength(8);
    const more = wrapper.get(".gm-refs__more");
    expect(more.text()).toBe("顯示其餘 3 筆");
    await more.trigger("click");
    expect(wrapper.findAll(".gm-refs__row")).toHaveLength(11);
    expect(more.attributes("aria-expanded")).toBe("true");
  });
});

describe("GmSourceText and GmProvenanceNote", () => {
  it("numbers every line, dims comments and highlights the selected line", () => {
    const wrapper = mount(GmSourceText, { props: { text: RULE_SOURCE.text, name: RULE_SOURCE.source_path, highlight: 2 } });
    const lines = wrapper.findAll(".gm-source__line");
    expect(lines).toHaveLength(5);
    expect(lines[0].classes()).toContain("is-comment");
    expect(lines[1].classes()).toContain("is-highlight");
    expect(lines[1].get("a").attributes("href")).toBe("#L2");
    expect(lines[1].get("a").attributes("aria-label")).toBe("第 2 行");
    expect(wrapper.get(".gm-source__count").text()).toBe("共 5 行");
  });

  it("treats a hash inside a block scalar as text, not a comment", () => {
    const text = "# 頂層註解\nprompts:\n  t_voice.system: |-\n    ### 合成標題\n    內文\n  # 區段註解\n";
    const wrapper = mount(GmSourceText, { props: { text, name: "prompts/t_voice.yaml" } });
    const comments = wrapper.findAll(".gm-source__line").map((line) => line.classes().includes("is-comment"));
    expect(comments).toEqual([true, false, false, false, false, true]);
  });

  it("states loaded, disk and reloadable provenance in Traditional Chinese", () => {
    const loaded = mount(GmProvenanceNote, { props: { path: "fixtures/t_critters.py" } });
    expect(loaded.text()).toContain("fixtures/t_critters.py");
    expect(loaded.text()).toContain("重新啟動伺服器");
    const disk = mount(GmProvenanceNote, { props: { path: "world/rules/rulebook/t_rules.yaml", variant: "disk" } });
    expect(disk.text()).toContain("不一定是伺服器目前載入的版本");
    const reloadable = mount(GmProvenanceNote, { props: { path: "prompts/t_voice.yaml", variant: "reloadable" } });
    expect(reloadable.text()).toContain("可在此重新載入");
    expect(reloadable.text()).toContain("可重新載入");
  });
});

describe("WorldHomeView", () => {
  it("groups loaded registries and lists the source files", async () => {
    const api = fakeApi({ "/registry/": WORLD_INVENTORY, "/sources/": WORLD_SOURCES });
    const { wrapper } = await mountAt(WorldHomeView, "/world", { api });
    const groups = wrapper.findAll(".gm-world-group");
    expect(groups.map((group) => group.get(".gm-world-group__label").text())).toEqual(["世界", "生物", "物品與經濟"]);
    const cards = groups[0].findAll(".gm-world-card");
    expect(cards.map((card) => card.attributes("href"))).toEqual(["/gm/world/t_hollows", "/gm/world/t_realms"]);
    expect(cards[1].get(".gm-world-card__number").classes()).toContain("is-zero");
    expect(wrapper.get(".gm-world-home__totals").text()).toContain("65");
    const sourceLinks = wrapper.findAll(".gm-world-sources__link");
    expect(sourceLinks.map((link) => link.attributes("href"))).toEqual([
      "/gm/world/sources/rulebook/t_rules.yaml",
      "/gm/world/sources/rulebook/commerce/t_rules.yaml",
      "/gm/world/sources/prompts/t_voice.yaml",
    ]);
  });

  it("runs the cross-registry search from ?q= and groups every hit", async () => {
    const api = fakeApi({ "/registry/": WORLD_INVENTORY, "/sources/": WORLD_SOURCES });
    api.get = ((original) => async (path) => (path.startsWith("/registry/?q=") ? WORLD_SEARCH : original(path)))(api.get);
    const { wrapper } = await mountAt(WorldHomeView, "/world?q=%E6%9C%88", { api });
    const hits = wrapper.findAll(".gm-world-hits__group");
    expect(hits).toHaveLength(2);
    expect(hits[0].text()).toContain("合成小獸");
    expect(hits[0].findAll("a.gm-entity-link").map((a) => a.attributes("href"))).toEqual([
      "/gm/world/t_critters/t_marked",
      "/gm/world/t_critters/t_moonlit",
    ]);
    expect(wrapper.text()).toContain("共 3 筆符合「月」");
  });

  it("shows an empty search and an inventory error with retry", async () => {
    const api = fakeApi({
      "/registry/": errorWith("database_unreadable", "資料庫目前無法讀取。", 503),
      "/sources/": WORLD_SOURCES,
    });
    const { wrapper } = await mountAt(WorldHomeView, "/world", { api });
    expect(wrapper.text()).toContain("無法載入登錄表索引");
    expect(wrapper.text()).toContain("database_unreadable");
  });
});

describe("WorldRegistryView", () => {
  it("lists keys with summary fields, provenance and forward paging", async () => {
    const api = fakeApi({ "/registry/t_critters": CRITTER_PAGE });
    const { wrapper } = await mountAt(WorldRegistryView, "/world/t_critters", {
      api,
      props: { registry: "t_critters", query: {} },
    });
    expect(wrapper.get(".gm-world-list__title").text()).toContain("合成小獸");
    expect(wrapper.text()).toContain("fixtures/critters");
    const headers = wrapper.findAll("th").map((th) => th.text());
    expect(headers).toEqual(["Key", "display_name_zh", "home_key"]);
    const firstRow = wrapper.findAll("tbody tr")[0];
    expect(firstRow.get("a").attributes("href")).toBe("/gm/world/t_critters/t_critter_00");
    expect(firstRow.text()).toContain("t_hollow_east");
    expect(wrapper.text()).toContain("載入下一頁");
    expect(api.calls[0].path).toBe("/registry/t_critters?limit=50");
  });

  it("passes the query to the server and reports an unknown registry", async () => {
    const api = fakeApi({ "/registry/t_absent": errorWith("registry_not_found", "找不到指定的登錄表。", 404) });
    const { wrapper } = await mountAt(WorldRegistryView, "/world/t_absent?q=x", {
      api,
      props: { registry: "t_absent", query: { q: "x" } },
    });
    expect(api.calls[0].path).toBe("/registry/t_absent?q=x&limit=50");
    expect(wrapper.text()).toContain("找不到這個登錄表");
  });
});

describe("WorldEntryView", () => {
  it("renders fields, outgoing references and inverse-grouped referrers", async () => {
    const api = fakeApi({ "/registry/t_critters/t_marked": MARKED_ENTRY });
    const { wrapper } = await mountAt(WorldEntryView, "/world/t_critters/t_marked", {
      api,
      props: { registry: "t_critters", entryKey: "t_marked" },
    });
    expect(wrapper.get(".gm-world-entry__key").text()).toBe("t_marked");
    expect(wrapper.get(".gm-world-entry__label").text()).toBe("斑紋獸");
    expect(wrapper.findAll(".gm-json-tree__row--linked")).toHaveLength(4);
    const references = wrapper.get("#references");
    expect(references.findAll(".gm-refs__row")).toHaveLength(4);
    expect(references.text()).toContain("有引用指向不存在的條目");
    const groups = wrapper.findAll(".gm-world-entry__group");
    expect(groups.map((group) => group.get("summary").text())).toEqual(["▸rivals1", "▸trophies11"]);
    expect(groups[0].attributes("open")).toBeDefined();
    expect(groups[1].attributes("open")).toBeUndefined();
    expect(wrapper.get(".gm-world-entry__anchors").text()).toContain("✕ 1");
    expect(wrapper.text()).toContain("fixtures/critters");
  });

  it("explains an unknown key with a way back to the list", async () => {
    const api = fakeApi({ "/registry/t_critters/t_absent": errorWith("entry_not_found", "此登錄表中沒有這個條目。", 404) });
    const { wrapper } = await mountAt(WorldEntryView, "/world/t_critters/t_absent", {
      api,
      props: { registry: "t_critters", entryKey: "t_absent" },
    });
    expect(wrapper.text()).toContain("找不到這個條目");
    expect(wrapper.get(".gm-error a").attributes("href")).toBe("/gm/world/t_critters");
  });
});

describe("WorldSourceView", () => {
  it("shows a rulebook as disk content without a reload action", async () => {
    const api = fakeApi({ "/sources/rulebook/t_rules.yaml": RULE_SOURCE });
    const { wrapper } = await mountAt(WorldSourceView, "/world/sources/rulebook/t_rules.yaml", { api });
    expect(wrapper.findAll(".gm-source__line")).toHaveLength(5);
    expect(wrapper.text()).toContain("磁碟內容");
    expect(wrapper.text()).not.toContain("重新載入提示詞庫");
  });

  it("reloads the prompt library through the CSRF-carrying API client and shows diagnostics", async () => {
    const requests = [];
    const fetchImpl = async (url, init) => {
      requests.push({ url, init });
      const body = url.endsWith(PROMPT_RELOAD_PATH) ? RELOAD_DEGRADED : PROMPT_SOURCE;
      return { status: 200, ok: true, text: async () => JSON.stringify({ ok: true, data: body }) };
    };
    const api = createGmApi({ fetchImpl, cookies: () => "csrftoken=t_token" });
    const { wrapper } = await mountAt(WorldSourceView, "/world/sources/prompts/t_voice.yaml", { api });
    expect(wrapper.text()).toContain("可在此重新載入");
    const button = wrapper.findAll("button").find((node) => node.text().includes("重新載入提示詞庫"));
    expect(button.classes()).not.toContain("ui-btn--danger");
    await button.trigger("click");
    await flushPromises();
    const post = requests.find((request) => request.init.method === "POST");
    expect(post.url).toBe("/gm/api/sources/prompts/reload");
    expect(post.init.headers["X-CSRFToken"]).toBe("t_token");
    expect(wrapper.text()).toContain("部分不可用");
    expect(wrapper.text()).toContain("t_voice.user");
    expect(wrapper.text()).toContain("這份載入結果已取代先前的提示詞庫");
    expect(wrapper.findAll("tbody tr")).toHaveLength(2);
  });

  it("keeps a failed reload visible with its code", async () => {
    const api = fakeApi({
      "/sources/prompts/t_voice.yaml": PROMPT_SOURCE,
      [PROMPT_RELOAD_PATH]: errorWith("csrf_failed", "安全驗證失敗。", 403),
    });
    const { wrapper } = await mountAt(WorldSourceView, "/world/sources/prompts/t_voice.yaml", { api });
    await wrapper.findAll("button").find((node) => node.text().includes("重新載入提示詞庫")).trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("重新載入失敗");
    expect(wrapper.text()).toContain("csrf_failed");
  });

  it("reports an unknown source", async () => {
    const api = fakeApi({ "/sources/rulebook/t_absent.yaml": errorWith("source_not_found", "找不到指定的原始檔。", 404) });
    const { wrapper } = await mountAt(WorldSourceView, "/world/sources/rulebook/t_absent.yaml", { api });
    expect(wrapper.text()).toContain("找不到這個原始檔");
  });
});
