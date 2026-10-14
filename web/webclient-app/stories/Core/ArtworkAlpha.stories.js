import ArtworkAlpha from "../../components/ArtworkAlpha.vue";

export default {
  title: "Core/ArtworkAlpha",
  component: ArtworkAlpha,
  parameters: { layout: "centered" },
};

const render = (args) => ({
  components: { ArtworkAlpha },
  setup: () => ({ args }),
  template:
    '<div style="width:220px;height:320px;background:linear-gradient(160deg,#1a1d20,#101214)"><ArtworkAlpha v-bind="args" /></div>',
});

// The observed-same-URL success is the only state that paints a fill.
export const ObservedSuccess = {
  render,
  args: { result: { url: "/art/defaults/woman.webp", phase: "success", dimensions: { width: 864, height: 1536 } } },
};
// An unobserved or failed resource paints nothing — never a solid rectangle.
export const FailedResource = { render, args: { result: { url: "/art/missing.webp", phase: "exhausted", dimensions: null } } };
export const NoResult = { render, args: { result: null } };
