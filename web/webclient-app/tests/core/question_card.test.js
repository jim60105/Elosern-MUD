// QuestionCard's initial focus (webclient-combat-cross-side-confirm D3):
// `initialFocus="no"` puts focus on 否 at mount and again when a lock
// releases; the default still focuses 是, and the room cards' question keeps
// both answers disabled while locked. `noWhileLocked` keeps 否 answering.
import { afterEach, describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import QuestionCard from "../../components/QuestionCard.vue";

let wrapper = null;

afterEach(() => {
  wrapper?.unmount();
  wrapper = null;
});

function mountCard(props) {
  wrapper = mount(QuestionCard, { props: { question: "確定要對友方使用〈基本攻擊〉？", ...props }, attachTo: document.body });
  return wrapper;
}

const yes = () => wrapper.get('[data-testid="question-card-yes"]').element;
const no = () => wrapper.get('[data-testid="question-card-no"]').element;

describe("QuestionCard initial focus", () => {
  it("focuses 是 by default", async () => {
    mountCard({});
    await nextTick();
    expect(document.activeElement).toBe(yes());
  });

  it('initialFocus="no" focuses 否 on mount', async () => {
    mountCard({ initialFocus: "no" });
    await nextTick();
    expect(document.activeElement).toBe(no());
  });

  it('initialFocus="no" returns to 否 after a lock releases', async () => {
    mountCard({ initialFocus: "no", locked: true, reason: "上一個行動尚未完成，請稍候。" });
    await nextTick();
    // Both answers disabled: the card itself holds focus.
    expect(no().disabled).toBe(true);
    expect(document.activeElement).toBe(wrapper.element);
    await wrapper.setProps({ locked: false });
    await nextTick();
    await nextTick();
    expect(document.activeElement).toBe(no());
  });

  it("noWhileLocked keeps 否 working while 是 waits", async () => {
    mountCard({ initialFocus: "no", noWhileLocked: true, locked: true, reason: "上一個行動尚未完成，請稍候。" });
    await nextTick();
    expect(yes().disabled).toBe(true);
    expect(no().disabled).toBe(false);
    expect(document.activeElement).toBe(no());
    expect(wrapper.get('[data-testid="question-card-reason"]').text()).toBe("上一個行動尚未完成，請稍候。");
    await wrapper.get('[data-testid="question-card-no"]').trigger("click");
    expect(wrapper.emitted("no")).toHaveLength(1);
  });

  it("the default lock still disables both answers (the room cards' question)", async () => {
    mountCard({ locked: true, reason: "等一下" });
    await nextTick();
    expect(yes().disabled).toBe(true);
    expect(no().disabled).toBe(true);
    await wrapper.setProps({ locked: false });
    await nextTick();
    await nextTick();
    expect(document.activeElement).toBe(yes());
  });

  it("the caution tone is a labelled modal dialog with a decorative caption", async () => {
    mountCard({ tone: "caution", caption: "跨陣營施展", initialFocus: "no" });
    await nextTick();
    const root = wrapper.element;
    expect(root.getAttribute("role")).toBe("dialog");
    expect(root.getAttribute("aria-modal")).toBe("true");
    const label = document.getElementById(root.getAttribute("aria-labelledby"));
    expect(label.textContent).toBe("確定要對友方使用〈基本攻擊〉？");
    expect(root.dataset.tone).toBe("caution");
    expect(wrapper.get(".question-card__caption").attributes("aria-hidden")).toBe("true");
  });
});
