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
  // The redesign's sample scene paintings are served under `/art/showcase/`
  // too, so the stage-transition stories can hand the real `art` validator
  // (which accepts only `/art/`-rooted URLs) two distinct scene bitmaps to
  // crossfade between. Storybook only: the product never serves this path.
  staticDirs: [
    { from: "../web/static", to: "/" },
    { from: "../web/webclient-app/assets/redesign", to: "/art/showcase" },
  ],
  framework: {
    name: "@storybook/vue3-vite",
    options: {},
  },
};

export default config;
