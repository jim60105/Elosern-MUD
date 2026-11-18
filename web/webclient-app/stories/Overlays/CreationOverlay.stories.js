import { h, nextTick, onMounted, ref, toRaw } from "vue";
import CreationOverlay from "../../components/CreationOverlay.vue";
import {
  CREATION_PANEL_SAMPLE,
  CREATION_PANEL_PRESET_DRAFT_SAMPLE,
  CREATION_PANEL_CUSTOM_DRAFT_SAMPLE,
  CREATION_PANEL_PROPOSAL_SAMPLE,
  CREATION_PANEL_PROPOSAL_TRANSIENT_SAMPLE,
  CREATION_PANEL_UNAVAILABLE_SAMPLE,
  CREATION_PORTRAIT_STATES,
} from "../fixtures.js";
import { CREATION_PANEL_WALL_DRAFT_SAMPLE, CREATION_PANEL_WALL_SAMPLE } from "../fixtures/creation_wall.js";

// CreationOverlay (B5 overlays family): the full-viewport character-creation
// wizard for the committed `creation` v5 panel — preset pick, custom form
// (age bounds gate on BOTH the age and apparent_age fields, design D1), the
// concept branch (transient proposal fill, retool-concept-transient-fill),
// and the server-persisted wizard draft. Every action emits the exact
// `creation.*` OOB envelope; the offline showcase stays truthful: no
// invented preset fields, budgets, or affinity values.
//
// Chrome: the mode switch is the shared `.ui-tabs` segmented tray and every
// action is a shared `.ui-btn` from the control layer in `styles/tokens.css`,
// so this surface carries the same button and tab treatment as the rest of
// the client. The stories below walk the complete creation feature — every
// tab, the confirmation screen, the in-flight apply, the proposal fill, the
// rejected-result region, and the unavailable form.

const renderOverlay = (args) => ({ render: () => h(CreationOverlay, args) });

// Some wizard states are reached only by operating the surface (the concept
// tab, an in-flight apply). Those stories drive the component through its own
// controls after mount instead of inventing props the panel does not carry —
// deterministic, offline, and identical to what a player would do.
const renderAfterSteps = (args, steps) => ({
  setup() {
    onMounted(async () => {
      for (const step of steps) {
        await nextTick();
        step();
      }
    });
    return () => h(CreationOverlay, args);
  },
});

const click = (testid) => () => {
  document.querySelector(`[data-testid="${testid}"]`)?.click();
};

const fill = (testid, value) => () => {
  const field = document.querySelector(`[data-testid="${testid}"]`);
  if (!field) return;
  field.value = value;
  field.dispatchEvent(new Event("input", { bubbles: true }));
};

// Selects commit through `change`, the event their v-model listens to.
const choose = (testid, value) => () => {
  const field = document.querySelector(`[data-testid="${testid}"]`);
  if (!field) return;
  field.value = value;
  field.dispatchEvent(new Event("change", { bubbles: true }));
};

const step = (key) => click(`creation-steps-tab-${key}`);
const SUBRACED_RACE = CREATION_PANEL_SAMPLE.custom.races.find((race) => Array.isArray(race.subraces)).key;

// A partial proposal: some fill items omitted, zero-valued allocations and a
// zero age still count as filled (the concept guide's marks).
const CREATION_PANEL_PARTIAL_PROPOSAL_SAMPLE = {
  ...CREATION_PANEL_SAMPLE,
  proposal: {
    revision: 1,
    race: "human",
    subrace: null,
    allocations: { hp: 0, mp: 0, sp: 0, atk_phys: 0, agility: 0, defense: 0, magic_power: 0 },
    persona: { personality: "謹慎多疑", life_story: "", habit: "" },
    age: 0,
  },
};

export default {
  title: "Overlays/CreationOverlay",
  component: CreationOverlay,
};

// The entry state: no server draft, the preset card wall on the first tab
// with the first card expanded. These committed cards carry no official
// image, so every figure is the shared loader's alpha-terminal silhouette.
export const Default = {
  render: renderOverlay,
  args: { creation: CREATION_PANEL_SAMPLE },
};

