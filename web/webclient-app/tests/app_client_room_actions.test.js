// exploration-room-actions: the AppClient composition contract for the room
// actions — the place card's 查看房間 and 等待, the wait card and its
// 進入夢境協作？ question, the 建議 pill and the suggestions card, focus return,
// the readout feed, and the focus home (webclient-room-actions,
// webclient-exploration-menu, webclient-context-actions-suggestions).
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../AppClient.vue";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";

// A ready envelope with one card of each kind (and a hint), as the validator
// commits it.
const READY = {
  status: "ready",
  cards: [
    { kind: "known_action", action_code: "explore.look", label: "看看木箱", params: { target_id: 3 }, hint: null },
    {
      kind: "known_action",
      action_code: "explore.wait",
      label: "等到黃昏",
      params: { daypart: "dusk" },
      hint: "先休息一會兒再行動",
    },
    { kind: "freeform", action_code: "explore.talk_freeform", label: "我們聊聊好嗎？", params: { npc_id: 7 }, hint: null },
    { kind: "known_action", action_code: "explore.look", label: "環顧四周", params: { room: true }, hint: null },
  ],
};

// The envelope the retired OptionCard emitted for each card kind (its
// `activate` intent, recorded before it was deleted): a known_action card
// carries its params unchanged; a freeform card is `explore.talk_freeform`
// whose speech is its label.
const FORMER_OPTION_CARD_INTENTS = [
  { action_id: "explore.look", payload: { target_id: 3 } },
  { action_id: "explore.wait", payload: { daypart: "dusk" } },
  { action_id: "explore.talk_freeform", payload: { npc_id: 7, speech: "我們聊聊好嗎？" } },
  { action_id: "explore.look", payload: { room: true } },
];

