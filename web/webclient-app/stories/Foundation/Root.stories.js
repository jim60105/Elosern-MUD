import App from "../../App.vue";

// A2 foundation stub story — documents the offline root and the design tokens
// before B1 lands the real AppShell. B-family component stories live alongside
// in their own family files (the manifest gate seeds with them in B1).
export default {
  title: "Foundation/Root",
  component: App,
};

export const OfflineStub = {
  render: () => App,
};
