// Prototype of the wilderness travel mode (blueprint layout A) and the
// lightweight camping cards. Reference only: mock terrain, reveal, routing
// and reserve prediction from travel-model.js; nothing dispatches, and the
// intents the real client would send appear in the strip above the stage.
//
// Try it: hover a revealed cell to preview a route, click to lock it, click
// again or Enter to depart (any key stops); arrows aim a neighbour and Enter
// steps, holding an arrow walks; 紮營 opens the camp card. The strip jumps
// the clock between light phases.
import { h } from "vue";
import WildernessTravelPrototype from "./WildernessTravelPrototype.vue";

const render = (args) => ({ render: () => h(WildernessTravelPrototype, { ...args, key: JSON.stringify(args) }) });

export default {
  title: "Design/WildernessTravel",
  component: WildernessTravelPrototype,
  render,
  argTypes: {
    scenario: {
      control: "select",
      options: ["free", "route", "dusk", "night", "woodland", "camp", "campfire", "landmark"],
    },
    motion: { control: "inline-radio", options: ["full", "off"] },
    zoom: { control: { type: "range", min: 18, max: 46, step: 4 } },
  },
};

// Morning on the road east of the capital, the trail walked yesterday
// revealed behind the party.
export const Morning = { args: { scenario: "free" } };
// Known land: yesterday's corridor is revealed, so today's leg to the
// watchtower is one previewed route with the pace stop and its camp mark.
export const RoutePreview = { name: "Route Preview", args: { scenario: "route" } };
// Dusk: the warm tint, the shorter twilight sight.
export const Dusk = { args: { scenario: "dusk" } };
// Night: sight shrinks to one cell, memory fades, only lights are sighted.
export const Night = { args: { scenario: "night" } };
// Inside the woods: ground sight is one cell.
export const Woodland = { args: { scenario: "woodland" } };
// The camp card at dusk with a tired party.
export const CampCard = { name: "Camp Card", args: { scenario: "camp" } };
// The campfire beat after confirming the camp.
export const Campfire = { args: { scenario: "campfire" } };
// Standing on the watchtower: the landmark card and the lit district.
export const LandmarkArrival = { name: "Landmark Arrival", args: { scenario: "landmark" } };
// Motion off: no camera glide, no flame, the campfire shows its result.
export const MotionOff = { name: "Motion Off", args: { scenario: "route", motion: "off" } };
