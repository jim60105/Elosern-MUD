import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";
import { mount } from "@vue/test-utils";
import CodexMedalGrid from "../../components/handbook/CodexMedalGrid.vue";
import { medalItems } from "../../components/handbook/title-codex-model.js";
import { titleCodex } from "../../stories/fixtures/title_codex_panels.js";

describe("CodexMedalGrid (handbook-titles-tab)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
    document.body.innerHTML = "";
  });

  function mountGrid(rail, selectedId = null) {
    wrapper?.unmount();
    wrapper = mount(CodexMedalGrid, {
      attachTo: document.body,
      props: { items: medalItems(titleCodex(), rail), selectedId, ariaLabel: "合成稱號" },
    });
    return wrapper;
  }

  const medal = (key) => wrapper.get(`[data-testid="handbook__medal--${key}"]`);
  const cell = (key) => wrapper.get(`[data-tile="${key}"]`);

  it("draws a grade gem for a guild row matching the grade grammar and the emblem otherwise", () => {
    mountGrid("guild");
    expect(medal("g_x_rank").find(".grade-gem").exists()).toBe(true);
    expect(medal("g_x_rank").find(".codex-emblem").exists()).toBe(false);
    mountGrid("combat");
    expect(medal("t_alpha").find(".grade-gem").exists()).toBe(false);
    expect(medal("t_alpha").find('[data-emblem="emblem_combat"]').exists()).toBe(true);
  });

  it("marks a locked medal and keeps its name", () => {
    mountGrid("combat");
    expect(medal("t_beta").attributes("data-locked")).toBe("true");
    expect(medal("t_beta").text()).toContain("乙稱號");
    expect(medal("t_alpha").attributes("data-locked")).toBe("false");
    expect(cell("t_beta").attributes("aria-label")).toBe("乙稱號，未取得");
  });

  it("badges the equipped medal", () => {
    mountGrid("combat");
    expect(medal("t_alpha").find(".codex-medal__eq").exists()).toBe(true);
    expect(medal("t_beta").find(".codex-medal__eq").exists()).toBe(false);
  });

  it("walks medals by keyboard without selecting, and selects on Enter", async () => {
    mountGrid("combat", "t_alpha");
    cell("t_alpha").element.focus();
    cell("t_alpha").element.dispatchEvent(new KeyboardEvent("keydown", { key: "End", bubbles: true }));
    await nextTick();
    await nextTick();
    expect(document.activeElement).toBe(cell("t_gamma").element);
    expect(wrapper.emitted("select")).toBeUndefined();
    cell("t_gamma").element.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    expect(wrapper.emitted("select")).toEqual([["t_gamma"]]);
  });
});
