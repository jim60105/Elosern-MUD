// The gallery window (change gallery-window-component): the category rail,
// the footer press mapping, client-local image selection and the focus and
// Escape layers. Synthetic v4 fixtures, a fake `dispatch` that records every
// call, and committed panels simulated through `setProps`. The tests assert
// the window's rules only, never shipped data.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";

import GalleryWindow from "../../components/GalleryWindow.vue";
import { initialImage } from "../../components/gallery-window-model.js";
import {
  GALLERY_V4_MINE,
  GALLERY_V4_MINE_BLANK,
  GALLERY_V4_MONSTER,
  GALLERY_V4_PARTY,
} from "../../stories/gallery-fixtures-v4.js";

const wrappers = [];

function mountWindow(props = {}) {
  let count = 0;
  const dispatch = props.dispatch ?? vi.fn(() => `request:${(count += 1)}`);
  const wrapper = mount(GalleryWindow, {
    props: { model: structuredClone(GALLERY_V4_MINE), dispatch, ...props },
    attachTo: document.body,
  });
  wrappers.push(wrapper);
  return { wrapper, dispatch };
}

afterEach(() => {
  wrappers.reverse().forEach((wrapper) => wrapper.unmount());
  wrappers.length = 0;
  document.body.replaceChildren();
});

const tab = (key) => document.querySelector(`[data-testid="icon-tabs__tab--${key}"]`);
const wallKeys = () => [...document.querySelectorAll('[data-testid="gallery-subject"]')].map((el) => el.dataset.subjectKey);
const trayItem = (id) => document.querySelector(`[data-testid="gallery-tray-item"][data-item-id="${id}"]`);
const footerButton = (key) => document.querySelector(`[data-testid="gallery-page__${key}"]`);
const pageSelection = () => document.querySelector('[data-testid="gallery-page"]')?.dataset.selection ?? null;
async function click(el) {
  el.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  await flushPromises();
}

async function key(el, name) {
  el.dispatchEvent(new KeyboardEvent("keydown", { key: name, bubbles: true, cancelable: true }));
  await flushPromises();
}

function withCards(model, cards) {
  return { ...structuredClone(model), cards: structuredClone(cards) };
}

describe("initialImage (the selection rule)", () => {
  const row = (id, changes = {}) => ({ image_id: id, is_default: false, ...changes });
  const entry = (identity, changes = {}) => ({ identity, is_current: false, ...changes });

  it("prefers the default card, then the first card, then the current and first official entry", () => {
    expect(initialImage([row("a"), row("b", { is_default: true })], [entry("o")])).toBe("b");
    expect(initialImage([row("a"), row("b")], [entry("o")])).toBe("a");
    expect(initialImage([], [entry("o1"), entry("o2", { is_current: true })])).toBe("o2");
    expect(initialImage([], [entry("o1"), entry("o2")])).toBe("o1");
    expect(initialImage([], [])).toBeNull();
    expect(initialImage(null, undefined)).toBeNull();
  });
});

describe("the rail switches category through the server", () => {
  it("marks the pressed tab before the commit and keeps the committed wall", async () => {
    const { wrapper, dispatch } = mountWindow();
    const mine = wallKeys();
    await click(tab("monster"));
    expect(dispatch).toHaveBeenCalledExactlyOnceWith("gallery.category.select", { category: "monster" });
    expect(tab("monster").getAttribute("aria-selected")).toBe("true");
    expect(tab("mine").getAttribute("aria-selected")).toBe("false");
    expect(wallKeys()).toEqual(mine);

    await wrapper.setProps({ model: structuredClone(GALLERY_V4_MONSTER) });
    await flushPromises();
    expect(wallKeys()).toEqual(GALLERY_V4_MONSTER.groups.flatMap((group) => group.subjects.map((subject) => subject.subject_key)));
    expect(tab("monster").getAttribute("aria-selected")).toBe("true");
  });

  it("drops the pressed mark on the next committed panel, whatever its category", async () => {
    const { wrapper } = mountWindow();
    await click(tab("monster"));
    await wrapper.setProps({ model: structuredClone(GALLERY_V4_MINE) });
    await flushPromises();
    expect(tab("mine").getAttribute("aria-selected")).toBe("true");
    expect(tab("monster").getAttribute("aria-selected")).toBe("false");
  });

  it("drops the pressed mark when the request is rejected and shows the feedback line", async () => {
    const { wrapper } = mountWindow();
    await click(tab("monster"));
    await wrapper.setProps({ result: { requestId: "request:1", outcome: "rejected" } });
    await flushPromises();
    expect(tab("mine").getAttribute("aria-selected")).toBe("true");
    const feedback = document.querySelector('[data-testid="gallery-window__feedback"]');
    expect(feedback.textContent).toContain("操作未完成");
    await click(feedback.querySelector("button"));
    expect(wrapper.emitted("log")).toHaveLength(1);
  });

  it("marks nothing when the dispatch sends nothing", async () => {
    const { dispatch } = mountWindow({ dispatch: vi.fn(() => null) });
    await click(tab("monster"));
    expect(dispatch).toHaveBeenCalledOnce();
    expect(tab("mine").getAttribute("aria-selected")).toBe("true");
  });

  it("sends nothing from a disabled tab and exposes its committed reason", async () => {
    const { dispatch } = mountWindow();
    const people = tab("people");
    await click(people);
    people.focus();
    await key(people, "Enter");
    expect(dispatch).not.toHaveBeenCalled();
    expect(people.getAttribute("aria-disabled")).toBe("true");
    const reason = GALLERY_V4_MINE.categories.find((row) => row.key === "people").reason;
    expect(document.getElementById(people.getAttribute("aria-describedby")).textContent).toBe(reason);
  });

  it("sends nothing for the committed category", async () => {
    const { dispatch } = mountWindow();
    await click(tab("mine"));
    expect(dispatch).not.toHaveBeenCalled();
  });
});