// A saved preset draft: its card opens on entry with the 目前草稿 marker.
export const PresetDraft = {
  render: renderOverlay,
  args: { creation: CREATION_PANEL_PRESET_DRAFT_SAMPLE },
};

// The card wall at its design size (eight cards with figures; one image is
// missing and falls back to the silhouette). Opening a card is local; only
// the expanded card's 以〈名字〉啟程 emits the preset save.
export const PresetWall = {
  render: renderOverlay,
  args: { creation: CREATION_PANEL_WALL_SAMPLE },
};

// Browsing from a restored draft: the pointer opens the first collapsed
// card, a local expansion that emits no action.
export const PresetWallBrowsing = {
  render: (args) => renderAfterSteps(args, [click("creation-preset-open")]),
  args: { creation: CREATION_PANEL_WALL_DRAFT_SAMPLE },
};

// The custom form resumed from the server-persisted draft on its first
// step (身分), beside the portrait slot: the silhouette the server table names
// for the draft's sex and apparent age, and the draft name beneath it. The
// footer carries 重設 and the single primary 確認角色 on every step.
export const CustomDraft = {
  render: renderOverlay,
  args: { creation: CREATION_PANEL_CUSTOM_DRAFT_SAMPLE },
};

// Step 02 (角色故事): affinity, background and the persona triple.
export const CustomStoryStep = {
  render: (args) => renderAfterSteps(args, [step("story")]),
  args: { creation: CREATION_PANEL_CUSTOM_DRAFT_SAMPLE },
};

// Step 03 (能力配置): the running total, the briefing and the seven axes in
// two columns; the rail keeps the remaining points on every step.
export const CustomAllocationStep = {
  render: (args) => renderAfterSteps(args, [step("allocation")]),
  args: { creation: CREATION_PANEL_CUSTOM_DRAFT_SAMPLE },
};

// A fresh custom form: unnamed, default sex and age, so the slot shows the
// table's silhouette for that interval and the unnamed label.
export const CustomEmptySlot = {
  render: (args) => renderAfterSteps(args, [click("creation-mode-custom")]),
  args: { creation: CREATION_PANEL_SAMPLE },
};

// An over-budget sum: the rail's remainder turns negative (never clamped).
export const CustomOverBudget = {
  render: (args) => renderAfterSteps(args, [step("allocation"), fill("creation-field-agility", "4")]),
  args: { creation: CREATION_PANEL_CUSTOM_DRAFT_SAMPLE },
};

// Error routing: a subrace-bearing race without a subrace, confirmed from
// the allocation step, reopens 身分 at the subrace select with 需修正.
export const CustomIdentityError = {
  render: (args) =>
    renderAfterSteps(args, [choose("creation-race", SUBRACED_RACE), step("allocation"), click("creation-submit")]),
  args: { creation: CREATION_PANEL_CUSTOM_DRAFT_SAMPLE },
};

// A partially filled persona reopens 角色故事 at its first empty textarea.
export const CustomStoryError = {
  render: (args) =>
    renderAfterSteps(args, [step("story"), fill("creation-persona-habit", ""), step("identity"), click("creation-submit")]),
  args: { creation: CREATION_PANEL_CUSTOM_DRAFT_SAMPLE },
};

// A budget mismatch reopens 能力配置 at its first axis.
export const CustomAllocationError = {
  render: (args) =>
    renderAfterSteps(args, [step("allocation"), fill("creation-field-hp", "5"), step("identity"), click("creation-submit")]),
  args: { creation: CREATION_PANEL_CUSTOM_DRAFT_SAMPLE },
};

// -- The live portrait slot (creation-draft-portrait) --------------------------
// Each committed `portrait` state beside the saved draft. Empty, pending,
// failed and unavailable keep the server silhouette; ready shows the
// supplied artwork. Failed and unavailable show the server reason.
const portraitDraft = (state) => ({ ...CREATION_PANEL_CUSTOM_DRAFT_SAMPLE, portrait: CREATION_PORTRAIT_STATES[state] });

