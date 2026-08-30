// TitleBallotMenu (title-epithet-nomination): the epithet nomination ballot
// surface over the committed `title_ballot` v1 panel. One candidate card
// renders the numbered 「index. display」 with its basis quote and its own
// 接受 N button; only candidates that are present get buttons; 放棄 emits the
// exact empty `title.decline` payload; the idle (zero-candidate),
// unavailable, and absent panel forms render nothing at all.
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import TitleBallotMenu from "../../components/TitleBallotMenu.vue";

function candidate(index, overrides = {}) {
  return {
    index,
    display: `異名${index}`,
    basis: `第${index}條事蹟引用。`,
    ...overrides,
  };
}

function panel(candidates) {
  return {
    schema_version: 1,
    available: true,
    kind: "title_ballot",
    candidates,
  };
}

describe("TitleBallotMenu (title-epithet-nomination)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  function mountMenu(ballot) {
    wrapper = mount(TitleBallotMenu, { props: { ballot } });
    return wrapper;
  }

  for (const count of [1, 2, 3]) {
    it(`renders ${count} candidate card(s) with numbered choice and basis quote`, () => {
      const candidates = Array.from({ length: count }, (_, i) => candidate(i + 1));
      const w = mountMenu(panel(candidates));
      expect(w.find('[data-testid="title-ballot-menu"]').exists()).toBe(true);
      for (const entry of candidates) {
        const card = w.get(`[data-testid="title-ballot-menu__candidate--${entry.index}"]`);
        expect(card.text()).toContain(`${entry.index}. ${entry.display}`);
        expect(card.get('[data-testid="title-ballot-menu__basis"]').text()).toBe(
          `「${entry.basis}」`,
        );
      }
      // Absent candidates carry no buttons at all.
      for (let index = count + 1; index <= 3; index += 1) {
        expect(w.find(`[data-testid="title-ballot-menu__accept--${index}"]`).exists()).toBe(
          false,
        );
      }
      expect(w.findAll(".title-ballot__accept")).toHaveLength(count);
    });
  }
  it("clicking 接受 N emits the exact numbered title.accept intent", async () => {
    const w = mountMenu(
      panel([candidate(1), candidate(2), candidate(3)]),
    );
    await w.get('[data-testid="title-ballot-menu__accept--2"]').trigger("click");
    expect(w.emitted("accept")).toEqual([
      [{ action_id: "title.accept", payload: { index: 2 } }],
    ]);
    expect(w.emitted("decline")).toBeUndefined();
  });

  it("every accept button carries its own candidate index", async () => {
    const w = mountMenu(panel([candidate(1), candidate(2)]));
    await w.get('[data-testid="title-ballot-menu__accept--1"]').trigger("click");
    await w.get('[data-testid="title-ballot-menu__accept--2"]').trigger("click");
    expect(w.emitted("accept")).toEqual([
      [{ action_id: "title.accept", payload: { index: 1 } }],
      [{ action_id: "title.accept", payload: { index: 2 } }],
    ]);
  });

  it("clicking 放棄 emits the exact empty title.decline intent", async () => {
    const w = mountMenu(panel([candidate(1)]));
    await w.get('[data-testid="title-ballot-menu__decline"]').trigger("click");
    expect(w.emitted("decline")).toEqual([
      [{ action_id: "title.decline", payload: {} }],
    ]);
  });

  it("the long-form basis renders verbatim (the panel never truncates)", () => {
    const basis = "援".repeat(80);
    const w = mountMenu(panel([candidate(1, { basis })]));
    expect(w.get('[data-testid="title-ballot-menu__basis"]').text()).toBe(
      `「${basis}」`,
    );
  });

  it("the idle zero-candidate form renders nothing", () => {
    const w = mountMenu(panel([]));
    expect(w.find('[data-testid="title-ballot-menu"]').exists()).toBe(false);
    expect(w.html()).toContain("<!--v-if-->");
  });

  it("the unavailable form and an absent panel render nothing", () => {
    const w = mountMenu({
      schema_version: 1,
      available: false,
      reason: { code: "ballot_unavailable", message: "異名提名目前無法顯示" },
    });
    expect(w.find('[data-testid="title-ballot-menu"]').exists()).toBe(false);
    w.setProps({ ballot: null });
    expect(w.find('[data-testid="title-ballot-menu"]').exists()).toBe(false);
  });

  it("a malformed candidate list renders nothing (host, not data source)", () => {
    const w = mountMenu({
      schema_version: 1,
      available: true,
      kind: "title_ballot",
      candidates: null,
    });
    expect(w.find('[data-testid="title-ballot-menu"]').exists()).toBe(false);
  });
});
