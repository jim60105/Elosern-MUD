import { describe, expect, it } from "vitest";
import GmSectionView from "../components/GmSectionView.vue";
import GmTable from "../components/GmTable.vue";
import { mountWith } from "./runtime-helpers.js";

function section(payload = {}) {
  return mountWith(GmSectionView, { props: { section: payload } });
}

describe("GmSectionView", () => {
  it("renders a ledger with mono values, tones and links", () => {
    const wrapper = section({
      key: "identity",
      title: "身分",
      type: "ledger",
      note: "備註",
      rows: [
        { key: "名稱", label: "名稱", value: "合成守衛" },
        { key: "識別碼", label: "識別碼", value: "#12", mono: true, tone: "gold" },
        { key: "房間", label: "房間", value: "#3", mono: true, link: { kind: "rooms", id: "3", label: "廣場" } },
        { key: "空值", label: "空值", value: null },
      ],
    });
    expect(wrapper.get("h3").text()).toContain("身分");
    const rows = wrapper.findAll(".gm-ledger__row");
    expect(rows.map((row) => row.get("dt").text())).toEqual(["名稱", "識別碼", "房間", "空值"]);
    expect(rows[1].get(".gm-value").classes()).toEqual(
      expect.arrayContaining(["gm-mono", "is-gold"]),
    );
    expect(rows[2].get("a").attributes("href")).toBe("/gm/runtime/rooms/3");
    expect(rows[3].get("dd").text()).toBe("—");
    expect(wrapper.get(".gm-section__note").text()).toBe("備註");
  });

  it("renders a table through the shared ledger table, cell links included", () => {
    const wrapper = section({
      key: "services",
      title: "服務與職業",
      type: "table",
      columns: [
        { key: "component", label: "服務元件" },
        { key: "slot", label: "插槽", mono: true },
      ],
      rows: [
        {
          key: "GuildStaff",
          cells: {
            component: { value: "公會櫃檯" },
            slot: { value: "GuildStaff", mono: true },
          },
        },
        {
          key: "npc",
          cells: { component: { value: "#12", link: { kind: "npcs", id: "12", label: "守衛" } }, slot: { value: "—" } },
        },
      ],
      empty_note: "此 NPC 目前沒有服務元件。",
    });
    expect(wrapper.findComponent(GmTable).exists()).toBe(true);
    expect(wrapper.findAll("th").map((n) => n.text())).toEqual(["服務元件", "插槽"]);
    expect(wrapper.get("a").attributes("href")).toBe("/gm/runtime/npcs/12");
    const empty = section({
      key: "services",
      title: "服務與職業",
      type: "table",
      columns: [{ key: "slot", label: "插槽" }],
      rows: [],
      empty_note: "此 NPC 目前沒有服務元件。",
    });
    expect(empty.findComponent(GmTable).text()).toContain("此 NPC 目前沒有服務元件。");
  });

  it("renders groups with their notes and rows", () => {
    const wrapper = section({
      key: "persona",
      title: "人物設定",
      type: "groups",
      note: "版本 1（世代 1）",
      groups: [
        { key: "身分", title: "身分", rows: [{ label: "公開身分", value: "記錄員" }] },
        { key: "外貌", title: "外貌", note: "合成備註", rows: [{ label: "外貌", value: "灰短褂" }] },
      ],
    });
    expect(wrapper.findAll(".gm-section__group-title").map((n) => n.text())).toEqual([
      "身分",
      "外貌 合成備註",
    ]);
    expect(wrapper.findAll(".gm-ledger__row")).toHaveLength(2);
    expect(wrapper.get(".gm-section__note").text()).toBe("版本 1（世代 1）");
  });

  it("renders tiles, chips, bullets and text payloads", () => {
    const tiles = section({
      key: "resources",
      title: "資源",
      type: "tiles",
      tiles: [
        { key: "hp", label: "生命", value: 30, unit: "/ 30" },
        { key: "mp", label: "魔力", value: 10, unit: "/ 10", tone: "gold" },
      ],
    });
    expect(tiles.findAll(".gm-stat").map((n) => n.text())).toEqual([
      "30生命/ 30",
      "10魔力/ 10",
    ]);
    expect(tiles.findAll(".gm-stat__value")[1].classes()).toContain("is-gold");

    const chips = section({
      key: "links",
      title: "相關連結",
      type: "chips",
      chips: [
        { key: "room", label: "廣場", link: { kind: "rooms", id: "3", label: "廣場" } },
        { key: "quests", label: "任務紀錄", link: { kind: "quests", id: "owner:12", owner: "12" } },
      ],
    });
    expect(chips.findAll(".gm-chip").map((n) => n.text())).toEqual(["廣場", "任務紀錄"]);
    expect(chips.get("a").attributes("href")).toBe("/gm/runtime/rooms/3");

    const bullets = section({ key: "truncation", title: "截斷", type: "bullets", items: ["t_a", "t_b"] });
    expect(bullets.findAll("li").map((n) => n.text())).toEqual(["t_a", "t_b"]);

    const text = section({ key: "prompt", title: "來源敘述", type: "text", text: "合成敘述" });
    expect(text.get("pre").text()).toBe("合成敘述");
  });

  it("renders a tree payload and an honest empty payload", () => {
    const tree = section({ key: "content", title: "內容", type: "tree", value: { note: "合成" } });
    expect(tree.get(".gm-json-tree").text()).toContain("note");
    const empty = section({ key: "schedule", title: "今日排程", type: "empty", note: "此 NPC 目前沒有排程。" });
    expect(empty.get(".gm-section__empty").text()).toBe("此 NPC 目前沒有排程。");
    expect(empty.find(".gm-section__note").exists()).toBe(false);
  });

  it("contains a failed section in its own slot", () => {
    const wrapper = section({
      key: "wallet",
      title: "錢包",
      error: { code: "source_unavailable", message: "此區塊的來源目前不存在或無法使用。" },
    });
    const error = wrapper.get(".gm-error");
    expect(error.text()).toContain("「錢包」無法讀取");
    expect(error.get("code").text()).toBe("source_unavailable");
    // ``live="off"`` renders no alert role: a section slot must not re-announce.
    expect(error.attributes("role")).toBeUndefined();
    expect(wrapper.get("h3").text()).toContain("錢包");
    expect(wrapper.attributes("data-type")).toBe("error");
  });

  it("falls back to a tree for an unknown payload type instead of hiding it", () => {
    const wrapper = section({ key: "future", title: "未來區塊", type: "hologram", value: { x: 1 } });
    expect(wrapper.get(".gm-json-tree").text()).toContain("hologram");
  });
});
