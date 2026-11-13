// The gallery wall (change gallery-wall-component): its pure placement
// helpers, the committed groups as aspect-true tiles, the inline tray, the
// tray's state marks and the two roving listboxes. Synthetic groups only:
// no shipped character, monster or category data.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { nextTick } from "vue";

import GalleryWall from "../../components/GalleryWall.vue";
import {
  GENERATE_TILE,
  tileShape,
  trayInsertIndex,
  trayItems,
  trayOpen,
  wallTiles,
} from "../../components/gallery-window-model.js";

const subject = (key, changes = {}) => ({
  subject_key: `portrait:character:${key}`,
  kind: "portrait:character",
  display_name: `name-${key}`,
  is_current: false,
  card_count: 1,
  artwork: null,
  ...changes,
});

const group = (key, subjects, changes = {}) => ({
  key, label: null, seen: null, total: null, expanded: true, count: subjects.length, subjects, ...changes,
});

const card = (id, changes = {}) => ({
  image_id: id,
  status: "card",
  label: `label-${id}`,
  artwork: null,
  is_default: false,
  chips: [],
  requested_fields: [],
  binding_present: false,
  created_at: null,
  ...changes,
});

const official = (identity) => ({ identity, artwork: null, is_current: false, is_catalog_default: false });

const MANY = { max_cards: null };
const ONE = { max_cards: 1 };

describe("gallery window model helpers", () => {
  it("places the tray after the last tile of the owner's row", () => {
    expect(trayInsertIndex(1, 4, 10)).toBe(3);
    expect(trayInsertIndex(0, 4, 10)).toBe(3);
    expect(trayInsertIndex(3, 4, 10)).toBe(3);
    expect(trayInsertIndex(4, 4, 10)).toBe(7);
    expect(trayInsertIndex(9, 4, 10)).toBe(9);
    // A short last row ends at the group's last tile.
    expect(trayInsertIndex(8, 4, 10)).toBe(9);
    expect(trayInsertIndex(1, 4, 2)).toBe(1);
    // One column: the tray follows the owner itself.
    expect(trayInsertIndex(2, 1, 5)).toBe(2);
  });

  it("draws scenes as landscape tiles and every other kind as portrait", () => {
    expect(tileShape("scene")).toBe("landscape");
    expect(tileShape("portrait:character")).toBe("portrait");
    expect(tileShape("portrait:monster")).toBe("portrait");
  });

  it("opens a tray only for capabilities allowing more than one card", () => {
    expect(trayOpen(null)).toBe(false);
    expect(trayOpen({ max_cards: 1 })).toBe(false);
    expect(trayOpen({ max_cards: null })).toBe(true);
  });

  it("lists wall tiles in reading order across expanded groups only", () => {
    const a = subject("a");
    const b = subject("b");
    const c = subject("c");
    const tiles = wallTiles([
      group("g1", [a, b]),
      group("g2", [], { expanded: false, count: 4, label: "x" }),
      group("g3", [c]),
    ]);
    expect(tiles.map((tile) => [tile.groupKey, tile.subject.subject_key])).toEqual([
      ["g1", a.subject_key], ["g1", b.subject_key], ["g3", c.subject_key],
    ]);
  });

  it("orders tray items as cards, the generate tile, then officials", () => {
    const items = trayItems([card("c1"), card("c2")], [official("o/a/b.webp")]);
    expect(items.map((item) => [item.kind, item.id])).toEqual([
      ["card", "c1"], ["card", "c2"], ["generate", GENERATE_TILE], ["official", "o/a/b.webp"],
    ]);
  });
});

