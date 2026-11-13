// Synthetic, protocol-valid gallery panels at schema version 4 (change
// gallery-v4-validators): one category at a time. No production character,
// item or monster data. Every exported panel passes validateGalleryPanel
// (web/static/webclient/js/tests/gallery_fixtures_v4.test.js); since
// gallery-v4-cutover these are the only gallery fixtures stories and tests use.

export const GALLERY_V4_IDS = Array.from(
  { length: 16 },
  (_, index) => `20000000-0000-4000-8000-${String(index + 1).padStart(12, "0")}`,
);

// Deterministic stand-ins for the canonical digests (a revision, a resource
// version, a retention token). Only their exact shape matters to a fixture.
const digest = (seed) => String(seed).padStart(2, "0") + "0123456789abcdef".repeat(4).slice(0, 62);
const FINGERPRINT = "a".repeat(64);

const LIVE = "portrait:character:7001";
const TWIN = "portrait:character:7004";
const COMPANION = "portrait:character:7002";
const SQUIRE = "portrait:character:7003";
const BEAST = "portrait:monster:synthetic_beast";
const WRAITH = "portrait:monster:synthetic_wraith";
const DRAKE = "portrait:monster:synthetic_drake";
const KEEPER = "portrait:character:7101";
const SCRIBE = "portrait:character:7102";

// On 768x1024 portrait aspect: w=0.5 => h=0.375
const PORTRAIT_RECT = { x: 0.25, y: 0.06, w: 0.5, h: 0.375 };
const PORTRAIT_SIZE = { width: 768, height: 1024 };

const parts = (subject) => {
  const [, directory, key] = subject.split(":");
  return { directory, key };
};

// The subject's committed silhouette: the gallery's one permitted terminal.
const alpha = (key) => ({
  kind: "alpha_mask",
  source_id: `gallery.alpha:${key}`,
  rank: 100,
  resource: {
    resource_id: `defaults/${key}.webp`,
    version: digest(90),
    url: `/art/defaults/${key}.webp`,
    origin: "silhouette",
    geometry: { image_size: null, face_rect: PORTRAIT_RECT, stage: null, aspect_ratio: "3:4" },
  },
});

// One exact gallery original of `subject`: a rank-10 runtime candidate, its
// silhouette terminal and a retention entry authorizing that same source.
const original = (subject, index, { stage = { scale: 1, x: 0, y: 0 }, silhouette = "woman" } = {}) => {
  const imageId = GALLERY_V4_IDS[index];
  const { directory, key } = parts(subject);
  return {
    subject_id: `${digest(1)}:${imageId}`,
    revision: digest(index + 10),
    generation_subject: subject,
    generation_state: "done",
    attempts: [{
      type: "image",
      source_id: `gallery.original:${imageId}`,
      rank: 10,
      resource: {
        resource_id: `gallery/${directory}/${key}/${imageId}.webp`,
        version: digest(index + 20),
        url: `/art/gallery/${directory}/${key}/${imageId}.webp`,
        origin: "runtime",
        geometry: { image_size: PORTRAIT_SIZE, face_rect: PORTRAIT_RECT, stage, aspect_ratio: "3:4" },
      },
    }],
    terminal: alpha(silhouette),
    retention_sources: [{ source_id: `gallery.original:${imageId}`, token: digest(index + 30) }],
  };
};

// A row with no stored output: truthful generation state and no image.
const empty = (subject, index, generation) => ({
  subject_id: `${digest(1)}:${GALLERY_V4_IDS[index]}`,
  revision: digest(index + 10),
  generation_subject: subject,
  generation_state: generation,
  attempts: [],
  terminal: null,
  retention_sources: [],
});

// One catalog-admitted official image: a rank-10 official candidate.
const official = (subject, index, identity) => ({
  subject_id: `${digest(1)}:${digest(index + 40).slice(0, 36)}`,
  revision: digest(index + 50),
  generation_subject: subject,
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
      geometry: { image_size: PORTRAIT_SIZE, face_rect: PORTRAIT_RECT, stage: null, aspect_ratio: "3:4" },
    },
  }],
  terminal: alpha("elder"),
  retention_sources: [{ source_id: `gallery.official:${identity}`, token: digest(index + 60) }],
});

