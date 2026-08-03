/*
 * Elosern DOM-independent local-map render model.
 *
 * Reduces a validated `local_map` panel into the logical minimap model
 * consumed by the GoldenLayout component: nodes with visibility states
 * distinguishable by shape/border/label in addition to color, edges, legend
 * text, and focus targets for remembered remote nodes (name/landmark, no
 * travel action). Unknown nodes never appear because the server already
 * validated the panel; this module only adds a small bounded layout pass.
 *
 * No `document` or `window` access at load time; Node tests exercise the
 * model directly. All server strings are passed through unchanged as display
 * text; the model never parses narrative.
 */
(function (root, factory) {
  "use strict";
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.Elosern = root.Elosern || {};
    root.Elosern.LocalMap = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // Renderer-local geometry caps (must stay within the panel's -1024..1024).
  var MAX_LAYOUT_X = 64;
  var MAX_LAYOUT_Y = 32;
  var MAX_FOCUS_TARGETS = 16;

  // Visibility -> non-color visual indicators.
  var STATE_INDICATORS = {
    current: { shape: "circle", border: "double", labelPrefix: "◆ " },
    visible_unvisited: { shape: "square", border: "thin", labelPrefix: "◇ " },
    visible_visited: { shape: "square", border: "medium", labelPrefix: "□ " },
    remembered: { shape: "diamond", border: "dashed", labelPrefix: "◆ " },
  };

  function clampCoord(value, minimum, maximum) {
    var n = Number(value);
    if (!isFinite(n)) {
      n = 0;
    }
    return Math.max(minimum, Math.min(maximum, Math.round(n)));
  }

  function nodeModel(node) {
    var indicator = STATE_INDICATORS[node.visibility] || STATE_INDICATORS.remembered;
    return {
      id: node.id,
      label: node.label,
      x: clampCoord(node.x, -MAX_LAYOUT_X, MAX_LAYOUT_X),
      y: clampCoord(node.y, -MAX_LAYOUT_Y, MAX_LAYOUT_Y),
      visibility: node.visibility,
      current: !!node.current,
      anchor: !!node.anchor,
      landmark: !!node.landmark,
      shape: indicator.shape,
      border: indicator.border,
      labelPrefix: indicator.labelPrefix,
      action: node.action === null || node.action === undefined ? null : {
        kind: node.action.kind,
        exit_ref: node.action.exit_ref,
        destination: node.action.destination,
      },
    };
  }

  function edgeModel(edge) {
    return {
      source: edge.source,
      destination: edge.destination,
      label: edge.label,
      known: !!edge.known,
      traversable: !!edge.traversable,
    };
  }

  function focusTargets(model) {
    var targets = [];
    model.nodes.forEach(function (node) {
      if (node.visibility !== "remembered") {
        return;
      }
      if (targets.length >= MAX_FOCUS_TARGETS) {
        return;
      }
      targets.push({
        nodeId: node.id,
        label: node.label,
        landmark: node.landmark,
        // Remembered remote nodes carry no travel action by construction.
        hasTravelAction: node.action !== null,
      });
    });
    return targets;
  }

  // Deterministic bounded layout pass: normalize the renderer-local node
  // positions into a finite pane while preserving relative order by (y, x).
  function normalizeLayout(nodes) {
    var minX = Infinity;
    var maxX = -Infinity;
    var minY = Infinity;
    var maxY = -Infinity;
    nodes.forEach(function (node) {
      if (node.x < minX) {
        minX = node.x;
      }
      if (node.x > maxX) {
        maxX = node.x;
      }
      if (node.y < minY) {
        minY = node.y;
      }
      if (node.y > maxY) {
        maxY = node.y;
      }
    });
    if (!isFinite(minX) || !isFinite(minY)) {
      return nodes;
    }
    var spanX = Math.max(1, maxX - minX);
    var spanY = Math.max(1, maxY - minY);
    return nodes.map(function (node) {
      return Object.assign({}, node, {
        x: Math.round(((node.x - minX) / spanX) * (MAX_LAYOUT_X * 2) - MAX_LAYOUT_X),
        y: Math.round(((node.y - minY) / spanY) * (MAX_LAYOUT_Y * 2) - MAX_LAYOUT_Y),
      });
    });
  }

  function reducePanel(panel) {
    var nodes = (panel && panel.nodes || []).map(nodeModel);
    nodes = normalizeLayout(nodes);
    var edges = (panel && panel.edges || []).map(edgeModel);
    var legend = (panel && panel.legend || []).slice();
    var model = {
      layer: panel && panel.layer || null,
      currentNode: panel && panel.current_node || null,
      title: panel && panel.title || "",
      nodes: nodes,
      edges: edges,
      legend: legend,
      focusTargets: [],
    };
    model.focusTargets = focusTargets(model);
    return model;
  }

  return {
    MAX_LAYOUT_X: MAX_LAYOUT_X,
    MAX_LAYOUT_Y: MAX_LAYOUT_Y,
    MAX_FOCUS_TARGETS: MAX_FOCUS_TARGETS,
    STATE_INDICATORS: Object.assign({}, STATE_INDICATORS),
    reducePanel: reducePanel,
    focusTargets: focusTargets,
  };
});
