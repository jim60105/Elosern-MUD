// Story fixture slices: see stories/fixtures.js (facade) for the public surface.

// The committed `dialogue` panel (v2) while a conversation is open: the
// host, the bond stage name, the session line, and four keyword choices.
// Stories derive their view model through `dialogueViewModel`, exactly as
// AppClient does (the showcase derived-shape rule).
export const DIALOGUE_PANEL_SAMPLE = {
  schema_version: 2,
  available: true,
  kind: "dialogue",
  host: { identity: 41, display_name: "灰婆婆", portrait_ref: null },
  bond_stage: "親睦",
  line: "「渡河要五枚銅板，多一子我也不走。」她瞥了你一眼，「倒是你，身上聞起來有點……不對味。」",
  choices: [
    { keyword_id: "fare", label: "「就五枚，走嗎？」" },
    { keyword_id: "smell", label: "含糊帶過氣味" },
    { keyword_id: "chest", label: "直接問箱櫃下落" },
    { keyword_id: "silence", label: "保持沉默，觀察她下一步" },
  ],
};
