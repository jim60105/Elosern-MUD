import { createRouter, createWebHistory } from "vue-router";
import OverviewView from "./views/OverviewView.vue";
import ForbiddenView from "./views/ForbiddenView.vue";
import NotFoundView from "./views/NotFoundView.vue";
import { GM_BASE } from "./lib/api.js";

// History routing under /gm/ (gm-portal-s1-foundation). Only delivered views
// have routes: the overview, the permission-denied view, and a not-found view
// for unknown client paths. Undelivered sections have no route.
export const routes = [
  { path: "/", name: "overview", component: OverviewView, meta: { title: "總覽", section: "overview", wide: true } },
  { path: "/forbidden", name: "forbidden", component: ForbiddenView, meta: { title: "權限不足" } },
  { path: "/:pathMatch(.*)*", name: "not-found", component: NotFoundView, meta: { title: "找不到頁面" } },
];

// The authorization guard: once an API call answers 403 `forbidden`, every
// navigation lands on the permission-denied view exactly once. The view
// itself never fetches, so it cannot re-trigger the guard (no loop). A full
// reload re-checks access on the server.
export function installAuthorizationGuard(router, authState) {
  router.beforeEach((to) => {
    if (authState.forbidden && to.name !== "forbidden") {
      return { name: "forbidden", replace: true };
    }
    return true;
  });
}

export function createGmRouter({ history = createWebHistory(GM_BASE), authState } = {}) {
  const router = createRouter({ history, routes });
  if (authState) installAuthorizationGuard(router, authState);
  return router;
}
