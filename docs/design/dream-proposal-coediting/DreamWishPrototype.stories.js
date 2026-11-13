// Design/DreamWish: the dream collaboration reworked as co-editing a wish
// (docs/superpowers/specs/2026-11-13-dream-proposal-coediting-design.md).
// The prototype component is a modified copy of components/DreamPanel.vue;
// this file plays the server: it applies the scripted edit commands of the
// design's edit contract and publishes the proposed panel state. Reference
// only, synthetic fixtures, no model call and no game time.
//
// Try it: pick the story the wish belongs to, speak (the placeholder suggests
// a line; an empty Enter does nothing), read her answer and watch the card's
// change line, 1 opens the whole wish, 2 stops speaking and hands the form
// over, then 許下這個願望 or 醒來 plays the farewell.
import { h, reactive, ref } from "vue";
import DreamWishPrototype from "./DreamWishPrototype.vue";
import { FAREWELLS, OPENING, SCRIPT, THREADS } from "./prototype-data.js";
import { dreamBundledDescriptor, sceneBundledResource } from "../../../web/webclient-app/stories/fixtures/art_panels.js";
import { atFullHd, atReference, windowViewportParameters } from "../../../web/webclient-app/stories/window-viewports.js";

export default {
  title: "Design/DreamWish",
  component: DreamWishPrototype,
  parameters: { layout: "fullscreen", ...windowViewportParameters },
};

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
// What changed: added and removed items by name, a state for the summary.
function diffProposal(before, after) {
  const lists = {};
  for (const key of LIST_FIELDS) {
    lists[key] = { added: after[key].filter((item) => !before[key].includes(item)), removed: before[key].filter((item) => !after[key].includes(item)) };
  }
  const same = (a, b) => a.kind === b.kind && a.text === b.text;
  return {
    // "formed" when the wish had no words before, "changed" afterwards.
    summary: before.summary === after.summary ? false : before.summary ? "changed" : "formed",
    lists,
    requirements: {
      added: after.requirements.filter((row) => !before.requirements.some((old) => same(old, row))),
      removed: before.requirements.filter((row) => !after.requirements.some((now) => same(now, row))),
    },
  };
}

function track(completed) {
  const ordinal = Math.min(4, Math.round(completed * 4 / 6));
  return { version: 1, completed, pleasure: Math.min(100, completed * 17), ordinal, level: LEVELS[ordinal],
    climax_phase: completed >= 6 ? "餘韻" : completed >= 5 ? "接近" : "未達", converging: completed + 1 >= 5 && completed < 6 };
}

// The state after `turns` scripted exchanges.
function fixture({ turns = 0, threads = THREADS, threadId = null, stage = null, drafted = false, ...overrides } = {}) {
  let proposal = emptyProposal();
  let changes = null;
  for (const turn of SCRIPT.slice(0, turns)) {
    const next = applyEdits(proposal, turn.edits);
    changes = diffProposal(proposal, next);
    proposal = next;
  }
  const last = turns ? SCRIPT[turns - 1] : null;
  const resolved = stage || (turns >= 6 ? "penned" : "wishing");
  return {
    session_id: "synthetic-dream-wish", revision: 1, completed: turns, remaining: 6 - turns,
    stage: resolved, proposal, changes: resolved === "penned" && turns < 6 ? null : changes,
    thread_id: threadId, thread_choices: threads, can_choose_thread: turns === 0 && resolved === "wishing",
    can_input: resolved === "wishing" && turns < 6, can_finalize: resolved === "wishing", can_edit: resolved === "penned",
    can_confirm: resolved === "penned", can_draft: true, can_awaken: true,
    pending: false, open: true, confirmed: false, failure: false, drafted,
    opening: OPENING, scene: last?.scene || "", dialogue: last?.dialogue || "",
    sample: SCRIPT[turns]?.sample || "",
    // Storybook serves the committed illustration at its static path, so the
    // prototype is reviewed over the real painting.
    scene_art: dreamBundledDescriptor({ attempts: [{ type: "image", source_id: "scene.bundled:dream_throne", rank: 40,
      resource: sceneBundledResource("dream_throne", { url: "/art/scenes/dream_throne.webp" }) }] }),
    track: track(turns), sleep: { tick_from: 100, tick_to: 100, seconds: 0, requested_seconds: 0, event_kinds: [] },
    farewell: "", outcome: "", ending: "", ending_phase: "", ...overrides,
  };
}

