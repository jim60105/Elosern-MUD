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