describe("footer presses map to one action or one editor", () => {
  const STORED = GALLERY_V4_MINE.cards[1];

  it("sends one gallery.default.set with the subject key and the card's image_id", async () => {
    const { dispatch } = mountWindow();
    await click(trayItem(STORED.image_id));
    await click(footerButton("default"));
    expect(dispatch).toHaveBeenCalledExactlyOnceWith("gallery.default.set", {
      subject_key: GALLERY_V4_MINE.selected,
      image_id: STORED.image_id,
    });
  });

  it("sends no second action while one is in flight", async () => {
    const { dispatch } = mountWindow();
    await click(trayItem(STORED.image_id));
    await click(footerButton("default"));
    await click(footerButton("default"));
    expect(dispatch).toHaveBeenCalledOnce();
  });

  it("sends nothing while the host gate is locked", async () => {
    const { dispatch } = mountWindow({ disabled: true });
    await click(trayItem(STORED.image_id));
    await click(footerButton("default"));
    await click(tab("monster"));
    expect(dispatch).not.toHaveBeenCalled();
  });

  it("opens the generate drawer for 重新生成 and sends nothing until it is submitted", async () => {
    const { dispatch } = mountWindow({ model: structuredClone(GALLERY_V4_MONSTER) });
    await click(footerButton("regenerate"));
    expect(document.querySelector('[data-drawer-key="gallery-generate"]')).not.toBeNull();
    expect(dispatch).not.toHaveBeenCalled();
  });

  it("maps the official keys to their actions", async () => {
    const model = withCards(GALLERY_V4_MINE, []);
    const { wrapper, dispatch } = mountWindow({ model });
    const current = model.official_entries.find((row) => row.is_current);
    expect(pageSelection()).toBe("official");
    await click(footerButton("official-clear-selection"));
    expect(dispatch).toHaveBeenLastCalledWith("gallery.official.clear_selection", {
      subject_key: model.selected, identity: current.identity,
    });
    await wrapper.setProps({ result: { requestId: "request:1", outcome: "rejected" } });
    await click(footerButton("official-geometry-clear"));
    expect(dispatch).toHaveBeenLastCalledWith("gallery.official.geometry.clear", {
      subject_key: model.selected, identity: current.identity,
    });
  });

  it("closes an editor on Escape without closing the window", async () => {
    const { wrapper } = mountWindow();
    await click(trayItem(STORED.image_id));
    await click(footerButton("face"));
    const modal = document.querySelector('[aria-label="臉部框選"]');
    expect(modal).not.toBeNull();
    await key(modal, "Escape");
    expect(document.querySelector('[aria-label="臉部框選"]')).toBeNull();
    expect(wrapper.emitted("close")).toBeUndefined();
  });
});

