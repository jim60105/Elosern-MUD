import { afterEach, describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import CodexDetail from "../../components/handbook/CodexDetail.vue";
import { glyphPath } from "../../components/dock-icons.js";

// A synthetic detail view model; every string is a fixture.
const detailOf = (overrides = {}) => ({
  id: "d1",
  name: "detail-name",
  ribbon: "ribbon-text",
  emblem: "explore",
  grade: null,
  locked: false,
  stamp: null,
  subtitle: "subtitle-text",
  sections: [
    { label: "s1", text: "text-1" },
    { label: "s2", text: "text-2" },
  ],
  nameplate: null,
  ...overrides,
});

const FOOTER = {
  reason: "reason-text",
  reasonTone: "plain",
  reasonRole: null,
  buttons: [{ key: "go", label: "go-label", tone: "primary", testid: "footer-go" }],
};

describe("CodexDetail (handbook-primitives)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
    document.body.innerHTML = "";
  });

  function mountDetail(props, slots = {}) {
    wrapper = mount(CodexDetail, { attachTo: document.body, props, slots });
    return wrapper;
  }

  const get = (id) => wrapper.get(`[data-testid="handbook__${id}"]`);
  const find = (id) => wrapper.find(`[data-testid="handbook__${id}"]`);

  it("renders the ribbon, title, subtitle and sections in order", () => {
    mountDetail({ detail: detailOf() });
    expect(get("detail").exists()).toBe(true);
    expect(get("ribbon").text()).toBe("ribbon-text");
    expect(wrapper.get("h3").text()).toBe("detail-name");
    expect(wrapper.get(".codex-detail__subtitle").text()).toBe("subtitle-text");
    const sections = wrapper.findAll('[data-testid="handbook__section"]');
    expect(sections.map((s) => [s.get("h4").text(), s.get("p").text()])).toEqual([
      ["s1", "text-1"],
      ["s2", "text-2"],
    ]);
    expect(find("stamp").exists()).toBe(false);
    expect(wrapper.find(".codex-detail__subtitle").exists()).toBe(true);
  });

  it("omits a missing subtitle and renders the stamp with its kind", () => {
    mountDetail({ detail: detailOf({ subtitle: null, stamp: { kind: "equipped", label: "stamp-label" } }) });
    expect(wrapper.find(".codex-detail__subtitle").exists()).toBe(false);
    expect(get("stamp").attributes("data-stamp")).toBe("equipped");
    expect(get("stamp").text()).toBe("stamp-label");
  });

  it("draws the emblem in the hero medal when there is no grade", () => {
    mountDetail({ detail: detailOf() });
    const medal = wrapper.get(".codex-detail__medal");
    expect(medal.find(".grade-gem").exists()).toBe(false);
    expect(medal.get("path").attributes("d")).toBe(glyphPath("emblem_explore"));
    expect(medal.attributes("data-locked")).toBeUndefined();
  });

  it("draws the grade gem in the hero medal when a grade is set", () => {
    mountDetail({ detail: detailOf({ grade: "B" }) });
    const medal = wrapper.get(".codex-detail__medal");
    expect(medal.get(".grade-gem").attributes("data-grade")).toBe("B");
    expect(medal.find(".codex-emblem").exists()).toBe(false);
  });

  it("marks a locked entry with the silhouette ring", () => {
    mountDetail({ detail: detailOf({ locked: true }) });
    const medal = wrapper.get(".codex-detail__medal");
    expect(medal.attributes("data-locked")).toBe("true");
    expect(medal.classes()).toContain("is-locked");
  });

  it("renders the nameplate beside the medal when present", () => {
    mountDetail({ detail: detailOf({ nameplate: "plate-text" }) });
    expect(wrapper.get(".codex-detail__nameplate").text()).toBe("plate-text");
  });

  it("lets the hero slot replace the default face", () => {
    mountDetail(
      { detail: detailOf({ grade: "B" }) },
      { hero: ({ detail }) => `hero-for-${detail.id}` },
    );
    expect(wrapper.find(".codex-detail__medal").exists()).toBe(false);
    expect(wrapper.get(".codex-detail__hero").text()).toBe("hero-for-d1");
  });

  it("renders no footer when footer is null", () => {
    mountDetail({ detail: detailOf(), footer: null });
    expect(wrapper.find("footer").exists()).toBe(false);
  });

  it("re-emits a footer press and focuses footer buttons through focus(key)", async () => {
    mountDetail({ detail: detailOf(), footer: FOOTER });
    const go = wrapper.get('[data-testid="footer-go"]');
    await go.trigger("click");
    expect(wrapper.emitted("press")).toEqual([["go"]]);
    wrapper.vm.focus("go");
    expect(document.activeElement).toBe(go.element);
  });

  it("renders the empty state for a null detail", () => {
    mountDetail({ detail: null, footer: FOOTER });
    expect(get("detail-empty").classes()).toContain("codex-detail--empty");
    expect(find("detail").exists()).toBe(false);
    expect(wrapper.find("footer").exists()).toBe(false);
  });
});
