<script setup>
// The map editor workbench (frontend design §2-§6) over the service's
// complete authoritative snapshot: header with domain tabs, breadcrumb,
// return button and status chips; one priority banner; the navigation,
// canvas and inspector columns (drawers when they cannot fit); and the
// diagnostics strip. The page follows the workspace files continuously
// (adopting external changes, held behind open drafts until 載入新版), keeps
// the selection by qualified identity, and runs guarded single-document
// commands (interior room layout moves; continental geometry, locations,
// districts, footprints and bindings; local maps, settlement nodes,
// prototypes, directed roads and bends) with undo/redo of the manual
// segment. Copying the OMP context only writes plain text to the clipboard;
// it starts nothing.
// Authored text is rendered with text interpolation only (never v-html).
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import MapCanvas from "./components/MapCanvas.vue";
import LayoutPositionFields from "./components/LayoutPositionFields.vue";
import NavigationPanel from "./components/NavigationPanel.vue";
import InspectorPanel from "./components/InspectorPanel.vue";
import DiagnosticsStrip from "./components/DiagnosticsStrip.vue";
import ContinentInspector from "./components/ContinentInspector.vue";
import SettlementInspector from "./components/SettlementInspector.vue";
import {
  KM,
  cellOfMetres,
  deleteLocation,
  documentCommand,
  featurePoints,
  insertPoint,
  insertionIndex,
  locationField,
  movePoint,
  nextId,
  parseContinentRef,
  removalOf,
  sameStored,
  siteField,
  storedFromMetres,
  footprintCell,
} from "./lib/continent.js";
import {
  NUDGE_M,
  deleteNodes,
  findSettlement,
  groupMoves,
  moveBend,
  moveNodes,
  nextId as nextNodeId,
  nodeBlockers,
  oneDocumentNodes,
  parseSettlementRef,
  roundPoint,
  settlementRemoval,
} from "./lib/settlement.js";
import { CONNECTING, DISCONNECTED, createWorkspaceClient } from "./lib/workspace_client.js";
import { ADOPT, HOLD_DRAFT, HOLD_RESTART, followDecision, preserveSelection } from "./lib/following.js";
import { workspaceBanner } from "./lib/banner.js";
import { createCommandClient } from "./lib/command_client.js";
import { findInterior, fromScene, moveCommand, parseRoomRef, storedPosition } from "./lib/layout_edit.js";
import { saveChip, saveState, FAILED, UNCERTAIN } from "./lib/persistence.js";
import { sceneFor } from "./lib/map_scene.js";
import { indexChip, partitionChip, syncChip } from "./lib/status.js";
import { inspect, mapTitle, sourcePathFor, worldTree } from "./lib/world_index.js";
import { locate, objectCatalog } from "./lib/objects.js";
import { searchObjects } from "./lib/search.js";
import { nextSelection } from "./lib/selection.js";
import { selectionSummary } from "./lib/selection_owner.js";
import { incomingOf, relationsOf } from "./lib/relations.js";
import { UNAVAILABLE as NOTHING_REFUSES, deletionRefusal } from "./lib/deletion.js";
import { diagnosticGroups, groupCounts } from "./lib/diagnostics.js";
import { defaultHiddenLayers, visibleScene } from "./lib/layers.js";
import { ompContext } from "./lib/context_copy.js";
import { cycleRegion, isMacPlatform, isTextTarget, resolveKey, shortcutLabel } from "./lib/keyboard.js";
import { DOMAIN_KEYS, TOOLS, pushReturn, toolKeys, useDrawers } from "./lib/workbench.js";

const client = ref({ connection: CONNECTING, workspace: null, error: null });
const domain = ref("continent");
const mapIds = ref({ settlement: null, interior: null });
const selection = ref([]);
const diagnosticsOpen = ref(false);
const persistence = ref({ inFlight: 0, failure: null, savedAt: null, lastDocument: null });
// Open field drafts of the layout fields and the continent inspector.
const layoutDrafts = ref(0);
// One counter per inspector placement: the lead-slot and record-slot
// instances can mount and unmount in either order without overwriting the
// other's count.
const continentDrafts = ref(0);
const leadDrafts = ref(0);
const settlementDrafts = ref(0);
const settlementLeadDrafts = ref(0);
const draftCount = computed(
  () => layoutDrafts.value + continentDrafts.value + leadDrafts.value + settlementDrafts.value + settlementLeadDrafts.value,
);
// Continent tool state: a two-click waterway start, an open creation form
// and a hint when a tool has no target. Never persisted, never sent.
const pendingStart = ref(null);
// Settlement road tool: the chosen source node while the destination is picked.
const roadStart = ref(null);
const creation = ref(null);
const toolHint = ref(null);
// The snapshot on screen (commands are built against it), the newest held
// one, why it is held, and a form epoch that discards drafts when bumped.
const displayed = ref(null);
const pending = ref(null);
const hold = ref(null);
const formEpoch = ref(0);
const removedSelection = ref([]);
// Workbench view state: never persisted, never sent.
const hiddenLayers = ref(defaultHiddenLayers());
const tool = ref("select");
const returnStack = ref([]);
const query = ref("");
const refusalShown = ref(false);
const copyNotice = ref(null);
const viewport = ref({ width: 1451, scale: 1 });
const drawer = ref(null); // null | "nav" | "inspector"
const mac = isMacPlatform();

const root = ref(null);
const canvasRef = ref(null);
const inspectorRef = ref(null);
const navToggle = ref(null);
const inspectorToggle = ref(null);

const workspace = computed(() => displayed.value);
const world = computed(() => workspace.value?.world ?? null);
const catalog = computed(() => objectCatalog(world.value));
const selected = computed(() => (selection.value.length === 1 ? selection.value[0] : null));

