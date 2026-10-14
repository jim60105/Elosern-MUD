// Synthetic, protocol-valid gallery records at schema version 3. No production
// character/item data.
export const GALLERY_IDS = Array.from({ length: 8 }, (_, index) => `10000000-0000-4000-8000-${String(index + 1).padStart(12, "0")}`);

// Deterministic stand-ins for the canonical digests (a revision, a resource
// version, a retention token). Only their exact shape matters to a fixture.
const digest = (seed) => String(seed).padStart(2, "0") + "0123456789abcdef".repeat(4).slice(0, 62);
const FINGERPRINT = "a".repeat(64);
const SUBJECT = "portrait:character:7001";

// The subject's committed silhouette: the gallery's one permitted terminal.
const alpha = (key, rect) => ({
  kind: "alpha_mask",
  source_id: `gallery.alpha:${key}`,
  rank: 100,
  resource: {
    resource_id: `defaults/${key}.webp`,
    version: digest(90),
    url: `/art/defaults/${key}.webp`,
    origin: "silhouette",
    geometry: { image_size: null, face_rect: rect, stage: null, aspect_ratio: "3:4" },
  },
});

// One exact gallery original: a rank-10 runtime candidate, its own silhouette
// terminal and a retention entry authorizing that same source.
const original = (index, imageId, { rect, stage, size, generation = "done" }) => ({
  subject_id: `${digest(1)}:${imageId}`,
  revision: digest(index + 10),
  generation_subject: SUBJECT,
  generation_state: generation,
  attempts: [{
    type: "image",
    source_id: `gallery.original:${imageId}`,
    rank: 10,
    resource: {
      resource_id: `gallery/character/7001/${imageId}.webp`,
      version: digest(index + 20),
      url: `/art/gallery/character/7001/${imageId}.webp`,
      origin: "runtime",
      geometry: { image_size: size, face_rect: rect, stage, aspect_ratio: "3:4" },
    },
  }],
  terminal: alpha("woman", rect),
  retention_sources: [{ source_id: `gallery.original:${imageId}`, token: digest(index + 30) }],
});

// A row with no stored output at all: truthful generation state and no image.
const empty = (index, imageId, generation) => ({
  subject_id: `${digest(1)}:${imageId}`,
  revision: digest(index + 10),
  generation_subject: SUBJECT,
  generation_state: generation,
  attempts: [],
  terminal: null,
  retention_sources: [],
});

// One exact catalog-admitted official image: a rank-10 official candidate plus
// its own silhouette terminal.
const official = (index, identity, { rect, size }) => ({
  // The exact-image tail is cut to the same length as a card's canonical UUID,
  // so one subject-identity bound covers both row kinds.
  subject_id: `${digest(1)}:${digest(index + 40).slice(0, 36)}`,
  revision: digest(index + 50),
  generation_subject: SUBJECT,
  generation_state: "done",
  attempts: [{
    type: "image",
    source_id: `gallery.official:${identity}`,
    rank: 10,
    resource: {
      resource_id: identity,
      version: FINGERPRINT,
      url: `/art/official/${FINGERPRINT}/${identity}`,
      origin: "official",
      geometry: { image_size: size, face_rect: rect, stage: null, aspect_ratio: "3:4" },
    },
  }],
  terminal: alpha("elder", rect),
  retention_sources: [{ source_id: `gallery.official:${identity}`, token: digest(index + 60) }],
});

// On 768x1024 portrait aspect: w=0.5 => h=0.375
const PORTRAIT_RECT = { x: 0.25, y: 0.06, w: 0.5, h: 0.375 };
const PORTRAIT_SIZE = { width: 768, height: 1024 };

const card = (index, changes = {}) => ({
  image_id: GALLERY_IDS[index],
  status: "card",
  label: "肖像",
  artwork: original(index, GALLERY_IDS[index], {
    rect: PORTRAIT_RECT,
    stage: { scale: 1, x: 0, y: 0 },
    size: PORTRAIT_SIZE,
  }),
  is_default: false,
  chips: ["預設臉框"],
  requested_fields: ["appearance"],
  binding_present: false,
  created_at: 1700000800 - index * 100,
  ...changes,
});

