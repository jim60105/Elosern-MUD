// webclient-avg-place-card-top-bar (design D3); place-card-relocation (design
// D2): the stage's place card states the location and the world time — the
// only surface that does — at the head of the `map` anchor, content-sized,
// display-only, hidden in creation.
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
});