let workspaceClient = null;
let commands = null;
onMounted(() => {
  workspaceClient = createWorkspaceClient({
    fetchImpl: (...args) => window.fetch(...args),
    EventSourceImpl: window.EventSource,
    onChange: (next) => {
      client.value = next;
      offer(next.workspace);
    },
  });
  // One manual segment per page load: a refresh never inherits undo/redo.
  commands = createCommandClient({
    fetchImpl: (...args) => window.fetch(...args),
    getWorkspace: () => displayed.value,
    refetch: () => workspaceClient.refetch(),
    onChange: (next) => {
      persistence.value = next;
    },
  });
  workspaceClient.start();
  measure();
  window.addEventListener("keydown", onKeydown);
  window.addEventListener("beforeunload", onBeforeUnload);
  window.addEventListener("resize", measure);
  document.addEventListener("copy", onCopy);
});
onBeforeUnmount(() => {
  workspaceClient?.stop();
  window.removeEventListener("keydown", onKeydown);
  window.removeEventListener("beforeunload", onBeforeUnload);
  window.removeEventListener("resize", measure);
  document.removeEventListener("copy", onCopy);
});

// -- file following ----------------------------------------------------------
function adopt(next) {
  displayed.value = next;
  pending.value = null;
  hold.value = null;
  if (next) commands?.clearRejection(next);
}

function offer(incoming) {
  if (!incoming || incoming === displayed.value || incoming === pending.value) return;
  const decision = followDecision({ displayed: displayed.value, incoming, drafts: draftCount.value });
  if (decision === ADOPT) {
    adopt(incoming);
  } else {
    pending.value = incoming;
    hold.value = decision;
  }
}

// The last draft resolved and its command (if confirmed) has its answer:
// nothing is lost by adopting the held change now. A confirmed draft is
// therefore always built against the snapshot it was typed on.
watch([draftCount, () => persistence.value.inFlight], ([count, inFlight]) => {
  if (count === 0 && inFlight === 0 && hold.value === HOLD_DRAFT) adopt(pending.value);
});

// A lost connection abandons queued commands: nothing is replayed later.
watch(
  () => client.value.connection,
  (connection) => {
    if (connection === DISCONNECTED) commands?.abandon();
  },
);

async function reconnect() {
  commands?.abandon();
  await workspaceClient.refetch();
  const fresh = client.value.workspace;
  if (fresh && fresh !== displayed.value && !client.value.error) {
    formEpoch.value += 1;
    adopt(fresh);
  }
}

function loadNewVersion() {
  if (!pending.value) return;
  formEpoch.value += 1;
  adopt(pending.value);
}

// Keep the open maps and the selection by stable identity across snapshots.
watch(world, (next) => {
  if (!next) return;
  const settlementIds = next.settlements.map((s) => s.id);
  const interiorIds = next.interiors.map((i) => i.id);
  if (!settlementIds.includes(mapIds.value.settlement)) mapIds.value.settlement = settlementIds[0] ?? null;
  if (!interiorIds.includes(mapIds.value.interior)) mapIds.value.interior = interiorIds[0] ?? null;
  const { kept, removed } = preserveSelection(selection.value, (ref) => catalog.value.has(ref));
  if (removed.length) {
    selection.value = kept;
    removedSelection.value = removed;
  }
});
watch(selection, (refs) => {
  if (refs.length) removedSelection.value = [];
  refusalShown.value = false;
});
const connectionState = computed(() => (hold.value === HOLD_RESTART ? "restarted" : client.value.connection));
const canvasStale = computed(
  () =>
    workspace.value?.preview_state === "stale" ||
    client.value.connection === DISCONNECTED ||
    hold.value === HOLD_RESTART,
);

// -- workbench ---------------------------------------------------------------
const DOMAINS = [
  { key: "continent", label: "大陸", chip: "1" },
  { key: "settlement", label: "據點", chip: "2" },
  { key: "interior", label: "室內", chip: "3" },
];
const FRAMES = { continent: "地理座標（公尺）· 1 km 格", settlement: "地方座標（公尺）", interior: "版面格（非距離）" };
const currentMapId = computed(() => (domain.value === "continent" ? null : mapIds.value[domain.value]));
const fullScene = computed(() => sceneFor(world.value, domain.value, currentMapId.value, selection.value));
const scene = computed(() => visibleScene(fullScene.value, hiddenLayers.value));
const title = computed(() => crumbFor(domain.value, currentMapId.value));
const sourcePath = computed(() => sourcePathFor(world.value, domain.value, currentMapId.value));
const frameLabel = computed(() => [FRAMES[domain.value], sourcePath.value].filter(Boolean).join(" · "));
const tree = computed(() => worldTree(world.value));
const objects = computed(() => scene.value?.items ?? scene.value?.marks ?? []);
const record = computed(() => inspect(world.value, selected.value));
const summary = computed(() => selectionSummary(catalog.value, selection.value));
const relations = computed(() =>
  relationsOf(world.value, workspace.value?.external_incoming_references ?? {}, selected.value),
);
const refusal = computed(() => {
  if (!refusalShown.value || !selection.value.length) return null;
  const rows = incomingOf(world.value, workspace.value?.external_incoming_references ?? {}, selection.value);
  return refusalFor(selection.value, rows);
});

function refusalFor(refs, rows) {
  const location = refs.length === 1 && refs[0].startsWith("location:");
  // Settlement nodes: every map reference (roads either way, gates, the city
  // gate, exteriors, landmarks) must be removed first, as the service guard
  // requires; external rows come from the index lookup.
  const nodes = oneDocumentNodes(refs);
  return deletionRefusal({
    externalStatus: workspace.value?.external_context_status,
    summary: summary.value,
    relations: nodes ? [...nodeBlockers(world.value, refs), ...rows.filter((row) => row.external)] : rows,
    internalBlocks: location || Boolean(nodes),
  });
}
const results = computed(() => searchObjects(catalog.value, query.value));
const tools = computed(() => TOOLS[domain.value] ?? []);
const drawers = computed(() => useDrawers(viewport.value));

