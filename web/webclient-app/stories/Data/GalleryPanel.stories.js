import { h, ref, toRaw } from "vue";
import GalleryPanel from "../../components/GalleryPanel.vue";
import OverlayHost from "../../components/OverlayHost.vue";
import { GALLERY_EMPTY, GALLERY_MONSTER, GALLERY_SAMPLE, galleryStoryModel } from "../gallery-fixtures.js";

export default { title: "Data/GalleryPanel", component: GalleryPanel };
export const Populated = { args: { model: galleryStoryModel() } };
export const Empty = { args: { model: galleryStoryModel(GALLERY_EMPTY) } };
export const Monster = { args: { model: galleryStoryModel(GALLERY_MONSTER) } };
export const Unavailable = { args: { model: { schema_version: 1, available: false, reason: { code: "gallery_unavailable", message: "目前無法讀取肖像圖庫。" } } } };
export const Locked = { args: { model: galleryStoryModel(), disabled: true } };

// Explicit fixture publications, not a second runtime service. The operator
// chooses success/rejection so every state is deterministic and inspectable.
export const Storyboard = {
  args: { model: galleryStoryModel() },
  render: (args) => ({
    setup() {
      const model = ref(structuredClone(toRaw(args.model)));
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
        const next = structuredClone(toRaw(model.value));
        const { action, payload } = request;
        if (success) {
          if (action === "gallery.subject.select") {
            model.value = galleryStoryModel(payload.subject_key.startsWith("portrait:monster:") ? GALLERY_MONSTER : GALLERY_EMPTY);
            model.value.selected = payload.subject_key;
          } else {
            if (action === "gallery.generate") {
              const pending = structuredClone(GALLERY_SAMPLE.cards[6]);
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
            if (action === "gallery.face_rect.update") next.cards.find((row) => row.image_id === payload.image_id).face_rect = { ...payload.face_rect };
            if (action === "gallery.binding.save") {
              const row = next.cards.find((item) => item.image_id === payload.image_id);
              row.binding_present = true;
              log.value = "展示用綁定已提交；條件由後續伺服器資料提供。";
            }
            // Explicit story-server counts; never production renderer logic.
            next.filters = {
              all: next.cards.length, defaults: next.cards.filter((row) => row.is_default).length,
              bound: next.cards.filter((row) => row.binding_present).length,
              pending: next.cards.filter((row) => row.status === "pending").length,
              failed: next.cards.filter((row) => row.status === "failed").length,
            };
            next.binding_warnings = next.binding_warnings.filter((warning) => next.cards.some((row) => row.image_id === warning.image_id));
            model.value = next;
          }
          revision.value += 1;
        }
        result.value = { requestId: request.id, outcome: success ? "success" : "rejected", message: success ? "操作完成。" : "補充提示詞不可超過 512 個字元。", presentationRevision: revision.value };
        log.value = result.value.message;
        waiting.value = null;
      }
      return () => h("div", [
        h(OverlayHost, { overlay: "gallery" }, { default: () => h(GalleryPanel, {
          model: model.value, result: result.value, revision: revision.value,
          disabled: !!waiting.value, dispatch,
          onLog: () => { log.value = result.value?.message || "尚無伺服器訊息。"; },
          onCharacter: () => { log.value = "正式介面會切換到目前角色的角色資料抽屜。"; },
        }) }),
        h("section", {
          class: "gallery-ui",
          style: "position:fixed;top:0;left:0;right:0;z-index:5000;background:#11151f;border-bottom:1px solid #c9ae75;padding:8px 16px;display:flex;align-items:center;gap:12px;font-size:12px",
          "aria-label": "分鏡展示控制",
        }, [
          h("strong", "互動分鏡"),
          h("button", { disabled: !waiting.value, onClick: () => publish(true) }, "發布成功"),
          h("button", { disabled: !waiting.value, onClick: () => publish(false) }, "發布拒絕"),
          h("button", { onClick: () => { model.value = galleryStoryModel(); revision.value++; } }, "發布初始圖庫"),
          h("span", { role: "status" }, log.value),
          h("details", [h("summary", "檢視操作意圖"), h("pre", { style: "position:absolute;top:50px;right:0;background:#111;padding:16px;max-width:480px;max-height:200px;overflow:auto" }, JSON.stringify(last.value, null, 2))]),
        ]),
      ]);
    },
  }),
};
