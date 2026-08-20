import { createApp } from "vue";
import AppShell from "./components/AppShell.vue";
import * as elosernLogic from "./logic.js";
import "./styles/tokens.css";
import "./styles/fonts.css";
import "./styles/app-shell.css";

// B1 (webclient-vue-02-showcase-core): the core narrative family is the live
// app root. The mount target is a dedicated #elosern-app container created
// inside #main-sub so the stock #messagewindow fallback survives the Vue
// mount (Vue clears its mount container's children) and is retired by the
// shell instead — hidden, never removed, so C3 can re-activate the degraded
// text path. The C2 bridge replaces this transient window.ElosernVue surface
// with the window.Elosern.* public façades over the same imported modules.

function resolveMountPoint() {
  const host = document.getElementById("main-sub") ?? document.body;
  let point = document.getElementById("elosern-app");
  if (!point || !host.contains(point)) {
    point = document.createElement("div");
    point.id = "elosern-app";
    host.appendChild(point);
  }
  return point;
}

const app = createApp(AppShell);
app.mount(resolveMountPoint());

window.ElosernVue = {
  stage: "showcase-core",
  app,
  logic: elosernLogic,
  protocolVersion: elosernLogic.Protocol.PROTOCOL_VERSION,
};
