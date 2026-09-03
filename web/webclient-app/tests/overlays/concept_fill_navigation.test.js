// retool-concept-fill-navigation task 1.0 + lifecycle contracts: the concept
// journey over the REAL store (fake transport) through the mounted AppClient.
// This file is the instrumented reproduction of the user-reported tab-kick
// bug and the permanent record of its pinned mechanism:
//
//   The stage watcher mirrors a stage VALUE change onto the wizard mode, and
//   `view.creationView` is a fresh object on every `publishView()`. Mount
//   leaves `lastStage = null`, so the first publish that carries a stage
//   value passes the null gate — and `dispatchAction()` publishes
//   synchronously in its finally. Clicking 套用概念 therefore re-emits stage
//   "root" (value !== lastStage) and the unfixed watcher writes
//   mode = "preset": the player is kicked off the concept tab at the moment
//   of the click with zero feedback (traced, pre-fix, as
//   "click apply -> mode=preset"). A second face of the same race lives
//   inside a completion commit whose stage value also changes: the proposal
//   watcher (registered earlier) applies first, then the stage watcher
//   overwrites the completion navigation.
//
// Every mode transition is recorded into `trace` with its triggering commit,
// so the post-fix assertions double as the lifecycle regression pin.

import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../../AppClient.vue";
import CreationOverlay from "../../components/CreationOverlay.vue";
import { useElosernStore } from "../../stores/elosern.js";
import {
  CREATION_PANEL_SAMPLE,
  CREATION_PANEL_PROPOSAL_SAMPLE,
  CREATION_PANEL_PROPOSAL_TRANSIENT_SAMPLE,
} from "../../stories/fixtures.js";
import * as fx from "../store/protocol_fixtures.js";

const CONCEPT_TEXT = "一個貓人少女，有豐富的背景設定";

function creationPanel(proposal) {
  return proposal === undefined
    ? { ...CREATION_PANEL_SAMPLE }
    : { ...CREATION_PANEL_SAMPLE, proposal };
}

