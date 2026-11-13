// The gallery image page (change gallery-image-page): the capability-driven
// footer descriptor, the page ribbon, the two-step deletion and the committed
// fact cells. Synthetic rows and labels only: no shipped character, monster
// or category data.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";

import GalleryImagePage from "../../components/GalleryImagePage.vue";
import { galleryDate } from "../../components/gallery-copy.js";
import { galleryFooter, galleryRibbon } from "../../components/gallery-window-model.js";

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

const official = (identity, changes = {}) => ({
  identity, artwork: null, is_current: false, is_catalog_default: false, ...changes,
});

const caps = (changes = {}) => ({
  supports_bindings: false,
  supports_field_selection: false,
  supports_free_text: false,
  supports_personal_official_preferences: false,
  supports_face_rect: false,
  supports_stage: false,
  supports_card_delete: false,
  max_cards: null,
  ...changes,
});

const EVERY = caps({
  supports_card_delete: true, supports_face_rect: true, supports_stage: true, supports_bindings: true,
  supports_personal_official_preferences: true, max_cards: null,
});

const labels = (footer) => footer.buttons.map((button) => button.label);

describe("galleryFooter (the footer follows the declared capabilities)", () => {
  it("offers every capability button, all enabled, for a multi-card card", () => {
    const footer = galleryFooter({ type: "card", row: card("c1") }, EVERY);
    expect(labels(footer)).toEqual(["刪除", "臉框", "舞台位置", "綁定裝備", "設為預設"]);
    expect(footer.buttons.every((button) => button.enabled)).toBe(true);
    expect(footer.buttons.map((button) => button.key)).toEqual(["delete", "face", "stage", "binding", "default"]);
    expect(footer.buttons[0].tone).toBe("danger");
    expect(footer.note).toBeNull();
  });

  it("disables 設為預設 on the default card with the reason 目前預設", () => {
    const footer = galleryFooter({ type: "card", row: card("c1", { is_default: true }) }, EVERY);
    const button = footer.buttons.find((entry) => entry.key === "default");
    expect(button.label).toBe("設為預設");
    expect(button.enabled).toBe(false);
    expect(button.describedByReason).toBe(true);
    expect(footer.note).toBe("目前預設");
  });

  it("offers 臉框, 舞台位置, 重新生成 for a one-card kind without deletion", () => {
    const footer = galleryFooter(
      { type: "card", row: card("c1") },
      caps({ supports_face_rect: true, supports_stage: true, max_cards: 1 }),
    );
    expect(labels(footer)).toEqual(["臉框", "舞台位置", "重新生成"]);
  });

  it("offers 刪除 and 重新生成 for a one-card kind with deletion and no geometry", () => {
    const footer = galleryFooter({ type: "card", row: card("c1") }, caps({ supports_card_delete: true, max_cards: 1 }));
    expect(labels(footer)).toEqual(["刪除", "重新生成"]);
  });

  it("declares nothing for a card when the capabilities are null", () => {
    expect(galleryFooter({ type: "card", row: card("c1") }, null)).toEqual({ buttons: [], note: null });
  });

  it("separates the destructive button without changing the order", () => {
    const footer = galleryFooter({ type: "card", row: card("c1") }, EVERY);
    expect(footer.buttons.filter((button) => button.spacerBefore).map((button) => button.key)).toEqual(["face"]);
  });

  it("reads no subject category", () => {
    expect(galleryFooter.toString()).not.toMatch(/kind|portrait|monster|scene|character/);
  });
});