function crumbFor(key, mapId) {
  if (key !== "interior") return mapTitle(world.value, key, mapId);
  const interior = world.value?.interiors.find((item) => item.id === mapId);
  const exterior = interior?.exterior;
  return exterior ? `${mapTitle(world.value, "settlement", exterior.settlement)} › ${mapId}` : mapId ?? "";
}

const currentSaveState = computed(() =>
  saveState({
    workspace: workspace.value,
    inFlight: persistence.value.inFlight,
    failure: persistence.value.failure,
    drafts: draftCount.value,
  }),
);
const banner = computed(() =>
  workspaceBanner({
    workspace: workspace.value,
    connection: client.value.connection,
    hold: hold.value,
    pending: pending.value,
    drafts: draftCount.value,
    failure: persistence.value.failure,
  }),
);
const chips = computed(() => [
  { key: "save", name: "存檔", state: currentSaveState.value, ...saveChip(currentSaveState.value, persistence.value.savedAt) },
  { key: "sync", name: "檔案同步", state: workspace.value?.preview_state ?? "loading", ...syncChip(workspace.value, client.value.connection) },
  { key: "index", name: "索引", ...indexChip(workspace.value) },
  { key: "partition", name: "分區", ...partitionChip(workspace.value) },
]);
const groups = computed(() =>
  diagnosticGroups({
    workspace: workspace.value,
    world: world.value,
    catalog: catalog.value,
    failure: persistence.value.failure,
    connection: client.value.connection,
    hidden: hiddenLayers.value,
  }),
);
const counts = computed(() => groupCounts(groups.value));
const stripOpen = computed(() => diagnosticsOpen.value || (workspace.value && workspace.value.preview_state !== "current"));
const stripSummary = computed(() => [chips.value[1].text, chips.value[2].text, chips.value[3].text]);
const modifierLabel = shortcutLabel(mac);
const hints = `${modifierLabel}Z 復原 · Shift+${modifierLabel}Z 重做 · ${modifierLabel}C 複製脈絡 · F6 切換區域 · / 搜尋`;
const copyHint = mac ? "Meta+C" : "Control+C";
const settlementOptions = computed(() => world.value?.settlements.map((s) => s.id) ?? []);
const interiorOptions = computed(() => world.value?.interiors.map((i) => i.id) ?? []);
const returnLabel = computed(() => returnStack.value.at(-1)?.label ?? null);

function measure() {
  const scale = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--ui-scale")) || 1;
  viewport.value = { width: window.innerWidth, scale };
}
watch(drawers, (on) => {
  if (!on) drawer.value = null;
});

// -- navigation --------------------------------------------------------------
function here() {
  const first = catalog.value.get(selection.value[0]);
  const label = [crumbFor(domain.value, currentMapId.value), first?.label].filter(Boolean).join(" · ");
  return { domain: domain.value, mapId: currentMapId.value, selection: [...selection.value], label };
}

function show(key, mapId) {
  if (key !== domain.value) tool.value = "select";
  domain.value = key;
  if (mapId) mapIds.value = { ...mapIds.value, [key]: mapId };
}

// Cross-map navigation (search, diagnostics, relationships, local maps)
// keeps return context; focus lands on the destination's inspector heading,
// or on the canvas for a map-level target.
async function navigate({ domain: key, mapId = null, refs = [], layer = null }) {
  const before = here();
  const destination = key === "continent" ? null : mapId ?? mapIds.value[key];
  const moved = before.domain !== key || before.mapId !== destination;
  if (moved || refs.some((ref) => !before.selection.includes(ref))) {
    returnStack.value = pushReturn(returnStack.value, before);
  }
  if (layer && hiddenLayers.value.includes(layer)) hiddenLayers.value = hiddenLayers.value.filter((item) => item !== layer);
  show(key, mapId);
  selection.value = refs;
  await settleFocus(refs.length > 0);
}

async function settleFocus(toInspector) {
  if (drawers.value) drawer.value = toInspector ? "inspector" : null;
  await nextTick();
  if (toInspector) inspectorRef.value?.focusHeading();
  else root.value?.querySelector("[data-region='canvas']")?.focus();
}

async function goBack() {
  const entry = returnStack.value.at(-1);
  if (!entry) return;
  returnStack.value = returnStack.value.slice(0, -1);
  // The files may have changed since: return only to what still exists.
  const maps = entry.domain === "settlement" ? world.value?.settlements : world.value?.interiors;
  const mapId = entry.domain === "continent" || maps?.some((item) => item.id === entry.mapId) ? entry.mapId : null;
  show(entry.domain, mapId);
  selection.value = entry.selection.filter((ref) => catalog.value.has(ref));
  await settleFocus(selection.value.length > 0);
}

function openDomain(key) {
  show(key);
  selection.value = [];
}

function openTreeEntry(entry) {
  if (entry.domain === "continent") {
    show("continent");
    selection.value = entry.id.startsWith("location:") ? [entry.id] : [];
  } else {
    show(entry.domain, entry.mapId);
    selection.value = [];
  }
}

function follow(ref) {
  const target = locate(catalog.value, ref);
  if (!target) return;
  const layer = catalog.value.get(ref)?.layer ?? null;
  navigate({ domain: target.domain, mapId: target.mapId, refs: target.ref ? [target.ref] : [], layer });
}

function goDiagnostic(row) {
  const target = row.target;
  if (!target) return;
  navigate({ domain: target.domain, mapId: target.mapId, refs: target.ref ? [target.ref] : [], layer: target.layer });
}

