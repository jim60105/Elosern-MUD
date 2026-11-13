import { h, ref, toRaw } from "vue";
import GalleryImagePage from "../../components/GalleryImagePage.vue";
import { GALLERY_CATEGORY_LABELS } from "../../components/gallery-copy.js";
import {
  GALLERY_V4_MINE,
  GALLERY_V4_MINE_BLANK,
  GALLERY_V4_MONSTER,
  GALLERY_V4_SCENE_PANELS,
  galleryStoryModel,
} from "../gallery-fixtures-v4.js";
import { atFullHd, atReference, windowViewportParameters } from "../window-viewports.js";

// GalleryImagePage (gallery-image-page): the gallery window's right page,
// built and reviewed before the window exists. One selected image: the art at
// 9:16 beside its fact cells, and a footer whose buttons are what the
// subject's declared capabilities produce. The story frames the page in the
// window's book grid (rail, wall, page) at the prototype's column
// proportions so the page has the window's width; the rail and the wall are
// empty surfaces here. A press is shown in a status line instead of being
// dispatched; a host that dispatches sets `disabled` until the commit lands.

// A fixed minute clock: fixture cards were made around 1700000800 (epoch s).
const NOW = 1_700_086_400_000;

const render = (args) => ({
  setup() {
    const model = structuredClone(toRaw(args.model));
    const panel = args.description ? { ...model, description: args.description } : model;
    const subject = model.groups.flatMap((group) => group.subjects).find((row) => row.subject_key === model.selected) ?? null;
    const group = model.groups.find((row) => row.subjects.includes(subject));
    const selection = args.pick(model);
    const last = ref(null);
    return () =>
      h("div", { class: "gallery-page-story-host" }, [h("style", STORY_CSS), h("div", { class: "gallery-page-story" }, [
        h("div", { class: "gallery-page-story__rail", "aria-hidden": "true" }),
        h("div", { class: "gallery-page-story__wall", "aria-hidden": "true" }),
        h("div", { class: "gallery-page-story__page" }, [
          h(GalleryImagePage, {
            panel,
            subject,
            groupLabel: group?.label ?? null,
            categoryLabel: GALLERY_CATEGORY_LABELS[model.category],
            selection,
            now: NOW,
            onPress: (key) => (last.value = key),
          }),
          last.value ? h("p", { class: "gallery-page-story__intent", role: "status" }, `press: ${last.value}`) : null,
        ]),
      ])]);
  },
});

// The window's book grid (the prototype's `.gwin` columns) inside a drawer
// inset, drawn with the game's ink surfaces. Story chrome only.
const STORY_CSS = `
.gallery-page-story-host {
  box-sizing: border-box;
  height: calc(100vh - var(--header-h, 0px));
  padding: var(--sp-6);
  background: var(--ink-950);
}
.gallery-page-story {
  display: grid;
  grid-template-columns: calc(84px * var(--ui-scale)) minmax(calc(360px * var(--ui-scale)), 0.82fr) minmax(0, 1.18fr);
  height: 100%;
  overflow: hidden;
  background: var(--ink-900);
  border: calc(1px * var(--ui-scale)) solid rgba(185, 154, 96, 0.35);
  border-radius: var(--radius);
}
.gallery-page-story__rail {
  background: var(--ink-950);
  border-right: calc(1px * var(--ui-scale)) solid rgba(185, 154, 96, 0.2);
}
.gallery-page-story__wall {
  background: var(--ink-860);
  border-right: calc(1px * var(--ui-scale)) solid rgba(185, 154, 96, 0.28);
}
.gallery-page-story__page { position: relative; min-width: 0; min-height: 0; }
.gallery-page-story__intent {
  position: absolute;
  top: var(--sp-2);
  right: var(--sp-3);
  margin: 0;
  padding: calc(2px * var(--ui-scale)) var(--sp-3);
  color: var(--paper-400);
  font: var(--text-xs) var(--f-mono);
  background: var(--ink-950);
  border: calc(1px * var(--ui-scale)) dashed var(--ink-600);
  border-radius: var(--radius-sm);
}
`;

