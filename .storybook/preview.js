import { h } from "vue";
import "../web/webclient-app/styles/tokens.css";
import "../web/webclient-app/styles/fonts.css";
import "../web/webclient-app/styles/fonts-hack.css";
import "../web/webclient-app/styles/app-shell.css";
import "../web/static/webclient/css/ansi_palette.css";
import { installUiScale } from "../web/webclient-app/lib/ui_scale.js";

// The live client's chrome factor, so a story viewed above 1080px height
// renders at the same proportional scale (webclient-proportional-ui-scale).
installUiScale();

export const decorators = [
  (story, context) => ({
    render: () => context.title === "Core/AppShell"
      ? h(story())
      : h("div", {
        class: "elosern elosern-root",
        style: { paddingTop: "var(--header-h)", boxSizing: "border-box", overflow: "auto" },
      }, [h(story())]),
  }),
];

export const initialGlobals = {
  backgrounds: { value: "ink-950" },
};

export const parameters = {
  layout: "fullscreen",
  backgrounds: {
    options: { "ink-950": { name: "ink-950", value: "#0b0d10" } },
  },
};
