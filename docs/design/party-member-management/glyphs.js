// Approved visual prototype of the party window, shop, and navigation
// (docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md).
// Reference only. Existing dock glyphs are reused by key; the paths below
// are the new 24x24 stroke glyphs the implementation adds to dock-icons.js.
import { GLYPHS as DOCK } from "../../../web/webclient-app/components/dock-icons.js";

export const NEW_GLYPHS = {
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

export function pathFor(key) {
  return NEW_GLYPHS[key] ?? DOCK[key] ?? null;
}
