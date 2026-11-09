import { afterEach, describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import CodexDetail from "../../components/handbook/CodexDetail.vue";
import { glyphPath } from "../../components/dock-icons.js";
import { codexDetail, MONSTER_CATEGORY } from "../../components/handbook/lore-codex-model.js";
import { codexCategory, codexEntry, loreCodex } from "../../stories/fixtures/lore_codex_panels.js";

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

// handbook-codex-tab (design D4): the codex detail, built through the model
// from a synthetic v2 panel.
describe("CodexDetail codex entries (handbook-codex-tab)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
  });

  const LOCKED = ["field_one", "field_two", "field_three", "field_four"];
  const panel = loreCodex([
    codexCategory(MONSTER_CATEGORY, "獸類", [
      {
        key: "tier",
        label: "甲階",
        slots: [
          codexEntry("k_sig", "合成目擊", {
            stage: "sighted",
            card: [
              { name: "display_name_zh", value: "合成目擊" },
              { name: "published_appearance_zh", value: "合成外觀。" },
            ],
            locked_fields: LOCKED,
          }),
          codexEntry("k_def", "合成擊敗", {
            stage: "defeated",
            card: [
              { name: "display_name_zh", value: "合成擊敗" },
              { name: "variants", value: "合成變種甲\n合成變種乙" },
            ],
          }),
        ],
      },
    ]),
  ]);
  const mountCodex = (key) => {
    wrapper = mount(CodexDetail, {
      props: { detail: codexDetail(panel, MONSTER_CATEGORY, key), footer: null, artPanel: panel },
    });
    return wrapper;
  };
  const find = (id) => wrapper.find(`[data-testid="handbook__${id}"]`);
  const reached = () =>
    wrapper.findAll('[data-testid="handbook__research-track"] li').map((li) => li.attributes("data-reached"));

  it("stamps the stage on the hero and draws the art or emblem instead of the medal", () => {
    mountCodex("k_sig");
    expect(find("stamp").attributes("data-stage")).toBe("sighted");
    expect(find("stamp").text()).toBe("目擊");
    expect(wrapper.find(".codex-detail__medal").exists()).toBe(false);
    expect(find("art-emblem").exists()).toBe(true);
    wrapper.unmount();
    mountCodex("k_def");
    expect(find("stamp").attributes("data-stage")).toBe("defeated");
  });

  it("reaches only the first research step for a sighted entry and both once defeated", () => {
    mountCodex("k_sig");
    expect(reached()).toEqual(["true", "false"]);
    wrapper.unmount();
    mountCodex("k_def");
    expect(reached()).toEqual(["true", "true"]);
  });

  it("renders one locked box per locked field, in order, with no value", () => {
    mountCodex("k_sig");
    const boxes = wrapper.findAll('[data-testid="handbook__locked-field"]');
    expect(boxes.map((box) => box.attributes("data-field"))).toEqual(LOCKED);
    for (const box of boxes) {
      expect(box.get("h4").text()).toBe("資料");
      expect(box.get("p").text()).toBe("擊敗後解鎖");
    }
    // Only the shipped field renders as a section, never a locked one.
    const fields = wrapper.findAll('[data-testid="handbook__section"]').map((section) => section.attributes("data-field"));
    expect(fields).toEqual(["published_appearance_zh"]);
  });

  it("renders no locked box for a defeated entry, and keeps a value's lines", () => {
    mountCodex("k_def");
    expect(find("locked-field").exists()).toBe(false);
    const variants = wrapper.get('[data-field="variants"]');
    expect(variants.get("h4").text()).toBe("變種");
    expect(variants.get("p").element.textContent).toBe("合成變種甲\n合成變種乙");
  });

  it("renders no footer for a codex detail", () => {
    mountCodex("k_def");
    expect(wrapper.find("footer").exists()).toBe(false);
    expect(find("actions").exists()).toBe(false);
  });

  it("fills the empty column from the empty slot", () => {
    wrapper = mount(CodexDetail, { props: { detail: null }, slots: { empty: "empty-guidance" } });
    expect(find("detail-empty").text()).toBe("empty-guidance");
  });
});
