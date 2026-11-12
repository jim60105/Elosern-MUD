import { h } from "vue";
import GalleryWindowPrototype from "./GalleryWindowPrototype.vue";
import { FIRST_RELEASE_DISABLED, GALLERY } from "./prototype-data.js";
import { atFullHd, atReference, windowViewportParameters } from "../../../web/webclient-app/stories/window-viewports.js";

// Design/GalleryWindow: the portrait gallery rebuilt as its own book-style
// window. Five rail categories replace the 24-row subject rail; a subject
// that may hold several images opens a tray under its row; portraits are
// 9:16 tiles and scenes 16:9. Reference only, synthetic fixtures; not
// imported by the app.

const render = (args, context) => ({
  render: () => h(GalleryWindowPrototype, { ...args, key: `${context.id}:${JSON.stringify(args.category)}` }),
});

export default {
  title: "Design/GalleryWindow",
  component: GalleryWindowPrototype,
  parameters: { layout: "fullscreen", ...windowViewportParameters },
  render,
  args: { gallery: GALLERY },
};

// 我的角色: every character of the account; the one being played is marked
// and its tray is open on its default image.
export const MyCharacters = { ...atReference, args: { category: "mine" } };
// The first specification: 人物 and 背景 stay on the rail, disabled with a reason.
export const FirstRelease = { ...atReference, args: { category: "mine", disabled: FIRST_RELEASE_DISABLED } };
// 隊友: the played character's party; the tray lists personal and official images.
export const Party = { ...atReference, args: { category: "party" } };
// A read-only official image selected: only the personal adjustments are offered.
export const OfficialImage = { ...atReference, args: { category: "mine", image: "o8" } };
// A character without any image: the tray holds only 生成新圖.
export const NoImages = { ...atReference, args: { category: "party", subject: "npc:13" } };
// 魔物: grouped by threat tier, one image each, so no tray; the heading counts
// the unseen species.
export const Monsters = { ...atReference, args: { category: "monster" } };
// 人物 (second specification): grouped by where each person was last met.
export const People = { ...atReference, args: { category: "people" } };
// 背景 (third specification): landscape tiles and a landscape page, no face
// frame and no stage transform.
export const Scenes = { ...atReference, args: { category: "scene" } };

export const MyCharactersFullHd = { ...atFullHd, args: { category: "mine" } };
export const MonstersFullHd = { ...atFullHd, args: { category: "monster" } };
export const ScenesFullHd = { ...atFullHd, args: { category: "scene" } };