export const CustomPortraitPending = {
  render: renderOverlay,
  args: { creation: portraitDraft("pending") },
};

export const CustomPortraitReady = {
  render: renderOverlay,
  args: { creation: portraitDraft("ready") },
};

export const CustomPortraitFailed = {
  render: renderOverlay,
  args: { creation: portraitDraft("failed") },
};

export const CustomPortraitUnavailable = {
  render: renderOverlay,
  args: { creation: portraitDraft("unavailable") },
};

// 生成肖像 opens the real gallery drawer in creation context over the
// overlay: the prompt only, no field selection or equipment. Opening sends
// nothing (this standalone mount has no store, so a submit would only emit).
export const CustomPortraitDrawer = {
  render: (args) => renderAfterSteps(args, [click("creation-portrait-generate")]),
  args: { creation: portraitDraft("empty") },
};

// Regenerating from a ready portrait: the drawer shows it as the reference.
export const CustomPortraitDrawerReady = {
  render: (args) => renderAfterSteps(args, [click("creation-portrait-generate")]),
  args: { creation: portraitDraft("ready") },
};

// A refused submission (the shared gate held, simulated by a dispatch that
// admits nothing): the drawer keeps the typed prompt beside the existing
// rejection feedback.
export const CustomPortraitRefused = {
  render: (args) =>
    renderAfterSteps(args, [
      click("creation-portrait-generate"),
      () => {},
      () => {
        const field = document.querySelector('[data-drawer-key="creation-portrait"] textarea');
        if (!field) return;
        field.value = "月光下的城牆，回頭凝視";
        field.dispatchEvent(new Event("input", { bubbles: true }));
      },
      click("gallery-generate__submit"),
    ]),
  args: { creation: portraitDraft("empty"), dispatch: () => null },
};

// The server reports the art service unavailable while the drawer is open:
// submit is disabled, the prompt stays editable and a refresh is offered
// inside the drawer (it emits request-sync; nothing is generated).
export const CustomPortraitDrawerUnavailable = {
  render: (args) => ({
    setup() {
      const panel = ref(portraitDraft("empty"));
      onMounted(async () => {
        await nextTick();
        click("creation-portrait-generate")();
        await nextTick();
        panel.value = portraitDraft("unavailable");
      });
      return () => h(CreationOverlay, { ...args, creation: panel.value });
    },
  }),
  args: {},
};

// The concept tab: the guide column (nothing filled yet) beside the concept
// field, with the primary 套用概念 in the shared action bar.
export const ConceptMode = {
  render: (args) => renderAfterSteps(args, [click("creation-mode-concept")]),
  args: { creation: CREATION_PANEL_SAMPLE },
};

// The guide over a partial proposal: only the items it carries are marked.
export const ConceptPartialProposal = {
  render: (args) => renderAfterSteps(args, [click("creation-mode-concept")]),
  args: { creation: CREATION_PANEL_PARTIAL_PROPOSAL_SAMPLE },
};

// The guide over a complete proposal: every listed item is marked; sex and
// portrait are never listed.
export const ConceptFullProposal = {
  render: (args) => renderAfterSteps(args, [click("creation-mode-concept")]),
  args: { creation: CREATION_PANEL_PROPOSAL_TRANSIENT_SAMPLE },
};

// The in-flight apply (retool-concept-fill-navigation D1): the dispatch is
// admitted and never settles, so the spinner shows and the primary action is
// frozen and relabelled — the loading affordance the concept branch owes the
// player.
export const ConceptPending = {
  render: (args) =>
    renderAfterSteps(args, [
      click("creation-mode-concept"),
      fill("creation-field-concept", "在霧骨渡口長大的抄書女學徒，習慣睡前整理書架。"),
      click("creation-concept-submit"),
    ]),
  args: {
    creation: CREATION_PANEL_SAMPLE,
    // A return-bearing dispatch that admits the mutation (a requestId) and
    // never settles: exactly the pending window, no timers, no network.
    dispatch: () => "story-request-1",
  },
};

