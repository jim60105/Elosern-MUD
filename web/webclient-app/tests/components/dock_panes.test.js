// H3 (task 5.1/4.4): table-driven unit tests for the pane-kind classifier
// (`classifyPane`) and the tab-bar badge derivation (`badgeCount`). These
// pin the classifier against the real exploration/combat frame shapes —
// including the standard `back` row that must not break the `every(...)`
// checks, and the distinction between the combat `targets` pane and the
// exploration interact-target (nav) rows.

import { describe, expect, it } from "vitest";

import { badgeCount, classifyPane } from "../../components/dock-panes.js";

describe("classifyPane (task 5.1)", () => {
  it("classifies the move outlet frame (exit rows + back row) as outlet", () => {
    // Normalized exploration move frame: `exit-*` rows with `direction`,
    // plus the standard `back` row. The `back` row must not break the
    // `every(...)` check.
    const frame = {
      items: [
        { key: "exit-north", label: "北へ", enabled: true, action_id: "explore.move", direction: "north" },
        { key: "exit-east", label: "東へ", enabled: true, action_id: "explore.move", direction: "east" },
        { key: "back", label: "戻る", navigation: true, surface: "back" },
      ],
    };
    expect(classifyPane(frame)).toBe("outlet");
  });

  it("classifies the look nav frame (explore.look rows + back row) as nav", () => {
    const frame = {
      items: [
        { key: "look-room", label: "查看房間", action_id: "explore.look" },
        { key: "entity-1", label: "老婦", action_id: "explore.look", kind: "npc" },
        { key: "back", label: "戻る", navigation: true, surface: "back" },
      ],
      title: "查看",
    };
    expect(classifyPane(frame)).toBe("nav");
  });

  it("classifies the exploration interact-target list (target-<id> nav rows) as nav, not combat targets", () => {
    // Exploration interact targets are navigation cells whose `surface` is a
    // `target-<id>` key (they open the target-affordance frame). They must
    // NOT be classified as the combat `targets` pane.
    const frame = {
      items: [
        { key: "target-1", label: "老婦", navigation: true, surface: "target-1" },
        { key: "target-2", label: "木箱", navigation: true, surface: "target-2" },
        { key: "back", label: "戻る", navigation: true, surface: "back" },
      ],
    };
    expect(classifyPane(frame)).toBe("nav");
  });

  it("classifies the combat target frame (toggle-target / selected) as targets", () => {
    // Combat AREA candidate rows carry the `toggle-target` action and a
    // client-local `selected` flag.
    const frame = {
      items: [
        { key: "target-a", label: "ゴブリン", action_id: "toggle-target", selected: true },
        { key: "target-b", label: "オーク", action_id: "toggle-target", selected: false },
      ],
    };
    expect(classifyPane(frame)).toBe("targets");
  });

  it("classifies the skill frame (open-skill) as skills", () => {
    const frame = {
      items: [
        { key: "skill-1", label: "火球術", action_id: "open-skill", cost_text: "MP 20" },
        { key: "skill-2", label: "治癒", action_id: "open-skill", cost_text: "MP 8" },
      ],
    };
    expect(classifyPane(frame)).toBe("skills");
  });

  it("classifies the scale (威力) frame as scales", () => {
    const frame = {
      items: [
        { key: "scale-1", label: "1 倍", action_id: "choose-scale", scaleChoice: true, description: "MP 10" },
        { key: "scale-2", label: "2 倍", action_id: "choose-scale", scaleChoice: true, description: "MP 16" },
      ],
    };
    expect(classifyPane(frame)).toBe("scales");
  });

  it("classifies the confirm frame (confirm-* / cancel-* rows) as confirm", () => {
    const frame = {
      items: [
        { key: "confirm-forfeit", label: "確認投降", action_id: "combat.forfeit" },
        { key: "cancel-forfeit", label: "取消", navigation: true, surface: "cancel-forfeit" },
      ],
    };
    expect(classifyPane(frame)).toBe("confirm");
  });

  it("classifies the suggestions frame (action-* cards, dismiss, back) as cards", () => {
    const frame = {
      items: [
        { key: "action-explore.talk_freeform", label: "交談", action_id: "explore.talk_freeform" },
        { key: "action-options.dismiss", label: "✕ 清除建議", action_id: "options.dismiss" },
        { key: "back", label: "戻る", navigation: true, surface: "back" },
      ],
    };
    expect(classifyPane(frame)).toBe("cards");
  });

  it("classifies the keyword frame (kw-* rows) as nav", () => {
    const frame = {
      items: [
        { key: "kw-1", label: "尋常", navigation: true, surface: "kw-1" },
        { key: "kw-2", label: "詳細", navigation: true, surface: "kw-2" },
      ],
    };
    expect(classifyPane(frame)).toBe("nav");
  });

  it("classifies the stable root frame (no action rows) as plain", () => {
    const frame = {
      items: [
        { key: "move", label: "移動", navigation: true, surface: "move" },
        { key: "look", label: "查看", navigation: true, surface: "look" },
        { key: "interact", label: "互動", navigation: true, surface: "interact" },
      ],
    };
    expect(classifyPane(frame)).toBe("plain");
  });

  it("returns plain for an empty frame", () => {
    expect(classifyPane({ items: [] })).toBe("plain");
    expect(classifyPane(null)).toBe("plain");
  });
});

describe("badgeCount (task 4.4)", () => {
  it("derives the 互動 badge from exploration.interact.length", () => {
    // Hoist the nested arrays so the V8/Node 24 parser doesn't trip on a
    // nested object-in-array-in-object literal (the session's documented quirk).
    const interact = [{ identity: "t1" }, { identity: "t2" }];
    const view = { panels: { exploration: { interact } } };
    expect(badgeCount("interact", view)).toBe(2);
  });

  it("derives the 建議 badge from suggestions.cards.length", () => {
    const cards = [{ action_code: "explore.wait" }];
    const view = { suggestions: { status: "ready", cards } };
    expect(badgeCount("suggestions", view)).toBe(1);
  });

  it("derives the 技能 badge from the flattened skill-descriptor count", () => {
    // `context_actions.skills` is an array of categories; each category owns
    // a `groups` array; each group owns a `skills` array. The badge counts
    // every skill descriptor across all categories and groups.
    // Hoist the nested `skills` array (categories → groups → skills) to
    // dodge the V8/Node 24 parser quirk on nested object-in-array literals.
    const attackSkills = [{ name: "斬撃" }, { name: "連撃" }];
    const supportSkills = [{ name: "治癒" }];
    const skills = [
      { name: "攻撃", groups: [{ skills: attackSkills }] },
      { name: "補助", groups: [{ skills: supportSkills }] },
    ];
    const view = { panels: { context_actions: { kind: "combat", skills } } };
    expect(badgeCount("skills", view)).toBe(3);
  });

  it("returns 0 for a non-combat context_actions (no skill badge)", () => {
    const skills = [];
    const view = { panels: { context_actions: { kind: "exploration", skills } } };
    expect(badgeCount("skills", view)).toBe(0);
  });

  it("returns 0 for unknown surfaces", () => {
    expect(badgeCount("unknown", { panels: {} })).toBe(0);
  });
});
