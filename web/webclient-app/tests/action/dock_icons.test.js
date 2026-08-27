import { describe, expect, it } from "vitest";
import { GLYPHS, glyphAttrs, glyphPath, glyphSvg } from "../../components/dock-icons.js";

// Unit tests for the dock glyph table (fix-webclient-hud-dock-guidance-and-icons):
// the ten reference-matched `d` strings, the per-key stroke attributes, and
// the regression check that an untouched key keeps its prior value.
describe("dock-icons glyph table", () => {
  // The exact `d` strings `docs/design/elosern-redesign/index.html` draws for
  // the exploration and combat root tab concepts.
  const REFERENCE_D = {
    move: "M12 5v14M12 5 7 10M12 5l5 5",
    look: "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z M9 12a3 3 0 1 0 6 0a3 3 0 1 0 -6 0",
    interact: "M4 5h16v11H8l-4 4V5Z",
    suggestions: "M12 3l1.9 5.6L19.5 10l-5.6 1.9L12 17l-1.9-5.1L4.5 10l5.6-1.4L12 3Z",
    attack: "M5 19 19 5M5 19h4M5 19v-4",
    skills: "M12 3l1.9 5.6L19.5 10l-5.6 1.9L12 17l-1.9-5.1L4.5 10l5.6-1.4L12 3Z",
    items: "M4 8h16v11H4zM8 8V6a4 4 0 0 1 8 0v2",
    defend: "M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3Z",
    flee: "M13 5l7 7-7 7M4 12h16",
    forfeit: "M6 2h12l-5 8v6M9 2l1 7",
  };

  it("returns the reference `d` string for every reference-matched key", () => {
    for (const [key, d] of Object.entries(REFERENCE_D)) {
      expect(glyphPath(key)).toBe(d);
    }
    // `suggestions` and `skills` intentionally share the reference's single
    // star glyph.
    expect(REFERENCE_D.suggestions).toBe(REFERENCE_D.skills);
  });

  it("still returns the prior unchanged value for an untouched key", () => {
    expect(GLYPHS.character).toBe("M12 2a5 5 0 1 1 0 10 5 5 0 0 1 0-10zm-7 22v-1c0-3.9 3.1-7 7-7s7 3.1 7 7v1h-14z");
    expect(glyphPath("character")).toBe(GLYPHS.character);
  });

  it("returns the reference's selective stroke attributes per key", () => {
    expect(glyphAttrs("move")).toEqual({ "stroke-linecap": "round", "stroke-linejoin": "round" });
    expect(glyphAttrs("interact")).toEqual({ "stroke-linejoin": "round" });
    expect(glyphAttrs("attack")).toEqual({ "stroke-linecap": "round" });
    expect(glyphAttrs("flee")).toEqual({ "stroke-linecap": "round" });
    // The star glyphs and the other replaced/untouched keys carry no
    // attributes (the reference omits them there).
    for (const key of ["look", "suggestions", "skills", "items", "defend", "forfeit", "character", "quests", "inventory", "wait"]) {
      expect(glyphAttrs(key)).toEqual({});
    }
    expect(glyphAttrs(null)).toEqual({});
  });

  it("merges the per-key stroke attributes into the glyphSvg path", () => {
    const moveSvg = glyphSvg("move");
    expect(moveSvg.children[0].props["stroke-linecap"]).toBe("round");
    expect(moveSvg.children[0].props["stroke-linejoin"]).toBe("round");
    expect(moveSvg.children[0].props.d).toBe(REFERENCE_D.move);
    const interactSvg = glyphSvg("interact");
    expect(interactSvg.children[0].props["stroke-linejoin"]).toBe("round");
    expect(interactSvg.children[0].props["stroke-linecap"]).toBeUndefined();
    const starSvg = glyphSvg("suggestions");
    expect(starSvg.children[0].props["stroke-linecap"]).toBeUndefined();
    expect(starSvg.children[0].props["stroke-linejoin"]).toBeUndefined();
  });

  it("returns null for unmapped keys", () => {
    expect(glyphPath("no-such-key")).toBeNull();
    expect(glyphSvg("no-such-key")).toBeNull();
  });
});