describe("image selection is client-local and follows the committed subject", () => {
  it("opens a new subject on its default card", async () => {
    const { wrapper } = mountWindow({ model: structuredClone(GALLERY_V4_PARTY) });
    const subject = GALLERY_V4_MINE.selected;
    const cards = structuredClone(GALLERY_V4_MINE.cards.slice(0, 3)).map((row, index) => ({ ...row, is_default: index === 1 }));
    await wrapper.setProps({ model: { ...structuredClone(GALLERY_V4_MINE), selected: subject, cards } });
    await flushPromises();
    expect(pageSelection()).toBe("card");
    expect(trayItem(cards[1].image_id).getAttribute("aria-selected")).toBe("true");
    expect(trayItem(cards[0].image_id).getAttribute("aria-selected")).toBe("false");
  });

  it("closes the editor of a vanished image without sending and shows the replacement", async () => {
    const { wrapper, dispatch } = mountWindow();
    const doomed = GALLERY_V4_MINE.cards[1];
    await click(trayItem(doomed.image_id));
    await click(footerButton("face"));
    expect(document.querySelector('[aria-label="臉部框選"]')).not.toBeNull();
    const next = withCards(GALLERY_V4_MINE, GALLERY_V4_MINE.cards.filter((row) => row.image_id !== doomed.image_id));
    await wrapper.setProps({ model: next });
    await flushPromises();
    expect(document.querySelector('[aria-label="臉部框選"]')).toBeNull();
    expect(dispatch).not.toHaveBeenCalled();
    const replacement = initialImage(next.cards, next.official_entries);
    expect(trayItem(replacement).getAttribute("aria-selected")).toBe("true");
  });

  it("adopts the first image that appears on an empty page", async () => {
    const { wrapper } = mountWindow({ model: structuredClone(GALLERY_V4_MINE_BLANK) });
    expect(pageSelection()).toBe("empty");
    const card = GALLERY_V4_MINE.cards[2];
    await wrapper.setProps({ model: withCards(GALLERY_V4_MINE_BLANK, [card]) });
    await flushPromises();
    expect(pageSelection()).toBe("card");
  });
});

describe("focus is rescued and Escape closes in layers", () => {
  it("moves focus to the rail's selected tab when a commit removes the focused tile", async () => {
    const { wrapper } = mountWindow();
    const twin = GALLERY_V4_MINE.groups[0].subjects[1].subject_key;
    document.querySelector(`[data-testid="gallery-subject"][data-subject-key="${twin}"]`).focus();
    const next = structuredClone(GALLERY_V4_MINE);
    next.groups[0].subjects = next.groups[0].subjects.filter((row) => row.subject_key !== twin);
    await wrapper.setProps({ model: next });
    await flushPromises();
    expect(document.activeElement).toBe(tab("mine"));
  });

  it("puts focus back on the owner tile when a confirmed delete leaves the page without a button", async () => {
    const { wrapper } = mountWindow();
    const doomed = GALLERY_V4_MINE.cards[1];
    const pendingRow = GALLERY_V4_MINE.cards.find((row) => row.status === "pending");
    await click(trayItem(doomed.image_id));
    await click(footerButton("delete"));
    await click(footerButton("confirm-delete"));
    footerButton("delete").focus();
    // The commit keeps only the pending card, whose footer has no button.
    await wrapper.setProps({
      result: { requestId: "request:1", outcome: "success", presentationRevision: 2 },
      revision: 2,
      model: withCards(GALLERY_V4_MINE, [pendingRow]),
    });
    await flushPromises();
    await flushPromises();
    expect(document.activeElement?.dataset.subjectKey).toBe(GALLERY_V4_MINE.selected);
  });

  it("returns from the tray to the owner tile, then closes the window", async () => {
    const { wrapper } = mountWindow();
    const item = trayItem(GALLERY_V4_MINE.cards[0].image_id);
    item.focus();
    await key(item, "Escape");
    expect(document.activeElement?.dataset.subjectKey).toBe(GALLERY_V4_MINE.selected);
    expect(wrapper.emitted("close")).toBeUndefined();
    await key(document.activeElement, "Escape");
    expect(wrapper.emitted("close")).toHaveLength(1);
  });
});

describe("an unavailable panel", () => {
  it("shows the committed reason and offers no control", () => {
    mountWindow({ model: { schema_version: 4, kind: "gallery", available: false, reason: { message: "測試原因" } } });
    expect(document.querySelector('[data-testid="gallery-window__unavailable"]').textContent).toContain("測試原因");
    expect(document.querySelector('[data-testid="gallery-window__rail"]')).toBeNull();
    expect(document.querySelector('[data-testid="gallery-wall"]')).toBeNull();
  });

  it("falls back to the generic reason", () => {
    mountWindow({ model: null });
    expect(document.querySelector('[data-testid="gallery-window__unavailable"]').textContent).toContain("圖庫目前無法使用。");
  });
});

// Every length in the window's own styles is token-driven: any literal pixel
// size is `calc(<n>px * var(--ui-scale))` or a token, text uses `--text-*`
// tokens (none below `--text-xs`), and durations use `--motion-*`.
describe("GalleryWindow styles", () => {
  const APP_ROOT = join(process.cwd(), "web/webclient-app");
  const source = readFileSync(join(APP_ROOT, "components/GalleryWindow.vue"), "utf8");
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
    const declarations = [...css.matchAll(/(?:^|[;{\s])(font-size)\s*:\s*([^;}]+)/g)];
    expect(declarations.length).toBeGreaterThan(0);
    for (const [, property, value] of declarations) {
      const tokens = [...value.matchAll(/var\((--text-[a-z0-9]+)\)/g)].map((match) => match[1]);
      expect(tokens, `${property}: ${value}`).toHaveLength(1);
      expect(TEXT_TOKENS).toContain(tokens[0]);
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
