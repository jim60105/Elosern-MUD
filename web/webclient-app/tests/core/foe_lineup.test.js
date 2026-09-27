// webclient-combat-foes-on-stage (design D1-D5): the foe line-up stands at
// most three foes in `actor-right`, in presenter order, as never-dimmed
// StageActors resolved from the committed art catalog; each slot exposes
// its portrait reference and a decorative hit-point gauge; the row is a
// depth-staged, leftward-growing line whose geometry comes from one pure
// helper; a foe that leaves is inert while it fades.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";
import FoeLineup from "../../components/FoeLineup.vue";
import {
  FOE_EXPOSED,
  FOE_LINEUP_MAX,
  FOE_SCALES,
  activeFoes,
  foeHpPercent,
  foeLineupSpan,
  foeSlots,
} from "../../components/foe-lineup.js";

const APP_ROOT = join(process.cwd(), "web/webclient-app");

function entry(ref, extra = {}) {
  return {
    subject_key: `npc_${ref}`,
    status: "done",
    url: `/art/portraits/npc_${ref}.webp`,
    aspect_ratio: "3:4",
    alt: "肖像",
    placeholder: null,
    face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.5 },
    context: { name: "敵人", role: "敵方" },
    ...extra,
  };
}

function foe(identity, extra = {}) {
  return {
    identity,
    token: `e${identity}`,
    display_name: `敵人${identity}`,
    team: "foes",
    state: "active",
    hp_current: 30,
    hp_maximum: 60,
    portrait_ref: String(identity),
    ...extra,
  };
}

const ART = {
  schema_version: 2,
  available: true,
  kind: "scene",
  scene: null,
  portrait_catalog: { 1: entry(1), 2: entry(2), 3: entry(3), 4: entry(4), 5: entry(5) },
};