describe("AppClient room actions (exploration-room-actions)", () => {
  let store;
  let wrapper;
  let sender;
  let revision;

  async function settle() {
    for (let i = 0; i < 4; i += 1) {
      await nextTick();
    }
  }

  async function mountWith({ suggestions = undefined, mode = "exploration" } = {}) {
    wrapper = mount(AppClient, { attachTo: document.body });
    store.beginTransport(1);
    store.setConnected(true);
    store.setLoggedIn(true);
    revision = 1;
    const result = store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          revision,
          mode,
          panels: {
            status: fx.statusPanel(),
            exploration: fx.explorationPanel(),
            local_map: fx.localMapPanel(),
            context_actions: fx.explorationActions(suggestions ? { suggestions } : undefined),
          },
        }),
      ],
      {},
    );
    expect(result.accepted).toBe(true);
    await settle();
  }

  async function commit(panels, extra = {}) {
    revision += 1;
    const result = store.receive(1, "ui_update", [fx.update({ revision, panels, ...extra })], {});
    expect(result.accepted).toBe(true);
    await settle();
  }

  async function suggestionsCommit(suggestions) {
    await commit({ context_actions: fx.explorationActions({ suggestions }) });
  }

  const lookButton = () => wrapper.find('[data-anchor="map"] [data-testid="place-card-look"]');
  const waitButton = () => wrapper.find('[data-anchor="map"] [data-testid="place-card-wait"]');
  const pill = () => wrapper.find('#action-dock [data-testid="suggestions-pill"]');
  const waitCard = () => wrapper.find('[data-anchor="choices"] [data-testid="wait-card"]');
  const sugCard = () => wrapper.find('[data-anchor="choices"] [data-testid="suggestions-card"]');
  const question = () => wrapper.find('[data-anchor="choices"] [data-testid="dream-question"]');
  const rowsOf = (card) => card.findAll('[role="menuitem"]');
  const readout = () => ({
    lead: wrapper.get('[data-testid="exploration-readout-lead"]').text(),
    text: wrapper.get('[data-testid="exploration-readout-text"]').text(),
  });

  function key(element, name, init = {}) {
    element.dispatchEvent(new KeyboardEvent("keydown", { key: name, bubbles: true, cancelable: true, ...init }));
  }

  async function openWaitCard() {
    await waitButton().trigger("click");
    await settle();
    expect(waitCard().exists()).toBe(true);
  }

  async function openSleepQuestion() {
    await openWaitCard();
    await rowsOf(waitCard())[1].trigger("click");
    await settle();
    expect(question().exists()).toBe(true);
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  describe("the place card's buttons", () => {
    it("render beside the location and the time in exploration, and keep the heading's accessible name", async () => {
      await mountWith();
      const card = wrapper.get('[data-anchor="map"] [data-testid="place-card"]');
      expect(lookButton().attributes("aria-label")).toBe("查看房間");
      expect(waitButton().text()).toBe("等待");
      const heading = card.get('[data-testid="place-card__location"]');
      expect(heading.text()).toBe("石板廣場");
      expect(heading.attributes("title")).toBe("石板廣場");
      // The buttons sit beside the heading and the time, not inside them.
      expect(heading.element.contains(lookButton().element)).toBe(false);
      expect(lookButton().element.parentElement).toBe(card.element);
      expect(waitButton().element.previousElementSibling.getAttribute("data-testid")).toBe("place-card__time");
    });

    it("are absent in combat and while the exploration panel is unavailable", async () => {
      await mountWith();
      await commit(
        { context_actions: fx.combatActions(), local_map: fx.localMapPanel() },
        { mode: "combat" },
      );
      expect(lookButton().exists()).toBe(false);
      expect(waitButton().exists()).toBe(false);
      expect(wrapper.find('[data-testid="place-card"] button').exists()).toBe(false);

      wrapper.unmount();
      document.body.innerHTML = "";
      setActivePinia(createPinia());
      store = useElosernStore();
      store.setSender(sender);
      await mountWith();
      await commit({
        exploration: { schema_version: 4, available: false, reason: { code: "scene_lost", message: "這片區域暫時不可用。" } },
      });
      expect(lookButton().exists()).toBe(false);
      expect(waitButton().exists()).toBe(false);
      expect(pill().exists()).toBe(false);
      expect(wrapper.find('#action-dock [data-testid="exit-compass"]').exists()).toBe(false);
    });

    it("查看房間 submits exactly the room look, and nothing while a submission is locked", async () => {
      await mountWith();
      await lookButton().trigger("click");
      expect(sender.sent.actions).toHaveLength(1);
      expect(sender.sent.actions[0]).toMatchObject({ action_id: "explore.look", payload: { room: true } });
      // The first look is still in flight: a second activation sends nothing.
      await lookButton().trigger("click");
      expect(sender.sent.actions).toHaveLength(1);
    });

    it("feed the readout on hover and focus, and fall back when left", async () => {
      await mountWith();
      await waitButton().trigger("mouseenter");
      expect(readout()).toEqual({ lead: "等待", text: "讓時間流逝、休息或睡眠" });
      await waitButton().trigger("mouseleave");
      expect(readout().text).toMatch(/^出口 \d · 在場 \d$/);
      await lookButton().trigger("focus");
      expect(readout()).toEqual({ lead: "查看房間", text: "重新觀察四周" });
      await lookButton().trigger("blur");
      expect(readout().text).toMatch(/^出口/);
    });
  });

  describe("the wait card", () => {
    it("opens locally, stops the compass, and Escape returns focus to 等待", async () => {
      await mountWith();
      waitButton().element.focus();
      await openWaitCard();
      expect(sender.sent.actions).toHaveLength(0);
      expect(document.activeElement).toBe(waitCard().element);
      // The compass is not live while a card is open (a walk stops).
      expect(store.view.roomCard).toEqual({ kind: "wait" });
      expect(wrapper.findComponent({ name: "ExitCompass" }).props("active")).toBe(false);
      // The rail leaves the stage under the card.
      expect(store.view.railVisible).toBe(false);
      key(waitCard().element, "Escape");
      await settle();
      expect(waitCard().exists()).toBe(false);
      expect(document.activeElement).toBe(waitButton().element);
      expect(wrapper.findComponent({ name: "ExitCompass" }).props("active")).toBe(true);
    });

    it("✕ 返回 closes it with focus on 等待", async () => {
      await mountWith();
      await openWaitCard();
      await waitCard().get('[data-testid="choice-card-back"]').trigger("click");
      await settle();
      expect(waitCard().exists()).toBe(false);
      expect(document.activeElement).toBe(waitButton().element);
      expect(sender.sent.actions).toHaveLength(0);
    });

    it("等待直到黎明 submits the dawn wait once and closes the card", async () => {
      await mountWith();
      await openWaitCard();
      key(waitCard().element, "1");
      await settle();
      expect(sender.sent.actions).toHaveLength(1);
      expect(sender.sent.actions[0]).toMatchObject({ action_id: "explore.wait", payload: { daypart: "dawn" } });
      expect(waitCard().exists()).toBe(false);
    });

    it("休息 N 小時 opens the bounded form and submits nothing until confirmed; Escape returns to the row", async () => {
      await mountWith();
      await openWaitCard();
      await rowsOf(waitCard())[2].trigger("click");
      await settle();
      const form = wrapper.get('[data-anchor="choices"] [data-testid="exploration-rest-form"]');
      expect(sender.sent.actions).toHaveLength(0);
      key(form.element.querySelector("input"), "Escape");
      await settle();
      expect(wrapper.find('[data-testid="exploration-rest-form"]').exists()).toBe(false);
      expect(waitCard().isVisible()).toBe(true);
      expect(document.activeElement).toBe(waitCard().element);
      expect(waitCard().get('[data-active="true"]').attributes("data-row-key")).toBe("wait-rest");
    });

    it("a committed move closes the card in that commit", async () => {
      await mountWith();
      await openWaitCard();
      await commit({
        exploration: fx.explorationPanel({ look: { room: { identity: 77, display_name: "渡口", room: true } } }),
        local_map: fx.localMapPanel(),
      });
      expect(store.view.roomCard).toBeNull();
      expect(waitCard().exists()).toBe(false);
    });

    it("a mode change closes the card in that commit", async () => {
      await mountWith();
      await openWaitCard();
      await commit({ context_actions: fx.combatActions(), local_map: fx.localMapPanel() }, { mode: "combat" });
      expect(store.view.roomCard).toBeNull();
      expect(waitCard().exists()).toBe(false);
    });
  });

  describe("the 進入夢境協作？ question", () => {
    it("opens without a request when 睡眠至完全恢復 is chosen, focus on 是", async () => {
      await mountWith();
      await openSleepQuestion();
      expect(sender.sent.actions).toHaveLength(0);
      expect(question().get('[data-testid="question-card-question"]').text()).toBe("進入夢境協作？");
      expect(document.activeElement).toBe(question().get('[data-testid="question-card-yes"]').element);
      // No separate dream row on the card.
      expect(rowsOf(waitCard()).map((row) => row.text())).not.toContain("睡眠並進入夢境協作");
    });

    it("是 sleeps into the dream: one explore.wait with sleep and dream", async () => {
      await mountWith();
      await openSleepQuestion();
      await question().get('[data-testid="question-card-yes"]').trigger("click");
      await settle();
      expect(sender.sent.actions).toHaveLength(1);
      expect(sender.sent.actions[0]).toMatchObject({ action_id: "explore.wait", payload: { sleep: true, dream: true } });
      expect(question().exists()).toBe(false);
      expect(waitCard().exists()).toBe(false);
    });

    it("否 is a plain sleep: one explore.wait with sleep only", async () => {
      await mountWith();
      await openSleepQuestion();
      await question().get('[data-testid="question-card-no"]').trigger("click");
      await settle();
      expect(sender.sent.actions).toHaveLength(1);
      expect(sender.sent.actions[0].payload).toEqual({ sleep: true });
    });

    it("the close control and Escape cancel the sleep and return to the sleep row", async () => {
      await mountWith();
      await openSleepQuestion();
      await question().get('[data-testid="question-card-close"]').trigger("click");
      await settle();
      expect(question().exists()).toBe(false);
      expect(document.activeElement).toBe(waitCard().element);
      expect(waitCard().get('[data-active="true"]').attributes("data-row-key")).toBe("wait-sleep");

      key(waitCard().element, "Enter");
      await settle();
      expect(question().exists()).toBe(true);
      key(question().element, "Escape");
      await settle();
      expect(question().exists()).toBe(false);
      expect(document.activeElement).toBe(waitCard().element);
      expect(sender.sent.actions).toHaveLength(0);
    });

    it("traps focus and honours the lock with the wait rows' reason", async () => {
      await mountWith();
      await openSleepQuestion();
      const yes = question().get('[data-testid="question-card-yes"]').element;
      const no = question().get('[data-testid="question-card-no"]').element;
      const close = question().get('[data-testid="question-card-close"]').element;
      key(yes, "Tab");
      expect(document.activeElement).toBe(no);
      key(no, "Tab");
      expect(document.activeElement).toBe(close);
      key(close, "Tab");
      expect(document.activeElement).toBe(yes);
      // Another action goes in flight while the question is open.
      store.dispatchAction("explore.look", { room: true });
      await settle();
      expect(question().get('[data-testid="question-card-yes"]').attributes("disabled")).toBeDefined();
      expect(question().get('[data-testid="question-card-no"]').attributes("disabled")).toBeDefined();
      expect(question().get('[data-testid="question-card-reason"]').text()).toContain("上一個行動尚未完成");
      await question().get('[data-testid="question-card-yes"]').trigger("click");
      expect(sender.sent.actions).toHaveLength(1);
      expect(question().element.contains(document.activeElement)).toBe(true);
    });

    it("re-resolves the sleep row at activation: a vanished panel sends nothing", async () => {
      await mountWith();
      await openSleepQuestion();
      expect(store.activateWaitRow("wait-sleep", { dream: true })).toMatchObject({ sent: true });
      // A second answer once the card is gone resolves nothing.
      expect(store.activateWaitRow("wait-sleep", { dream: true })).toMatchObject({ sent: false, reason: "missing" });
      expect(sender.sent.actions).toHaveLength(1);
    });
  });

  describe("the 建議 pill and the suggestions card", () => {
    it("labels the pill by status: 建議 while generating, 建議 N when ready, absent when unavailable", async () => {
      await mountWith();
      expect(pill().text()).toBe("建議");
      expect(pill().attributes("aria-label")).toBe("建議");
      await suggestionsCommit(READY);
      expect(pill().text()).toBe("建議 4");
      expect(pill().attributes("aria-label")).toBe("建議 4");
      await suggestionsCommit({ status: "degraded", cards: [] });
      expect(pill().text()).toBe("建議");
      await suggestionsCommit({ status: "unavailable" });
      expect(pill().exists()).toBe(false);
    });

    it("opens the card locally and Escape returns focus to the pill", async () => {
      await mountWith({ suggestions: READY });
      pill().element.focus();
      await pill().trigger("click");
      await settle();
      expect(sender.sent.actions).toHaveLength(0);
      expect(sugCard().exists()).toBe(true);
      key(sugCard().element, "Escape");
      await settle();
      expect(sugCard().exists()).toBe(false);
      expect(document.activeElement).toBe(pill().element);
    });

    it("the generating card shows the muted state and no card row", async () => {
      await mountWith();
      await pill().trigger("click");
      await settle();
      expect(sugCard().get('[data-testid="choice-card-note"]').text()).toBe("AI 正在構思建議…");
      expect(sugCard().findAll('[data-testid="suggestions-card-row"]')).toHaveLength(0);
      expect(sugCard().find('[data-testid="suggestions-card-dismiss"]').exists()).toBe(false);
      expect(sugCard().find('[data-testid="choice-card-back"]').exists()).toBe(true);
    });

    it("ready replaces the muted state in place with rows carrying label and hint, then 清除建議 above ✕ 返回", async () => {
      await mountWith();
      await pill().trigger("click");
      await settle();
      const cardEl = sugCard().element;
      await suggestionsCommit(READY);
      expect(sugCard().element).toBe(cardEl);
      expect(sugCard().find('[data-testid="choice-card-note"]').exists()).toBe(false);
      const rows = rowsOf(sugCard());
      expect(rows.map((row) => row.attributes("data-testid"))).toEqual([
        "suggestions-card-row",
        "suggestions-card-row",
        "suggestions-card-row",
        "suggestions-card-row",
        "suggestions-card-dismiss",
        "choice-card-back",
      ]);
      expect(rows[1].get('[data-testid="choice-card-hint"]').text()).toBe("先休息一會兒再行動");
      expect(rows[0].find('[data-testid="choice-card-hint"]').exists()).toBe(false);
      const dismiss = rows[4];
      expect(dismiss.text()).toBe("清除建議");
      expect(dismiss.find('svg[data-icon="trash"]').exists()).toBe(true);
      expect(dismiss.text()).not.toContain("✕");
      expect(dismiss.classes()).toContain("choice-card__row--trailing");
    });

    it("degraded shows the rule cards with the muted note, or the empty line", async () => {
      await mountWith({ suggestions: { status: "degraded", cards: [READY.cards[0]] } });
      await pill().trigger("click");
      await settle();
      expect(sugCard().findAll('[data-testid="choice-card-note"]').map((n) => n.text())).toEqual(["AI 建議目前不可用"]);
      expect(sugCard().findAll('[data-testid="suggestions-card-row"]')).toHaveLength(1);
      await suggestionsCommit({ status: "degraded", cards: [] });
      expect(sugCard().findAll('[data-testid="choice-card-note"]').map((n) => n.text())).toEqual([
        "AI 建議目前不可用",
        "現在沒有什麼值得做的動作",
      ]);
      expect(sugCard().find('[data-testid="suggestions-card-dismiss"]').exists()).toBe(true);
    });

    it("each card kind dispatches the former OptionCard envelope, once, and the card closes", async () => {
      for (let index = 0; index < FORMER_OPTION_CARD_INTENTS.length; index += 1) {
        wrapper?.unmount();
        document.body.innerHTML = "";
        setActivePinia(createPinia());
        store = useElosernStore();
        sender = fx.createFakeSender();
        store.setSender(sender);
        await mountWith({ suggestions: READY });
        await pill().trigger("click");
        await settle();
        await rowsOf(sugCard())[index].trigger("click");
        await settle();
        expect(sender.sent.actions).toHaveLength(1);
        const { action_id, payload } = sender.sent.actions[0];
        expect({ action_id, payload }).toEqual(FORMER_OPTION_CARD_INTENTS[index]);
        expect(sugCard().exists()).toBe(false);
      }
    });

    it("a freeform card echoes exactly one input line", async () => {
      await mountWith({ suggestions: READY });
      const before = store.narrative.filter((line) => line.kind === "in").length;
      await pill().trigger("click");
      await settle();
      await rowsOf(sugCard())[2].trigger("click");
      const echoes = store.narrative.filter((line) => line.kind === "in").length - before;
      expect(echoes).toBe(1);
    });

    it("清除建議 dispatches options.dismiss, and nothing while locked", async () => {
      await mountWith({ suggestions: READY });
      await pill().trigger("click");
      await settle();
      store.dispatchAction("explore.look", { room: true });
      await settle();
      await sugCard().get('[data-testid="suggestions-card-dismiss"]').trigger("click");
      expect(sender.sent.actions.map((a) => a.action_id)).toEqual(["explore.look"]);
      expect(sugCard().exists()).toBe(true);
    });

    it("清除建議 sends the dismiss envelope when free", async () => {
      await mountWith({ suggestions: READY });
      await pill().trigger("click");
      await settle();
      await sugCard().get('[data-testid="suggestions-card-dismiss"]').trigger("click");
      expect(sender.sent.actions).toHaveLength(1);
      expect(sender.sent.actions[0]).toMatchObject({ action_id: "options.dismiss", payload: {} });
    });

    it("keeps the active row on a surviving card across a suggestions-only update", async () => {
      await mountWith({ suggestions: READY });
      await pill().trigger("click");
      await settle();
      key(sugCard().element, "ArrowDown");
      await settle();
      expect(sugCard().get('[data-active="true"]').text()).toContain("等到黃昏");
      // The cards reorder: the focused card survives at another index.
      await suggestionsCommit({ status: "ready", cards: [READY.cards[3], READY.cards[2], READY.cards[1]] });
      expect(sugCard().get('[data-active="true"]').text()).toContain("等到黃昏");
      // The same set again: nothing moves.
      await suggestionsCommit({ status: "ready", cards: [READY.cards[3], READY.cards[2], READY.cards[1]] });
      expect(sugCard().get('[data-active="true"]').text()).toContain("等到黃昏");
    });

    it("an unavailable envelope closes the card and drops the pill; focus falls back to the compass", async () => {
      await mountWith({ suggestions: READY });
      await pill().trigger("click");
      await settle();
      await suggestionsCommit({ status: "unavailable" });
      expect(sugCard().exists()).toBe(false);
      expect(pill().exists()).toBe(false);
      expect(document.activeElement).toBe(wrapper.get('[data-testid="exit-compass"]').element);
    });

    it("a transport reset retires the card before the first new snapshot", async () => {
      await mountWith({ suggestions: READY });
      await pill().trigger("click");
      await settle();
      store.beginTransport(2);
      await settle();
      expect(store.view.roomCard).toBeNull();
      expect(sugCard().exists()).toBe(false);
      expect(sender.sent.actions).toHaveLength(0);
    });

    it("feeds the readout while hovered", async () => {
      await mountWith({ suggestions: READY });
      await pill().trigger("mouseenter");
      expect(readout()).toEqual({ lead: "建議", text: "4 個可行的下一步" });
      await pill().trigger("mouseleave");
      expect(readout().text).toMatch(/^出口/);
    });
  });

  describe("the focus home", () => {
    it("the dock leaves the tab order at the exploration root and returns to it in combat", async () => {
      await mountWith();
      expect(wrapper.get("#action-dock").attributes("tabindex")).toBe("-1");
      await commit({ context_actions: fx.combatActions(), local_map: fx.localMapPanel() }, { mode: "combat" });
      expect(wrapper.get("#action-dock").attributes("tabindex")).toBe("0");
    });

    it("a drawer closing returns focus to the compass that opened it", async () => {
      await mountWith();
      const compass = wrapper.get('[data-testid="exit-compass"]').element;
      compass.focus();
      store.openHudDrawer("inventory");
      await settle();
      await wrapper.get('[data-testid="hud-drawer-close"]').trigger("click");
      await settle();
      expect(document.activeElement).toBe(compass);
    });

    it("the compass unmounting while focused hands focus to the dock", async () => {
      await mountWith();
      wrapper.get('[data-testid="exit-compass"]').element.focus();
      await commit({
        exploration: { schema_version: 4, available: false, reason: { code: "scene_lost", message: "這片區域暫時不可用。" } },
      });
      expect(wrapper.find('[data-testid="exit-compass"]').exists()).toBe(false);
      expect(document.activeElement).toBe(document.getElementById("action-dock"));
    });

    it("the command field's Escape re-homes focus on the compass", async () => {
      await mountWith();
      await wrapper.get('[data-testid="command-line-toggle"]').trigger("click");
      await settle();
      const input = wrapper.get("textarea#inputfield").element;
      expect(document.activeElement).toBe(input);
      key(input, "Escape");
      await settle();
      expect(document.activeElement).toBe(wrapper.get('[data-testid="exit-compass"]').element);
    });
  });
});