function toggleLayer(key) {
  hiddenLayers.value = hiddenLayers.value.includes(key)
    ? hiddenLayers.value.filter((item) => item !== key)
    : [...hiddenLayers.value, key];
  if (domain.value !== "continent") return;
  // A selected object on a now-hidden layer leaves the selection.
  const visible = new Set(objects.value.map((mark) => mark.id));
  const kept = selection.value.filter((ref) => catalog.value.get(ref)?.domain !== "continent" || visible.has(ref));
  if (kept.length !== selection.value.length) selection.value = kept;
}

// -- selection ---------------------------------------------------------------
function choose({ ref, toggle = false, range = false }) {
  if (domain.value === "settlement" && tool.value === "road" && parseSettlementRef(ref)?.kind === "node") {
    pickRoadEnd(parseSettlementRef(ref).nodeId);
    return;
  }
  selection.value = nextSelection(selection.value, ref, { toggle, range, order: objects.value.map((mark) => mark.id) });
  if (drawers.value && selection.value.length && !toggle && !range) drawer.value = "inspector";
}

function chooseResult({ ref, toggle }) {
  if (toggle) {
    selection.value = nextSelection(selection.value, ref, { toggle: true });
    return;
  }
  const target = locate(catalog.value, ref);
  if (target) navigate({ domain: target.domain, mapId: target.mapId, refs: [ref], layer: catalog.value.get(ref)?.layer });
}

async function onCanvasEnter() {
  if (drawers.value) drawer.value = "inspector";
  await nextTick();
  inspectorRef.value?.focusFirstField();
}

// -- interior layout commands ----------------------------------------------
const selectedRoom = computed(() => {
  const room = parseRoomRef(selected.value);
  if (!room || domain.value !== "interior") return null;
  const interior = findInterior(world.value, room.interiorId);
  const position = interior && storedPosition(interior, room.roomId);
  return position ? { ...room, position } : null;
});
const layoutMovable = computed(() => Boolean(world.value));
const placing = computed(
  () => (domain.value === "continent" && tool.value !== "select") || (domain.value === "settlement" && tool.value === "node"),
);
// Nodes of one settlement document selected on the settlement map (the
// group a drag, Shift+arrow or the inspector's delta moves together).
const selectedNodes = computed(() => (domain.value === "settlement" ? oneDocumentNodes(selection.value) : null));
const showSettlementInspector = computed(
  () => domain.value === "settlement" && Boolean(world.value) && Boolean(findSettlement(world.value, currentMapId.value)),
);
const pendingPoints = computed(() => (pendingStart.value ? [pendingStart.value.point] : []));
const showContinentInspector = computed(
  () =>
    domain.value === "continent" &&
    Boolean(world.value) &&
    (Boolean(creation.value) || Boolean(toolHint.value) || (selected.value && (parseContinentRef(selected.value) || selected.value.startsWith("location:")))),
);

watch([tool, domain, currentMapId], () => {
  pendingStart.value = null;
  roadStart.value = null;
  creation.value = null;
  toolHint.value = null;
});

function submitMove(interiorId, roomId, positionOf) {
  // Built when its turn comes, against the snapshot the previous command left.
  return commands.submit((current) => {
    const interior = findInterior(current.world, interiorId);
    const from = interior && storedPosition(interior, roomId);
    if (!from) return null;
    const to = positionOf(from);
    if (to[0] === from[0] && to[1] === from[1]) return null;
    return moveCommand(current.world, interiorId, roomId, to);
  });
}

// -- continent commands ------------------------------------------------------
// One descriptor is one named command, built against the snapshot that is
// current when its turn comes (fingerprint included).
function send(descriptor) {
  return commands.submit((current) => documentCommand(current, descriptor));
}

function continentMove(id, point) {
  const parsed = parseContinentRef(id);
  if (parsed?.feature && parsed.index !== null) {
    const entry = featurePoints(world.value, parsed.feature)[parsed.index];
    const stored = storedFromMetres(world.value, id, point);
    return entry && !sameStored(entry.stored, stored) ? movePoint(id, stored) : null;
  }
  if (parsed?.kind === "site") {
    const site = world.value.continent.harbor_sites.find((row) => row.id === parsed.id);
    const cell = cellOfMetres(world.value, point);
    return site && !sameStored(site.cell, cell) ? siteField(parsed.id, "cell", cell) : null;
  }
  const location = world.value.locations.find((row) => row.qualified_ref === id);
  if (location) {
    const cell = cellOfMetres(world.value, point);
    return sameStored(location.cell, cell) ? null : locationField(location.id, "cell", cell);
  }
  return null;
}

function onPlace({ point }) {
  const current = world.value;
  if (current && domain.value === "settlement" && tool.value === "node") {
    placeNode(point);
    return;
  }
  if (!current || domain.value !== "continent") return;
  toolHint.value = null;
  const cell = cellOfMetres(current, point);
  if (tool.value === "point") {
    const ref = selected.value;
    const parsed = parseContinentRef(ref);
    if (!parsed?.feature) {
      toolHint.value = "加控制點：先選取大陸海岸線、林線或一條水系（或其中一個控制點）。";
      return;
    }
    const points = featurePoints(current, parsed.feature);
    let index;
    if (parsed.kind === "ford") index = points.length;
    else if (parsed.index !== null) index = parsed.index + 1;
    else index = insertionIndex(points.map((entry) => entry.m), point, { closed: parsed.kind === "mainland" });
    const stored = storedFromMetres(current, parsed.feature, point);
    send(insertPoint(parsed.feature, index, stored)).then((result) => {
      if (result?.changed) selection.value = [`${parsed.feature}#${index}`];
    });
  } else if (tool.value === "waterway") {
    if (!pendingStart.value) {
      pendingStart.value = { cell, point: { x: (cell[0] + 0.5) * cellSize(), y: (cell[1] + 0.5) * cellSize() } };
      toolHint.value = "水系：再點一次終點；Esc 取消。";
      return;
    }
    const start = pendingStart.value.cell;
    pendingStart.value = null;
    const ids = current.continent.waterways.map((row) => row.id);
    creation.value = { type: "waterway", route: [start, cell], defaults: { id: nextId("waterway", ids) } };
  } else if (tool.value === "ridge") {
    creation.value = { type: "pass", defaults: { id: "pass", y_min: String(cell[1]), y_max: String(cell[1] + 2) } };
  } else if (tool.value === "location") {
    const ids = [...current.locations.map((row) => row.id), ...current.continent.harbor_sites.map((row) => row.id)];
    creation.value = {
      type: "location",
      cell,
      defaults: { id: nextId("location", ids), as: "location", kind: "dungeon", display_name_zh: "", description: "" },
    };
  } else if (tool.value === "footprint") {
    const parsed = parseContinentRef(selected.value);
    const settlement = parsed?.kind === "footprint" ? current.settlements.find((row) => row.id === parsed.id) : null;
    if (!settlement?.footprint) {
      toolHint.value = "佔地：先選取一個據點佔地（物件清單或地點的檢查器）。";
      return;
    }
    const filled = settlement.footprint.cells.some(([x, y]) => x === cell[0] && y === cell[1]);
    send(footprintCell(current, settlement.id, cell, !filled));
  }
  if (drawers.value && (creation.value || toolHint.value)) drawer.value = "inspector";
}

