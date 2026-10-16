// webclient-combat-defeated-foes (design D1-D4): a fallen figure keeps its
// slot in a look of its own. StageActor's `fallen` puts the pose and the tone
// on the `.stage-actor__fall` wrapper around the keyed beat wrapper, stamps
// the broken seal over a defeated foe's chest only, keeps the seal out of the
// accessibility tree, and lands a change of look at once at `off` and while
// the client hydrates. The pose tokens compress about the base, so the
// transformed box stays inside the untransformed slot.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import StageActor from "../../components/StageActor.vue";
import { artworkDescriptor, artworkResource } from "../../stories/fixtures/art_panels.js";

const APP_ROOT = join(process.cwd(), "web/webclient-app");
const PANEL = { schema_version: 3, available: true };
const ENTRY = artworkDescriptor({
  subject_id: "npc_41",
  generation_subject: "npc_41",
  generation_state: "done",
  attempts: [
    {
      type: "image",
      source_id: "portrait.default:41",
      rank: 30,
      resource: artworkResource({ resource_id: "portrait/character/npc_41.webp", url: "/art/portraits/npc_41.webp" }),
    },
  ],
});

function token(css, name) {
  const match = new RegExp(`${name}:\\s*([^;]+);`).exec(css);
  if (!match) throw new Error(`missing token ${name}`);
  return match[1].trim();
}

// The box a CSS `transform` of the form `scaleY(s)` (optionally after a
// `translateY(p%)`) maps a `height`-tall slot to, about `transform-origin`'s
// vertical position `originY` (0 = top, 1 = base). Independent of the
// component: plain affine arithmetic on the box's two edges.
function transformedEdges(height, { scaleY, translateY = 0, originY }) {
  const origin = originY * height;
  const map = (y) => origin + (y - origin) * scaleY + translateY * height;
  return { top: map(0), bottom: map(height) };
}