export const GALLERY_SAMPLE = {
  schema_version: 3, available: true, kind: "gallery",
  subjects: [
    { subject_key: "portrait:character:7001", kind: "portrait:character", display_name: "夜行者", is_puppet: true },
    { subject_key: "portrait:character:7002", kind: "portrait:character", display_name: "旅伴", is_puppet: false },
    { subject_key: "portrait:monster:synthetic_beast", kind: "portrait:monster", display_name: "測試魔物", is_puppet: false },
  ],
  selected: "portrait:character:7001",
  filters: { all: 8, defaults: 1, bound: 3, pending: 1, failed: 1 },
  capabilities: { supports_bindings: true, supports_field_selection: true, supports_free_text: true, supports_personal_official_preferences: true, max_cards: null },
  cards: [
    card(0, { is_default: true, binding_present: true, chips: ["主手", "防具", "預設臉框", "目前預設"] }),
    card(1, { binding_present: true, chips: ["飾品", "預設臉框"] }),
    card(2, { binding_present: true, chips: ["防具", "預設臉框"] }),
    card(3), card(4),
    card(5, { artwork: original(5, GALLERY_IDS[5], { rect: PORTRAIT_RECT, stage: { scale: 0.6, x: -0.2, y: 0.1 }, size: PORTRAIT_SIZE }) }),
    { image_id: GALLERY_IDS[6], status: "pending", label: "肖像（生成中）", artwork: empty(6, GALLERY_IDS[6], "pending"), is_default: false, binding_present: false, chips: [], requested_fields: [], created_at: 1700000200 },
    { image_id: GALLERY_IDS[7], status: "failed", label: "暫時無法生成，稍後再試（sd_connection_error）", artwork: empty(7, GALLERY_IDS[7], "failed"), is_default: false, binding_present: false, chips: [], requested_fields: [], created_at: 1700000100 },
  ],
  equipment_summary: {
    weapon_main: { value: "synthetic_sword", display_name: "暗影劍刃" },
    weapon_off: { value: null, display_name: "未裝備" },
    armor: { value: "synthetic_coat", display_name: "黑夜長袍" },
    accessories: { value: ["synthetic_brooch", "synthetic_ring"], display_names: ["銀月髮飾", "暮光耳環"], equipped_count: 2 },
  },
  binding_warnings: [
    { image_id: GALLERY_IDS[0], label: "肖像", conditions: ["主手：暗影劍刃", "防具：黑夜長袍"] },
    { image_id: GALLERY_IDS[1], label: "肖像", conditions: ["飾品：銀月髮飾、暮光耳環（任一）"] },
  ],
  error_state: { code: "sd_connection_error", at: 1700000100 },
  // The official read model: catalog-admitted read-only images of the selected
  // subject's content reference. Synthetic fingerprint and identities; the
  // third row is the retained personal selection.
  official_entries: [
    {
      identity: "preset/synthetic_preset/dawn.webp",
      artwork: official(0, "preset/synthetic_preset/dawn.webp", { rect: PORTRAIT_RECT, size: PORTRAIT_SIZE }),
      is_current: false,
      is_catalog_default: true,
    },
    {
      identity: "preset/synthetic_preset/dusk.webp",
      artwork: official(1, "preset/synthetic_preset/dusk.webp", { rect: PORTRAIT_RECT, size: PORTRAIT_SIZE }),
      is_current: false,
      is_catalog_default: false,
    },
    {
      identity: "preset/synthetic_preset/midnight.webp",
      artwork: official(2, "preset/synthetic_preset/midnight.webp", { rect: { x: 0.2, y: 0.1, w: 0.5, h: 0.375 }, size: PORTRAIT_SIZE }),
      is_current: true,
      is_catalog_default: false,
    },
  ],
};
export const GALLERY_EMPTY = {
  ...GALLERY_SAMPLE, cards: [], binding_warnings: [], error_state: null, official_entries: [],
  filters: { all: 0, defaults: 0, bound: 0, pending: 0, failed: 0 },
};
export const GALLERY_MONSTER = {
  ...GALLERY_EMPTY, selected: "portrait:monster:synthetic_beast", official_entries: [],
  capabilities: { supports_bindings: false, supports_field_selection: false, supports_free_text: false, supports_personal_official_preferences: false, max_cards: 1 },
  equipment_summary: null,
};

// Story-only media remapping: the offline static server has no /art/gallery,
// /art/official or /art/defaults route, so the committed fallback artwork is
// substituted into the descriptors' own resources (their candidate, and the
// silhouette terminal that rides with it). This is a display substitution for
// the showcase build, never a wire shape: the published fixture above stays
// the protocol-valid record.
export function galleryStoryModel(model = GALLERY_SAMPLE) {
  const result = structuredClone(model);
  const images = ["woman", "elder", "man", "woman", "elder", "man"];
  // On 864x1536 fallback aspect: h=0.16 => w=0.16*1536/864 ≈ 0.2847
  const fallbackRect = { x: 0.3576, y: 0.02, w: 0.2847, h: 0.16 };
  const substitute = (artwork, image) => {
    const candidate = artwork?.attempts?.find((entry) => entry.type === "image");
    if (candidate) {
      candidate.resource.url = `/art/defaults/${image}.webp`;
      candidate.resource.geometry.face_rect = { ...fallbackRect };
    }
    const terminal = artwork?.terminal;
    if (terminal) {
      terminal.resource.resource_id = `defaults/${image}.webp`;
      terminal.resource.url = `/art/defaults/${image}.webp`;
      terminal.source_id = `gallery.alpha:${image}`;
      terminal.resource.geometry.face_rect = { ...fallbackRect };
    }
  };
  result.cards.forEach((row, index) => {
    substitute(row.artwork, images[index % images.length]);
  });
  result.official_entries.forEach((row, index) => {
    substitute(row.artwork, images[(index + 3) % images.length]);
  });
  return result;
}
