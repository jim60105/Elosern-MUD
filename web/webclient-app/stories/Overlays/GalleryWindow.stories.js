import { h, ref, toRaw } from "vue";
import GalleryWindow from "../../components/GalleryWindow.vue";
import {
  GALLERY_V4_EMPTY,
  GALLERY_V4_MINE,
  GALLERY_V4_MINE_BLANK,
  GALLERY_V4_MINE_ROSTER,
  GALLERY_V4_MONSTER,
  GALLERY_V4_PARTY,
  GALLERY_V4_PEOPLE,
  galleryStoryModel,
} from "../gallery-fixtures-v4.js";
import { atFullHd, atReference, windowViewportParameters } from "../window-viewports.js";

// GalleryWindow (gallery-window-component): the gallery as its own
// book-style window on the shared drawer chrome — the category rail, the
// subject wall with its inline tray, and the selected image's page — for side
// by side review with Design/GalleryWindow at both viewport sizes. Mounted in
// the app under the `gallery` drawer key (gallery-window-mount). Deterministic
// and offline: synthetic v4 panels with story-only media; in the state stories
// a press is shown in a status line and nothing is dispatched, so the window
// never waits for a commit. The Storyboard story publishes explicit results.

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
// 人物: met people grouped by place, one place expanded and its first person
// selected; the other places are heading buttons carrying their count, and a
// press shows the gallery.group.select it would send.
export const People = { ...atReference, args: { model: GALLERY_V4_PEOPLE } };

export const MyCharactersFullHd = { ...atFullHd, args: { model: GALLERY_V4_MINE_ROSTER } };
export const FirstReleaseFullHd = { ...atFullHd, args: { model: GALLERY_V4_MINE } };
export const MonstersFullHd = { ...atFullHd, args: { model: GALLERY_V4_MONSTER } };
export const PeopleFullHd = { ...atFullHd, args: { model: GALLERY_V4_PEOPLE } };

// ---- the interactive storyboard ---------------------------------------------

// The committed panel the story server publishes for each category, and the
// two no-image frames: committed official rows with no card rows, and
// no official rows with no card rows. All route through galleryStoryModel, so
// the offline build serves committed local artwork and needs no game, AI, or
// image service.
const BY_CATEGORY = { mine: GALLERY_V4_MINE, party: GALLERY_V4_PARTY, monster: GALLERY_V4_MONSTER };
const OFFICIAL_ONLY = { ...GALLERY_V4_MINE_BLANK, official_entries: GALLERY_V4_MINE.official_entries };

// The story server's answer to one successful request: the next committed
// panel. Explicit fixture publications, not a second runtime service.
function publishSuccess(current, { action, payload }) {
  if (action === "gallery.category.select") {
    return galleryStoryModel(BY_CATEGORY[payload.category] ?? { ...GALLERY_V4_EMPTY, category: payload.category });
  }
  if (action === "gallery.subject.select") {
    // Another listed subject of the same category: the story server
    // publishes it with no artwork yet.
    const base = BY_CATEGORY[current.category] ?? GALLERY_V4_MINE;
    return galleryStoryModel(payload.subject_key === base.selected ? base : {
      ...base, selected: payload.subject_key, cards: [], official_entries: [], binding_warnings: [], error_state: null,
    });
  }
  const next = structuredClone(toRaw(current));
  const card = next.cards.find((row) => row.image_id === payload.image_id);
  if (action === "gallery.generate") {
    const pending = structuredClone(GALLERY_V4_MINE.cards.find((row) => row.status === "pending"));
    next.cards = next.cards.filter((row) => row.status !== "pending");
    pending.created_at = 1700000900;
    next.cards.unshift(pending);
  }
  if (action === "gallery.card.delete") next.cards = next.cards.filter((row) => row.image_id !== payload.image_id);
  if (action === "gallery.default.set") next.cards.forEach((row) => {
    row.is_default = row.image_id === payload.image_id;
    row.chips = row.chips.filter((chip) => chip !== "目前預設");
    if (row.is_default) row.chips.push("目前預設");
  });
  // The rectangle and the stage live in the row's own canonical descriptor:
  // the story server rewrites that exact candidate's geometry.
  if (action === "gallery.face_rect.update") card.artwork.attempts[0].resource.geometry.face_rect = { ...payload.face_rect };
  if (action === "gallery.stage.update") card.artwork.attempts[0].resource.geometry.stage = { ...payload.stage };
  if (action === "gallery.binding.save") card.binding_present = true;
  if (action === "gallery.official.select") next.official_entries.forEach((row) => { row.is_current = row.identity === payload.identity; });
  if (action === "gallery.official.clear_selection") next.official_entries.forEach((row) => { row.is_current = false; });
  next.binding_warnings = next.binding_warnings.filter((warning) => next.cards.some((row) => row.image_id === warning.image_id));
  return next;
}