// -- settlement commands ------------------------------------------------------
// Road tool: the first chosen node is the source, the second the
// destination; the creation form then asks for the authored direction(s).
function pickRoadEnd(nodeId) {
  toolHint.value = null;
  if (!roadStart.value) {
    roadStart.value = nodeId;
    creation.value = null;
    toolHint.value = "道路：再選取終點節點；Esc 取消。";
  } else {
    const source = roadStart.value;
    roadStart.value = null;
    creation.value = { type: "road", defaults: { source, destination: nodeId, direction: "", two_way: false, return_direction: "" } };
  }
  if (drawers.value) drawer.value = "inspector";
}

function placeNode(point) {
  const settlement = findSettlement(world.value, currentMapId.value);
  if (!settlement) return;
  const [x, y] = roundPoint(point);
  creation.value = {
    type: "node",
    defaults: {
      id: nextNodeId("node", settlement.nodes.map((row) => row.id)),
      x: String(x),
      y: String(y),
      key: "",
      desc: "",
      prototype_parent: "grid_room",
      anchor_key: null,
    },
  };
  if (drawers.value) drawer.value = "inspector";
}

// A drag of one node, or of a node inside a one-document multi-selection
// (the whole group moves by one integer metre delta), or of a bend.
function settlementMove(id, point) {
  const parsed = parseSettlementRef(id);
  const settlement = parsed && findSettlement(world.value, parsed.settlementId);
  if (!settlement) return null;
  const [x, y] = roundPoint(point);
  if (parsed.kind === "bend") {
    const road = settlement.roads.find((row) => row.source === parsed.source && row.destination === parsed.destination);
    const bend = road?.bends[parsed.index];
    return bend && (bend[0] !== x || bend[1] !== y) ? moveBend(settlement.id, parsed.source, parsed.destination, parsed.index, [x, y]) : null;
  }
  if (parsed.kind !== "node") return null;
  const node = settlement.nodes.find((row) => row.id === parsed.nodeId);
  if (!node) return null;
  const dx = x - node.local_m[0];
  const dy = y - node.local_m[1];
  if (!dx && !dy) return null;
  const group = oneDocumentNodes(selection.value);
  const ids = group && group.settlementId === settlement.id && group.nodeIds.includes(node.id) ? group.nodeIds : [node.id];
  return moveNodes(settlement.id, groupMoves(settlement, ids, dx, dy));
}

function nudgeNodes([dx, dy]) {
  const group = selectedNodes.value;
  // Built against the snapshot current when its turn comes.
  commands.submit((current) => {
    const settlement = findSettlement(current.world, group.settlementId);
    if (!settlement || !group.nodeIds.every((nodeId) => settlement.nodes.some((row) => row.id === nodeId))) return null;
    // The layout grid's ArrowUp is -y; the settlement frame is north-up.
    return documentCommand(current, moveNodes(settlement.id, groupMoves(settlement, group.nodeIds, dx * NUDGE_M, -dy * NUDGE_M)));
  });
}

function onCreateMap(descriptor, settlementId) {
  send(descriptor).then((result) => {
    if (result?.changed) navigate({ domain: "settlement", mapId: settlementId });
  });
}

function openCreation(request) {
  roadStart.value = null;
  toolHint.value = null;
  creation.value = request;
}

function cellSize() {
  return (world.value?.continent?.cell_size_km ?? 1) * KM;
}

function onCreate(descriptor, ref) {
  creation.value = null;
  send(descriptor).then((result) => {
    if (result?.changed && ref) selection.value = [ref];
  });
}

function cancelTool() {
  pendingStart.value = null;
  roadStart.value = null;
  creation.value = null;
  toolHint.value = null;
}

function onCanvasMove({ id, point, settle }) {
  if (domain.value === "settlement") {
    const descriptor = settlementMove(id, point);
    if (!selection.value.includes(id)) selection.value = [id];
    if (!descriptor) return settle();
    // A refused move (a coordinate already taken) settles back to the snapshot.
    send(descriptor).finally(settle);
    return;
  }
  if (domain.value === "continent") {
    const descriptor = continentMove(id, point);
    selection.value = [id];
    if (!descriptor) return settle();
    send(descriptor).finally(settle);
    return;
  }
  const room = parseRoomRef(id);
  if (!room) return settle();
  selection.value = [id];
  submitMove(room.interiorId, room.roomId, () => fromScene(point)).finally(settle);
}

function onFieldConfirm(position) {
  const room = selectedRoom.value;
  if (room) submitMove(room.interiorId, room.roomId, () => position);
}

