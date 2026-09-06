import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import LoreCodexDrawer from "../../components/LoreCodexDrawer.vue";
import {
  LORE_CODEX_PANEL_EMPTY_SAMPLE,
  LORE_CODEX_PANEL_SAMPLE,
  LORE_CODEX_PANEL_UNAVAILABLE_SAMPLE,
} from "../../stories/fixtures.js";

describe("LoreCodexDrawer (webclient-lore-codex-drawer)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountDrawer(props = {}) {
    wrapper = mount(LoreCodexDrawer, {
      props: {
        codex: LORE_CODEX_PANEL_SAMPLE,
        ...props,
      },
    });
    return wrapper;
  }

  it("renders the aggregate control with the panel's discovered_total and one honest control per category", () => {
    const w = mountDrawer();
    expect(w.get('[data-testid="lore-codex-drawer__aggregate"]').text()).toContain("全部");
    expect(w.get('[data-testid="lore-codex-drawer__aggregate"]').text()).toContain("4");
    const pills = w.findAll('[data-testid^="lore-codex-drawer__category--"]');
    expect(pills).toHaveLength(8);
    // The 魔物 pill shows its discovered count; a zero-count category shows
    // zero — no denominator, total, or percentage anywhere on the surface.
    expect(w.get('[data-testid="lore-codex-drawer__category--monster"]').text()).toContain("魔物");
    expect(w.get('[data-testid="lore-codex-drawer__category--monster"]').text()).toContain("1");
    expect(w.get('[data-testid="lore-codex-drawer__category--guild"]').text()).toContain("0");
    expect(w.find('[data-testid="lore-codex-drawer__empty"]').exists()).toBe(false);
  });

  it("lists every discovered entry across every category under the aggregate control", () => {
    const w = mountDrawer();
    const titles = w.findAll('[data-testid^="lore-codex-drawer__entry--"]').map((row) => row.text());
    expect(titles.some((t) => t.includes("人類"))).toBe(true);
    expect(titles.some((t) => t.includes("灰河"))).toBe(true);
    expect(titles.some((t) => t.includes("霧骨狼"))).toBe(true);
    expect(titles.some((t) => t.includes("霧骨渡口"))).toBe(true);
    expect(titles).toHaveLength(4);
  });

  it("selecting a category filters the entry list locally to exactly that category", async () => {
    const w = mountDrawer();
    await w.get('[data-testid="lore-codex-drawer__category--monster"]').trigger("click");
    const rows = w.findAll('[data-testid^="lore-codex-drawer__entry--"]');
    expect(rows).toHaveLength(1);
    expect(rows[0].attributes("data-testid")).toBe("lore-codex-drawer__entry--monster-mist_wolf");
    // Other categories' entries are gone, not greyed or stubbed.
    expect(w.find('[data-testid="lore-codex-drawer__entry--race-human"]').exists()).toBe(false);
    expect(w.find('[data-testid="lore-codex-drawer__entry--anchor-misty_ford"]').exists()).toBe(false);
  });

  it("selecting a zero-count category renders an empty entry list", async () => {
    const w = mountDrawer();
    await w.get('[data-testid="lore-codex-drawer__category--guild"]').trigger("click");
    expect(w.findAll('[data-testid^="lore-codex-drawer__entry--"]')).toHaveLength(0);
    expect(w.find('[data-testid="lore-codex-drawer__card"]').exists()).toBe(false);
  });

  it("renders the selected entry's card exactly in the panel's field order", async () => {
    const w = mountDrawer();
    await w.get('[data-testid="lore-codex-drawer__entry--monster-mist_wolf"]').trigger("click");
    const card = w.get('[data-testid="lore-codex-drawer__card"]');
    expect(card.get('[data-testid="lore-codex-drawer__card-title"]').text()).toBe("霧骨狼");
    const names = card.findAll(".lore-codex-drawer__card-field-name").map((n) => n.text());
    const values = card.findAll(".lore-codex-drawer__card-field-value").map((v) => v.text());
    // The panel's card fields, in the panel's order, unmodified.
    expect(names).toEqual(["名稱", "描述", "例證"]);
    expect(values).toEqual(["霧骨狼", "群棲於霧中的中型獸，骨白如霧。", "霧骨狼·頭狼"]);
  });

  it("navigation dispatches nothing: no event of any kind is emitted", async () => {
    const w = mountDrawer();
    await w.get('[data-testid="lore-codex-drawer__category--race"]').trigger("click");
    await w.get('[data-testid="lore-codex-drawer__entry--race-human"]').trigger("click");
    await w.get('[data-testid="lore-codex-drawer__aggregate"]').trigger("click");
    // The wrapper records the native `click`s the trigger() calls produce;
    // the component itself declares no emits and emits none — no action,
    // no fetch request, no drawer event of any kind.
    const emitted = w.emitted() ?? {};
    expect(Object.keys(emitted).filter((key) => key !== "click")).toEqual([]);
  });

  it("the showcase's initial category and entry seeds select without a click", () => {
    const w = mountDrawer({
      initialCategory: "all",
      initialEntryKey: "monster:mist_wolf",
    });
    const card = w.get('[data-testid="lore-codex-drawer__card"]');
    expect(card.get('[data-testid="lore-codex-drawer__card-title"]').text()).toBe("霧骨狼");
    const names = card.findAll(".lore-codex-drawer__card-field-name").map((n) => n.text());
    expect(names).toEqual(["名稱", "描述", "例證"]);
  });

  it("an entry seed that matches nothing renders no card", () => {
    const w = mountDrawer({ initialEntryKey: "race:unknown_entry" });
    expect(w.find('[data-testid="lore-codex-drawer__card"]').exists()).toBe(false);
  });

  it("an empty codex renders the honest empty message and no entry rows", () => {
    const w = mountDrawer({ codex: LORE_CODEX_PANEL_EMPTY_SAMPLE });
    expect(w.get('[data-testid="lore-codex-drawer__empty"]').text()).toContain("尚未發現任何條目");
    expect(w.find('[data-testid="lore-codex-drawer__entries"]').exists()).toBe(false);
    expect(w.find('[data-testid="lore-codex-drawer__card"]').exists()).toBe(false);
    // The strip still renders: every category is a zero-count control.
    const pills = w.findAll('[data-testid^="lore-codex-drawer__category--"]');
    expect(pills).toHaveLength(8);
  });

  it("an unavailable panel renders the registry-owned reason and no codex content", () => {
    const w = mountDrawer({ codex: LORE_CODEX_PANEL_UNAVAILABLE_SAMPLE });
    const unavailable = w.get('[data-testid="lore-codex-drawer__unavailable"]');
    expect(unavailable.text()).toBe("知識圖鑑目前無法顯示");
    expect(unavailable.attributes("data-reason-code")).toBe("lore_codex_unavailable");
    // No category strip, entry list, or card beside the reason.
    expect(w.find('[data-testid="lore-codex-drawer__strip"]').exists()).toBe(false);
    expect(w.find('[data-testid="lore-codex-drawer__entries"]').exists()).toBe(false);
    expect(w.find('[data-testid="lore-codex-drawer__card"]').exists()).toBe(false);
  });

  it("a missing panel renders the honest absence line, not an invented reason", () => {
    const w = mountDrawer({ codex: null });
    expect(w.get('[data-testid="lore-codex-drawer__absent"]').exists()).toBe(true);
    expect(w.find('[data-testid="lore-codex-drawer__unavailable"]').exists()).toBe(false);
  });
});
