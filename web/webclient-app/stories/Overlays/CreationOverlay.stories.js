import { h, nextTick, onMounted, ref, toRaw } from "vue";
import CreationOverlay from "../../components/CreationOverlay.vue";
import {
  CREATION_PANEL_SAMPLE,
  CREATION_PANEL_PRESET_DRAFT_SAMPLE,
  CREATION_PANEL_CUSTOM_DRAFT_SAMPLE,
  CREATION_PANEL_PROPOSAL_SAMPLE,
  CREATION_PANEL_PROPOSAL_TRANSIENT_SAMPLE,
  CREATION_PANEL_UNAVAILABLE_SAMPLE,
} from "../fixtures.js";

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
  field.dispatchEvent(new Event("input"));
};

export default {
  title: "Overlays/CreationOverlay",
  component: CreationOverlay,
};

// The entry state: no server draft, the preset cards on the first tab.
export const Default = {
  render: renderOverlay,
  args: { creation: CREATION_PANEL_SAMPLE },
};

export const PresetDraft = {
  render: renderOverlay,
  args: { creation: CREATION_PANEL_PRESET_DRAFT_SAMPLE },
};

// The custom form resumed from the server-persisted draft, with the sticky
// action bar carrying 重設 and the single primary 確認自訂.
export const CustomDraft = {
  render: renderOverlay,
  args: { creation: CREATION_PANEL_CUSTOM_DRAFT_SAMPLE },
};

// The concept tab: the free-text concept field with the primary 套用概念 in
// the shared action bar.
export const ConceptMode = {
  render: (args) => renderAfterSteps(args, [click("creation-mode-concept")]),
  args: { creation: CREATION_PANEL_SAMPLE },
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
          h("span", { style: "color:var(--gold-400);font-size:13px" }, "故事發布控制"),
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
        h("p", { role: "status", style: "margin:0;padding:4px 16px;color:var(--paper-400);font-size:13px" }, notice.value),
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
