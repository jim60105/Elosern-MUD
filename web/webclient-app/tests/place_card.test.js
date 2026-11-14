// webclient-avg-place-card-top-bar (design D3); place-card-relocation (design
// D2): the stage's place card states the location and the world time — the
// only surface that does — at the head of the `map` anchor, content-sized,
// display-first, hidden in creation. exploration-room-actions (design D3):
// only while `actionsEnabled` it carries the 查看房間 and 休息 buttons
// (redesign-rest-entry relabels 等待 to 休息).
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import AppShell from "../components/AppShell.vue";
import PlaceCard from "../components/PlaceCard.vue";

const APP_ROOT = join(process.cwd(), "web/webclient-app");
const FOCUSABLE = "button, a[href], input, textarea, select, [tabindex]";

describe("PlaceCard", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  it("states the location as its heading and the world time beneath it", () => {
    wrapper = mount(PlaceCard, {
      props: { locationLabel: "測試起點", timeLabel: "春季 3 日 ‧ 12:00" },
    });
    const heading = wrapper.get('[data-testid="place-card__location"]');
    expect(heading.element.tagName).toBe("H1");
    expect(heading.text()).toBe("測試起點");
    expect(wrapper.get('[data-testid="place-card__time"]').text()).toBe("春季 3 日 ‧ 12:00");
  });

  it("sets the heading and the time on two levels with a decorative rule and no leading separator", () => {
    wrapper = mount(PlaceCard, {
      props: { locationLabel: "測試起點", timeLabel: "春季 3 日 ‧ 12:00" },
    });
    const children = [...wrapper.element.querySelectorAll("[data-testid]")].map((el) => el.dataset.testid);
    expect(children).toEqual(["place-card__location", "place-card__rule", "place-card__time"]);
    const rule = wrapper.get('[data-testid="place-card__rule"]');
    expect(rule.attributes("aria-hidden")).toBe("true");
    expect(rule.text()).toBe("");
    // The time line renders the committed label verbatim, from its first value.
    expect(wrapper.get('[data-testid="place-card__time"]').element.textContent).toBe("春季 3 日 ‧ 12:00");
    const css = readFileSync(join(APP_ROOT, "components/PlaceCard.vue"), "utf8");
    expect(css).not.toMatch(/place-card__time::before/);
  });

  it("falls back to its placeholders when nothing is committed", () => {
    wrapper = mount(PlaceCard, { props: { locationLabel: null, timeLabel: null } });
    expect(wrapper.get('[data-testid="place-card__location"]').text()).toBe("位置：--");
    expect(wrapper.get('[data-testid="place-card__time"]').text()).toBe("時間：--");
  });

  it("keeps an overlong label whole for assistive technology and holds no tab stop", () => {
    const long = "伊洛瑟恩王都外城區‧商人公會附屬倉庫的地下儲藏室";
    wrapper = mount(PlaceCard, { props: { locationLabel: long, timeLabel: "秋季 28 日 ‧ 23:59" } });
    const heading = wrapper.get('[data-testid="place-card__location"]');
    expect(heading.text()).toBe(long);
    expect(heading.attributes("title")).toBe(long);
    expect(wrapper.element.querySelectorAll(FOCUSABLE)).toHaveLength(0);
    // The truncation is CSS (ellipsis at the column's width), never a
    // shortened string; the card sizes to its content.
    const css = readFileSync(join(APP_ROOT, "components/PlaceCard.vue"), "utf8");
    expect(css).toContain("text-overflow: ellipsis");
    expect(css).not.toContain("height: 100%");
  });

  it("heads AppShell's map anchor from the labels AppShell receives, hidden in creation", () => {
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    wrapper = mount(AppShell, {
      attachTo: host,
      props: { mode: "exploration", locationLabel: "石板廣場", timeLabel: "春季 3 日 ‧ 12:00" },
    });
    const card = wrapper.get('[data-testid="anchor-map"] > [data-testid="place-card"]:first-child');
    expect(card.get('[data-testid="place-card__location"]').text()).toBe("石板廣場");
    expect(card.get('[data-testid="place-card__time"]').text()).toBe("春季 3 日 ‧ 12:00");
    // The top band states neither value.
    expect(wrapper.get('[data-testid="topbar"]').text()).not.toContain("石板廣場");
    expect(wrapper.get('[data-testid="topbar"]').text()).not.toContain("12:00");

    // No `place` anchor or `--place-h` token remains; creation hides the
    // card with its `map` anchor (the HudFrame gate and the focus-rescue map).
    expect(wrapper.find('[data-anchor="place"]').exists()).toBe(false);
    const hud = readFileSync(join(APP_ROOT, "components/HudFrame.vue"), "utf8");
    expect(hud).not.toContain('data-anchor="place"');
    expect(hud).toMatch(/\.elosern-stage\[data-elosern-mode="creation"\] \[data-anchor="map"\],/);
    const shell = readFileSync(join(APP_ROOT, "components/AppShell.vue"), "utf8");
    expect(shell).not.toContain("data-anchor='place'");
    expect(shell).toMatch(/creation: "[^"]*\[data-anchor='map'\]/);
    const tokens = readFileSync(join(APP_ROOT, "styles/tokens.css"), "utf8");
    expect(tokens).not.toContain("--place-h");
    const shellCss = readFileSync(join(APP_ROOT, "styles/app-shell.css"), "utf8");
    expect(shellCss).not.toContain("--place-h");
    expect(tokens).toContain("--header-h: calc(48px * var(--ui-scale));");
  });

  describe("room actions (exploration-room-actions)", () => {
    it("renders 查看房間 and 休息 only while actions are enabled", async () => {
      wrapper = mount(PlaceCard, { props: { locationLabel: "石板廣場", timeLabel: "春季 3 日 ‧ 12:00" } });
      expect(wrapper.findAll("button")).toHaveLength(0);
      await wrapper.setProps({ actionsEnabled: true });
      const look = wrapper.get('[data-testid="place-card-look"]');
      const wait = wrapper.get('[data-testid="place-card-wait"]');
      expect(look.attributes("aria-label")).toBe("查看房間");
      expect(look.find("svg").exists()).toBe(true);
      expect(wait.text()).toBe("休息");
      expect(wait.classes()).toContain("place-card__action--wait");
      expect(wrapper.text()).not.toContain("等待");
      expect(wait.find("svg").exists()).toBe(true);
      await wrapper.setProps({ actionsEnabled: false });
      expect(wrapper.element.querySelectorAll(FOCUSABLE)).toHaveLength(0);
    });

    it("emits look-room and wait, and its readout content on hover and focus", async () => {
      wrapper = mount(PlaceCard, { props: { locationLabel: "石板廣場", timeLabel: "t", actionsEnabled: true } });
      await wrapper.get('[data-testid="place-card-look"]').trigger("click");
      await wrapper.get('[data-testid="place-card-wait"]').trigger("click");
      expect(wrapper.emitted("look-room")).toHaveLength(1);
      expect(wrapper.emitted("wait")).toHaveLength(1);
      await wrapper.get('[data-testid="place-card-look"]').trigger("mouseenter");
      await wrapper.get('[data-testid="place-card-look"]').trigger("mouseleave");
      await wrapper.get('[data-testid="place-card-wait"]').trigger("focus");
      expect(wrapper.emitted("hover").map(([content]) => content && content.lead)).toEqual(["查看房間", null, "休息"]);
    });

    it("keeps the heading's full accessible name beside the buttons", () => {
      const long = "伊洛瑟恩王都外城區‧商人公會附屬倉庫的地下儲藏室";
      wrapper = mount(PlaceCard, { props: { locationLabel: long, timeLabel: "t", actionsEnabled: true } });
      const heading = wrapper.get('[data-testid="place-card__location"]');
      expect(heading.text()).toBe(long);
      expect(heading.attributes("title")).toBe(long);
      expect(heading.element.contains(wrapper.get('[data-testid="place-card-look"]').element)).toBe(false);
    });
  });

  // place-card-instrument-panel (design D5): the card wears the shared
  // instrument-panel chrome, its actions have no chrome, and a new location
  // enters from the column's anchored (right) edge.
  describe("instrument panel (place-card-instrument-panel)", () => {
    const placeCardSource = () => readFileSync(join(APP_ROOT, "components/PlaceCard.vue"), "utf8");
    const panelSource = () => readFileSync(join(APP_ROOT, "components/instrument-panel.css"), "utf8");

    it("wears the shared instrument panel chrome instead of the island box", () => {
      wrapper = mount(PlaceCard, { props: { locationLabel: "石板廣場", timeLabel: "春季 3 日 ‧ 12:00" } });
      expect(wrapper.classes()).toEqual(expect.arrayContaining(["place-card", "instrument-panel"]));

      const source = placeCardSource();
      expect(source).toContain('import "./instrument-panel.css";');
      const card = rule(source, ".place-card");
      expect(card).not.toBe("");
      for (const property of ["padding", "background", "backdrop-filter", "border", "border-radius", "box-shadow"]) {
        expect(card).not.toContain(property);
      }

      const panel = panelSource();
      const ground = rule(panel, ".instrument-panel::before");
      expect(ground).toContain("background: var(--panel);");
      expect(ground).toContain("backdrop-filter: blur(calc(9px * var(--ui-scale)));");
      expect(ground).toContain("mask-image:");
      expect(ground).toContain("pointer-events: none;");
      const fitting = rule(panel, ".instrument-panel::after");
      expect(fitting).toContain("var(--band-ornament) right 0 top 0");
      expect(fitting).toContain("right calc(14px * var(--ui-scale))");
      expect(fitting).toContain("pointer-events: none;");
      expect(rule(panel, ".instrument-panel")).toContain("calc(var(--instrument-pad-right, 26px) * var(--ui-scale))");
      expect(panel).not.toContain("border:");
      expect(panel).not.toContain("border-radius");
      expect(panel).not.toContain("box-shadow");

      const shellCss = readFileSync(join(APP_ROOT, "styles/app-shell.css"), "utf8");
      expect(shellCss).not.toMatch(/\.place-card\b/);
    });

    it("sets the room actions without chrome and marks only the active one", () => {
      wrapper = mount(PlaceCard, { props: { locationLabel: "石板廣場", timeLabel: "t", actionsEnabled: true } });
      const source = placeCardSource();
      const action = rule(source, ".place-card__action");
      for (const declaration of [
        "border: 0;",
        "background: none;",
        "height: calc(30px * var(--ui-scale));",
        "min-width: calc(30px * var(--ui-scale));",
        "opacity: 0.86;",
      ]) {
        expect(action).toContain(declaration);
      }
      const tick = rule(source, ".place-card__action::after");
      expect(tick).toContain("opacity: 0;");
      expect(tick).toContain("background: var(--gold-500);");
      expect(source).toContain(
        ".place-card__action:hover::after,\n.place-card__action:focus-visible::after {\n  opacity: 1;",
      );
      expect(wrapper.get('[data-testid="place-card-wait"]').text()).toBe("休息");
    });

    it("slides a new location in from the right", () => {
      const enter = rule(placeCardSource(), ".place-card-enter-from");
      expect(enter).toContain("transform: translateX(calc(var(--motion-shift-lg) * var(--motion-travel)));");
      expect(enter).not.toContain("-1 *");
    });
  });
});

// The text of the first rule that opens with `selector {` at the start of a
// line, up to the next `}` (built like hud_frame.test.js's extractRule).
function rule(source, selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = new RegExp(`(?:^|\\n)${escaped}\\s*\\{[^}]*\\}`).exec(source);
  return match ? match[0] : "";
}