// The transient concept proposal applied into the custom form (the v2
// five-key slot). A mount-time fill deliberately lands OUTSIDE the concept
// tab and never navigates (retool-concept-transient-fill), so the story opens
// 自訂 the way the player would, to show what the fill actually wrote.
export const Proposal = {
  render: (args) => renderAfterSteps(args, [click("creation-mode-custom")]),
  args: { creation: CREATION_PANEL_PROPOSAL_SAMPLE },
};

// The expanded v3 proposal (bump-creation-panel-proposal-v3): name, ages,
// background and affinity arrive too — the wire's third element is trimmed to
// the human affinity cap of 2 before it reaches the form.
export const ProposalTransientFill = {
  render: (args) => renderAfterSteps(args, [click("creation-mode-custom")]),
  args: { creation: CREATION_PANEL_PROPOSAL_TRANSIENT_SAMPLE },
};

// The custom form with the server-declared gender select and the dice roll
// in flight (namegen-creation-ui): 女性 is picked, the 🎲 dispatch was
// admitted, and the settled success result backfills the name field — the
// story freezes the in-flight window, the component test proves the
// request-id-matched backfill.
export const CustomSexRoll = {
  render: (args) =>
    renderAfterSteps(args, [
      click("creation-mode-custom"),
      fill("creation-sex", "female"),
      click("creation-roll-name"),
    ]),
  args: {
    creation: CREATION_PANEL_SAMPLE,
    dispatch: () => "story-roll-1",
    result: null,
  },
};

// The confirmation screen (the legacy creation dock contract): the
// destructive step never dispatches until 確認 is pressed.
export const ConfirmStage = {
  render: renderOverlay,
  args: {
    creation: CREATION_PANEL_CUSTOM_DRAFT_SAMPLE,
    stage: { stage: "confirm", confirmLabel: "確認清除草稿並重新開始？" },
  },
};

// A recognized non-success `ui_action_result`: the overlay is the presenting
// surface in creation mode, so the server's message renders verbatim in the
// always-reachable result region.
export const RejectedResult = {
  render: renderOverlay,
  args: {
    creation: CREATION_PANEL_CUSTOM_DRAFT_SAMPLE,
    result: {
      outcome: "rejected",
      code: "creation_draft_stale",
      message: "草稿版本已過期，請重新整理後再送出。",
    },
  },
};

// The registry-owned unavailable form: the server's reason verbatim, no
// invented controls.
export const Unavailable = {
  render: renderOverlay,
  args: { creation: CREATION_PANEL_UNAVAILABLE_SAMPLE },
};

