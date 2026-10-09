// Approved-direction prototype of the exploration screen redesign
// (docs/superpowers/specs/2026-10-10-scene-overview-redesign-design.md).
// Reference only: self-contained mock data, not wired to any payload.
//
// Try it: hover the compass to aim, click to move, hold to keep walking
// (steer with the cursor), or focus it and use the arrows / [ ] / Enter.
// Digits 1–9 pick the presence rail; Tab walks compass → rail → place
// card → 建議.
import { h } from "vue";
import ScenePrototype from "./ScenePrototype.vue";
import { START_SCENES } from "./prototype-data.js";

const render = (args) => ({ render: () => h(ScenePrototype, { ...args, key: JSON.stringify(args) }) });

export default { title: "Design/SceneOverviewRedesign", render };

// Eight-way wilderness on real lattice bearings; a river blocks one cell.
export const Wilderness = { args: { startScene: START_SCENES.wilderness } };
// A grid-layer town: irregular bearings, a crossing to the wilderness by
// direction word, an up stair and a portal on the outer ring, a locked door.
export const TownGate = { args: { startScene: START_SCENES.town } };
// A busy square: the rail overflows into 其餘 N.
export const MarketSquare = { args: { startScene: START_SCENES.square } };
// An interior: no coordinates, so 北 resolves by word and the rest are portals.
export const GuildInterior = { args: { startScene: START_SCENES.guild } };
// A person chosen from the rail: standee in from the right, verbs centred.
export const PersonFocus = { args: { startScene: START_SCENES.guild, initialFocus: "grian" } };
