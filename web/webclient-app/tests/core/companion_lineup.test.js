import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import CompanionLineup from "../../components/CompanionLineup.vue";
import {
  companionSlots,
  companionLineupSpan,
  companionFigures,
  displayedLineup,
  lineupSlotByIdentity,
} from "../../components/companion-lineup.js";
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
      // The reference viewport and its larger-display pins
      // (retarget-desktop-viewport-contract D8): 1451x790 (S = 1), 1741x948
      // (S ≈ 1.2, uncapped) and 2560x1440 (S = 1.4, the cap). The band and the
      // anchor model the shared tokens at each chrome factor.
      for (const [width, height] of [[1451, 790], [1741, 948], [2560, 1440]]) {
        const s = Math.min(1.4, Math.max(1, Math.min(height / 790, width / 1451)));
        const band = Math.max(190 * s, Math.min(400 * s, height * 0.2785));
        const actorHeight = Math.min(height * 0.62, 680 * s, height - 48 * s - band);
        const anchorWidth = actorHeight * 2 / 3;
        const column = width <= 1350 ? 216 * s : Math.max(220 * s, Math.min(330 * s, width * 0.2));
        const inset = Math.max(width * 0.06, column + 8 * s - actorHeight / 3);
        const span = companionLineupSpan(count) * anchorWidth;
        const shift = Math.max(0, span - anchorWidth - inset + 16);
        expect(inset + anchorWidth + shift - span).toBeGreaterThanOrEqual(16);
        expect(inset + anchorWidth + shift).toBeLessThan(width / 2);
        const choiceLeft = Math.max(width * 0.3, width / 2 - 280);
        const maximumSpan = (choiceLeft - 32) / anchorWidth;
        // The span cap is exact, so the only slack needed is floating point.
        expect(16 + companionLineupSpan(count, maximumSpan) * anchorWidth).toBeLessThanOrEqual(
          choiceLeft - 16 + 1e-6,
        );
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
  // reuse-lineup-person-focus D1: the membership join reads the figures the
  // lineup actually displays, matches on identity alone, and normalizes the
  // wire identity only for that comparison.
  it("joins a wire identity to the displayed figure, never to a name or an image", () => {
    const slots = figures();
    expect(slots.map((slot) => slot.identity)).toEqual([1, 2, 3, 4, 5]);
    // The join is the displayed list, bounded by the lineup's own maximum.
    expect(displayedLineup(slots)).toEqual(slots);
    expect(displayedLineup(slots.slice(0, 2))).toEqual(slots.slice(0, 2));
    expect(displayedLineup(null)).toEqual([]);
    expect(lineupSlotByIdentity(null, 1)).toBeNull();
    // A bounded string status identity joins its numeric party row, and the
    // matched slot keeps its own native identity for the speaking signal.
    expect(lineupSlotByIdentity(slots, "2")).toBe(slots[1]);
    expect(lineupSlotByIdentity(slots, 2)).toBe(slots[1]);
    expect(lineupSlotByIdentity(slots, "2").identity).toBe(2);
    expect(lineupSlotByIdentity(slots, "99")).toBeNull();
    expect(lineupSlotByIdentity(slots, null)).toBeNull();
    expect(lineupSlotByIdentity(slots, undefined)).toBeNull();
    // Identity only: an equal display name never matches, and a null portrait
    // still does.
    expect(slots[1].displayName).toBe("同行0");
    expect(lineupSlotByIdentity(slots, "同行0")).toBeNull();
    expect(slots[2].portrait).toBeNull();
    expect(lineupSlotByIdentity(slots, 3)).toBe(slots[2]);
    // A row beyond the displayed maximum is not a figure, so not a member.
    const wide = [...slots, { identity: 99, portrait: null, displayName: "同行4", isControlled: false }];
    expect(displayedLineup(wide)).toHaveLength(5);
    expect(lineupSlotByIdentity(wide, 99)).toBeNull();
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
