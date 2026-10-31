// exploration-room-actions; redesign-rest-entry: the AppClient composition
// contract for the room actions — the place card's 查看房間 and 休息, the
// two-layer rest entry (the TimeChoiceCard tiles, then the shared shell
// around the wait or sleep form), the 建議 pill and the suggestions card,
// focus return, the readout feed, and the focus home (webclient-room-actions,
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

  async function mountWith({ suggestions = undefined, mode = "exploration", status = fx.statusPanel() } = {}) {
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
            status,
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
  const tile = (key) => wrapper.find(`[data-anchor="choices"] [data-testid="wait-card-tile"][data-tile="${key}"]`);
  const waitShell = () => wrapper.find('[data-anchor="choices"] [data-testid="wait-form-card"]');
  const sleepShell = () => wrapper.find('[data-anchor="choices"] [data-testid="sleep-card"]');
  const shellInput = (shell) => shell.element.querySelector('input[type="number"]');
  const sugCard = () => wrapper.find('[data-anchor="choices"] [data-testid="suggestions-card"]');
  const rowsOf = (card) => card.findAll('[role="menuitem"]');
  const readout = () => ({
    lead: wrapper.get('[data-testid="exploration-readout-lead"]').text(),
    text: wrapper.get('[data-testid="exploration-readout-text"]').text(),
  });

  function key(element, name, init = {}) {
    const event = new KeyboardEvent("keydown", { key: name, bubbles: true, cancelable: true, ...init });
    element.dispatchEvent(event);
    return event;
  }

  async function openWaitCard() {
    await waitButton().trigger("click");
    await settle();
    expect(waitCard().exists()).toBe(true);
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
      expect(waitButton().text()).toBe("休息");
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
        exploration: { schema_version: 6, available: false, reason: { code: "scene_lost", message: "這片區域暫時不可用。" } },
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
      expect(readout()).toEqual({ lead: "休息", text: "保持清醒等待，或入睡恢復精力" });
      await waitButton().trigger("mouseleave");
      expect(readout().text).toMatch(/^出口 \d · 在場 \d$/);
      await lookButton().trigger("focus");
      expect(readout()).toEqual({ lead: "查看房間", text: "重新觀察四周" });
      await lookButton().trigger("blur");
      expect(readout().text).toMatch(/^出口/);
    });
  });

  describe("the rest entry's first layer", () => {
    it("opens locally on the 等待 tile, stops the compass, and Escape returns focus to 休息", async () => {
      await mountWith();
      waitButton().element.focus();
      await openWaitCard();
      expect(sender.sent.actions).toHaveLength(0);
      expect(document.activeElement).toBe(tile("wait").element);
      // The compass is not live while a card is open (a walk stops).
      expect(store.view.roomCard).toEqual({ kind: "wait" });
      expect(wrapper.findComponent({ name: "ExitCompass" }).props("active")).toBe(false);
      // The rail leaves the stage under the card.
      expect(store.view.railVisible).toBe(false);
      key(tile("wait").element, "Escape");
      await settle();
      expect(waitCard().exists()).toBe(false);
      expect(document.activeElement).toBe(waitButton().element);
      expect(wrapper.findComponent({ name: "ExitCompass" }).props("active")).toBe(true);
      expect(sender.sent.actions).toHaveLength(0);
    });

    it("its ✕ closes the entry with focus on 休息", async () => {
      await mountWith();
      await openWaitCard();
      await waitCard().get('[data-testid="wait-card-close"]').trigger("click");
      await settle();
      expect(waitCard().exists()).toBe(false);
      expect(document.activeElement).toBe(waitButton().element);
      expect(sender.sent.actions).toHaveLength(0);
    });

    it("1 opens the wait form and Enter on the 睡眠 tile the sleep form, each with its input focused", async () => {
      await mountWith();
      await openWaitCard();
      key(tile("wait").element, "1");
      await settle();
      expect(waitCard().exists()).toBe(false);
      expect(waitShell().exists()).toBe(true);
      expect(document.activeElement).toBe(shellInput(waitShell()));
      expect(sender.sent.actions).toHaveLength(0);
      await waitShell().get('[data-testid="rest-step-back"]').trigger("click");
      await settle();
      tile("sleep").element.focus();
      // Enter on a focused button activates it natively (a click).
      key(tile("sleep").element, "Enter");
      await tile("sleep").trigger("click");
      await settle();
      expect(sleepShell().exists()).toBe(true);
      expect(document.activeElement).toBe(shellInput(sleepShell()));
      expect(sender.sent.actions).toHaveLength(0);
    });

    it("shows 現在 HH:MM and the controlled body's 精力 line from the committed panels", async () => {
      await mountWith();
      await openWaitCard();
      expect(tile("wait").get('[data-testid="wait-card-tile-context"]').text()).toBe("現在 12:00");
      expect(tile("sleep").get('[data-testid="wait-card-tile-context"]').text()).toBe("精力 80%（精神充沛）");
    });

    it("reads the controlled body's row under possession", async () => {
      const status = fx.statusPanel();
      status.actor = { ...status.actor, name: "隨從", identity: "99" };
      status.fatigue = [
        { ...status.fatigue[0] },
        {
          identity: "99",
          name: "隨從",
          reserve_percent: 35,
          stage: "moderate",
          label: "中度疲勞",
          severity: "warning",
          restriction: null,
          asleep: false,
        },
      ];
      await mountWith({ status });
      await openWaitCard();
      expect(tile("sleep").get('[data-testid="wait-card-tile-context"]').text()).toBe("精力 35%（中度疲勞）");
    });

    it("a status panel without a fatigue row for the controlled body hides only the 睡眠 tile's context line", async () => {
      // The validator requires at least the status source's own row, so the
      // absent source is a panel whose rows do not name the controlled body.
      const status = fx.statusPanel();
      status.actor = { ...status.actor, identity: "99" };
      await mountWith({ status });
      await openWaitCard();
      expect(tile("sleep").find('[data-testid="wait-card-tile-context"]').exists()).toBe(false);
      expect(tile("sleep").get(".time-choice__hint").text()).toBe("入睡，恢復精力");
      expect(tile("wait").get('[data-testid="wait-card-tile-context"]').text()).toBe("現在 12:00");
    });

    it("a committed move closes it in that commit", async () => {
      await mountWith();
      await openWaitCard();
      await commit({
        exploration: fx.explorationPanel({ look: { room: { identity: 77, display_name: "渡口", room: true } } }),
        local_map: fx.localMapPanel(),
      });
      expect(store.view.roomCard).toBeNull();
      expect(waitCard().exists()).toBe(false);
    });

    it("a mode change closes it in that commit", async () => {
      await mountWith();
      await openWaitCard();
      await commit({ context_actions: fx.combatActions(), local_map: fx.localMapPanel() }, { mode: "combat" });
      expect(store.view.roomCard).toBeNull();
      expect(waitCard().exists()).toBe(false);
    });

    it("renders no wait row or rest card at any layer, and the view carries no wait-row list", async () => {
      await mountWith();
      await openWaitCard();
      const retired = () =>
        wrapper.findAll('[data-testid="wait-card-row"], [data-testid="rest-card"], .rest-card').length;
      expect(retired()).toBe(0);
      expect(waitCard().findAll('[role="menuitem"]')).toHaveLength(0);
      key(tile("wait").element, "1");
      await settle();
      expect(retired()).toBe(0);
      await waitShell().get('[data-testid="rest-step-back"]').trigger("click");
      await settle();
      key(tile("wait").element, "2");
      await settle();
      expect(sleepShell().exists()).toBe(true);
      expect(retired()).toBe(0);
      expect(store.view.waitRows).toBeUndefined();
    });
  });

  describe("the rest entry's second layer", () => {
    async function openStep(which) {
      await openWaitCard();
      key(tile("wait").element, which === "wait" ? "1" : "2");
      await settle();
      const shell = which === "wait" ? waitShell() : sleepShell();
      expect(shell.exists()).toBe(true);
      return shell;
    }

    it("captions each shell with its mode and labels the dialog by it", async () => {
      await mountWith();
      const wait = await openStep("wait");
      expect(wait.attributes("role")).toBe("dialog");
      expect(wait.attributes("aria-modal")).toBe("true");
      const caption = document.getElementById(wait.attributes("aria-labelledby"));
      expect(caption.textContent).toBe("等待");
      expect(caption.getAttribute("aria-hidden")).toBeNull();
      expect(wait.find('[data-testid="wait-form"]').exists()).toBe(true);
      expect(wait.get('[data-testid="wait-form-dawn"]').text()).toBe("等待直到黎明");
      expect(wait.get('[data-testid="rest-step-back"]').attributes("aria-label")).toBe("返回上一層");
      expect(wait.get('[data-testid="rest-step-back"]').attributes("title")).toBe("返回上一層");
      expect(wait.get('[data-testid="rest-step-close"]').attributes("aria-label")).toBe("關閉並回到探索");
      expect(wait.get('[data-testid="rest-step-close"]').attributes("title")).toBe("關閉");
      await wait.get('[data-testid="rest-step-back"]').trigger("click");
      await settle();
      const sleep = await openStep("sleep");
      expect(document.getElementById(sleep.attributes("aria-labelledby")).textContent).toBe("睡眠");
      expect(sleep.find('[data-testid="sleep-form"]').exists()).toBe(true);
      expect(sleep.text()).not.toContain("睡眠模式");
      expect(sleep.classes()).toContain("rest-step");
    });

    for (const which of ["wait", "sleep"]) {
      it(`‹ and Escape in the ${which} form step back to the ${which} tile without dispatching`, async () => {
        await mountWith();
        const shell = await openStep(which);
        await shell.get('[data-testid="rest-step-back"]').trigger("click");
        await settle();
        expect(waitCard().exists()).toBe(true);
        expect(document.activeElement).toBe(tile(which).element);
        await openStep(which);
        key(shellInput(which === "wait" ? waitShell() : sleepShell()), "Escape");
        await settle();
        expect(waitCard().exists()).toBe(true);
        expect(document.activeElement).toBe(tile(which).element);
        expect(sender.sent.actions).toHaveLength(0);
      });
    }

    it("Escape on ‹ steps back too", async () => {
      await mountWith();
      const shell = await openStep("sleep");
      const back = shell.get('[data-testid="rest-step-back"]').element;
      back.focus();
      key(back, "Escape");
      await settle();
      expect(waitCard().exists()).toBe(true);
      expect(document.activeElement).toBe(tile("sleep").element);
    });

    it("its ✕ closes everything with focus on 休息", async () => {
      await mountWith();
      const shell = await openStep("wait");
      await shell.get('[data-testid="rest-step-close"]').trigger("click");
      await settle();
      expect(store.view.roomCard).toBeNull();
      expect(waitCard().exists()).toBe(false);
      expect(waitShell().exists()).toBe(false);
      expect(document.activeElement).toBe(waitButton().element);
      expect(sender.sent.actions).toHaveLength(0);
    });

    it("the four options send exactly their existing payloads and close the entry", async () => {
      const cases = [
        ["wait", async (shell) => shell.get('[data-testid="wait-form-dawn"]').trigger("click"), { daypart: "dawn" }],
        [
          "wait",
          async (shell) => {
            await shell.get("input").setValue("1.5");
            await shell.get("form").trigger("submit");
          },
          { seconds: 5400 },
        ],
        ["sleep", async (shell) => shell.get('[data-testid="sleep-form-recovery"]').trigger("click"), { sleep: true }],
        [
          "sleep",
          async (shell) => {
            await shell.get("input").setValue("2");
            await shell.get("form").trigger("submit");
          },
          { sleep: true, sleep_mode: "duration", seconds: 7200 },
        ],
      ];
      for (const [which, act, payload] of cases) {
        wrapper?.unmount();
        document.body.innerHTML = "";
        setActivePinia(createPinia());
        store = useElosernStore();
        sender = fx.createFakeSender();
        store.setSender(sender);
        await mountWith();
        const shell = await openStep(which);
        await act(shell);
        await settle();
        expect(sender.sent.actions).toHaveLength(1);
        expect(sender.sent.actions[0].action_id).toBe("explore.wait");
        expect(sender.sent.actions[0].payload).toEqual(payload);
        expect(store.view.roomCard).toBeNull();
        expect(waitShell().exists() || sleepShell().exists()).toBe(false);
      }
    });

    it("an out-of-bounds duration errors without dispatching", async () => {
      await mountWith();
      const shell = await openStep("sleep");
      await shell.get("input").setValue("0");
      await shell.get("form").trigger("submit");
      await settle();
      expect(sender.sent.actions).toHaveLength(0);
      expect(sleepShell().get('[role="alert"]').text()).toContain("請輸入有效時長");
      expect(sleepShell().exists()).toBe(true);
    });

    it("traps Tab across the form controls and the two corner buttons", async () => {
      await mountWith();
      const shell = await openStep("wait");
      const input = shellInput(shell);
      const close = shell.get('[data-testid="rest-step-close"]').element;
      const dawn = shell.get('[data-testid="wait-form-dawn"]').element;
      expect(document.activeElement).toBe(input);
      // Shift+Tab from the input (not the first control) stays native here;
      // from the first control it wraps to the ✕.
      dawn.focus();
      const back = key(dawn, "Tab", { shiftKey: true });
      expect(back.defaultPrevented).toBe(true);
      expect(document.activeElement).toBe(close);
      // Tab from the ✕ (the last control) wraps to the form's first control.
      const forward = key(close, "Tab");
      expect(forward.defaultPrevented).toBe(true);
      expect(document.activeElement).toBe(dawn);
      // A Tab between inner controls is left to the browser.
      const inner = key(input, "Tab");
      expect(inner.defaultPrevented).toBe(false);
      // The DOM order walks the form first, then ‹, then ✕.
      const order = Array.from(shell.element.querySelectorAll("button, input")).map(
        (el) => el.getAttribute("data-testid") || el.getAttribute("type"),
      );
      expect(order).toEqual(["wait-form-dawn", "number", "submit", "rest-step-back", "rest-step-close"]);
    });

    it("stepping back does not replay the tiles' entrance", async () => {
      await mountWith();
      await openWaitCard();
      expect(waitCard().classes()).not.toContain("choice-card--still");
      key(tile("wait").element, "1");
      await settle();
      await waitShell().get('[data-testid="rest-step-back"]').trigger("click");
      await settle();
      expect(waitCard().classes()).toContain("choice-card--still");
    });

    it("a committed move and a mode change close the entry while a form is shown", async () => {
      await mountWith();
      await openStep("wait");
      await commit({
        exploration: fx.explorationPanel({ look: { room: { identity: 77, display_name: "渡口", room: true } } }),
        local_map: fx.localMapPanel(),
      });
      expect(store.view.roomCard).toBeNull();
      expect(waitShell().exists()).toBe(false);
      await openStep("sleep");
      await commit({ context_actions: fx.combatActions(), local_map: fx.localMapPanel() }, { mode: "combat" });
      expect(store.view.roomCard).toBeNull();
      expect(sleepShell().exists()).toBe(false);
    });

    it("a lock engaging on the focused form control moves focus to ‹", async () => {
      await mountWith();
      const shell = await openStep("sleep");
      expect(document.activeElement).toBe(shellInput(shell));
      expect(store.activateRoomLook()).toMatchObject({ sent: true });
      await settle();
      expect(shellInput(sleepShell()).disabled).toBe(true);
      expect(document.activeElement).toBe(sleepShell().get('[data-testid="rest-step-back"]').element);
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
        exploration: { schema_version: 6, available: false, reason: { code: "scene_lost", message: "這片區域暫時不可用。" } },
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
