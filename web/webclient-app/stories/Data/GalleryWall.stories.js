import { h, ref, toRaw } from "vue";
import GalleryWall from "../../components/GalleryWall.vue";
import {
  GALLERY_V4_EMPTY,
  GALLERY_V4_MINE,
  GALLERY_V4_MINE_ROSTER,
  GALLERY_V4_MONSTER,
  GALLERY_V4_PARTY,
  galleryStoryModel,
} from "../gallery-fixtures-v4.js";
import { atFullHd, atReference, windowViewportParameters } from "../window-viewports.js";

// GalleryWall (gallery-wall-component): the gallery window's centre, built
// and reviewed before the window exists. Committed v4 groups as aspect-true
// tiles; a subject that may hold several cards opens a tray under its row.
// The story frames the wall in the window's book grid (rail, wall, page) at
// the prototype's column proportions so tile sizes match the window; the rail
// and the page are empty surfaces here. Selection is local story state: a
// subject other than the committed one is shown with an empty tray, as the
// story server would publish it.

const render = (args) => ({
  setup() {
    const model = structuredClone(toRaw(args.model));
    const selectedSubject = ref(model.selected);
    const selectedImage = ref(args.selectedImage ?? null);
    const committed = (key) => key === model.selected;
    function onSelectSubject(key) {
      selectedSubject.value = key;
      selectedImage.value = null;
    }
    return () =>
      h("div", { class: "gallery-wall-story-host" }, [h("style", STORY_CSS), h("div", { class: "gallery-wall-story" }, [
        h("div", { class: "gallery-wall-story__rail", "aria-hidden": "true" }),
        h(GalleryWall, {
          groups: model.groups,
          selectedSubject: selectedSubject.value,
          cards: committed(selectedSubject.value) ? model.cards : [],
          officialEntries: committed(selectedSubject.value) ? model.official_entries : [],
          capabilities: model.capabilities,
          selectedImage: selectedImage.value,
          panel: model,
          ariaLabel: args.ariaLabel,
          pendingSubject: args.pendingSubject ?? null,
          "onSelect-subject": onSelectSubject,
          "onSelect-image": (id) => (selectedImage.value = id),
          onGenerate: () => (selectedImage.value = "generate"),
        }),
        h("div", { class: "gallery-wall-story__page", "aria-hidden": "true" }),
      ])]);
  },
});

// The window's book grid (the prototype's `.gwin` columns) inside a drawer
// inset, drawn with the game's ink surfaces. Story chrome only.
const STORY_CSS = `
.gallery-wall-story-host {
  box-sizing: border-box;
  height: calc(100vh - var(--header-h, 0px));
  padding: var(--sp-6);
  background: var(--ink-950);
}
.gallery-wall-story {
  display: grid;
  grid-template-columns: calc(84px * var(--ui-scale)) minmax(calc(360px * var(--ui-scale)), 0.82fr) minmax(0, 1.18fr);
  height: 100%;
  overflow: hidden;
  background: var(--ink-900);
  border: calc(1px * var(--ui-scale)) solid rgba(185, 154, 96, 0.35);
  border-radius: var(--radius);
}
.gallery-wall-story__rail {
  background: var(--ink-950);
  border-right: calc(1px * var(--ui-scale)) solid rgba(185, 154, 96, 0.2);
}
.gallery-wall-story__page { background: var(--ink-900); }
`;

export default {
  title: "Data/GalleryWall",
  component: GalleryWall,
  parameters: { layout: "fullscreen", ...windowViewportParameters },
  render,
};

// 我的角色 with a full roster: the live character is selected and its tray
// opens under the first row; the rest of the roster continues below it.
export const Mine = { ...atReference, args: { model: galleryStoryModel(GALLERY_V4_MINE_ROSTER), ariaLabel: "我的角色", selectedImage: GALLERY_V4_MINE_ROSTER.cards[0].image_id } };
// 隊友: one unlabelled group, the first companion selected with its card.
export const Party = { ...atReference, args: { model: galleryStoryModel(GALLERY_V4_PARTY), ariaLabel: "隊友" } };
// 魔物: threat-tier headings with seen / total; one card each, so no tray.
export const Monster = { ...atReference, args: { model: galleryStoryModel(GALLERY_V4_MONSTER), ariaLabel: "魔物" } };
// An enabled category with no subject.
export const Empty = { ...atReference, args: { model: galleryStoryModel(GALLERY_V4_EMPTY), ariaLabel: "隊友" } };
// Every tray state: the default card (crown, 預設), bound, custom-face and
// staged cards, a pending row (spinner, 生成中), a failed row (triangle,
// 生成失敗) and two read-only official images (double border), one selected.
export const TrayStates = {
  ...atReference,
  args: {
    model: galleryStoryModel(GALLERY_V4_MINE),
    ariaLabel: "我的角色",
    selectedImage: GALLERY_V4_MINE.official_entries[1].identity,
  },
};
// A subject selection in flight: the second character's tile is busy.
export const PendingSelection = {
  ...atReference,
  args: { model: galleryStoryModel(GALLERY_V4_MINE_ROSTER), ariaLabel: "我的角色", pendingSubject: GALLERY_V4_MINE_ROSTER.groups[0].subjects[2].subject_key },
};

export const MineFullHd = { ...atFullHd, args: Mine.args };
export const TrayStatesFullHd = { ...atFullHd, args: TrayStates.args };