// -- copy-only OMP context ---------------------------------------------------
function contextText() {
  return ompContext({
    workspace: workspace.value,
    connection: client.value.connection,
    hold: hold.value,
    catalog: catalog.value,
    refs: selection.value,
    domain: domain.value,
    mapId: currentMapId.value,
  });
}

let forceCopy = false;
function notice(state) {
  copyNotice.value = state === "ok" ? { state, text: "✓ 已複製 OMP 脈絡" } : { state, text: "✕ 無法寫入剪貼簿" };
}

// Native copy of a text selection or inside a field stays native; otherwise
// (keyboard, menu or the explicit action) the clipboard receives the context.
function onCopy(event) {
  if (!forceCopy) {
    if (isTextTarget(document.activeElement)) return;
    const textSelection = window.getSelection?.();
    if (textSelection && !textSelection.isCollapsed && String(textSelection).trim()) return;
  }
  if (!event.clipboardData) return;
  event.clipboardData.setData("text/plain", contextText());
  event.preventDefault();
  notice("ok");
}

function copyContext() {
  forceCopy = true;
  let done = false;
  try {
    done = document.execCommand("copy");
  } catch {
    // The asynchronous clipboard below is the fallback.
    done = false;
  } finally {
    forceCopy = false;
  }
  if (done) return;
  if (!navigator.clipboard) {
    notice("failed");
    return;
  }
  navigator.clipboard.writeText(contextText()).then(
    () => notice("ok"),
    () => notice("failed"),
  );
}

// -- keyboard and focus --------------------------------------------------------
function regions() {
  return [...(root.value?.querySelectorAll("[data-region]") ?? [])].filter((el) => el.getClientRects().length);
}

function openDrawer(which) {
  drawer.value = drawer.value === which ? null : which;
  if (drawer.value) {
    nextTick(() => root.value?.querySelector(`[data-region='${which === "nav" ? "nav" : "inspector"}']`)?.focus());
  }
}

function closeDrawer() {
  const which = drawer.value;
  drawer.value = null;
  nextTick(() => (which === "nav" ? navToggle.value : inspectorToggle.value)?.focus());
}