export default {
  title: "Data/GalleryImagePage",
  component: GalleryImagePage,
  parameters: { layout: "fullscreen", ...windowViewportParameters },
  render,
};

const card = (index) => (model) => ({ type: "card", row: model.cards[index] });
const officialEntry = (index) => (model) => ({ type: "official", row: model.official_entries[index] });

const MINE = galleryStoryModel(GALLERY_V4_MINE);

// A character's spare card: chips, a binding condition, every capability.
const characterCard = { model: MINE, pick: card(1) };
// The default card: crown and 目前預設; 設為預設 is disabled with that reason.
const defaultCard = { model: MINE, pick: card(0) };
// A monster's only card: one-card kind, 臉框 · 舞台位置 · 重新生成, no 狀態.
// The description shows the letter box a subject's prose fills.
const monsterCard = {
  model: galleryStoryModel(GALLERY_V4_MONSTER),
  pick: card(0),
  description: "（示意文字）棲息在山谷霧氣中的生物，夜裡才會靠近旅人的營火。",
};
// The current official image: read-only art (double border), 清除選取.
const officialImage = { model: MINE, pick: officialEntry(1) };
// A card still generating: no button, the page says 生成中.
const pendingCard = { model: MINE, pick: card(4) };
// A failed card: its committed label carries the reason; 重新生成 only.
const failedCard = { model: MINE, pick: card(5) };
// A subject without any image: 生成新圖.
const noImage = { model: galleryStoryModel(GALLERY_V4_MINE_BLANK), pick: () => ({ type: "empty" }) };
// A scene's generated image (gallery-landscape-page): the landscape page, the
// 16:9 art above, the description left and the facts right; 生成圖 with
// 刪除 · 重新生成.
const sceneCard = { model: galleryStoryModel(GALLERY_V4_SCENE_PANELS.generated), pick: card(0) };
// A scene without a generated image: its bundled tile artwork as 官方內建圖,
// 生成新圖.
const sceneBundled = { model: galleryStoryModel(GALLERY_V4_SCENE_PANELS.bundled), pick: () => ({ type: "empty" }) };

// 刪除 pressed once: the alert warning, 確認刪除 and 取消 (focused).
async function armDelete({ canvasElement }) {
  for (let frame = 0; frame < 60; frame += 1) {
    const button = canvasElement.querySelector('[data-testid="gallery-page__delete"]');
    if (button) {
      button.click();
      return;
    }
    await new Promise((resolve) => requestAnimationFrame(resolve));
  }
}

export const CharacterCard = { ...atReference, args: characterCard };
export const DefaultCard = { ...atReference, args: defaultCard };
export const MonsterCard = { ...atReference, args: monsterCard };
export const OfficialEntry = { ...atReference, args: officialImage };
export const Pending = { ...atReference, args: pendingCard };
export const Failed = { ...atReference, args: failedCard };
export const Empty = { ...atReference, args: noImage };
export const ArmedDelete = { ...atReference, args: characterCard, play: armDelete };
export const Scenes = { ...atReference, args: sceneCard };
export const SceneBundled = { ...atReference, args: sceneBundled };

export const CharacterCardFullHd = { ...atFullHd, args: characterCard };
export const DefaultCardFullHd = { ...atFullHd, args: defaultCard };
export const MonsterCardFullHd = { ...atFullHd, args: monsterCard };
export const OfficialEntryFullHd = { ...atFullHd, args: officialImage };
export const PendingFullHd = { ...atFullHd, args: pendingCard };
export const FailedFullHd = { ...atFullHd, args: failedCard };
export const EmptyFullHd = { ...atFullHd, args: noImage };
export const ArmedDeleteFullHd = { ...atFullHd, args: characterCard, play: armDelete };
export const ScenesFullHd = { ...atFullHd, args: sceneCard };
export const SceneBundledFullHd = { ...atFullHd, args: sceneBundled };
