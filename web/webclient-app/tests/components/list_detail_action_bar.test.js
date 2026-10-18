// webclient-window-primitives: ListDetail scrolls its columns independently
// with the action bar pinned outside the detail's scroll region, and
// ActionBar shows committed disabled reasons and no rule text of its own.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { h } from "vue";
import ActionBar from "../../components/ActionBar.vue";
import ListDetail from "../../components/ListDetail.vue";

const APP_ROOT = join(process.cwd(), "web/webclient-app");

function rule(css, selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = new RegExp(`(?:^|\\n)${escaped} \\{([^}]*)\\}`).exec(css);
  return match ? match[1] : "";
}

describe("ListDetail (webclient-window-primitives)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
  });

  it("renders the rail, list and detail columns with the action bar outside the detail scroll", () => {
    wrapper = mount(ListDetail, {
      props: { listLabel: "背包物品", detailLabel: "物品詳情" },
      slots: {
        rail: () => h("nav", "rail"),
        list: () => h("ul", Array.from({ length: 60 }, (_, i) => h("li", `row ${i}`))),
        detail: () => h("article", "detail"),
        actions: () => h(ActionBar, { actions: [{ key: "use", label: "使用…" }] }),
      },
    });
    const root = wrapper.get('[data-testid="list-detail"]');
    expect(root.classes()).toContain("list-detail--rail");
    const list = wrapper.get('[data-testid="list-detail__list"]');
    const detail = wrapper.get('[data-testid="list-detail__detail"]');
    const scroll = wrapper.get('[data-testid="list-detail__scroll"]');
    const actions = wrapper.get('[data-testid="list-detail__actions"]');
    expect(list.attributes("aria-label")).toBe("背包物品");
    expect(detail.attributes("aria-label")).toBe("物品詳情");
    // The bar is a child of the detail column, never inside either scroll
    // region, so scrolling the list or the detail leaves it in place.
    expect(actions.element.parentElement).toBe(detail.element);
    expect(scroll.element.contains(actions.element)).toBe(false);
    expect(list.element.contains(actions.element)).toBe(false);
    expect(list.element.contains(scroll.element)).toBe(false);
    expect(detail.element.lastElementChild).toBe(actions.element);
  });

  it("declares two independent scroll regions and a non-scrolling detail column", () => {
    const css = readFileSync(join(APP_ROOT, "components/ListDetail.vue"), "utf8");
    expect(rule(css, ".list-detail__list")).toMatch(/overflow: auto;/);
    expect(rule(css, ".list-detail__list")).toMatch(/min-height: 0;/);
    expect(rule(css, ".list-detail__detail")).toMatch(/overflow: hidden;/);
    expect(rule(css, ".list-detail__detail")).toMatch(/flex-direction: column;/);
    expect(rule(css, ".list-detail__scroll")).toMatch(/overflow: auto;/);
    expect(rule(css, ".list-detail__scroll")).toMatch(/flex: 1;/);
    expect(rule(css, ".list-detail__scroll")).toMatch(/min-height: 0;/);
    expect(rule(css, ".list-detail__actions")).toMatch(/flex: none;/);
  });

  it("omits the rail column and the bar when not given, and narrows the list for portraits", () => {
    wrapper = mount(ListDetail, {
      props: { variant: "portrait" },
      slots: { list: () => h("p", "list"), detail: () => h("p", "detail") },
    });
    const root = wrapper.get('[data-testid="list-detail"]');
    expect(root.classes()).not.toContain("list-detail--rail");
    expect(root.classes()).toContain("list-detail--portrait");
    expect(wrapper.find('[data-testid="list-detail__rail"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="list-detail__actions"]').exists()).toBe(false);
  });
});

describe("ActionBar (webclient-window-primitives)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
  });

  it("shows a disabled give control's committed reason in the left slot", async () => {
    wrapper = mount(ActionBar, {
      props: {
        actions: [
          { key: "give", label: "交給艾拉", enabled: false, reason: "戰鬥中無法交換物品" },
          { key: "use", label: "使用…", tone: "primary" },
        ],
      },
    });
    const reason = wrapper.get('[data-testid="action-bar__reason"]');
    expect(reason.text()).toBe("戰鬥中無法交換物品");
    expect(reason.element.parentElement.classList.contains("action-bar__lead")).toBe(true);
    const give = wrapper.get('[data-testid="action-bar__btn--give"]');
    expect(give.attributes("aria-disabled")).toBe("true");
    expect(give.attributes("aria-describedby")).toBe(reason.attributes("id"));
    // Disabled stays focusable but emits nothing.
    expect(give.attributes("disabled")).toBeUndefined();
    await give.trigger("click");
    expect(wrapper.emitted("action")).toBeUndefined();
    const use = wrapper.get('[data-testid="action-bar__btn--use"]');
    expect(use.attributes("aria-disabled")).toBeUndefined();
    expect(use.classes()).toContain("action-bar__btn--primary");
    await use.trigger("click");
    expect(wrapper.emitted("action")).toEqual([["use"]]);
  });

  it("shows a caller reason with its code, deduplicates reasons, and orders buttons after the lead", () => {
    wrapper = mount(ActionBar, {
      props: {
        reason: { code: "transfer_in_combat", message: "戰鬥中無法交換物品" },
        actions: [
          { key: "a", label: "甲", enabled: false, reason: "戰鬥中無法交換物品" },
          { key: "b", label: "乙", enabled: false, reason: "倒地時無法行動" },
        ],
      },
      slots: { default: () => h("div", { class: "stepper" }, "1") },
    });
    const reasons = wrapper.findAll('[data-testid="action-bar__reason"]');
    expect(reasons.map((r) => r.text())).toEqual(["戰鬥中無法交換物品", "倒地時無法行動"]);
    expect(reasons[0].attributes("data-reason-code")).toBe("transfer_in_combat");
    expect(wrapper.get('[data-testid="action-bar__btn--a"]').attributes("aria-describedby")).toBe(reasons[0].attributes("id"));
    expect(wrapper.get('[data-testid="action-bar__btn--b"]').attributes("aria-describedby")).toBe(reasons[1].attributes("id"));
    const children = [...wrapper.get('[data-testid="action-bar"]').element.children];
    expect(children[0].classList.contains("action-bar__lead")).toBe(true);
    expect(children[1].classList.contains("stepper")).toBe(true);
  });

  it("renders no text of its own: no reasons, no rule copy, only the given labels", () => {
    wrapper = mount(ActionBar, { props: { actions: [{ key: "equip", label: "裝備", glyph: "sword" }] } });
    expect(wrapper.find('[data-testid="action-bar__reason"]').exists()).toBe(false);
    expect(wrapper.get(".action-bar__lead").text()).toBe("");
    expect(wrapper.text()).toBe("裝備");
    expect(wrapper.get('[data-testid="action-bar__btn--equip"] svg').attributes("aria-hidden")).toBe("true");
  });

  it("an enabled control's reason is not shown", () => {
    wrapper = mount(ActionBar, { props: { actions: [{ key: "x", label: "甲", enabled: true, reason: "不顯示" }] } });
    expect(wrapper.text()).toBe("甲");
  });
});