describe("GalleryWall (webclient-gallery-wall)", () => {
  let wrapper;

  afterEach(() => {
    vi.restoreAllMocks();
    wrapper?.unmount();
    wrapper = undefined;
    document.body.innerHTML = "";
  });

  // jsdom does not resolve `repeat(auto-fill, ...)`, so a test that depends
  // on the measured column count stubs the grid's computed tracks.
  function stubColumns(count) {
    const real = window.getComputedStyle.bind(window);
    vi.spyOn(window, "getComputedStyle").mockImplementation((el) =>
      el.classList?.contains("gwall__grid")
        ? { gridTemplateColumns: Array(count).fill("100px").join(" ") }
        : real(el),
    );
  }

  async function mountWall(props = {}) {
    wrapper = mount(GalleryWall, {
      attachTo: document.body,
      props: { groups: [], ariaLabel: "wall", ...props },
    });
    await flushPromises();
    await nextTick();
    return wrapper;
  }

  const tiles = () => wrapper.findAll('[data-testid="gallery-subject"]');
  const tile = (key) => wrapper.get(`[data-subject-key="portrait:character:${key}"]`);
  const tray = () => wrapper.find('[data-testid="gallery-tray"]');
  const trayTiles = () => wrapper.findAll('[data-testid="gallery-tray-item"]');

  async function press(target, key) {
    const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true });
    target.element.dispatchEvent(event);
    await nextTick();
    await nextTick();
    return event;
  }

  describe("committed groups as aspect-true subject tiles", () => {
    it("starts an unlabeled group with its tiles and no heading", async () => {
      await mountWall({ groups: [group("g", [subject("a"), subject("b"), subject("c")])] });
      expect(tiles()).toHaveLength(3);
      expect(wrapper.find("h3").exists()).toBe(false);
    });

    it("carries a tier heading's label and seen / total", async () => {
      await mountWall({ groups: [group("g", [subject("a")], { label: "t_low", seen: 1, total: 2 })] });
      const heading = wrapper.get("h3");
      expect(heading.text()).toContain("t_low");
      expect(heading.text().replace(/\s+/g, " ")).toContain("1 / 2");
    });

    it("shows only the heading and count of a collapsed group", async () => {
      await mountWall({
        groups: [
          group("open", [subject("a")]),
          group("closed", [], { label: "t_place", expanded: false, count: 7 }),
        ],
      });
      const sections = wrapper.findAll('[role="group"]');
      const closed = sections.find((section) => section.text().includes("t_place"));
      expect(closed.get("h3").text()).toContain("7");
      expect(closed.findAll('[data-testid="gallery-subject"]')).toHaveLength(0);
      expect(tiles()).toHaveLength(1);
    });

    it("marks the live character by visible text and in its accessible name", async () => {
      await mountWall({ groups: [group("g", [subject("a", { is_current: true }), subject("b")])] });
      expect(tile("a").text()).toContain("操作中");
      expect(tile("a").attributes("aria-label")).toContain("操作中");
      expect(tile("b").text()).not.toContain("操作中");
    });

    it("shows an image count only above one and sizes tiles by shape", async () => {
      await mountWall({
        groups: [group("g", [
          subject("a", { card_count: 3 }),
          subject("b", { card_count: 1 }),
          { ...subject("s"), subject_key: "scene:s", kind: "scene" },
        ])],
      });
      expect(tile("a").find(".gtile__count").text()).toBe("3");
      expect(tile("a").attributes("aria-label")).toContain("3");
      expect(tile("b").find(".gtile__count").exists()).toBe(false);
      expect(tile("a").classes()).toContain("gtile--portrait");
      expect(wrapper.get('[data-subject-key="scene:s"]').classes()).toContain("gtile--landscape");
    });
  });

  describe("the tray under the owner's row", () => {
    it("follows the last tile of the owner's row in a four-column wall", async () => {
      stubColumns(4);
      const subjects = ["a", "b", "c", "d", "e", "f"].map((key) => subject(key));
      await mountWall({
        groups: [group("g", subjects)],
        selectedSubject: subjects[1].subject_key,
        capabilities: MANY,
        cards: [card("c1")],
      });
      const trayEl = tray().element;
      const follows = (key) => Boolean(tile(key).element.compareDocumentPosition(trayEl) & Node.DOCUMENT_POSITION_FOLLOWING);
      // The tray comes after the fourth tile and before the fifth.
      expect(follows("d")).toBe(true);
      expect(follows("e")).toBe(false);
      const ordered = [...wrapper.element.querySelectorAll('[data-testid="gallery-subject"], [data-testid="gallery-tray"]')];
      expect(ordered.indexOf(trayEl)).toBe(4);
      expect(tile("b").attributes("aria-expanded")).toBe("true");
      expect(tile("b").attributes("aria-controls")).toBe(trayEl.id);
      // The wall listbox still owns every tile, the ones after the tray too.
      const wall = wrapper.get('[role="listbox"][aria-label="wall"]');
      const owned = wall.attributes("aria-owns").split(" ").map((id) => document.getElementById(id));
      expect(owned.some((el) => el.contains(tile("e").element))).toBe(true);
      expect(wall.element.contains(trayEl)).toBe(false);
    });

    it("needs no adopted run when the owner sits on the last row", async () => {
      stubColumns(4);
      const subjects = ["a", "b", "c", "d", "e"].map((key) => subject(key));
      await mountWall({
        groups: [group("g", subjects), group("h", [subject("f")], { label: "next" })],
        selectedSubject: subjects[4].subject_key,
        capabilities: MANY,
      });
      const wall = wrapper.get('[role="listbox"][aria-label="wall"]');
      // The later group is adopted; the owner's own group is not split.
      const owned = wall.attributes("aria-owns").split(" ").map((id) => document.getElementById(id));
      expect(owned).toHaveLength(1);
      expect(owned[0].contains(tile("f").element)).toBe(true);
      expect(wall.element.contains(tile("e").element)).toBe(true);
      await wrapper.setProps({ groups: [group("g", subjects)] });
      await flushPromises();
      expect(wrapper.get('[role="listbox"][aria-label="wall"]').attributes("aria-owns")).toBeUndefined();
    });

    it("opens no tray for a one-card subject", async () => {
      await mountWall({
        groups: [group("g", [subject("a"), subject("b")])],
        selectedSubject: subject("a").subject_key,
        capabilities: ONE,
      });
      expect(tray().exists()).toBe(false);
      expect(tile("a").attributes("aria-expanded")).toBeUndefined();
    });

    it("lists the cards, then 生成新圖, then the official run", async () => {
      await mountWall({
        groups: [group("g", [subject("a", { card_count: 2 })])],
        selectedSubject: subject("a").subject_key,
        capabilities: MANY,
        cards: [card("c1"), card("c2")],
        officialEntries: [official("preset/x/one.webp")],
      });
      expect(trayTiles().map((item) => item.attributes("data-item-kind"))).toEqual(["card", "card", "generate", "official"]);
      expect(trayTiles()[2].text()).toContain("生成新圖");
      const run = wrapper.get('[data-testid="gallery-tray-official"]');
      expect(run.attributes("aria-label")).toBe("官方圖片（唯讀）");
      expect(run.findAll('[data-testid="gallery-tray-item"]')).toHaveLength(1);
      expect(tray().attributes("aria-label")).toBe("name-a的圖片");
    });

    it("scrolls an opening tray smoothly at full motion, and only on opening", async () => {
      const scroll = vi.fn();
      Element.prototype.scrollIntoView = scroll;
      try {
        await mountWall({
          groups: [group("g", [subject("a"), subject("b")])],
          selectedSubject: subject("a").subject_key,
          capabilities: MANY,
        });
        expect(scroll).toHaveBeenCalledTimes(1);
        expect(scroll).toHaveBeenLastCalledWith({ block: "nearest", behavior: "smooth" });
        // A re-measure (a new commit of the same owner) does not scroll.
        await wrapper.setProps({ groups: [group("g", [subject("a"), subject("b")])] });
        await flushPromises();
        expect(scroll).toHaveBeenCalledTimes(1);
        await wrapper.setProps({ selectedSubject: subject("b").subject_key });
        await flushPromises();
        expect(scroll).toHaveBeenCalledTimes(2);
      } finally {
        delete Element.prototype.scrollIntoView;
      }
    });

    it.each([
      ["the reduced-motion media query", () => { window.matchMedia = () => ({ matches: true }); }],
      ["the off motion level", () => { document.documentElement.dataset.motion = "off"; }],
    ])("scrolls without motion under %s", async (_name, arrange) => {
      const scroll = vi.fn();
      Element.prototype.scrollIntoView = scroll;
      const media = window.matchMedia;
      arrange();
      try {
        await mountWall({
          groups: [group("g", [subject("a")])],
          selectedSubject: subject("a").subject_key,
          capabilities: MANY,
        });
        expect(scroll).toHaveBeenCalledWith({ block: "nearest", behavior: "auto" });
      } finally {
        window.matchMedia = media;
        delete document.documentElement.dataset.motion;
        delete Element.prototype.scrollIntoView;
      }
    });

    it("scrolls an opening tray into view without motion when reduced motion is set", async () => {
      document.documentElement.dataset.motion = "reduced";
      const scroll = vi.fn();
      Element.prototype.scrollIntoView = scroll;
      try {
        await mountWall({
          groups: [group("g", [subject("a")])],
          selectedSubject: subject("a").subject_key,
          capabilities: MANY,
        });
        expect(scroll).toHaveBeenCalledWith({ block: "nearest", behavior: "auto" });
      } finally {
        delete document.documentElement.dataset.motion;
        delete Element.prototype.scrollIntoView;
      }
    });
  });

  describe("tray tiles carry state by shape and text", () => {
    it("marks default, pending and failed tiles with text and a shape", async () => {
      await mountWall({
        groups: [group("g", [subject("a")])],
        selectedSubject: subject("a").subject_key,
        capabilities: MANY,
        cards: [
          card("c1", { is_default: true }),
          card("c2", { status: "pending" }),
          card("c3", { status: "failed" }),
        ],
      });
      const [first, second, third] = trayTiles();
      expect(first.text()).toContain("預設");
      expect(first.find('[data-mark="crown"]').exists()).toBe(true);
      expect(second.text()).toContain("生成中");
      expect(second.find('[data-mark="spinner"]').exists()).toBe(true);
      expect(third.text()).toContain("生成失敗");
      expect(third.find('[data-mark="warning"]').exists()).toBe(true);
    });
  });

  describe("two roving listboxes", () => {
    const FOUR = () => [group("g1", [subject("a"), subject("b")]), group("g2", [subject("c"), subject("d")], { label: "x" })];

    it("moves focus, not selection, with ArrowRight, End and Home", async () => {
      await mountWall({ groups: FOUR() });
      tile("a").element.focus();
      await press(tile("a"), "ArrowRight");
      expect(document.activeElement).toBe(tile("b").element);
      await press(tile("b"), "End");
      expect(document.activeElement).toBe(tile("d").element);
      await press(tile("d"), "Home");
      expect(document.activeElement).toBe(tile("a").element);
      expect(wrapper.emitted("select-subject")).toBeUndefined();
      expect(tiles().filter((el) => el.attributes("tabindex") === "0")).toHaveLength(1);
    });

    it("selects once on Enter", async () => {
      await mountWall({ groups: FOUR() });
      tile("a").element.focus();
      await press(tile("a"), "ArrowRight");
      await press(tile("b"), "Enter");
      expect(wrapper.emitted("select-subject")).toEqual([[subject("b").subject_key]]);
    });

    it("returns Escape in the tray to the owner without propagating", async () => {
      const outer = vi.fn();
      document.body.addEventListener("keydown", outer);
      try {
        await mountWall({
          groups: [group("g", [subject("a"), subject("b")])],
          selectedSubject: subject("a").subject_key,
          capabilities: MANY,
          cards: [card("c1")],
        });
        const first = trayTiles()[0];
        first.element.focus();
        const event = await press(first, "Escape");
        expect(document.activeElement).toBe(tile("a").element);
        expect(event.defaultPrevented).toBe(true);
        expect(outer).not.toHaveBeenCalled();
        expect(tray().exists()).toBe(true);
      } finally {
        document.body.removeEventListener("keydown", outer);
      }
    });

    it("walks the tray in order and activates its tiles", async () => {
      await mountWall({
        groups: [group("g", [subject("a")])],
        selectedSubject: subject("a").subject_key,
        capabilities: MANY,
        cards: [card("c1")],
        officialEntries: [official("preset/x/one.webp")],
        selectedImage: GENERATE_TILE,
      });
      const generate = trayTiles()[1];
      expect(generate.attributes("tabindex")).toBe("0");
      expect(generate.attributes("aria-selected")).toBe("true");
      generate.element.focus();
      await press(generate, "Enter");
      expect(wrapper.emitted("generate")).toHaveLength(1);
      await press(generate, "ArrowRight");
      expect(document.activeElement).toBe(trayTiles()[2].element);
      await press(trayTiles()[2], " ");
      await press(trayTiles()[2], "Home");
      expect(document.activeElement).toBe(trayTiles()[0].element);
      await trayTiles()[0].trigger("click");
      expect(wrapper.emitted("select-image")).toEqual([["preset/x/one.webp"], ["c1"]]);
      expect(wrapper.emitted("select-subject")).toBeUndefined();
    });

    it("reports focus loss once when a new commit drops the focused tile", async () => {
      await mountWall({ groups: FOUR() });
      tile("c").element.focus();
      await wrapper.setProps({ groups: [group("g1", [subject("a"), subject("b")])] });
      await nextTick();
      expect(wrapper.emitted("focus-lost")).toHaveLength(1);
      await wrapper.setProps({ groups: [group("g1", [subject("a")])] });
      await nextTick();
      expect(wrapper.emitted("focus-lost")).toHaveLength(1);
    });

    it("reports focus loss when the focused tray's owner leaves the wall", async () => {
      await mountWall({
        groups: [group("g", [subject("a"), subject("b")])],
        selectedSubject: subject("a").subject_key,
        capabilities: MANY,
        cards: [card("c1")],
      });
      trayTiles()[0].element.focus();
      await wrapper.setProps({ groups: [group("g", [subject("b")])], selectedSubject: subject("b").subject_key });
      await nextTick();
      expect(wrapper.emitted("focus-lost")).toHaveLength(1);
    });

    it("steps ArrowDown and ArrowUp by the measured columns across the tray", async () => {
      stubColumns(2);
      const subjects = ["a", "b", "c", "d", "e"].map((key) => subject(key));
      await mountWall({
        groups: [group("g", subjects)],
        selectedSubject: subjects[0].subject_key,
        capabilities: MANY,
      });
      tile("b").element.focus();
      await press(tile("b"), "ArrowDown");
      expect(document.activeElement).toBe(tile("d").element);
      await press(tile("d"), "ArrowDown");
      expect(document.activeElement).toBe(tile("e").element);
      await press(tile("e"), "ArrowUp");
      expect(document.activeElement).toBe(tile("c").element);
      await press(tile("c"), "ArrowUp");
      expect(document.activeElement).toBe(tile("a").element);
      expect(wrapper.emitted("select-subject")).toBeUndefined();
    });

    it("keeps focus on a tile that the new selection moves across the tray", async () => {
      stubColumns(2);
      const subjects = ["a", "b", "c", "d", "e"].map((key) => subject(key));
      await mountWall({
        groups: [group("g", subjects)],
        selectedSubject: subjects[0].subject_key,
        capabilities: MANY,
      });
      tile("e").element.focus();
      await press(tile("e"), "Enter");
      await wrapper.setProps({ selectedSubject: subjects[4].subject_key });
      await flushPromises();
      expect(document.activeElement).toBe(tile("e").element);
      expect(tile("e").attributes("aria-expanded")).toBe("true");
    });

    it("moves focus within the tray when the focused card leaves it", async () => {
      await mountWall({
        groups: [group("g", [subject("a")])],
        selectedSubject: subject("a").subject_key,
        capabilities: MANY,
        cards: [card("c1"), card("c2")],
      });
      trayTiles()[1].element.focus();
      await wrapper.setProps({ cards: [card("c1")] });
      await flushPromises();
      expect(tray().element.contains(document.activeElement)).toBe(true);
    });

    it("returns the wall's tab stop to the selected tile once focus leaves", async () => {
      const hasFocus = vi.spyOn(document, "hasFocus").mockReturnValue(true);
      await mountWall({
        groups: [group("g", [subject("a"), subject("b"), subject("c")])],
        selectedSubject: subject("a").subject_key,
        capabilities: MANY,
      });
      tile("a").element.focus();
      await press(tile("a"), "End");
      expect(tile("c").attributes("tabindex")).toBe("0");
      trayTiles()[0].element.focus();
      await nextTick();
      expect(tile("a").attributes("tabindex")).toBe("0");
      expect(tile("c").attributes("tabindex")).toBe("-1");
      // A window blur keeps the stop where focus left it.
      tile("a").element.focus();
      await press(tile("a"), "End");
      hasFocus.mockReturnValue(false);
      tile("c").element.dispatchEvent(new FocusEvent("focusout", { bubbles: true, relatedTarget: null }));
      await nextTick();
      expect(tile("c").attributes("tabindex")).toBe("0");
    });

    it("keeps a still-listed focused tile without reporting a loss", async () => {
      await mountWall({ groups: FOUR() });
      tile("a").element.focus();
      await wrapper.setProps({ groups: [group("g1", [subject("a")])] });
      await nextTick();
      expect(wrapper.emitted("focus-lost")).toBeUndefined();
    });
  });
});

