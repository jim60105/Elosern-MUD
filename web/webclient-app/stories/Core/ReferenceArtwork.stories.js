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

export const AdventurerSample = { render: renderArtwork, args: { subject: "adventurer" } };
export const GuildSample = { render: renderArtwork, args: { subject: "clerk" } };
export const MonsterSample = { render: renderArtwork, args: { subject: "wolf" } };