describe("galleryFooter (non-card selections have fixed footers)", () => {
  it("offers no button for a pending row and notes that it is generating", () => {
    expect(galleryFooter({ type: "card", row: card("c1", { status: "pending" }) }, EVERY)).toEqual({ buttons: [], note: "生成中" });
  });

  it("offers only 重新生成 for a failed row", () => {
    const footer = galleryFooter({ type: "card", row: card("c1", { status: "failed" }) }, EVERY);
    expect(footer.buttons.map((button) => [button.key, button.label])).toEqual([["regenerate", "重新生成"]]);
  });

  it("offers 生成新圖 for a subject without any image", () => {
    for (const selection of [null, { type: "empty" }]) {
      const footer = galleryFooter(selection, EVERY);
      expect(footer.buttons.map((button) => [button.key, button.label, button.tone])).toEqual([["generate", "生成新圖", "primary"]]);
    }
  });

  it("keeps official entries read-only without personal preferences", () => {
    const footer = galleryFooter(
      { type: "official", row: official("o/a.webp") },
      { ...EVERY, supports_personal_official_preferences: false },
    );
    expect(footer.buttons).toEqual([]);
  });

  it("offers clearing on a current official entry", () => {
    const footer = galleryFooter({ type: "official", row: official("o/a.webp", { is_current: true }) }, EVERY);
    expect(labels(footer)).toEqual(["清除個人調整", "臉框", "舞台位置", "清除選取"]);
    expect(footer.buttons.at(-1).key).toBe("official-clear-selection");
  });

  it("offers 設為預設 on an official entry that is not current", () => {
    const footer = galleryFooter({ type: "official", row: official("o/a.webp") }, EVERY);
    expect(footer.buttons.map((button) => button.key)).toEqual([
      "official-geometry-clear", "official-face", "official-stage", "official-select",
    ]);
    expect(labels(footer).at(-1)).toBe("設為預設");
  });

  it("gates the official geometry buttons on the declared geometry facts", () => {
    const footer = galleryFooter(
      { type: "official", row: official("o/a.webp") },
      caps({ supports_personal_official_preferences: true }),
    );
    expect(labels(footer)).toEqual(["清除個人調整", "設為預設"]);
  });
});

describe("galleryRibbon", () => {
  it("reads the category label, then the group label when there is one", () => {
    expect(galleryRibbon("category-x", "group-y")).toBe("category-x・group-y");
    expect(galleryRibbon("category-x", null)).toBe("category-x");
    expect(galleryRibbon("category-x", "")).toBe("category-x");
  });
});

// ---- the page component ------------------------------------------------------

const NOW = 1_700_000_000_000;

const panel = (changes = {}) => ({
  schema_version: 4,
  available: true,
  kind: "gallery",
  description: null,
  capabilities: EVERY,
  binding_warnings: [],
  ...changes,
});

const subjectRow = { subject_key: "portrait:character:1", kind: "portrait:character", display_name: "subject-name", is_current: false, card_count: 2, artwork: null };

