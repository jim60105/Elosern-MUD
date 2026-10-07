import { describe, expect, it } from "vitest";
import { reactive } from "vue";
import { createMemoryHistory } from "vue-router";
import { createGmRouter, routes } from "../router.js";
import { GM_SECTIONS } from "../lib/sections.js";

function makeRouter(authState = reactive({ forbidden: false })) {
  const history = createMemoryHistory("/gm/");
  return { router: createGmRouter({ history, authState }), authState, history };
}

describe("GM router", () => {
  it("routes the delivered views; undelivered sections own no route", () => {
    const names = routes.map((route) => route.name);
    expect(names).toEqual([
      "overview",
      "runtime-home",
      "runtime-search",
      "runtime-object-raw",
      "runtime-list",
      "runtime-entity",
      "world-home",
      "world-source",
      "world-sources",
      "world-registry",
      "world-entry",
      "saves",
      "forbidden",
      "not-found",
    ]);
    const delivered = GM_SECTIONS.filter((section) => section.route).map((section) => section.key);
    expect(delivered).toEqual(["overview", "runtime", "world-data", "actions"]);
    // S6 is contextual, without a standalone navigation placeholder.
    expect(GM_SECTIONS.find((section) => section.key === "intervention")).toBeUndefined();
    for (const section of GM_SECTIONS.filter((s) => !s.route)) {
      expect(names).not.toContain(section.key);
      expect(section.children).toBeUndefined();
    }
  });

  it("resolves the runtime navigation tree entries to their registered routes", () => {
    const runtime = GM_SECTIONS.find((section) => section.key === "runtime");
    expect(runtime.children.map((child) => child.label)).toEqual([
      "全域搜尋",
      "帳號",
      "玩家角色",
      "NPC",
      "魔物",
      "房間",
      "任務",
      "敘事紀錄",
      "美術資產",
    ]);
    for (const child of runtime.children) {
      const href = child.route === "runtime-list" ? { name: child.route, params: child.params } : { name: child.route };
      expect(child.route).toBeTruthy();
      expect(child.href.startsWith("/gm/runtime")).toBe(true);
      expect(routes.some((route) => route.name === href.name)).toBe(true);
    }
  });

  it("enters routes directly and through history under the /gm/ base", async () => {
    const { router } = makeRouter();
    await router.push("/");
    expect(router.currentRoute.value.name).toBe("overview");
    expect(router.resolve("/").href).toBe("/gm/");
    await router.push("/runtime");
    expect(router.currentRoute.value.name).toBe("runtime-home");
    await router.push("/runtime/npcs");
    expect(router.currentRoute.value.name).toBe("runtime-list");
    expect(router.currentRoute.value.params.kind).toBe("npcs");
    await router.push("/runtime");
    router.back();
    await new Promise((resolve) => setTimeout(resolve, 0));
    await router.isReady();
    expect(router.currentRoute.value.name).toBe("runtime-list");
  });

  it("keeps the reserved runtime paths ahead of the kind routes", async () => {
    const { router } = makeRouter();
    await router.push("/runtime/search?q=12");
    expect(router.currentRoute.value.name).toBe("runtime-search");
    expect(router.currentRoute.value.query.q).toBe("12");
    await router.push("/runtime/object/12/raw");
    expect(router.currentRoute.value.name).toBe("runtime-object-raw");
    expect(router.currentRoute.value.params.dbref).toBe("12");
    await router.push("/runtime/npcs/12?owner=%233");
    expect(router.currentRoute.value.name).toBe("runtime-entity");
    expect(router.currentRoute.value.params).toMatchObject({ kind: "npcs", id: "12" });
    expect(router.currentRoute.value.query.owner).toBe("#3");
  });

  it("still lands an unknown client path on the not-found view", async () => {
    const { router } = makeRouter();
    await router.push("/no/such/page");
    expect(router.currentRoute.value.name).toBe("not-found");
  });

  it("lands an authorization failure on the denied view once, without a loop", async () => {
    const { router, authState } = makeRouter();
    await router.push("/");
    const visited = [];
    let guardRuns = 0;
    router.beforeEach(() => {
      guardRuns += 1;
    });
    router.afterEach((to, _from, failure) => {
      if (!failure) visited.push(to.name);
    });
    authState.forbidden = true;
    await router.push("/some/where");
    expect(router.currentRoute.value.name).toBe("forbidden");
    await router.push("/forbidden");
    await router.push("/anything");
    expect(router.currentRoute.value.name).toBe("forbidden");
    // Exactly one transition into the denied view; later attempts stay put.
    expect(visited).toEqual(["forbidden"]);
    // Three attempts, one redirect: the guard ran a bounded number of times.
    expect(guardRuns).toBeLessThanOrEqual(4);
  });

  it("lets a directly entered denied route render without redirecting", async () => {
    const { router } = makeRouter();
    await router.push("/forbidden");
    expect(router.currentRoute.value.name).toBe("forbidden");
    expect(router.currentRoute.value.fullPath).toBe("/forbidden");
  });

  it("resolves the saves page directly through history routing", async () => {
    const { router } = makeRouter();
    await router.push("/saves");
    expect(router.currentRoute.value.name).toBe("saves");
    expect(router.currentRoute.value.meta.section).toBe("actions");
  });
});
