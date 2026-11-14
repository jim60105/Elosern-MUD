// landmark-rite-surfaces (design D7): the rite model, the rite arrival card,
// the rite panel and the rite backdrop, each mounted alone over synthetic
// panels. Assertions read structure, state attributes, test ids and emitted
// events; where two states differ, the rendered texts are compared rather
// than the interface wording.
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";
import RitePanels from "../../../static/webclient/js/elosern/protocol/panels/rite.js";
import { SOLO_ONLY_REASON, UNSEEN_LABEL, riteRows, ritePerformers } from "../../components/rite/rite-model.js";
import { RITE_ART_PANEL, RITE_PARTY, ritePanel, ritePanelWithArt } from "../../stories/fixtures/rite.js";

afterEach(() => {
  document.body.innerHTML = "";
});

describe("rite fixtures", () => {
  it("are valid committed rite panels", () => {
    expect(() => RitePanels.validateRitePanel(ritePanel())).not.toThrow();
    expect(() => RitePanels.validateRitePanel(ritePanelWithArt({ performers: RITE_PARTY, seen: ["drink"] }))).not.toThrow();
  });
});

describe("rite model", () => {
  it("names the performers: the first row is self, the rest by member id", () => {
    const performers = ritePerformers(ritePanel({ performers: RITE_PARTY }));
    expect(performers).toEqual([
      { id: "self", memberId: null, name: "合成旅人", self: true },
      { id: "7", memberId: 7, name: "合成同伴", self: false },
      { id: "8", memberId: 8, name: "合成學徒", self: false },
    ]);
  });

  it("a possessed companion in the first row is not self", () => {
    const [first] = ritePerformers(
      ritePanel({ performers: [{ member_id: null, name: "合成附身者", owner: false }, { member_id: 3, name: "合成主人", owner: true }] }),
    );
    expect(first).toEqual({ id: "self", memberId: null, name: "合成附身者", self: false });
  });

  it("the controlled character may pick every option; only unseen ones are unread", () => {
    const rite = ritePanel({ seen: ["bathe"] });
    const rows = riteRows(rite, ritePerformers(rite)[0]);
    expect(rows.map((row) => row.key)).toEqual(["drink", "bathe", "leave"]);
    expect(rows.slice(0, 2)).toEqual([
      { key: "drink", badge: "1", label: "俯身飲下", enabled: true, reason: null, unread: true },
      { key: "bathe", badge: "2", label: "浸入池中", enabled: true, reason: null, unread: false },
    ]);
    expect(rows[2]).toMatchObject({ key: "leave", back: true, kind: "leave", icon: "close" });
  });

  it("a companion cannot pick a solo-only option, which is not marked unread", () => {
    const rite = ritePanel({ performers: RITE_PARTY });
    const rows = riteRows(rite, ritePerformers(rite)[1]);
    expect(rows[0]).toMatchObject({ key: "drink", enabled: true, reason: null, unread: true });
    expect(rows[1]).toMatchObject({ key: "bathe", enabled: false, reason: SOLO_ONLY_REASON, unread: false });
  });
});
