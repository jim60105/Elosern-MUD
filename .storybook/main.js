/** @type {import('@storybook/vue3-vite').StorybookConfig} */
const config = {
  stories: ["../web/webclient-app/**/*.stories.js"],
  // Serve the repo's static tree so story fixtures can use the production
  // `/art/...` media URL vocabulary (the committed built-in fallbacks live
  // at web/static/art/defaults/) instead of inventing asset-import URLs the
  // wire validators reject.
  staticDirs: [{ from: "../web/static", to: "/" }],
  framework: {
    name: "@storybook/vue3-vite",
    options: {},
  },
};

export default config;
