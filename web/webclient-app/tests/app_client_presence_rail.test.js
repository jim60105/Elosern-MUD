// exploration-presence-rail (tasks 2.2, 3.2, 3.3): the AppClient wiring of
// the presence rail and the person focus. The rail on the stage floor, the
// verb card in the `choices` anchor (no request, no router frame), the
// cockpit stepping away around it (the command panel inert and dimmed, the
// map anchor away, the rail hidden), the standee and the speaker line, the
// card closing on Escape, on 返回, on 查看, on a departure (with the readout
// flash), and on a move, focus returning to the opener, the one StageActor
// element surviving the 交談 commit, the overflow card, the rail digits, the
// Tab chain compass → rail → footer, and the compass walk stopping when a
// card opens.
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../AppClient.vue";
import { useElosernStore } from "../stores/elosern.js";
import { ART_PANEL_SAMPLE, ART_PANEL_UNAVAILABLE_SAMPLE } from "../stories/fixtures.js";
import {
  fixtureDigest,
  artworkDescriptor,
  artworkResource,
} from "../stories/fixtures/art_panels.js";
import * as fx from "./store/protocol_fixtures.js";

// The exploration panel is schema v4: its interact targets and look entities
// carry a nullable `portrait_ref` that the presenter fills only for an
// admitted catalog image. These fixtures commit exactly those accepted
// snapshots/updates, so the medallion face crops and the non-party standee
// image are asserted end to end through the store.
const CLERK = {
  identity: 7,
  display_name: "店長",
  portrait_ref: null,
  affordances: [
    { kind: "action", action_id: "explore.talk_open", label: "交談", enabled: true, disabled_reason: null },
    { kind: "navigate", surface: "guild", label: "公會服務", enabled: true, disabled_reason: null },
  ],
};

