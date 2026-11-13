// World/DreamPanel: the dream collaboration as co-editing a wish, played as the
// staged server (design: stage 8 of
// docs/superpowers/specs/2026-11-13-dream-proposal-coediting-design.md). The
// fixture applies the design's scripted edit commands and publishes a schema-4
// panel state. Reference only: synthetic fixtures, no model call, no game time.
//
// Try it: pick the story the wish belongs to, speak (an empty Enter does
// nothing), read her answer, 1 opens the whole wish, 2 stops speaking and hands
// the form over, then 許下這個願望 or 醒來 closes the dream.
import { h, nextTick, onMounted, reactive, ref } from "vue";
import DreamPanel from "../../components/DreamPanel.vue";
import {
  dreamBundledDescriptor,
  dreamDescriptor,
  dreamExhaustedDescriptor,
  dreamRefusedDescriptor,
} from "../fixtures.js";
import { OPENING, SCRIPT, THREADS } from "../fixtures/dream_wish.js";

export default { title: "World/DreamPanel", component: DreamPanel };

const SESSION_ID = "synthetic-dream-wish";
const EXCHANGES = 6;
const LIST_FIELDS = ["themes", "atmosphere", "participants", "emphasis", "exclusions"];
const LEVELS = ["平靜", "微興奮", "中等", "高度", "極限"];
const emptyProposal = () => ({ summary: "", themes: [], atmosphere: [], participants: [], emphasis: [], exclusions: [], requirements: [] });
const clone = (value) => JSON.parse(JSON.stringify(value));

// ---- the edit contract (design: "Edit Contract") ----
// Each field is a small text file: one item per line, a requirement row as
// `kind: text`. All edits apply to a copy or none do.
function fieldText(proposal, path) {
  if (path === "summary") return proposal.summary;
  if (path === "requirements") return proposal.requirements.map((row) => `${row.kind}: ${row.text}`).join("\n");
  return proposal[path].join("\n");
}
function storeField(proposal, path, text) {
  if (path === "summary") { proposal.summary = text; return; }
  const lines = [...new Set(text.split("\n").map((line) => line.trim()).filter(Boolean))];
  if (path !== "requirements") { proposal[path] = lines; return; }
  proposal.requirements = lines.map((line) => {
    const at = line.indexOf(": ");
    if (at < 1) throw new Error(`malformed requirement line: ${line}`);
    return { kind: line.slice(0, at), text: line.slice(at + 2) };
  });
}
function applyEdits(proposal, edits) {
  const next = clone(proposal);
  for (const edit of edits) {
    let text = fieldText(next, edit.path);
    if (edit.command === "create") text = edit.file_text;
    else if (edit.command === "str_replace") {
      const matches = text.split(edit.old_str).length - 1;
      if (matches !== 1) throw new Error(`old_str matched ${matches} times in ${edit.path}`);
      text = text.replace(edit.old_str, edit.new_str);
    } else if (edit.command === "insert") {
      const lines = text ? text.split("\n") : [];
      lines.splice(edit.insert_line, 0, edit.insert_text);
      text = lines.join("\n");
    } else throw new Error(`unknown command: ${edit.command}`);
    storeField(next, edit.path, text);
  }
  return next;
}
// What changed: added and removed items by name, and whether the summary first
// took shape or changed. The wire publishes null for an unchanged summary, so an
// empty edit set is an all-empty report rather than a false.
function diffProposal(before, after) {
  const lists = {};
  for (const key of LIST_FIELDS) {
    lists[key] = { added: after[key].filter((item) => !before[key].includes(item)), removed: before[key].filter((item) => !after[key].includes(item)) };
  }
  const same = (a, b) => a.kind === b.kind && a.text === b.text;
  return {
    summary: before.summary === after.summary ? null : before.summary ? "changed" : "formed",
    lists,
    requirements: {
      added: after.requirements.filter((row) => !before.requirements.some((old) => same(old, row))),
      removed: before.requirements.filter((row) => !after.requirements.some((now) => same(now, row))),
    },
  };
}

function track(completed) {
  const ordinal = Math.min(4, Math.round(completed * 4 / EXCHANGES));
  return { version: 1, completed, pleasure: Math.min(100, completed * 17), ordinal, level: LEVELS[ordinal],
    climax_phase: completed >= EXCHANGES ? "餘韻" : completed >= 5 ? "接近" : "未達",
    converging: completed + 1 >= 5 && completed < EXCHANGES };
}

