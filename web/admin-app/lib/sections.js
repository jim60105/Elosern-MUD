// GM navigation model (design §5 layout): one section per sub-project. Only
// the overview is delivered in S1; every other section is disabled with
// 「尚未開放」 and owns no route or placeholder page until its change lands.
export const GM_SECTIONS = Object.freeze([
  Object.freeze({ key: "overview", label: "總覽", route: "overview", href: "/gm/" }),
  Object.freeze({ key: "operations", label: "維運", route: null }),
  Object.freeze({ key: "runtime", label: "執行期狀態", route: null }),
  Object.freeze({ key: "world-data", label: "世界資料", route: null }),
  Object.freeze({ key: "actions", label: "操作", route: null }),
  Object.freeze({ key: "intervention", label: "GM 介入", route: null }),
]);

export const DISABLED_SECTION_TAG = "尚未開放";
