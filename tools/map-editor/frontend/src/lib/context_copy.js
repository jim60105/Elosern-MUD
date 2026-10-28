// The copy-only OMP context (frontend design §1.1, requirements §7): plain
// text identifying the selected objects, their workspace-relative source
// documents, qualified IDs, coordinate frames and units, and whether it came
// from the current files or a stale preview. It is built from an allowlist
// of snapshot fields only, so the launch token, session, segment, history,
// fingerprints and absolute paths can never appear. It states no ownership
// or agreement, starts nothing and calls nothing: copying is the only effect.

import { DOMAIN_LABELS } from "./objects.js";
import { DISCONNECTED } from "./workspace_client.js";
import { HOLD_RESTART } from "./following.js";
import { clock } from "./status.js";
import { storedPosition } from "./layout_edit.js";

// Authored text joins line-based text as one line: no pasted line can look
// like a separate instruction.
function oneLine(value) {
  return String(value ?? "").replace(/\s+/g, " ").trim();
}

// The first failing location only (path:line); the loader's message is left
// out, so nothing it embeds (an absolute path, a value) reaches the clipboard.
function failingLocation(workspace) {
  const [first] = workspace?.candidate_diagnostics ?? [];
  if (!first?.relative_path) return null;
  return first.line ? `${first.relative_path}:${first.line}` : first.relative_path;
}

export function currentness({ workspace, connection, hold }) {
  const at = clock(workspace?.snapshot_read_at);
  if (connection === DISCONNECTED) return { current: false, text: `過期預覽（服務未連線；最後可用版本 ${at}）` };
  if (hold === HOLD_RESTART) return { current: false, text: `過期預覽（服務已重啟；最後可用版本 ${at}）` };
  if (workspace?.preview_state === "stale") {
    const failing = failingLocation(workspace);
    return { current: false, text: `過期預覽（最後可用版本 ${at}${failing ? `；目前檔案無法載入：${failing}` : ""}）` };
  }
  return { current: true, text: `現行檔案（讀取於 ${at}）` };
}

function coordinates(world, entry) {
  if (entry.frame) return [oneLine(entry.frame)];
  if (entry.kind === "location") {
    const location = world.locations.find((row) => row.qualified_ref === entry.ref);
    return [
      `座標：格 (${location.cell[0]}, ${location.cell[1]})（1 km 格）；中心 東 ${location.centre_m[0]} m、北 ${location.centre_m[1]} m（大陸地理座標，公尺）`,
    ];
  }
  if (entry.kind === "node") {
    const settlement = world.settlements.find((row) => row.id === entry.mapId);
    const node = settlement.nodes.find((row) => row.qualified_ref === entry.ref);
    return [
      `座標：東 ${node.local_m[0]} m、北 ${node.local_m[1]} m（據點地方座標，公尺）；世界 東 ${node.world_m[0]} m、北 ${node.world_m[1]} m（大陸地理座標，公尺）`,
    ];
  }
  const interior = world.interiors.find((row) => row.id === entry.mapId);
  const position = storedPosition(interior, entry.id);
  const layout = interior.layout_relative_path;
  return [
    `版面：格 x ${position[0]}, y ${position[1]}（${layout ?? "無版面文件，依清單排列"}；版面僅供編輯器使用，不代表距離或座標）`,
  ];
}

export function ompContext({ workspace, connection = null, hold = null, catalog, refs = [], domain = null, mapId = null }) {
  const world = workspace?.world ?? null;
  const lines = ["[地圖編纂脈絡]", `來源：${currentness({ workspace, connection, hold }).text}`];
  const entries = refs.map((ref) => catalog.get(ref)).filter(Boolean);
  if (!world) {
    lines.push("目前沒有可用的預覽。");
    return lines.join("\n");
  }
  if (!entries.length) {
    const path =
      domain === "continent"
        ? world.continent.relative_path
        : (domain === "settlement" ? world.settlements : world.interiors).find((row) => row.id === mapId)?.relative_path;
    lines.push(`開啟的地圖：${DOMAIN_LABELS[domain] ?? domain} ${domain}${mapId ? ` · ${mapId}` : ""}`);
    if (path) lines.push(`文件：${path}`);
    lines.push("選取：（無）");
    return lines.join("\n");
  }
  const documents = new Set(entries.map((entry) => entry.relativePath));
  lines.push(`選取 ${entries.length} 個物件（${documents.size} 份文件）：`);
  for (const entry of entries) {
    lines.push(`- ${entry.ref}（${oneLine(entry.label)}）`);
    lines.push(`  領域：${DOMAIN_LABELS[entry.domain]} ${entry.domain}${entry.mapId ? ` · 地圖 ${entry.mapId}` : ""}`);
    lines.push(`  文件：${entry.relativePath}`);
    for (const line of coordinates(world, entry)) lines.push(`  ${line}`);
  }
  return lines.join("\n");
}
