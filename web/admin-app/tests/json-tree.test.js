import { describe, expect, it } from "vitest";
import GmJsonTree from "../components/GmJsonTree.vue";
import { NPC_RAW, mountWith } from "./runtime-helpers.js";

describe("GmJsonTree", () => {
  it("renders scalars as JSON and keys as their own nodes", () => {
    const wrapper = mountWith(GmJsonTree, {
      props: { value: { count: 7, flag: true, note: "合成", missing: null } },
    });
    const keys = wrapper.findAll(".gm-json-tree__key").map((node) => node.text());
    expect(keys).toEqual(["count", "flag", "note", "missing"]);
    const values = wrapper.findAll(".gm-json-tree__scalar").map((node) => node.text());
    expect(values).toEqual(["7", "true", '"合成"', "null"]);
    expect(wrapper.findAll(".gm-json-tree__scalar")[2].attributes("data-type")).toBe("string");
  });

  it("links every $ref to the object's raw inspection", () => {
    const wrapper = mountWith(GmJsonTree, { props: { value: NPC_RAW.raw.location } });
    const anchor = wrapper.get("a");
    expect(anchor.attributes("href")).toBe("/gm/runtime/object/3/raw");
    expect(anchor.text()).toBe("合成廣場");
    expect(wrapper.get(".gm-json-tree__type").text()).toBe("typeclasses.rooms.Room");
  });

  it("presents an unserializable value distinctly with its bounded repr", () => {
    const marker = { $unserializable: "set", repr: "{1, 2}" };
    const wrapper = mountWith(GmJsonTree, { props: { value: marker, name: "t_marker" } });
    const row = wrapper.get(".gm-json-tree__row--marker");
    expect(row.get(".gm-json-tree__marker").text()).toBe("⟨set⟩");
    expect(row.get(".gm-json-tree__repr").text()).toBe("{1, 2}");
    // The rest of the inventory still renders around it.
    const inventory = mountWith(GmJsonTree, { props: { value: NPC_RAW.raw, openDepth: 3 } });
    expect(inventory.text()).toContain("t_count");
    expect(inventory.text()).toContain("⟨set⟩");
    expect(inventory.text()).toContain("合成廣場");
  });

  it("collapses containers beyond the open depth and reports their size", () => {
    const value = { outer: { inner: { deep: 1 } } };
    const shallow = mountWith(GmJsonTree, { props: { value, openDepth: 1 } });
    expect(shallow.findAll("details[open]")).toHaveLength(1);
    expect(shallow.text()).toContain("物件 · 1 鍵");
    const deep = mountWith(GmJsonTree, { props: { value, openDepth: 3 } });
    expect(deep.findAll("details[open]")).toHaveLength(3);
    expect(deep.text()).toContain("deep");
  });

  it("says so explicitly when a container is empty, and renders arrays with indexes", () => {
    const empty = mountWith(GmJsonTree, { props: { value: {} } });
    expect(empty.get(".gm-json-tree__empty").text()).toBe("（空）");
    const array = mountWith(GmJsonTree, { props: { value: ["a", "b"] } });
    expect(array.get("summary").text()).toContain("陣列 · 2 項");
    expect(array.findAll(".gm-json-tree__key").map((node) => node.text())).toEqual(["0", "1"]);
  });

  it("keeps a nested reference addressable at any depth", () => {
    const value = { evidence: { call_id: { $ref: "#9" } } };
    const wrapper = mountWith(GmJsonTree, { props: { value, openDepth: 5 } });
    const nested = wrapper.findAll("a");
    expect(nested.map((node) => node.attributes("href"))).toEqual(["/gm/runtime/object/9/raw"]);
    expect(nested[0].attributes("data-kind")).toBe("object");
  });
});
