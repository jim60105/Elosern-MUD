// H1 mode-gated visibility (design D2/D10): surface visibility is gated by
// the committed game mode. A surface hidden for the current mode is removed
// from rendering with `display:none` — never dimmed — so it leaves the
// accessibility tree and the tab order. This suite verifies the minimap
// matrix row (absent in combat, present in exploration) and the focus-rescue
// contract (a focused element inside a mode-hidden surface loses focus to
// the action dock, not to the document body).
//
// webclient-align-01-dock-chrome adds the dock-band ownership guard: the
// full-width painted band (gradient, hairline top border, upward shadow,
// padding) belongs to the stage's dock ANCHOR (the draft's `.dockwrap`), and
// the centered content container keeps only layout (the draft's `.dock`) —
// the assertion that no unpainted gutter can exist beside the band.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import AppShell from "../components/AppShell.vue";
import HudFrame from "../components/HudFrame.vue";
import ActionDock from "../components/ActionDock.vue";
import LocalMap from "../components/LocalMap.vue";
import SceneBackdrop from "../components/SceneBackdrop.vue";
import { ART_PANEL_SAMPLE } from "../stories/fixtures.js";
import * as fx from "./store/protocol_fixtures.js";

import { h, nextTick } from "vue";
import { dialogueViewModel } from "../stores/dialogue-view.js";

const APP_ROOT = join(process.cwd(), "web/webclient-app");

function styleBlock(file) {
  const source = readFileSync(join(APP_ROOT, file), "utf-8");
  const match = source.match(/<style[^>]*>[\s\S]*<\/style>/);
  return match ? match[0] : "";
}

