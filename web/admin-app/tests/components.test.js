import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import GmPanel from "../components/GmPanel.vue";
import GmTable from "../components/GmTable.vue";
import GmEmpty from "../components/GmEmpty.vue";
import GmError from "../components/GmError.vue";
import GmStatusBadge from "../components/GmStatusBadge.vue";

describe("GmStatusBadge", () => {
  it.each([
    ["ok", "status-marker--ok"],
    ["warn", "status-marker--warn"],
    ["crit", "status-marker--crit"],
  ])("wraps .status-marker for %s", (status, modifier) => {
    const badge = mount(GmStatusBadge, { props: { status, label: "正常" } });
    expect(badge.classes()).toEqual(expect.arrayContaining(["status-marker", modifier]));
    expect(badge.text()).toBe("正常");
  });

  it("renders a neutral marker without a status color modifier", () => {
    const badge = mount(GmStatusBadge, { props: { label: "未知" } });
    expect(badge.classes()).toContain("status-marker");
    expect(badge.classes().some((name) => name.startsWith("status-marker--"))).toBe(false);
  });
});

describe("GmTable", () => {
  const columns = [
    { key: "label", label: "項目" },
    { key: "key", label: "識別碼", mono: true },
  ];

  it("renders identifiers verbatim in mono cells", () => {
    const rows = [{ key: "quest:Ash_Wolf-01", label: "任務" }];
    const table = mount(GmTable, { props: { columns, rows, rowKey: "key", caption: "清單" } });
    const cells = table.findAll("td");
    expect(cells[1].text()).toBe("quest:Ash_Wolf-01");
    expect(cells[1].classes()).toContain("gm-table__mono");
    expect(cells[0].classes()).not.toContain("gm-table__mono");
    expect(table.get("caption").text()).toBe("清單");
    expect(table.findAll("th").map((th) => th.attributes("scope"))).toEqual(["col", "col"]);
  });

  it("yields to the empty state when there are no rows", () => {
    const table = mount(GmTable, {
      props: { columns, rows: [], caption: "清單", emptyTitle: "沒有紀錄" },
    });
    expect(table.find("table").exists()).toBe(false);
    expect(table.findComponent(GmEmpty).text()).toContain("沒有紀錄");
  });

  it("lets a cell slot supply rich content", () => {
    const table = mount(GmTable, {
      props: { columns, rows: [{ key: "k", label: "x" }], caption: "清單" },
      slots: { "cell-label": "<strong>自訂</strong>" },
    });
    expect(table.get("td strong").text()).toBe("自訂");
  });
});

describe("GmPanel, GmEmpty, GmError", () => {
  it("labels the panel region by its title", () => {
    const panel = mount(GmPanel, { props: { title: "系統健康" }, slots: { default: "內容" } });
    const id = panel.get("h2").attributes("id");
    expect(panel.get("section").attributes("aria-labelledby")).toBe(id);
  });

  it("shows the empty title and message", () => {
    const empty = mount(GmEmpty, { props: { message: "沒有符合的項目。" } });
    expect(empty.text()).toContain("目前沒有資料");
    expect(empty.text()).toContain("沒有符合的項目。");
  });

  it("announces errors and shows the code verbatim with neutral actions", () => {
    const error = mount(GmError, {
      props: { title: "載入失敗", message: "伺服器回應的格式不正確。", code: "malformed_response" },
      slots: { actions: "<button class='ui-btn'>重試</button>" },
    });
    expect(error.attributes("role")).toBe("alert");
    expect(error.get("code").text()).toBe("malformed_response");
    expect(error.find(".ui-btn--danger").exists()).toBe(false);
  });
});
