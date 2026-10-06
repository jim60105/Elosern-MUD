// Synthetic, protocol-valid gallery records. No production character/item data.
export const GALLERY_IDS = Array.from({ length: 8 }, (_, index) => `10000000-0000-4000-8000-${String(index + 1).padStart(12, "0")}`);
const card = (index, changes = {}) => ({
  image_id: GALLERY_IDS[index], status: "card",
  label: "肖像",
  url: `/art/gallery/character/7001/${GALLERY_IDS[index]}.webp`,
  // On 768x1024 portrait aspect: w=0.5 => h=0.375
  face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.375 },
  stage: { scale: 1, x: 0, y: 0 },
  is_default: false, chips: ["預設臉框"], requested_fields: ["appearance"],
  binding_present: false, created_at: 1700000800 - index * 100,
  ...changes,
});
export const GALLERY_SAMPLE = {
  schema_version: 1, available: true, kind: "gallery",
  subjects: [
    { subject_key: "portrait:character:7001", kind: "portrait:character", display_name: "夜行者", is_puppet: true },
    { subject_key: "portrait:character:7002", kind: "portrait:character", display_name: "旅伴", is_puppet: false },
    { subject_key: "portrait:monster:synthetic_beast", kind: "portrait:monster", display_name: "測試魔物", is_puppet: false },
  ],
  selected: "portrait:character:7001",
  filters: { all: 8, defaults: 1, bound: 3, pending: 1, failed: 1 },
  capabilities: { supports_bindings: true, supports_field_selection: true, supports_free_text: true, max_cards: null },
  cards: [
    card(0, { is_default: true, binding_present: true, chips: ["主手", "防具", "預設臉框", "目前預設"] }),
    card(1, { binding_present: true, chips: ["飾品", "預設臉框"] }),
    card(2, { binding_present: true, chips: ["防具", "預設臉框"] }),
    card(3), card(4),
    card(5, { stage: { scale: 0.6, x: -0.2, y: 0.1 } }),
    { image_id: GALLERY_IDS[6], status: "pending", label: "肖像（生成中）", url: null, face_rect: null, stage: null, is_default: false, binding_present: false, chips: [], requested_fields: [], created_at: 1700000200 },
    { image_id: GALLERY_IDS[7], status: "failed", label: "暫時無法生成，稍後再試（sd_connection_error）", url: null, face_rect: null, stage: null, is_default: false, binding_present: false, chips: [], requested_fields: [], created_at: 1700000100 },
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
      url: `/art/official/${"a".repeat(64)}/preset/synthetic_preset/dawn.webp`,
      face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.375 },
      is_current: false,
      is_catalog_default: true,
    },
    {
      identity: "preset/synthetic_preset/dusk.webp",
      url: `/art/official/${"a".repeat(64)}/preset/synthetic_preset/dusk.webp`,
      face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.375 },
      is_current: false,
      is_catalog_default: false,
    },
    {
      identity: "preset/synthetic_preset/midnight.webp",
      url: `/art/official/${"a".repeat(64)}/preset/synthetic_preset/midnight.webp`,
      face_rect: { x: 0.2, y: 0.1, w: 0.5, h: 0.375 },
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
  capabilities: { supports_bindings: false, supports_field_selection: false, supports_free_text: false, max_cards: 1 },
  equipment_summary: null,
};

// Story-only media remapping: the offline static server has no /art/gallery
// route. Reuse committed fallback artwork and its illustrative face bounds.
export function galleryStoryModel(model = GALLERY_SAMPLE) {
  const result = structuredClone(model);
  const images = ["woman", "elder", "man", "woman", "elder", "man"];
  result.cards.forEach((row, index) => {
    if (row.url) {
      row.url = `/art/defaults/${images[index % images.length]}.webp`;
      // On 864x1536 fallback aspect: h=0.16 => w=0.16*1536/864 ≈ 0.2847
      row.face_rect = { x: 0.3576, y: 0.02, w: 0.2847, h: 0.16 };
    }
  });
  // The offline static server has no /art/official route either: reuse the
  // committed fallback artwork for the official previews too.
  result.official_entries.forEach((row, index) => {
    row.url = `/art/defaults/${images[(index + 3) % images.length]}.webp`;
    row.face_rect = { x: 0.3576, y: 0.02, w: 0.2847, h: 0.16 };
  });
  return result;
}
