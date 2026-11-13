// The gallery image page (change gallery-image-page): the capability-driven
// footer descriptor, the page ribbon, the two-step deletion and the committed
// fact cells. Synthetic rows and labels only: no shipped character, monster
// or category data.
import { describe, expect, it } from "vitest";

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
