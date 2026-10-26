// Design/MapEditor: the approved standalone map-editor frontend
// (docs/superpowers/specs/2026-10-26-map-editor-frontend-design.md) as an
// interactive reference prototype. Synthetic mock data; nothing is saved and
// no service is called. Outside the webclient component-coverage manifest.
//
// The preview renders Design/MapEditor stories without the game shell root
// (the editor never imports the shell CSS) but keeps the live --ui-scale, so
// 1451x790 shows the reference geometry and 2560x1440 the 1.4 cap.
//
// Keyboard: 1/2/3 domains; V N R E A tools; F6 / Shift+F6 cycle header →
// navigation → canvas → inspector → diagnostics; arrow keys walk objects on
// the focused canvas, Enter jumps to the first inspector field; Esc cancels
// the tool, then the field draft, then the selection; Delete shows the
// inline refusal; Alt+← returns after following an entrance; / focuses
// search. Single-key shortcuts never act inside a text field.
import { h } from "vue";
import MapEditorPrototype from "./MapEditorPrototype.vue";

const frame = (args) => ({
  render: () => h("div", { style: "height: 100vh;" }, [h(MapEditorPrototype, args)]),
});

// 200 % browser zoom: half the CSS viewport drawn at twice the size.
const zoomed = (args) => ({
  render: () =>
    h("div", { style: "width: 100vw; height: 100vh; overflow: hidden;" }, [
      h("div", { style: "width: 50vw; height: 50vh; transform: scale(2); transform-origin: 0 0;" }, [
        h(MapEditorPrototype, args),
      ]),
    ]),
});

export default {
  title: "Design/MapEditor",
  component: MapEditorPrototype,
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "獨立地圖編纂器的設計原型：遊戲墨夜主題的三欄工作台（導覽／畫布／檢查器＋診斷列）、頁首狀態膠囊與單一優先橫幅。外部 AI 編輯沒有特殊模式：檔案變更自動載入，由文件指紋防止覆寫。",
      },
    },
  },
};

// ① Continent: river control point selected, stale partition.
export const ContinentControlPoint = { render: frame, args: { initialDomain: "continent", initialSelection: "cp:4" } };

// ② Settlement: node with directed roads, references and multiline prose.
export const SettlementNodeSelected = { render: frame, args: { initialSelection: "north_gate_ave" } };

// Road tool with the explicit 建立雙向 option (two directed rows, one command).
export const SettlementBidirectionalRoad = { render: frame, args: { initialSelection: "bell_square", roadTool: true } };

// ③ Interior: coordinate-free room cards; layout-only note.
export const InteriorRooms = { render: frame, args: { initialDomain: "interior", initialSelection: "furnace_room" } };

// ④ Entrance followed from the interior: return button in the breadcrumb.
export const EntranceFollowed = {
  render: frame,
  args: { initialSelection: "entrance", followedFrom: "鍛冶工坊 · 前店" },
};

// Field draft (dashed gold) and a rejected integer with the error kept on the field.
export const FieldDraftAndError = { render: frame, args: { initialSelection: "north_gate_ave", draftDemo: true } };

// Delete refused inline with locatable references; no cascade, no modal.
export const DeleteRefused = { render: frame, args: { initialSelection: "north_gate_ave", deleteDemo: true } };

// External index unavailable: deletion refused, editing unaffected.
export const DeleteIndexUnavailable = {
  render: frame,
  args: { initialSelection: "north_gate_ave", deleteDemo: true, index: "unavailable" },
};

// Priority banner ①: service disconnected; last snapshot desaturated.
export const BannerDisconnected = { render: frame, args: { initialSelection: "north_gate_ave", banner: "disconnected" } };

// Priority banner ②: a save failed; disk still holds the prior version.
export const BannerSaveFailed = { render: frame, args: { initialSelection: "north_gate_ave", banner: "saveFailed" } };

// Priority banner ③: an external change arrived while a field draft is open.
export const BannerExternalChangeWithDraft = {
  render: frame,
  args: { initialSelection: "north_gate_ave", banner: "externalDraft" },
};

// Priority banner ④: externally written YAML does not load; stale preview.
export const BannerStalePreview = {
  render: frame,
  args: { initialSelection: "north_gate_ave", banner: "stale", diagnosticsOpen: true },
};

// No snapshot was ever loadable: explicit unavailable preview, not an empty map.
export const NoPreview = { render: frame, args: { noPreview: true, diagnosticsOpen: true } };

// Partition regeneration running: chip offers cancel; mutations are rejected by the service.
export const PartitionGenerating = {
  render: frame,
  args: { initialDomain: "continent", initialSelection: "cp:4", partition: "generating" },
};

// 200 % browser zoom at the 1451x790 reference: side columns become drawers.
export const Zoom200Drawers = { render: zoomed, args: { initialSelection: "north_gate_ave", drawers: true } };
