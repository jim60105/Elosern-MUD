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
 * Layout is a bounded integer lattice computed over the current field of
 * view only: `current`, `visible_unvisited`, and `visible_visited` nodes
 * occupy `col = x - minX`, `row = y - minY` cells, and the model exports
 * the lattice's column and row counts. `remembered` remote nodes are kept
 * out of the coordinate canvas entirely (their payload coordinates describe
 * places outside the current view and must not distort the local spacing);
 * they surface as a bounded, order-preserved list.
 *
 * When the in-view span would exceed `MAX_LATTICE` columns or rows -- only
 * possible for a schema-valid but geometrically sparse payload -- the model
 * falls back to rank compression over the distinct sorted coordinate
 * values, which cannot exceed the payload's 64-node bound.
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

  var MAX_LATTICE = 64;
  var MAX_FOCUS_TARGETS = 16;
  var MAX_NODES = 64;

  // Visibility -> non-color visual indicators.
  var STATE_INDICATORS = {
    current: { shape: "circle", border: "double", labelPrefix: "◆ " },
    visible_unvisited: { shape: "square", border: "thin", labelPrefix: "◇ " },
    visible_visited: { shape: "square", border: "medium", labelPrefix: "□ " },
    remembered: { shape: "diamond", border: "dashed", labelPrefix: "◆ " },
  };

  function nodeModel(node) {
    var indicator = STATE_INDICATORS[node.visibility] || STATE_INDICATORS.remembered;
    return {
      id: node.id,
      label: node.label,
      x: node.x,
      y: node.y,
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
    model.remembered.forEach(function (node) {
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

  // Rank compression: distinct sorted coordinate values become consecutive
  // indices. Deterministic and bounded by the number of distinct values.
  function compressAxis(values) {
    var sorted = values.slice().sort(function (a, b) {
      return a - b;
    });
    var rank = {};
    var index = 0;
    for (var i = 0; i < sorted.length; i += 1) {
      if (rank[sorted[i]] === undefined) {
        rank[sorted[i]] = index;
        index += 1;
      }
    }
    return rank;
  }

  // Deterministic bounded layout pass: place only in-view nodes on the
  // lattice. Returns { nodes, cols, rows }.
  function layoutNodes(nodes) {
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
    if (nodes.length === 0) {
      return { nodes: [], cols: 0, rows: 0 };
    }
    var cols = maxX - minX + 1;
    var rows = maxY - minY + 1;
    if (cols <= MAX_LATTICE && rows <= MAX_LATTICE) {
      return {
        nodes: nodes.map(function (node) {
          return Object.assign({}, node, {
            col: node.x - minX,
            row: node.y - minY,
          });
        }),
        cols: cols,
        rows: rows,
      };
    }
    // Sparse fallback: rank-compress both axes; cannot exceed the payload's
    // node bound (at most 64 distinct values each).
    var colRank = compressAxis(nodes.map(function (node) {
      return node.x;
    }));
    var rowRank = compressAxis(nodes.map(function (node) {
      return node.y;
    }));
    return {
      nodes: nodes.map(function (node) {
        return Object.assign({}, node, {
          col: colRank[node.x],
          row: rowRank[node.y],
        });
      }),
      cols: Math.max(1, Object.keys(colRank).length),
      rows: Math.max(1, Object.keys(rowRank).length),
    };
  }

  function reducePanel(panel) {
    var all = (panel && panel.nodes || []).map(nodeModel);
    var inView = [];
    var remembered = [];
    for (var i = 0; i < all.length && inView.length + remembered.length < MAX_NODES; i += 1) {
      var node = all[i];
      if (node.visibility === "remembered") {
        remembered.push(node);
      } else {
        inView.push(node);
      }
    }
    var layout = layoutNodes(inView);
    var edges = (panel && panel.edges || []).map(edgeModel);
    var legend = (panel && panel.legend || []).slice();
    var model = {
      layer: panel && panel.layer || null,
      currentNode: panel && panel.current_node || null,
      title: panel && panel.title || "",
      nodes: layout.nodes,
      cols: layout.cols,
      rows: layout.rows,
      edges: edges,
      legend: legend,
      remembered: remembered,
      focusTargets: [],
    };
    model.focusTargets = focusTargets(model);
    return model;
  }

  return {
    MAX_LATTICE: MAX_LATTICE,
    MAX_FOCUS_TARGETS: MAX_FOCUS_TARGETS,
    MAX_NODES: MAX_NODES,
    STATE_INDICATORS: Object.assign({}, STATE_INDICATORS),
    reducePanel: reducePanel,
    focusTargets: focusTargets,
    layoutNodes: layoutNodes,
  };
});
