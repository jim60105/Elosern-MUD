// npc-interaction-service-card (slice U): the interaction card's pure row
// model. `verbMenuFor` composes the fixed common slots, the deterministic
// conditional order and the contextual services; `verbCardRows` turns them
// into card rows with digit badges that stop at position 9, their group
// identity and their inline reasons. No DOM, no store: the producers alone.
import { describe, expect, it } from "vitest";

import ExplorationMenu from "../lib/exploration_menu.js";
import { BACK_ROW, overflowCardRows, verbCardRows } from "../composables/use-person-focus.js";

function action(action_id, label, extra = {}) {
  return { kind: "action", action_id, label, enabled: true, disabled_reason: null, ...extra };
}

function service(key, label, section, extra = {}) {
  return {
    key,
    label,
    enabled: true,
    disabled_reason: null,
    route: { kind: "services", npc_id: 7, section },
    ...extra,
  };
}

function target(overrides = {}) {
  return {
    identity: 7,
    display_name: "店長",
    portrait_ref: null,
    services: { state: "none", entries: [] },
    affordances: [action("explore.talk_open", "交談")],
    ...overrides,
  };
}

function card(targetRow) {
  const model = ExplorationMenu.buildMenus({ interact: [targetRow] }, {});
  return ExplorationMenu.verbMenuFor(model, targetRow).items;
}

describe("the interaction card's row model", () => {
  it("keeps 交談 at slot 1 and 查看 at slot 2 for every target", () => {
    const rows = card(target());
    expect(rows.slice(0, 2).map((row) => row.key)).toEqual(["talk-open", "look-target"]);
    expect(rows.slice(0, 2).map((row) => row.group)).toEqual(["common", "common"]);
    expect(rows[1].actionId).toBe("explore.look");
    expect(rows[1].payload).toEqual({ target_id: 7 });
  });

  it("keeps both common slots when they are unavailable, with their reasons", () => {
    const rows = card(
      target({
        affordances: [
          action("explore.talk_open", "交談", {
            enabled: false,
            disabled_reason: { code: "busy", message: "守衛正在值勤。" },
          }),
        ],
      }),
    );
    expect(rows[0]).toMatchObject({ key: "talk-open", enabled: false, actionId: null, payload: null });
    expect(rows[0].disabledReason).toMatchObject({ code: "busy", message: "守衛正在值勤。" });
    // 查看 keeps its slot whatever talk did.
    expect(rows[1].key).toBe("look-target");
  });

  it("synthesizes a never-callable 交談 for a target with no talk descriptor", () => {
    const rows = card(target({ affordances: [action("explore.engage", "戰鬥")] }));
    expect(rows.map((row) => row.key)).toEqual(["talk-open", "look-target", "engage", "back"]);
    expect(rows[0]).toMatchObject({ enabled: false, actionId: null, payload: null });
    expect(rows[0].disabledReason.code).toBe("not_conversable");
  });

  it("orders the conditional rows invite, leave, possess, deliver, editor", () => {
    const rows = card(
      target({
        affordances: [
          { kind: "navigate", surface: "npc_persona", label: "編輯人物設定", enabled: true, disabled_reason: null },
          action("explore.deliver", "交付", { params: { npc_id: 7, item_key: "herb" } }),
          action("explore.possess", "附身"),
          action("explore.party_leave", "解散"),
          action("explore.party_invite", "邀請"),
        ],
      }),
    );
    expect(rows.map((row) => row.key)).toEqual([
      "talk-open",
      "look-target",
      "party-invite",
      "party-leave",
      "possess",
      "deliver",
      "service-npc_persona",
      "back",
    ]);
    expect(rows.slice(2, 7).every((row) => row.group === "conditional")).toBe(true);
  });

  it("keeps the server's service order and each entry's own key and route", () => {
    const rows = card(
      target({
        services: {
          state: "ready",
          entries: [service("guild.board", "查看委託看板", "board"), service("shop", "交易", "shop")],
        },
      }),
    );
    const services = rows.filter((row) => row.group === "services");
    expect(services.map((row) => row.key)).toEqual(["service-guild.board", "service-shop"]);
    expect(services.map((row) => row.serviceRoute.section)).toEqual(["board", "shop"]);
    expect(services.every((row) => row.actionId === null && row.payload === null)).toBe(true);
  });

  it("keeps a disabled service row in place with its own key and reason", () => {
    const rows = card(
      target({
        services: {
          state: "ready",
          entries: [
            service("shop", "交易", "shop"),
            service("guild.board", "查看委託看板", "board", {
              enabled: false,
              disabled_reason: { code: "paused", message: "看板維護中。" },
            }),
          ],
        },
      }),
    );
    const services = rows.filter((row) => row.group === "services");
    expect(services.map((row) => row.key)).toEqual(["service-shop", "service-guild.board"]);
    expect(services[1].enabled).toBe(false);
    expect(services[1].disabledReason.message).toBe("看板維護中。");
  });

  it("keeps the unreadable services state as one disabled sentence row", () => {
    const rows = card(target({ services: { state: "unreadable", entries: [] } }));
    const services = rows.filter((row) => row.group === "services");
    expect(services).toHaveLength(1);
    expect(services[0].key).toBe("services-unreadable");
    expect(services[0].enabled).toBe(false);
    expect(services[0].description).toBe("服務資訊暫時無法讀取。");
  });

  it("omits the services group when the projection is none", () => {
    expect(card(target()).some((row) => row.group === "services")).toBe(false);
  });

  it("carries the trailing unnumbered return", () => {
    const rows = card(target());
    expect(rows.at(-1).key).toBe("back");
    expect(rows.at(-1).goBack).toBe(true);
    expect(rows.at(-1).group).toBeUndefined();
  });
});

