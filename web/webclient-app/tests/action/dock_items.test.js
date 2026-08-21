import { describe, expect, it } from "vitest";
import {
  actionIntentForItem,
  disabledReasonText,
  dockItemKeys,
} from "../../components/dock-items.js";

const ACTION = {
  action_id: "explore.move",
  label: "走往北岸大道",
  params: { exit_ref: "north", current_node: 42 },
  freeform: false,
  navigation: false,
  enabled: true,
  disabled_reason: null,
};

const NAVIGATION = {
  surface: "guild",
  label: "公會",
  navigation: true,
  enabled: true,
  disabled_reason: null,
};

const TARGET = { identity: "e1", label: "灰袍盜賊", enabled: true, disabled_reason: null };

describe("dockItems (B2 action-dock family)", () => {
  it("derives the preserved action- keys from action entries", () => {
    expect(dockItemKeys([ACTION])).toEqual(["action-explore.move"]);
  });

  it("derives the preserved target- keys from target entries", () => {
    expect(dockItemKeys([TARGET])).toEqual(["target-e1"]);
  });

  it("derives action- keys for navigation surfaces", () => {
    expect(dockItemKeys([NAVIGATION])).toEqual(["action-guild"]);
  });

  it("disambiguates duplicate keys by positional suffix, deterministically", () => {
    const first = { ...ACTION };
    const second = {
      ...ACTION,
      label: "走往南門",
      params: { exit_ref: "south", current_node: 43 },
    };
    const keys = dockItemKeys([first, second]);
    expect(keys).toEqual(["action-explore.move", "action-explore.move-2"]);
    expect(dockItemKeys([second, first])).toEqual([
      "action-explore.move",
      "action-explore.move-2",
    ]);
  });

  it("maps an action entry to the exact OOB action intent without aliasing", () => {
    const intent = actionIntentForItem(ACTION);
    expect(intent).toEqual({
      action_id: "explore.move",
      payload: { exit_ref: "north", current_node: 42 },
    });
    intent.payload.current_node = 43;
    expect(ACTION.params.current_node).toBe(42);
  });

  it("emits no OOB intent for local navigation and target entries", () => {
    expect(actionIntentForItem(NAVIGATION)).toBeNull();
    expect(actionIntentForItem(TARGET)).toBeNull();
  });

  it("surfaces the server-authored disabled reason text", () => {
    expect(disabledReasonText(ACTION)).toBeNull();
    expect(
      disabledReasonText({
        ...ACTION,
        enabled: false,
        disabled_reason: { code: "recovery", message: "正在調息，無法行動" },
      }),
    ).toBe("正在調息，無法行動");
    expect(
      disabledReasonText({ ...ACTION, enabled: false, disabled_reason: null }),
    ).toBeNull();
  });

  it("rejects items that match no preserved shape", () => {
    expect(() => dockItemKeys([{ label: "x" }])).toThrow(TypeError);
  });
});
