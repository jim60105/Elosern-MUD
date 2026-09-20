// Story fixture slices: see stories/fixtures.js (facade) for the public surface.

// The `art` payload when the scene asset is generated: the 16:9 scene
// renders cover-style and the 3:4 portrait catalog carries contextual
// names/roles; labels and alt text stay DOM nodes outside the bitmaps.
export const ART_PANEL_SAMPLE = {
  schema_version: 2,
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
  },
  portrait_catalog: {
    "101": {
      subject_key: "port_harbor_master",
      status: "done",
      url: "/art/portraits/port_harbor_master.png",
      aspect_ratio: "3:4",
      alt: "碼頭船長的肖像",
      placeholder: null,
      face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.5 },
      context: { name: "老周", role: "對話對象" },
    },
    "217": {
      subject_key: "port_river_ogre",
      status: "done",
      url: "/art/portraits/port_river_ogre.png",
      aspect_ratio: "3:4",
      alt: "河灣巨魔的肖像",
      placeholder: null,
      face_rect: { x: 0.3, y: 0.1, w: 0.4, h: 0.4 },
      context: { name: "河灣巨魔", role: "敵方" },
    },
  },
};

// The art panel while the scene asset is still generating: the scene is
// pending, there is no prior image (url/subject_key null), and the panel
// degrades to the truthful "missing" placeholder — no invented bitmap.
export const ART_PANEL_PENDING_SAMPLE = {
  schema_version: 2,
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
  },
  portrait_catalog: {
    "101": {
      subject_key: "port_harbor_master",
      status: "pending",
      url: null,
      aspect_ratio: null,
      alt: "碼頭船長的肖像",
      placeholder: { kind: "missing", label: "肖像圖像尚未生成" },
      face_rect: null,
      context: { name: "老周", role: "對話對象" },
    },
  },
};

// The registry-owned unavailable form for the art panel.
export const ART_PANEL_UNAVAILABLE_SAMPLE = {
  schema_version: 2,
  available: false,
  reason: { code: "art_unavailable", message: "場景圖像目前無法顯示" },
};