function trapTab(event) {
  const element = root.value?.querySelector(`[data-region='${drawer.value === "nav" ? "nav" : "inspector"}']`);
  if (!element) return;
  const focusable = [
    ...element.querySelectorAll("button, input, select, textarea, [tabindex]:not([tabindex='-1'])"),
  ].filter((el) => !el.disabled && el.getClientRects().length);
  if (!focusable.length) {
    event.preventDefault();
    element.focus();
    return;
  }
  const first = focusable[0];
  const last = focusable.at(-1);
  if (!element.contains(document.activeElement)) {
    event.preventDefault();
    first.focus();
  } else if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

function focusSearch() {
  if (drawers.value) drawer.value = "nav";
  nextTick(() => root.value?.querySelector("[data-search]")?.focus());
}

function inNudgeScope(target) {
  return Boolean(target?.closest?.("[data-region='canvas'], .objects"));
}

// Ctrl/⌘+C outside text fields copies the context; a text selection on the
// page keeps the browser's own copy.
function isContextCopy(event) {
  const primary = mac ? event.metaKey && !event.ctrlKey : event.ctrlKey && !event.metaKey;
  if (!primary || event.altKey || event.shiftKey || event.isComposing || String(event.key ?? "").toLowerCase() !== "c") return false;
  if (isTextTarget(event.target)) return false;
  const textSelection = window.getSelection?.();
  return !(textSelection && !textSelection.isCollapsed && String(textSelection).trim());
}

function onKeydown(event) {
  if (!commands) return;
  if (isContextCopy(event)) {
    event.preventDefault();
    copyContext();
    return;
  }
  if (event.key === "Tab" && drawer.value) {
    trapTab(event);
    return;
  }
  const action = resolveKey(event, {
    mac,
    text: isTextTarget(event.target),
    drawerOpen: Boolean(drawer.value),
    toolActive: tool.value !== "select" || Boolean(creation.value || pendingStart.value || roadStart.value),
    refusalShown: Boolean(refusal.value),
    hasSelection: selection.value.length > 0,
    nudgeScope: (Boolean(selectedRoom.value) || Boolean(selectedNodes.value)) && inNudgeScope(event.target),
    canReturn: returnStack.value.length > 0,
    domains: DOMAIN_KEYS,
    tools: toolKeys(domain.value),
  });
  if (!action) return;
  event.preventDefault();
  switch (action.type) {
    case "region": {
      const list = regions();
      const index = cycleRegion(list.length, list.findIndex((el) => el.contains(document.activeElement)), action.step);
      list[index]?.focus();
      break;
    }
    case "trap":
      break;
    case "escape":
      if (action.target === "drawer") closeDrawer();
      else if (action.target === "tool") {
        tool.value = "select";
        cancelTool();
      }
      else if (action.target === "refusal") refusalShown.value = false;
      else selection.value = [];
      break;
    case "save":
      // Save flushes accepted operations; it never forces a field draft.
      commands.flush();
      break;
    case "search":
      focusSearch();
      break;
    case "return":
      goBack();
      break;
    case "undo":
      commands.undo();
      break;
    case "redo":
      commands.redo();
      break;
    case "nudge": {
      if (selectedNodes.value) {
        nudgeNodes(action.delta);
        break;
      }
      const { interiorId, roomId } = selectedRoom.value;
      submitMove(interiorId, roomId, ([x, y]) => [x + action.delta[0], y + action.delta[1]]);
      break;
    }
    case "delete":
      requestDelete();
      break;
    case "domain":
      openDomain(action.domain);
      break;
    case "tool":
      tool.value = action.tool;
      break;
    default:
      break;
  }
}

function requestDelete() {
  if (!selection.value.length) return;
  if (selection.value.length === 1 && world.value) {
    const ref = selection.value[0];
    const settlementRemovalCommand = settlementRemoval(ref);
    if (settlementRemovalCommand) {
      // Roads and bends are owned by their settlement document only.
      const parsed = parseSettlementRef(ref);
      send(settlementRemovalCommand).then((result) => {
        if (result?.changed) selection.value = parsed.kind === "bend" ? [parsed.road] : [];
      });
      return;
    }
    const removal = removalOf(world.value, ref);
    if (removal) {
      // Geometry removals remove no qualified object: no index is involved.
      const feature = parseContinentRef(ref)?.feature;
      send(removal).then((result) => {
        if (result?.changed) selection.value = feature && parseContinentRef(ref).kind !== "ford" ? [feature] : [];
      });
      return;
    }
    if (ref.startsWith("location:")) {
      const rows = incomingOf(world.value, workspace.value?.external_incoming_references ?? {}, [ref]);
      if (refusalFor([ref], rows).key === NOTHING_REFUSES) {
        const id = ref.slice("location:".length);
        send(deleteLocation(id)).then((result) => {
          if (result?.changed) selection.value = [];
        });
        return;
      }
    }
  }
  const nodes = world.value ? oneDocumentNodes(selection.value) : null;
  if (nodes) {
    const rows = incomingOf(world.value, workspace.value?.external_incoming_references ?? {}, selection.value);
    if (refusalFor(selection.value, rows).key === NOTHING_REFUSES) {
      send(deleteNodes(nodes.settlementId, nodes.nodeIds)).then((result) => {
        if (result?.changed) selection.value = [];
      });
      return;
    }
  }
  refusalShown.value = true;
  nextTick(() => root.value?.querySelector("[data-delete-refusal]")?.scrollIntoView({ block: "nearest" }));
}

function onBeforeUnload(event) {
  // Resolve drafts and pending saves before leaving; nothing is restored later.
  if (draftCount.value > 0 || persistence.value.inFlight > 0) {
    event.preventDefault();
    event.returnValue = "";
  }
}

function onBannerAction(action) {
  if (action === "reconnect") reconnect();
  else if (action === "adopt") loadNewVersion();
  else commands?.reload();
}

const BANNER_ACTIONS = { reload: "重新讀取", adopt: "載入新版", reconnect: "重新連線並讀取" };

async function onChip(key) {
  if (key === "save") {
    if (currentSaveState.value === FAILED || currentSaveState.value === UNCERTAIN) {
      root.value?.querySelector("[data-banner-action]")?.focus();
    }
    return;
  }
  diagnosticsOpen.value = true;
  await nextTick();
  const group = { index: "external", partition: "partition" }[key];
  const target =
    (group && root.value?.querySelector(`[data-diagnostic-group='${group}']`)) ||
    root.value?.querySelector("[data-diagnostics-list]");
  target?.scrollIntoView?.({ block: "nearest" });
  root.value?.querySelector("[data-diagnostics-list]")?.focus();
}
</script>

<template>
  <div
    ref="root"
    class="editor"
    :class="{ 'editor--drawers': drawers }"
    :data-preview-state="workspace?.preview_state ?? 'loading'"
    :data-connection="connectionState"
    :data-layout="drawers ? 'drawers' : 'columns'"
  >
    <header class="editor__header" role="banner" tabindex="-1" data-region="header" aria-label="工作區">
      <span class="editor__seal" aria-hidden="true">✎</span>
      <h1 class="editor__title">地圖編纂</h1>
      <nav class="editor__tabs" aria-label="領域">
        <button
          v-for="item in DOMAINS"
          :key="item.key"
          type="button"
          class="editor__tab"
          :class="{ 'editor__tab--active': domain === item.key }"
          :aria-pressed="domain === item.key"
          :aria-keyshortcuts="item.chip"
          :data-domain-tab="item.key"
          @click="openDomain(item.key)"
        >
          {{ item.label }} <kbd class="editor__key">{{ item.chip }}</kbd>
        </button>
      </nav>
      <div class="editor__crumb" aria-label="目前位置">
        <button
          v-if="returnLabel"
          type="button"
          class="button editor__back"
          aria-keyshortcuts="Alt+ArrowLeft"
          data-return
          @click="goBack"
        >
          ← 返回 {{ returnLabel }}
        </button>
        <span class="editor__crumb-title" data-crumb>{{ title }}</span>
      </div>
      <div v-if="drawers" class="editor__drawer-toggles">
        <button ref="navToggle" type="button" class="button" :aria-expanded="drawer === 'nav'" data-drawer-toggle="nav" @click="openDrawer('nav')">
          導覽
        </button>
        <button
          ref="inspectorToggle"
          type="button"
          class="button"
          :aria-expanded="drawer === 'inspector'"
          data-drawer-toggle="inspector"
          @click="openDrawer('inspector')"
        >
          檢查器
        </button>
      </div>
      <ul class="editor__chips" aria-label="工作區狀態">
        <li v-for="chip in chips" :key="chip.key">
          <button
            type="button"
            class="chip"
            :class="`chip--${chip.tone}`"
            :data-chip="chip.key"
            :data-chip-state="chip.state"
            :aria-label="`${chip.name}：${chip.text}`"
            @click="onChip(chip.key)"
          >
            <span aria-hidden="true">{{ chip.glyph }}</span> {{ chip.text }}
          </button>
        </li>
      </ul>
    </header>

    <div class="editor__banner-slot" aria-live="polite">
      <section v-if="banner" class="banner" :class="`banner--${banner.tone}`" :data-banner="banner.key">
        <strong class="banner__title">{{ banner.title }}</strong>
        <span class="banner__text">{{ banner.text }}</span>
        <button
          v-if="banner.action"
          type="button"
          class="banner__action"
          :data-banner-action="banner.action"
          @click="onBannerAction(banner.action)"
        >
          {{ BANNER_ACTIONS[banner.action] }}
        </button>
      </section>
    </div>

    <nav
      class="editor__nav"
      :class="{ 'editor__drawer--open': drawer === 'nav' }"
      aria-label="世界導覽"
      tabindex="-1"
      data-region="nav"
      :role="drawers && drawer === 'nav' ? 'dialog' : null"
      :aria-modal="drawers && drawer === 'nav' ? 'true' : null"
    >
      <NavigationPanel
        :domain="domain"
        :tree="tree"
        :hidden="hiddenLayers"
        :objects="objects"
        :selection="selection"
        :query="query"
        :results="results"
        :map-options="domain === 'settlement' ? settlementOptions : interiorOptions"
        :current-map-id="currentMapId"
        @layer="toggleLayer"
        @tree="openTreeEntry"
        @choose="choose"
        @result="chooseResult"
        @query="query = $event"
        @map="(id) => { show(domain, id); selection = []; }"
      />
    </nav>

    <main class="editor__canvas" :aria-label="`地圖畫布：${title || '地圖'}。Tab 或方向鍵巡覽物件，Enter 選取並編輯。`" tabindex="-1" data-region="canvas">
      <MapCanvas
        v-if="scene"
        ref="canvasRef"
        :scene="scene"
        :selected="selection"
        :stale="canvasStale"
        :label="title"
        :movable="layoutMovable"
        :busy="persistence.inFlight > 0"
        :tools="tools"
        :tool="tool"
        :placing="placing"
        :pending="pendingPoints"
        :frame-label="frameLabel"
        @select="choose"
        @enter="onCanvasEnter"
        @move="onCanvasMove"
        @place="onPlace"
        @tool="tool = $event"
      />
      <div v-else-if="workspace && !world" class="no-preview" data-no-preview>
        <p class="no-preview__title">⦸ 無可用預覽</p>
        <p>工作區目前無法載入；請依下方診斷在外部修正檔案，修正後會自動載入。</p>
      </div>
      <div v-else-if="world" class="no-preview">
        <p>此領域沒有可顯示的地圖。</p>
      </div>
    </main>

    <aside
      class="editor__inspector"
      :class="{ 'editor__drawer--open': drawer === 'inspector' }"
      aria-label="檢查器"
      tabindex="-1"
      data-region="inspector"
      :role="drawers && drawer === 'inspector' ? 'dialog' : 'complementary'"
      :aria-modal="drawers && drawer === 'inspector' ? 'true' : null"
    >
      <InspectorPanel
        ref="inspectorRef"
        :record="record"
        :summary="summary"
        :relations="relations"
        :refusal="refusal"
        :removed="removedSelection"
        :copy-hint="copyHint"
        @follow="follow"
        @copy="copyContext"
        @delete="requestDelete"
      >
        <template #lead>
        <ContinentInspector
          v-if="showContinentInspector && !record"
          :key="`${formEpoch}:lead`"
          :world="world"
          :workspace="workspace"
          :selected="null"
          :creation="creation"
          :hint="toolHint"
          @send="send"
          @create="onCreate"
          @cancel="cancelTool"
          @select="(ref) => (selection = [ref])"
          @follow="follow"
          @drafts="leadDrafts = $event"
          @create-map="onCreateMap"
        />
        <SettlementInspector
          v-if="showSettlementInspector && !record"
          :key="`${formEpoch}:settlement-lead`"
          :world="world"
          :workspace="workspace"
          :settlement-id="currentMapId"
          :selection="selection"
          :creation="creation"
          :hint="toolHint"
          :submit="send"
          @create="onCreate"
          @cancel="cancelTool"
          @open="openCreation"
          @select="(ref) => (selection = [ref])"
          @follow="follow"
          @delete="requestDelete"
          @drafts="settlementLeadDrafts = $event"
        />
        </template>
        <template v-if="selectedRoom">
          <h3 class="section-label">版面位置</h3>
          <LayoutPositionFields
            :key="formEpoch"
            :room-ref="selected"
            :position="selectedRoom.position"
            @confirm="onFieldConfirm"
            @drafts="layoutDrafts = $event"
          />
          <p class="inspector__note">只寫入 {{ `content/map-editor-layouts/${selectedRoom.interiorId}.yaml` }}；不改變世界座標或距離。</p>
        </template>
        <ContinentInspector
          v-if="showContinentInspector && record"
          :key="`${formEpoch}:${selected ?? ''}`"
          :world="world"
          :workspace="workspace"
          :selected="selected"
          :creation="creation"
          :hint="toolHint"
          @send="send"
          @create="onCreate"
          @cancel="cancelTool"
          @select="(ref) => (selection = [ref])"
          @follow="follow"
          @drafts="continentDrafts = $event"
          @create-map="onCreateMap"
        />
        <SettlementInspector
          v-if="showSettlementInspector && record"
          :key="`${formEpoch}:${selected ?? ''}`"
          :world="world"
          :workspace="workspace"
          :settlement-id="currentMapId"
          :selection="selection"
          :creation="creation"
          :hint="toolHint"
          :submit="send"
          @create="onCreate"
          @cancel="cancelTool"
          @open="openCreation"
          @select="(ref) => (selection = [ref])"
          @follow="follow"
          @delete="requestDelete"
          @drafts="settlementDrafts = $event"
        />
      </InspectorPanel>
    </aside>

    <section class="editor__diagnostics" aria-label="診斷" tabindex="-1" data-region="diagnostics">
      <DiagnosticsStrip
        :groups="groups"
        :counts="counts"
        :open="Boolean(stripOpen)"
        :summary="stripSummary"
        :last-document="persistence.lastDocument"
        :notice="copyNotice"
        :hints="hints"
        @toggle="diagnosticsOpen = !stripOpen"
        @go="goDiagnostic"
      />
    </section>
  </div>
</template>
