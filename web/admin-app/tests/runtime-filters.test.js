import { describe, expect, it } from "vitest";
import GmFilterBar from "../components/GmFilterBar.vue";
import GmPager from "../components/GmPager.vue";
import { mountWith } from "./runtime-helpers.js";

const FIELDS = [
  { key: "owner", label: "擁有角色", type: "text", mono: true, required: true },
  { key: "generated", label: "只看生成任務", type: "checkbox" },
  {
    key: "subtype",
    label: "子類型",
    type: "select",
    default: "event",
    options: [
      { value: "event", label: "事件" },
      { value: "thread", label: "故事線" },
    ],
  },
];

describe("GmFilterBar", () => {
  it("renders each filter kind with its label and requirement marker", () => {
    const wrapper = mountWith(GmFilterBar, { props: { fields: FIELDS, modelValue: {} } });
    expect(wrapper.findAll(".gm-filter-bar__label").map((n) => n.text().replace(/\s+/g, ""))).toEqual([
      "擁有角色＊",
      "只看生成任務",
      "子類型",
    ]);
    expect(wrapper.get("input[name='owner']").classes()).toContain("gm-mono");
    expect(wrapper.get("input[name='generated']").attributes("type")).toBe("checkbox");
    expect(wrapper.get("select[name='subtype']").findAll("option").map((o) => o.text())).toEqual([
      "事件",
      "故事線",
    ]);
    expect(wrapper.get("select[name='subtype']").element.value).toBe("event");
    expect(wrapper.text()).toContain("未套用條件");
  });

  it("commits a changed filter and drops a cleared one", async () => {
    const wrapper = mountWith(GmFilterBar, {
      props: { fields: FIELDS, modelValue: { owner: "#5" } },
    });
    await wrapper.get("input[name='owner']").setValue("#9");
    expect(wrapper.emitted("update:modelValue").at(-1)[0]).toEqual({ owner: "#9" });
    expect(wrapper.emitted("change")).toHaveLength(1);
    await wrapper.get("input[name='owner']").setValue("");
    expect(wrapper.emitted("update:modelValue").at(-1)[0]).toEqual({});
    await wrapper.get("input[name='generated']").setValue(true);
    expect(wrapper.emitted("update:modelValue").at(-1)[0]).toEqual({ owner: "#5", generated: true });
  });

  it("reports the applied count and resets only when something is applied", async () => {
    const applied = mountWith(GmFilterBar, {
      props: { fields: FIELDS, modelValue: { owner: "#5", generated: true } },
    });
    expect(applied.text()).toContain("已套用 2 項");
    await applied.get(".gm-filter-bar__reset").trigger("click");
    expect(applied.emitted("change").at(-1)[0]).toEqual({});
    const empty = mountWith(GmFilterBar, { props: { fields: FIELDS, modelValue: {} } });
    expect(empty.get(".gm-filter-bar__reset").attributes("aria-disabled")).toBe("true");
    await empty.get(".gm-filter-bar__reset").trigger("click");
    expect(empty.emitted("change")).toBeUndefined();
  });
});

describe("GmPager", () => {
  it("offers the next page only while a cursor exists", async () => {
    const more = mountWith(GmPager, { props: { nextCursor: "abc", limit: 50, shown: 50, page: 1 } });
    expect(more.text()).toContain("第 1 頁");
    expect(more.text()).toContain("本頁 50 筆");
    expect(more.get(".gm-pager__more").text()).toBe("載入下一頁");
    await more.get(".gm-pager__more").trigger("click");
    expect(more.emitted("more")).toHaveLength(1);
    const done = mountWith(GmPager, { props: { nextCursor: null, limit: 50, shown: 12, page: 2 } });
    expect(done.get(".gm-pager__more").text()).toBe("已到最後一頁");
    expect(done.get(".gm-pager__more").attributes("aria-disabled")).toBe("true");
    await done.get(".gm-pager__more").trigger("click");
    expect(done.emitted("more")).toBeUndefined();
  });

  it("restarts at the first page and changes the page size", async () => {
    const wrapper = mountWith(GmPager, { props: { nextCursor: "x", limit: 50, shown: 50, page: 3 } });
    await wrapper.get(".gm-pager__select").setValue("200");
    expect(wrapper.emitted("limit")[0]).toEqual([200]);
    await wrapper.get(".gm-pager__select").setValue("50");
    expect(wrapper.emitted("limit")).toHaveLength(1);
    // The first page is already the start: nothing to reset.
    // ``:aria-disabled="null"`` removes the attribute entirely.
    expect(wrapper.findAll("button")[0].attributes("aria-disabled")).toBeUndefined();
    await wrapper.findAll("button")[0].trigger("click");
    expect(wrapper.emitted("first")).toHaveLength(1);
    const first = mountWith(GmPager, { props: { nextCursor: null, limit: 50, shown: 3, page: 1 } });
    await first.findAll("button")[0].trigger("click");
    expect(first.emitted("first")).toBeUndefined();
  });
});
