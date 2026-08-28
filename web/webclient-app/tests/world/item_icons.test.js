import { describe, expect, it } from "vitest";
import {
  ITEM_ICONS,
  KIND_LABELS,
  RARITY_LABELS,
  UNKNOWN_ITEM_ICON,
  itemIcon,
  itemIconLabel,
  itemIconPath,
  kindLabel,
  rarityLabel,
  unknownItemLabel,
  unknownItemPath,
} from "../../components/item-icons.js";

// The closed icon-key vocabulary (the server's ItemIconKey).
const ICON_KEYS = ["food", "potion", "weapon", "armor", "accessory", "ammunition", "tool", "material", "misc"];
const RARITIES = ["common", "uncommon", "rare", "epic", "legendary"];

describe("item-icons.js (redesign-inventory-item-grid, task 3.2)", () => {
  it("maps every closed services-v2 icon key to a local SVG path and a Traditional Chinese label", () => {
    expect(Object.keys(ITEM_ICONS).sort()).toEqual([...ICON_KEYS].sort());
    for (const key of ICON_KEYS) {
      const entry = ITEM_ICONS[key];
      expect(typeof entry.d).toBe("string");
      expect(entry.d.length).toBeGreaterThan(0);
      expect(entry.label).toBeTruthy();
      // No URL, no HTML, no emoji, no raw SVG markup.
      expect(entry.d).not.toMatch(/[:/]/);
      expect(entry.d).not.toContain("<");
    }
  });

  it("returns null for unmapped or non-string icon keys", () => {
    expect(itemIcon("future_enum_key")).toBeNull();
    expect(itemIcon(42)).toBeNull();
    expect(itemIcon(null)).toBeNull();
    expect(itemIconPath("food")).toBe(ITEM_ICONS.food.d);
    expect(itemIconPath("future_enum_key")).toBeNull();
    expect(itemIconLabel("food")).toBe(ITEM_ICONS.food.label);
    expect(itemIconLabel("future_enum_key")).toBeNull();
  });

  it("provides the neutral unknown-item fallback (the presentation: null case)", () => {
    expect(typeof unknownItemPath()).toBe("string");
    expect(unknownItemLabel()).toBe("未知");
    expect(UNKNOWN_ITEM_ICON.d.length).toBeGreaterThan(0);
  });

  it("spells kind and rarity words from the closed vocabularies", () => {
    expect(Object.keys(KIND_LABELS).sort()).toEqual([...ICON_KEYS].sort());
    expect(Object.keys(RARITY_LABELS).sort()).toEqual([...RARITIES].sort());
    expect(kindLabel("potion")).toBe("藥水");
    expect(kindLabel("unknown_kind")).toBeNull();
    expect(rarityLabel("rare")).toBe("稀有");
    expect(rarityLabel("mythic")).toBeNull();
    expect(rarityLabel(1)).toBeNull();
  });
});