// One committed catalog value in the exact accepted shape: the canonical
// descriptor (with the target's own face crop and stage placement) plus its
// display context. A null `url` models a subject with no real candidate.
function faceEntry(identity, url, faceRect, name, role) {
  return {
    artwork: artworkDescriptor({
      subject_id: identity,
      generation_subject: identity,
      generation_state: url ? "done" : "pending",
      attempts: url
        ? [
            {
              type: "image",
              source_id: `portrait.default:${identity}`,
              rank: 30,
              resource: artworkResource({
                resource_id: url,
                version: fixtureDigest(url),
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
    }),
    context: { name, role },
  };
}

const CLERK_FACE = faceEntry(
  "npc_7",
  "/art/portraits/npc_7.webp",
  { x: 0.25, y: 0.06, w: 0.5, h: 0.5 },
  "店長",
  "對話對象",
);

const CLERK_FACE_REPLACED = faceEntry(
  "npc_7",
  "/art/portraits/npc_7_replaced.webp",
  { x: 0.22, y: 0.04, w: 0.52, h: 0.52 },
  "店長",
  "對話對象",
);

const BYSTANDER_FACE = faceEntry(
  "npc_8",
  "/art/portraits/npc_8.webp",
  { x: 0.3, y: 0.1, w: 0.4, h: 0.4 },
  "旅人",
  "人物",
);

// The bystander look entity (no interact descriptor): the rail's dashed
// medallion.
const TRAVELLER = { identity: 8, display_name: "旅人", kind: "character", portrait_ref: null };

function artPanel(extra = null) {
  if (extra === null) {
    return ART_PANEL_SAMPLE;
  }
  return {
    ...ART_PANEL_SAMPLE,
    portrait_catalog: { ...ART_PANEL_SAMPLE.portrait_catalog, ...extra },
  };
}


describe("AppClient presence rail and person focus (exploration-presence-rail)", () => {
  let store;
  let wrapper;
  let sender;
  let revision;

  function exploration(overrides = {}) {
    return fx.explorationPanel({ interact: [CLERK], ...overrides });
  }

  async function mountWith(panel = exploration(), art = artPanel()) {
    wrapper = mount(AppClient, { attachTo: document.body });
    store.beginTransport(1);
    store.setConnected(true);
    store.setLoggedIn(true);
    revision = 1;
    const result = store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          revision,
          panels: {
            status: fx.statusPanel(),
            exploration: panel,
            local_map: fx.localMapPanel(),
            context_actions: fx.explorationActions(),
            art,
          },
        }),
      ],
      {},
    );
    expect(result.accepted).toBe(true);
    await settle();
  }

  async function settle() {
    for (let i = 0; i < 4; i += 1) {
      await nextTick();
    }
  }

  async function commit(panels, extra = {}) {
    revision += 1;
    const result = store.receive(1, "ui_update", [fx.update({ revision, panels, ...extra })], {});
    expect(result.accepted).toBe(true);
    await settle();
  }

  const rail = () => wrapper.find('[data-anchor="presence"] [data-testid="presence-rail"]');
  const entry = (key) => wrapper.get(`[data-anchor="presence"] [data-entry-key="${key}"]`);
  const card = () => wrapper.find('[data-anchor="choices"] [data-testid="presence-card"]');
  const cardRows = () => card().findAll('[role="menuitem"]');
  const standee = () => wrapper.find('[data-testid="anchor-actor-right"] [data-testid="stage-actor"]');
  const stage = () => wrapper.get('[data-testid="elosern-stage"]');
  const readoutText = () => wrapper.get('[data-testid="exploration-readout-text"]').text();

  function key(element, name, init = {}) {
    element.dispatchEvent(new KeyboardEvent("keydown", { key: name, bubbles: true, cancelable: true, ...init }));
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  it("stands the rail on the stage floor with the host's medallion and the object's lozenge", async () => {
    await mountWith();
    expect(rail().exists()).toBe(true);
    expect(rail().findAll('[data-testid="presence-entry"]').map((el) => el.attributes("data-entry-key"))).toEqual([
      "target-7",
      "object-3",
    ]);
    expect(entry("target-7").get('[data-testid="presence-entry-initial"]').text()).toBe("店");
    expect(wrapper.find('#action-dock [data-item-key="target-7"]').exists()).toBe(false);
  });

  it("an empty room renders no rail and no placeholder", async () => {
    await mountWith(exploration({ interact: [], look: { entities: [], objects: [] } }));
    expect(wrapper.find('[data-anchor="presence"] [data-testid="presence-rail"]').exists()).toBe(false);
    expect(wrapper.find('[data-anchor="presence"] [data-testid="presence-entry"]').exists()).toBe(false);
    expect(wrapper.get('[data-anchor="presence"]').text()).toBe("");
  });

  it("hover explains: the readout shows the clerk's name over the affordance summary", async () => {
    await mountWith();
    await entry("target-7").trigger("mouseenter");
    expect(wrapper.get('[data-testid="exploration-readout-lead"]').text()).toBe("店長");
    expect(readoutText()).toBe("交談／公會服務");
    await entry("target-7").trigger("mouseleave");
    expect(readoutText()).toMatch(/^出口 \d · 在場 1$/);
  });

  it("opening is local: the verb card, the standee, the speaker line, and the cockpit stepping away", async () => {
    await mountWith();
    await entry("target-7").trigger("click");
    await settle();

    expect(sender.sent.actions).toHaveLength(0);
    expect(store.router.depth()).toBe(1);
    expect(cardRows().map((row) => row.text())).toEqual(["1交談", "2公會服務", "3查看", "返回"]);
    expect(document.activeElement).toBe(card().element);
    // The rail fades out (kept mounted, hidden and inert).
    expect(rail().attributes("style")).toContain("display: none");
    expect(rail().attributes("inert")).toBeDefined();
    // The command panel is inert and dims; the map anchor steps away.
    expect(stage().attributes("data-person-focus")).toBe("true");
    expect(stage().attributes("data-card-open")).toBe("true");
    expect(wrapper.get('[data-anchor="band-command"]').attributes("inert")).toBeDefined();
    expect(wrapper.get('[data-anchor="map"]').attributes("inert")).toBeDefined();
    // The standee in actor-right and the speaker line.
    expect(standee().exists()).toBe(true);
    expect(wrapper.get('[data-testid="message-name-plate"]').text()).toContain("店長");
  });

  it("a target without a portrait uses the dialogue silhouette treatment", async () => {
    await mountWith();
    store.activatePresence("target-7");
    await settle();
    expect(standee().exists()).toBe(true);
    expect(standee().find("img").exists()).toBe(false);
    expect(standee().text()).toContain("店長");
  });

  it("an accepted snapshot reaches the target and bystander medallions and the non-party standee", async () => {
    await mountWith(
      exploration({
        interact: [{ ...CLERK, portrait_ref: "7" }],
        look: {
          room: { identity: 42, display_name: "石板廣場", room: true },
          entities: [{ ...TRAVELLER, portrait_ref: "8" }],
          objects: [{ identity: 3, display_name: "木箱" }],
        },
      }),
      artPanel({ 7: CLERK_FACE, 8: BYSTANDER_FACE }),
    );
    // The gold target medallion and the dashed bystander medallion both show
    // the supplied crop; the reference is read from the committed catalog and
    // never built from identity.
    expect(entry("target-7").get('[data-testid="presence-entry-face"]').attributes("src")).toBe(
      CLERK_FACE.artwork.attempts[0].resource.url,
    );
    expect(entry("entity-8").get('[data-testid="presence-entry-face"]').attributes("src")).toBe(
      BYSTANDER_FACE.artwork.attempts[0].resource.url,
    );
    // The non-party focus figure renders the same catalog image with the
    // supplied stage geometry, opening no action and pushing no frame.
    await entry("target-7").trigger("click");
    await settle();
    expect(standee().get("img").attributes("src")).toBe(CLERK_FACE.artwork.attempts[0].resource.url);
    expect(sender.sent.actions).toHaveLength(0);
    expect(store.router.depth()).toBe(1);
  });

  it("a late art refresh reaches the open card without reopening or dispatching", async () => {
    await mountWith(
      exploration({
        interact: [{ ...CLERK, portrait_ref: null }],
        look: {
          room: { identity: 42, display_name: "石板廣場", room: true },
          entities: [TRAVELLER],
          objects: [{ identity: 3, display_name: "木箱" }],
        },
      }),
    );
    expect(entry("target-7").find('[data-testid="presence-entry-face"]').exists()).toBe(false);
    await entry("target-7").trigger("click");
    await settle();
    expect(standee().find("img").exists()).toBe(false);
    const identity = card().attributes("data-card-kind");
    const rowsBefore = cardRows().map((row) => row.text());
    expect(identity).toBe("verbs");

    // One newer committed update supplies the usable reference and image.
    await commit({
      art: artPanel({ 7: CLERK_FACE }),
      exploration: exploration({
        interact: [{ ...CLERK, portrait_ref: "7" }],
        look: {
          room: { identity: 42, display_name: "石板廣場", room: true },
          entities: [TRAVELLER],
          objects: [{ identity: 3, display_name: "木箱" }],
        },
      }),
    });
    expect(card().exists()).toBe(true);
    expect(standee().get("img").attributes("src")).toBe(CLERK_FACE.artwork.attempts[0].resource.url);
    expect(entry("target-7").get('[data-testid="presence-entry-face"]').attributes("src")).toBe(
      CLERK_FACE.artwork.attempts[0].resource.url,
    );
    // The open card keeps its target, its verb order and its geometry; no
    // focus message or action is dispatched by the refresh.
    expect(cardRows().map((row) => row.text())).toEqual(rowsBefore);
    expect(store.router.depth()).toBe(1);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("a newer committed URL replaces a failed face, and an unavailable catalog falls back truthfully", async () => {
    await mountWith(
      exploration({
        interact: [{ ...CLERK, portrait_ref: "7" }],
        look: {
          room: { identity: 42, display_name: "石板廣場", room: true },
          entities: [{ ...TRAVELLER, portrait_ref: "404" }],
          objects: [{ identity: 3, display_name: "木箱" }],
        },
      }),
      artPanel({ 7: CLERK_FACE }),
    );
    // The unknown bystander reference resolves to no catalog entry: the
    // dashed medallion keeps the name's first character.
    expect(entry("entity-8").find('[data-testid="presence-entry-face"]').exists()).toBe(false);
    expect(entry("entity-8").get('[data-testid="presence-entry-initial"]').text()).toBe("旅");
    // A failed load keeps the initial, and a genuinely newer URL recovers.
    await entry("target-7").get('[data-testid="presence-entry-face"]').trigger("error");
    await settle();
    expect(entry("target-7").find('[data-testid="presence-entry-face"]').exists()).toBe(false);
    expect(entry("target-7").get('[data-testid="presence-entry-initial"]').text()).toBe("店");
    await commit({ art: artPanel({ 7: CLERK_FACE_REPLACED }) });
    expect(entry("target-7").get('[data-testid="presence-entry-face"]').attributes("src")).toBe(
      CLERK_FACE_REPLACED.artwork.attempts[0].resource.url,
    );
    // An unavailable art panel leaves every medallion on its initial and the
    // standee on the established placeholder — exploration stays usable.
    await commit({ art: ART_PANEL_UNAVAILABLE_SAMPLE });
    expect(entry("target-7").find('[data-testid="presence-entry-face"]').exists()).toBe(false);
    await entry("target-7").trigger("click");
    await settle();
    expect(standee().exists()).toBe(true);
    expect(standee().find("img").exists()).toBe(false);
    expect(sender.sent.actions).toHaveLength(0);
    expect(store.router.depth()).toBe(1);
  });

  it("a failed standee image keeps the open card and recovers on a newer URL", async () => {
    await mountWith(
      exploration({
        interact: [{ ...CLERK, portrait_ref: "7" }],
        look: {
          room: { identity: 42, display_name: "石板廣場", room: true },
          entities: [TRAVELLER],
          objects: [{ identity: 3, display_name: "木箱" }],
        },
      }),
      artPanel({ 7: CLERK_FACE }),
    );
    // The figure's presented attempt image: one element per attempt, so a
    // failed candidate hands over to the descriptor's own terminal.
    const portraitImg = () => standee().find("img.reference-artwork__figure");
    await entry("target-7").trigger("click");
    await settle();
    expect(portraitImg().attributes("src")).toBe(CLERK_FACE.artwork.attempts[0].resource.url);
    const rowsBefore = cardRows().map((row) => row.text());

    // The figure's own image fails: the card stays open on the same target
    // with the same verbs, and the descriptor's own terminal takes over as the
    // presented attempt while the reached fault keeps its local marker.
    await portraitImg().trigger("error");
    await settle();
    expect(card().exists()).toBe(true);
    expect(store.view?.presenceCard?.identity ?? null).not.toBeNull();
    expect(portraitImg().attributes("src")).toBe("/art/defaults/man.webp");
    expect(standee().find('[data-testid="artwork-failure"]').exists()).toBe(true);
    expect(cardRows().map((row) => row.text())).toEqual(rowsBefore);

    // One newer committed URL replaces the failed one: the still-open card
    // renders the new figure without reopening or dispatching anything.
    await commit({
      art: artPanel({ 7: CLERK_FACE_REPLACED }),
      exploration: exploration({
        interact: [{ ...CLERK, portrait_ref: "7" }],
        look: {
          room: { identity: 42, display_name: "石板廣場", room: true },
          entities: [TRAVELLER],
          objects: [{ identity: 3, display_name: "木箱" }],
        },
      }),
    });
    expect(card().exists()).toBe(true);
    expect(portraitImg().attributes("src")).toBe(CLERK_FACE_REPLACED.artwork.attempts[0].resource.url);
    expect(sender.sent.actions).toHaveLength(0);
    expect(store.router.depth()).toBe(1);
  });

  it("Escape and 返回 close the card and return focus to the medallion that opened it", async () => {
    await mountWith();
    for (const close of ["escape", "back-row"]) {
      await entry("target-7").trigger("click");
      await settle();
      expect(card().exists(), close).toBe(true);
      if (close === "escape") {
        key(card().element, "Escape");
      } else {
        await cardRows().at(-1).trigger("click");
      }
      await settle();
      expect(card().exists(), close).toBe(false);
      expect(standee().exists(), close).toBe(false);
      expect(stage().attributes("data-person-focus"), close).toBeUndefined();
      expect(document.activeElement, close).toBe(rail().element);
      expect(
        document.getElementById(rail().attributes("aria-activedescendant")).dataset.entryKey,
        close,
      ).toBe("target-7");
    }
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("查看 submits one explore.look and closes the card", async () => {
    await mountWith();
    store.activatePresence("target-7");
    await settle();
    key(card().element, "3");
    await settle();
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({ action_id: "explore.look", payload: { target_id: 7 } });
    expect(card().exists()).toBe(false);
    expect(document.activeElement).toBe(rail().element);
  });

  it("a card owns the digits: `1` picks its first row, never the rail's", async () => {
    await mountWith();
    store.activatePresence("target-7");
    await settle();
    key(card().element, "1");
    await settle();
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({ action_id: "explore.talk_open", payload: { npc_id: 7 } });
  });

  it("the focused person leaves: the card closes in that commit and the readout flashes", async () => {
    await mountWith();
    store.activatePresence("target-7");
    await settle();
    await commit({ exploration: exploration({ interact: [], look: { entities: [] } }), local_map: fx.localMapPanel() });
    expect(card().exists()).toBe(false);
    expect(standee().exists()).toBe(false);
    expect(readoutText()).toBe("店長 已經離開了。");
    expect(wrapper.get('[data-testid="exploration-readout"]').attributes("data-flash")).toBe("true");
  });

  it("a committed move closes the card and leaves the dock on the new room's exploration root", async () => {
    await mountWith();
    store.activatePresence("target-7");
    await settle();
    await commit({
      exploration: exploration({ look: { room: { identity: 77, display_name: "渡口", room: true } } }),
      local_map: fx.localMapPanel(),
    });
    expect(card().exists()).toBe(false);
    expect(store.view.dockSource).toBe("exploration.root");
    expect(wrapper.find('#action-dock [data-testid="exploration-root"]').exists()).toBe(true);
  });

  it("交談 hands the same standee element to the dialogue screen", async () => {
    await mountWith();
    store.activatePresence("target-7");
    await settle();
    const before = standee().element;
    expect(store.activatePresenceVerb("talk-open").sent).toBe(true);
    await settle();
    revision += 1;
    store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          revision,
          mode: "dialogue",
          panels: {
            status: fx.statusPanel(),
            exploration: exploration(),
            local_map: fx.localMapPanel(),
            context_actions: fx.explorationActions(),
            art: artPanel(),
            dialogue: {
              schema_version: 2,
              available: true,
              kind: "dialogue",
              host: { identity: 7, display_name: "店長", portrait_ref: null },
              bond_stage: "熟識",
              line: "歡迎。",
              choices: [{ keyword_id: "news", label: "最近有什麼消息？" }],
            },
          },
        }),
      ],
      {},
    );
    await settle();
    expect(store.view.mode).toBe("dialogue");
    expect(card().exists()).toBe(false);
    expect(standee().element).toBe(before);
    expect(wrapper.findAll('[data-testid="anchor-actor-right"] [data-testid="stage-actor"]')).toHaveLength(1);
    // The card held focus when 交談 committed: focus goes to the dialogue's
    // focus home (the message page or the choice list), never the body.
    const active = document.activeElement;
    expect(active).not.toBe(document.body);
    expect(
      active.matches('[data-testid="message-page"]') || active.matches('[data-testid="dialogue-choices"]'),
    ).toBe(true);
  });

  it("the overflow card lists the rest, objects marked ◇, and a pick opens that person's card", async () => {
    const crowd = [1, 2, 3, 4, 5].map((n) => ({ identity: 100 + n, display_name: `旅人${n}`, portrait_ref: null, affordances: [] }));
    await mountWith(exploration({ interact: crowd, look: { entities: [], objects: [{ identity: 3, display_name: "木箱" }, { identity: 4, display_name: "告示板" }] } }));
    const slots = rail().findAll('[data-testid="presence-entry"]');
    expect(slots).toHaveLength(6);
    expect(slots[5].text()).toContain("＋2");
    await slots[5].trigger("click");
    await settle();
    expect(card().attributes("data-card-kind")).toBe("overflow");
    expect(cardRows().map((row) => row.text())).toEqual(["1◇ 木箱", "2◇ 告示板", "返回"]);
    key(card().element, "Escape");
    await settle();
    expect(document.getElementById(rail().attributes("aria-activedescendant")).dataset.entryKey).toBe("presence-more");
  });

  it("rail digits: `1` opens the card from anywhere, and a digit past the rail is claimed and does nothing", async () => {
    await mountWith();
    expect(store.focusPress("5")).toBe(true);
    expect(card().exists()).toBe(false);
    expect(store.focusPress("1")).toBe(true);
    await settle();
    expect(card().exists()).toBe(true);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("opening a card stops the compass", async () => {
    await mountWith();
    const compass = wrapper.get('[data-testid="exit-compass"]');
    expect(compass.classes()).not.toContain("exit-compass--inactive");
    store.activatePresence("target-7");
    await settle();
    expect(compass.classes()).toContain("exit-compass--inactive");
    store.closePresenceCard();
    await settle();
    expect(compass.classes()).not.toContain("exit-compass--inactive");
  });

  it("Tab walks compass → rail → 查看房間 → 等待 → 建議, and Shift+Tab walks back", async () => {
    await mountWith();
    const compass = wrapper.get('[data-testid="exit-compass"]').element;
    const look = wrapper.get('[data-anchor="map"] [data-testid="place-card-look"]').element;
    const wait = wrapper.get('[data-anchor="map"] [data-testid="place-card-wait"]').element;
    const pill = wrapper.get('#action-dock [data-testid="suggestions-pill"]').element;
    compass.focus();
    key(compass, "Tab");
    expect(document.activeElement).toBe(rail().element);
    key(rail().element, "Tab");
    expect(document.activeElement).toBe(look);
    key(look, "Tab");
    expect(document.activeElement).toBe(wait);
    key(wait, "Tab");
    expect(document.activeElement).toBe(pill);
    key(pill, "Tab", { shiftKey: true });
    expect(document.activeElement).toBe(wait);
    key(wait, "Tab", { shiftKey: true });
    expect(document.activeElement).toBe(look);
    key(look, "Tab", { shiftKey: true });
    expect(document.activeElement).toBe(rail().element);
    key(rail().element, "Tab", { shiftKey: true });
    expect(document.activeElement).toBe(compass);
  });

  it("the Tab chain skips a zone that is absent or inert", async () => {
    await mountWith();
    const compass = wrapper.get('[data-testid="exit-compass"]').element;
    const look = wrapper.get('[data-anchor="map"] [data-testid="place-card-look"]').element;
    // An empty room: no rail, so the compass hands over to 查看房間.
    await commit({ exploration: exploration({ interact: [], look: { ...exploration().look, entities: [], objects: [] } }) });
    expect(rail().exists()).toBe(false);
    compass.focus();
    key(compass, "Tab");
    expect(document.activeElement).toBe(look);
    key(look, "Tab", { shiftKey: true });
    expect(document.activeElement).toBe(compass);
    // An inert map anchor (person focus takes the place card away): the
    // chain skips the place card's buttons.
    wrapper.get('[data-anchor="map"]').element.setAttribute("inert", "");
    const pill = wrapper.get('#action-dock [data-testid="suggestions-pill"]').element;
    compass.focus();
    key(compass, "Tab");
    expect(document.activeElement).toBe(pill);
    key(pill, "Tab", { shiftKey: true });
    expect(document.activeElement).toBe(compass);
    wrapper.get('[data-anchor="map"]').element.removeAttribute("inert");
  });
});

// ---------------------------------------------------------------------------
// reuse-lineup-person-focus: an opened verb card whose target is already drawn
// in the actor-left lineup reuses that figure — no actor-right copy — and the
// selected companion is lit and elevated through the existing companion
// speaking signal, restoring its baseline when the card closes, the target
// leaves, the lineup changes or the mode hands over to dialogue.
//
// Every case drives accepted snapshots/updates through the store (party,
// roster, status, possession banner, art and dialogue included) and reads the
// committed stage: the actor-left figures with their z/dim/geometry, the
// actor-right anchor's DOM counts, the centred card, the speaker line and the
// readout flash.
// ---------------------------------------------------------------------------

// The roster the player's own figure resolves from (identity 1), so the
// controlled front keeps a stable identity across possession swaps.
const FOCUS_ROSTER = {
  schema_version: 3,
  available: true,
  characters: [{
    identity: 1,
    name: "艾莉亞",
    current: true,
    pending: false,
    // The row's portrait IS the complete canonical descriptor.
    portrait: faceEntry(
      "portrait:character:1",
      "/art/defaults/man.webp",
      { x: 0.25, y: 0.06, w: 0.5, h: 0.5 },
      "艾莉亞",
      "人物",
    ).artwork,
  }],
  max_characters: 5,
  can_create: true,
  switch_locked: false,
  lock_reason: null,
};
const FOCUS_NAMES = { 101: "蕾娜", 102: "幽", 103: "艾德蒙", 104: "雪莉", 105: "旅人見習" };
const FOCUS_TALK = {
  kind: "action", action_id: "explore.talk_open", label: "交談", enabled: true, disabled_reason: null,
};
function focusMember(identity) {
  return {
    identity,
    display_name: FOCUS_NAMES[identity] ?? `同行${identity}`,
    portrait_ref: null,
    hp_current: 120,
    hp_maximum: 160,
    bond_stage: "親睦",
    membership: { general: true, temporary_commissions: [] },
  };
}
function focusParty(...identities) {
  return {
    schema_version: 2,
    available: true,
    // The general quota is a separate bound from the rendered row: the
    // truncated-row case carries more rows than the quota allows.
    general_quota: { used: Math.min(identities.length, 4), limit: 4 },
    slots: identities.map(focusMember),
  };
}
const FOCUS_PARTY_UNAVAILABLE = {
  schema_version: 2,
  available: false,
  reason: { code: "party_unavailable", message: "隊伍資訊目前無法顯示" },
};
function focusTarget(identity, overrides = {}) {
  return {
    identity,
    display_name: FOCUS_NAMES[identity] ?? "目標",
    portrait_ref: null,
    affordances: [FOCUS_TALK],
    ...overrides,
  };
}
// The five present people: two party companions in the default lineup, the
// truncated-row and reorder cases' extra identities, and one non-party control.
function focusRoom(overrides = {}) {
  return fx.explorationPanel({
    interact: [101, 102, 103, 104, 105].map((identity) => focusTarget(identity)),
    look: {
      room: { identity: 42, display_name: "石板廣場", room: true },
      entities: [],
      objects: [{ identity: 3, display_name: "木箱" }],
    },
    ...overrides,
  });
}

describe("AppClient companion focus (reuse-lineup-person-focus)", () => {
  let store;
  let wrapper;
  let sender;
  let revision;
  // The committed actor identity the status panel carries: the wire identity
  // the possession cases swap. `fx.update` deep-merges into the shared fixture
  // snapshot, so every commit names the panels it depends on instead of
  // inheriting the fixture's own default `status` panel.
  let actorIdentity;
  const statusWithActor = () => fx.statusPanel({ actor: { identity: actorIdentity } });

  async function settle() {
    for (let i = 0; i < 4; i += 1) {
      await nextTick();
    }
  }

  async function mountFocus({
    rows = [101, 102],
    exploration = focusRoom(),
    art = artPanel(),
    actor = "1",
    extra = {},
  } = {}) {
    actorIdentity = actor;
    wrapper = mount(AppClient, { attachTo: document.body });
    store.beginTransport(1);
    store.setConnected(true);
    store.setLoggedIn(true);
    revision = 1;
    const result = store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          revision,
          panels: {
            status: statusWithActor(),
            exploration,
            local_map: fx.localMapPanel(),
            context_actions: fx.explorationActions(),
            art,
            roster: FOCUS_ROSTER,
            party: focusParty(...rows),
            ...extra,
          },
        }),
      ],
      {},
    );
    expect(result.accepted).toBe(true);
    await settle();
  }

  async function commit(panels = {}, extra = {}) {
    revision += 1;
    const result = store.receive(
      1,
      "ui_update",
      [fx.update({ revision, panels: { status: statusWithActor(), ...panels }, ...extra })],
      {},
    );
    expect(result.accepted).toBe(true);
    await settle();
  }

  // The one 交談 submission's reply, rejected: it releases the submission lock.
  async function releaseLock() {
    store.receive(
      1,
      "ui_action_result",
      [fx.actionResult({ outcome: "rejected", code: "invalid", message: "不行。" })],
      {},
    );
    await settle();
  }

  const card = () => wrapper.find('[data-anchor="choices"] [data-testid="presence-card"]');
  const cardRows = () => card().findAll('[role="menuitem"]');
  const rail = () => wrapper.get('[data-anchor="presence"] [data-testid="presence-rail"]');
  const entry = (key) => wrapper.get(`[data-anchor="presence"] [data-entry-key="${key}"]`);
  const stage = () => wrapper.get('[data-testid="elosern-stage"]');
  const readoutText = () => wrapper.get('[data-testid="exploration-readout-text"]').text();
  const figures = () => wrapper.findAll('[data-testid="companion-figure"]');
  const figureIds = () => figures().map((slot) => slot.attributes("data-identity"));
  const figure = (identity) => wrapper.get(`[data-testid="companion-figure"][data-identity="${identity}"]`);
  const actorOf = (identity) => figure(identity).get('[data-testid="stage-actor"]');
  const speaks = (identity) => actorOf(identity).attributes("data-speaking");
  const zOf = (identity) => figure(identity).element.style.zIndex;
  const boxOf = (identity) => {
    const style = figure(identity).element.style;
    return [style.height, style.width, style.right, style.bottom];
  };
  const rightActors = () =>
    wrapper.findAll('[data-testid="anchor-actor-right"] [data-testid="stage-actor"]');

  async function open(key) {
    await entry(key).trigger("click");
    await settle();
  }

  function key(element, name, init = {}) {
    element.dispatchEvent(new KeyboardEvent("keydown", { key: name, bubbles: true, cancelable: true, ...init }));
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  it("opens a rendered companion's card on its own figure: no copy, no action, no frame", async () => {
    await mountFocus();
    expect(figureIds()).toEqual(["1", "101", "102"]);
    const selectedBox = boxOf("101");
    const otherBox = boxOf("102");
    const controlledBox = boxOf("1");

    await open("target-101");

    // Client-local: no request and no router frame.
    expect(sender.sent.actions).toHaveLength(0);
    expect(store.router.depth()).toBe(1);
    expect(card().attributes("data-card-kind")).toBe("verbs");
    expect(cardRows().map((row) => row.text())).toEqual(["1交談", "2查看", "返回"]);
    expect(stage().attributes("data-person-focus")).toBe("true");
    expect(wrapper.get('[data-testid="message-name-plate"]').text()).toContain("蕾娜");
    // One representation of that identity: the existing left figure, never an
    // actor-right copy.
    expect(rightActors()).toHaveLength(0);
    // The selected non-controlled companion is lit and above every baseline
    // figure; the other companion keeps the listener dim at its own baseline z.
    expect(speaks("101")).toBe("true");
    expect(zOf("101")).toBe("6");
    expect(speaks("102")).toBe("false");
    expect(zOf("102")).toBe("1");
    // The controlled front keeps its exploration props: lit, baseline z, and
    // no beat gesture of its own here.
    expect(speaks("1")).toBe("true");
    expect(zOf("1")).toBe("3");
    expect(actorOf("1").attributes("data-beat")).toBeUndefined();
    // Focus changes no geometry: the same committed lineup, byte for byte.
    expect(boxOf("101")).toEqual(selectedBox);
    expect(boxOf("102")).toEqual(otherBox);
    expect(boxOf("1")).toEqual(controlledBox);
  });

  it("a same-name, same-portrait target outside the lineup keeps the actor-right standee", async () => {
    const face = faceEntry(
      "npc_101",
      "/art/portraits/npc_101.webp",
      { x: 0.25, y: 0.06, w: 0.5, h: 0.5 },
      "蕾娜",
      "對話對象",
    );
    await mountFocus({
      exploration: focusRoom({
        interact: [focusTarget(101), focusTarget(7, { display_name: "蕾娜", portrait_ref: "101" })],
      }),
      art: artPanel({ 101: face }),
    });
    await open("target-7");

    // The different identity selects the normal standee — the equal name and
    // the equal reference prove nothing about membership.
    expect(rightActors()).toHaveLength(1);
    expect(rightActors()[0].attributes("data-identity")).toBe("7");
    expect(rightActors()[0].text()).toContain("蕾娜");
    // No lineup companion gains exploration emphasis.
    expect(speaks("101")).toBe("false");
    expect(zOf("101")).toBe("2");
    expect(speaks("102")).toBe("false");
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("a raw party row outside the displayed lineup is not a rendered figure", async () => {
    await mountFocus({ rows: [101, 102, 103, 104, 105], exploration: focusRoom() });
    // The bounded row draws the controlled front plus four companions; the
    // fifth raw party row is never rendered.
    expect(figureIds()).toEqual(["1", "101", "102", "103", "104"]);

    await open("target-105");

    expect(rightActors()).toHaveLength(1);
    expect(rightActors()[0].attributes("data-identity")).toBe("105");
    for (const identity of ["101", "102", "103", "104"]) {
      expect(speaks(identity), identity).toBe("false");
    }
    expect(zOf("101")).toBe("4");
  });

  it("membership is identity-only: a null portrait and an unavailable catalog change nothing", async () => {
    await mountFocus({ art: ART_PANEL_UNAVAILABLE_SAMPLE });
    // Every figure keeps its truthful initial: no art is resolved at all.
    expect(actorOf("101").find("img").exists()).toBe(false);

    await open("target-101");

    expect(rightActors()).toHaveLength(0);
    expect(speaks("101")).toBe("true");
    expect(zOf("101")).toBe("6");
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("emphasis follows the selected identity through a party reorder, not its slot index", async () => {
    await mountFocus();
    await open("target-101");
    expect(zOf("101")).toBe("6");

    await commit({ party: focusParty(103, 101) });

    expect(figureIds()).toEqual(["1", "103", "101"]);
    expect(speaks("101")).toBe("true");
    expect(zOf("101")).toBe("6");
    // The companion that took the selected identity's old index stays a
    // listener at the new lineup's baseline z.
    expect(speaks("103")).toBe("false");
    expect(zOf("103")).toBe("2");
    expect(zOf("1")).toBe("3");
  });

  it("a possession swap of the selected companion never elevates the controlled front", async () => {
    await mountFocus();
    await open("target-101");
    expect(zOf("101")).toBe("6");

    // The player possesses the focused companion: it becomes the controlled
    // front, so it holds no listener elevation and keeps its own props.
    actorIdentity = "101";
    await commit({
      possession_banner: { schema_version: 1, available: true, host_name: "蕾娜", since_tick: 0 },
    });
    expect(figureIds()).toEqual(["101", "1", "102"]);
    expect(rightActors()).toHaveLength(0);
    expect(speaks("101")).toBe("true");
    expect(zOf("101")).toBe("3");
    expect(speaks("102")).toBe("false");

    // Releasing it returns the emphasis to the still-open card's target.
    actorIdentity = "1";
    await commit({
      possession_banner: {
        schema_version: 1, available: false,
        reason: { code: "unavailable", message: "目前沒有附身" },
      },
    });
    expect(figureIds()).toEqual(["1", "101", "102"]);
    expect(zOf("101")).toBe("6");
    expect(speaks("101")).toBe("true");
    expect(rightActors()).toHaveLength(0);
  });

  it("the controlled placeholder front (string status identity, no party rows) is never elevated", async () => {
    await mountFocus({
      rows: [],
      actor: "101",
      extra: {
        possession_banner: { schema_version: 1, available: true, host_name: "蕾娜", since_tick: 0 },
      },
    });
    // The unrendered party leaves the controlled placeholder: the wire string
    // identity joins the numeric interact identity, so no actor-right copy
    // appears either — and the controlled figure stays at its baseline.
    expect(figureIds()).toEqual(["101"]);

    await open("target-101");
    expect(rightActors()).toHaveLength(0);
    expect(zOf("101")).toBe("1");
    expect(speaks("101")).toBe("true");

    // An unavailable party panel keeps that same single controlled figure.
    await commit({ party: FOCUS_PARTY_UNAVAILABLE });
    expect(figureIds()).toEqual(["101"]);
    expect(rightActors()).toHaveLength(0);
    expect(zOf("101")).toBe("1");
  });

  it("transfers representation both ways between the left figure and actor-right", async () => {
    // 101 is present but not a party member: its card stands a right figure.
    await mountFocus({ rows: [102] });
    await open("target-101");
    expect(figureIds()).toEqual(["1", "102"]);
    expect(rightActors()).toHaveLength(1);
    expect(rightActors()[0].attributes("data-identity")).toBe("101");

    // It joins the committed rendered lineup: the left figure takes over in
    // that commit and the right standee is gone rather than leaving behind a
    // duplicate (the live DOM count through the transfer is pinned by the
    // managed browser method, where a CSS leave phase really runs).
    await commit({ party: focusParty(101, 102) });
    expect(figureIds()).toEqual(["1", "101", "102"]);
    expect(rightActors()).toHaveLength(0);
    expect(speaks("101")).toBe("true");
    expect(zOf("101")).toBe("6");

    // It leaves the lineup again while the card survives: the ordinary
    // actor-right standee takes over, still exactly one representation.
    await commit({ party: focusParty(102) });
    expect(figureIds()).toEqual(["1", "102"]);
    expect(rightActors()).toHaveLength(1);
    expect(rightActors()[0].attributes("data-identity")).toBe("101");
    expect(speaks("102")).toBe("false");
  });

  it("closing through Escape, 返回 and 查看 restores the baseline and the opener", async () => {
    await mountFocus();
    for (const close of ["escape", "back-row", "look-row"]) {
      await open("target-101");
      expect(zOf("101"), close).toBe("6");
      expect(speaks("101"), close).toBe("true");
      if (close === "escape") {
        key(card().element, "Escape");
        await settle();
      } else if (close === "back-row") {
        await cardRows().at(-1).trigger("click");
        await settle();
      } else {
        await cardRows().at(-2).trigger("click");
        await settle();
      }
      expect(card().exists(), close).toBe(false);
      // The current baseline is restored with no remembered focus z, and the
      // lineage never had a right-side figure to leave behind.
      expect(zOf("101"), close).toBe("2");
      expect(speaks("101"), close).toBe("false");
      expect(rightActors(), close).toHaveLength(0);
      if (close === "look-row") {
        expect(sender.sent.actions).toHaveLength(1);
        expect(sender.sent.actions[0]).toMatchObject({
          action_id: "explore.look",
          payload: { target_id: 101 },
        });
      } else {
        expect(sender.sent.actions).toHaveLength(0);
      }
      // Focus returns to the medallion that opened the card.
      expect(
        document.getElementById(rail().attributes("aria-activedescendant")).dataset.entryKey,
        close,
      ).toBe("target-101");
    }
  });

  it("a locked departure clears the emphasis at once and settles the card once", async () => {
    await mountFocus();
    await open("target-101");
    // An unrelated 交談 submission holds the settlement lock.
    expect(store.activatePresenceVerb("talk-open").sent).toBe(true);

    await commit({ exploration: focusRoom({ interact: [focusTarget(102)] }) });

    // The committed target is gone, so the derived list emphasis is gone in
    // that commit — while the locked settlement still holds the card open and
    // claims no departure.
    expect(card().exists()).toBe(true);
    expect(speaks("101")).toBe("false");
    expect(zOf("101")).toBe("2");
    expect(rightActors()).toHaveLength(0);
    expect(store.view.presenceNotice).toBe(null);

    // The lock releases: the normal settlement closes the card and flashes the
    // departure exactly once.
    await releaseLock();
    expect(card().exists()).toBe(false);
    expect(store.view.presenceNotice.seq).toBe(1);
    expect(readoutText()).toBe("蕾娜 已經離開了。");
    expect(wrapper.get('[data-testid="exploration-readout"]').attributes("data-flash")).toBe("true");
    expect(zOf("101")).toBe("2");
    expect(rightActors()).toHaveLength(0);
  });

  it("a committed move closes the card with no departure claim and no stale emphasis", async () => {
    await mountFocus();
    await open("target-101");

    await commit({
      exploration: focusRoom({
        look: {
          room: { identity: 77, display_name: "渡口", room: true },
          entities: [],
          objects: [],
        },
      }),
    });

    expect(card().exists()).toBe(false);
    expect(store.view.presenceNotice).toBe(null);
    expect(zOf("101")).toBe("2");
    expect(speaks("101")).toBe("false");
    expect(rightActors()).toHaveLength(0);
  });

  // The emphasis is derived state, so the final focus state does not depend on
  // a transition running: full, reduced and off all land on the same props.
  for (const level of ["full", "reduced", "off"]) {
    it(`reaches the same focus and restoration state at ${level} motion`, async () => {
      await mountFocus();
      store.setMotionLevel(level);
      await settle();

      await open("target-101");
      expect(zOf("101")).toBe("6");
      expect(speaks("101")).toBe("true");
      expect(speaks("102")).toBe("false");
      expect(rightActors()).toHaveLength(0);

      key(card().element, "Escape");
      await settle();
      expect(card().exists()).toBe(false);
      expect(zOf("101")).toBe("2");
      expect(speaks("101")).toBe("false");
      expect(rightActors()).toHaveLength(0);
    });
  }

  it("an unavailable panel and an epoch reset cannot retain a former selected slot", async () => {
    await mountFocus();
    await open("target-101");
    expect(zOf("101")).toBe("6");

    // The exploration panel goes away: the derived emphasis clears while the
    // store's own lifecycle keeps the card (the settled rule).
    await commit({
      exploration: {
        schema_version: 4,
        available: false,
        reason: { code: "scene_lost", message: "場景暫時無法顯示" },
      },
    });
    expect(store.view.presenceCard).toMatchObject({ kind: "verbs", identity: 101 });
    expect(speaks("101")).toBe("false");
    expect(zOf("101")).toBe("2");
    expect(rightActors()).toHaveLength(0);

    // A transport reset (a fresh generation and epoch) leaves no card, no
    // emphasis and no right-side figure; the companion that is no longer a
    // rendered member cannot stay selected.
    store.beginTransport(2);
    store.setConnected(true);
    const result = store.receive(
      2,
      "ui_snapshot",
      [
        fx.snapshot({
          revision: 1,
          presentation_epoch: fx.EPOCH_B,
          panels: {
            status: statusWithActor(),
            exploration: focusRoom(),
            local_map: fx.localMapPanel(),
            context_actions: fx.explorationActions(),
            art: artPanel(),
            roster: FOCUS_ROSTER,
            party: FOCUS_PARTY_UNAVAILABLE,
          },
        }),
      ],
      {},
    );
    expect(result.accepted).toBe(true);
    await settle();
    expect(card().exists()).toBe(false);
    expect(figureIds()).toEqual(["1"]);
    expect(zOf("1")).toBe("1");
    expect(rightActors()).toHaveLength(0);
  });

  it("交談 submits once and hands the companion over to dialogue without a duplicate", async () => {
    await mountFocus();
    await open("target-101");

    expect(store.activatePresenceVerb("talk-open").sent).toBe(true);
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({
      action_id: "explore.talk_open",
      payload: { npc_id: 101 },
    });

    // An intermediate exploration commit still carries the target: the card
    // and the companion's emphasis survive it.
    await commit({ exploration: focusRoom() });
    expect(card().exists()).toBe(true);
    expect(speaks("101")).toBe("true");
    expect(zOf("101")).toBe("6");
    expect(rightActors()).toHaveLength(0);

    // The dialogue commit hands over: the same identity is still represented
    // once on the left, and the existing dialogue speaking signal owns dim/z.
    revision += 1;
    const dialogue = store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          revision,
          mode: "dialogue",
          panels: {
            status: fx.statusPanel({ actor: { identity: "1" } }),
            exploration: focusRoom(),
            local_map: fx.localMapPanel(),
            context_actions: fx.explorationActions(),
            art: artPanel(),
            roster: FOCUS_ROSTER,
            party: focusParty(101, 102),
            dialogue: {
              schema_version: 2,
              available: true,
              kind: "dialogue",
              host: { identity: 101, display_name: "蕾娜", portrait_ref: null },
              bond_stage: "熟識",
              line: "歡迎。",
              choices: [{ keyword_id: "news", label: "最近有什麼消息？" }],
            },
          },
        }),
      ],
      {},
    );
    expect(dialogue.accepted).toBe(true);
    await settle();
    expect(store.view.mode).toBe("dialogue");
    expect(card().exists()).toBe(false);
    expect(figureIds()).toEqual(["1", "101", "102"]);
    expect(rightActors()).toHaveLength(0);
    expect(speaks("101")).toBe("true");
    expect(zOf("101")).toBe("6");
    expect(speaks("1")).toBe("false");
    expect(sender.sent.actions).toHaveLength(1);

    // 交談's own reply releases the submission lock (its declared revision is
    // the committed one), exactly as the live transport's result would.
    store.receive(1, "ui_action_result", [fx.actionResult({ presentation_revision: revision })], {});
    await settle();
    expect(store.view.dispatch.inFlight).toBe(null);

    // The player speaks: the existing dialogue host/player signals take over
    // and the hosted companion is dimmed again.
    expect(store.dispatchAction("explore.talk_scripted", { npc_id: 101, keyword_id: "news" }, null)).not.toBe(null);
    await settle();
    expect(store.view.dialogueSpeaker).toBe("player");
    expect(speaks("101")).toBe("false");
    expect(zOf("101")).toBe("2");
    expect(speaks("1")).toBe("true");
    expect(sender.sent.actions).toHaveLength(2);
  });

  it("a failed talk keeps the surviving card and the companion emphasis", async () => {
    await mountFocus();
    await open("target-101");
    expect(store.activatePresenceVerb("talk-open").sent).toBe(true);
    expect(sender.sent.actions).toHaveLength(1);

    // The submission is rejected while its target and rendered figure survive:
    // the existing action feedback speaks once, the card and the emphasis stay,
    // and nothing is resubmitted or mutated.
    store.receive(
      1,
      "ui_action_result",
      [
        fx.actionResult({
          outcome: "rejected",
          code: "talk_unavailable",
          message: "對方現在無法交談。",
          presentation_revision: revision,
        }),
      ],
      {},
    );
    await settle();
    expect(store.narrative.filter((line) => line.kind === "err").map((line) => line.text)).toEqual([
      "對方現在無法交談。",
    ]);
    expect(store.view.dispatch.inFlight).toBe(null);
    expect(card().exists()).toBe(true);
    expect(card().attributes("data-card-kind")).toBe("verbs");
    expect(speaks("101")).toBe("true");
    expect(zOf("101")).toBe("6");
    expect(figureIds()).toEqual(["1", "101", "102"]);
    expect(rightActors()).toHaveLength(0);
    expect(sender.sent.actions).toHaveLength(1);
  });

  // Everything above mounts AppClient before the store commits. The shell also
  // has to survive a mount against an already-committed store — a hot reload,
  // or a remount while a card is open or a conversation is on — because the
  // derivations and the transfer watcher are read during setup.
  it("mounts against an already-committed card and an already-committed dialogue", async () => {
    store.beginTransport(1);
    store.setConnected(true);
    store.setLoggedIn(true);
    revision = 1;
    const result = store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          revision,
          panels: {
            status: fx.statusPanel({ actor: { identity: "1" } }),
            exploration: focusRoom(),
            local_map: fx.localMapPanel(),
            context_actions: fx.explorationActions(),
            art: artPanel(),
            roster: FOCUS_ROSTER,
            party: focusParty(101, 102),
          },
        }),
      ],
      {},
    );
    expect(result.accepted).toBe(true);
    expect(store.activatePresence("target-101").handled).toBe(true);

    wrapper = mount(AppClient, { attachTo: document.body });
    await settle();
    expect(zOf("101")).toBe("6");
    expect(speaks("101")).toBe("true");
    expect(rightActors()).toHaveLength(0);
    wrapper.unmount();
    wrapper = null;
    document.body.innerHTML = "";

    revision += 1;
    const dialogue = store.receive(
      1,
      "ui_update",
      [
        fx.update({
          revision,
          mode: "dialogue",
          panels: {
            dialogue: {
              schema_version: 2,
              available: true,
              kind: "dialogue",
              host: { identity: 101, display_name: "蕾娜", portrait_ref: null },
              bond_stage: null,
              line: "歡迎。",
              choices: [],
            },
          },
        }),
      ],
      {},
    );
    expect(dialogue.accepted).toBe(true);

    wrapper = mount(AppClient, { attachTo: document.body });
    await settle();
    expect(figureIds()).toEqual(["1", "101", "102"]);
    expect(rightActors()).toHaveLength(0);
    expect(zOf("101")).toBe("6");
    expect(speaks("101")).toBe("true");
  });
});
