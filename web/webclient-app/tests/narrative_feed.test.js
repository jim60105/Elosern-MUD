import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { afterEach, describe, expect, it } from "vitest";
import NarrativeFeed from "../components/NarrativeFeed.vue";

// Mock the scroll geometry jsdom does not compute; `scrollTop` is backed by
// a real settable value so the component's scrollToBottom() is observable.
function mockScrollGeometry(wrapper, { scrollHeight, clientHeight, scrollTop }) {
  const el = wrapper.element;
  let value = scrollTop;
  Object.defineProperty(el, "scrollHeight", { configurable: true, value: scrollHeight });
  Object.defineProperty(el, "clientHeight", { configurable: true, value: clientHeight });
  Object.defineProperty(el, "scrollTop", {
    configurable: true,
    get: () => value,
    set: (next) => {
      value = next;
    },
  });
}

async function flush() {
  await nextTick();
  await nextTick();
}

describe("NarrativeFeed (B1 core family)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  it("renders out lines through the preserved markup allowlist pipeline", () => {
    wrapper = mount(NarrativeFeed, {
      props: {
        lines: [
          {
            kind: "out",
            text:
              "<span class=\"color-203\">石板</span> <span style=\"color: #e06b6b;\">紅</span> 廣場",
          },
        ],
      },
    });
    const line = wrapper.get(".narrative-line.out");
    const spans = line.findAll("span");
    expect(spans).toHaveLength(2);
    expect(spans[0].classes()).toContain("color-203");
    expect(spans[1].element.style.color).toBe("rgb(224, 107, 107)");
  });

  it("degrades unrecognized markup to literal text (no invented elements)", () => {
    wrapper = mount(NarrativeFeed, {
      props: { lines: [{ kind: "out", text: "前文 <div>未接受</div> 後文 <i>斜體</i>。" }] },
    });
    const line = wrapper.get(".narrative-line.out");
    expect(line.findAll("div, i")).toHaveLength(0);
    expect(line.text()).toBe("前文 <div>未接受</div> 後文 <i>斜體</i>。");
  });

  it("renders player input lines as literal .inp lines with a divider (never through the pipeline)", () => {
    wrapper = mount(NarrativeFeed, {
      props: {
        lines: [
          { kind: "out", text: "第一行。" },
          { kind: "in", text: "<b>look</b>" },
        ],
      },
    });
    const lines = wrapper.findAll(".narrative-line");
    expect(lines).toHaveLength(2);
    const inputLine = lines[1];
    expect(inputLine.classes()).toContain("inp");
    expect(inputLine.findAll("b")).toHaveLength(0);
    expect(inputLine.text()).toBe("<b>look</b>");
    expect(wrapper.get('[data-testid="narrative-divider"]')).toBeTruthy();
  });

  it("omits the divider for a first input line and tags box-drawing lines map-art", () => {
    wrapper = mount(NarrativeFeed, {
      props: {
        lines: [
          { kind: "in", text: "look" },
          { kind: "out", text: "│  北面出口  │" },
        ],
      },
    });
    expect(wrapper.findAll('[data-testid="narrative-divider"]')).toHaveLength(0);
    expect(wrapper.get(".narrative-line.map-art")).toBeTruthy();
  });

  it("counts lines into the unread marker while away from the bottom, and jumping clears it", async () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(NarrativeFeed, {
      attachTo: host,
      props: { lines: [{ kind: "out", text: "初始行。" }] },
    });
    mockScrollGeometry(wrapper, { scrollHeight: 600, clientHeight: 100, scrollTop: 0 });

    await wrapper.setProps({
      lines: [
        { kind: "out", text: "初始行。" },
        { kind: "out", text: "新敘事行。" },
      ],
    });
    await flush();

    const marker = wrapper.get('[data-testid="unread-indicator"]');
    expect(marker.attributes("data-count")).toBe("1");
    expect(wrapper.get('[data-testid="unread-indicator-button"]').text()).toBe(
      "↓ 1 則新訊息（點擊返回最新）",
    );

    await wrapper.get('[data-testid="unread-indicator-button"]').trigger("click");
    await flush();
    expect(wrapper.get('[data-testid="unread-indicator"]').attributes("data-count")).toBe("0");
    expect(wrapper.find('[data-testid="unread-indicator-button"]').exists()).toBe(false);
    expect(wrapper.element.scrollTop).toBe(600);
    expect(document.activeElement).toBe(wrapper.element);
  });

  it("auto-scrolls to the bottom when the reader is at the bottom", async () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(NarrativeFeed, {
      attachTo: host,
      props: { lines: [{ kind: "out", text: "初始行。" }] },
    });
    mockScrollGeometry(wrapper, { scrollHeight: 600, clientHeight: 100, scrollTop: 500 });

    await wrapper.setProps({
      lines: [
        { kind: "out", text: "初始行。" },
        { kind: "out", text: "新敘事行。" },
      ],
    });
    await flush();

    expect(wrapper.element.scrollTop).toBe(600);
    expect(wrapper.get('[data-testid="unread-indicator"]').attributes("data-count")).toBe("0");
  });
});
