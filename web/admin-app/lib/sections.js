// GM navigation model (design §5 layout): one section per sub-project. The
// runtime state section (gm-portal-s3-runtime-state) is delivered and carries
// its navigation tree as children — global search first, then the curated
// kinds. The world-data section (gm-portal-s4-world-data) is one entry: its
// home page carries the grouped registry index, so ~40 registries never flood
// the tree. The S5 slot (key ``actions``) is delivered as 「存檔」, the world
// save page (gm-portal-s5-saves): the sub-project's scope narrowed to save
// management, so the entry is named for what it holds. The S2b operations
// dashboard IS the 總覽 home, so no separate operations entry exists, and S6
// (gm-portal-s6-console) landed as contextual console controls on entity, raw,
// memory and dashboard surfaces — deliberately no standalone entry. With S2–S6
// delivered, every navigation section is live; a section with a null route
// would still render inert and tagged 「尚未開放」, which is the behavior the
// nav tests pin for any future undelivered entry.
import { RUNTIME_KINDS, RUNTIME_ROUTE } from "./runtime.js";
import { SAVES_ROUTE } from "./saves.js";
import { WORLD_ROUTE } from "./world.js";

export const GM_SECTIONS = Object.freeze([
  Object.freeze({ key: "overview", label: "總覽", route: "overview", href: "/gm/" }),
  Object.freeze({
    key: "runtime",
    label: "執行期狀態",
    route: RUNTIME_ROUTE.home,
    href: "/gm/runtime",
    children: Object.freeze([
      Object.freeze({
        key: "runtime-search",
        label: "全域搜尋",
        route: RUNTIME_ROUTE.search,
        href: "/gm/runtime/search",
      }),
      ...RUNTIME_KINDS.map((kind) =>
        Object.freeze({
          key: `runtime-${kind.key}`,
          label: kind.label,
          route: RUNTIME_ROUTE.list,
          params: Object.freeze({ kind: kind.key }),
          href: `/gm/runtime/${kind.key}`,
        }),
      ),
    ]),
  }),
  Object.freeze({ key: "world-data", label: "世界資料", route: WORLD_ROUTE.home, href: "/gm/world" }),
  Object.freeze({ key: "actions", label: "存檔", route: SAVES_ROUTE.home, href: "/gm/saves" }),
]);

export const DISABLED_SECTION_TAG = "尚未開放";
