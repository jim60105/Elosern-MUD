// webclient-avg-place-card-top-bar (design D3/D4): the stage's place card
// states the location and the world time — the only surface that does — in
// the fixed-height `place` anchor, display-only, hidden in creation.
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
      props: { locationLabel: "測試起點", timeLabel: "春季 3 日 · 12:00" },
    });
    const heading = wrapper.get('[data-testid="place-card__location"]');
    expect(heading.element.tagName).toBe("H1");
    expect(heading.text()).toBe("測試起點");
    expect(wrapper.get('[data-testid="place-card__time"]').text()).toBe("春季 3 日 · 12:00");
  });

  it("falls back to its placeholders when nothing is committed", () => {
    wrapper = mount(PlaceCard, { props: { locationLabel: null, timeLabel: null } });
    expect(wrapper.get('[data-testid="place-card__location"]').text()).toBe("位置：--");
    expect(wrapper.get('[data-testid="place-card__time"]').text()).toBe("時間：--");
  });

  it("keeps an overlong label whole for assistive technology and holds no tab stop", () => {
    const long = "伊洛瑟恩王都外城區・商人公會附屬倉庫的地下儲藏室";
    wrapper = mount(PlaceCard, { props: { locationLabel: long, timeLabel: "秋季 28 日 · 23:59" } });
    const heading = wrapper.get('[data-testid="place-card__location"]');
    expect(heading.text()).toBe(long);
    expect(heading.attributes("title")).toBe(long);
    expect(wrapper.element.querySelectorAll(FOCUSABLE)).toHaveLength(0);
    // The truncation is CSS (ellipsis inside a fixed-height anchor), never
    // a shortened string.
    const css = readFileSync(join(APP_ROOT, "components/PlaceCard.vue"), "utf8");
    expect(css).toContain("text-overflow: ellipsis");
    expect(css).toContain("height: 100%");
  });

  it("renders inside AppShell's place anchor from the labels AppShell receives, hidden in creation", () => {
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    wrapper = mount(AppShell, {
      attachTo: host,
      props: { mode: "exploration", locationLabel: "石板廣場", timeLabel: "春季 3 日 · 12:00" },
    });
    const card = wrapper.get('[data-testid="anchor-place"] [data-testid="place-card"]');
    expect(card.get('[data-testid="place-card__location"]').text()).toBe("石板廣場");
    expect(card.get('[data-testid="place-card__time"]').text()).toBe("春季 3 日 · 12:00");
    // The top band states neither value.
    expect(wrapper.get('[data-testid="topbar"]').text()).not.toContain("石板廣場");
    expect(wrapper.get('[data-testid="topbar"]').text()).not.toContain("12:00");

    // Creation hides the anchor with display:none (the HudFrame gate) and
    // the shell's focus-rescue map names it.
    const hud = readFileSync(join(APP_ROOT, "components/HudFrame.vue"), "utf8");
    expect(hud).toMatch(/\.elosern-stage\[data-elosern-mode="creation"\] \[data-anchor="place"\],/);
    const shell = readFileSync(join(APP_ROOT, "components/AppShell.vue"), "utf8");
    expect(shell).toMatch(/creation: "\[data-anchor='place'\]/);
    const tokens = readFileSync(join(APP_ROOT, "styles/tokens.css"), "utf8");
    expect(tokens).toContain("--place-h: 68px;");
    expect(tokens).toContain("--header-h: 48px;");
  });
});
