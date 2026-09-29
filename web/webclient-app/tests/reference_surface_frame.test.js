// webclient-drawer-frame-unification: the shared reference-surface header.
// DrawerHeader is presentational (glyph, title, subtitle, one named close
// control, emits `close` only); the drawer and overlay hosts keep their own
// modal lifecycles; every header draws the registry glyph of the navigation
// control that opens its surface; the gallery carries exactly one header.

import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../AppClient.vue";
import DrawerHeader from "../components/DrawerHeader.vue";
import GalleryGenerateDrawer from "../components/GalleryGenerateDrawer.vue";
import { glyphPath } from "../components/dock-icons.js";
import { useElosernStore } from "../stores/elosern.js";
import { GALLERY_SAMPLE } from "../stories/gallery-fixtures.js";
import * as fx from "./store/protocol_fixtures.js";

describe("DrawerHeader", () => {
  it("draws the registry glyph, the title, the subtitle and one named close control", async () => {
    const w = mount(DrawerHeader, { props: { icon: "lineage", title: "技能系譜", subtitle: "熟練度", surface: "overlay-host" } });
    expect(w.get(".drawer-header__icon path").attributes("d")).toBe(glyphPath("lineage"));
    expect(w.get(".drawer-header__icon").attributes("aria-hidden")).toBe("true");
    expect(w.get('[data-testid="overlay-host__title"]').text()).toBe("技能系譜");
    expect(w.get(".drawer-header__subtitle").text()).toBe("熟練度");
    const close = w.get('[data-testid="overlay-host-close"]');
    expect(close.attributes("aria-label")).toBe("關閉");
    expect(close.text()).toBe("");
    await close.trigger("click");
    expect(w.emitted("close")).toHaveLength(1);
  });

  it("renders no glyph for a missing or unmapped key and no empty subtitle", () => {
    for (const icon of [null, "no-such-glyph"]) {
      const w = mount(DrawerHeader, { props: { icon, title: "T", surface: "hud-drawer" } });
      expect(w.find(".drawer-header__icon").exists()).toBe(false);
      expect(w.find(".drawer-header__subtitle").exists()).toBe(false);
    }
  });

  it("owns no key handling: Escape on the header emits nothing", async () => {
    const w = mount(DrawerHeader, { props: { icon: "help", title: "說明", surface: "overlay-host" } });
    await w.get(".drawer-header__close").trigger("keydown", { key: "Escape" });
    expect(w.emitted("close")).toBeUndefined();
  });
});

describe("reference surface headers in the client", () => {
  let store;
  let wrapper;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    store.setSender(fx.createFakeSender());
    wrapper = mount(AppClient, { attachTo: document.body });
    store.beginTransport(1);
    store.setConnected(true);
  });
  afterEach(() => {
    wrapper.unmount();
    document.body.replaceChildren();
  });

  async function snapshot(extra = {}) {
    const panels = {
      status: fx.statusPanel(),
      exploration: fx.explorationPanel(),
      context_actions: fx.explorationActions(),
      gallery: GALLERY_SAMPLE,
      ...extra,
    };
    expect(store.receive(1, "ui_snapshot", [fx.snapshot({ panels, revision: 1 })]).accepted).toBe(true);
    await wrapper.vm.$nextTick();
  }

  const navGlyph = (testid) => wrapper.get(`[data-testid="${testid}"] path`).attributes("d");
  const headerGlyph = () => wrapper.get(".drawer-header__icon path").attributes("d");

  it("draws each tool's own navigation glyph in the header of the surface it opens", async () => {
    await snapshot();
    const tools = [
      ["nav-tool-lineage", "技能系譜"],
      ["nav-tool-codex", "稱號冊"],
      ["gallery-opener", "角色肖像圖庫"],
      ["nav-tool-help", "說明"],
      ["nav-settings", "設定"],
      ["nav-tool-lore", "世界圖鑑"],
    ];
    for (const [testid, title] of tools) {
      const opener = wrapper.get(`[data-testid="${testid}"]`);
      opener.element.focus();
      await opener.trigger("click");
      await wrapper.vm.$nextTick();
      expect(headerGlyph(), testid).toBe(navGlyph(testid));
      expect(wrapper.findAll(".drawer-header"), testid).toHaveLength(1);
      expect(wrapper.findAll(".drawer-header__close"), testid).toHaveLength(1);
      expect(wrapper.get(".drawer-header__title").text(), testid).toBe(title);
      await wrapper.get(".drawer-header__close").trigger("click");
      expect(document.activeElement, testid).toBe(opener.element);
    }
  }, 20000);

  it("names the help overlay's dialog after its title", async () => {
    await snapshot();
    await wrapper.get('[data-testid="nav-tool-help"]').trigger("click");
    expect(wrapper.get('[data-testid="overlay-host"]').attributes("aria-label")).toBe("說明");
    // The scrim is the dialog's sibling, never inside the trapped surface.
    const scrim = wrapper.get('[data-testid="overlay-host-scrim"]');
    expect(scrim.attributes("aria-hidden")).toBe("true");
    expect(scrim.element.nextElementSibling).toBe(wrapper.get('[data-testid="overlay-host"]').element);
  });

  it("gives every reference drawer a registry glyph", async () => {
    await snapshot();
    const opened = [];
    for (const name of ["skill", "inventory", "quest", "lore", "status", "party"]) {
      store.openHudDrawer(name);
      await wrapper.vm.$nextTick();
      // A drawer opens only while its payload is present; the fixture
      // snapshot backs most of them.
      if (!wrapper.find('[data-testid="hud-drawer"]').exists()) continue;
      opened.push(name);
      const icon = wrapper.find('[data-testid="hud-drawer"] .drawer-header__icon path');
      expect(icon.exists(), name).toBe(true);
      expect(icon.attributes("d"), name).toBeTruthy();
      store.closeHudDrawer();
      await wrapper.vm.$nextTick();
    }
    expect(opened).toEqual(expect.arrayContaining(["quest", "status"]));
  });

  it("closes a nested gallery editor and then the gallery, each through its own owner", async () => {
    await snapshot();
    const opener = wrapper.get('[data-testid="gallery-opener"]');
    opener.element.focus();
    await opener.trigger("click");
    const panel = wrapper.get('[data-testid="gallery-panel"]');
    // The gallery body renders no title or close control of its own.
    expect(panel.findAll("h2")).toHaveLength(0);
    expect(panel.text()).not.toContain("角色肖像管理");
    const generate = panel.findAll("button").find((b) => b.text() === "生成新圖");
    generate.element.focus();
    await generate.trigger("click");
    const editor = wrapper.getComponent(GalleryGenerateDrawer);
    // The editor is its own drawer with its own header; the overlay's header
    // is not duplicated inside it.
    expect(editor.findAll(".drawer-header")).toHaveLength(1);
    expect(document.activeElement).toBe(editor.get('[data-testid="hud-drawer-close"]').element);

    // Escape inside the editor closes only the editor.
    await editor.get('[data-testid="hud-drawer"]').trigger("keydown", { key: "Escape" });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    expect(wrapper.findComponent(GalleryGenerateDrawer).exists()).toBe(false);
    expect(wrapper.find('[data-testid="gallery-panel"]').exists()).toBe(true);
    expect(document.activeElement).toBe(generate.element);

    // The next Escape closes the gallery overlay and restores its opener.
    await generate.trigger("keydown", { key: "Escape" });
    expect(wrapper.find('[data-testid="gallery-panel"]').exists()).toBe(false);
    expect(document.activeElement).toBe(opener.element);
  }, 20000);
});
