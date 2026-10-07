import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import GmShell from "../components/GmShell.vue";
import GmNav from "../components/GmNav.vue";
import GmPageHeader from "../components/GmPageHeader.vue";
import { GM_SECTIONS } from "../lib/sections.js";

function nav(props = {}) {
  return mount(GmNav, { props: { items: GM_SECTIONS, activeKey: "overview", ...props } });
}

describe("GmNav", () => {
  it("lists every design section in order with the overview active", () => {
    const wrapper = nav();
    const labels = wrapper.findAll(".gm-nav__label").map((node) => node.text().replace("，", ""));
    expect(labels).toEqual(["總覽", "維運", "執行期狀態", "世界資料", "存檔"]);
    const active = wrapper.get("[aria-current='page']");
    expect(active.attributes("data-section")).toBe("overview");
    expect(active.attributes("href")).toBe("/gm/");
    expect(active.classes()).toContain("is-active");
  });

  it("renders undelivered sections disabled with 尚未開放 and no link", () => {
    const wrapper = nav();
    const disabled = wrapper.findAll("[aria-disabled='true']");
    expect(disabled.map((node) => node.attributes("data-section"))).toEqual([
      "operations",
    ]);
    for (const node of disabled) {
      expect(node.element.tagName).toBe("SPAN");
      expect(node.attributes("href")).toBeUndefined();
      expect(node.attributes("tabindex")).toBeUndefined();
      expect(node.text()).toContain("尚未開放");
    }
    // The delivered saves section (S5) is a real link to its page.
    const saves = wrapper.get("[data-section='actions']");
    expect(saves.element.tagName).toBe("A");
    expect(saves.attributes("href")).toBe("/gm/saves");
    // The delivered world-data section (S4) is a real link to its home.
    const world = wrapper.get("[data-section='world-data']");
    expect(world.element.tagName).toBe("A");
    expect(world.attributes("href")).toBe("/gm/world");
    // The delivered runtime section is a real link.
    const runtime = wrapper.get("[data-section='runtime']");
    expect(runtime.element.tagName).toBe("A");
    expect(runtime.attributes("href")).toBe("/gm/runtime");
  });

  it("renders the runtime navigation tree only while that section is active", () => {
    const collapsed = nav();
    expect(collapsed.find(".gm-nav__tree").exists()).toBe(false);
    const wrapper = nav({ activeKey: "runtime", activeRoute: "runtime-list" });
    const children = wrapper.findAll(".gm-nav__child");
    expect(children.map((node) => node.text())).toEqual([
      "全域搜尋",
      "帳號",
      "玩家角色",
      "NPC",
      "魔物",
      "房間",
      "任務",
      "敘事紀錄",
      "美術資產",
    ]);
    expect(children[1].attributes("href")).toBe("/gm/runtime/accounts");
    expect(children.find((node) => node.text() === "全域搜尋").attributes("href")).toBe(
      "/gm/runtime/search",
    );
  });

  it("marks the current child entry and navigates it with its full location", async () => {
    const wrapper = nav({ activeKey: "runtime", activeRoute: "runtime-list" });
    const child = wrapper.findAll(".gm-nav__child").find((node) => node.text() === "NPC");
    const link = child.element;
    link.addEventListener("click", (event) => event.preventDefault());
    await child.trigger("click", { button: 0 });
    const emitted = wrapper.emitted("navigate");
    expect(emitted).toHaveLength(1);
    expect(emitted[0][0].route).toBe("runtime-list");
    expect(emitted[0][0].params).toEqual({ kind: "npcs" });
  });

  it("ignores pointer and keyboard activation of a disabled section", async () => {
    const wrapper = nav();
    const disabled = wrapper.get("[data-section='operations']");
    await disabled.trigger("click");
    await disabled.trigger("keydown", { key: "Enter" });
    await disabled.trigger("keydown", { key: " " });
    expect(wrapper.emitted("navigate")).toBeUndefined();
  });

  it("emits navigate for a delivered section on a plain click only", async () => {
    const wrapper = nav();
    const link = wrapper.get("[data-section='overview']");
    // jsdom cannot navigate; swallow the browser default after Vue's handler.
    link.element.addEventListener("click", (event) => event.preventDefault());
    await link.trigger("click", { button: 0, ctrlKey: true });
    expect(wrapper.emitted("navigate")).toBeUndefined();
    await link.trigger("click", { button: 0 });
    expect(wrapper.emitted("navigate")).toHaveLength(1);
    expect(wrapper.emitted("navigate")[0][0].key).toBe("overview");
  });
});

describe("GmPageHeader", () => {
  it("shows the account verbatim in mono with its level and a neutral logout form", () => {
    const wrapper = mount(GmPageHeader, {
      props: { title: "總覽", account: "Op_01 <x>", permissionLevel: "Developer", logoutUrl: "/auth/logout/" },
    });
    expect(wrapper.get("h1").text()).toBe("總覽");
    expect(wrapper.get(".gm-page-header__account").text()).toBe("Op_01 <x>");
    expect(wrapper.get(".gm-page-header__level").text()).toBe("Developer");
    const form = wrapper.get("form");
    expect(form.attributes("method")).toBe("post");
    expect(form.attributes("action")).toBe("/auth/logout/");
    const button = form.get("button");
    expect(button.text()).toBe("登出");
    expect(button.classes()).toContain("ui-btn--ghost");
    expect(button.classes()).not.toContain("ui-btn--danger");
  });

  it("posts the csrftoken cookie with the logout form", async () => {
    document.cookie = "csrftoken=logout-token";
    const wrapper = mount(GmPageHeader, { props: { title: "總覽", logoutUrl: "/auth/logout/" } });
    await wrapper.get("form").trigger("submit");
    expect(wrapper.get("input[name='csrfmiddlewaretoken']").element.value).toBe("logout-token");
  });
});

describe("GmShell", () => {
  it("composes navigation, header, and content landmarks", async () => {
    const wrapper = mount(GmShell, {
      props: { sections: GM_SECTIONS, activeKey: "overview", title: "總覽", account: "op" },
      slots: { default: "<p class='content'>內容</p>" },
    });
    expect(wrapper.get("nav").attributes("aria-label")).toBe("GM 主選單");
    expect(wrapper.get("main#gm-main .content").text()).toBe("內容");
    expect(wrapper.get("header h1").text()).toBe("總覽");
    expect(wrapper.get("a.gm-shell__skip").attributes("href")).toBe("#gm-main");
    await wrapper.get("[data-section='overview']").trigger("click", { button: 0 });
    expect(wrapper.emitted("navigate")[0][0].key).toBe("overview");
    await wrapper.get("[data-section='operations']").trigger("click");
    expect(wrapper.emitted("navigate")).toHaveLength(1);
  });

  it("renders the runtime tree when the runtime section is the active area", () => {
    const wrapper = mount(GmShell, {
      props: { sections: GM_SECTIONS, activeKey: "runtime", activeRoute: "runtime-list", title: "執行期清單" },
    });
    expect(wrapper.findAll(".gm-nav__child").length).toBe(9);
  });
});
