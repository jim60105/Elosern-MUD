// Synthetic data for the approved creation layout. Reference only: the
// names, races and prose are invented for the prototype, and every figure is
// one of the committed built-in defaults under web/static/art/defaults/.
const art = (key) => `/art/defaults/${key}.webp`;

export const PRESETS = [
  { key: "wandering_blade", name: "流浪劍客", race: "獸人", subrace: "狼族", art: art("woman"),
    emphasis: "重擊與近戰優先的前衛配點",
    background: "一位尋找冒險者公會試煉的流浪劍客，行囊裡只有一把磨舊的長劍。" },
  { key: "lantern_scholar", name: "燈下學士", race: "精靈", subrace: "林地族", art: art("man"),
    emphasis: "魔力與研究優先的術師配點",
    background: "在燈下研讀古籍的學士，為了一頁失落的註解離開了書庫。" },
  { key: "harbor_hauler", name: "碼頭腳夫", race: "人類", subrace: "平原人", art: art("boy"),
    emphasis: "體力與搬運優先的均衡配點",
    background: "在霧骨渡口搬運貨物的腳夫，認得每一艘船的船長。" },
  { key: "hedge_healer", name: "籬邊藥師", race: "人類", subrace: "山地人", art: art("girl"),
    emphasis: "療癒與採集優先的支援配點",
    background: "跟著祖母學會辨認藥草的年輕藥師，第一次獨自出遠門。" },
  { key: "old_warden", name: "退役守望", race: "人類", subrace: "平原人", art: art("elder"),
    emphasis: "防禦與經驗優先的守備配點",
    background: "守了三十年城門的老兵，退役後仍習慣在黎明前醒來。" },
  { key: "road_singer", name: "行路歌手", race: "精靈", subrace: "河谷族", art: art("woman"),
    emphasis: "敏捷與交涉優先的遊歷配點",
    background: "以歌換宿的旅人，記得沿途每一座村莊的搖籃曲。" },
  { key: "ash_smith", name: "灰爐鐵匠", race: "獸人", subrace: "熊族", art: art("man"),
    emphasis: "力量與鍛造優先的工匠配點",
    background: "爐火熄滅的鐵匠鋪最後一位學徒，帶著師傅的鐵鎚上路。" },
  { key: "marsh_scout", name: "沼澤斥候", race: "獸人", subrace: "狐族", art: art("girl"),
    emphasis: "偵查與遠程優先的斥候配點",
    background: "在沼地長大的斥候，能從水面的波紋讀出來者的腳步。" },
];

export const SILHOUETTES = { female: art("woman"), male: art("man") };

export const AXES = [
  { key: "hp", label: "生命", help: "承傷能力", min: 0, max: 50, value: 30 },
  { key: "mp", label: "魔力", help: "法術資源", min: 0, max: 50, value: 20 },
  { key: "sp", label: "精神", help: "精神資源", min: 0, max: 50, value: 24 },
  { key: "atk", label: "攻擊", help: "近戰傷害", min: 0, max: 20, value: 12 },
  { key: "agi", label: "敏捷", help: "先攻與迴避", min: 0, max: 20, value: 10 },
  { key: "def", label: "防禦", help: "減傷能力", min: 0, max: 20, value: 8 },
  { key: "mag", label: "魔法攻擊", help: "法術威力", min: 0, max: 240, value: 120 },
];

export const ELEMENTS = ["火", "水", "風", "土", "雷", "冰", "光", "暗"];

// The generate drawer's shape for a not-yet-activated draft: no equipment
// and no appearance field exist yet, so only free text is offered.
export const DRAFT_GALLERY_MODEL = {
  groups: [],
  selected: null,
  capabilities: { supports_field_selection: false, supports_free_text: true, max_cards: 1 },
};