describe("GalleryImagePage (webclient-gallery-image-page)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
    document.body.innerHTML = "";
  });

  async function mountPage(props = {}) {
    wrapper = mount(GalleryImagePage, {
      attachTo: document.body,
      props: {
        panel: panel(),
        subject: subjectRow,
        categoryLabel: "category-x",
        selection: { type: "card", row: card("c1", { created_at: 1_699_990_000 }) },
        now: NOW,
        ...props,
      },
    });
    await flushPromises();
    return wrapper;
  }

  const button = (key) => wrapper.find(`[data-testid="gallery-page__${key}"]`);
  const buttonLabels = () => wrapper.findAll('[data-testid="gallery-page__footer"] button').map((el) => el.text());
  const cell = (name) => wrapper.find(`[data-cell="${name}"]`);
  const presses = () => (wrapper.emitted("press") ?? []).map(([key]) => key);

  async function keydown(target, key) {
    const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true });
    target.element.dispatchEvent(event);
    await flushPromises();
    return event;
  }

  describe("deletion takes two steps", () => {
    it("arms a confirmation instead of emitting, with focus on 取消", async () => {
      await mountPage();
      await button("delete").trigger("click");
      await flushPromises();
      expect(presses()).toEqual([]);
      expect(buttonLabels()).toEqual(["確認刪除", "取消"]);
      const warning = wrapper.get('[data-testid="gallery-page__delete-warning"]');
      expect(warning.text()).toBe("刪除後無法復原。");
      expect(warning.attributes("role")).toBe("alert");
      expect(document.activeElement).toBe(button("cancel").element);
    });

    it("emits nothing when the player cancels, and returns focus to 刪除", async () => {
      await mountPage();
      await button("delete").trigger("click");
      await button("cancel").trigger("click");
      await flushPromises();
      expect(wrapper.emitted("press")).toBeUndefined();
      expect(buttonLabels()[0]).toBe("刪除");
      expect(document.activeElement).toBe(button("delete").element);
    });

    it("emits press(delete) once on confirmation", async () => {
      await mountPage();
      await button("delete").trigger("click");
      await button("confirm-delete").trigger("click");
      await flushPromises();
      expect(presses()).toEqual(["delete"]);
      expect(buttonLabels()[0]).toBe("刪除");
    });

    it("disarms on Escape inside the page without emitting", async () => {
      await mountPage();
      await button("delete").trigger("click");
      await flushPromises();
      const event = await keydown(button("cancel"), "Escape");
      expect(event.defaultPrevented).toBe(true);
      expect(wrapper.emitted("press")).toBeUndefined();
      expect(buttonLabels()[0]).toBe("刪除");
    });

    it("lets Escape through to the window when nothing is armed", async () => {
      await mountPage();
      const event = await keydown(button("delete"), "Escape");
      expect(event.defaultPrevented).toBe(false);
    });

    it("disarms when another image is selected, and keeps the arm across a re-commit of the same one", async () => {
      await mountPage();
      await button("delete").trigger("click");
      await wrapper.setProps({ selection: { type: "card", row: card("c1", { created_at: 1_699_990_000 }) } });
      expect(buttonLabels()).toEqual(["確認刪除", "取消"]);
      await wrapper.setProps({ selection: { type: "card", row: card("c2") } });
      expect(buttonLabels()[0]).toBe("刪除");
      await wrapper.setProps({ selection: { type: "card", row: card("c1") } });
      expect(buttonLabels()[0]).toBe("刪除");
      expect(wrapper.emitted("press")).toBeUndefined();
    });

    it("blocks every press, a second delete included, while the host is busy", async () => {
      await mountPage();
      await button("delete").trigger("click");
      await button("confirm-delete").trigger("click");
      await wrapper.setProps({ disabled: true });
      await button("delete").trigger("click");
      await button("face").trigger("click");
      await keydown(button("delete"), "Escape");
      expect(presses()).toEqual(["delete"]);
      expect(button("delete").attributes("aria-disabled")).toBe("true");
      expect(buttonLabels()[0]).toBe("刪除");
    });
  });

  describe("the footer", () => {
    it("emits the other keys directly", async () => {
      await mountPage();
      await button("face").trigger("click");
      await button("default").trigger("click");
      expect(presses()).toEqual(["face", "default"]);
    });

    it("describes the disabled 設為預設 by 目前預設 and emits nothing for it", async () => {
      await mountPage({ selection: { type: "card", row: card("c1", { is_default: true }) } });
      const note = wrapper.get('[data-testid="gallery-page__note"]');
      expect(note.text()).toBe("目前預設");
      expect(button("default").attributes("aria-disabled")).toBe("true");
      expect(button("default").attributes("aria-describedby")).toBe(note.attributes("id"));
      await button("default").trigger("click");
      expect(wrapper.emitted("press")).toBeUndefined();
    });

    it("shows 生成中 and no button for a pending row", async () => {
      await mountPage({ selection: { type: "card", row: card("c1", { status: "pending" }) } });
      expect(buttonLabels()).toEqual([]);
      expect(wrapper.get('[data-testid="gallery-page__note"]').text()).toBe("生成中");
      expect(wrapper.get('[data-testid="gallery-page__art"]').text()).toContain("生成中");
    });
  });

  describe("committed facts in cells", () => {
    it("reads the category and the group label on the ribbon", async () => {
      await mountPage({ categoryLabel: "category-x", groupLabel: "group-y" });
      expect(wrapper.get('[data-testid="gallery-page__ribbon"]').text()).toBe("category-x・group-y");
      await wrapper.setProps({ groupLabel: null });
      expect(wrapper.get('[data-testid="gallery-page__ribbon"]').text()).toBe("category-x");
    });

    it("lists exactly the committed chips", async () => {
      await mountPage({ selection: { type: "card", row: card("c1", { chips: ["chip-a", "chip-b"] }) } });
      expect(cell("chips").findAll("li").map((el) => el.text())).toEqual(["chip-a", "chip-b"]);
    });

    it("omits 標記 when there is no chip", async () => {
      await mountPage();
      expect(cell("chips").exists()).toBe(false);
    });

    it("shows the committed label and the relative and exact time", async () => {
      await mountPage();
      expect(cell("image").find(".gpage__line").text()).toBe("label-c1");
      const date = galleryDate(1_699_990_000, NOW);
      expect(cell("time").text()).toContain(date.relative);
      expect(cell("time").get("time").text()).toBe(date.exact);
      expect(cell("time").get("time").attributes("datetime")).toBe(date.iso);
    });

    it("dates stored and failed rows only", async () => {
      await mountPage({ selection: { type: "card", row: card("c1", { status: "failed", created_at: 1_699_990_000 }) } });
      expect(cell("time").exists()).toBe(true);
      for (const selection of [
        { type: "card", row: card("c1", { status: "pending", created_at: 1_699_990_000 }) },
        { type: "official", row: official("o/a.webp") },
        { type: "empty" },
      ]) {
        await wrapper.setProps({ selection });
        expect(cell("time").exists()).toBe(false);
      }
    });

    it("reads 日期不詳 for an impossible time", async () => {
      await mountPage({ selection: { type: "card", row: card("c1", { created_at: Number.NaN }) } });
      expect(cell("time").text()).toContain("日期不詳");
      expect(cell("time").find("time").exists()).toBe(false);
    });

    it("shows 狀態 only when the kind allows several cards", async () => {
      await mountPage({ selection: { type: "card", row: card("c1", { is_default: true }) } });
      expect(cell("status").text()).toContain("目前預設");
      expect(cell("status").find('[data-mark="crown"]').exists()).toBe(true);
      await wrapper.setProps({ selection: { type: "card", row: card("c2") } });
      expect(cell("status").find(".gpage__line").text()).toBe("備用圖片");
      await wrapper.setProps({ selection: { type: "card", row: card("c3", { status: "pending" }) } });
      expect(cell("status").find(".gpage__line").text()).toBe("生成中");
      await wrapper.setProps({ selection: { type: "card", row: card("c4", { status: "failed" }) } });
      expect(cell("status").find(".gpage__line").text()).toBe("生成失敗");
      await wrapper.setProps({ panel: panel({ capabilities: caps({ max_cards: 1 }) }) });
      expect(cell("status").exists()).toBe(false);
      await wrapper.setProps({ selection: { type: "official", row: official("o/a.webp") }, panel: panel() });
      expect(cell("status").exists()).toBe(false);
    });

    it("notes the replacement rule of a one-card kind", async () => {
      await mountPage({ panel: panel({ capabilities: caps({ max_cards: 1 }) }) });
      expect(cell("image").text()).toContain("只保留一張，重新生成會替換原圖。");
    });

    it("names an official entry and marks it read-only", async () => {
      await mountPage({ selection: { type: "official", row: official("o/a.webp") } });
      expect(cell("image").find(".gpage__line").text()).toBe("官方圖片");
      expect(cell("image").text()).toContain("唯讀，只能調整個人的臉框與舞台位置。");
    });

    it("says 尚無圖片 for a subject without any image", async () => {
      await mountPage({ selection: { type: "empty" } });
      expect(cell("image").find(".gpage__line").text()).toBe("尚無圖片");
      expect(buttonLabels()).toEqual(["生成新圖"]);
    });

    it("lists the committed warning conditions of that card across both columns", async () => {
      const warnings = [
        { image_id: "c1", label: "x", conditions: ["cond-a", "cond-b"] },
        { image_id: "c2", label: "x", conditions: ["cond-c"] },
      ];
      await mountPage({ panel: panel({ binding_warnings: warnings }) });
      expect(cell("conditions").findAll("li").map((el) => el.text())).toEqual(["cond-a", "cond-b"]);
      expect(cell("conditions").classes()).toContain("gpage__cell--wide");
      await wrapper.setProps({ selection: { type: "card", row: card("c9") } });
      expect(cell("conditions").exists()).toBe(false);
    });

    it("renders a non-null committed description in a letter box", async () => {
      await mountPage();
      expect(wrapper.find('[data-testid="gallery-page__letter"]').exists()).toBe(false);
      await wrapper.setProps({ panel: panel({ description: "prose-text" }) });
      expect(wrapper.get('[data-testid="gallery-page__letter"]').text()).toContain("prose-text");
    });

    it("renders without a subject row", async () => {
      await mountPage({ subject: null });
      expect(wrapper.find('[data-testid="gallery-page__title"]').exists()).toBe(false);
      expect(cell("image").exists()).toBe(true);
    });
  });
});

// Every length in the page's own styles is token-driven: any literal pixel
// size is `calc(<n>px * var(--ui-scale))` or a token, text uses `--text-*`
// tokens (none below `--text-xs`), and durations use `--motion-*`.
describe("GalleryImagePage styles", () => {
  const APP_ROOT = join(process.cwd(), "web/webclient-app");
  const source = readFileSync(join(APP_ROOT, "components/GalleryImagePage.vue"), "utf8");
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
