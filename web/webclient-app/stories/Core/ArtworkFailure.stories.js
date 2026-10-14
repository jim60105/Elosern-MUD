import ArtworkFailure from "../../components/ArtworkFailure.vue";

export default {
  title: "Core/ArtworkFailure",
  component: ArtworkFailure,
  parameters: { layout: "centered" },
};

const render = (args) => ({
  components: { ArtworkFailure },
  setup: () => ({ args }),
  template: '<div style="width:280px;background:#10121a"><ArtworkFailure v-bind="args" /></div>',
});

// A reached load failure: the local explanation persists at the image position.
export const LoadFailed = { render, args: { kind: "failure", reason: "image_load_failed" } };
// A browser-only decode failure: the same local indication, no invented transport.
export const DecodeFailed = { render, args: { kind: "failure", reason: "image_decode_failed" } };
// A required panel could not supply data: availability styling, not a broken image.
export const PanelUnavailable = { render, args: { kind: "failure", reason: "panel_unavailable" } };
// In-progress loading carries no error styling.
export const Loading = { render, args: { kind: "loading", reason: null } };
// Expected absence renders nothing at all.
export const ExpectedAbsent = { render, args: { kind: "expected", reason: null } };
