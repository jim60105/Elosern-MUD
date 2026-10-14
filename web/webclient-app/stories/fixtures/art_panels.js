// Story fixture slices: see stories/fixtures.js (facade) for the public surface.

// The canonical artwork descriptor vocabulary (change
// unified-portrait-image-contract): the ONE shape the art panel's catalog
// values and the roster row portraits both carry. `revision` and each
// resource `version` are deterministic 64-character digests of their own
// fixture label — the wire validators bound the SHAPE, and no reader
// recomputes either from the facts.
export function fixtureDigest(label) {
  let out = "";
  for (let i = 0; i < 64; i += 1) {
    out += "0123456789abcdef"[(label.charCodeAt(i % label.length) + i) % 16];
  }
  return out;
}

export function artworkResource(overrides = {}) {
  return {
    resource_id: "portrait/character/port_harbor_master.png",
    version: fixtureDigest("resource"),
    url: "/art/portraits/port_harbor_master.png",
    origin: "runtime",
    geometry: {
      image_size: null,
      face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.5 },
      stage: { scale: 1.1, x: -0.1, y: 0 },
      aspect_ratio: "3:4",
    },
    ...overrides,
  };
}

// The committed silhouette alpha mask at its own terminal rank. Its resource
// is deliberately distinct from every candidate's, so the validator's
// "terminal duplicates an attempt resource" rule is never tripped.
export function artworkTerminal(overrides = {}) {
  return {
    kind: "alpha_mask",
    source_id: "portrait.alpha:man",
    rank: 100,
    resource: artworkResource({
      resource_id: "defaults/man.webp",
      version: fixtureDigest("terminal"),
      url: "/art/defaults/man.webp",
      origin: "silhouette",
      geometry: {
        image_size: null,
        face_rect: { x: 0.35, y: 0.03, w: 0.29, h: 0.16 },
        stage: null,
        aspect_ratio: "3:4",
      },
    }),
    ...overrides,
  };
}

export function artworkDescriptor(overrides = {}) {
  return {
    subject_id: "port_harbor_master",
    revision: fixtureDigest("revision"),
    generation_subject: "port_harbor_master",
    generation_state: "done",
    attempts: [
      {
        type: "image",
        source_id: "portrait.default:1",
        rank: 30,
        resource: artworkResource(),
      },
    ],
    terminal: artworkTerminal(),
    retention_sources: [],
    ...overrides,
  };
}

// One catalog value: exactly the canonical descriptor plus its bounded display
// context.
export function artworkEntry(overrides = {}, descriptor = null) {
  return {
    artwork: descriptor ?? artworkDescriptor(),
    context: { name: "老周", role: "對話對象" },
    ...overrides,
  };
}

// The `art` payload when the scene asset is generated: the 16:9 scene
// renders cover-style and the 3:4 portrait catalog carries each admitted
// entity's complete canonical descriptor beside its contextual name/role;
// labels and alt text stay DOM nodes outside the bitmaps.
export const ART_PANEL_SAMPLE = {
  schema_version: 3,
  available: true,
  kind: "scene",
  scene: {
    archetype: "river_dawn",
    label: "河畔清晨",
    subject_key: "scene_river_dawn",
    status: "done",
    url: "/art/scenes/scene_river_dawn.png",
    aspect_ratio: "16:9",
    alt: "河畔清晨的場景",
    placeholder: null,
    stage: { scale: 1, x: 0, y: 0 },
  },
  portrait_catalog: {
    "101": artworkEntry({ context: { name: "老周", role: "對話對象" } }),
    "217": artworkEntry(
      {
        context: { name: "河灣巨魔", role: "敵方" },
      },
      artworkDescriptor({
        subject_id: "port_river_ogre",
        generation_subject: "port_river_ogre",
        attempts: [
          {
            type: "image",
            source_id: "portrait.default:2",
            rank: 30,
            resource: artworkResource({
              resource_id: "portrait/character/port_river_ogre.png",
              version: fixtureDigest("ogre"),
              url: "/art/portraits/port_river_ogre.png",
              geometry: {
                image_size: null,
                face_rect: { x: 0.3, y: 0.1, w: 0.4, h: 0.4 },
                stage: { scale: 1, x: 0, y: 0 },
                aspect_ratio: "3:4",
              },
            }),
          },
        ],
        terminal: artworkTerminal({
          source_id: "portrait.alpha:monster_anon",
          resource: artworkResource({
            resource_id: "defaults/monster_anon.webp",
            version: fixtureDigest("monster-terminal"),
            url: "/art/defaults/monster_anon.webp",
            origin: "silhouette",
            geometry: {
              image_size: null,
              face_rect: { x: 0.35, y: 0.03, w: 0.29, h: 0.16 },
              stage: null,
              aspect_ratio: "3:4",
            },
          }),
        }),
      }),
    ),
  },
};

// The art panel while the scene asset is still generating: the scene is
// pending, there is no prior image (url/subject_key null), and the panel
// degrades to the truthful "missing" placeholder — no invented bitmap. The
// admitted portrait entry keeps its complete descriptor with no real
// candidate: its own generation is pending and only the attribute-selected
// alpha terminal remains.
export const ART_PANEL_PENDING_SAMPLE = {
  schema_version: 3,
  available: true,
  kind: "scene",
  scene: {
    archetype: "river_dawn",
    label: "河畔清晨",
    subject_key: null,
    status: "pending",
    url: null,
    aspect_ratio: null,
    alt: "河畔清晨的場景",
    placeholder: { kind: "missing", label: "場景圖像尚未生成" },
    stage: null,
  },
  portrait_catalog: {
    "101": artworkEntry(
      { context: { name: "老周", role: "對話對象" } },
      artworkDescriptor({
        subject_id: "port_harbor_master",
        generation_subject: "port_harbor_master",
        generation_state: "pending",
        attempts: [],
      }),
    ),
  },
};

// The registry-owned unavailable form for the art panel.
export const ART_PANEL_UNAVAILABLE_SAMPLE = {
  schema_version: 3,
  available: false,
  reason: { code: "art_unavailable", message: "場景圖像目前無法顯示" },
};
