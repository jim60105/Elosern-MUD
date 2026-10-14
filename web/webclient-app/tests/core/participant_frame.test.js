import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import ParticipantFrame from "../../components/ParticipantFrame.vue";
import {
  fixtureDigest,
  artworkDescriptor,
  artworkResource,
} from "../../stories/fixtures/art_panels.js";

// The combat participant frame's own portrait contract after the
// unified-portrait-image-contract cutover: the row's reference names a
// canonical artwork descriptor in the committed `art` panel's catalog, and the
// row renders it through the shared real-only avatar position — never the
// alpha terminal, never a client-built catalog key, and never a silent null.
const PANEL = { schema_version: 3, available: true };
const PARTICIPANTS = [
  {
    identity: "m1",
    team: "party",
    token: "小美",
    display_name: "小美",
    hp_current: 80,
    hp_maximum: 100,
    state: "active",
    portrait_ref: "portrait_mei",
  },
  {
    identity: "f1",
    team: "foes",
    token: "哥布林",
    display_name: "哥布林",
    hp_current: 45,
    hp_maximum: 45,
    state: "active",
    portrait_ref: null,
  },
];

function entry(identity, url, faceRect = { x: 0.25, y: 0.06, w: 0.5, h: 0.5 }) {
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
      // A real-only position never requests the terminal, but the descriptor
      // still carries it: the frame simply must not paint it.
      terminal: artworkDescriptor().terminal,
    }),
    context: { name: identity, role: "敵方" },
  };
}

const mountFrame = (artPanel, participants = PARTICIPANTS) =>
  mount(ParticipantFrame, {
    props: {
      participants,
      artPanel,
    },
  });

describe("participant frame portrait positions", () => {
  it("renders the descriptor's own candidate with the row's recenter crop", () => {
    const wrapper = mountFrame({
      ...PANEL,
      portrait_catalog: { portrait_mei: entry("portrait_mei", "/art/mei.png") },
    });
    const image = wrapper.get("img.avatar-artwork__figure");
    expect(image.attributes("src")).toBe("/art/mei.png");
    // The combat row keeps its recenters-only cover crop (never the small
    // thumbnail's zoom enlargement).
    expect(image.element.style.objectPosition).toBe("50% 31%");
    expect(image.element.style.width).toBe("");
    wrapper.unmount();
  });

  it("never requests the alpha terminal for an avatar position", () => {
    const wrapper = mountFrame({
      ...PANEL,
      portrait_catalog: { portrait_mei: entry("portrait_mei", null) },
    });
    // No real candidate: the identity glyph stands, and the descriptor's
    // terminal is NOT requested (a silhouette is not an avatar).
    expect(wrapper.find("img").exists()).toBe(false);
    expect(wrapper.findAll(".avatar-artwork__initial").map((g) => g.text())).toContain(
      "小",
    );
    expect(wrapper.find('[data-testid="artwork-alpha"]').exists()).toBe(false);
    wrapper.unmount();
  });

  it("keeps a reference-less row an expected absence and an admitted one a failure", () => {
    const wrapper = mountFrame({
      ...PANEL,
      portrait_catalog: { portrait_mei: entry("portrait_mei", "/art/mei.png") },
    });
    // The foe carries no reference at all: expected absence, no marker.
    expect(wrapper.findAll('[data-testid="artwork-failure"]')).toHaveLength(0);
    wrapper.unmount();

    // The same row with a reference the committed catalog does not carry: a
    // local failure with the shared persistent marker.
    const dangling = mountFrame({
      ...PANEL,
      portrait_catalog: { portrait_other: entry("portrait_other", "/art/other.png") },
    });
    expect(dangling.findAll('[data-testid="artwork-failure"]')).toHaveLength(1);
    dangling.unmount();
  });

  it("treats an unavailable art panel as a required-surface failure", () => {
    const wrapper = mountFrame({
      available: false,
      portrait_catalog: { portrait_mei: entry("portrait_mei", "/art/mei.png") },
    });
    expect(wrapper.findAll("img")).toHaveLength(0);
    expect(wrapper.findAll('[data-testid="artwork-failure"]')).toHaveLength(1);
    wrapper.unmount();
  });
});
