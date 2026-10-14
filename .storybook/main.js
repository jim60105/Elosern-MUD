/** @type {import('@storybook/vue3-vite').StorybookConfig} */
const config = {
  // The GM portal stories (gm-portal-s1-foundation) share the tooling, not
  // the game component layer; preview.js renders them under `.gm-root`.
  //
  // Approved redesign prototypes live beside their design documents under
  // docs/design/ (reference only, mock data, outside the webclient
  // component-coverage manifest).
  stories: [
    "../web/webclient-app/**/*.stories.js",
    "../web/admin-app/**/*.stories.js",
    "../docs/design/**/*.stories.js",
  ],
  // Serve the repo's static tree so story fixtures can use the production
  // `/art/...` media URL vocabulary (the committed built-in fallbacks live
  // at web/static/art/defaults/) instead of inventing asset-import URLs the
  // wire validators reject.
  //
  // The redesign's remaining sample painting (the unrelated guild hall) is
  // served under `/art/showcase/` for the stories that still frame a
  // decorative backdrop. The committed bundled scene illustrations under
  // `web/static/art/scenes/` reach the stories through the `../web/static`
  // mapping above as `/art/scenes/<key>.webp`, which is the same path the
  // running game serves them from.
  staticDirs: [
    { from: "../web/static", to: "/" },
    { from: "../web/webclient-app/assets/redesign", to: "/art/showcase" },
    // The game favicon (web/brand/, generated into web/static/favicon/):
    // Storybook uses a staticDirs entry that targets /favicon.svg as the
    // manager's favicon.
    { from: "../web/static/favicon/favicon.svg", to: "/favicon.svg" },
  ],
  framework: {
    name: "@storybook/vue3-vite",
    options: {},
  },
};

export default config;
