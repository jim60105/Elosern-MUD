// Story fixture slices: see stories/fixtures.js (facade) for the public surface.
import { artworkDescriptor, artworkResource } from "./art_panels.js";

// The committed `lore_codex` panel v2 (webclient-lore-codex-panel): the
// eight codex categories in CODE_CATEGORIES mapping order, each with its
// discovered count, its registry total and its groups of slots (an entry
// slot with its rendered card fields, or an identity-free placeholder).
// Deterministic offline literals only.
const LORE_CODEX_PLACEHOLDER = Object.freeze({ placeholder: true });
const LORE_CODEX_ENTRY = (key, title, card, stage = null) =>
  Object.freeze({
    key,
    title,
    stage,
    art: null,
    card: Object.freeze(card.map((field) => Object.freeze(field))),
    locked_fields: Object.freeze([]),
  });
const LORE_CODEX_CATEGORY = (key, label, slots, group = { key, label: null }) =>
  Object.freeze({
    key,
    label,
    discovered: slots.filter((slot) => !slot.placeholder).length,
    total: slots.length,
    groups: Object.freeze([Object.freeze({ ...group, slots: Object.freeze(slots) })]),
  });

export const LORE_CODEX_PANEL_SAMPLE = Object.freeze({
  schema_version: 2,
  available: true,
  discovered_total: 4,
  total: 8,
  categories: Object.freeze([
    LORE_CODEX_CATEGORY("race", "種族", [
      LORE_CODEX_ENTRY("human", "平原族", [
        { name: "display_name_zh", value: "平原族" },
        { name: "description", value: "適應力最強的短命種，遍布灰河沿岸。" },
      ]),
      LORE_CODEX_PLACEHOLDER,
    ]),
    LORE_CODEX_CATEGORY("nation", "國家", []),
    LORE_CODEX_CATEGORY("region", "地域", [
      LORE_CODEX_ENTRY("grey_river", "灰河", [
        { name: "display_name_zh", value: "灰河" },
        { name: "terrain_flavor_zh", value: "終年起霧的寬緩河流，渡口夜燈明滅。" },
      ]),
    ]),
    LORE_CODEX_CATEGORY(
      "monster",
      "魔物",
      [
        LORE_CODEX_ENTRY(
          "mist_wolf",
          "霧骨狼",
          [
            { name: "display_name_zh", value: "霧骨狼" },
            { name: "description", value: "群棲於霧中的中型獸，骨白如霧。" },
            { name: "example_monsters_zh", value: "霧骨狼‧頭狼" },
          ],
          "defeated",
        ),
        LORE_CODEX_PLACEHOLDER,
      ],
      { key: "moderate", label: "中階" },
    ),
    LORE_CODEX_CATEGORY("element", "元素", []),
    LORE_CODEX_CATEGORY("magic", "魔法", []),
    LORE_CODEX_CATEGORY("anchor", "地點", [
      LORE_CODEX_ENTRY("misty_ford", "霧骨渡口", [
        { name: "display_name_zh", value: "霧骨渡口" },
        { name: "description", value: "灰河上的主要渡口，旅人與貨物的集散地。" },
      ]),
    ]),
    LORE_CODEX_CATEGORY("guild", "公會", [LORE_CODEX_PLACEHOLDER, LORE_CODEX_PLACEHOLDER]),
  ]),
});

export const LORE_CODEX_PANEL_EMPTY_SAMPLE = Object.freeze({
  schema_version: 2,
  available: true,
  discovered_total: 0,
  total: 3,
  categories: Object.freeze([
    LORE_CODEX_CATEGORY("race", "種族", [LORE_CODEX_PLACEHOLDER]),
    LORE_CODEX_CATEGORY("nation", "國家", [LORE_CODEX_PLACEHOLDER]),
    LORE_CODEX_CATEGORY("region", "地域", []),
    LORE_CODEX_CATEGORY("monster", "魔物", [LORE_CODEX_PLACEHOLDER], { key: "moderate", label: "中階" }),
    LORE_CODEX_CATEGORY("element", "元素", []),
    LORE_CODEX_CATEGORY("magic", "魔法", []),
    LORE_CODEX_CATEGORY("anchor", "地點", []),
    LORE_CODEX_CATEGORY("guild", "公會", []),
  ]),
});

export const LORE_CODEX_PANEL_UNAVAILABLE_SAMPLE = Object.freeze({
  schema_version: 2,
  available: false,
  reason: Object.freeze({
    code: "lore_codex_unavailable",
    message: "知識圖鑑目前無法顯示",
  }),
});
// Synthetic `lore_codex` v2 builders for the handbook codex tab stories and
// tests (handbook-codex-tab). Every key, title, label and field value a caller
// passes is invented test data; the builders add no shipped string.
export const CODEX_PLACEHOLDER = Object.freeze({ placeholder: true });

// One entry slot. `card` defaults to a title field plus one description field.
export function codexEntry(key, title, overrides = {}) {
  return {
    key,
    title,
    stage: null,
    art: null,
    card: [
      { name: "display_name_zh", value: title },
      { name: "description", value: `${title}的合成記述。` },
    ],
    locked_fields: [],
    ...overrides,
  };
}