describe("the card rows", () => {
  const many = Array.from({ length: 12 }, (_, index) => ({
    key: `row-${index + 1}`,
    label: `列 ${index + 1}`,
    enabled: true,
    group: "services",
    groupLabel: "服務",
  }));

  it("badges only positions 1 through 9 and appends the return row", () => {
    const rows = verbCardRows(many);
    expect(rows).toHaveLength(13);
    expect(rows.slice(0, 9).map((row) => row.badge)).toEqual([
      "1",
      "2",
      "3",
      "4",
      "5",
      "6",
      "7",
      "8",
      "9",
    ]);
    // No alternate numbering scheme past the ninth row.
    expect(rows.slice(9, 12).map((row) => row.badge)).toEqual([null, null, null]);
    expect(rows.at(-1)).toBe(BACK_ROW);
  });

  it("carries each row's group identity and heading", () => {
    const rows = verbCardRows(card(target({
      services: { state: "ready", entries: [service("shop", "交易", "shop")] },
    })));
    const byKey = Object.fromEntries(rows.map((row) => [row.key, row]));
    expect(byKey["talk-open"]).toMatchObject({ group: "common", groupLabel: "一般" });
    expect(byKey["look-target"]).toMatchObject({ group: "common", groupLabel: "一般" });
    expect(byKey["service-shop"]).toMatchObject({ group: "services", groupLabel: "服務" });
    expect(byKey.back.group).toBeUndefined();
  });

  it("drops the builder's own back row and keeps a disabled row's reason", () => {
    const rows = verbCardRows([
      { key: "talk-open", label: "交談", enabled: false, disabledReason: { code: "x", message: "不可。" } },
      { key: "back", goBack: true },
    ]);
    expect(rows.map((row) => row.key)).toEqual(["talk-open", "back"]);
    expect(rows[0].enabled).toBe(false);
    expect(rows[0].reason).toBe("不可。");
  });

  it("badges the overflow card's rows the same way", () => {
    // Six slots show; everything past the fifth folds into the overflow card.
    const entries = Array.from({ length: 15 }, (_, index) => ({
      key: `entry-${index + 1}`,
      label: `項目 ${index + 1}`,
      presence: "bystander",
    }));
    const rows = overflowCardRows(entries);
    expect(rows.slice(0, 9).map((row) => row.badge)).toEqual([
      "1",
      "2",
      "3",
      "4",
      "5",
      "6",
      "7",
      "8",
      "9",
    ]);
    // Ten folded entries: the tenth has no digit, and the return keeps ✕.
    expect(rows[9].badge).toBe(null);
    expect(rows.at(-1)).toBe(BACK_ROW);
  });
});
