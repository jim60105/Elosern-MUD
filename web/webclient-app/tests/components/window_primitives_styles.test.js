// webclient-window-primitives: primitive sizing and motion use tokens. Every
// size is `calc(<n>px * var(--ui-scale))` or a token, every text size is a
// `--text-*` token (none below `--text-xs`), and no duration is literal.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const APP_ROOT = join(process.cwd(), "web/webclient-app");
const PRIMITIVES = ["WindowFrame", "MemberRail", "ListDetail", "ActionBar", "HoldingsStrip"];

function source(name) {
  return readFileSync(join(APP_ROOT, `components/${name}.vue`), "utf8");
}

function styles(name) {
  const blocks = [...source(name).matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)].map((match) => match[1]);
  return blocks.join("\n").replace(/\/\*[\s\S]*?\*\//g, "");
}

const SCALED_PX = /calc\(\s*-?\d*\.?\d+px\s*\*\s*var\(--ui-scale\)\s*\)/g;
const TEXT_TOKENS = ["--text-xs", "--text-sm", "--text-md", "--text-base", "--text-lg", "--text-xl", "--text-2xl", "--text-3xl", "--text-4xl"];

describe("window primitive styles (webclient-window-primitives)", () => {
  it.each(PRIMITIVES)("%s has a scoped style block", (name) => {
    expect(source(name)).toMatch(/<style scoped>/);
  });

  it.each(PRIMITIVES)("%s writes no raw pixel size", (name) => {
    const css = styles(name).replace(SCALED_PX, "SCALED");
    expect(css.match(/-?\d*\.?\d+px\b/g) ?? []).toEqual([]);
    // Other absolute units are raw sizes too.
    expect(css.match(/\d(pt|rem|vh|vw)\b/g) ?? []).toEqual([]);
  });

  it.each(PRIMITIVES)("%s sizes text only through --text-* tokens", (name) => {
    const css = styles(name);
    const declarations = [...css.matchAll(/(?:^|[;{\s])(font-size|font)\s*:\s*([^;}]+)/g)];
    for (const [, property, value] of declarations) {
      if (property === "font-size" && /^(inherit|1em)$/.test(value.trim())) continue;
      const tokens = [...value.matchAll(/var\((--text-[a-z0-9]+)\)/g)].map((match) => match[1]);
      expect(tokens, `${name}: ${property}: ${value}`).toHaveLength(1);
      expect(TEXT_TOKENS, `${name}: ${property}: ${value}`).toContain(tokens[0]);
      // A token scaled by calc() could render below --text-xs.
      expect(value, `${name}: ${property}: ${value}`).not.toMatch(/calc\([^)]*--text-/);
    }
  });

  it.each(PRIMITIVES)("%s names every duration through a --motion-* token", (name) => {
    const css = styles(name);
    for (const [, value] of css.matchAll(/(?:transition|animation)[a-z-]*\s*:\s*([^;}]+)/g)) {
      expect(value, `${name}: ${value}`).not.toMatch(/(?<![\w-])\d*\.?\d+m?s\b/);
      if (value.trim() !== "none") expect(value).toMatch(/var\(--motion-[a-z-]+\)/);
    }
  });

  it.each(PRIMITIVES)("%s puts no inline style sizes in its template", (name) => {
    const template = source(name).replace(/<script[\s\S]*?<\/script>/g, "").replace(/<style[\s\S]*?<\/style>/g, "");
    expect(template).not.toMatch(/\sstyle=/);
    expect(template).not.toMatch(/\s(width|height)="\d+"/);
  });
});