const STORYBOARD_CSS = `
.gallery-storyboard__bar {
  position: fixed; top: 0; left: 0; right: 0; z-index: calc(var(--z-surface-modal) + 10);
  display: flex; flex-wrap: wrap; align-items: center; gap: var(--sp-2) var(--sp-3);
  padding: var(--sp-2) var(--sp-4); box-sizing: border-box;
  color: var(--paper-100); font: var(--text-sm) var(--f-sans);
  background: var(--ink-900); border-bottom: calc(1px * var(--ui-scale)) solid var(--gold-600);
}
.gallery-storyboard__bar strong { font-family: var(--f-display); color: var(--gold-300); letter-spacing: 0.08em; }
.gallery-storyboard__bar button {
  min-height: calc(32px * var(--ui-scale)); padding: 0 var(--sp-3);
  color: var(--paper-100); font: inherit; background: var(--ink-860);
  border: calc(1px * var(--ui-scale)) solid var(--gold-600); border-radius: var(--radius-sm); cursor: pointer;
}
.gallery-storyboard__bar button:disabled { opacity: 0.45; cursor: not-allowed; }
.gallery-storyboard__bar button:focus-visible { outline: none; box-shadow: var(--focus); }
.gallery-storyboard__status { flex: 1; min-width: 0; color: var(--paper-300); }
.gallery-storyboard__intent { position: relative; }
.gallery-storyboard__intent pre {
  position: absolute; top: 100%; right: 0; max-width: calc(480px * var(--ui-scale)); max-height: calc(220px * var(--ui-scale));
  margin: var(--sp-1) 0 0; padding: var(--sp-3); overflow: auto;
  font: var(--text-xs) var(--f-mono); background: var(--ink-950); border: calc(1px * var(--ui-scale)) solid var(--gold-600);
}
`;

// The interactive storyboard (webclient-gallery-ui): the real window, its
// drawers and dialogs, driven by the story-only publication bar on top. The
// operator chooses success or rejection for each sent request, so every
// state is deterministic and inspectable. The frame guide is
// docs/design/legacy-design/elosern-redesign2/gallery-storyboard.md.
export const Storyboard = {
  ...atReference,
  args: { model: GALLERY_V4_MINE },
  render: (args, context) => ({
    setup() {
      const model = ref(galleryStoryModel(structuredClone(toRaw(args.model))));
      const result = ref(null);
      const revision = ref(1);
      const waiting = ref(null);
      const last = ref(null);
      const log = ref("");
      let serial = 0;
      function dispatch(action, payload) {
        if (waiting.value) return null;
        const request = { id: `story:${++serial}`, action, payload };
        waiting.value = request;
        last.value = request;
        log.value = "等待展示用伺服器回覆。請選擇「發布成功」或「發布拒絕」。";
        return request.id;
      }
      function publish(success) {
        const request = waiting.value;
        if (!request) return;
        if (success) {
          model.value = publishSuccess(model.value, request);
          revision.value += 1;
        }
        result.value = {
          requestId: request.id,
          outcome: success ? "success" : "rejected",
          message: success ? "操作完成。" : "補充提示詞不可超過 512 個字元。",
          presentationRevision: revision.value,
        };
        log.value = result.value.message;
        waiting.value = null;
      }
      function republish(panel) {
        model.value = galleryStoryModel(panel);
        revision.value += 1;
      }
      return () =>
        h("div", { class: "gallery-window-story", key: context.id }, [
          h("style", STORY_CSS + STORYBOARD_CSS),
          h(GalleryWindow, {
            model: model.value, result: result.value, revision: revision.value,
            disabled: !!waiting.value, dispatch,
            onClose: () => { log.value = "正式介面會關閉圖庫視窗並把焦點還給 圖庫 工具。"; },
            onLog: () => { log.value = result.value?.message || "尚無伺服器訊息。"; },
            onCharacter: () => { log.value = "正式介面會切換到目前角色的狀態分頁。"; },
          }),
          h("section", { class: "gallery-storyboard__bar", "aria-label": "分鏡展示控制" }, [
            h("strong", "互動分鏡"),
            h("button", { type: "button", disabled: !waiting.value, onClick: () => publish(true) }, "發布成功"),
            h("button", { type: "button", disabled: !waiting.value, onClick: () => publish(false) }, "發布拒絕"),
            h("button", { type: "button", onClick: () => republish(GALLERY_V4_MINE) }, "發布初始圖庫"),
            h("button", { type: "button", onClick: () => republish(OFFICIAL_ONLY) }, "發布僅官方圖片"),
            h("button", { type: "button", onClick: () => republish(GALLERY_V4_MINE_BLANK) }, "發布無官方空圖庫"),
            h("span", { class: "gallery-storyboard__status", role: "status" }, log.value),
            h("details", { class: "gallery-storyboard__intent" }, [
              h("summary", "檢視操作意圖"),
              h("pre", JSON.stringify(last.value, null, 2)),
            ]),
          ]),
        ]);
    },
  }),
};