// The state after `turns` scripted exchanges: exactly the schema-4 shape the
// server publishes, including the four schema-3 keys a client may still read.
function fixture({ turns = 0, threads = THREADS, threadId = null, stage = null, drafted = false,
  pending = false, failure = false, requirementVersion = null, ...overrides } = {}) {
  let proposal = emptyProposal();
  let changes = null;
  for (const turn of SCRIPT.slice(0, turns)) {
    const next = applyEdits(proposal, turn.edits);
    changes = diffProposal(proposal, next);
    proposal = next;
  }
  const last = turns ? SCRIPT[turns - 1] : null;
  const resolved = stage || (turns >= EXCHANGES ? "finalized" : "conversing");
  const conversing = resolved === "conversing";
  const remaining = EXCHANGES - turns;
  return {
    session_id: SESSION_ID, revision: 1, completed: turns, remaining,
    can_input: conversing && remaining > 0 && !pending,
    can_confirm: resolved === "finalized",
    can_finalize: conversing && !pending,
    can_choose_thread: conversing && turns === 0 && !pending,
    can_edit: resolved === "finalized",
    can_draft: true, can_awaken: true,
    pending, open: true, confirmed: false, failure, drafted,
    opening: OPENING, scene: last?.scene || "", dialogue: last?.dialogue || "",
    // The shared canonical scene descriptor of the dream's own source chain.
    scene_art: dreamDescriptor(),
    direction_parts: proposal.summary ? [proposal.summary] : [],
    thread_choices: threads, draft_preferences: null,
    requirements: clone(proposal.requirements), requirement_version: requirementVersion,
    stage: resolved, proposal, changes, thread_id: threadId,
    track: track(turns), sleep: { tick_from: 100, tick_to: 100, requested_seconds: 0, seconds: 0, event_kinds: [] },
    ending: "", ending_phase: "",
    ...overrides,
  };
}

const render = (args) => ({
  setup() {
    const { disconnected, open: openLayer, ...options } = args;
    const state = reactive(fixture(options));
    const root = ref(null);
    const epoch = ref(0);
    const auto = ref(true);
    const intent = ref(null);
    const note = ref("合成伺服器：勾選自動發布時，操作意圖會在短暫延遲後套用；取消勾選可手動發布成功或失敗。");
    const store = {
      view: reactive({ connected: !disconnected, motionLevel: "full", textSpeed: "normal", dispatch: { inFlight: null } }),
      dispatchAction(action, payload) {
        intent.value = { action, payload };
        if (action === "dream.say") {
          Object.assign(state, { pending: true, failure: false });
          state.revision += 1;
          syncStageFlags();
        }
        if (auto.value) setTimeout(publishSuccess, action === "dream.say" ? 1100 : 240);
        return "synthetic-request";
      },
    };
    // Every fabricated frame stays a legal schema-4 payload: the stage decides
    // which flags a surface may offer, so each synthetic transition re-derives
    // the set instead of leaving a stale one behind.
    function syncStageFlags() {
      const conversing = state.stage === "conversing";
      state.can_input = state.open && conversing && state.remaining > 0 && !state.pending;
      state.can_finalize = state.open && conversing && !state.pending;
      state.can_choose_thread = state.open && conversing && state.completed === 0 && !state.pending;
      state.can_edit = state.open && state.stage === "finalized";
      state.can_confirm = state.open && state.stage === "finalized";
      state.can_draft = state.open;
      // The server publishes no offered thread once the dream is closed.
      if (!state.open) state.thread_choices = [];
    }
    // The schema-3 keys mirror what the server derives from the working wish.
    function syncPublished() {
      state.direction_parts = state.proposal.summary ? [state.proposal.summary] : [];
      state.requirements = clone(state.proposal.requirements);
    }
    function publishSuccess() {
      if (!intent.value) { note.value = "請先提交操作意圖。"; return; }
      const { action, payload } = intent.value;
      intent.value = null;
      if (action === "dream.say") {
        const turn = SCRIPT[state.completed];
        if (turn) {
          const next = applyEdits(state.proposal, turn.edits);
          state.changes = diffProposal(state.proposal, next);
          state.proposal = next;
          syncPublished();
          state.scene = turn.scene;
          state.dialogue = turn.dialogue;
          state.completed += 1;
          state.remaining = EXCHANGES - state.completed;
          state.track = track(state.completed);
          // The sixth settled exchange finalizes in the same save.
          if (state.completed >= EXCHANGES) state.stage = "finalized";
        }
      } else if (action === "dream.choose_thread") {
        state.thread_id = payload.thread_id;
      } else if (action === "dream.finalize") {
        state.stage = "finalized";
        state.drafted = true;
      } else if (action === "dream.draft" || action === "dream.confirm") {
        if (payload?.direction) {
          const { summary, requirements, kind, thread_id: threadId, ...lists } = payload.direction;
          state.proposal = { ...emptyProposal(), ...lists, summary, requirements: requirements || [] };
          state.thread_id = threadId;
          syncPublished();
        }
        state.drafted = true;
        if (action === "dream.confirm") Object.assign(state, { open: false, confirmed: true });
      } else if (action === "dream.awaken") {
        state.open = false;
      }
      state.pending = false;
      state.failure = false;
      state.revision += 1;
      syncStageFlags();
      note.value = "已發布合成成功結果；睡眠結果仍為 100 → 100。";
    }
    function publishFailure() {
      if (intent.value?.action !== "dream.say") { note.value = "生成失敗只套用於訴說。"; return; }
      intent.value = null;
      Object.assign(state, { pending: false, failure: true });
      state.revision += 1;
      syncStageFlags();
      note.value = "已發布生成失敗：這次不算數，願望維持原狀。";
    }
    function reset() {
      Object.assign(state, fixture(options));
      intent.value = null;
      epoch.value += 1;
      note.value = "已重新發布初始夢境。";
    }
    // A story that must land on an open layer activates the row itself, exactly
    // as a player would: the component gains no presentation-only prop. The
    // query stays inside this story's own root, so a second mounted story can
    // never receive the click.
    const rowFor = { view: "main", sheet: "main", take: "take" };
    onMounted(async () => {
      const row = rowFor[openLayer];
      if (!row) return;
      await nextTick();
      root.value?.querySelector(`[data-row='${row}']`)?.click();
    });
    const tools = () => h("details", { style: "font-family: var(--f-sans); font-size: var(--text-sm); color: var(--paper-500);" }, [
      h("summary", "夢境分鏡工具（僅供展示）"),
      h("section", { "aria-label": "合成伺服器", style: "display: flex; gap: 12px; flex-wrap: wrap; align-items: center;" }, [
        h("label", [h("input", { type: "checkbox", checked: auto.value, onChange: (event) => { auto.value = event.target.checked; } }), " 自動發布成功"]),
        h("button", { class: "ui-btn ui-btn--sm", onClick: publishSuccess }, "發布成功"),
        h("button", { class: "ui-btn ui-btn--sm", onClick: publishFailure }, "發布生成失敗"),
        h("button", { class: "ui-btn ui-btn--sm", onClick: reset }, "重新開始"),
      ]),
      h("p", { role: "status" }, note.value),
      h("details", [h("summary", "檢視操作意圖"), h("pre", JSON.stringify(intent.value, null, 2))]),
    ]);
    return () => h("main", { ref: root, style: "color: var(--paper-100);" }, [
      h(DreamPanel, { key: epoch.value, state, store }, { storyTools: tools }),
    ]);
  },
});