describe("FoeLineup", () => {
  let wrapper;
  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.replaceChildren();
  });

  const slots = () => wrapper.findAll('[data-testid="foe-slot"]');

  it.each([
    [1, 1],
    [3, 3],
    [5, 3],
  ])("stands %i active foes as %i slots in presenter order", (given, shown) => {
    const foes = [1, 2, 3, 4, 5].slice(0, given).map((id) => foe(id));
    wrapper = mount(FoeLineup, { props: { foes, artPanel: ART } });
    const root = wrapper.get('[data-testid="foe-lineup"]');
    expect(root.attributes("data-count")).toBe(String(shown));
    expect(slots().map((s) => s.attributes("data-portrait-ref"))).toEqual(
      ["1", "2", "3"].slice(0, shown),
    );
    expect(slots().map((s) => s.get("img").attributes("src"))).toEqual(
      ["1", "2", "3"].slice(0, shown).map((ref) => `/art/portraits/npc_${ref}.webp`),
    );
  });

  it("resolves each foe only through the committed catalog", () => {
    const pending = entry(2, {
      status: "pending",
      url: null,
      face_rect: null,
      placeholder: { kind: "missing", label: "肖像生成中" },
    });
    wrapper = mount(FoeLineup, {
      props: {
        foes: [foe(1), foe(2), foe(9, { display_name: "蒙面刺客" })],
        artPanel: { ...ART, portrait_catalog: { 1: entry(1), 2: pending } },
      },
    });
    const [image, card, missing] = slots();
    expect(image.get("img").attributes("src")).toBe("/art/portraits/npc_1.webp");
    // A pending entry keeps its own card and label, the foe's initial in the ring.
    expect(card.find("img").exists()).toBe(false);
    expect(card.get(".reference-artwork__placeholder-label").text()).toBe("肖像生成中");
    expect(card.get(".reference-artwork__placeholder-glyph").text()).toBe("敵");
    // A reference with no entry: the name's initial and the name.
    expect(missing.find("img").exists()).toBe(false);
    expect(missing.attributes("data-portrait-ref")).toBe("9");
    expect(missing.get(".reference-artwork__placeholder-glyph").text()).toBe("蒙");
    expect(missing.get(".reference-artwork__placeholder-label").text()).toBe("蒙面刺客");
  });

  it("shows the name placeholder for a null reference and builds no URL", () => {
    wrapper = mount(FoeLineup, {
      props: { foes: [foe(4, { portrait_ref: null, display_name: "哥布林" })], artPanel: ART },
    });
    const slot = slots()[0];
    expect(slot.attributes("data-portrait-ref")).toBe("");
    expect(slot.find("img").exists()).toBe(false);
    expect(slot.get(".reference-artwork__placeholder-label").text()).toBe("哥布林");
    expect(wrapper.html()).not.toContain("npc_4");
  });

  it("is decorative: never dimmed, nothing focusable, hidden from assistive technology", () => {
    wrapper = mount(FoeLineup, { props: { foes: [foe(1), foe(2)], artPanel: ART } });
    const root = wrapper.get('[data-testid="foe-lineup"]');
    expect(root.attributes("aria-hidden")).toBe("true");
    expect(root.findAll("button, a, input, textarea, select, [tabindex]")).toHaveLength(0);
    const actors = wrapper.findAll('[data-testid="stage-actor"]');
    expect(actors).toHaveLength(2);
    for (const actor of actors) {
      expect(actor.attributes("data-side")).toBe("right");
      expect(actor.attributes("data-speaking")).toBe("true");
    }
  });

  it("carries a gauge per foe from the committed hit points, with no numerals", async () => {
    wrapper = mount(FoeLineup, {
      props: { foes: [foe(1, { hp_current: 15, hp_maximum: 60 }), foe(2, { hp_current: 0, hp_maximum: 0 })], artPanel: ART },
    });
    const gauges = wrapper.findAll('[data-testid="foe-gauge"]');
    expect(gauges).toHaveLength(2);
    expect(gauges[0].get(".foe-lineup__fill").element.style.width).toBe("25%");
    expect(gauges[0].get(".foe-lineup__ghost").element.style.width).toBe("25%");
    expect(gauges[1].get(".foe-lineup__fill").element.style.width).toBe("0%");
    expect(wrapper.text()).not.toMatch(/\d/);
    expect(wrapper.text()).not.toContain("e1");
    await wrapper.setProps({ foes: [foe(1, { hp_current: 45, hp_maximum: 60 }), foe(2)] });
    expect(wrapper.findAll(".foe-lineup__fill")[0].element.style.width).toBe("75%");
  });

  it("places each slot from the geometry helper, the front foe above the ones behind", () => {
    wrapper = mount(FoeLineup, { props: { foes: [foe(1), foe(2), foe(3)], artPanel: ART } });
    const geometry = foeSlots(3);
    slots().forEach((slot, index) => {
      const style = slot.element.style;
      expect(style.height).toBe(`${geometry[index].scale * 100}%`);
      expect(style.right).toBe(`${geometry[index].right * 100}%`);
      expect(style.bottom).toBe(`${geometry[index].lift * 100}%`);
      expect(Number(style.zIndex)).toBe(3 - index);
      expect(style.getPropertyValue("--foe-index")).toBe(String(index));
    });
    expect(wrapper.get('[data-testid="foe-lineup"]').element.style.getPropertyValue("--foe-front-scale")).toBe(
      String(geometry[0].scale),
    );
  });

  it("makes a leaving foe inert while it fades", async () => {
    wrapper = mount(FoeLineup, {
      props: { foes: [foe(1), foe(2)], artPanel: ART, motionLevel: "full" },
      global: { stubs: { transition: false, "transition-group": false } },
      attachTo: document.body,
    });
    const leaving = slots()[0].element;
    await wrapper.setProps({ foes: [foe(2)] });
    await nextTick();
    expect(leaving.isConnected).toBe(true);
    expect(leaving.inert).toBe(true);
    expect(leaving.classList.contains("foe-leave-active")).toBe(true);
    // The remaining foe re-slots into the front place.
    const remaining = wrapper.findAll('[data-testid="foe-slot"]').filter((s) => !s.element.inert);
    expect(remaining).toHaveLength(1);
    expect(remaining[0].attributes("data-portrait-ref")).toBe("2");
    expect(remaining[0].element.style.right).toBe("0%");
  });

  it("removes a leaving foe at once at the off level", async () => {
    wrapper = mount(FoeLineup, {
      props: { foes: [foe(1), foe(2)], artPanel: ART, motionLevel: "off" },
      global: { stubs: { transition: false, "transition-group": false } },
      attachTo: document.body,
    });
    await wrapper.setProps({ foes: [foe(2)] });
    await nextTick();
    expect(slots()).toHaveLength(1);
  });

  it("names every duration through the motion tokens and never FLIPs the re-slotting", () => {
    const source = readFileSync(join(APP_ROOT, "components/FoeLineup.vue"), "utf8");
    expect(source).not.toMatch(/(transition|animation)[a-z-]*:[^;]*[0-9]m?s/);
    const slotRule = /\.foe-lineup__slot \{[\s\S]*?\}/.exec(source)[0];
    expect(slotRule).toContain("right calc(var(--motion-actor) * var(--motion-travel))");
    expect(slotRule).toContain("height calc(var(--motion-actor) * var(--motion-travel))");
    expect(slotRule).not.toMatch(/transition:[^;]*transform/);
  });
});

