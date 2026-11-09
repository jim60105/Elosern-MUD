import { describe, expect, it } from "vitest";
import { HANDBOOK_TAB_META, handbookTabs } from "../../components/handbook/handbook-tabs.js";

describe("handbookTabs (handbook-titles-tab)", () => {
  it("lists the book, counter and titles tabs outside combat, in bar order", () => {
    expect(handbookTabs({ combat: false })).toEqual(["book", "counter", "titles"]);
  });

  it("lists only the titles tab in combat", () => {
    expect(handbookTabs({ combat: true })).toEqual(["titles"]);
  });

  it("describes every tab it can list", () => {
    for (const key of handbookTabs({ combat: false })) {
      expect(HANDBOOK_TAB_META[key]).toBeTruthy();
    }
  });
});