// The panel's first frame: the opening narration and the story choice.
export const Storyboard = { render };
export const Arrival = { render, args: { turns: 0 } };
// No thread to continue: the choice is not shown at all.
export const ArrivalNoThreads = { render, args: { turns: 0, threads: [] } };
// After the first exchange: she wrote the wish, the thread is fixed.
export const FirstWish = { render, args: { turns: 1 } };
export const Conversing = { render, args: { turns: 2 } };
// The fifth exchange settled: the dream is about to end.
export const Converging = { render, args: { turns: 5 } };
export const Pending = { render, args: { turns: 2, pending: true } };
export const Failed = { render, args: { turns: 2, failure: true } };
export const Drafted = { render, args: { turns: 2, drafted: true } };
// The wish's requirement rows as she wrote them, with no saved version yet.
export const RequirementsProposed = { render, args: { turns: 1 } };
// The same rows frozen into the saved draft that confirmation compares.
export const RequirementsShown = { render, args: { turns: 1, stage: "finalized", drafted: true,
  requirementVersion: "synthetic-dream-wish:v1" } };
// Six exchanges spent: the form is the player's without a warning.
export const AtCap = { render, args: { turns: 6 } };
export const ManyThreads = { render, args: { turns: 0, threads: Array.from({ length: 32 }, (_, index) => ({
  id: `synthetic-thread-${index}`, label: `合成故事線 ${index + 1}：${"在港灣與雪原之間往返的長篇委託紀錄".repeat(index % 3 + 1)}` })) } };
export const Disconnected = { render, args: { turns: 2, disconnected: true } };
// The operator root holds no preferred image: absence is normal, so the required
// bundled dream illustration carries the stage with no error styling.
export const BundledDream = { render, args: { turns: 2, scene_art: dreamBundledDescriptor() } };
// The preferred image was refused at admission: its reached failure stays stated
// while the bundled dream it precedes stands in for it.
export const PreferredRefused = { render, args: { turns: 2, scene_art: dreamRefusedDescriptor() } };
// Every position is unavailable: nothing is presented and the stage states the
// reached fact instead of a broken image.
export const MissingArt = { render, args: { turns: 2, scene_art: dreamExhaustedDescriptor() } };
// The whole wish, read-only, while she still holds the pen.
export const WholeWish = { render, args: { turns: 3, open: "view" } };
// The one irreversible step: what is given up, focus on staying.
export const StopSpeaking = { render, args: { turns: 3, open: "take" } };
// The player holds the form: every field edits, the thread stays fixed.
export const OwnHand = { render, args: { turns: 3, stage: "finalized", drafted: true, open: "sheet" } };