describe("the line-up geometry", () => {
  it("caps the row at three and keeps every scale falling front to back", () => {
    expect(FOE_LINEUP_MAX).toBe(3);
    expect(foeSlots(5)).toHaveLength(3);
    expect(foeSlots(0)).toEqual([]);
    for (const count of [1, 2, 3]) {
      const scales = FOE_SCALES[count];
      expect(scales).toHaveLength(count);
      scales.slice(1).forEach((scale, i) => expect(scale).toBeLessThan(scales[i]));
      // The front foe gives up height as the group grows.
      if (count > 1) expect(scales[0]).toBeLessThan(FOE_SCALES[count - 1][0]);
    }
    expect(FOE_SCALES[1]).toEqual([1]);
  });

  it("steps each foe left so exactly the exposed share of it shows past the one in front", () => {
    const slots = foeSlots(3);
    expect(slots[0].right).toBe(0);
    for (let i = 1; i < slots.length; i += 1) {
      const frontLeft = slots[i - 1].right + slots[i - 1].scale;
      const backLeft = slots[i].right + slots[i].scale;
      expect(backLeft - frontLeft).toBeCloseTo(FOE_EXPOSED * slots[i].scale, 10);
      expect(slots[i].lift).toBeGreaterThan(slots[i - 1].lift);
      expect(slots[i].z).toBeLessThan(slots[i - 1].z);
    }
    expect(foeLineupSpan(0)).toBe(0);
    expect(foeLineupSpan(1)).toBe(1);
    expect(foeLineupSpan(3)).toBeCloseTo(slots[2].right + slots[2].scale, 10);
    expect(foeLineupSpan(2)).toBeLessThan(foeLineupSpan(3));
  });

  it("selects the active foes in presenter order and computes the gauge", () => {
    const participants = [
      foe(1),
      { ...foe(2), team: "party" },
      foe(3, { state: "defeated" }),
      foe(4, { state: "fled" }),
      foe(5, { state: "knocked_out" }),
      foe(6),
    ];
    expect(activeFoes(participants).map((p) => p.identity)).toEqual([1, 6]);
    expect(activeFoes(null)).toEqual([]);
    expect(foeHpPercent({ hp_current: 30, hp_maximum: 60 })).toBe(50);
    expect(foeHpPercent({ hp_current: 90, hp_maximum: 60 })).toBe(100);
    expect(foeHpPercent({ hp_current: 1, hp_maximum: 0 })).toBe(0);
    expect(foeHpPercent({ hp_current: null, hp_maximum: 60 })).toBeNull();
  });
});
