import { h, reactive, ref } from "vue";
import DreamPanel from "../../components/DreamPanel.vue";

export default { title: "World/DreamPanel", component: DreamPanel };

function fixture(overrides = {}) {
  return {
    session_id: "synthetic-storyboard-dream", revision: 1, completed: 0, remaining: 6,
    can_input: true, can_confirm: true, can_draft: true, can_awaken: true,
    pending: false, open: true, confirmed: false, failure: false,
    opening: "雲海之上矗立著一座純白的王座。王座上的女神面容模糊，卻像一直在等你。積水漫過你的腳踝，湧如泉水的液面映著王座。你可以在這裡商談故事方向，也可以隨時醒來。",
    scene: "", dialogue: "",
    scene_art: "/art/official/0000000000000000000000000000000000000000000000000000000000000000/npc/dream_goddess/dream-throne.webp",
    direction_parts: [], draft_preferences: null,
    thread_choices: [{ id: "synthetic-known-thread", label: "合成故事：碼頭上留下的信" }],
    track: { version: 1, completed: 0, pleasure: 0, ordinal: 0, level: "平靜", climax_phase: "未達", converging: false },
    sleep: { tick_from: 100, tick_to: 100, seconds: 0, requested_seconds: 0, event_kinds: [] },
    ending: "", ending_phase: "", ...overrides,
  };
}

const render = (args) => ({
  setup() {
    const { disconnected, ...overrides } = args;
    const state = reactive(fixture(overrides));
    const intent = ref(null);
    const note = ref("操作只提交意圖。上方按鈕是合成伺服器發布器，不會呼叫模型或推進遊戲時間。");
    const store = {
      view: reactive({ connected: !args.disconnected, motionLevel: "full", textSpeed: "normal", dispatch: { inFlight: null } }),
      dispatchAction(action, payload) {
        intent.value = { action, payload };
        note.value = "已收到操作意圖，請選擇成功或拒絕發布。";
        if (action === "dream.say") {
          state.pending = true;
          state.can_input = false;
          state.revision += 1;
        }
        return "synthetic-storyboard-request";
      },
    };
    function publishSuccess() {
      if (!intent.value) { note.value = "請先提交操作意圖。"; return; }
      const { action, payload } = intent.value;
      if (action === "dream.say") {
        state.completed += 1;
        state.remaining = 6 - state.completed;
        const levels = ["平靜", "微興奮", "中等", "高度", "極限"];
        const ordinal = Math.min(4, Math.round(state.completed * 4 / 6));
        Object.assign(state.track, { completed: state.completed, ordinal, level: levels[ordinal],
          pleasure: Math.min(100, state.completed * 17), converging: state.completed + 1 >= 5 });
        state.scene = "身影微微側過身，替你的念頭留出一小片位置。霧沒有散去，遠處卻像有了可以走近的輪廓。";
        state.dialogue = "「那就先留下這個念頭。你還想替它添上什麼？」";
        state.direction_parts = payload.message_parts;
      } else if (action === "dream.draft" || action === "dream.confirm") {
        if (payload.direction && typeof payload.direction === "object") {
          const { summary, ...preferences } = payload.direction;
          state.direction_parts = [summary];
          state.draft_preferences = preferences;
        }
      }
      if (action === "dream.confirm" || action === "dream.awaken") {
        state.open = false;
        state.confirmed = action === "dream.confirm";
        state.can_confirm = false;
        state.can_draft = false;
        state.ending = "合成結尾：夢境淡去，你醒了。";
      }
      state.pending = false;
      state.failure = false;
      state.can_input = state.open && state.remaining > 0;
      state.revision += 1;
      note.value = "已發布合成成功結果；睡眠結果仍為 100 → 100。";
      intent.value = null;
    }
    function publishFailure() {
      state.pending = false;
      state.failure = true;
      state.can_input = state.open && state.remaining > 0;
      state.revision += 1;
      note.value = "已發布合成拒絕／生成失敗，交流次數不變，仍可儲存草稿或醒來。";
      intent.value = null;
    }
    function publishCap() {
      Object.assign(state, { completed: 6, remaining: 0, can_input: false, pending: false });
      Object.assign(state.track, { completed: 6, pleasure: 100, ordinal: 4, level: "極限", converging: true });
      state.revision += 1;
      intent.value = null;
      note.value = "已發布合成六次上限，自由文字關閉，離開操作仍可使用。";
    }
    function reset() { Object.assign(state, fixture()); intent.value = null; note.value = "已重新發布初始零秒睡眠夢境。"; }
    return () => h("main", { style: "--workspace-bottom: 16px; color: var(--paper-100);" }, [
      h(DreamPanel, { state, store }, { storyTools: () => [
      h("details", { style: "font-family: var(--f-sans); font-size: var(--text-sm); color: var(--paper-500);" }, [
      h("summary", "分鏡測試工具（僅供展示）"),
      h("section", { "aria-label": "夢境分鏡發布器", style: "display: flex; gap: 12px; flex-wrap: wrap;" }, [
        h("button", { class: "ui-btn ui-btn--sm", onClick: publishSuccess }, "發布成功"),
        h("button", { class: "ui-btn ui-btn--sm", onClick: publishFailure }, "發布拒絕／生成失敗"),
        h("button", { class: "ui-btn ui-btn--sm", onClick: publishCap }, "發布第六次上限"),
        h("button", { class: "ui-btn ui-btn--sm", onClick: () => { state.revision += 1; note.value = "合成重新連線：保留睡眠結果與交流次數。"; } }, "重新連線"),
        h("button", { class: "ui-btn ui-btn--sm", onClick: reset }, "重新發布初始夢境"),
      ]),
      h("p", { role: "status" }, note.value),
      h("details", [h("summary", "檢視操作意圖"), h("pre", JSON.stringify(intent.value, null, 2))]),
      ]),
      ] }),
    ]);
  },
});

