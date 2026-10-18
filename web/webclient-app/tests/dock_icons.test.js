import { describe, expect, it } from "vitest";
import { glyphAttrs, glyphPath } from "../components/dock-icons.js";

describe("dock-icons glyph table (the 拿 chip's get glyph)", () => {
  it('glyphPath("get") returns the reference get-icon path', () => {
    expect(glyphPath("get")).toBe(
      "M6 11V7a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v4M4 11h16v9H4z",
    );
  });

  it("still returns the prior unchanged value for an untouched key", () => {
    // The `character` key is not touched by this change (the sibling
    // icon-fix change owns the other keys).
    expect(glyphPath("character")).toBe(
      "M12 2a5 5 0 1 1 0 10 5 5 0 0 1 0-10zm-7 22v-1c0-3.9 3.1-7 7-7s7 3.1 7 7v1h-14z",
    );
  });
});

// quest-drawer-ui-primitives (design Decision 7): the sixteen quest drawer
// glyphs, pinned to the approved prototype's `ICONS` paths
// (docs/design/quest-drawer-redesign/QuestDrawerPrototype.vue). `lock` has
// no prototype path (the prototype drew a CSS box), so only its presence is
// pinned.
const QUEST_GLYPHS = {
  quest_book: "M6 3.5h11a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2zM6 3.5a2 2 0 0 0-2 2V8h2M9.5 8.5h6M9.5 12h6M9.5 15.5h3.5",
  guild_counter: "M12 2.8 4.5 5.6v6c0 4.8 3.2 8 7.5 9.6 4.3-1.6 7.5-4.8 7.5-9.6v-6zM12 7v9.5M8.5 10.5h7",
  quest_in_progress: "M7 3h10M7 21h10M8 3c0 5 8 5 8 9s-8 4-8 9M16 3c0 5-8 5-8 9s8 4 8 9M10 18.5h4",
  quest_completed: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM8 12.4l2.8 2.8 5.4-5.6",
  quest_failed: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM9 9l6 6M15 9l-6 6",
  cat_gather: "M6 18c0-7 5-12 13-12 0 8-5 13-12 13M6 18l7-7",
  cat_defeat: "M19.5 4.5v3.2L10.4 16.8 7.2 13.6l9.1-9.1zM5.3 11.7l7 7M8.8 15.2l-4.3 4.3",
  cat_escort: "M12 3 5 6v5.5c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6z",
  cat_explore: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM15.5 8.5l-2 5-5 2 2-5z",
  cat_emergency: "M12 3 2.5 20h19zM12 9.5v5M12 17.2v.3",
  track_flag: "M6.5 21V4h11l-2.4 4 2.4 4h-11",
  reward_copper: "M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16zM12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z",
  reward_merit: "M12 3l2.6 5.6 6 .7-4.5 4.1 1.2 6L12 16.4 6.7 19.4l1.2-6L3.4 9.3l6-.7z",
  reward_item: "M9 3h6M10 3v4.5L6 15a4 4 0 0 0 3.6 6h4.8A4 4 0 0 0 18 15l-4-7.5V3",
  deadline: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 7v5l3 2",
};

describe("dock-icons quest drawer glyphs (quest-drawer-ui-primitives)", () => {
  it.each(Object.entries(QUEST_GLYPHS))("%s carries the prototype path", (key, d) => {
    expect(glyphPath(key)).toBe(d);
  });

  it.each([...Object.keys(QUEST_GLYPHS), "lock"])("%s yields a path and round stroke attrs", (key) => {
    expect(glyphPath(key)).toMatch(/^M/);
    expect(glyphAttrs(key)).toEqual({ "stroke-linecap": "round", "stroke-linejoin": "round" });
  });
});

// webclient-window-primitives: the party member management glyphs, pinned to
// the approved prototype's `NEW_GLYPHS` paths, copied here so the pin does
// not depend on the design-reference file
// (docs/design/party-member-management/glyphs.js).
const PARTY_GLYPHS = {
  member: "M12 20.5s-7.5-4.6-7.5-10.1A4.3 4.3 0 0 1 12 7.6a4.3 4.3 0 0 1 7.5 2.8c0 5.5-7.5 10.1-7.5 10.1z",
  status: "M4 5h16M4 10h16M4 15h10M4 20h7",
  potion: "M10 3h4M10.5 3v5L6 15.5A3.5 3.5 0 0 0 9 21h6a3.5 3.5 0 0 0 3-5.5L13.5 8V3M7.5 14h9",
  sword: "M19.5 4.5v3.2L10.4 16.8 7.2 13.6l9.1-9.1zM5.3 11.7l7 7M8.8 15.2l-4.3 4.3",
  hammer: "M5 4h9l3 3-2 2-3-1H5zM10 8l-6.5 11.5 1.8 1L12 9.5",
  bow: "M6 3c6 3 9 8 9 9s-3 6-9 9M6 3v18M15 12H3M3 12l3-2M3 12l3 2",
  shield: "M12 3 4.5 6v5.5c0 4.5 3 7.7 7.5 9.5 4.5-1.8 7.5-5 7.5-9.5V6z",
  armor: "M8 3 4 5.5V11l3 1v9h10v-9l3-1V5.5L16 3c-.6 1.8-2.1 3-4 3s-3.4-1.2-4-3z",
  staff: "M7 21 17 5M15.5 3.5a2.5 2.5 0 1 0 3.5 3.5",
  amulet: "M7 3c0 4 2.2 6.5 5 7 2.8-.5 5-3 5-7M12 10l-3.5 4 3.5 6 3.5-6z",
  ration: "M4 13h16l-1.5 6h-13zM7 13c0-3 2.2-5 5-5s5 2 5 5M12 5v3",
  scroll: "M7 4h11v13a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3v-1h11v1a3 3 0 0 0 3 3M7 4a2 2 0 0 0-2 2v10",
  herb: "M12 21V9M12 13c-4 0-6-3-6-7 4 0 6 3 6 7zM12 11c3.5 0 5.5-2.5 5.5-6-3.5 0-5.5 2.5-5.5 6z",
  holy: "M12 3v18M6 9h12",
  ice: "M12 2.5v19M3.8 7.2l16.4 9.6M3.8 16.8l16.4-9.6M9.5 4.2 12 6.5l2.5-2.3M9.5 19.8 12 17.5l2.5 2.3",
  wind: "M3 9h11a3 3 0 1 0-3-3M3 14h15a3 3 0 1 1-3 3M3 19h7",
  buff: "M12 4l2.2 5.1 5.3.4-4 3.6 1.3 5.4L12 15.6 7.2 18.5l1.3-5.4-4-3.6 5.3-.4z",
  debuff: "M12 3 2.5 20h19zM12 9.5v5M12 17.2v.3",
  slot_empty: "M5 5h14v14H5z",
  plus: "M12 5v14M5 12h14",
  minus: "M5 12h14",
  give: "M4 12h13M13 7l5 5-5 5",
  knocked_out: "M6 9l6 6 6-6",
};

describe("dock-icons party member management glyphs (webclient-window-primitives)", () => {
  it.each(Object.entries(PARTY_GLYPHS))("%s carries the prototype path", (key, d) => {
    expect(glyphPath(key)).toBe(d);
  });

  it.each(Object.keys(PARTY_GLYPHS))("%s draws with round caps and joins, as the prototype's PmGlyph", (key) => {
    expect(glyphAttrs(key)).toEqual({ "stroke-linecap": "round", "stroke-linejoin": "round" });
  });

  it("adds all twenty-three glyphs", () => {
    expect(Object.keys(PARTY_GLYPHS)).toHaveLength(23);
  });
});
