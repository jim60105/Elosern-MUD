// Prototype of the landmark rite interface (design
// docs/superpowers/specs/2026-11-14-landmark-rites-design.md §12). Reference
// only: mock data, nothing dispatches; the strip above the stage shows the
// intent the real client would send.
//
// Try it: Enter / 走近 on the arrival card enters the AVG stage; pick a story
// with its digit, the arrows + Enter, or a click; click or Space / Enter on
// the message window to read the scene line by line; click a figure on the
// stage (or ← / →) to change who performs; Esc / 退開 steps back to the map,
// where the 儀式 entry under the place card reopens the card.
import { h } from "vue";
import LandmarkRitesPrototype from "./LandmarkRitesPrototype.vue";

const render = (args) => ({ render: () => h(LandmarkRitesPrototype, { ...args, key: JSON.stringify(args) }) });

export default {
  title: "Design/LandmarkRites",
  component: LandmarkRitesPrototype,
  render,
  parameters: { layout: "fullscreen" },
  argTypes: {
    initialPhase: { control: "select", options: ["arrival", "menu", "map"] },
    companions: { control: { type: "range", min: 0, max: 3, step: 1 } },
    motion: { control: "inline-radio", options: ["full", "off"] },
  },
};

// The new card: arriving on an unlit district's landmark.
export const Arrival = { args: { initialPhase: "arrival" } };
// The archetype art has not been generated yet: the quiet ink band.
export const ArrivalNoArt = { name: "Arrival No Art", args: { initialPhase: "arrival", art: false } };
// The new panel on the AVG stage: the party stands on the stage, the player
// performs by default, both stories still unexperienced.
export const Menu = { args: { initialPhase: "menu" } };
// A companion picked on the stage: the solo-only story is disabled with its
// reason, and the first story is already experienced (no pip).
export const MenuCompanion = { name: "Menu Companion", args: { initialPhase: "menu", initialPerformer: 7, initialSeen: ["drink"] } };
// No story declares a watch scene (changes 1–4): the figures are not
// pickable and the panel offers no switch.
export const MenuSoloOnly = { name: "Menu Solo Only", args: { initialPhase: "menu", watchScenes: false } };
// Alone, with a third story authored.
export const MenuAloneThree = { name: "Menu Alone Three", args: { initialPhase: "menu", companions: 0, third: true } };
// The stage without art: quiet ink behind the party.
export const MenuNoArt = { name: "Menu No Art", args: { initialPhase: "menu", art: false } };
// Stepped back: the map with the 儀式 entry under the place card.
export const SteppedBack = { name: "Stepped Back", args: { initialPhase: "map", initialSeen: ["drink"] } };
// The one city landmark: the same card over the room's own stage.
export const CityArrival = { name: "City Arrival", args: { initialPhase: "arrival", city: true } };
// Motion off: every state lands at once.
export const MotionOff = { name: "Motion Off", args: { initialPhase: "menu", motion: "off" } };