const thread = { id: "synthetic-known-thread", label: "合成故事：碼頭上留下的信" };
const midTrack = { version: 1, completed: 2, pleasure: 32, ordinal: 1, level: "微興奮", climax_phase: "未達", converging: false };
const said = "我想在北境的雪原上，與那位失散的騎士重逢……";
const conversing = {
  completed: 2, remaining: 4, track: midTrack, direction_parts: [said],
  scene: "水面泛起細細的漣漪，她垂落的髮絲拂過王座扶手，白石被她的體溫映得微微發亮。湧如泉水的液面一圈圈蕩開，漫過你的腳踝。",
  dialogue: "「重逢嗎……那就讓雪替你們記得彼此吧。你還想替這個念頭添上什麼？」",
};

export const Storyboard = { render };
export const Conversing = { render, args: conversing };
export const Converging = { render, args: { ...conversing, completed: 5, remaining: 1,
  track: { version: 1, completed: 5, pleasure: 86, ordinal: 3, level: "高度", climax_phase: "接近", converging: true } } };
export const Pending = { render, args: { ...conversing, pending: true, can_input: false } };
export const Failed = { render, args: { ...conversing, failure: true } };
export const Drafted = { render, args: { ...conversing, direction_parts: ["讓雪原上的重逢，成為我醒來後的第一段故事。"],
  draft_preferences: { kind: "thread_direction", thread_id: thread.id, themes: ["重逢", "信任"], atmosphere: ["靜謐"], exclusions: ["暴力"] } } };
export const AtCap = { render, args: { ...conversing, completed: 6, remaining: 0, can_input: false,
  direction_parts: ["讓雪原上的重逢，成為我醒來後的第一段故事。"],
  dialogue: "「……帶著它醒來吧。」",
  track: { version: 1, completed: 6, pleasure: 100, ordinal: 4, level: "極限", climax_phase: "餘韻", converging: true } } };
export const ManyThreads = { render, args: { ...conversing, thread_choices: Array.from({ length: 32 }, (_, index) => ({
  id: `synthetic-thread-${index}`, label: `合成故事線 ${index + 1}：${"在港灣與雪原之間往返的長篇委託紀錄".repeat(index % 3 + 1)}` })) } };
export const Disconnected = { render, args: { ...conversing, disconnected: true } };
export const NoArt = { render, args: { ...conversing, scene_art: "" } };