const card = (subject, index, changes = {}) => ({
  image_id: GALLERY_V4_IDS[index],
  status: "card",
  label: "肖像",
  artwork: original(subject, index),
  is_default: false,
  chips: ["預設臉框"],
  requested_fields: ["appearance"],
  binding_present: false,
  created_at: 1700000800 - index * 100,
  ...changes,
});

const tile = (subject, display_name, { card_count = 1, is_current = false, artwork = null } = {}) => ({
  subject_key: subject,
  kind: `portrait:${parts(subject).directory}`,
  display_name,
  is_current,
  card_count,
  artwork,
});

const group = (key, subjects, changes = {}) => ({
  key, label: null, seen: null, total: null, expanded: true, count: subjects.length, subjects, ...changes,
});

const categories = (counts, enabled = {}) => ["mine", "party", "people", "monster", "scene"].map((key) => {
  const on = enabled[key] ?? !["people", "scene"].includes(key);
  return { key, count: counts[key] ?? 0, enabled: on, reason: on ? null : "尚未開放" };
});

const CHARACTER_CAPABILITIES = {
  supports_bindings: true, supports_field_selection: true, supports_free_text: true,
  supports_personal_official_preferences: true, supports_face_rect: true,
  supports_stage: true, supports_card_delete: true, max_cards: null,
};
const MONSTER_CAPABILITIES = {
  supports_bindings: false, supports_field_selection: false, supports_free_text: false,
  supports_personal_official_preferences: false, supports_face_rect: true,
  supports_stage: true, supports_card_delete: false, max_cards: 1,
};
const BARE_EQUIPMENT = {
  weapon_main: { value: null, display_name: "未裝備" },
  weapon_off: { value: null, display_name: "未裝備" },
  armor: { value: null, display_name: "未裝備" },
  accessories: { value: [], display_names: [], equipped_count: 0 },
};
const NO_SELECTION = {
  selected: null, description: null, cards: [], official_entries: [], equipment_summary: null,
  capabilities: null, binding_warnings: [], error_state: null,
};
const HEADER = { schema_version: 4, available: true, kind: "gallery" };

const LIVE_CARDS = [
  card(LIVE, 0, { is_default: true, binding_present: true, chips: ["主手", "防具", "預設臉框", "目前預設"] }),
  card(LIVE, 1, { binding_present: true, chips: ["飾品", "預設臉框"] }),
  card(LIVE, 2, { chips: ["自訂臉框"] }),
  card(LIVE, 3, { artwork: original(LIVE, 3, { stage: { scale: 0.6, x: -0.2, y: 0.1 } }) }),
  {
    image_id: GALLERY_V4_IDS[4], status: "pending", label: "肖像（生成中）", artwork: empty(LIVE, 4, "pending"),
    is_default: false, binding_present: false, chips: [], requested_fields: [], created_at: 1700000200,
  },
  {
    image_id: GALLERY_V4_IDS[5], status: "failed", label: "暫時無法生成，稍後再試（sd_connection_error）",
    artwork: empty(LIVE, 5, "failed"), is_default: false, binding_present: false, chips: [],
    requested_fields: [], created_at: 1700000100,
  },
];

// Mine: the live character (current, selected) opens a tray of cards —
// default, bound, custom face, staged, pending and failed — plus official
// read-only entries; a second account character sits beside it.
export const GALLERY_V4_MINE = {
  ...HEADER,
  categories: categories({ mine: 2, party: 2, monster: 3 }),
  category: "mine",
  groups: [group("mine", [
    tile(LIVE, "夜行者", { card_count: 4, is_current: true, artwork: original(LIVE, 0) }),
    tile(TWIN, "晨星", { card_count: 0 }),
  ])],
  selected: LIVE,
  description: null,
  cards: LIVE_CARDS,
  official_entries: [
    {
      identity: "preset/synthetic_preset/dawn.webp",
      artwork: official(LIVE, 0, "preset/synthetic_preset/dawn.webp"),
      is_current: false,
      is_catalog_default: true,
    },
    {
      identity: "preset/synthetic_preset/dusk.webp",
      artwork: official(LIVE, 1, "preset/synthetic_preset/dusk.webp"),
      is_current: true,
      is_catalog_default: false,
    },
  ],
  equipment_summary: {
    weapon_main: { value: "synthetic_sword", display_name: "暗影劍刃" },
    weapon_off: { value: null, display_name: "未裝備" },
    armor: { value: "synthetic_coat", display_name: "黑夜長袍" },
    accessories: { value: ["synthetic_brooch", "synthetic_ring"], display_names: ["銀月髮飾", "暮光耳環"], equipped_count: 2 },
  },
  capabilities: { ...CHARACTER_CAPABILITIES },
  binding_warnings: [
    { image_id: GALLERY_V4_IDS[0], label: "肖像", conditions: ["主手：暗影劍刃", "防具：黑夜長袍"] },
    { image_id: GALLERY_V4_IDS[1], label: "肖像", conditions: ["飾品：銀月髮飾、暮光耳環（任一）"] },
  ],
  error_state: { code: "sd_connection_error", at: 1700000100 },
};

