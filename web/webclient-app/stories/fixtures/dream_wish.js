// Synthetic fixtures for the staged dream panel. Nothing here is game data: the
// wording only has to exercise every edit command and every kind of change the
// surface must show. Later stages extend this file.
//
// Copied from docs/design/dream-proposal-coediting/prototype-data.js without the
// per-turn `sample` instructions and without the farewell lines: the shipped
// panel has no suggestion field and the farewell arrives with its own stage.

export const THREADS = [
  { id: "thread-letter", label: "碼頭上留下的那封信，收信人至今沒有出現。" },
  { id: "thread-bell", label: "舊鐘樓每到午夜便自己響起，鎮上無人願意上去查看。" },
];

export const OPENING =
  "雲海之上矗立著一座純白的王座。王座上的身影面容模糊，卻像一直在等你。"
  + "你可以在這裡說出願望，她會替你把願望理清，也可以隨時醒來。";

// One scripted exchange per turn: her answer and the edit commands of the
// design's edit contract.
export const SCRIPT = [
  {
    scene: "身影微微傾身，雲面隨著你的話亮起一行淡金色的光。",
    dialogue: "「南門、走失的母親。我聽見了。接下來，你想讓它往哪裡走？」",
    edits: [
      { command: "create", path: "summary", file_text: "在南門遇見一位尋找母親的少女，陪她一起找人。" },
      { command: "create", path: "themes", file_text: "尋親\n護送" },
      { command: "create", path: "requirements", file_text: "place: 南門\nnew_character: 尋找母親的少女" },
    ],
  },
  {
    scene: "雲海的風緩了下來，那行光的邊緣變得柔和。",
    dialogue: "「溫柔的、不見刀光的故事。我明白了。」",
    edits: [
      { command: "create", path: "atmosphere", file_text: "溫柔" },
      { command: "create", path: "exclusions", file_text: "戰鬥" },
    ],
  },
  {
    scene: "她輕輕抬手，其中一點光暗了下去，雲面泛起漣漪，另一點光隨即亮起。",
    dialogue: "「不是一路相送，而是替她四處探問。這樣的託付，確實更像悄悄話。」",
    edits: [
      { command: "str_replace", path: "themes", old_str: "護送", new_str: "打聽消息" },
      { command: "str_replace", path: "summary", old_str: "陪她一起找人。", new_str: "受她私下委託，在城裡四處打聽消息。" },
      { command: "insert", path: "requirements", insert_line: 2, insert_text: "private_commission: 少女私下委託尋人" },
    ],
  },
  {
    scene: "雲面沒有變化，身影只是靜靜看著你。",
    dialogue: "「可以。只是我想先問：你希望最後找得到她的母親嗎？還是留給醒來後的路去回答？」",
    edits: [],
  },
  {
    scene: "雲面的光收攏在一起，像一盞即將放飛的燈。",
    dialogue: "「那就讓巷弄裡的炊煙與閒談陪著你們。夢快到盡頭了。」",
    edits: [{ command: "insert", path: "emphasis", insert_line: 0, insert_text: "街坊的日常" }],
  },
  {
    scene: "所有的光在雲面上安靜地亮了一瞬。",
    dialogue: "「南門、溫柔的探問、巷弄裡的日常。這就是你此刻的願望了。」",
    edits: [],
  },
];
