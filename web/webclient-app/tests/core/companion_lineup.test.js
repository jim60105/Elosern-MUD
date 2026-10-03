import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import CompanionLineup from "../../components/CompanionLineup.vue";
import { companionSlots, companionLineupSpan, companionFigures } from "../../components/companion-lineup.js";
import { portraitFor } from "../../components/party-helpers.js";

const player = { identity: 1, portrait: null, displayName: "測試主角" };
const companions = Array.from({ length: 4 }, (_, i) => ({ identity: i + 2, portrait_ref: i === 0 ? "2" : null, display_name: `同行${i}` }));
const entry = { url: null, status: "pending", placeholder: { kind: "missing", label: "尚未生成" } };
const artPanel = { portrait_catalog: { "2": entry } };
const figures = (overrides = {}) => companionFigures({ player, companions, actorIdentity: "1", possessing: false, artPanel, portraitFor, ...overrides });

describe("companion standing lineup", () => {
  it("keeps solo geometry and bounds the actual 2:3 anchor at every acceptance viewport", () => {
    expect(companionSlots(0)).toEqual([]);
    expect(companionSlots(1)).toEqual([{ scale: 1, x: 0, lift: 0, z: 1 }]);
    expect(companionSlots(99)).toHaveLength(5);
    for (let count = 2; count <= 5; count++) {
      const slots = companionSlots(count);
      slots.slice(1).forEach((slot, i) => {
        expect(slot.x).toBeLessThan(slots[i].x);
        expect(slot.scale).toBe(1);
        expect(slot.z).toBeLessThan(slots[i].z);
        expect(slot.lift).toBe(0);
      });
      for (const [width, height] of [[1920, 1080], [1440, 900], [1280, 720]]) {
        const band = Math.max(260, Math.min(400, height * 0.278));
        const actorHeight = Math.min(height * 0.62, 680, height - 48 - band);
        const anchorWidth = actorHeight * 2 / 3;
        const column = width <= 1440 ? 216 : Math.max(220, Math.min(330, width * 0.2));
        const inset = Math.max(width * 0.06, column + 8 - actorHeight / 3);
        const span = companionLineupSpan(count) * anchorWidth;
        const shift = Math.max(0, span - anchorWidth - inset + 16);
        expect(inset + anchorWidth + shift - span).toBeGreaterThanOrEqual(16);
        expect(inset + anchorWidth + shift).toBeLessThan(width / 2);
        const choiceLeft = Math.max(width * 0.3, width / 2 - 280);
        const maximumSpan = (choiceLeft - 32) / anchorWidth;
        expect(16 + companionLineupSpan(count, maximumSpan) * anchorWidth).toBeLessThanOrEqual(choiceLeft - 16);
      }
    }
  });
  it("swaps exactly the possessed companion's former position and restores on release", () => {
    const normal = figures();
    const possessed = figures({ actorIdentity: "3", possessing: true });
    expect(normal.map((s) => s.identity)).toEqual([1, 2, 3, 4, 5]);
    expect(possessed.map((s) => s.identity)).toEqual([3, 2, 1, 4, 5]);
    expect(possessed[0].portrait).toBeNull();
    expect(possessed[0].displayName).toBe("同行1");
    expect(possessed.filter((s) => s.isControlled)).toHaveLength(1);
    expect(figures()).toEqual(normal);
    expect(figures({ actorIdentity: "3", possessing: false })).toEqual(normal);
    const unknown = figures({ actorIdentity: "99", possessing: true, controlledName: "測試宿主" });
    expect(unknown[0]).toEqual({ identity: "99", portrait: null, displayName: "測試宿主", isControlled: true });
    expect(unknown.slice(1)).toEqual(normal.slice(1));
  });
  it("retains pending catalog entries and uses null for missing refs without inventing art", () => {
    expect(figures()[1].portrait).toBe(entry);
    expect(portraitFor(artPanel, "missing")).toBeNull();
    expect(portraitFor(artPanel, null)).toBeNull();
  });
  it("renders decorative figures and forwards the controlled beat only", async () => {
    const wrapper = mount(CompanionLineup, { props: { slots: figures(), dimmed: true, gesture: "hit", gestureKey: "r:1", floatAmount: 8, motionLevel: "off" } });
    expect(wrapper.attributes("aria-hidden")).toBe("true");
    expect(wrapper.findAll('[data-testid="companion-figure"]')).toHaveLength(5);
    expect(wrapper.findAll('[data-beat="hit"]')).toHaveLength(1);
    expect(wrapper.findAll('[data-speaking="false"]')).toHaveLength(5);
    expect(wrapper.findAll("button, a, input, [tabindex]")).toHaveLength(0);
    await wrapper.setProps({ slots: figures({ actorIdentity: "3", possessing: true }) });
    expect(wrapper.get('[data-slot="0"]').attributes("data-identity")).toBe("3");
    expect(wrapper.get('[data-slot="2"]').attributes("data-identity")).toBe("1");
    expect(wrapper.findAll('[data-beat="hit"]')).toHaveLength(1);
    wrapper.unmount();
  });
  it("lifts only the speaking companion and always restores paint without moving slots", async () => {
    const wrapper = mount(CompanionLineup, { props: { slots: figures(), motionLevel: "off" } });
    const slot = () => wrapper.get('[data-slot="2"]');
    const originalPosition = [slot().element.style.right, slot().element.style.bottom, slot().element.style.height];
    expect(wrapper.findAll('[data-speaking="false"]')).toHaveLength(4);
    expect(slot().element.style.zIndex).toBe("3");
    await wrapper.setProps({ speakingIdentity: 3, dimmed: true });
    expect(slot().element.style.zIndex).toBe("6");
    expect(slot().get('[data-testid="stage-actor"]').attributes("data-speaking")).toBe("true");
    expect([slot().element.style.right, slot().element.style.bottom, slot().element.style.height]).toEqual(originalPosition);
    await wrapper.setProps({ slots: figures({ actorIdentity: "3", possessing: true }) });
    expect(slot().element.style.zIndex).toBe("3");
    expect(slot().get('[data-testid="stage-actor"]').attributes("data-speaking")).toBe("false");
    await wrapper.setProps({ slots: figures(), speakingIdentity: 4 });
    expect(slot().element.style.zIndex).toBe("3");
    expect(wrapper.get('[data-slot="3"]').element.style.zIndex).toBe("6");
    await wrapper.setProps({ speakingIdentity: null, slots: figures().slice(0, 3) });
    expect(slot().element.style.zIndex).toBe("1");
    expect(slot().get('[data-testid="stage-actor"]').attributes("data-speaking")).toBe("false");
    wrapper.unmount();
  });
});
