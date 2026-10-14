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
import {
  artworkDescriptor,
  artworkResource,
} from "../../stories/fixtures/art_panels.js";

// One medallion's catalog value: the canonical descriptor plus its context.
function faceEntry(identity, url, faceRect) {
  return {
    artwork: artworkDescriptor({
      subject_id: `entity:${identity}`,
      generation_subject: `entity:${identity}`,
      generation_state: url ? "done" : "pending",
      attempts: url
        ? [
            {
              type: "image",
              source_id: `portrait.default:${identity}`,
              rank: 30,
              resource: artworkResource({
                resource_id: url,
                version: `${url}`.padEnd(64, "0").slice(0, 64),
                url,
                geometry: {
                  image_size: null,
                  face_rect: faceRect,
                  stage: { scale: 1, x: 0, y: 0 },
                  aspect_ratio: "3:4",
                },
              }),
            },
          ]
        : [],
      terminal: null,
    }),
    context: { name: `人物${identity}`, role: "人物" },
  };
}

const FACE = faceEntry(11, "/art/portraits/11.webp", { x: 0.3, y: 0.1, w: 0.4, h: 0.4 });
const BYSTANDER_FACE = faceEntry(21, "/art/portraits/21.webp", { x: 0.2, y: 0.05, w: 0.5, h: 0.5 });
const REPLACEMENT_FACE = faceEntry(11, "/art/portraits/11-replaced.webp", {
  x: 0.25,
  y: 0.08,
  w: 0.42,
  h: 0.42,
});

// The wire-valid decimal references the presenter supplies (schema v4).
const PORTRAITS = { 11: "11", 21: "21" };

const PENDING_FACE = faceEntry(11, null, null);

function entriesFor(options) {
  return ExplorationMenu.presenceEntries(explorationPanelFixture(options));
}

const ROOM = {
  targets: [
    { identity: 11, name: "合成職員", affordances: [AFFORDANCES.talk, AFFORDANCES.guild] },
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
      "合成職員",
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

  it("a target and a bystander medallion show the supplied face crop", () => {
    const w = mountRail({
      entries: entriesFor({ ...ROOM, portraits: PORTRAITS }),
      artPanel: {
    schema_version: 3,
    available: true,
    portrait_catalog: { 11: FACE, 21: BYSTANDER_FACE },
  },
    });
    const [clerk, , traveller] = slots(w);
    const clerkFace = clerk.get('[data-testid="presence-entry-face"]');
    expect(clerkFace.attributes("src")).toBe(FACE.artwork.attempts[0].resource.url);
    expect(clerkFace.attributes("style")).toContain("width");
    const travellerFace = traveller.get('[data-testid="presence-entry-face"]');
    expect(travellerFace.attributes("src")).toBe(BYSTANDER_FACE.artwork.attempts[0].resource.url);
    // The wolf's descriptor carries no reference at all, so its medallion
    // shows the name's first character and never a borrowed image.
    expect(slots(w)[1].find('[data-testid="presence-entry-face"]').exists()).toBe(false);
    expect(slots(w)[1].get('[data-testid="presence-entry-initial"]').text()).toBe("霧");
    // Object lozenges are never portrait-bearing: the gem stands in for the
    // medallion entirely.
    expect(slots(w)[3].find('[data-testid="presence-entry-face"]').exists()).toBe(false);
    expect(slots(w)[3].find('[data-testid="presence-entry-initial"]').exists()).toBe(false);
    expect(slots(w)[3].find(".presence-rail__gem").exists()).toBe(true);
  });

  it("a pending, unknown or absent reference shows the initial, never a built key", () => {
    const panel = explorationPanelFixture({
      targets: [{ identity: 11, name: "合成職員", affordances: [AFFORDANCES.talk] }],
      entities: [
        { identity: 21, name: "旅人" },
        { identity: 22, name: "無圖者" },
      ],
      portraits: { 11: "11", 21: "999" },
    });
    const w = mountRail({
      entries: ExplorationMenu.presenceEntries(panel),
      artPanel: {
        portrait_catalog: {
          // A catalogued but unfinished portrait: no URL, so no image.
          11: PENDING_FACE,
          // The bystander's reference names no entry at all.
          21: undefined,
        },
      },
    });
    expect(slots(w).map((slot) => slot.attributes("data-entry-key"))).toEqual([
      "target-11",
      "entity-21",
      "entity-22",
    ]);
    for (const [index, initial] of [
      [0, "合"],
      [1, "旅"],
      [2, "無"],
    ]) {
      expect(slots(w)[index].find('[data-testid="presence-entry-face"]').exists()).toBe(false);
      expect(slots(w)[index].get('[data-testid="presence-entry-initial"]').text()).toBe(initial);
    }
  });

  it("a failed image keeps the initial and a newer committed URL recovers in place", async () => {
    const entries = entriesFor({ ...ROOM, portraits: PORTRAITS });
    const w = mountRail({ entries, artPanel: { schema_version: 3, available: true, portrait_catalog: { 11: FACE } } });
    await slots(w)[0].get('[data-testid="presence-entry-face"]').trigger("error");
    expect(slots(w)[0].find('[data-testid="presence-entry-face"]').exists()).toBe(false);
    expect(slots(w)[0].get('[data-testid="presence-entry-initial"]').text()).toBe("合");
    // A newer committed catalog entry replaces the failed URL: the same rail
    // (never reopened, never re-mounted) renders the supplied crop again.
    await w.setProps({
      artPanel: { schema_version: 3, available: true, portrait_catalog: { 11: REPLACEMENT_FACE } },
    });
    const recovered = slots(w)[0].get('[data-testid="presence-entry-face"]');
    expect(recovered.attributes("src")).toBe(REPLACEMENT_FACE.artwork.attempts[0].resource.url);
    expect(w.findAll('[data-testid="presence-rail"]')).toHaveLength(1);
  });

  it("the same failed URL is not retried automatically", async () => {
    const entries = entriesFor({ ...ROOM, portraits: PORTRAITS });
    const w = mountRail({ entries, artPanel: { schema_version: 3, available: true, portrait_catalog: { 11: FACE } } });
    await slots(w)[0].get('[data-testid="presence-entry-face"]').trigger("error");
    // A re-committed panel still naming the failed URL stays on the initial:
    // there is no retry policy, only a genuinely changed URL.
    await w.setProps({
      artPanel: { schema_version: 3, available: true, portrait_catalog: { 11: { ...FACE } } },
    });
    expect(slots(w)[0].find('[data-testid="presence-entry-face"]').exists()).toBe(false);
    expect(slots(w)[0].get('[data-testid="presence-entry-initial"]').text()).toBe("合");
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
      [{ lead: "合成職員", text: "交談／公會服務", tone: "normal" }],
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
