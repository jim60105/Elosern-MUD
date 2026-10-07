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

  it("covers every severity and provenance without filtering condition data", () => {
    for (const severity of ["beneficial", "informational", "warning", "harmful", "critical"]) {
      for (const kind of ["equipment", "non_equipment", "mixed", "unknown"]) {
        const condition = {
          code: "t_warning", label: "合成警告", severity,
          provenance: {
            kind,
            equipment_sources: ["equipment", "mixed"].includes(kind)
              ? [{ item_key: "t_a", label: "合成護符" }] : [],
          },
        };
        expect(isVitalsVisible({
          mode: "exploration", resources: fullResources, conditions: [condition], lowHp: false,
        })).toBe(["warning", "harmful", "critical"].includes(severity) && kind !== "equipment");
      }
    }
  });

  it("adopts same-code source changes only from accepted revisions and preserves mode gates", () => {
    setActivePinia(createPinia());
    const store = useElosernStore();
    store.beginTransport(1);
    store.setConnected(true);
    store.setLoggedIn(true);
    const condition = (kind) => ({
      code: "t_warning", label: "合成警告", severity: "warning",
      provenance: { kind, equipment_sources: [{ item_key: "t_a", label: "合成護符" }] },
    });
    const message = (revision, kind, mode = "exploration", epoch = fx.EPOCH_A) => fx.snapshot({
      revision, presentation_epoch: epoch, mode,
      panels: { status: fx.statusPanel({ resources: fullResources, conditions: [condition(kind)] }) },
    });
    expect(store.receive(1, "ui_snapshot", [message(1, "equipment")], {}).accepted).toBe(true);
    expect(store.view.vitals.visible).toBe(false);
    expect(store.receive(1, "ui_update", [message(2, "mixed")], {}).accepted).toBe(true);
    expect(store.view.vitals.visible).toBe(true);
    expect(store.receive(1, "ui_update", [message(3, "equipment")], {}).accepted).toBe(true);
    expect(store.view.vitals.visible).toBe(false);
    expect(store.receive(1, "ui_update", [message(2, "mixed")], {}).accepted).toBe(false);
    expect(store.view.vitals.visible).toBe(false);
    for (const [revision, mode] of [[4, "dialogue"], [5, "creation"], [6, "exploration"]]) {
      expect(store.receive(1, "ui_update", [message(revision, "mixed", mode)], {}).accepted).toBe(true);
      // The store carries data attention; the mounted shell owns mode gates.
      expect(store.view.vitals.visible).toBe(true);
    }
    store.beginTransport(2);
    expect(store.receive(2, "ui_snapshot", [message(1, "equipment", "exploration", fx.EPOCH_B)], {}).accepted).toBe(true);
    expect(store.receive(2, "ui_update", [message(99, "mixed")], {}).accepted).toBe(false);
    expect(store.view.vitals.visible).toBe(false);
    const unavailable = fx.snapshot({ revision: 2, presentation_epoch: fx.EPOCH_B, mode: "combat" });
    unavailable.panels.status = {
      schema_version: 3, available: false, reason: { code: "status_unavailable", message: "暫無資料" },
    };
    expect(store.receive(2, "ui_update", [unavailable], {}).accepted).toBe(true);
    expect(store.view.vitals.visible).toBe(false);
  });

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
        conditions: [{ code: "poison", label: "中毒", provenance: { kind: "non_equipment", equipment_sources: [] }, severity: "harmful" }],
        lowHp: false,
      }),
    ).toBe(true);
  });

  it("one warning condition at full vitals shows the island", () => {
    expect(
      isVitalsVisible({
        mode: "exploration",
        resources: fullResources,
        conditions: [{ code: "fatigued", label: "疲憊", provenance: { kind: "non_equipment", equipment_sources: [] }, severity: "warning" }],
        lowHp: false,
      }),
    ).toBe(true);
  });

  it("one critical condition at full vitals shows the island", () => {
    expect(
      isVitalsVisible({
        mode: "exploration",
        resources: fullResources,
        conditions: [{ code: "dying", label: "瀕死", provenance: { kind: "non_equipment", equipment_sources: [] }, severity: "critical" }],
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
          { code: "defense_instinct_defense_bonus", label: "防禦本能", provenance: { kind: "non_equipment", equipment_sources: [] }, severity: "beneficial" },
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
        conditions: [{ code: "info_only", label: "提示", provenance: { kind: "non_equipment", equipment_sources: [] }, severity: "informational" }],
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
          schema_version: 3,
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
