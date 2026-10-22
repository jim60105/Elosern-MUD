// Visual prototypes of the redesigned big-map drawer
// (docs/superpowers/specs/2026-10-22-world-map-drawer-design.md).
// Reference only: self-contained mock data, not wired to any payload, and
// outside the webclient component-coverage manifest.
import { h } from "vue";
import WorldMapPrototype from "./WorldMapPrototype.vue";

// The full-screen overlay over a dimmed stage, as the other drawer prototypes.
const overlay = (args) => ({
  render: () =>
    h(
      "div",
      {
        style: [
          "position: fixed; inset: 0; z-index: 8;",
          "background: linear-gradient(rgba(5,6,8,.78), rgba(5,6,8,.86)), url(/art/showcase/sample-guild.webp) center/cover;",
          "padding: calc(24px * var(--ui-scale));",
          "box-sizing: border-box;",
        ].join(""),
      },
      [h(WorldMapPrototype, args)],
    ),
});

export default {
  title: "Design/WorldMap",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "大地圖抽屜的設計稿：A 為全幅地圖＋浮動控制列＋點選才出現的右側抽屜；B 為固定三欄。拖曳平移、滾輪縮放；＋／－ 切換縮放級距，C 回到目前位置，0 顯示全圖，1／2 切換分頁。",
      },
    },
  },
};

// Option A — recommended.
export const A_AreaCity = { render: overlay, args: { layout: "floating", initialTab: "area", location: "city" } };
export const A_AreaCitySelected = {
  render: overlay,
  args: { layout: "floating", initialTab: "area", location: "city", initialSelection: "node:south_gate" },
};
export const A_AreaWilderness = { render: overlay, args: { layout: "floating", initialTab: "area", location: "wild" } };
export const A_WorldRegion = { render: overlay, args: { layout: "floating", initialTab: "world", location: "wild" } };
export const A_WorldContinent = {
  render: overlay,
  args: { layout: "floating", initialTab: "world", location: "wild", initialSpan: 5700 },
};
export const A_WorldDistrictSelected = {
  render: overlay,
  args: { layout: "floating", initialTab: "world", location: "wild", initialSelection: "quest:q_escort" },
};
export const A_WorldNearby = {
  render: overlay,
  args: { layout: "floating", initialTab: "world", location: "wild", initialSpan: 60 },
};

// Option B — for comparison.
export const B_AreaCity = { render: overlay, args: { layout: "columns", initialTab: "area", location: "city" } };
export const B_WorldRegion = { render: overlay, args: { layout: "columns", initialTab: "world", location: "wild" } };
