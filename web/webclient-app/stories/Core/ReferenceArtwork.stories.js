import ReferenceArtwork from "../../components/ReferenceArtwork.vue";

export default {
  title: "Core/ReferenceArtwork",
  component: ReferenceArtwork,
  parameters: { layout: "centered" },
};

const renderArtwork = (args) => ({
  components: { ReferenceArtwork },
  setup: () => ({ args }),
  template: '<ReferenceArtwork v-bind="args" style="width:340px;height:640px;background:#121519" />',
});

export const CharacterPortrait = {
  render: renderArtwork,
  args: {
    portrait: {
      subject_key: "port_hero",
      status: "done",
      url: "/art/defaults/man.webp",
      aspect_ratio: "3:4",
      alt: "主角的肖像",
      placeholder: null,
      face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.5 },
    },
  },
};

export const ElderPortrait = {
  render: renderArtwork,
  args: {
    portrait: {
      subject_key: "port_elder",
      status: "done",
      url: "/art/defaults/elder.webp",
      aspect_ratio: "3:4",
      alt: "長者的肖像",
      placeholder: null,
      face_rect: { x: 0.3, y: 0.1, w: 0.4, h: 0.4 },
    },
  },
};

export const MonsterPortrait = {
  render: renderArtwork,
  args: {
    portrait: {
      subject_key: "monster_anon",
      status: "done",
      url: "/art/defaults/monster_anon.webp",
      aspect_ratio: "3:4",
      alt: "野獸的肖像",
      placeholder: null,
      face_rect: { x: 0.2, y: 0.15, w: 0.6, h: 0.5 },
    },
  },
};
