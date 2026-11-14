// Synthetic `rite` panels (landmark-rite-panel D1) for the landmark rite
// surfaces' stories and tests. Every name is synthetic; the shape is the
// committed wire shape, and tests/rite/surfaces.test.js passes these panels
// through the real validator so they can never drift from it.
import { sceneBundledResource, sceneDescriptor } from "./art_panels.js";

// The committed art panel the rite artwork is judged by (its availability).
export const RITE_ART_PANEL = { schema_version: 4, available: true, kind: "scene", portrait_catalog: {} };

// The archetype scene descriptor: the bundled shrine illustration.
export const RITE_ART = sceneDescriptor({
  subject_id: "wilderness:合成高地:120,40",
  generation_subject: "scene:shrine_interior",
  attempts: [
    {
      type: "image",
      source_id: "scene.bundled:shrine_interior",
      rank: 40,
      resource: sceneBundledResource("shrine_interior", { url: "/art/scenes/shrine_interior.webp" }),
    },
  ],
  retention_sources: [],
});

export function ritePanel(overrides = {}) {
  return {
    schema_version: 1,
    available: true,
    kind: "rite",
    district: { key: "synthetic_highlands", name: "合成高地", landmark: "合成石龕", lit: false },
    guardian: { name: "合成泉聲", form: "水面映出的聲音，只在有人俯身時開口。" },
    art: null,
    options: [
      { key: "drink", label: "俯身飲下", companion: true },
      { key: "bathe", label: "浸入池中", companion: false },
    ],
    performers: [{ member_id: null, name: "合成旅人", owner: true }],
    delivery: null,
    seen: [],
    ...overrides,
  };
}

export function ritePanelWithArt(overrides = {}) {
  return ritePanel({ art: RITE_ART, ...overrides });
}

// The party standing on the stage: the controlled character and two
// companions, the first admitted to every rite that admits a companion.
export const RITE_PARTY = [
  { member_id: null, name: "合成旅人", owner: true },
  { member_id: 7, name: "合成同伴", owner: false },
  { member_id: 8, name: "合成學徒", owner: false },
];
