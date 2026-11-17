// Story-only preset cards for the creation card wall (creation-preset-card-
// wall). Synthetic: the names, prose and keys are invented for the showcase,
// and every figure is one of the committed built-in 9:16 defaults under
// web/static/art/defaults/, presented as the card's image attempt (the offline
// static server serves no official-art route). One card's image is missing on
// purpose, so the wall shows the shared loader's alpha-terminal fallback. The
// terminal is the committed `man` mask, so no image attempt reuses its URL.
import { artworkDescriptor, artworkResource, artworkTerminal } from "./art_panels.js";
import { CREATION_PANEL_SAMPLE } from "./creation_panels.js";

const FIGURES = [
  ["woman", { x: 0.36, y: 0.03, w: 0.28, h: 0.16 }],
  ["boy", { x: 0.36, y: 0.04, w: 0.28, h: 0.15 }],
  ["girl", { x: 0.37, y: 0.04, w: 0.27, h: 0.15 }],
  ["elder", { x: 0.35, y: 0.03, w: 0.29, h: 0.16 }],
];

const CARDS = [
  ["story_wall_drifter", "霧原遊俠", "beastfolk", "獸民：堅韌、忠實，長於戰技。", "重擊與近戰優先的前衛配點", "沿著霧原的商道替人護送貨車，刀鞘上刻著每一趟走過的里程。"],
  ["story_wall_archivist", "塔頂抄錄員", "elf", "精靈：長壽、敏銳，長於學藝。", "魔力與研究優先的術師配點", "在高塔頂層抄錄星圖的學徒，為了一頁缺漏的註解第一次下山。"],
  ["story_wall_ferryhand", "渡口船工", "human", "人族：均衡、勤奮，長於商貿。", "體力與搬運優先的均衡配點", "在渡口撐船長大，認得河上每一處暗流，也記得每位船長欠的酒錢。"],
  ["story_wall_herbalist", "林緣採藥人", "human", "人族：均衡、勤奮，長於商貿。", "療癒與採集優先的支援配點", "跟著祖母辨認林緣的藥草，這是她第一次獨自走出村子。"],
  ["story_wall_warden", "退役哨長", "human", "人族：均衡、勤奮，長於商貿。", "防禦與經驗優先的守備配點", "守了三十年的北哨，卸下職務那天，才發現自己從沒看過南方的海。"],
  ["story_wall_singer", "旅路歌者", "elf", "精靈：長壽、敏銳，長於學藝。", "敏捷與交涉優先的遊走配點", "唱著別人的故事走過許多城鎮，想找到一首屬於自己的歌。"],
  ["story_wall_smith", "灰爐鐵匠", "beastfolk", "獸民：堅韌、忠實，長於戰技。", "攻擊與耐力優先的重裝配點", "爐火熄滅的那一夜，帶著最後一把未完成的劍離開了工坊。"],
  ["story_wall_scout", "沼澤斥候", "human", "人族：均衡、勤奮，長於商貿。", "先攻與偵察優先的輕裝配點", "在沼澤邊境替商隊探路，擅長在泥地裡不留下腳印。"],
];

function cardArtwork(key, index) {
  const [figure, faceRect] = FIGURES[index % FIGURES.length];
  // The sixth card's image is absent, so its loader reaches the terminal.
  const url = index === 5 ? `/art/defaults/missing-${key}.webp` : `/art/defaults/${figure}.webp`;
  return artworkDescriptor({
    subject_id: `creation:preset:${key}`,
    generation_subject: null,
    generation_state: null,
    attempts: [
      {
        type: "image",
        source_id: `portrait.official:${key}`,
        rank: 10,
        resource: artworkResource({
          resource_id: `preset/${key}.webp`,
          url,
          origin: "official",
          geometry: { image_size: null, face_rect: faceRect, stage: null, aspect_ratio: "9:16" },
        }),
      },
    ],
    terminal: artworkTerminal(),
  });
}

export const CREATION_WALL_PRESETS = CARDS.map(([key, name, race, raceDescription, emphasis, background], index) => ({
  key,
  display_name: name,
  race,
  race_description: raceDescription,
  subrace: null,
  emphasis,
  background,
  artwork: cardArtwork(key, index),
}));

export const CREATION_PANEL_WALL_SAMPLE = {
  ...CREATION_PANEL_SAMPLE,
  presets: CREATION_WALL_PRESETS,
};

export const CREATION_PANEL_WALL_DRAFT_SAMPLE = {
  ...CREATION_PANEL_WALL_SAMPLE,
  draft: { mode: "preset", stage: "preset_selected", preset_key: CREATION_WALL_PRESETS[2].key },
};
