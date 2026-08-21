import { mount } from "@vue/test-utils";
import { ref, nextTick } from "vue";
import { afterEach, describe, expect, it } from "vitest";
import ChoicePointBlock from "../../components/ChoicePointBlock.vue";

const READY = {
  status: "ready",
  cards: [
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
  ],
};

describe("ChoicePointBlock (B2 action-dock family)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountBlock(suggestions) {
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(
      {
        components: { ChoicePointBlock },
        setup: () => ({ suggestions: ref(suggestions) }),
        template: "<ChoicePointBlock :suggestions=\"suggestions\" />",
      },
      { attachTo: host },
    );
    return wrapper;
  }

  it("renders the generating state as one muted line", () => {
    const w = mountBlock({ status: "generating" });
    const block = w.get('[data-testid="choicepoint-block"]');
    expect(block.classes()).toContain("choicepoint-generating");
    expect(block.attributes("data-state")).toBe("generating");
    expect(w.get(".choicepoint-generating__line").text()).toBe(
      "AI 正在構思建議…",
    );
    expect(w.findAll('[data-testid="option-card"]')).toHaveLength(0);
  });

  it("replaces the generating line in place with the ready group", async () => {
    const w = mountBlock({ status: "generating" });
    const rootBefore = w.get('[data-testid="choicepoint-block"]').element;
    w.vm.suggestions = READY;
    await nextTick();
    const rootAfter = w.get('[data-testid="choicepoint-block"]').element;
    expect(rootAfter).toBe(rootBefore);
    expect(rootAfter.classList.contains("choicepoint-ready")).toBe(true);
    expect(w.findAll('[data-testid="option-card"]')).toHaveLength(2);
    expect(w.get('[data-testid="choicepoint-dismiss"]').text()).toBe(
      "✕ 清除建議",
    );
  });

  it("renders nothing for the stream-foreign statuses", () => {
    for (const suggestions of [
      null,
      { status: "degraded", cards: [] },
      { status: "unavailable" },
    ]) {
      const w = mountBlock(suggestions);
      expect(w.find('[data-testid="choicepoint-block"]').exists()).toBe(false);
      w.unmount();
      document.body.innerHTML = "";
      wrapper = null;
    }
  });

  it("emits the exact OOB action intent for a ready card", async () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(ChoicePointBlock, {
      attachTo: host,
      props: { suggestions: READY },
    });
    const cards = wrapper.findAll('[data-testid="option-card"]');
    await cards[1].trigger("click");
    expect(wrapper.emitted("action")).toHaveLength(1);
    expect(wrapper.emitted("action")[0][0]).toEqual({
      action_id: "explore.talk_freeform",
      payload: { npc_id: 9, speech: "我們聊聊好嗎？" },
    });
    await wrapper.get('[data-testid="choicepoint-dismiss"]').trigger("click");
    expect(wrapper.emitted("action")[1][0]).toEqual({
      action_id: "options.dismiss",
      payload: {},
    });
  });

  it("remains movable: a re-parented root keeps rendering and updating", async () => {
    // The narrative stream owns the block's position (C3): the block is a
    // single stateless root that newer text moves to the stream end.
    const stream = document.createElement("div");
    document.body.appendChild(stream);
    const lateText = document.createElement("p");
    stream.appendChild(lateText);
    wrapper = mount(ChoicePointBlock, {
      attachTo: stream,
      props: { suggestions: { status: "generating" } },
    });
    const initialRoot = wrapper.element;
    // A new narrative line lands after the block, then the stream moves the
    // block to its new end (native re-parent, as the stream adapter does).
    lateText.textContent = "新的敘事落在水面。";
    stream.insertBefore(initialRoot, lateText);
    expect(initialRoot.parentElement).toBe(stream);
    expect(initialRoot.nextSibling).toBe(lateText);
    // A committed ready update renders into the same, moved root.
    wrapper.setProps({ suggestions: READY });
    await nextTick();
    expect(wrapper.element).toBe(initialRoot);
    expect(initialRoot.parentElement).toBe(stream);
    expect(initialRoot.nextSibling).toBe(lateText);
    expect(initialRoot.classList.contains("choicepoint-ready")).toBe(true);
    expect(wrapper.findAll('[data-testid="option-card"]')).toHaveLength(2);
  });
});
