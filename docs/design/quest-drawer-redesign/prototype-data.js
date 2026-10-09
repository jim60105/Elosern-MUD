// Approved visual prototype of the quest drawer redesign
// (docs/superpowers/specs/2026-10-09-quest-drawer-redesign-design.md).
// Reference only: self-contained mock data, not wired to any payload.
// Mock data in the proposed quest_log v2 / board v6 shape: structured
// grade, category, rationale, flavor, reward, 1-based stage.

export const PLAYER_RANK = {
  rank: "E",
  merit: 140,
  next_rank: "D",
  next_threshold: 500,
  merit_qualified: false,
  exam_enabled: true,
};

const flavor = {
  sparrow:
    "收穫已近尾聲，東側田區每天清晨仍有成群穗鳴雀來訪。農戶請公會處理持續侵入的族群，以免今年最後一批穀物留不下來。",
  lynx:
    "高地運輸隊連續在晨霧中失去馱獸，獵人找到的足跡始終沿道路外緣移動。部族請公會處理已開始追逐運輸隊的個體。",
  crab:
    "港外的候船燈附近聚集了一批潮燈蟹，已有夜歸小船認錯泊岸方向。碼頭請公會清理這處聚集地，恢復燈號辨識。",
  hare:
    "平原邊緣的鬆土帶出現新的築埂兔巢，坑洞妨礙農具與牲畜通行。農戶請公會清除這一帶的族群，讓田間作業恢復。",
};

const rationale = {
  sparrow: "低階群居鳥類，較強個體會自不同方向干擾驅趕者；個體不難應付，但數量分散，取巧不易。",
  lynx: "中階獵食者會反覆試探隊伍邊緣，避開完整隊列；高地森林的晨霧讓接近方向難以判斷，落單的人風險明顯上升。",
  crab: "低階甲殼類，但守礁型占據狹窄洞口，防禦遠高於同階個體；礁隙與潮池讓隊伍無法展開，只能逐處清理。",
  hare: "平原鬆土讓牠們容易鑽回洞道，護巢型又會加固入口；個體不強，逐一找出田埂間的巢口才是難處。",
};

const GUILD = { kind: "guild", label: "埃洛西恩冒險者公會 阿爾托利亞分會" };

export const BOOK = [
  {
    id: "q1", state: "in_progress", name: "驅除東部平原穗鳴雀", category: "討伐", grade: "F",
    objective: "在東部大平原討伐 2 隻穗鳴雀", variants: "計數變體：領群型、啄穗型",
    progress: 1, target: 2, stage: 1, stages: 1, deadline: null, tracked: true,
    issuer: GUILD, settlement: "counter",
    reward: { copper: 40, merit: 20, items: [] },
    rationale: rationale.sparrow, flavor: flavor.sparrow,
    abandon: true,
  },
  {
    id: "q2", state: "in_progress", name: "討伐西北高地森林霧鬃山貓", category: "討伐", grade: "D",
    objective: "在西北高地森林討伐 1 隻霧鬃山貓", variants: "計數變體：林間潛行型、追跡型",
    progress: 0, target: 1, stage: 1, stages: 1, deadline: "剩餘 2 日 3 時", tracked: false,
    issuer: GUILD, settlement: "counter",
    reward: { copper: 320, merit: 90, items: [{ name: "治療藥水", qty: 3 }] },
    rationale: rationale.lynx, flavor: flavor.lynx,
    abandon: true,
  },
  {
    id: "q3", state: "in_progress", name: "磨坊糧運", category: "護衛", grade: "F",
    objective: "將糧食袋交付給磨坊的老周", variants: null,
    progress: 3, target: 10, stage: 2, stages: 3, deadline: "天亮前", tracked: false,
    issuer: { kind: "npc", label: "農夫 老周" }, settlement: "auto",
    reward: { copper: 220, merit: 0, items: [] },
    rationale: null, flavor: "老周把三袋糧食交給你，要求天亮前送到磨坊。",
    abandon: false,
  },
  {
    id: "q4", state: "completed", name: "討伐低階魔物", category: "討伐", grade: "F",
    objective: "討伐 1 隻低階魔物", variants: null,
    progress: 1, target: 1, stage: 1, stages: 1, deadline: null, tracked: false,
    issuer: GUILD, settlement: "counter",
    reward: { copper: 50, merit: 25, items: [{ name: "治療藥水", qty: 2 }] },
    rationale: null, flavor: null, turnin: true, claimed: false,
  },
  {
    id: "q5", state: "completed", name: "清理西南海岸潮燈蟹", category: "討伐", grade: "E",
    objective: "在西南海岸討伐 1 隻潮燈蟹", variants: "計數變體：岸行型、守礁型",
    progress: 1, target: 1, stage: 1, stages: 1, deadline: null, tracked: false,
    issuer: GUILD, settlement: "counter",
    reward: { copper: 120, merit: 45, items: [] },
    rationale: rationale.crab, flavor: flavor.crab, turnin: false, claimed: true,
  },
  {
    id: "q6", state: "failed", name: "驅除東部平原築埂兔", category: "討伐", grade: "F",
    objective: "在東部大平原討伐 2 隻築埂兔", variants: "計數變體：築巢型、護巢型",
    progress: 0, target: 2, stage: 1, stages: 1, deadline: "期限已過", tracked: false,
    issuer: GUILD, settlement: "counter",
    reward: { copper: 40, merit: 20, items: [] },
    rationale: rationale.hare, flavor: flavor.hare,
  },
];

export const BOARD = [
  {
    id: "b1", name: "驅除東部平原築埂兔", category: "討伐", grade: "F",
    objective: "在東部大平原討伐 2 隻築埂兔", variants: "計數變體：築巢型、護巢型",
    target: 2, deadline: null, issuer: GUILD, settlement: "counter",
    reward: { copper: 40, merit: 20, items: [] },
    rationale: rationale.hare, flavor: flavor.hare, accept: { enabled: true },
  },
  {
    id: "b2", name: "討伐低階魔物", category: "討伐", grade: "F",
    objective: "討伐 1 隻低階魔物", variants: null,
    target: 1, deadline: null, issuer: GUILD, settlement: "counter",
    reward: { copper: 50, merit: 25, items: [{ name: "治療藥水", qty: 2 }] },
    rationale: null, flavor: null, accept: { enabled: true },
  },
  {
    id: "b3", name: "清理西南海岸潮燈蟹", category: "討伐", grade: "E",
    objective: "在西南海岸討伐 1 隻潮燈蟹", variants: "計數變體：岸行型、守礁型",
    target: 1, deadline: null, issuer: GUILD, settlement: "counter",
    reward: { copper: 120, merit: 45, items: [] },
    rationale: rationale.crab, flavor: flavor.crab, accept: { enabled: true },
  },
  {
    id: "b4", name: "清理西部丘陵築埂兔", category: "討伐", grade: "E",
    objective: "在西部丘陵討伐 3 隻築埂兔", variants: "計數變體：築巢型、護巢型",
    target: 3, deadline: "接取後 3 日", issuer: GUILD, settlement: "counter",
    reward: { copper: 150, merit: 50, items: [{ name: "解毒草", qty: 2 }] },
    rationale: rationale.hare, flavor: flavor.hare,
    accept: { enabled: false, reason: "你已接下同一份委託" },
  },
];

export const GRADES = ["F", "E", "D", "C", "B", "A", "S"];
