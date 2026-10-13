// exploration-presence-rail (task 2.1): PresenceRail. The entry order and
// kinds, the portrait face crop and the initial fallback, the six-slot limit
// with `＋N`, the activation intent for every kind (the store turns a
// bystander's or an object's into its existing look payload), the readout
// feed, the keyboard composite, and an empty room rendering nothing.
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";
import PresenceRail from "../../components/PresenceRail.vue";
import ExplorationMenu from "../../lib/exploration_menu.js";
import { explorationPanelFixture, AFFORDANCES } from "../../stories/fixtures/scene_overview.js";

const FACE = {
  status: "done",
  url: "/art/portraits/npc_11.webp",
  face_rect: { x: 0.3, y: 0.1, w: 0.4, h: 0.4 },
};

function entriesFor(options) {
  return ExplorationMenu.presenceEntries(explorationPanelFixture(options));
}

const ROOM = {
  targets: [
    { identity: 11, name: "葛里安‧衛登", affordances: [AFFORDANCES.talk, AFFORDANCES.guild] },
    { identity: 12, name: "霧狼", affordances: [AFFORDANCES.engage] },
  ],
  entities: [{ identity: 21, name: "旅人" }],
  objects: [
    { identity: 31, name: "任務板" },
    { identity: 32, name: "木箱" },
  ],
};

describe("PresenceRail", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountRail(props) {
    wrapper = mount(PresenceRail, { attachTo: document.body, props: { motionLevel: "off", ...props } });
    return wrapper;
  }

  const slots = (w) => w.findAll('[data-testid="presence-entry"]');
  const rail = (w) => w.get('[data-testid="presence-rail"]');

  it("lists targets, bystanders, a separator, then objects, each with a name plate", () => {
    const w = mountRail({ entries: entriesFor(ROOM) });
    expect(slots(w).map((slot) => [slot.attributes("data-entry-key"), slot.attributes("data-presence")])).toEqual([
      ["target-11", "target"],
      ["target-12", "target"],
      ["entity-21", "bystander"],
      ["object-31", "object"],
      ["object-32", "object"],
    ]);
    expect(slots(w).map((slot) => slot.get('[data-testid="presence-entry-name"]').text())).toEqual([
      "葛里安‧衛登",
      "霧狼",
      "旅人",
      "任務板",
      "木箱",
    ]);
    const order = Array.from(
      rail(w).element.querySelectorAll('[data-testid="presence-entry"], [data-testid="presence-rail-separator"]'),
    ).map((el) => el.getAttribute("data-testid"));
    expect(order.indexOf("presence-rail-separator")).toBe(3);
    expect(order.filter((id) => id === "presence-rail-separator")).toHaveLength(1);
    expect(w.find(".presence-rail__medal--dashed").exists()).toBe(true);
    expect(w.findAll(".presence-rail__gem")).toHaveLength(2);
  });

  it("a medallion shows the face crop when the portrait resolves, else the first character", () => {
    const entries = entriesFor(ROOM).map((entry) =>
      entry.key === "target-11" ? { ...entry, portraitRef: "npc_11" } : entry,
    );
    const w = mountRail({ entries, artPanel: { portrait_catalog: { npc_11: FACE, npc_12: { status: "pending", url: null } } } });
    const [clerk, wolf] = slots(w);
    const face = clerk.get('[data-testid="presence-entry-face"]');
    expect(face.attributes("src")).toBe(FACE.url);
    expect(face.attributes("style")).toContain("width");
    expect(wolf.find('[data-testid="presence-entry-face"]').exists()).toBe(false);
    expect(wolf.get('[data-testid="presence-entry-initial"]').text()).toBe("霧");
  });

  it("seven entries show five and a ＋2 slot", () => {
    const crowd = {
      targets: [1, 2, 3, 4, 5].map((n) => ({ identity: n, name: `旅人${n}`, affordances: [] })),
      objects: [
        { identity: 31, name: "任務板" },
        { identity: 32, name: "木箱" },
      ],
    };
    const w = mountRail({ entries: entriesFor(crowd) });
    expect(slots(w)).toHaveLength(6);
    const more = slots(w)[5];
    expect(more.attributes("data-entry-key")).toBe("presence-more");
    expect(more.text()).toContain("＋2");
  });

  it("an empty room renders no rail and no placeholder", () => {
    const w = mountRail({ entries: [] });
    expect(w.find('[data-testid="presence-rail"]').exists()).toBe(false);
    expect(w.html()).not.toContain("presence");
  });

  it("every kind emits its key on a click: the store decides the payload", async () => {
    const w = mountRail({ entries: entriesFor(ROOM) });
    await slots(w)[2].trigger("click");
    await slots(w)[3].trigger("click");
    await slots(w)[0].trigger("click");
    expect(w.emitted("activate")).toEqual([["entity-21"], ["object-31"], ["target-11"]]);
    // The bystander's and the object's entries carry the old look rows'
    // payloads verbatim.
    const byKey = Object.fromEntries(entriesFor(ROOM).map((entry) => [entry.key, entry]));
    expect(byKey["entity-21"].payload).toEqual({ target_id: 21 });
    expect(byKey["object-31"].payload).toEqual({ target_id: 31 });
    expect(byKey["object-31"].actionId).toBe("explore.look");
  });

  it("is one tab stop: ←/→ wrap, Enter activates, a held repeat never does", async () => {
    const w = mountRail({ entries: entriesFor(ROOM) });
    expect(w.findAll("[tabindex]")).toHaveLength(1);
    rail(w).element.focus();
    const key = async (name, init = {}) => {
      rail(w).element.dispatchEvent(new KeyboardEvent("keydown", { key: name, bubbles: true, cancelable: true, ...init }));
      await nextTick();
    };
    await key("ArrowRight");
    expect(document.getElementById(rail(w).attributes("aria-activedescendant")).dataset.entryKey).toBe("target-12");
    await key("ArrowLeft");
    await key("ArrowLeft");
    expect(document.getElementById(rail(w).attributes("aria-activedescendant")).dataset.entryKey).toBe("object-32");
    await key("Enter", { repeat: true });
    expect(w.emitted("activate")).toBeUndefined();
    await key("Enter");
    expect(w.emitted("activate")).toEqual([["object-32"]]);
  });

  it("hover and focus feed the readout: the name over the affordance summary, or 查看", async () => {
    const w = mountRail({ entries: entriesFor(ROOM) });
    await slots(w)[0].trigger("mouseenter");
    await slots(w)[3].trigger("mouseenter");
    await slots(w)[3].trigger("mouseleave");
    expect(w.emitted("hover")).toEqual([
      [{ lead: "葛里安‧衛登", text: "交談／公會服務", tone: "normal" }],
      [{ lead: "任務板", text: "查看", tone: "normal" }],
      [null],
    ]);
  });

  it("focusEntry focuses the rail on the opener's slot", async () => {
    const w = mountRail({ entries: entriesFor(ROOM) });
    expect(w.vm.focusEntry("object-31")).toBe(true);
    await nextTick();
    expect(document.activeElement).toBe(rail(w).element);
    expect(document.getElementById(rail(w).attributes("aria-activedescendant")).dataset.entryKey).toBe("object-31");
    expect(w.vm.focusEntry("target-99")).toBe(false);
  });

  it("Tab reports its direction to the host", async () => {
    const w = mountRail({ entries: entriesFor(ROOM) });
    rail(w).element.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", shiftKey: true, bubbles: true }));
    expect(w.emitted("tab")[0][0].backward).toBe(true);
  });
});
