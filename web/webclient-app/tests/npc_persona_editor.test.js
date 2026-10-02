import { afterEach, describe, expect, it, vi } from "vitest";
import { effectScope, nextTick, reactive } from "vue";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { useNpcPersonaEditor } from "../composables/use-npc-persona-editor.js";
import NpcPersonaEditor from "../components/NpcPersonaEditor.vue";
import { npcPersonaEditorStates, NPC_PERSONA_READ_SAMPLE as sample } from "../stories/npc-persona-fixtures.js";
import { validateDraft, draftFromData } from "../components/npc-persona-editor-model.js";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";

const scopes = [], wrappers = [];
afterEach(() => { scopes.splice(0).forEach(s => s.stop()); wrappers.splice(0).forEach(w => w.unmount()); vi.restoreAllMocks(); document.body.innerHTML = ""; });
function fixture() {
  let seq = 0;
  const store = { view: reactive({ connected: true, phase: "active", epoch: "a", generation: 1, hudDrawer: null, mutationsLocked: false, dispatch: { inFlight: null }, mode: "exploration", rosterCharacters: [{ identity: 42, current: true }], panels: { exploration: { available: true, interact: [{ identity: sample.npc_id }, { identity: 99 }] } }, lastActionResult: null, npcPersonaRequest: null }), dispatchAction: vi.fn(() => `r:${++seq}`), closeHudDrawer() { this.view.hudDrawer = null; } };
  const scope = effectScope(); scopes.push(scope);
  const ed = scope.run(() => useNpcPersonaEditor(store));
  const view = () => ed.npcPersonaEditor.value;
  async function open(id = sample.npc_id) { store.view.npcPersonaRequest = { npcId: id, seq: ++seq }; store.view.hudDrawer = "npc_persona"; await nextTick(); }
  async function result(data = sample, extra = {}) { const id = store.dispatchAction.mock.results.at(-1).value; store.view.lastActionResult = { requestId: id, epoch: store.view.epoch, outcome: "success", data, ...extra }; await nextTick(); }
  return { store, ed, view, open, result };
}

