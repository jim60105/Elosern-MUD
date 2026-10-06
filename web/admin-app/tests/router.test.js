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
  it("routes only delivered views; undelivered sections own no route", () => {
    const names = routes.map((route) => route.name);
    expect(names).toEqual(["overview", "forbidden", "not-found"]);
    for (const section of GM_SECTIONS.filter((s) => !s.route)) {
      expect(names).not.toContain(section.key);
    }
  });

  it("enters routes directly and through history under the /gm/ base", async () => {
    const { router } = makeRouter();
    await router.push("/");
    expect(router.currentRoute.value.name).toBe("overview");
    expect(router.resolve("/").href).toBe("/gm/");
    await router.push("/runtime");
    expect(router.currentRoute.value.name).toBe("not-found");
    router.back();
    await new Promise((resolve) => setTimeout(resolve, 0));
    await router.isReady();
    expect(router.currentRoute.value.name).toBe("overview");
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
});