// The wall's sizing and motion rules, as for the window primitives: every
// size is `calc(<n>px * var(--ui-scale))` or a token, text uses `--text-*`
// tokens (none below `--text-xs`), and durations use `--motion-*`.
describe("GalleryWall styles", () => {
  const APP_ROOT = join(process.cwd(), "web/webclient-app");
  const source = readFileSync(join(APP_ROOT, "components/GalleryWall.vue"), "utf8");
  const css = [...source.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)]
    .map((match) => match[1]).join("\n").replace(/\/\*[\s\S]*?\*\//g, "");
  const SCALED_PX = /calc\(\s*-?\d*\.?\d+px\s*\*\s*var\(--ui-scale\)\s*\)/g;
  const TEXT_TOKENS = ["--text-xs", "--text-sm", "--text-md", "--text-base", "--text-lg", "--text-xl", "--text-2xl", "--text-3xl", "--text-4xl"];

  it("has a scoped style block", () => {
    expect(source).toMatch(/<style scoped>/);
  });

  it("writes no raw pixel size", () => {
    const rest = css.replace(SCALED_PX, "SCALED");
    expect(rest.match(/-?\d*\.?\d+px\b/g) ?? []).toEqual([]);
    expect(rest.match(/\d(pt|rem|vh|vw)\b/g) ?? []).toEqual([]);
  });

  it("sizes text only through --text-* tokens", () => {
    const declarations = [...css.matchAll(/(?:^|[;{\s])(font-size|font)\s*:\s*([^;}]+)/g)];
    expect(declarations.length).toBeGreaterThan(0);
    for (const [, property, value] of declarations) {
      const tokens = [...value.matchAll(/var\((--text-[a-z0-9]+)\)/g)].map((match) => match[1]);
      expect(tokens, `${property}: ${value}`).toHaveLength(1);
      expect(TEXT_TOKENS).toContain(tokens[0]);
      expect(value).not.toMatch(/calc\([^)]*--text-/);
    }
  });

  it("names every duration through a --motion-* token", () => {
    for (const [, value] of css.matchAll(/(?:transition|animation)[a-z-]*\s*:\s*([^;}]+)/g)) {
      expect(value, value).not.toMatch(/(?<![\w-])\d*\.?\d+m?s\b/);
      if (value.trim() !== "none") expect(value).toMatch(/var\(--motion-[a-z-]+\)/);
    }
  });

  it("puts no inline style sizes in its template", () => {
    const template = source.replace(/<script[\s\S]*?<\/script>/g, "").replace(/<style[\s\S]*?<\/style>/g, "");
    expect(template).not.toMatch(/\sstyle=/);
    expect(template).not.toMatch(/\s(width|height)="\d+"/);
  });
});