describe("NPC editor state machine", () => {
  it("binds once, ignores superseded and wrong-target reads, and clears on close", async () => {
    const f = fixture(); await f.open(); const old = f.store.dispatchAction.mock.results.at(-1).value;
    expect(f.store.dispatchAction).toHaveBeenCalledTimes(1);
    f.ed.npcPersonaClose(); await nextTick(); await f.open(99);
    f.store.view.lastActionResult = { requestId: old, epoch: "a", outcome: "success", data: sample }; await nextTick();
    expect(f.view().baseline).toBe(null);
    await f.result({ ...sample, npc_id: 99 }); expect(f.view().npcId).toBe(99);
    f.ed.npcPersonaClose(); expect(f.view().draft.speech_style).toBe("");
  });
  it("submits once and only adopts a confirmed save", async () => {
    const f = fixture(); await f.open(); await f.result();
    f.ed.npcPersonaSetField("offline_greeting", "新問候");
    expect(f.ed.npcPersonaSave()).toBe(true); expect(f.ed.npcPersonaSave()).toBe(false);
    expect(f.view().state).toBe("saving"); expect(f.view().baseline.offline_greeting).toBe("");
    await f.result({ ...sample, persona_version: 4, offline_greeting: "新問候" });
    expect(f.view().state).toBe("ready_clean"); expect(f.view().version).toBe(4);
    expect(f.store.dispatchAction.mock.calls.filter(c => c[0] === "npc.persona.update")).toHaveLength(1);
  });
  it.each([["speech_style", "npc_persona.required_empty.speech_style"], ["offline_greeting", "npc_persona.greeting_invalid"]])("retains rejected %s and requests field focus", async (field, code) => {
    const f = fixture(); await f.open(); await f.result(); f.ed.npcPersonaSetField(field, "修改"); f.ed.npcPersonaSave();
    await f.result(null, { outcome: "rejected", code, message: "未通過檢查" });
    expect(f.view().draft[field]).toBe("修改"); expect(f.view().baseline[field]).not.toBe("修改"); expect(f.view().focusRequest.field).toBe(field);
  });
  it("reloads conflicts without merging, then explicitly discards to latest baseline", async () => {
    const f = fixture(); await f.open(); await f.result(); f.ed.npcPersonaSetField("habit", "草稿"); f.ed.npcPersonaSave();
    await f.result(null, { outcome: "rejected", code: "npc_persona.version_conflict", message: "版本衝突" }); expect(f.view().state).toBe("conflict");
    f.ed.npcPersonaReload(); await f.result({ ...sample, persona_version: 4, persona: { ...sample.persona, habit: "他處修改" } });
    expect(f.view().draft.habit).toBe("草稿"); expect(f.view().baseline.habit).toBe("他處修改"); expect(f.view().canSave).toBe(true);
    f.ed.npcPersonaDiscard(); expect(f.view().draft.habit).toBe("他處修改");
  });
  it("keeps departed drafts, ignores snapshot refreshes, and recovers on return", async () => {
    const f = fixture(); await f.open(); await f.result(); f.ed.npcPersonaSetField("habit", "草稿");
    f.store.view.panels.exploration.interact = []; await nextTick(); expect(f.view().state).toBe("unavailable"); expect(f.view().canSave).toBe(false);
    f.store.view.panels.exploration.interact = [{ identity: sample.npc_id }]; await nextTick(); expect(f.view().draft.habit).toBe("草稿"); expect(f.view().canSave).toBe(true);
  });
  it.each([false, true])("re-reads after reconnect, moved version conflict=%s", async (moved) => {
    const f = fixture(); await f.open(); await f.result(); f.ed.npcPersonaSetField("habit", "草稿"); f.ed.npcPersonaSave();
    f.store.view.connected = false; await nextTick(); expect(f.view().canSave).toBe(false); expect(f.view().draft.habit).toBe("草稿");
    f.store.view.generation = 2; f.store.view.epoch = "b"; f.store.view.connected = true; f.store.view.mutationsLocked = true; await nextTick();
    expect(f.store.dispatchAction).toHaveBeenCalledTimes(2);
    f.store.view.mutationsLocked = false; await nextTick(); expect(f.store.dispatchAction).toHaveBeenCalledTimes(3);
    await f.result({ ...sample, persona_version: moved ? 4 : 3 }); expect(f.view().state).toBe(moved ? "conflict" : "ready_dirty"); expect(f.view().draft.habit).toBe("草稿");
  });
  it.each(["detach", "epoch", "character"])("clears private state on %s replacement", async (kind) => {
    const f = fixture(); await f.open(); await f.result();
    if (kind === "detach") f.store.view.phase = "detached";
    else if (kind === "epoch") f.store.view.epoch = "other";
    else { f.store.view.connected = false; await nextTick(); f.store.view.generation = 2; f.store.view.epoch = "b"; f.store.view.rosterCharacters = [{ current: true, identity: 43 }]; f.store.view.connected = true; }
    await nextTick(); expect(f.view().open).toBe(false); expect(f.view().draft["identity.hidden"]).toBe("");
  });
  it("never writes persistent browser storage across an edit journey", async () => {
    const storage = vi.spyOn(Storage.prototype, "setItem"); const f = fixture(); await f.open(); await f.result(); f.ed.npcPersonaSetField("habit", "草稿"); f.ed.npcPersonaClose(); expect(storage).not.toHaveBeenCalled();
  });
  it("settles a reconnect during the initial read without repeated reads", async () => {
    const f = fixture(); await f.open(); f.store.view.connected = false; await nextTick();
    f.store.view.generation = 2; f.store.view.epoch = "b"; f.store.view.connected = true; await nextTick();
    await f.result(); await nextTick(); expect(f.view().state).toBe("ready_clean"); expect(f.store.dispatchAction).toHaveBeenCalledTimes(2);
  });
});

