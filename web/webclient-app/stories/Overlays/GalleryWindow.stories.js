import { h, ref, toRaw } from "vue";
import GalleryWindow from "../../components/GalleryWindow.vue";
import {
  GALLERY_V4_MINE,
  GALLERY_V4_MINE_BLANK,
  GALLERY_V4_MINE_ROSTER,
  GALLERY_V4_MONSTER,
  GALLERY_V4_PARTY,
  galleryStoryModel,
} from "../gallery-fixtures-v4.js";
import { atFullHd, atReference, windowViewportParameters } from "../window-viewports.js";

// GalleryWindow (gallery-window-component): the gallery as its own
// book-style window on the shared drawer chrome — the category rail, the
// subject wall with its inline tray, and the selected image's page — for side
// by side review with Design/GalleryWindow at both viewport sizes. Not
// mounted in the app yet. Deterministic and offline: synthetic v4 panels
// with story-only media; a press is shown in a status line and nothing is
// dispatched, so the window never waits for a commit here.

const render = (args, context) => ({
  setup() {
    const model = galleryStoryModel(structuredClone(toRaw(args.model)));
    const last = ref(null);
    const dispatch = (action, payload) => {
      last.value = `${action} ${JSON.stringify(payload)}`;
      return null;
    };
    return () =>
      h("div", { class: "gallery-window-story", key: context.id }, [
        h("style", STORY_CSS),
        h(GalleryWindow, { model, dispatch, onClose: () => {} }),
        last.value ? h("p", { class: "gallery-window-story__intent", role: "status" }, `送出 ${last.value}`) : null,
      ]);
  },
});

// Story chrome only: the stage behind the drawer and the intent line.
const STORY_CSS = `
.gallery-window-story { position: relative; width: 100%; height: 100vh; background: var(--ink-950); overflow: hidden; }
.gallery-window-story__intent {
  position: fixed; left: var(--sp-4); bottom: var(--sp-2); z-index: calc(var(--z-surface-modal) + 1);
  max-width: 60vw; margin: 0; padding: var(--sp-1) var(--sp-3); overflow: hidden; white-space: nowrap; text-overflow: ellipsis;
  color: var(--paper-200); font: var(--text-xs) var(--f-mono); background: var(--ink-900);
  border: calc(1px * var(--ui-scale)) solid var(--gold-600); border-radius: var(--radius-sm);
}
`;

export default {
  title: "Overlays/GalleryWindow",
  component: GalleryWindow,
  parameters: { layout: "fullscreen", ...windowViewportParameters },
  render,
};

// 我的角色: the account's characters, the one being played first and marked;
// its tray is open on its default image and the roster continues below it.
export const MyCharacters = { ...atReference, args: { model: GALLERY_V4_MINE_ROSTER } };
// The first release: 人物 and 背景 stay on the rail, disabled with a reason;
// the tray shows every card state and the official read-only run.
export const FirstRelease = { ...atReference, args: { model: GALLERY_V4_MINE } };
// 隊友: the played character's party, the first companion selected.
export const Party = { ...atReference, args: { model: GALLERY_V4_PARTY } };
// A subject with official images only: the current one opens selected and
// the footer offers the personal adjustments alone.
export const OfficialImage = { ...atReference, args: { model: { ...GALLERY_V4_MINE, cards: [], binding_warnings: [] } } };
// A character without any image: the tray holds only 生成新圖 and the page
// offers 生成新圖.
export const NoImages = { ...atReference, args: { model: GALLERY_V4_MINE_BLANK } };
// 魔物: threat-tier groups with seen / total; one image each, so no tray.
export const Monsters = { ...atReference, args: { model: GALLERY_V4_MONSTER } };

export const MyCharactersFullHd = { ...atFullHd, args: { model: GALLERY_V4_MINE_ROSTER } };
export const FirstReleaseFullHd = { ...atFullHd, args: { model: GALLERY_V4_MINE } };
export const MonstersFullHd = { ...atFullHd, args: { model: GALLERY_V4_MONSTER } };
