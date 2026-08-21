import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import ChoiceCardRow from "../../components/ChoiceCardRow.vue";

const CARDS = [
  {
    kind: "known_action",
    action_code: "explore.look",
    label: "查看房間",
    params: { room: true },
  },
  {
    kind: "freeform",
    action_code: "explore.talk_freeform",
    label: "我們聊聊好嗎？",
    params: { npc_id: 9 },
  },
];

describe("ChoiceCardRow (B2 action-dock family)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountRow(cards) {
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(ChoiceCardRow, {
      attachTo: host,
      props: { cards },
    });
    return wrapper;
  }

  it("renders the card group with the preserved a11y label", () => {
    const w = mountRow(CARDS);
    const row = w.get('[data-testid="choice-card-row"]');
    expect(row.attributes("role")).toBe("group");
    expect(row.attributes("aria-label")).toBe("建議動作");
    const cards = w.findAll('[data-testid="option-card"]');
    expect(cards).toHaveLength(2);
    expect(cards.map((card) => card.get(".option-card-label").text())).toEqual([
      "查看房間",
      "我們聊聊好嗎？",
    ]);
  });

  it("re-emits each card's exact OOB action intent untouched", async () => {
    const w = mountRow(CARDS);
    const cards = w.findAll('[data-testid="option-card"]');
    await cards[1].trigger("click");
    expect(w.emitted("action")).toHaveLength(1);
    expect(w.emitted("action")[0][0]).toEqual({
      action_id: "explore.talk_freeform",
      payload: { npc_id: 9, speech: "我們聊聊好嗎？" },
    });
    await cards[0].trigger("click");
    expect(w.emitted("action")).toHaveLength(2);
    expect(w.emitted("action")[1][0]).toEqual({
      action_id: "explore.look",
      payload: { room: true },
    });
  });
});