describe("StageActor fallen looks", () => {
  let wrapper;
  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  const fall = () => wrapper.get('[data-testid="stage-actor"] > [data-testid="stage-actor-fall"]');
  const seal = () => wrapper.find('[data-testid="stage-actor-seal"]');

  it("stands with no fallen look and no seal by default", () => {
    wrapper = mount(StageActor, { props: { artwork: ENTRY, panel: PANEL, side: "right" } });
    expect(wrapper.attributes("data-fallen")).toBeUndefined();
    expect(fall().attributes("data-fallen")).toBeUndefined();
    expect(seal().exists()).toBe(false);
  });

  it("collapses a defeated foe with a decorative broken seal, and kneels a downed ally without one", async () => {
    wrapper = mount(StageActor, { props: { artwork: ENTRY, panel: PANEL, side: "right", fallen: "defeated" } });
    expect(wrapper.attributes("data-fallen")).toBe("defeated");
    expect(fall().attributes("data-fallen")).toBe("defeated");
    expect(seal().exists()).toBe(true);
    expect(seal().attributes("aria-hidden")).toBe("true");
    // The seal is drawn, not a bitmap: a ring with a missing wedge and a crack.
    expect(seal().element.tagName.toLowerCase()).toBe("svg");
    expect(seal().find(".stage-actor__seal-ring").exists()).toBe(true);
    expect(seal().find(".stage-actor__seal-crack").exists()).toBe(true);
    expect(wrapper.find("img[src*='seal']").exists()).toBe(false);
    // The beat wrapper (and the portrait in it) stands inside the fall wrapper.
    expect(fall().find(".stage-actor__beat [data-testid='reference-artwork']").exists()).toBe(true);
    expect(wrapper.findAll("button, a, input, textarea, select, [tabindex]")).toHaveLength(0);

    await wrapper.setProps({ side: "left", fallen: "down" });
    expect(fall().attributes("data-fallen")).toBe("down");
    expect(seal().exists()).toBe(false);
  });

  it("keeps the fall wrapper mounted across beat steps, so a collapse is never cut short", async () => {
    wrapper = mount(StageActor, {
      props: { artwork: ENTRY, panel: PANEL, side: "right", gesture: "hit", gestureKey: "r:1", floatAmount: 9 },
    });
    const element = fall().element;
    await wrapper.setProps({ gesture: "defeat", gestureKey: "r:2", floatAmount: null, fallen: "defeated" });
    expect(fall().element).toBe(element);
    expect(fall().get(".stage-actor__beat").attributes("data-beat")).toBe("defeat");
    await wrapper.setProps({ gesture: null, gestureKey: null });
    expect(fall().element).toBe(element);
    expect(fall().attributes("data-fallen")).toBe("defeated");
  });

  it("lands a change of look in the commit's frame at off and while hydrating", async () => {
    wrapper = mount(StageActor, { props: { artwork: ENTRY, panel: PANEL, side: "right", motionLevel: "full" } });
    expect(fall().attributes("data-fall-instant")).toBeUndefined();
    await wrapper.setProps({ motionLevel: "off" });
    expect(fall().attributes("data-fall-instant")).toBe("true");
    await wrapper.setProps({ motionLevel: "reduced" });
    expect(fall().attributes("data-fall-instant")).toBeUndefined();
    await wrapper.setProps({ fallInstant: true });
    expect(fall().attributes("data-fall-instant")).toBe("true");
    // At off the seal is in place in the same frame (no enter phase).
    await wrapper.setProps({ fallInstant: false, motionLevel: "off", fallen: "defeated" });
    expect(seal().exists()).toBe(true);
    expect(seal().classes()).not.toContain("stage-seal-enter-active");
  });

  it("composes each look from the fallen tokens, with no transition when instant", () => {
    const source = readFileSync(join(APP_ROOT, "components/StageActor.vue"), "utf-8");
    const rule = (selector) => {
      const start = source.indexOf(`${selector} {`);
      expect(start, selector).toBeGreaterThan(-1);
      return source.slice(start, source.indexOf("}", start));
    };
    const base = rule(".stage-actor__fall");
    expect(base).toMatch(/transform-origin:\s*50% 100%/);
    // The pose travels with the motion level; tone and opacity fade on the defeat beat.
    expect(base).toMatch(/transform calc\(var\(--motion-beat-defeat\) \* var\(--motion-travel\)\) var\(--ease-exit\)/);
    expect(base).toMatch(/filter var\(--motion-beat-defeat\) var\(--ease-exit\)/);
    const defeated = rule('.stage-actor__fall[data-fallen="defeated"]');
    expect(defeated).toContain("transform: scaleY(var(--fall-defeated-squash))");
    expect(defeated).toContain("filter: var(--fall-defeated-tone)");
    expect(defeated).toContain("opacity: var(--fall-defeated-opacity)");
    const down = rule('.stage-actor__fall[data-fallen="down"]');
    expect(down).toContain("transform: scaleY(var(--fall-down-squash))");
    expect(rule('.stage-actor__fall[data-fall-instant="true"]')).toContain("transition: none");
    // Never rotated or translated: a pure compression.
    expect(`${defeated}${down}`).not.toMatch(/rotate|translate/);
  });

  it("keeps each posed figure's transformed box inside its untransformed slot, feet planted", () => {
    const css = readFileSync(join(APP_ROOT, "styles/tokens.css"), "utf-8");
    const defeatedSquash = Number(token(css, "--fall-defeated-squash"));
    const downSquash = Number(token(css, "--fall-down-squash"));
    expect(defeatedSquash).toBe(0.8);
    expect(downSquash).toBe(0.92);
    expect(token(css, "--fall-defeated-tone")).toBe("grayscale(1) brightness(0.45)");
    expect(token(css, "--fall-defeated-opacity")).toBe("0.8");
    expect(token(css, "--fall-down-tone")).toBe("grayscale(0.6) brightness(0.7)");
    expect(token(css, "--fall-down-opacity")).toBe("1");
    const height = 440;
    for (const [squash, drop] of [[defeatedSquash, 0.2], [downSquash, 0.08]]) {
      const box = transformedEdges(height, { scaleY: squash, originY: 1 });
      expect(box.top).toBeGreaterThanOrEqual(0);
      expect(box.bottom).toBeLessThanOrEqual(height);
      expect(box.bottom).toBeCloseTo(height, 6);
      expect(box.top / height).toBeCloseTo(drop, 6);
    }
    // The rejected sink (a 12% drop about the base) would leave the slot.
    expect(transformedEdges(height, { scaleY: 0.8, translateY: 0.12, originY: 1 }).bottom).toBeGreaterThan(height);
  });

  it("differs from the listener dim by shape and mark, not brightness alone", () => {
    wrapper = mount(StageActor, { props: { artwork: ENTRY, panel: PANEL, side: "left", dimmed: true } });
    expect(wrapper.attributes("data-speaking")).toBe("false");
    expect(fall().attributes("data-fallen")).toBeUndefined();
    expect(seal().exists()).toBe(false);
  });
});
