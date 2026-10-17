// webclient-combat-foes-on-stage (design D1-D5) and webclient-combat-formation
// (design D1/D3/D4): the foe line-up stands every active foe up to its
// maximum (15, or 16 minus the drawn party), in presenter order, as
// never-dimmed StageActors resolved from the committed art catalog; each slot
// exposes its portrait reference and stands at the formation engine's box;
// names and hit points live on the figure plates, never on a floor plate; a
// foe that leaves is inert while it fades.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";
import FoeLineup from "../../components/FoeLineup.vue";
import { fixtureDigest, artworkDescriptor, artworkResource } from "../../stories/fixtures/art_panels.js";
import { FOE_STAGE_MAX, drawnFoes, fallenLook, foeStageLimit } from "../../components/foe-lineup.js";

const APP_ROOT = join(process.cwd(), "web/webclient-app");

// One committed catalog value: the canonical descriptor plus its context.
function entry(ref, extra = {}) {
  return {
    artwork: artworkDescriptor({
      subject_id: `npc_${ref}`,
      generation_subject: `npc_${ref}`,
      attempts: [
        {
          type: "image",
          source_id: `portrait.default:${ref}`,
          rank: 30,
          resource: artworkResource({
            resource_id: `portrait/character/npc_${ref}.webp`,
            version: fixtureDigest(String(`npc-${ref}`)),
            url: `/art/portraits/npc_${ref}.webp`,
          }),
        },
      ],
    }),
    context: { name: "敵人", role: "敵方" },
    ...extra,
  };
}

