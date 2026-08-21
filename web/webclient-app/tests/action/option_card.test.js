import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import OptionCard from "../../components/OptionCard.vue";

const KNOWN_CARD = {
  kind: "known_action",
  action_code: "explore.look",
  label: "查看房間",
  params: { room: true },
};

const KNOWN_CARD_WITH_HINT = {
  kind: "known_action",
  action_code: "explore.wait",
  label: "等到黃昏",
  params: { daypart: "dusk" },
  hint: "先休息一會兒再行動",
};

const FREEFORM_CARD = {
  kind: "freeform",
  action_code: "explore.talk_freeform",
  label: "我們聊聊好嗎？",
  params: { npc_id: 9 },
  hint: "說任何想說的話",
};

describe("OptionCard (B2 action-dock family)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountCard(card) {
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(OptionCard, {
      attachTo: host,
      props: { card },
    });
    return wrapper;
  }

  it("renders the exact server-authored shape as text nodes", () => {
    const w = mountCard(KNOWN_CARD_WITH_HINT);
    const card = w.get('[data-testid="option-card"]');
    expect(card.classes()).toContain("option-card-known");
    expect(card.get(".option-card-label").text()).toBe("等到黃昏");
    expect(card.get(".option-card-hint").text()).toBe("先休息一會兒再行動");
    // No card content ever enters a markup pipeline: the label cell is a
    // bare text node even for markup-shaped labels.
    const markup = mountCard({
      ...KNOWN_CARD,
      label: "<span class=\"color-033\">看似標記</span>",
    });
    const labelCell = markup.get(".option-card-label");
    expect(labelCell.text()).toBe("<span class=\"color-033\">看似標記</span>");
    expect(labelCell.element.childNodes).toHaveLength(1);
    expect(labelCell.element.childNodes[0].nodeType).toBe(3);
    expect(labelCell.element.querySelector("span")).toBeNull();
    markup.unmount();
    document.body.innerHTML = "";
  });

  it("omits the hint cell when the server hint is absent", () => {
    const w = mountCard(KNOWN_CARD);
    expect(w.find(".option-card-hint").exists()).toBe(false);
  });

  it("activates a known_action card with its exact OOB intent", async () => {
    const w = mountCard(KNOWN_CARD);
    await w.get('[data-testid="option-card"]').trigger("click");
    expect(w.emitted("action")).toHaveLength(1);
    expect(w.emitted("action")[0][0]).toEqual({
      action_id: "explore.look",
      payload: { room: true },
    });
  });

  it("does not alias the server params into the emitted payload", async () => {
    const card = {
      kind: "known_action",
      action_code: "explore.talk_scripted",
      label: "與灰婆婆交談",
      params: { npc_id: 7, keyword_id: "問候" },
    };
    const w = mountCard(card);
    await w.get('[data-testid="option-card"]').trigger("click");
    const payload = w.emitted("action")[0][0].payload;
    payload.npc_id = 8;
    expect(card.params.npc_id).toBe(7);
  });

  it("activates a freeform card as explore.talk_freeform with the label as speech", async () => {
    const w = mountCard(FREEFORM_CARD);
    expect(w.get('[data-testid="option-card"]').classes()).toContain(
      "option-card-freeform",
    );
    await w.get('[data-testid="option-card"]').trigger("click");
    expect(w.emitted("action")[0][0]).toEqual({
      action_id: "explore.talk_freeform",
      payload: { npc_id: 9, speech: "我們聊聊好嗎？" },
    });
  });
});
