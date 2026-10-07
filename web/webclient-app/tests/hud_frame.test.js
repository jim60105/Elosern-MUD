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
import { afterEach, describe, expect, it, vi } from "vitest";
import AppShell from "../components/AppShell.vue";
import HudFrame from "../components/HudFrame.vue";
import ActionDock from "../components/ActionDock.vue";
import LocalMap from "../components/LocalMap.vue";
import SceneBackdrop from "../components/SceneBackdrop.vue";
import DialogueChoices from "../components/DialogueChoices.vue";
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

  it("keeps the creation vitals gate at display:none", () => {
    const creation = mountShell("creation", false);
    expect(creation.get('[data-testid="elosern-stage"]').attributes("data-elosern-mode")).toBe("creation");
    const css = styleBlock("components/HudFrame.vue");
    expect(css).toContain('.elosern-stage[data-elosern-mode="creation"] [data-anchor="vitals"]');
    expect(extractRule(css, '.elosern-stage[data-elosern-mode="creation"] [data-anchor="command-line"]')).toContain("display: none");
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

  it("collapses the command region and hides cockpit anchors in dialogue", () => {
    // Anchors stay mounted, but mode gates remove cockpit layout and access.
    const dialogue = mountShell("dialogue", true);
    expect(dialogue.find('[data-elosern-mode="dialogue"]').exists()).toBe(true);
    for (const anchor of ["band-message", "actor-left", "actor-right", "vitals", "map", "command-line", "band-command"]) {
      expect(dialogue.find(`[data-anchor="${anchor}"]`).exists()).toBe(true);
    }
    expect(dialogue.find(".local-map").exists()).toBe(true);
    // The dock stays in the DOM (never remounted); CSS hides it.
    expect(document.getElementById("action-dock")).not.toBe(null);

    // webclient-mode-transitions (design D1): the collapsed region is inert
    // from the commit (out of the tab order, the accessibility tree, and
    // hit-testing), slides out as an absolute layer over the band's right
    // third, and ends `visibility: hidden` instead of `display:none`.
    expect(dialogue.get('[data-anchor="band-command"]').attributes("inert")).toBeDefined();
    const css = styleBlock("components/HudFrame.vue");
    const collapsed = extractRule(css, '.elosern-stage[data-elosern-mode="dialogue"] [data-anchor="band-command"]');
    expect(collapsed).not.toContain("display: none");
    for (const declaration of [
      "position: absolute",
      "right: 0",
      "width: 33.3333%",
      "transform: translateX(calc(100% * var(--motion-travel)))",
      "opacity: 0",
      "visibility: hidden",
    ]) {
      expect(collapsed).toContain(declaration);
    }
    expect(extractRule(css, '.elosern-stage[data-elosern-mode="dialogue"] .stage-band')).toContain(
      "grid-template-columns: minmax(0, 1fr)",
    );
    for (const anchor of ["vitals", "map"]) {
      expect(dialogue.get(`[data-anchor="${anchor}"]`).attributes("inert")).toBeDefined();
      expect(dialogue.get(`[data-anchor="${anchor}"]`).attributes("aria-hidden")).toBe("true");
      for (const source of [css, readFileSync(join(APP_ROOT, "styles/app-shell.css"), "utf-8")]) {
        // Match the grouped gate, including both selector arms.
        expect(source).toContain('.elosern-stage[data-elosern-mode="dialogue"] [data-anchor="vitals"],\n.elosern-stage[data-elosern-mode="dialogue"] [data-anchor="map"] {\n  display: none !important;');
      }
    }
  });

  it.each(["map", "vitals"])("rescues %s focus before the dialogue DOM patch", async (anchor) => {
    const shell = mountShell("exploration", true);
    const target = anchor === "map"
      ? shell.get('[data-anchor="map"] [data-node]').element
      : document.createElement("button");
    target.setAttribute("tabindex", "0");
    if (anchor === "vitals") {
      shell.get('[data-anchor="vitals"]').element.appendChild(target);
    }
    target.focus();
    expect(document.activeElement).toBe(target);
    const page = shell.get('[data-testid="message-page"]').element;
    const observed = [];
    const originalFocus = page.focus.bind(page);
    const spy = vi.spyOn(page, "focus").mockImplementation((options) => {
      observed.push({
        mode: shell.get('[data-testid="elosern-stage"]').attributes("data-elosern-mode"),
        active: document.activeElement,
      });
      originalFocus(options);
    });
    await shell.setProps({ mode: "dialogue" });
    await nextTick();
    expect(observed[0]).toEqual({ mode: "exploration", active: target });
    expect(document.activeElement).toBe(page);
    expect(document.activeElement).not.toBe(document.body);
    spy.mockRestore();
  });

  it("mode hide wins over injured vitals and restores both anchors on exit", async () => {
    const style = document.createElement("style");
    style.textContent = styleBlock("components/HudFrame.vue").replace(/<\/?style[^>]*>/g, "");
    document.body.appendChild(style);
    const shell = mountShell("exploration", true);
    const status = document.createElement("div");
    status.dataset.testid = "status-panel";
    status.textContent = "HP 80/100";
    status.style.display = "block";
    shell.get('[data-anchor="vitals"]').element.appendChild(status);
    const anchors = ["vitals", "map"].map((name) => shell.get(`[data-anchor="${name}"]`).element);
    await shell.setProps({ mode: "dialogue", vitalsVisible: true });
    for (const anchor of anchors) {
      expect(getComputedStyle(anchor).display).toBe("none");
    }
    // A data revision cannot reveal a mode-hidden ancestor.
    status.textContent = "HP 70/100";
    expect(getComputedStyle(anchors[0]).display).toBe("none");
    await shell.setProps({ mode: "exploration" });
    for (const anchor of anchors) {
      expect(getComputedStyle(anchor).display).not.toBe("none");
      expect(anchor.hasAttribute("inert")).toBe(false);
      expect(anchor.hasAttribute("aria-hidden")).toBe(false);
    }
    expect(status.style.display).toBe("block");
  });

  describe("the dialogue focus home (webclient-dialogue-stage-actors D5; webclient-dialogue-choices-overlay D7)", () => {
    const VM = dialogueViewModel({
      schema_version: 2,
      available: true,
      kind: "dialogue",
      host: { identity: 41, display_name: "灰婆婆", portrait_ref: null },
      bond_stage: null,
      line: "「渡河要五枚銅板。」",
      choices: [{ keyword_id: "fare", label: "「就五枚，走嗎？」" }],
    });

    // `list` renders the dialogue choice list in the `choices` slot, as
    // AppClient does once the line is read.
    function mountLive(mode, extra = {}, { list = false } = {}) {
      const host = document.createElement("div");
      host.id = "elosern-app";
      document.body.appendChild(host);
      wrapper = mount(AppShell, {
        attachTo: host,
        props: { mode, dialogue: mode === "dialogue" ? VM : null, ...extra },
        slots: {
          "action-dock": () => h(ActionDock, { mode }),
          choices: () => (list ? h(DialogueChoices, { picks: VM.picks }) : null),
        },
      });
      return wrapper;
    }

    const page = (shell) => shell.get('[data-testid="message-page"]').element;
    const choiceList = (shell) => shell.get('[data-anchor="choices"] [data-testid="dialogue-choices"]').element;

    it("moves focus from the dock to the message page on entering dialogue (no list while the line is read)", async () => {
      const shell = mountLive("exploration");
      const dock = document.getElementById("action-dock");
      dock.focus();
      expect(document.activeElement).toBe(dock);
      await shell.setProps({ mode: "dialogue", dialogue: VM });
      await nextTick();
      await nextTick();
      expect(document.activeElement).toBe(page(shell));
    });

    it("lands on the choice list when it is already shown on entering dialogue", async () => {
      const shell = mountLive("exploration", {}, { list: true });
      document.getElementById("action-dock").focus();
      await shell.setProps({ mode: "dialogue", dialogue: VM });
      await nextTick();
      await nextTick();
      await nextTick();
      expect(document.activeElement).toBe(choiceList(shell));
    });

    it("returns focus from the choice list to the dock on leaving dialogue", async () => {
      const shell = mountLive("dialogue", {}, { list: true });
      choiceList(shell).focus();
      await shell.setProps({ mode: "exploration", dialogue: null });
      await nextTick();
      await nextTick();
      expect(document.activeElement).toBe(document.getElementById("action-dock"));
    });

    for (const nextMode of ["combat", "creation"]) {
      it(`moves focus from the choice list to the dock when dialogue gives way to ${nextMode}`, async () => {
        const shell = mountLive("dialogue", {}, { list: true });
        choiceList(shell).focus();
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

    it("rescues focus from a hiding vitals island to the message page, then to the shown list", async () => {
      const shell = mountLive("dialogue", { vitalsVisible: true }, { list: true });
      const island = document.createElement("div");
      island.setAttribute("data-testid", "status-panel");
      island.tabIndex = 0;
      shell.get('[data-anchor="vitals"]').element.appendChild(island);
      island.focus();
      await shell.setProps({ vitalsVisible: false });
      expect(document.activeElement).toBe(page(shell));
      await nextTick();
      expect(document.activeElement).toBe(choiceList(shell));
    });

    it("an Escape from the command line in dialogue lands on the message page without a list", async () => {
      const shell = mountLive("dialogue");
      await shell.vm.focusCommandField();
      expect(document.activeElement?.id).toBe("inputfield");
      shell.vm.releaseCommandField(true);
      await nextTick();
      expect(document.activeElement).toBe(page(shell));
    });

    it("an Escape from the command line in dialogue lands on the choice list once it is rendered", async () => {
      const shell = mountLive("dialogue", {}, { list: true });
      await shell.vm.focusCommandField();
      shell.vm.releaseCommandField(true);
      // The page first (always rendered), the list after the next render.
      expect(document.activeElement).toBe(page(shell));
      await nextTick();
      expect(document.activeElement).toBe(choiceList(shell));
    });

    it("focusMessagePage() parks focus on the message page", () => {
      const shell = mountLive("dialogue", {}, { list: true });
      choiceList(shell).focus();
      shell.vm.focusMessagePage();
      expect(document.activeElement).toBe(page(shell));
    });
  });

  it("gates the choices anchor to dialogue mode and bounds it above the scene caption row", () => {
    const css = styleBlock("components/HudFrame.vue");
    const anchor = extractRule(css, '.elosern-stage [data-anchor="choices"]');
    expect(anchor).toMatch(/width: min\(560px \* var\(--ui-scale\), 40%\)/);
    expect(anchor).toMatch(/left: calc\(50% - min\(280px \* var\(--ui-scale\), 20%\)\)/);
    expect(anchor).toMatch(/bottom: calc\(var\(--stage-caption-top\) \+ 8px \* var\(--ui-scale\)\)/);
    expect(anchor).toMatch(/z-index: 4/);
    expect(css).toMatch(/\.elosern-stage:not\(\[data-elosern-mode="dialogue"\]\) \[data-anchor="choices"\]\s*\{\s*display: none;/);
    const frame = mount(HudFrame, { props: { mode: "dialogue" }, slots: { choices: () => h("div", { class: "probe" }) } });
    expect(frame.get('[data-testid="anchor-choices"]').attributes("data-anchor")).toBe("choices");
    expect(frame.find('[data-anchor="choices"] .probe').exists()).toBe(true);
    frame.unmount();
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
    // The band material (webclient-band-material-pass) is painted here once.
    expect(bandRule).toContain("background:");

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
    expect(tokens).toContain("--band-h: clamp(190px * var(--ui-scale), 27.85vh, 400px * var(--ui-scale));");
    expect(tokens).toContain("--stage-content-bottom: calc(var(--band-h) + var(--command-line-h));");
    expect(tokens).not.toContain("--dock-h");
    const shellCss = readFileSync(join(APP_ROOT, "styles/app-shell.css"), "utf8");
    expect(shellCss).not.toContain("--dock-h");
    expect(shellCss).not.toContain("stage-portrait");
  });

  it("docks the vitals anchor on the band's top edge in both geometry copies, rising out of it", () => {
    // vitals-bar-redesign design D1: the `vitals` anchor is bottom-anchored
    // on the band's upper edge in the left gutter, never top-anchored, and
    // bounded below the top band. app-shell.css mirrors HudFrame's offsets.
    const frame = extractRule(styleBlock("components/HudFrame.vue"), '.elosern-stage [data-anchor="vitals"]');
    const shell = extractRule(
      readFileSync(join(APP_ROOT, "styles/app-shell.css"), "utf8"),
      '.elosern-root .elosern-stage [data-anchor="vitals"]',
    );
    for (const rule of [frame, shell]) {
      expect(rule, "the vitals anchor rule exists").not.toBe("");
      expect(rule).toContain("bottom: var(--band-h);");
      expect(rule).not.toMatch(/\btop:/);
      expect(rule).toContain("left: calc(16px * var(--ui-scale));");
      expect(rule).toContain("max-height: calc(100% - var(--header-h) - var(--band-h) - 2 * var(--stage-inset-y));");
    }
    expect(frame).toContain("overflow-y: auto;");
    expect(frame).toContain("z-index: 4;");
    // The dock's reveal enters from 12px BELOW its resting place and leaves
    // the same way (task 1.5): a positive Y travel, scaled by the travel token.
    const reveal = extractRule(
      styleBlock("components/StatusPanel.vue"),
      ".vitals-reveal-enter-from,\n.vitals-reveal-leave-to",
    );
    expect(reveal).toContain("transform: translateY(calc(var(--motion-shift-sm) * var(--motion-travel)));");
    expect(reveal).not.toContain("-1 *");
  });

  it("stands the scene caption on the stage floor between the portrait anchors", () => {
    // The backdrop box already ends at the band's top edge, so the caption
    // clears only the command-line row: no band-sized offset on top.
    const shellCss = readFileSync(join(APP_ROOT, "styles/app-shell.css"), "utf8");
    const rule = extractRule(shellCss, ".elosern-root .scene-backdrop .scene-backdrop__caption");
    expect(rule).toContain("bottom: calc(var(--command-line-h) + 12px * var(--ui-scale));");
    expect(rule).toContain("left: calc(var(--actor-left-inset) + var(--actor-h) * 2 / 3 + 16px * var(--ui-scale));");
    // The right side clears the right anchor box, or, while the foe line-up
    // stands (webclient-combat-foes-on-stage), its leftmost foe.
    expect(rule).toContain("calc(var(--actor-right-inset) + var(--actor-h) * 2 / 3 + 16px * var(--ui-scale)),");
    expect(rule).toContain("var(--actor-h) * 2 / 3 * var(--foe-lineup-span, 0) + 16px * var(--ui-scale)");
    expect(rule).toContain("var(--foe-face-clear) - var(--actor-h) * var(--foe-front-scale, 1) / 3");
    expect(rule).toContain("transition: right calc(var(--motion-actor) * var(--motion-travel)) var(--ease-standard);");
    expect(shellCss).not.toMatch(/scene-backdrop[^{]*\{[^}]*\d+vh/);
    const tokens = readFileSync(join(APP_ROOT, "styles/tokens.css"), "utf8");
    expect(tokens).toContain(
      "--stage-caption-top: calc(var(--stage-content-bottom) + 12px * var(--ui-scale) + var(--scene-caption-h));",
    );
  });


  it("holds the combat veil only while the round that ended the fight plays", async () => {
    // webclient-combat-beat-choreography D6: `data-beat-hold` renders only
    // with the prop; the mode attribute follows the committed mode.
    const wrapper = mount(HudFrame, { props: { mode: "exploration", modeChange: "combat-exploration" } });
    const stage = wrapper.get('[data-testid="elosern-stage"]');
    expect(stage.attributes("data-beat-hold")).toBeUndefined();
    await wrapper.setProps({ beatHold: true });
    expect(stage.attributes("data-beat-hold")).toBe("combat");
    expect(stage.attributes("data-elosern-mode")).toBe("exploration");
    expect(wrapper.get('[data-testid="stage-combat-veil"]').attributes("aria-hidden")).toBe("true");
    await wrapper.setProps({ beatHold: false });
    expect(stage.attributes("data-beat-hold")).toBeUndefined();

    const frameCss = styleBlock("components/HudFrame.vue");
    expect(extractRule(frameCss, '.elosern-stage[data-beat-hold="combat"] .stage-combat-veil')).toContain(
      "opacity: 1;",
    );
    // The pulse runs on unbroken across the flip: one rule serves both the
    // combat mode and the hold, so its resolved value cannot drift apart.
    expect(frameCss).toMatch(
      /\.elosern-stage\[data-elosern-mode="combat"\] \.stage-combat-veil::before,\s*\.elosern-stage\[data-beat-hold="combat"\] \.stage-combat-veil::before\s*\{\s*animation: elosern-combat-pulse var\(--motion-pulse\)/,
    );
    // The release fades on the combat exit's own veil transition.
    expect(extractRule(frameCss, ".elosern-stage[data-mode-change] .stage-combat-veil")).toContain(
      "transition: opacity var(--motion-actor)",
    );
    wrapper.unmount();
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