const render = (args) => ({
  setup() {
    const { disconnected, open: openLayer, leave, ...options } = args;
    const state = reactive(fixture(options));
    const epoch = ref(0);
    const auto = ref(true);
    const intent = ref(null);
    const note = ref("合成伺服器：自動發布成功結果。取消勾選即可手動發布成功或失敗。");
    const store = {
      view: reactive({ connected: !disconnected, motionLevel: "full", textSpeed: "normal", dispatch: { inFlight: null } }),
      dispatchAction(action, payload) {
        intent.value = { action, payload };
        if (action === "dream.say") {
          Object.assign(state, { pending: true, can_input: false, failure: false, can_choose_thread: false });
          state.revision += 1;
        }
        if (auto.value) setTimeout(publishSuccess, action === "dream.say" ? 1100 : 240);
        return "synthetic-request";
      },
    };
    function leaveWith(outcome) {
      const kept = state.proposal.summary.trim();
      const resolved = outcome === "confirmed" ? "confirmed" : kept ? "draft" : "empty";
      Object.assign(state, { open: false, confirmed: resolved === "confirmed", can_input: false, can_confirm: false, can_draft: false,
        outcome: resolved, farewell: FAREWELLS[resolved] });
    }
    function publishSuccess() {
      if (!intent.value) return;
      const { action, payload } = intent.value;
      intent.value = null;
      if (action === "dream.say") {
        const turn = SCRIPT[state.completed];
        const next = applyEdits(state.proposal, turn.edits);
        state.changes = diffProposal(state.proposal, next);
        state.proposal = next;
        state.scene = turn.scene;
        state.dialogue = turn.dialogue;
        state.completed += 1;
        state.remaining = 6 - state.completed;
        state.track = track(state.completed);
        state.sample = SCRIPT[state.completed]?.sample || "";
        state.pending = false;
        if (state.completed >= 6) Object.assign(state, { stage: "penned", can_edit: true, can_confirm: true, can_finalize: false });
        state.can_input = state.stage === "wishing";
      } else if (action === "dream.choose_thread") {
        state.thread_id = payload.thread_id;
      } else if (action === "dream.finalize") {
        Object.assign(state, { stage: "penned", can_input: false, can_edit: true, can_confirm: true, can_finalize: false, drafted: true });
      } else if (action === "dream.draft" || action === "dream.confirm") {
        if (payload.direction) {
          const { summary, requirements, kind, thread_id: threadId, ...lists } = payload.direction;
          state.proposal = { ...emptyProposal(), ...lists, summary, requirements: requirements || [] };
          state.thread_id = threadId;
        }
        state.drafted = true;
        if (action === "dream.confirm") leaveWith("confirmed");
      } else if (action === "dream.awaken") {
        leaveWith("awaken");
      }
      state.revision += 1;
    }
    function publishFailure() {
      if (intent.value?.action !== "dream.say") return;
      intent.value = null;
      Object.assign(state, { pending: false, failure: true, can_input: true });
      state.revision += 1;
      note.value = "已發布生成失敗：這次不算數，願望維持原狀。";
    }
    function reset() {
      Object.assign(state, fixture(options));
      intent.value = null;
      epoch.value += 1;
    }
    if (leave) setTimeout(() => { leaveWith(leave); state.revision += 1; }, 400);
    const tools = () => h("details", { style: "font-family: var(--f-sans); font-size: var(--text-sm); color: var(--paper-500);" }, [
      h("summary", "原型工具（僅供展示）"),
      h("section", { "aria-label": "合成伺服器", style: "display: flex; gap: 12px; flex-wrap: wrap; align-items: center;" }, [
        h("label", [h("input", { type: "checkbox", checked: auto.value, onChange: (event) => { auto.value = event.target.checked; } }), " 自動發布成功"]),
        h("button", { class: "ui-btn ui-btn--sm", onClick: publishSuccess }, "發布成功"),
        h("button", { class: "ui-btn ui-btn--sm", onClick: publishFailure }, "發布生成失敗"),
        h("button", { class: "ui-btn ui-btn--sm", onClick: reset }, "重新開始"),
      ]),
      h("p", { role: "status" }, note.value),
      h("details", [h("summary", "檢視操作意圖"), h("pre", JSON.stringify(intent.value, null, 2))]),
    ]);
    return () => h("main", { style: "color: var(--paper-100);" }, [
      h(DreamWishPrototype, { key: epoch.value, state, store, initialLayer: openLayer,
        onDeparted: () => { note.value = "夢境已交還給既有的醒來流程。"; } }, { storyTools: tools }),
      // After the farewell the real client hands over to the waking flow.
      !state.open && h("button", { class: "ui-btn ui-btn--sm", style: "position: fixed; z-index: 4000; right: 24px; bottom: 24px;", onClick: reset }, "重新開始原型"),
    ]);
  },
});

// Arrival: the opening narration, the story choice above the reply bar.
export const Arrival = { render, ...atReference };
// No thread to continue: the choice is not shown at all.
export const ArrivalNoThreads = { render, ...atReference, args: { threads: [] } };
// After the first exchange: she wrote the wish, the thread is fixed.
export const FirstWish = { render, ...atReference, args: { turns: 1 } };
// A turn that rewrote the wish, added one item and struck another out.
export const ChangedWish = { render, ...atReference, args: { turns: 3, threadId: THREADS[0].id } };
// She only asked a question: nothing changed, and the card says so.
export const NothingChanged = { render, ...atReference, args: { turns: 4 } };
// The whole wish, read-only, with this turn's additions and removals named.
export const WholeWish = { render, ...atReference, args: { turns: 3, open: "view" } };
// The one irreversible step: what is given up, focus on staying.
export const StopSpeaking = { render, ...atReference, args: { turns: 3, open: "take" } };
// The player holds the form: every field edits, the thread stays fixed.
export const OwnHand = { render, ...atReference, args: { turns: 3, stage: "penned", drafted: true, open: "sheet" } };
// Six exchanges spent: the form is theirs without a warning.
export const AtCap = { render, ...atReference, args: { turns: 6 } };
// The farewell of a granted wish: it rises to the throne.
export const FarewellGranted = { render, ...atReference, args: { turns: 6, leave: "confirmed" } };
// Leaving with the wish kept for another night.
export const FarewellKept = { render, ...atReference, args: { turns: 2, leave: "awaken" } };
// The same stage at 1920×1080.
export const ChangedWishFullHd = { render, ...atFullHd, args: { turns: 3 } };
export const WholeWishFullHd = { render, ...atFullHd, args: { turns: 3, open: "view" } };
