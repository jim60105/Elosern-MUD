// GM navigation model (design §5 layout): one section per sub-project. The
// runtime state section (gm-portal-s3-runtime-state) is delivered and carries
// its navigation tree as children — global search first, then the curated
// kinds. Every other section is still disabled with 「尚未開放」 and owns no
// route or placeholder page until its own change lands.
import { RUNTIME_KINDS, RUNTIME_ROUTE } from "./runtime.js";

export const GM_SECTIONS = Object.freeze([
  Object.freeze({ key: "overview", label: "總覽", route: "overview", href: "/gm/" }),
  Object.freeze({ key: "operations", label: "維運", route: null }),
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
  Object.freeze({ key: "world-data", label: "世界資料", route: null }),
  Object.freeze({ key: "actions", label: "操作", route: null }),
  Object.freeze({ key: "intervention", label: "GM 介入", route: null }),
]);

export const DISABLED_SECTION_TAG = "尚未開放";