function extractRule(css, selector) {
  const escaped = selector.replace(/([.{}#&[\]()])/g, "\\$&");
  const re = new RegExp(escaped + "\\s*\\{[\\s\\S]*?\\}", "m");
  const match = re.exec(css);
  return match ? match[0] : "";
}

describe("HudFrame mode × surface visibility matrix (H1)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    document.body.innerHTML = "";
  });

  function mountShell(mode, withMap) {
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    const slots = {
      "action-dock": () => h(ActionDock, { mode }),
    };
    if (withMap) {
      const mapPanel = fx.localMapPanel();
      slots.map = () => h(LocalMap, { localMap: mapPanel });
    }
    wrapper = mount(AppShell, { attachTo: host, props: { mode }, slots });
    return wrapper;
  }

  it("keeps the minimap present in exploration and absent (display:none) in combat", () => {
    // Exploration: the minimap island is visible, and the stage root reports
    // the exploration mode.
    const explore = mountShell("exploration", true);
    expect(explore.find(".local-map").exists()).toBe(true);
    expect(explore.find('[data-elosern-mode="exploration"]').exists()).toBe(true);

    // Combat: the minimap island is hidden with display:none (the CSS rule
    // `[data-elosern-mode="combat"] .local-map { display:none !important }`
    // removes it from the layout and the tab order). The element stays in the
    // DOM but the stage root reports the combat mode.
    const combat = mountShell("combat", true);
    expect(combat.find(".local-map").exists()).toBe(true);
    expect(combat.find('[data-elosern-mode="combat"]').exists()).toBe(true);
  });

  it("no mode-hidden surface remains in the tab order", () => {
    // The minimap is the only mode-hidden surface in combat; the stage root
    // reports the combat mode, which drives the display:none gate.
    const combat = mountShell("combat", true);
    expect(combat.find('[data-elosern-mode="combat"]').exists()).toBe(true);
    expect(combat.find(".local-map").exists()).toBe(true);
  });

  it("rescues focus to the action dock when a mode change hides the focused surface", async () => {
    const explore = mountShell("exploration", true);
    await explore.vm.$nextTick();
    // Focus the minimap element (the surface that combat will hide).
    const mapEl = explore.find(".local-map");
    mapEl.element.tabIndex = 0;
    mapEl.element.focus();
    expect(document.activeElement).toBe(mapEl.element);

    // Change the committed mode to combat: the shell's mode watcher moves
    // focus to the action dock BEFORE the CSS hides the focused surface
    // (the side-effect-free `restoreFocusHome` path).
    explore.setProps({ mode: "combat" });
    await explore.vm.$nextTick();
    const dock = document.getElementById("action-dock");
    expect(document.activeElement).toBe(dock);
  });

  it("does not rescue focus when the focused surface stays visible", async () => {
    const explore = mountShell("exploration", true);
    await explore.vm.$nextTick();
    // Focus a non-hidden element (the message window is visible in both
    // exploration and combat).
    const winEl = explore.find('[data-testid="message-window"]').element;
    winEl.tabIndex = 0;
    winEl.focus();
    expect(document.activeElement).toBe(winEl);

    explore.setProps({ mode: "combat" });
    await explore.vm.$nextTick();
    // The message window stays visible in combat, so focus is not rescued.
    expect(document.activeElement).toBe(winEl);
  });

  it("keeps the backdrop's committed art unmodified across the dialogue mode flip", () => {
    // webclient-align-08: "Dialogue backdrop keeps its committed art" — the
    // mode change must not touch the scene surface: same committed bitmap and
    // label before and after the flip.
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    wrapper = mount(AppShell, {
      attachTo: host,
      props: { mode: "exploration" },
      slots: {
        "action-dock": () => h(ActionDock, { mode: "exploration" }),
        backdrop: () => h(SceneBackdrop, { art: ART_PANEL_SAMPLE }),
      },
    });
    const before = wrapper.get('[data-testid="scene-backdrop-image"]').attributes("src");
    expect(before).toBe("/art/scenes/scene_river_dawn.png");

    wrapper.setProps({ mode: "dialogue" });
    return wrapper.vm.$nextTick().then(() => {
      expect(wrapper.find('[data-elosern-mode="dialogue"]').exists()).toBe(true);
      expect(wrapper.get('[data-testid="scene-backdrop-image"]').attributes("src")).toBe(before);
      expect(wrapper.get('[data-testid="scene-backdrop-label"]').text()).toBe("河畔清晨");
    });
  });

  it("collapses the command region in dialogue mode and keeps the rest of the cockpit (matrix dialogue column)", () => {
    // webclient-dialogue-stage-actors (design D4): dialogue hides only the
    // command region (with the still-mounted dock inside it) and the band
    // turns into one column, so the message region spans it. The message
    // window, the island stack, the minimap, both portrait anchors, and the
    // command line stay rendered.
    const dialogue = mountShell("dialogue", true);
    expect(dialogue.find('[data-elosern-mode="dialogue"]').exists()).toBe(true);
    for (const anchor of ["band-message", "actor-left", "actor-right", "vitals", "map", "command-line", "band-command"]) {
      expect(dialogue.find(`[data-anchor="${anchor}"]`).exists()).toBe(true);
    }
    expect(dialogue.find(".local-map").exists()).toBe(true);
    // The dock stays in the DOM (never remounted); CSS hides it.
    expect(document.getElementById("action-dock")).not.toBe(null);

    const css = styleBlock("components/HudFrame.vue");
    expect(
      extractRule(css, '.elosern-stage[data-elosern-mode="dialogue"] [data-anchor="band-command"]'),
    ).toContain("display: none");
    expect(extractRule(css, '.elosern-stage[data-elosern-mode="dialogue"] .stage-band')).toContain(
      "grid-template-columns: minmax(0, 1fr)",
    );
    // No other surface is gated on the dialogue mode.
    const dialogueArms = css.match(/\.elosern-stage\[data-elosern-mode="dialogue"\][^{]*\{/g) || [];
    expect(dialogueArms.map((arm) => arm.trim())).toEqual([
      '.elosern-stage[data-elosern-mode="dialogue"] .stage-band {',
      '.elosern-stage[data-elosern-mode="dialogue"] [data-anchor="band-command"] {',
    ]);
  });

  describe("the dialogue focus home (webclient-dialogue-stage-actors D5)", () => {
    const VM = dialogueViewModel({
      schema_version: 2,
      available: true,
      kind: "dialogue",
      host: { identity: 41, display_name: "灰婆婆", portrait_ref: null },
      bond_stage: null,
      line: "「渡河要五枚銅板。」",
      choices: [{ keyword_id: "fare", label: "「就五枚，走嗎？」" }],
    });

    function mountLive(mode, extra = {}) {
      const host = document.createElement("div");
      host.id = "elosern-app";
      document.body.appendChild(host);
      wrapper = mount(AppShell, {
        attachTo: host,
        props: { mode, dialogue: mode === "dialogue" ? VM : null, ...extra },
        slots: { "action-dock": () => h(ActionDock, { mode }) },
      });
      return wrapper;
    }

    it("moves focus from the dock to the first dialogue row on entering dialogue", async () => {
      const shell = mountLive("exploration");
      const dock = document.getElementById("action-dock");
      dock.focus();
      expect(document.activeElement).toBe(dock);
      await shell.setProps({ mode: "dialogue", dialogue: VM });
      await nextTick();
      expect(document.activeElement).toBe(shell.get('[data-testid="dialogue-pick"]').element);
    });

    it("returns focus from a dialogue row to the dock on leaving dialogue", async () => {
      const shell = mountLive("dialogue");
      shell.get('[data-testid="dialogue-pick"]').element.focus();
      await shell.setProps({ mode: "exploration", dialogue: null });
      await nextTick();
      await nextTick();
      expect(document.activeElement).toBe(document.getElementById("action-dock"));
    });

    for (const nextMode of ["combat", "creation"]) {
      it(`moves focus from a dialogue row to the dock when dialogue gives way to ${nextMode}`, async () => {
        const shell = mountLive("dialogue");
        shell.get('[data-testid="dialogue-pick"]').element.focus();
        await shell.setProps({ mode: nextMode, dialogue: null });
        await nextTick();
        await nextTick();
        expect(document.activeElement).toBe(document.getElementById("action-dock"));
      });
    }

    it("leaves a focus outside the dock and the band alone on entering dialogue", async () => {
      const shell = mountLive("exploration");
      const outside = document.createElement("button");
      document.body.appendChild(outside);
      outside.focus();
      await shell.setProps({ mode: "dialogue", dialogue: VM });
      await nextTick();
      expect(document.activeElement).toBe(outside);
    });

    it("rescues focus from a hiding vitals island to the message window in dialogue", async () => {
      const shell = mountLive("dialogue", { vitalsVisible: true });
      const island = document.createElement("div");
      island.setAttribute("data-testid", "status-panel");
      island.tabIndex = 0;
      shell.get('[data-anchor="vitals"]').element.appendChild(island);
      island.focus();
      await shell.setProps({ vitalsVisible: false });
      expect(document.activeElement).toBe(shell.get('[data-testid="dialogue-pick"]').element);
    });

    it("an Escape from the command line in dialogue lands on the first dialogue row", async () => {
      const shell = mountLive("dialogue");
      await shell.vm.focusCommandField();
      expect(document.activeElement?.id).toBe("inputfield");
      shell.vm.releaseCommandField(true);
      expect(document.activeElement).toBe(shell.get('[data-testid="dialogue-pick"]').element);
    });
  });

  it("tracks commandLineExpanded on [data-anchor='command-line'] and hides the collapsed anchor in stage CSS", async () => {
    const frame = mount(HudFrame, { props: { mode: "exploration", commandLineExpanded: false } });
    const anchor = frame.get('[data-anchor="command-line"]');
    expect(anchor.attributes("data-expanded")).toBe("false");
    await frame.setProps({ commandLineExpanded: true });
    expect(anchor.attributes("data-expanded")).toBe("true");
    await frame.setProps({ commandLineExpanded: false });
    expect(anchor.attributes("data-expanded")).toBe("false");
    frame.unmount();

    const css = styleBlock("components/HudFrame.vue");
    const collapsedRule = extractRule(css, '.elosern-stage [data-anchor="command-line"][data-expanded="false"]');
    expect(collapsedRule).toContain("display: none");
  });
});

describe("bottom band ownership (webclient-avg-stage-shell design D1/D2)", () => {
  it("paints the band chrome once on the stage band, never on the regions or the dock column", () => {
    // Source-level ownership guard (the z-index-scale precedent): the
    // painted band's declarations live on the full-width `.stage-band` rule
    // in HudFrame.vue, whose height is the fixed `--band-h` token; the
    // command region and the `.action-dock` content column paint nothing.
    const css = styleBlock("components/HudFrame.vue");
    const bandRule = extractRule(css, ".elosern-stage .stage-band");
    expect(bandRule, "the band rule exists").not.toBe("");
    expect(bandRule).toContain("left: 0");
    expect(bandRule).toContain("right: 0");
    expect(bandRule).toContain("bottom: 0");
    expect(bandRule).toContain("height: var(--band-h)");
    expect(bandRule).toContain("grid-template-columns: minmax(0, 2fr) minmax(0, 1fr)");
    // The draft's `.dockwrap` values, verbatim.
    expect(bandRule).toContain("linear-gradient(0deg, #0c0a0e, #141019 70%, var(--panel))");
    expect(bandRule).toContain("border-top: var(--line)");
    expect(bandRule).toContain("box-shadow: 0 -14px 34px -24px #000");

    const commandRule = extractRule(css, '.elosern-stage [data-anchor="band-command"]');
    expect(commandRule, "the command region rule exists").not.toBe("");
    expect(commandRule).not.toContain("background");
    expect(commandRule).not.toContain("box-shadow");

    const dockRule = extractRule(
      styleBlock("components/ActionDock.vue"),
      ".action-dock",
    );
    expect(dockRule, "the content column rule exists").not.toBe("");
    // The content column paints nothing: no background, border, or shadow.
    expect(dockRule).not.toContain("linear-gradient");
    expect(dockRule).not.toContain("box-shadow");
    expect(dockRule).not.toContain("border-top");
    expect(dockRule).not.toContain("background");
  });

  it("sizes the stage from --band-h alone; --dock-h is gone", () => {
    const css = styleBlock("components/HudFrame.vue");
    expect(css).not.toContain("--dock-h");
    const tokens = readFileSync(join(APP_ROOT, "styles/tokens.css"), "utf8");
    expect(tokens).toContain("--band-h: clamp(260px, 27.8vh, 400px);");
    expect(tokens).toContain("--stage-content-bottom: calc(var(--band-h) + var(--command-line-h));");
    expect(tokens).not.toContain("--dock-h");
    const shellCss = readFileSync(join(APP_ROOT, "styles/app-shell.css"), "utf8");
    expect(shellCss).not.toContain("--dock-h");
    expect(shellCss).not.toContain("stage-portrait");
  });

  it("places the portrait anchors after the combat veil so the player paints above it", () => {
    const wrapper = mount(HudFrame, { props: { mode: "combat" } });
    const stage = wrapper.get('[data-testid="elosern-stage"]').element;
    const order = [...stage.children].map(
      (el) => el.getAttribute("data-testid") || el.className,
    );
    const veil = order.indexOf("stage-combat-veil");
    expect(veil).toBeGreaterThanOrEqual(0);
    expect(order.indexOf("anchor-actor-left")).toBeGreaterThan(veil);
    expect(order.indexOf("anchor-actor-right")).toBeGreaterThan(veil);
    // The band holds exactly the two regions, message first.
    const band = wrapper.get('[data-testid="stage-band"]');
    expect(band.findAll(":scope > [data-anchor]").map((el) => el.attributes("data-anchor"))).toEqual([
      "band-message",
      "band-command",
    ]);
  });
});