// Mine with the selected live character holding no card, official entry,
// warning or recorded error yet: the empty-card guidance frame.
export const GALLERY_V4_MINE_BLANK = {
  ...GALLERY_V4_MINE,
  groups: [group("mine", [
    tile(LIVE, "夜行者", { card_count: 0, is_current: true }),
    tile(TWIN, "晨星", { card_count: 0 }),
  ])],
  cards: [],
  official_entries: [],
  binding_warnings: [],
  error_state: null,
};

// Mine with a full account roster: six characters, the live one first and
// selected, so its tray opens under the first row and the rest of the roster
// continues below it. Its tray holds three cards and one official entry.
const ROSTER = [7005, 7006, 7007, 7008].map((id) => `portrait:character:${id}`);
export const GALLERY_V4_MINE_ROSTER = {
  ...GALLERY_V4_MINE,
  categories: categories({ mine: 6, party: 2, monster: 3 }),
  groups: [group("mine", [
    tile(LIVE, "夜行者", { card_count: 3, is_current: true, artwork: original(LIVE, 8) }),
    tile(TWIN, "晨星", { card_count: 0 }),
    tile(ROSTER[0], "銀弦", { card_count: 2, artwork: original(ROSTER[0], 12) }),
    tile(ROSTER[1], "灰燼", { artwork: original(ROSTER[1], 13) }),
    tile(ROSTER[2], "潮汐守望者", { card_count: 5, artwork: original(ROSTER[2], 14) }),
    tile(ROSTER[3], "白鴉", { card_count: 0 }),
  ])],
  cards: [
    card(LIVE, 8, { is_default: true, chips: ["預設臉框", "目前預設"] }),
    card(LIVE, 9),
    card(LIVE, 10, { chips: ["自訂臉框"] }),
  ],
  official_entries: [GALLERY_V4_MINE.official_entries[0]],
  binding_warnings: [],
  error_state: null,
};

// Party: two companions in one unlabelled group, the first selected.
export const GALLERY_V4_PARTY = {
  ...HEADER,
  categories: categories({ mine: 2, party: 2, monster: 3 }),
  category: "party",
  groups: [group("party", [
    tile(COMPANION, "旅伴", { artwork: original(COMPANION, 6) }),
    tile(SQUIRE, "侍從", { card_count: 0 }),
  ])],
  selected: COMPANION,
  description: null,
  cards: [card(COMPANION, 6, { is_default: true, chips: ["預設臉框", "目前預設"] })],
  official_entries: [],
  equipment_summary: BARE_EQUIPMENT,
  capabilities: { ...CHARACTER_CAPABILITIES },
  binding_warnings: [],
  error_state: null,
};

// Monster: threat-tier groups with seen / total; a tier with no sighting
// keeps its heading and no tile. The selected species holds its single card.
export const GALLERY_V4_MONSTER = {
  ...HEADER,
  categories: categories({ mine: 2, party: 2, monster: 3 }),
  category: "monster",
  groups: [
    group("tier:common", [
      tile(BEAST, "測試魔物", { artwork: original(BEAST, 7, { silhouette: "monster_anon" }) }),
      tile(WRAITH, "測試幽影", { card_count: 0 }),
    ], { label: "常見", seen: 2, total: 4 }),
    group("tier:elite", [tile(DRAKE, "測試飛龍", { card_count: 0 })], { label: "菁英", seen: 1, total: 2 }),
    group("tier:boss", [], { label: "首領", seen: 0, total: 1 }),
  ],
  selected: BEAST,
  description: null,
  cards: [{
    ...card(BEAST, 7, { requested_fields: [] }),
    artwork: original(BEAST, 7, { silhouette: "monster_anon" }),
  }],
  official_entries: [],
  equipment_summary: null,
  capabilities: { ...MONSTER_CAPABILITIES },
  binding_warnings: [],
  error_state: null,
};

