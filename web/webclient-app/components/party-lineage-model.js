// party-lineage-model (webclient-party-lineage-tab, design §6.5): the pure
// projections the party window's 系譜 tab reads from the committed `lineage`
// v2 panel. Nothing here evaluates a growth rule: node states, levels, XP
// bands, readiness, prerequisite text and every count are the server's
// derived view, only grouped, named and placed for display.

const isAvailable = (panel) => !!panel && panel.available === true;

// The committed graphs, or none while the panel is unavailable or absent.
export function lineageGraphs(lineage) {
  return isAvailable(lineage) && Array.isArray(lineage.graphs) ? lineage.graphs : [];
}

const nodesOf = (graph) => (Array.isArray(graph?.nodes) ? graph.nodes : []);
const edgesOf = (graph) => (Array.isArray(graph?.edges) ? graph.edges : []);

// The list column's sections: graphs grouped by their element/style label in
// the payload's own order of first appearance.
export function groupGraphs(lineage) {
  const groups = [];
  for (const graph of lineageGraphs(lineage)) {
    const label = graph.group_label_zh;
    let group = groups.find((entry) => entry.label === label);
    if (!group) {
      group = { label, graphs: [] };
      groups.push(group);
    }
    group.graphs.push(graph);
  }
  return groups;
}

// The graph's name: its supplied root nodes' display names joined with ‧.
// A root the payload does not carry as a node is skipped; no name is ever
// derived from a skill key.
export function rootName(graph) {
  const byKey = new Map(nodesOf(graph).map((node) => [node.skill_key, node.display_name_zh]));
  return (Array.isArray(graph?.root_keys) ? graph.root_keys : [])
    .map((key) => byKey.get(key))
    .filter((name) => typeof name === "string" && name !== "")
    .join(" ‧ ");
}

// The node's display state from its committed flags: capped (filled
// diamond, solid border, 見頂), owned (half-filled, solid border) or locked
// (dashed). Ownership decides, so the diamonds always agree with the
// graph's committed owned_count.
export function nodeState(node) {
  if (node?.owned === true) return node.capped === true ? "capped" : "owned";
  return "locked";
}

export const NODE_STATE_LABEL = Object.freeze({ capped: "見頂", owned: "已習得", locked: "未習得" });

// The diamond row's accessible summary: how many nodes are in each state.
export function stateSummary(graph) {
  const counts = { capped: 0, owned: 0, locked: 0 };
  for (const node of nodesOf(graph)) counts[nodeState(node)] += 1;
  return ["capped", "owned", "locked"]
    .filter((state) => counts[state] > 0)
    .map((state) => `${NODE_STATE_LABEL[state]} ${counts[state]}`)
    .join("、");
}

// 可解鎖: the server marked at least one node of the graph ready.
export function graphReady(graph) {
  return nodesOf(graph).some((node) => node.ready === true);
}

// Display-only formatting: practice XP is a float; the stored pair
// xp_into_level / xp_to_next_level is the node's own level band.
export function formatXp(value) {
  return Number.isInteger(value) ? String(value) : String(Math.round(value * 10) / 10);
}

// An owned node's growth line: level, meter fill and 「23/50 → 下一階」, or
// 見頂 with a full meter when capped. Null for a node that is not owned.
export function nodeGrowth(node) {
  if (!node || node.owned !== true) return null;
  const level = Number.isInteger(node.level) ? node.level : 0;
  if (node.capped === true) return { capped: true, levelText: `Lv ${level}`, percent: 100, xpText: "見頂" };
  const into = Number.isFinite(node.xp_into_level) ? Math.max(0, node.xp_into_level) : 0;
  const toNext = Number.isFinite(node.xp_to_next_level) ? Math.max(0, node.xp_to_next_level) : 0;
  const band = into + toNext;
  const percent = band > 0 ? Math.min(100, Math.round((into / band) * 100)) : 0;
  return { capped: false, levelText: `Lv ${level}`, percent, xpText: `${formatXp(into)}/${formatXp(band)} → 下一階` };
}

// The prerequisite line split between its 「…」 clauses (display only: the
// parts join back to the committed text), so a line wraps between two
// prerequisites rather than inside a skill name.
export function prereqParts(text) {
  return typeof text === "string" && text !== "" ? text.split(/(?<=」)(?=「)/) : [];
}

// The graph containing a skill, or null.
export function graphOfSkill(lineage, skillKey) {
  if (!skillKey) return null;
  return lineageGraphs(lineage).find((graph) => nodesOf(graph).some((node) => node.skill_key === skillKey)) ?? null;
}

// The detail drawing: one row per committed `depth`, the row's nodes spread
// evenly across the width in payload order (a lone node, such as a merge,
// centres itself), and one curve per committed edge from parent to child
// with its minimum level labelled at the curve's midpoint. Coordinates are
// percentages of the canvas; an edge naming a node the payload does not
// carry is not drawn.
export function graphLayout(graph) {
  const nodes = nodesOf(graph);
  if (nodes.length === 0) return null;
  const depthOf = (node) => (Number.isInteger(node.depth) && node.depth >= 0 ? node.depth : 0);
  const rows = Math.max(...nodes.map(depthOf)) + 1;
  const perRow = new Map();
  for (const node of nodes) {
    const depth = depthOf(node);
    if (!perRow.has(depth)) perRow.set(depth, []);
    perRow.get(depth).push(node);
  }
  const positions = {};
  let widest = 1;
  for (const [depth, members] of perRow) {
    widest = Math.max(widest, members.length);
    members.forEach((node, index) => {
      positions[node.skill_key] = {
        x: ((index + 0.5) / members.length) * 100,
        y: ((depth + 0.5) / rows) * 100,
        depth,
        column: index,
        span: members.length,
      };
    });
  }
  const byKey = new Map(nodes.map((node) => [node.skill_key, node]));
  const edges = [];
  for (const edge of edgesOf(graph)) {
    const from = positions[edge.from_key];
    const to = positions[edge.to_key];
    if (!from || !to) continue;
    const mid = (from.y + to.y) / 2;
    edges.push({
      key: `${edge.from_key}>${edge.to_key}`,
      from: edge.from_key,
      to: edge.to_key,
      level: edge.min_level,
      d: `M${from.x} ${from.y} C${from.x} ${mid} ${to.x} ${mid} ${to.x} ${to.y}`,
      lx: (from.x + to.x) / 2,
      ly: mid,
      locked: nodeState(byKey.get(edge.to_key)) === "locked",
    });
  }
  return { rows, widest, positions, edges };
}
