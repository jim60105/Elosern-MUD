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

// --- The scene artwork vocabulary (change unified-scene-rendering) ----------
//
// The scene descriptor's own facts: one logical place identity, the scene
// archetype's generation key, the ordered room-aware source chain and the
// retention authorizations the backend issues while a known-good output is
// still applicable. Scene ranks are room 10, generated 20, operator 30,
// bundled 40 and terminal 100; a scene resource carries no face rectangle and
// no placement triple (a landscape is not a portrait).

// One generated scene output: the runtime path carries its bounded cache
// version, so a regeneration is a new request rather than the cached bytes.
export function sceneResource(overrides = {}) {
  const version = overrides.version ?? fixtureDigest("scene-output");
  return {
    resource_id: "scene/river_dawn.png",
    version,
    url: `/art/scene/river_dawn.png?v=${version}`,
    origin: "runtime",
    geometry: { image_size: null, face_rect: null, stage: null, aspect_ratio: null },
    ...overrides,
  };
}

// One committed bundled illustration: the required type artwork and the
// terminal image are the repository's own fingerprinted identities.
export function sceneBundledResource(key = "river_dawn", overrides = {}) {
  const fingerprint = fixtureDigest(`bundled-${key}`);
  return {
    resource_id: `bundled-scene/${key}/${fingerprint}.webp`,
    version: fingerprint,
    url: `/art/bundled-scene/${key}/${fingerprint}.webp`,
    origin: "bundled_official",
    geometry: { image_size: { width: 1536, height: 864 }, face_rect: null, stage: null, aspect_ratio: null },
    ...overrides,
  };
}

export const SCENE_SUBJECT = "scene:river_dawn";
export const SCENE_PLACE = "grid:t_synth_map:0,0";

// One scene descriptor: the generated archetype artwork ahead of the required
// bundled illustration, with the generated source authorized for retention.
export function sceneDescriptor(overrides = {}) {
  return {
    subject_id: SCENE_PLACE,
    revision: fixtureDigest("scene-revision"),
    generation_subject: SCENE_SUBJECT,
    generation_state: "done",
    attempts: [
      {
        type: "image",
        source_id: `scene.generated:${SCENE_SUBJECT}`,
        rank: 20,
        resource: sceneResource(),
      },
      {
        type: "image",
        source_id: "scene.bundled:river_dawn",
        rank: 40,
        resource: sceneBundledResource("river_dawn"),
      },
    ],
    terminal: {
      kind: "scene_image",
      source_id: "scene.terminal:city_street",
      rank: 100,
      resource: sceneBundledResource("city_street"),
    },
    retention_sources: [
      { source_id: `scene.generated:${SCENE_SUBJECT}`, token: fixtureDigest("scene-retention") },
    ],
    ...overrides,
  };
}

// One complete `art` scene block: exactly the archetype, the two display
// strings the stage renders outside the bitmap, and the canonical descriptor.
export function sceneBlock(overrides = {}, descriptor = null) {
  return {
    archetype: "river_dawn",
    label: "河畔清晨",
    alt: "河畔清晨的場景",
    artwork: descriptor ?? sceneDescriptor(),
    ...overrides,
  };
}

// The `art` payload when the scene asset is generated: the stage renders the
// descriptor's own successful source cover-cropped, and the 3:4 portrait
// catalog carries each admitted entity's complete canonical descriptor beside
// its contextual name/role; labels and alt text stay DOM nodes outside the
// bitmaps.
export const ART_PANEL_SAMPLE = {
  schema_version: 4,
  available: true,
  kind: "scene",
  scene: sceneBlock(),
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

// The art panel while the scene asset is still generating: the same logical
// place and generation subject are pending, the descriptor carries NO
// generated candidate (nothing is synthesized) but still authorizes the
// retained generated source, so a backdrop that already showed that image
// keeps it with the factual progress notice; the required bundled
// illustration is the current attempt. The admitted portrait entry keeps its
// complete descriptor with no real candidate: its own generation is pending
// and only the attribute-selected alpha terminal remains.
export const ART_PANEL_PENDING_SAMPLE = {
  schema_version: 4,
  available: true,
  kind: "scene",
  scene: sceneBlock(
    {},
    sceneDescriptor({
      generation_state: "pending",
      revision: fixtureDigest("scene-revision-pending"),
      attempts: [
        {
          type: "image",
          source_id: "scene.bundled:river_dawn",
          rank: 40,
          resource: sceneBundledResource("river_dawn"),
        },
      ],
    }),
  ),
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

// The art panel after a FAILED regeneration of the same scene: the recorded
// failure is a reached fact the backdrop must show, the retained generated
// source stays authorized (its pixels remain truthful), and the healthy
// bundled illustration is the current attempt.
export const ART_PANEL_FAILED_SAMPLE = {
  ...ART_PANEL_PENDING_SAMPLE,
  scene: sceneBlock(
    {},
    sceneDescriptor({
      generation_state: "failed",
      revision: fixtureDigest("scene-revision-failed"),
      attempts: [
        {
          type: "fault",
          source_id: `scene.generated:${SCENE_SUBJECT}`,
          rank: 20,
          reason: "generation_failed",
        },
        {
          type: "image",
          source_id: "scene.bundled:river_dawn",
          rank: 40,
          resource: sceneBundledResource("river_dawn"),
        },
      ],
    }),
  ),
};

// The art panel for a room whose authored scene metadata cannot be honored:
// the archetype is null, the single reached fact is the configuration failure
// at the town terminal's own position, and the permitted town terminal image
// follows it. No generation is claimed.
export const ART_PANEL_MALFORMED_SAMPLE = {
  schema_version: 4,
  available: true,
  kind: "scene",
  scene: sceneBlock(
    { archetype: null, label: "場景", alt: "場景" },
    sceneDescriptor({
      subject_id: "room:1",
      generation_subject: null,
      generation_state: null,
      revision: fixtureDigest("scene-revision-malformed"),
      attempts: [
        {
          type: "fault",
          source_id: "scene.terminal:city_street",
          rank: 100,
          reason: "configuration_invalid",
        },
      ],
      terminal: {
        kind: "scene_image",
        source_id: "scene.terminal:city_street",
        rank: 100,
        resource: sceneBundledResource("city_street"),
      },
      retention_sources: [],
    }),
  ),
  portrait_catalog: {},
};

// The registry-owned unavailable form for the art panel.
export const ART_PANEL_UNAVAILABLE_SAMPLE = {
  schema_version: 4,
  available: false,
  reason: { code: "art_unavailable", message: "場景圖像目前無法顯示" },
};