// An enabled category with no subject: nothing selected, no card facts.
export const GALLERY_V4_EMPTY = {
  ...HEADER,
  categories: categories({ mine: 1, party: 0, monster: 3 }),
  category: "party",
  groups: [],
  ...NO_SELECTION,
};

// People (enabled here only to exercise group expansion): the first place is
// expanded and its first person selected with no image yet; the other places
// are collapsed, carrying their count and no subjects.
export const GALLERY_V4_PEOPLE = {
  ...HEADER,
  categories: categories({ mine: 2, party: 2, people: 14, monster: 3 }, { people: true }),
  category: "people",
  groups: [
    group("place:synthetic_inn", [
      tile(KEEPER, "旅店老闆", { card_count: 0 }),
      tile(SCRIBE, "抄寫員", { card_count: 0 }),
    ], { label: "測試旅店" }),
    group("place:synthetic_market", [], { label: "測試市集", expanded: false, count: 7 }),
    group("place:synthetic_harbor", [], { label: "測試港口", expanded: false, count: 5 }),
  ],
  selected: KEEPER,
  description: null,
  cards: [],
  official_entries: [],
  equipment_summary: BARE_EQUIPMENT,
  capabilities: { ...CHARACTER_CAPABILITIES },
  binding_warnings: [],
  error_state: null,
};

// People with every place collapsed: listed nothing, so nothing is selected.
export const GALLERY_V4_PEOPLE_COLLAPSED = {
  ...HEADER,
  categories: categories({ mine: 2, party: 2, people: 12, monster: 3 }, { people: true }),
  category: "people",
  groups: [
    group("place:synthetic_market", [], { label: "測試市集", expanded: false, count: 7 }),
    group("place:synthetic_harbor", [], { label: "測試港口", expanded: false, count: 5 }),
  ],
  ...NO_SELECTION,
};

// Story-only media remapping: the offline static server has no /art/gallery,
// /art/official or /art/defaults route, so the committed fallback artwork is
// substituted into the descriptors' own resources (their candidate, and the
// silhouette terminal that rides with it) for the cards, the official entries
// and the subject tiles. This is a display substitution for the showcase
// build, never a wire shape: the exported fixtures above stay protocol-valid.
export function galleryStoryModel(model = GALLERY_V4_MINE) {
  const result = structuredClone(model);
  if (result.available !== true) return result;
  const images = ["woman", "elder", "man", "woman", "elder", "man"];
  // On 864x1536 fallback aspect: h=0.16 => w=0.16*1536/864 ≈ 0.2847
  const fallbackRect = { x: 0.3576, y: 0.02, w: 0.2847, h: 0.16 };
  const substitute = (artwork, image) => {
    // A monster subject shows the committed monster silhouette, never a person.
    const key = artwork?.generation_subject?.startsWith("portrait:monster:") ? "monster_anon" : image;
    const candidate = artwork?.attempts?.find((entry) => entry.type === "image");
    if (candidate) {
      candidate.resource.url = `/art/defaults/${key}.webp`;
      candidate.resource.geometry.face_rect = { ...fallbackRect };
    }
    const terminal = artwork?.terminal;
    if (terminal) {
      terminal.resource.resource_id = `defaults/${key}.webp`;
      terminal.resource.url = `/art/defaults/${key}.webp`;
      terminal.source_id = `gallery.alpha:${key}`;
      terminal.resource.geometry.face_rect = { ...fallbackRect };
    }
  };
  result.cards.forEach((row, index) => substitute(row.artwork, images[index % images.length]));
  result.official_entries.forEach((row, index) => substitute(row.artwork, images[(index + 3) % images.length]));
  result.groups.forEach((row) => row.subjects.forEach((tile, index) => substitute(tile.artwork, images[(index + 1) % images.length])));
  return result;
}