describe("NPC editor dialog", () => {
  function render(editor) { const w = mount(NpcPersonaEditor, { props: { editor }, attachTo: document.body }); wrappers.push(w); return w; }
  it("names the dialog, labels every field, and contains keyboard focus", async () => {
    const w = render(npcPersonaEditorStates.clean()); await nextTick(); const dialog = w.get('[role="dialog"]');
    expect(document.getElementById(dialog.attributes("aria-labelledby")).textContent).toContain(sample.display_name);
    for (const control of w.findAll("textarea")) expect(w.find(`label[for="${control.attributes("id")}"]`).exists()).toBe(true);
    const buttons = w.findAll("button"); buttons.at(-1).element.focus(); await buttons.at(-1).trigger("keydown", { key: "Tab" }); expect(dialog.element.contains(document.activeElement)).toBe(true);
  });
  it("does not truncate greeting overflow or charge it to the card", () => {
    const draft = draftFromData(sample), before = validateDraft(draft).total.used; draft.offline_greeting = "😀".repeat(301);
    const check = validateDraft(draft); expect(check.greeting.used).toBe(301); expect(check.greeting.over).toBe(true); expect(check.total.used).toBe(before); expect(check.valid).toBe(false);
    const w = render({ ...npcPersonaEditorStates.clean(), draft, validation: check, dirty: true, canSave: false }); expect(w.get("#npc-persona-field-offline_greeting").element.value).toBe(draft.offline_greeting); expect(w.get('[data-testid="npc-persona-editor-save"]').element.disabled).toBe(true);
  });
  it("Escape asks before discarding and declining preserves the field and focus", async () => {
    const editor = { ...npcPersonaEditorStates.clean(), dirty: true, dirtyFields: ["habit"] }; const w = render(editor); await nextTick(); const input = w.get("#npc-persona-field-habit"); input.element.focus();
    await input.trigger("keydown", { key: "Escape" }); await nextTick(); expect(w.find('[role="alertdialog"]').exists()).toBe(true);
    await w.get('[data-testid="npc-persona-editor-confirm-keep"]').trigger("keydown", { key: "Escape" }); await nextTick(); expect(w.find('[role="alertdialog"]').exists()).toBe(false); expect(document.activeElement).toBe(input.element); expect(w.emitted("close")).toBeUndefined();
    await input.trigger("keydown", { key: "Escape" }); await nextTick(); await w.get('[data-testid="npc-persona-editor-confirm-discard"]').trigger("click"); expect(w.emitted("close")).toHaveLength(1);
  });
  it("cannot promise discard while a save is already in flight", async () => {
    const w = render(npcPersonaEditorStates.saving()); await w.get('[data-testid="npc-persona-editor-cancel"]').trigger("click"); expect(w.find('[role="alertdialog"]').exists()).toBe(false); expect(w.emitted("close")).toBeUndefined(); expect(w.get('[role="status"]').text()).toContain("儲存中");
  });
  it("focuses and announces a rejected greeting while preserving plain text", async () => {
    const editor = { ...npcPersonaEditorStates.clean(), draft: { ...npcPersonaEditorStates.clean().draft, offline_greeting: "<b>草稿</b>" }, rejection: { field: "offline_greeting", message: "問候語格式無效" }, focusRequest: null };
    const w = render(editor); await w.setProps({ editor: { ...editor, focusRequest: { field: "offline_greeting", seq: 1 }, announcement: "問候語格式無效" } }); await nextTick();
    const field = w.get("#npc-persona-field-offline_greeting"); expect(document.activeElement).toBe(field.element); expect(field.element.value).toBe("<b>草稿</b>"); expect(field.attributes("aria-describedby")).toContain("-error"); expect(w.get('[data-testid="npc-persona-editor-status"]').attributes("aria-live")).toBe("polite");
  });
});

describe("editor store routing and privacy", () => {
  it("activates the bound entry once and keeps rejection out of narrative", async () => {
    setActivePinia(createPinia()); const store = useElosernStore(), sender = fx.createFakeSender(); store.setSender(sender); store.beginTransport(1); store.setConnected(true); store.receive(1, "ui_snapshot", [fx.snapshot()], {});
    const scope = effectScope(); scopes.push(scope); scope.run(() => useNpcPersonaEditor(store));
    store.openNpcPersonaEditor(sample.npc_id); await nextTick(); expect(sender.sent.actions.map(a => a.action_id)).toEqual(["npc.persona.read"]);
    const before = store.view.logEntries; store.receive(1, "ui_action_result", [fx.actionResult({ request_id: sender.sent.actions[0].request_id, outcome: "rejected", code: "npc_persona.unavailable", message: "私人錯誤", presentation_revision: 0 })], {}); await nextTick(); expect(store.view.logEntries).toEqual(before);
  });
});
