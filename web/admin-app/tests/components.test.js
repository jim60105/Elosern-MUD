import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import GmPanel from "../components/GmPanel.vue";
import GmTable from "../components/GmTable.vue";
import GmEmpty from "../components/GmEmpty.vue";
import GmError from "../components/GmError.vue";
import GmStatusBadge from "../components/GmStatusBadge.vue";
import GmMeter from "../components/GmMeter.vue";
import GmServiceCard from "../components/GmServiceCard.vue";
import GmRefreshBar from "../components/GmRefreshBar.vue";
import GmCodeBlock from "../components/GmCodeBlock.vue";

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


describe("GmMeter", () => {
  it("is decorative with a hidden text label and patterned segments", () => {
    const wrapper = mount(GmMeter, {
      props: {
        label: "成功 3，降級 1",
        segments: [
          { key: "ok", value: 3, tone: "ok", pattern: "solid" },
          { key: "degraded", value: 1, tone: "warn", pattern: "hatch" },
          { key: "rejected", value: 0, tone: "crit", pattern: "cross" },
        ],
      },
    });
    expect(wrapper.get(".gm-meter__track").attributes("aria-hidden")).toBe("true");
    expect(wrapper.get(".gm-visually-hidden").text()).toBe("成功 3，降級 1");
    const fills = wrapper.findAll(".gm-meter__fill");
    expect(fills.map((fill) => fill.attributes("style"))).toEqual(["width: 75%;", "width: 25%;"]);
    expect(fills[1].classes()).toContain("gm-meter__fill--hatch");
  });

  it("clamps a single value and marks zero with a tick", () => {
    const over = mount(GmMeter, { props: { label: "x", value: 900, max: 500 } });
    expect(over.get(".gm-meter__fill").attributes("style")).toBe("width: 100%;");
    const zero = mount(GmMeter, { props: { label: "x", value: 0, max: 500 } });
    expect(zero.get(".gm-meter__track").classes()).toContain("gm-meter__track--empty");
  });
});

describe("GmServiceCard", () => {
  it("states status in text and rule style, and a slot error as critical", () => {
    const warn = mount(GmServiceCard, { props: { name: "翻譯", status: "warn", statusLabel: "假後端" } });
    expect(warn.classes()).toContain("gm-service-card--warn");
    expect(warn.get(".status-marker").text()).toBe("假後端");
    const failed = mount(GmServiceCard, {
      props: { name: "SD 繪圖", status: "ok", statusLabel: "正常", error: { code: "sd_unavailable", message: "無法取得" } },
    });
    expect(failed.attributes("data-status")).toBe("crit");
    expect(failed.get(".status-marker").text()).toBe("無法取得狀態");
    expect(failed.get("code").text()).toBe("sd_unavailable");
  });
});

describe("GmRefreshBar", () => {
  it("describes each freshness state and blocks refresh while busy", async () => {
    const wrapper = mount(GmRefreshBar, { props: { state: "live", lastUpdatedAt: 100, now: 108 } });
    expect(wrapper.text()).toContain("8 秒前");
    expect(wrapper.text()).toContain("每 5 秒自動更新");
    await wrapper.get("button").trigger("click");
    expect(wrapper.emitted("refresh")).toHaveLength(1);
    await wrapper.setProps({ state: "refreshing" });
    await wrapper.get("button").trigger("click");
    expect(wrapper.emitted("refresh")).toHaveLength(1);
    await wrapper.setProps({ state: "stale", errorMessage: "斷線" });
    expect(wrapper.get(".status-marker").text()).toBe("資料過期");
    expect(wrapper.text()).toContain("更新失敗：斷線");
    expect(wrapper.get("[role='status']").text()).toBe("資料已過期");
    await wrapper.setProps({ state: "live" });
    expect(wrapper.get("[role='status']").text()).toBe("已恢復即時更新");
  });
});

describe("GmCodeBlock", () => {
  it("renders JSON verbatim, collapses long content, and never injects HTML", async () => {
    const text = Array.from({ length: 30 }, (_, index) => `<b>line ${index}</b>`).join("\n");
    const wrapper = mount(GmCodeBlock, { props: { text, maxLines: 5 } });
    expect(wrapper.find("pre b").exists()).toBe(false);
    expect(wrapper.classes()).toContain("is-collapsed");
    const toggle = wrapper.findAll("button").find((button) => button.text().startsWith("顯示全部"));
    await toggle.trigger("click");
    expect(wrapper.classes()).not.toContain("is-collapsed");
    const json = mount(GmCodeBlock, { props: { text: { a: [1] } } });
    expect(json.get("pre").text()).toBe('{\n  "a": [\n    1\n  ]\n}');
  });
});
