import { createApp } from "vue";
import App from "./App.vue";
import * as elosernLogic from "./logic.js";
import "./styles/tokens.css";
import "./styles/fonts.css";
import "./styles/app-shell.css";

// A2 (webclient-vue-01-foundation) build stub: proves the bundle, its styles,
// and its self-hosted fonts load from the origin offline. The real AppShell
// lands in B1 (webclient-vue-02-showcase-core).

const mountPoint = document.getElementById("main-sub") ?? createFallbackMount();

const app = createApp(App);
app.mount(mountPoint);

// Review-window marker for the offline-load browser check; C2 replaces this
// with the window.Elosern.* public-contract bridge. The imported logic keeps
// the preserved UMD reducer/router/markup/map modules inside the production
// bundle (design D1).
window.ElosernVue = {
  stage: "foundation-stub",
  app,
  logic: elosernLogic,
  protocolVersion: elosernLogic.Protocol.PROTOCOL_VERSION,
};

function createFallbackMount() {
  const element = document.createElement("div");
  element.id = "elosern-app";
  document.body.appendChild(element);
  return element;
}
