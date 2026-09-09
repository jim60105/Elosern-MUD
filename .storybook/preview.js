import { h } from "vue";
import "../web/webclient-app/styles/tokens.css";
import "../web/webclient-app/styles/fonts.css";
import "../web/webclient-app/styles/app-shell.css";

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
