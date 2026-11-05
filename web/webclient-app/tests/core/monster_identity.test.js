// monster-individual-names (design D5): the client's one reading of the
// `monster_identity` wire facts. Synthetic names only.
import { describe, expect, it } from "vitest";
import { isNamedMonster, monsterDetailTag } from "../../components/monster-identity.js";

const UNNAMED = Object.freeze({ individual_name: null, species_name: "合成鶉", variant_name: "合成型" });
const NAMED = Object.freeze({ individual_name: "合成首領", species_name: "合成鶉", variant_name: "合成型" });

describe("monster identity reading", () => {
  it("tags an unnamed individual with its variant", () => {
    expect(isNamedMonster(UNNAMED)).toBe(false);
    expect(monsterDetailTag(UNNAMED)).toBe("合成型");
  });

  it("tags a named individual with its variant followed by its species", () => {
    expect(isNamedMonster(NAMED)).toBe(true);
    expect(monsterDetailTag(NAMED)).toBe("合成型合成鶉");
  });

  it("reads no identity as unnamed and untagged", () => {
    for (const identity of [null, undefined]) {
      expect(isNamedMonster(identity)).toBe(false);
      expect(monsterDetailTag(identity)).toBe(null);
    }
  });
});
