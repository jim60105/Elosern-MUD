import { createRouter, createWebHistory } from "vue-router";
import OverviewView from "./views/OverviewView.vue";
import ForbiddenView from "./views/ForbiddenView.vue";
import NotFoundView from "./views/NotFoundView.vue";
import RuntimeEntityView from "./views/RuntimeEntityView.vue";
import RuntimeHomeView from "./views/RuntimeHomeView.vue";
import RuntimeListView from "./views/RuntimeListView.vue";
import RuntimeSearchView from "./views/RuntimeSearchView.vue";
import WorldEntryView from "./views/WorldEntryView.vue";
import WorldHomeView from "./views/WorldHomeView.vue";
import WorldRegistryView from "./views/WorldRegistryView.vue";
import WorldSourceView from "./views/WorldSourceView.vue";
import SavesView from "./views/SavesView.vue";
import { GM_BASE } from "./lib/api.js";

// History routing under /gm/. Delivered sections own routes: the overview, the
// runtime state section (its nav tree, search, per-kind lists, entity pages and
// the universal raw view), the permission-denied view, and a not-found view for
// unknown client paths. The world-data section (S4) owns its home, the source
// viewer, registry lists and entry pages. The saves section (S5) owns one page.
// The undelivered section (S6) has no route.
//
// Order matters: the reserved runtime paths (search, the object raw route) are
// registered before the parameterized kind routes, and the reserved world
// source path before the registry routes, so they can never be swallowed — the
// same precedence the server's URL map keeps (no registry is named
// ``sources``; a contract test pins that).
export const routes = [
  { path: "/", name: "overview", component: OverviewView, meta: { title: "總覽", section: "overview", wide: true } },
  {
    path: "/runtime",
    name: "runtime-home",
    component: RuntimeHomeView,
    meta: { title: "執行期狀態", section: "runtime", wide: true },
  },
  {
    path: "/runtime/search",
    name: "runtime-search",
    component: RuntimeSearchView,
    meta: { title: "執行期搜尋", section: "runtime" },
  },
  {
    path: "/runtime/object/:dbref/raw",
    name: "runtime-object-raw",
    component: RuntimeEntityView,
    meta: { title: "物件原始資料", section: "runtime" },
  },
  {
    path: "/runtime/:kind",
    name: "runtime-list",
    component: RuntimeListView,
    props: (route) => ({ kind: String(route.params.kind), query: { ...route.query } }),
    meta: { title: "執行期清單", section: "runtime" },
  },
  {
    path: "/runtime/:kind/:id",
    name: "runtime-entity",
    component: RuntimeEntityView,
    meta: { title: "執行期實體", section: "runtime" },
  },
  {
    path: "/world",
    name: "world-home",
    component: WorldHomeView,
    meta: { title: "世界資料", section: "world-data", wide: true },
  },
  {
    path: "/world/sources/:name+",
    name: "world-source",
    component: WorldSourceView,
    meta: { title: "原始檔", section: "world-data", wide: true },
  },
  {
    path: "/world/sources",
    name: "world-sources",
    redirect: { name: "world-home" },
  },
  {
    path: "/world/:registry",
    name: "world-registry",
    component: WorldRegistryView,
    props: (route) => ({ registry: String(route.params.registry), query: { ...route.query } }),
    meta: { title: "登錄表", section: "world-data" },
  },
  {
    path: "/world/:registry/:key",
    name: "world-entry",
    component: WorldEntryView,
    props: (route) => ({ registry: String(route.params.registry), entryKey: String(route.params.key) }),
    meta: { title: "登錄表條目", section: "world-data", wide: true },
  },
  {
    path: "/saves",
    name: "saves",
    component: SavesView,
    meta: { title: "存檔", section: "actions", wide: true },
  },
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