// An explicit publication desk, not a server emulator: nothing settles on a
// timer. Every frame mounts the production wizard and uses synthetic panels.
export const Storyboard = {
  render: () => ({
    setup() {
      const panel = ref(structuredClone(CREATION_PANEL_SAMPLE));
      const stage = ref({ stage: "root" });
      const result = ref(null);
      const dispatchState = ref({ inFlight: null, submittedRequestId: null });
      const intent = ref(null);
      const notice = ref("展示資料，所有發布操作僅供故事展示。");
      const mountKey = ref(0);
      let sequence = 0;
      let proposalRevision = 0;
      let previousStage = "root";
      function dispatch(action) {
        if (dispatchState.value.inFlight !== null) return null;
        const requestId = `creation-story-${++sequence}`;
        intent.value = structuredClone(action);
        result.value = null;
        dispatchState.value = { inFlight: requestId, submittedRequestId: requestId };
        notice.value = "已記錄操作意圖，請選擇發布成功或發布拒絕。";
        return requestId;
      }
      function publish(success) {
        if (!intent.value || dispatchState.value.inFlight === null) return;
        const { action_id: actionId, payload } = toRaw(intent.value);
        result.value = {
          requestId: dispatchState.value.submittedRequestId,
          outcome: success ? "success" : "rejected",
          message: success ? "" : "展示拒絕：資料未通過驗證，請檢查後重試。",
          ...(actionId === "creation.roll_name" && success
            ? { data: { display_name: CREATION_PANEL_CUSTOM_DRAFT_SAMPLE.draft.display_name } } : {}),
        };
        if (success && actionId === "creation.concept") {
          panel.value = {
            ...panel.value,
            proposal: { ...structuredClone(CREATION_PANEL_PROPOSAL_TRANSIENT_SAMPLE.proposal), revision: ++proposalRevision },
          };
        } else if (success && ["creation.preset", "creation.custom"].includes(actionId)) {
          const draft = actionId === "creation.preset"
            ? { mode: "preset", stage: "preset_selected", preset_key: payload.preset_key }
            : { ...payload, mode: "custom", stage: "custom_filled" };
          panel.value = { ...panel.value, draft };
          previousStage = actionId === "creation.preset" ? "presets" : "custom";
          stage.value = { stage: "confirm", confirmAction: "creation.activate", confirmLabel: "確認以這份草稿建立角色？" };
        } else if (success && actionId === "creation.reset") {
          panel.value = structuredClone(CREATION_PANEL_SAMPLE);
          stage.value = { stage: "root" };
          mountKey.value++;
        }
        notice.value = success && actionId === "creation.activate"
          ? "已發布啟用成功。正式遊戲接續探索畫面；此展示保留建角工作區。"
          : success ? "已發布成功。" : "已發布拒絕，保留目前輸入。";
        dispatchState.value = { ...dispatchState.value, inFlight: null };
      }
      function reconnect() {
        panel.value = { ...structuredClone(toRaw(panel.value)), proposal: undefined };
        stage.value = { stage: panel.value.draft?.mode === "custom" ? "custom" : "root" };
        result.value = null;
        dispatchState.value = { inFlight: null, submittedRequestId: null };
        mountKey.value++;
        notice.value = "已重新掛載，僅恢復已發布的草稿。";
      }
      const button = (text, handler, disabled = false) =>
        h("button", { class: "ui-btn", type: "button", onClick: handler, disabled }, text);
      return () => h("div", { class: "elosern", style: "position:absolute;inset:0;display:flex;flex-direction:column;background:var(--ink-950)" }, [
        h("div", { "aria-label": "故事發布控制", style: "padding:8px 16px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;border-bottom:1px dashed var(--gold-500)" }, [
          h("span", { style: "color:var(--gold-400);font-size:16px" }, "故事發布控制"),
          button("發布成功", () => publish(true), dispatchState.value.inFlight === null),
          button("發布拒絕", () => publish(false), dispatchState.value.inFlight === null),
          button("重新連線", reconnect),
          button("發布自訂草稿", () => {
            panel.value = structuredClone(CREATION_PANEL_CUSTOM_DRAFT_SAMPLE);
            reconnect();
          }),
          h("details", [
            h("summary", { style: "cursor:pointer;color:var(--paper-300)" }, "檢視操作意圖"),
            h("pre", { style: "max-height:160px;overflow:auto;color:var(--paper-100)" }, JSON.stringify(intent.value, null, 2)),
          ]),
        ]),
        h("p", { role: "status", style: "margin:0;padding:4px 16px;color:var(--paper-400);font-size:16px" }, notice.value),
        h("div", { style: "position:relative;flex:1;min-height:0" }, [
          h(CreationOverlay, {
            key: mountKey.value, creation: panel.value, stage: stage.value,
            result: result.value, dispatchState: dispatchState.value, dispatch,
            onAction: dispatch,
            onRequestReset: () => {
              previousStage = panel.value.draft?.mode === "custom" ? "custom" : "root";
              stage.value = { stage: "confirm", confirmAction: "creation.reset", confirmLabel: "確認清除草稿並重新開始？" };
            },
            onCancelConfirm: () => { stage.value = { stage: previousStage }; },
            pushToast: ({ title }) => { notice.value = title; },
          }),
        ]),
      ]);
    },
  }),
};
