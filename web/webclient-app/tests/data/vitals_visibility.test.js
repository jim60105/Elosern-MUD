import { describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { isVitalsVisible } from "../../components/vitals.js";
import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "../store/protocol_fixtures.js";

describe("isVitalsVisible (webclient-retire-redundant-hud, design D2)", () => {
  const fullResources = {
    hp: { current: 100, maximum: 100 },
    mp: { current: 50, maximum: 50 },
    sp: { current: 40, maximum: 40 },
  };

  it("full vitals with no condition in exploration, dialogue, and combat", () => {
    expect(
      isVitalsVisible({
        mode: "exploration",
        resources: fullResources,
        conditions: [],
        lowHp: false,
      }),
    ).toBe(false);

    expect(
      isVitalsVisible({
        mode: "dialogue",
        resources: fullResources,
        conditions: [],
        lowHp: false,
      }),
    ).toBe(false);

    expect(
      isVitalsVisible({
        mode: "combat",
        resources: fullResources,
        conditions: [],
        lowHp: false,
      }),
    ).toBe(true);
  });

  it("mp below max shows the island", () => {
    const injuredMp = {
      ...fullResources,
      mp: { current: 49, maximum: 50 },
    };
    expect(
      isVitalsVisible({
        mode: "exploration",
        resources: injuredMp,
        conditions: [],
        lowHp: false,
      }),
    ).toBe(true);
  });

  it("one harmful condition at full vitals shows the island", () => {
    expect(
      isVitalsVisible({
        mode: "exploration",
        resources: fullResources,
        conditions: [{ code: "poison", label: "中毒", severity: "harmful" }],
        lowHp: false,
      }),
    ).toBe(true);
  });

  it("one warning condition at full vitals shows the island", () => {
    expect(
      isVitalsVisible({
        mode: "exploration",
        resources: fullResources,
        conditions: [{ code: "fatigued", label: "疲憊", severity: "warning" }],
        lowHp: false,
      }),
    ).toBe(true);
  });

  it("one critical condition at full vitals shows the island", () => {
    expect(
      isVitalsVisible({
        mode: "exploration",
        resources: fullResources,
        conditions: [{ code: "dying", label: "瀕死", severity: "critical" }],
        lowHp: false,
      }),
    ).toBe(true);
  });

  it("only beneficial conditions at full vitals in exploration leave the island hidden", () => {
    expect(
      isVitalsVisible({
        mode: "exploration",
        resources: fullResources,
        conditions: [
          { code: "defense_instinct_defense_bonus", label: "防禦本能", severity: "beneficial" },
        ],
        lowHp: false,
      }),
    ).toBe(false);
  });

  it("only informational conditions, or a condition with a missing severity, at full vitals in exploration leave the island hidden", () => {
    expect(
      isVitalsVisible({
        mode: "exploration",
        resources: fullResources,
        conditions: [{ code: "info_only", label: "提示", severity: "informational" }],
        lowHp: false,
      }),
    ).toBe(false);

    expect(
      isVitalsVisible({
        mode: "exploration",
        resources: fullResources,
        conditions: [{ code: "unknown_sev", label: "未知" }],
        lowHp: false,
      }),
    ).toBe(false);
  });

  it("lowHp forces the island visible", () => {
    expect(
      isVitalsVisible({
        mode: "exploration",
        resources: fullResources,
        conditions: [],
        lowHp: true,
      }),
    ).toBe(true);
  });

  it("a missing gauge and a string current (neither counts)", () => {
    expect(
      isVitalsVisible({
        mode: "exploration",
        resources: {
          hp: { current: "80", maximum: 100 },
        },
        conditions: [],
        lowHp: false,
      }),
    ).toBe(false);

    expect(
      isVitalsVisible({
        mode: "exploration",
        resources: {},
        conditions: [],
        lowHp: false,
      }),
    ).toBe(false);
  });

  it("the store slice derives visible through statusPanel snapshot fixtures", () => {
    setActivePinia(createPinia());
    const store = useElosernStore();
    store.beginTransport(1);
    store.setConnected(true);
    store.setLoggedIn(true);

    // Default statusPanel() fixture has hp 80/100 -> visible is true
    const r1 = store.receive(1, "ui_snapshot", [fx.snapshot({
      revision: 1,
      mode: "exploration",
      panels: { status: fx.statusPanel() },
    })], {});
    expect(r1.accepted).toBe(true);
    expect(store.view.vitals.visible).toBe(true);

    // Full vitals with no conditions in exploration -> visible is false
    const r2 = store.receive(1, "ui_snapshot", [fx.snapshot({
      revision: 2,
      mode: "exploration",
      panels: {
        status: fx.statusPanel({
          resources: fullResources,
          conditions: [],
        }),
      },
    })], {});
    expect(r2.accepted).toBe(true);
    expect(store.view.vitals.visible).toBe(false);

    // Same full vitals in combat -> visible is true
    const r3 = store.receive(1, "ui_snapshot", [fx.snapshot({
      revision: 3,
      mode: "combat",
      panels: {
        status: fx.statusPanel({
          resources: fullResources,
          conditions: [],
        }),
      },
    })], {});
    expect(r3.accepted).toBe(true);
    expect(store.view.vitals.visible).toBe(true);

    // Unavailable status panel -> visible is false
    const unavailableSnapshot = {
      protocol_version: 1,
      presentation_epoch: fx.EPOCH_A,
      revision: 4,
      mode: "exploration",
      panels: {
        status: {
          schema_version: 2,
          available: false,
          reason: { code: "status_unavailable", message: "無法顯示" },
        },
      },
      layout_version: 1,
      server_time: fx.serverTime(),
    };
    const r4 = store.receive(1, "ui_snapshot", [unavailableSnapshot], {});
    expect(r4.accepted).toBe(true);
    expect(store.view.vitals.visible).toBe(false);
  });
});