describe("concept fill navigation lifecycle (retool-concept-fill-navigation)", () => {
  let store;
  let sender;
  let host;
  let wrapper;
  let trace;
  let revision;

  function modeNow() {
    return host
      .querySelector('[data-testid="creation-overlay"]')
      ?.getAttribute("data-mode");
  }

  async function step(label) {
    await wrapper.vm.$nextTick();
    trace.push(`${label} -> mode=${modeNow()}`);
  }

  function lastLine() {
    return trace[trace.length - 1];
  }

  function openCreation() {
    store.beginTransport(1);
    store.setConnected(true);
    revision = 2;
    expect(
      store.receive(
        1,
        "ui_snapshot",
        [fx.snapshot({ mode: "creation", revision, panels: { creation: creationPanel() } })],
        {},
      ).accepted,
    ).toBe(true);
  }

  function commitCreation(proposal) {
    revision += 1;
    expect(
      store.receive(
        1,
        "ui_update",
        [
          fx.update({
            mode: "creation",
            revision,
            panels: { creation: creationPanel(proposal) },
          }),
        ],
        {},
      ).accepted,
    ).toBe(true);
  }

  function deliverResult(fields) {
    store.receive(1, "ui_action_result", [fx.actionResult(fields)], {});
  }

  async function mountApp() {
    openCreation();
    host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    wrapper = mount(AppClient, { attachTo: host });
    await wrapper.vm.$nextTick();
  }

  async function clickTestId(testid) {
    host.querySelector(`[data-testid="${testid}"]`).dispatchEvent(
      new MouseEvent("click", { bubbles: true }),
    );
    await wrapper.vm.$nextTick();
  }

  async function typeConcept(text) {
    const field = host.querySelector('[data-testid="creation-field-concept"]');
    field.value = text;
    field.dispatchEvent(new Event("input", { bubbles: true }));
    await wrapper.vm.$nextTick();
  }

  async function toConceptTabAndSubmit(label = "click apply") {
    await mountApp();
    await step("mount");
    await clickTestId("creation-mode-concept");
    await step("click concept tab");
    await typeConcept(CONCEPT_TEXT);
    await clickTestId("creation-concept-submit");
    await step(label);
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
    trace = [];
    revision = 2;
  });

  afterEach(() => {
    wrapper?.unmount();
    document.body.innerHTML = "";
    host = null;
    wrapper = null;
    store.$dispose();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  // -- Task 1.0: the kick path reproduced and pinned ------------------------

  it("a dispatched concept keeps the concept tab alive through the dispatch publish (pinned kick path)", async () => {
    await toConceptTabAndSubmit();
    // Pre-fix the recorded trace line here is "click apply -> mode=preset":
    // dispatchAction's synchronous finally-publish re-emitted stage "root"
    // while lastStage was still null and the unfixed watcher kicked the tab.
    expect(trace.join(" | ")).toContain("click apply -> mode=concept");
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({
      action_id: "creation.concept",
      payload: { concept: CONCEPT_TEXT },
    });
    expect(store.view.dispatch.inFlight).not.toBe(null);

    // The concept tab presents the waiting state and freezes its inputs.
    const loading = host.querySelector('[data-testid="creation-concept-loading"]');
    expect(loading).not.toBe(null);
    expect(loading.getAttribute("role")).toBe("status");
    expect(loading.textContent).toContain("概念生成中，請稍候…");
    expect(host.querySelector('[data-testid="creation-field-concept"]').disabled).toBe(true);
    expect(host.querySelector('[data-testid="creation-concept-submit"]').disabled).toBe(true);

    // An unrelated creation-panel commit mid-flight must not move the tab.
    commitCreation(undefined);
    await step("mid-flight unrelated commit");
    expect(lastLine()).toContain("mode=concept");

    // Completion: the fresh proposal lands, the waiting state settles, the
    // form auto-lands on the custom tab with the five transient fields
    // filled, and exactly one info toast confirms the apply.
    commitCreation(CREATION_PANEL_PROPOSAL_TRANSIENT_SAMPLE.proposal);
    await step("proposal commit");
    expect(lastLine()).toContain("mode=custom");
    expect(host.querySelector('[data-testid="creation-concept-loading"]')).toBe(null);
    expect(host.querySelector('[data-testid="creation-field-displayName"]').value).toBe("莉雅");
    expect(host.querySelector('[data-testid="creation-field-age"]').value).toBe("26");
    expect(host.querySelector('[data-testid="creation-field-apparentAge"]').value).toBe("24");
    expect(host.querySelector('[data-testid="creation-background"]').value).toBe(
      "燈下抄書的女學徒。",
    );
    expect(host.querySelector('[data-testid="creation-affinity-fire"]').checked).toBe(true);
    expect(host.querySelector('[data-testid="creation-affinity-wind"]').checked).toBe(true);
    expect(host.querySelector('[data-testid="creation-affinity-water"]').checked).toBe(false);
    expect(host.querySelector('[data-testid="creation-persona-personality"]').value).toBe(
      "沉穩內斂",
    );
    expect(store.view.toasts).toEqual([
      { id: expect.any(Number), title: "概念提案已套用到自訂表單", tone: "info" },
    ]);
    // A panel rebuild republishing the SAME revision fills nothing new,
    // navigates nothing, and never re-confirms.
    commitCreation(CREATION_PANEL_PROPOSAL_TRANSIENT_SAMPLE.proposal);
    await step("same-revision rebuild");
    expect(lastLine()).toContain("mode=custom");
    expect(store.view.toasts).toHaveLength(1);
  });

  it("a non-success concept result settles the waiting state and the store writes one crit toast", async () => {
    await toConceptTabAndSubmit();
    expect(host.querySelector('[data-testid="creation-concept-loading"]')).not.toBe(null);
    deliverResult({
      request_id: "session:1",
      outcome: "rejected",
      code: "ai_unavailable",
      message: "概念服務目前無法使用，請稍後再試。",
      presentation_revision: 2,
    });
    await step("rejected result");
    expect(lastLine()).toContain("mode=concept");
    expect(host.querySelector('[data-testid="creation-concept-loading"]')).toBe(null);
    expect(host.querySelector('[data-testid="creation-field-concept"]').disabled).toBe(false);
    // The overlay result region speaks the server message verbatim and the
    // store slice pushed exactly one crit toast (single writer for failure).
    expect(host.querySelector('[data-testid="creation-result-message"]').textContent).toContain(
      "概念服務目前無法使用，請稍後再試。",
    );
    expect(store.view.toasts.map((t) => t.tone)).toEqual(["crit"]);
    expect(store.view.toasts[0].title).toBe("概念服務目前無法使用，請稍後再試。");
    // Re-delivering the committed result never re-pushes (fingerprint dedup).
    deliverResult({
      request_id: "session:1",
      outcome: "rejected",
      code: "ai_unavailable",
      message: "概念服務目前無法使用，請稍後再試。",
      presentation_revision: 2,
    });
    await wrapper.vm.$nextTick();
    expect(store.view.toasts).toHaveLength(1);
  });

  it("a result for another request does not settle the waiting state", async () => {
    await toConceptTabAndSubmit();
    deliverResult({
      request_id: "session:9",
      outcome: "rejected",
      code: "stale_revision",
      message: "舊請求已被駁回。",
      presentation_revision: 2,
    });
    await wrapper.vm.$nextTick();
    expect(host.querySelector('[data-testid="creation-concept-loading"]')).not.toBe(null);
    expect(store.view.toasts).toEqual([]);
  });

  it("a gate-rejected apply never enters the waiting state (admission-gated pending)", async () => {
    await mountApp();
    // Absorb one root-stage publish first so `lastStage` is "root": the
    // gate-holding foreign dispatch's own publish then carries an unchanged
    // stage value and the concept tab legitimately stays presented.
    commitCreation(undefined);
    await wrapper.vm.$nextTick();
    await clickTestId("creation-mode-concept");
    await typeConcept("第二次概念");
    // Admit a different mutation first: a concept apply is now gate-rejected.
    expect(store.dispatchAction("creation.preset", { preset_key: "preset_harbor_hauler" })).toBe(
      "session:1",
    );
    await wrapper.vm.$nextTick();
    const apply = host.querySelector('[data-testid="creation-concept-submit"]');
    expect(apply.disabled).toBe(true); // frozen while the global gate is held
    expect(modeNow()).toBe("concept");
    apply.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await wrapper.vm.$nextTick();
    // Even a forced click on the frozen control creates no waiting state:
    // pending is set only after the dispatch is admitted.
    expect(host.querySelector('[data-testid="creation-concept-loading"]')).toBe(null);
    expect(sender.sent.actions.map((a) => a.action_id)).toEqual(["creation.preset"]);
    // Releasing the gate restores an editable, enabled concept tab.
    deliverResult({
      request_id: "session:1",
      outcome: "rejected",
      code: "no_draft",
      message: "動作未生效，請重試或返回上層。",
      presentation_revision: 2,
    });
    await wrapper.vm.$nextTick();
    expect(host.querySelector('[data-testid="creation-concept-submit"]').disabled).toBe(false);
    expect(host.querySelector('[data-testid="creation-concept-loading"]')).toBe(null);
    expect(host.querySelector('[data-testid="creation-field-concept"]').value).toBe("第二次概念");
  });

  it("a synchronously failed dispatch never sticks the waiting state (gate-release safety net)", async () => {
    await mountApp();
    await clickTestId("creation-mode-concept");
    await typeConcept("斷線概念");
    sender.sendAction = () => {
      throw new Error("socket closed");
    };
    await clickTestId("creation-concept-submit");
    await step("admitted then synchronously failed");
    // The store caught the synchronous failure, released its gate (uncertain)
    // and published; the safety net settles the waiting state — no stuck
    // spinner, the concept tab stays editable for a retry.
    expect(store.view.dispatch.inFlight).toBe(null);
    expect(lastLine()).toContain("mode=concept");
    expect(host.querySelector('[data-testid="creation-concept-loading"]')).toBe(null);
    expect(host.querySelector('[data-testid="creation-concept-submit"]').disabled).toBe(false);
    expect(host.querySelector('[data-testid="creation-field-concept"]').value).toBe("斷線概念");
  });

  it("a proposal-only panel refresh never navigates the dock (store contract)", async () => {
    await mountApp();
    expect(store.view.creationView.stage).toBe("root");
    commitCreation(CREATION_PANEL_PROPOSAL_TRANSIENT_SAMPLE.proposal);
    await wrapper.vm.$nextTick();
    // The panel signature covers presets, races, and the draft only: a
    // proposal delivery alone never moves the dock stage.
    expect(store.view.creationView.stage).toBe("root");
    expect(store.view.panels.creation.proposal.revision).toBe(1);
  });
});

// Standalone-overlay pins: the in-flight pin and the completion-publish latch
// gate on stage OBJECT IDENTITY, which the real store harness cannot exercise
// directly (the store's unchanged-value gate absorbs those publishes first).
// These mount the overlay alone and drive props the way a commit would.
describe("concept fill navigation pins (standalone overlay)", () => {
  function proposalSample(revision) {
    return {
      ...CREATION_PANEL_SAMPLE,
      proposal: { ...CREATION_PANEL_PROPOSAL_TRANSIENT_SAMPLE.proposal, revision },
    };
  }

  it("the in-flight pin holds the concept tab against stage value changes and the latch keeps the completion landing", async () => {
    const dispatch = vi.fn(() => "request-1");
    const pushToast = vi.fn();
    const wrapper = mount(CreationOverlay, {
      props: {
        creation: CREATION_PANEL_SAMPLE,
        stage: { stage: "root" },
        dispatch,
        pushToast,
      },
    });
    wrapper.get('[data-testid="creation-mode-concept"]').trigger("click");
    await nextTick();
    wrapper.get('[data-testid="creation-field-concept"]').setValue("釘住的測試");
    wrapper.get('[data-testid="creation-concept-submit"]').trigger("click");
    await nextTick();
    expect(dispatch).toHaveBeenCalledWith({
      action_id: "creation.concept",
      payload: { concept: "釘住的測試" },
    });
    expect(wrapper.get('[data-testid="creation-concept-loading"]').exists()).toBe(true);

    // Mid-flight a dock stage VALUE change (presets) must not move the
    // presented tab: the pin records the value but never writes `mode`.
    wrapper.setProps({ stage: { stage: "presets" } });
    await nextTick();
    expect(wrapper.get('[data-testid="creation-overlay"]').attributes("data-mode")).toBe("concept");

    // The completion commit carries the fresh proposal AND another stage
    // value change (root): the proposal watcher lands on custom first, and
    // the completion-publish latch swallows this publish's stale signal —
    // without the latch the value change would kick the landing back to
    // preset in the same flush.
    wrapper.setProps({ creation: proposalSample(1), stage: { stage: "root" } });
    await nextTick();
    expect(wrapper.get('[data-testid="creation-overlay"]').attributes("data-mode")).toBe("custom");
    expect(wrapper.find('[data-testid="creation-concept-loading"]').exists()).toBe(false);
    expect(pushToast).toHaveBeenCalledTimes(1);
    expect(pushToast).toHaveBeenCalledWith({
      title: "概念提案已套用到自訂表單",
      tone: "info",
    });

    // The very next publish is a NEW object: the latch is one-signal bounded
    // and a legitimate keyboard stage change mirrors again.
    wrapper.setProps({ stage: { stage: "concept" } });
    await nextTick();
    expect(wrapper.get('[data-testid="creation-overlay"]').attributes("data-mode")).toBe("concept");
  });

  it("an admitted-then-null dispatch (gate reject) never lights the loading state", async () => {
    const dispatch = vi.fn(() => null);
    const wrapper = mount(CreationOverlay, {
      props: { creation: CREATION_PANEL_SAMPLE, stage: { stage: "root" }, dispatch },
    });
    wrapper.get('[data-testid="creation-mode-concept"]').trigger("click");
    await nextTick();
    wrapper.get('[data-testid="creation-field-concept"]').setValue("被拒絕的概念");
    wrapper.get('[data-testid="creation-concept-submit"]').trigger("click");
    await nextTick();
    expect(dispatch).toHaveBeenCalledTimes(1);
    expect(wrapper.find('[data-testid="creation-concept-loading"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="creation-overlay"]').attributes("data-mode")).toBe("concept");
  });

  it("a foreign non-success result without dispatch state renders verbatim and never throws (standalone guard)", async () => {
    const wrapper = mount(CreationOverlay, {
      props: {
        creation: CREATION_PANEL_SAMPLE,
        result: {
          requestId: "someone-else",
          outcome: "rejected",
          code: "no_draft",
          message: "目前沒有可續寫的草稿。",
        },
      },
    });
    await nextTick();
    expect(wrapper.get('[data-testid="creation-result-message"]').text()).toContain(
      "目前沒有可續寫的草稿。",
    );
    expect(wrapper.find('[data-testid="creation-concept-loading"]').exists()).toBe(false);
  });

  it("the five-field map leaves absent keys untouched and trims affinity to the new race cap", async () => {
    // Human cap 2: the sample wire carries three registered keys — only the
    // first two land. A second proposal without the transient keys (race
    // elf) must not clear name/ages/background but must empty affinity to
    // the elf bound (0) via the race trim.
    const wrapper = mount(CreationOverlay, {
      props: { creation: CREATION_PANEL_SAMPLE, stage: { stage: "custom" } },
    });
    wrapper.get('[data-testid="creation-mode-custom"]').trigger("click");
    await nextTick();
    wrapper.setProps({ creation: proposalSample(1) });
    await nextTick();
    expect(wrapper.get('[data-testid="creation-field-displayName"]').element.value).toBe("莉雅");
    expect(wrapper.get('[data-testid="creation-field-age"]').element.value).toBe("26");
    expect(wrapper.get('[data-testid="creation-field-apparentAge"]').element.value).toBe("24");
    expect(wrapper.get('[data-testid="creation-background"]').element.value).toBe(
      "燈下抄書的女學徒。",
    );
    expect(wrapper.get('[data-testid="creation-affinity-fire"]').element.checked).toBe(true);
    expect(wrapper.get('[data-testid="creation-affinity-wind"]').element.checked).toBe(true);
    expect(wrapper.get('[data-testid="creation-affinity-water"]').element.checked).toBe(false);
    // Absent transient keys leave the local values untouched; the elf race
    // (bound 0) empties the selection via the race trim.
    wrapper.setProps({ creation: { ...CREATION_PANEL_PROPOSAL_SAMPLE, proposal: { ...CREATION_PANEL_PROPOSAL_SAMPLE.proposal, revision: 2 } } });
    await nextTick();
    expect(wrapper.get('[data-testid="creation-field-displayName"]').element.value).toBe("莉雅");
    expect(wrapper.get('[data-testid="creation-field-age"]').element.value).toBe("26");
    expect(wrapper.get('[data-testid="creation-background"]').element.value).toBe(
      "燈下抄書的女學徒。",
    );
    expect(
      wrapper
        .findAll('[data-testid^="creation-affinity-"]')
        .filter((node) => node.element.checked),
    ).toHaveLength(0);
  });
});