// The same value with no real candidate and no terminal.
function pendingEntry(ref, extra = {}) {
  return {
    artwork: artworkDescriptor({
      subject_id: `npc_${ref}`,
      generation_subject: `npc_${ref}`,
      generation_state: "pending",
      attempts: [],
      terminal: null,
    }),
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
  schema_version: 3,
  available: true,
  kind: "scene",
  scene: null,
  portrait_catalog: Object.fromEntries(Array.from({ length: 16 }, (_, i) => [i + 1, entry(i + 1)])),
};

// A formation side for `count` foes: distinct stage-pixel boxes, the first
// foe frontmost (as combat-formation.js returns them).
function formationSide(count) {
  return {
    ranks: 1,
    form: "full",
    figures: Array.from({ length: count }, (_, index) => ({
      index,
      rank: 0,
      box: { left: 1200 - index * 90, top: 240, width: 160, height: 240 },
      z: count - index,
    })),
  };
}

describe("FoeLineup", () => {
  let wrapper;
  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.replaceChildren();
  });

  const slots = () => wrapper.findAll('[data-testid="foe-slot"]');

  it.each([
    [1, FOE_STAGE_MAX, 1],
    [5, FOE_STAGE_MAX, 5],
    [15, FOE_STAGE_MAX, 15],
    [16, FOE_STAGE_MAX, 15],
    [15, 11, 11],
  ])("stands %i active foes under a maximum of %i as %i slots in presenter order", (given, max, shown) => {
    const ids = Array.from({ length: given }, (_, i) => i + 1);
    wrapper = mount(FoeLineup, { props: { foes: ids.map((id) => foe(id)), artPanel: ART, max } });
    const root = wrapper.get('[data-testid="foe-lineup"]');
    expect(root.attributes("data-count")).toBe(String(shown));
    const expected = ids.slice(0, shown).map(String);
    expect(slots().map((s) => s.attributes("data-portrait-ref"))).toEqual(expected);
    expect(slots().map((s) => s.get("img").attributes("src"))).toEqual(
      expected.map((ref) => `/art/portraits/npc_${ref}.webp`),
    );
  });

  it("resolves each foe only through the committed catalog", () => {
    const pending = pendingEntry(2);
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
    // An ADMITTED reference the committed catalog does not carry is a local
    // failure, not an absence: the name's initial and the shared unavailable
    // form stand, with the persistent local marker.
    expect(missing.find("img").exists()).toBe(false);
    expect(missing.attributes("data-portrait-ref")).toBe("9");
    expect(missing.get(".reference-artwork__placeholder-glyph").text()).toBe("蒙");
    expect(missing.get("figcaption").text()).toBe("蒙面刺客，無法提供");
    expect(missing.get('[data-testid="artwork-failure"]').exists()).toBe(true);
  });

  it("shows the name placeholder for a null reference and builds no URL", () => {
    wrapper = mount(FoeLineup, {
      props: { foes: [foe(4, { portrait_ref: null, display_name: "哥布林" })], artPanel: ART },
    });
    const slot = slots()[0];
    expect(slot.attributes("data-portrait-ref")).toBe("");
    expect(slot.find("img").exists()).toBe(false);
    expect(slot.get("figcaption").text()).toBe("哥布林，無肖像");
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

  it("carries no floor name plate, gauge or numerals, and nothing to activate", async () => {
    // The floor name and gauge moved to the figure plates
    // (webclient-combat-formation D4): the line-up states no name, token or
    // number of its own, and clicking or keying a slot activates nothing.
    const foes = [foe(1, { hp_current: 15, display_name: "哥布林" }), foe(2, { display_name: "狼" })];
    wrapper = mount(FoeLineup, { props: { foes, artPanel: ART, formation: formationSide(2) } });
    expect(wrapper.find(".foe-lineup__name").exists()).toBe(false);
    expect(wrapper.find('[data-testid="foe-gauge"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="figure-plate"]').exists()).toBe(false);
    expect(wrapper.text()).not.toMatch(/\d/);
    expect(wrapper.text()).not.toContain("e1");
    await slots()[1].trigger("click");
    await slots()[1].trigger("keydown", { key: "Enter" });
    expect(wrapper.emitted("action")).toBeUndefined();
    expect(wrapper.emitted("select")).toBeUndefined();
  });

  // webclient-combat-defeated-foes (design D1/D5): a knocked-out or
  // defeated foe keeps its slot in its defeated look; the displayed map wins
  // over a row's own state while a round plays.
  describe("fallen foes", () => {
    const slots = () => wrapper.findAll('[data-testid="foe-slot"]');

    it("keeps knocked-out and defeated foes in their slots, collapsed, at the formation's boxes", () => {
      const foes = [foe(1), foe(2, { state: "knocked_out" }), foe(3, { state: "defeated", hp_current: 0 })];
      wrapper = mount(FoeLineup, { props: { foes, artPanel: ART, formation: formationSide(3) } });
      expect(slots().map((s) => s.attributes("data-fallen") ?? null)).toEqual([null, "defeated", "defeated"]);
      expect(slots().map((s) => s.element.style.left)).toEqual(["1200px", "1110px", "1020px"]);
      expect(slots()[2].get('[data-testid="stage-actor"]').attributes("data-fallen")).toBe("defeated");
      expect(slots()[2].find('[data-testid="stage-actor-seal"]').exists()).toBe(true);
      expect(slots()[0].find('[data-testid="stage-actor-seal"]').exists()).toBe(false);
    });

    it("reads the displayed looks while a round plays, and lands them at once while hydrating", async () => {
      const round = { key: "r:1", step: 1, foes: [foe(1), foe(2)], defeated: [], fallen: {}, gestures: {} };
      wrapper = mount(FoeLineup, {
        props: { foes: [foe(1, { state: "defeated" }), foe(2)], stage: round, fallen: {}, artPanel: ART },
      });
      // The committed roster already lost foe 1; it stands until its beat.
      expect(slots()[0].attributes("data-fallen")).toBeUndefined();
      await wrapper.setProps({ fallen: { 1: "defeated" } });
      expect(slots()[0].attributes("data-fallen")).toBe("defeated");
      const fall = slots()[0].get('[data-testid="stage-actor-fall"]');
      expect(fall.attributes("data-fall-instant")).toBeUndefined();
      await wrapper.setProps({ fallInstant: true });
      expect(fall.attributes("data-fall-instant")).toBe("true");
    });
  });

  // webclient-combat-beat-choreography (design D5): while a round plays, the
  // row stands the round's pre-round foes and follows the displayed hit
  // points; each foe plays its own beat gesture.
  describe("while a combat round plays", () => {
    const stage = (foes, gestures = {}, key = "s-1/1:2") => ({ key, step: 2, foes, defeated: [], gestures });

    it("keeps a foe the committed roster has lost until its defeat beat", async () => {
      // The committed state already lost foe 1; the round has not shown its
      // defeat yet.
      wrapper = mount(FoeLineup, {
        props: { foes: [foe(2)], stage: stage([foe(1), foe(2)]), artPanel: ART },
      });
      expect(slots().map((s) => s.attributes("data-portrait-ref"))).toEqual(["1", "2"]);
      // The defeat beat plays on it while it still stands.
      await wrapper.setProps({ stage: stage([foe(1), foe(2)], { 1: { gesture: "defeat", amount: null } }) });
      expect(slots()[0].attributes("data-beat")).toBe("defeat");
      expect(slots()[0].get('[data-testid="stage-actor"] > .stage-actor__fall > .stage-actor__beat').attributes("data-beat")).toBe(
        "defeat",
      );
      // The round ends: the committed foes take over.
      await wrapper.setProps({ stage: null });
      expect(slots().map((s) => s.attributes("data-portrait-ref"))).toEqual(["2"]);
    });

    it("stands every pre-round foe, and drops a front foe once its defeat has played", async () => {
      const round = [foe(1), foe(2), foe(3), foe(4)];
      wrapper = mount(FoeLineup, { props: { foes: [foe(2), foe(3), foe(4)], stage: stage(round), artPanel: ART } });
      expect(slots().map((s) => s.attributes("data-portrait-ref"))).toEqual(["1", "2", "3", "4"]);
      await wrapper.setProps({ stage: stage(round.slice(1)) });
      expect(slots().map((s) => s.attributes("data-portrait-ref"))).toEqual(["2", "3", "4"]);
    });

    it("a live catalog omission is a local failure, never concealed by playback data", () => {
      // The CURRENT committed art panel is authoritative: a held foe whose
      // reference the live catalog no longer carries reports the local failure
      // it is, even though the round captured an older entry for it.
      const heldEntry = entry(99);
      heldEntry.artwork.attempts[0].resource = {
        ...heldEntry.artwork.attempts[0].resource,
        url: "/art/portraits/held_foe.webp",
      };
      const foe99 = foe(99, { display_name: "殘留敵手" });
      wrapper = mount(FoeLineup, {
        props: {
          foes: [foe99],
          artPanel: { ...ART, portrait_catalog: {} },
          stage: {
            key: "round:1",
            foes: [foe99],
            foeCatalog: { "99": heldEntry },
            gestures: {},
          },
        },
      });
      const slot = slots()[0];
      expect(slot.find("img").exists()).toBe(false);
      expect(slot.find('[data-testid="artwork-failure"]').exists()).toBe(true);
    });

    it("permits the captured catalog only when no live panel is committed", () => {
      // With no committed `art` panel at all, the round's own captured catalog
      // (an available panel's catalog when the round began) stands in.
      const heldEntry = entry(99);
      heldEntry.artwork.attempts[0].resource = {
        ...heldEntry.artwork.attempts[0].resource,
        url: "/art/portraits/held_foe.webp",
      };
      const foe99 = foe(99, { display_name: "殘留敵手" });
      wrapper = mount(FoeLineup, {
        props: {
          foes: [foe99],
          artPanel: null,
          stage: {
            key: "round:1",
            foes: [foe99],
            foeCatalog: { "99": heldEntry },
            gestures: {},
          },
        },
      });
      const slot = slots()[0];
      expect(slot.find("img").attributes("src")).toBe("/art/portraits/held_foe.webp");
      expect(slot.find('[data-testid="artwork-failure"]').exists()).toBe(false);
    });

    it("hands each foe its gesture, key, and damage number", () => {
      wrapper = mount(FoeLineup, {
        props: {
          foes: [foe(1), foe(2)],
          stage: stage([foe(1), foe(2)], {
            1: { gesture: "hit", amount: 12 },
            2: { gesture: "lunge", amount: null },
          }),
          artPanel: ART,
        },
      });
      const [first, second] = slots();
      expect(first.get(".stage-actor__beat").attributes("data-beat")).toBe("hit");
      expect(first.get('[data-testid="stage-actor-float"]').text()).toBe("−12");
      expect(second.get(".stage-actor__beat").attributes("data-beat")).toBe("lunge");
      expect(second.find('[data-testid="stage-actor-float"]').exists()).toBe(false);
      // The float is decorative and the row stays hidden from assistive
      // technology.
      expect(first.get('[data-testid="stage-actor-float"]').attributes("aria-hidden")).toBe("true");
      expect(wrapper.get('[data-testid="foe-lineup"]').attributes("aria-hidden")).toBe("true");
    });
  });

  it("stands each slot at its formation box in stage pixels, the first foe frontmost", async () => {
    const formation = formationSide(3);
    wrapper = mount(FoeLineup, { props: { foes: [foe(1), foe(2), foe(3)], artPanel: ART, formation } });
    expect(wrapper.get('[data-testid="foe-lineup"]').attributes("data-formation")).toBe("true");
    slots().forEach((slot, index) => {
      const { box, z } = formation.figures[index];
      const style = slot.element.style;
      expect([style.left, style.top, style.width, style.height]).toEqual(
        [box.left, box.top, box.width, box.height].map((value) => `${value}px`),
      );
      expect(Number(style.zIndex)).toBe(z);
      expect(style.getPropertyValue("--foe-index")).toBe(String(index));
      // The glide wrapper the shell's shared-scale glide drives.
      expect(slot.get(".formation-figure").attributes("data-glide-key")).toBe(`foe:${index + 1}`);
    });
    // Without a measured formation the slots carry no stage position.
    await wrapper.setProps({ formation: null });
    expect(wrapper.get('[data-testid="foe-lineup"]').attributes("data-formation")).toBeUndefined();
    expect(slots()[0].element.style.left).toBe("");
    // A resize, a reconnect and the lower motion levels re-form in place.
    expect(wrapper.get('[data-testid="foe-lineup"]').attributes("data-glide")).toBe("true");
    await wrapper.setProps({ glide: false });
    expect(wrapper.get('[data-testid="foe-lineup"]').attributes("data-glide")).toBe("false");
  });

  it("makes a leaving foe inert while it fades", async () => {
    wrapper = mount(FoeLineup, {
      props: { foes: [foe(1), foe(2)], artPanel: ART, motionLevel: "full", formation: formationSide(2) },
      global: { stubs: { transition: false, "transition-group": false } },
      attachTo: document.body,
    });
    const leaving = slots()[0].element;
    const leavingLeft = leaving.style.left;
    await wrapper.setProps({ foes: [foe(2)], formation: formationSide(1) });
    await nextTick();
    expect(leaving.isConnected).toBe(true);
    expect(leaving.inert).toBe(true);
    expect(leaving.classList.contains("foe-leave-active")).toBe(true);
    expect(wrapper.emitted("settled")).toBeUndefined();
    // The remaining foe re-slots into the front place.
    const remaining = wrapper.findAll('[data-testid="foe-slot"]').filter((s) => !s.element.inert);
    expect(remaining).toHaveLength(1);
    expect(remaining[0].attributes("data-portrait-ref")).toBe("2");
    expect(remaining[0].element.style.left).toBe(`${formationSide(1).figures[0].box.left}px`);
    // The leaving foe fades where it stood.
    expect(leaving.style.left).toBe(leavingLeft);
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
    // The leave has settled, and the row says so.
    expect(wrapper.emitted("settled")).toHaveLength(1);
  });

  it("names every duration through the motion tokens and never FLIPs the re-slotting", () => {
    const source = readFileSync(join(APP_ROOT, "components/FoeLineup.vue"), "utf8");
    expect(source).not.toMatch(/(transition|animation)[a-z-]*:[^;]*[0-9]m?s/);
    const slotRule = /\.foe-lineup__slot \{[\s\S]*?\}/.exec(source)[0];
    // One shared re-forming rule: every box edge on the travel duration.
    for (const property of ["left", "top", "width", "height"]) {
      expect(slotRule).toContain(`${property} calc(var(--motion-actor) * var(--motion-travel)) var(--ease-standard)`);
    }
    expect(slotRule).not.toMatch(/transition:[^;]*transform/);
    expect(source).toMatch(/\.foe-lineup\[data-glide="false"\] > \.foe-lineup__slot \{\s*transition: none;/);
  });
});

describe("the line-up selection", () => {
  it("stands at most fifteen foes, and sixteen participants with the drawn party", () => {
    expect(FOE_STAGE_MAX).toBe(15);
    expect(foeStageLimit(1)).toBe(15);
    expect(foeStageLimit(3)).toBe(13);
    expect(foeStageLimit(5)).toBe(11);
    // The controlled figure always stands, so a party of none counts as one.
    expect(foeStageLimit(0)).toBe(15);
  });

  it("selects the foes that have not fled in presenter order: the fallen keep their slot", () => {
    const participants = [
      foe(1),
      { ...foe(2), team: "party" },
      foe(3, { state: "defeated" }),
      foe(4, { state: "fled" }),
      foe(5, { state: "knocked_out" }),
      foe(6),
    ];
    expect(drawnFoes(participants).map((p) => p.identity)).toEqual([1, 3, 5, 6]);
    expect(drawnFoes(null)).toEqual([]);
  });

  it("maps a participant's state to its fallen look", () => {
    expect(fallenLook("foes", "knocked_out")).toBe("defeated");
    expect(fallenLook("foes", "defeated")).toBe("defeated");
    expect(fallenLook("party", "knocked_out")).toBe("down");
    expect(fallenLook("foes", "active")).toBeNull();
    expect(fallenLook("foes", "fled")).toBeNull();
    expect(fallenLook("party", "active")).toBeNull();
  });
});

// webclient-combat-stage-target-picking (design D4): during the stage target
// step every foe outside the lit set takes the dialogue listener dim (a
// fallen foe keeps its fallen look instead), lit foes carry the focus ring
// (static below `full`), and only selectable foes carry a hit area; no box or
// z changes, and nothing remains once the step ends.
describe("FoeLineup in the stage target step", () => {
  let wrapper;
  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });
  const targeting = (lit, selectable) => ({ lit: new Set(lit), selectable: new Set(selectable), selected: new Set() });
  const foes = [foe(1), foe(2), foe(3, { state: "defeated" }), foe(4)];
  const read = () =>
    wrapper.findAll('[data-testid="foe-slot"]').map((slot) => ({
      id: slot.attributes("data-identity"),
      speaking: slot.get('[data-testid="stage-actor"]').attributes("data-speaking"),
      focus: slot.attributes("data-target-focus") ?? null,
      motion: slot.attributes("data-target-motion") ?? null,
      hit: slot.find('[data-testid="stage-target-hit"]').exists(),
      style: slot.attributes("style"),
    }));

  it("dims all but the lit set, keeps the fallen look, and puts hit areas on candidates only", async () => {
    wrapper = mount(FoeLineup, { props: { foes, artPanel: ART, formation: formationSide(4), motionLevel: "full" } });
    const before = read();
    expect(before.every((s) => s.speaking === "true" && !s.hit && s.focus === null && s.motion === null)).toBe(true);
    await wrapper.setProps({ targeting: targeting(["2"], ["1", "2", "3"]) });
    const during = read();
    expect(during.map((s) => s.speaking)).toEqual(["false", "true", "true", "false"]);
    expect(during.map((s) => s.focus)).toEqual([null, "true", null, null]);
    expect(during.map((s) => s.hit)).toEqual([true, true, true, false]);
    expect(during.every((s) => s.motion === "full")).toBe(true);
    // No box or z changes for the step.
    expect(during.map((s) => s.style)).toEqual(before.map((s) => s.style));
    // The hit area reports the identity and the action.
    await wrapper.findAll('[data-testid="stage-target-hit"]')[0].trigger("pointerenter");
    await wrapper.findAll('[data-testid="stage-target-hit"]')[0].trigger("click");
    expect(wrapper.emitted("target-pointer")).toEqual([[1, "hover"], [1, "activate"]]);
    // Below `full` the ring is static.
    await wrapper.setProps({ motionLevel: "reduced" });
    expect(read().every((s) => s.motion === "static")).toBe(true);
    // The step ends: every foe returns to its state before it.
    await wrapper.setProps({ targeting: null });
    expect(read()).toEqual(before);
  });

  it("styles the static ring, the pulse and the reduced-motion fallback in the shared tokens", () => {
    const tokens = readFileSync(join(APP_ROOT, "styles/tokens.css"), "utf-8");
    expect(tokens).toMatch(/\[data-target-focus="true"\] > \.formation-figure \{[^}]*animation: elosern-target-pulse var\(--motion-target-pulse\)/);
    expect(tokens).toMatch(/\[data-target-motion="static"\]\[data-target-focus="true"\] > \.formation-figure \{[^}]*animation: none/);
    expect(tokens).toMatch(/@media \(prefers-reduced-motion: reduce\) \{\s*:root:not\(\[data-motion\]\) \[data-target-focus="true"\] > \.formation-figure \{[^}]*animation: none/);
    expect(tokens).toMatch(/\.stage-target__hit \{[^}]*pointer-events: auto/);
  });
});