// One category over `groups` ([{ key, label, slots }]); counts are derived.
export function codexCategory(key, label, groups) {
  const slots = groups.flatMap((group) => group.slots);
  return {
    key,
    label,
    discovered: slots.filter((slot) => !slot.placeholder).length,
    total: slots.length,
    groups,
  };
}

export function loreCodex(categories) {
  const slots = categories.flatMap((category) => category.groups.flatMap((group) => group.slots));
  return {
    schema_version: 2,
    available: true,
    discovered_total: slots.filter((slot) => !slot.placeholder).length,
    total: slots.length,
    categories,
  };
}

// One art descriptor with a single image attempt and no terminal, in the
// canonical descriptor shape the shared artwork lifecycle consumes.
export function codexArt(subject, url) {
  return artworkDescriptor({
    subject_id: subject,
    generation_subject: subject,
    attempts: [
      { type: "image", source_id: `${subject}:1`, rank: 30, resource: artworkResource({ resource_id: url, url }) },
    ],
    terminal: null,
  });
}

// A monster art descriptor whose portrait is not on disk: the shared
// lifecycle falls through to the committed silhouette alpha mask.
function codexMonsterArt(subject) {
  return artworkDescriptor({
    subject_id: subject,
    generation_subject: subject,
    attempts: [
      {
        type: "image",
        source_id: `${subject}:1`,
        rank: 30,
        resource: artworkResource({ resource_id: `portrait/monster/${subject}.webp`, url: `/art/portraits/${subject}-story-missing.webp` }),
      },
    ],
    terminal: {
      kind: "alpha_mask",
      source_id: "portrait.alpha:monster",
      rank: 100,
      resource: artworkResource({ resource_id: "defaults/monster_anon.webp", url: "/art/defaults/monster_anon.webp" }),
    },
  });
}

const STORY_LOCKED = ["published_description_zh", "published_ecology_zh", "habitat_tags", "variants"];
const storySighted = (key, title) =>
  codexEntry(key, title, {
    stage: "sighted",
    art: codexMonsterArt(key),
    card: [
      { name: "display_name_zh", value: title },
      { name: "published_appearance_zh", value: `${title}在霧中只露出一截輪廓。` },
      { name: "threat_tier", value: "合成階" },
    ],
    locked_fields: STORY_LOCKED,
  });
const storyDefeated = (key, title) =>
  codexEntry(key, title, {
    stage: "defeated",
    art: codexMonsterArt(key),
    card: [
      { name: "display_name_zh", value: title },
      { name: "published_appearance_zh", value: `${title}的骨甲泛著冷白。` },
      { name: "threat_tier", value: "合成階" },
      { name: "published_description_zh", value: `${title}成群出沒的合成記述。` },
      { name: "published_ecology_zh", value: `${title}在渡口一帶覓食的合成生態。` },
      { name: "habitat_tags", value: "河岸・霧林" },
      { name: "variants", value: `${title}・幼體\n${title}・首領` },
    ],
  });
const P = CODEX_PLACEHOLDER;
const one = (key, slots) => [{ key, label: null, slots }];

// The handbook codex tab's story panel: the eight categories in mapping
// order, the monster wall in two tiers with mixed stages, a region with its
// bundled scene art, and art-less entries elsewhere.
export const LORE_CODEX_HANDBOOK_SAMPLE = loreCodex([
  codexCategory("race", "種族", one("race", [codexEntry("s_race_a", "合成種族甲"), P, P])),
  codexCategory("nation", "國家", one("nation", [P, P])),
  codexCategory("region", "地域", one("region", [
    codexEntry("s_region_a", "合成地域甲", {
      art: codexArt("scene:s_region_a", "/art/scenes/city_street.webp"),
      card: [
        { name: "display_name_zh", value: "合成地域甲" },
        { name: "terrain_flavor_zh", value: "石板街道在雨後泛光的合成地貌。" },
      ],
    }),
    P,
  ])),
  codexCategory("monster", "魔物", [
    { key: "story_low", label: "合成低階", slots: [storyDefeated("s_mon_a", "合成骨狼"), storySighted("s_mon_b", "合成霧蛙"), P, P, P] },
    { key: "story_high", label: "合成高階", slots: [P, storySighted("s_mon_c", "合成灰鷲"), P, P, P, P, P] },
  ]),
  codexCategory("element", "元素", one("element", [codexEntry("s_elem_a", "合成元素甲"), P])),
  codexCategory("magic", "魔法", one("magic", [P, P, P])),
  codexCategory("anchor", "地點", one("anchor", [codexEntry("s_anchor_a", "合成地點甲"), P])),
  codexCategory("guild", "公會", one("guild", [P])),
]);

// Every slot of the story panel turned into a placeholder.
export const LORE_CODEX_HANDBOOK_EMPTY_SAMPLE = loreCodex(
  LORE_CODEX_HANDBOOK_SAMPLE.categories.map((category) =>
    codexCategory(
      category.key,
      category.label,
      category.groups.map((group) => ({ ...group, slots: group.slots.map(() => P) })),
    ),
  ),
);
