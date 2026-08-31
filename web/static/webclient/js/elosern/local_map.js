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
 * Alongside the lattice, the model exports a radial (graph) placement
 * (`radial`) and the data-derived `layoutVariant` resolver
 * (`variantForLayer`, design D3): coordinate-bearing layers resolve to
 * `"lattice"`, everything else to `"graph"`. `edgeMarkersFor` computes the
 * lattice-only direction markers for remembered nodes strictly outside the
 * drawn extent, from RAW payload coordinates against an explicitly passed
 * surface geometry (design D3b).
 *
 * When the in-view span would exceed `MAX_LATTICE` columns or rows -- only
 * possible for a schema-valid but geometrically sparse payload -- the model
 * falls back to rank compression over the distinct sorted coordinate
 * values, which cannot exceed the payload's 64-node bound. Direction
 * markers deliberately never read those compressed ranks.
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


  // ---------------------------------------------------------------------------
  // Radial (graph) placement — design D1.
  //
  // Explicit geometry contract in unscaled units, taken from the renderer's
  // wave-1 footprints (design D1): a node occupies a marker box `x±9, y±9`
  // (half-extent 9 = r8 circle + stroke, shared with the diamond ladder) and
  // a label box 58x23 spanning y in [+3, +26] under the node origin. The
  // diagonal span of one node's worst footprint pair is sqrt(58^2 + 23^2)
  // = 62.4, so the contract declares ARC = 67 (ceil + 4) as the minimum
  // centre-to-centre distance between ANY two nodes. Ring-to-ring and
  // centre-to-ring clearance R0 = G = 72 (>= ARC + 5); the original r0 =
  // G = 44 was disproved by exhaustive footprint sweep BEFORE implementation
  // (two horizontally aligned footprints 44 apart share 14px of the 58-wide
  // label box) and the amendment is part of the contract. Node tests MUST
  // pin this recurrence; implementers MUST NOT substitute another heuristic.
  var RADIAL_GEOMETRY = {
    // Minimum centre-to-centre distance between any two node footprints.
    ARC: 67,
    // Centre-to-ring-1 clearance.
    R0: 72,
    // Ring-to-ring clearance.
    G: 72,
    // Deepest label-box offset under a node origin (baseline 26).
    LABEL_BOTTOM: 26,
    // Symmetric canvas padding beyond the deepest footprint.
    PAD: 24
  };

  function radialArcMin(m) {
    if (m <= 1) {
      return RADIAL_GEOMETRY.R0;
    }
    return RADIAL_GEOMETRY.ARC / (2 * Math.sin(Math.PI / m));
  }

  // Deterministic radial placement pass over the in-view nodes. BFS hop rings
  // from the current node over an UNDIRECTED adjacency built from every
  // committed edge whose endpoints are BOTH in view (traversable or not —
  // edges are topology, not passability; serialization direction must not
  // affect rings). In-view nodes unreachable by any edge join the outermost
  // ring in payload order. Ring member slots: uniform `k*360/m` for even m
  // (a member sits exactly on the upward axis), `(k+0.5)*360/m` for odd m
  // (the ring straddles the axis symmetrically). Returns
  // { nodes: [{id, ring, slot, angle, radius, x, y}], width, height }.
  function layoutRadial(inView, edges) {
    var nodes = Array.isArray(inView) ? inView : [];
    if (nodes.length === 0) {
      return { nodes: [], width: 0, height: 0 };
    }
    var byKey = {};
    nodes.forEach(function (node, i) {
      byKey[String(node.id)] = { node: node, index: i };
    });
    var adjacency = {};
    (Array.isArray(edges) ? edges : []).forEach(function (edge) {
      if (!edge) {
        return;
      }
      var s = byKey[String(edge.source)];
      var d = byKey[String(edge.destination)];
      if (!s || !d) {
        return; // remembered/out-of-payload endpoints create no rings
      }
      var sk = String(edge.source);
      var dk = String(edge.destination);
      (adjacency[sk] = adjacency[sk] || []).push(d);
      (adjacency[dk] = adjacency[dk] || []).push(s);
    });
    var current = null;
    for (var c = 0; c < nodes.length; c += 1) {
      if (nodes[c].visibility === "current") {
        current = byKey[String(nodes[c].id)];
        break;
      }
    }
    // BFS: ring membership + global first-discovery order.
    var ringOf = {};
    var discovered = [];
    if (current) {
      var ck = String(current.node.id);
      ringOf[ck] = 0;
      discovered.push(current);
      var queue = [current];
      while (queue.length > 0) {
        var head = queue.shift();
        var neighbours = adjacency[String(head.node.id)] || [];
        for (var n = 0; n < neighbours.length; n += 1) {
          var key = String(neighbours[n].node.id);
          if (ringOf[key] === undefined) {
            ringOf[key] = ringOf[String(head.node.id)] + 1;
            discovered.push(neighbours[n]);
            queue.push(neighbours[n]);
          }
        }
      }
    }
    // Unreachable in-view nodes join the outermost discovered ring
    // (ring 1 when nothing was discovered) in payload order.
    var maxRing = 0;
    Object.keys(ringOf).forEach(function (k) {
      if (ringOf[k] > maxRing) {
        maxRing = ringOf[k];
      }
    });
    var fallbackRing = Math.max(1, maxRing);
    var members = []; // { entry, ring, order }
    discovered.forEach(function (entry) {
      members.push({
        entry: entry,
        ring: ringOf[String(entry.node.id)],
        order: members.length
      });
    });
    nodes.forEach(function (node, i) {
      var key = String(node.id);
      if (ringOf[key] === undefined) {
        members.push({ entry: byKey[key], ring: fallbackRing, order: 1000000 + i });
      }
    });
    // Ring radii per the D1 recurrence.
    var counts = {};
    members.forEach(function (m) {
      counts[m.ring] = (counts[m.ring] || 0) + 1;
    });
    var outermost = 0;
    members.forEach(function (m) {
      if (m.ring > outermost) {
        outermost = m.ring;
      }
    });
    var radius = [];
    for (var r = 1; r <= outermost; r += 1) {
      var m = counts[r] || 0;
      var arcMin = radialArcMin(m);
      radius[r] = r === 1
        ? Math.max(RADIAL_GEOMETRY.R0, arcMin)
        : Math.max(radius[r - 1] + RADIAL_GEOMETRY.G, arcMin);
    }
    // Centre-only / edgeless payloads: current alone at the centre of a
    // fixed positive padded square.
    var maxRadius = outermost > 0 ? radius[outermost] : 0;
    var side = 2 * (maxRadius + RADIAL_GEOMETRY.LABEL_BOTTOM + RADIAL_GEOMETRY.PAD);
    var centre = side / 2;
    var slotIndex = {};
    var placed = [];
    members
      .slice()
      .sort(function (a, b) {
        if (a.ring !== b.ring) {
          return a.ring - b.ring;
        }
        return a.order - b.order;
      })
      .forEach(function (member) {
        var ring = member.ring;
        var entry = member.entry;
        var out = {
          id: entry.node.id,
          ring: ring,
          slot: 0,
          angle: 0,
          radius: 0,
          x: centre,
          y: centre
        };
        if (ring > 0) {
          var m = counts[ring];
          var slot = slotIndex[ring] || 0;
          slotIndex[ring] = slot + 1;
          var angleDeg = (slot + (m % 2 === 1 ? 0.5 : 0)) * (360 / m);
          var angleRad = (angleDeg * Math.PI) / 180;
          out.slot = slot;
          out.angle = angleDeg;
          out.radius = radius[ring];
          out.x = centre + radius[ring] * Math.sin(angleRad);
          out.y = centre - radius[ring] * Math.cos(angleRad);
        }
        placed.push(out);
      });
    return { nodes: placed, width: side, height: side };
  }

  // Data-derived layout resolution — design D3. The coordinate-bearing layer
  // set is a closed contract mirrored across layers: `grid`/`wilderness`
  // correspond one-to-one to the presenter's canonical map-ID prefixes
  // (`grid:` from xyzgrid, `wild:` from the wilderness contrib) and to the
  // `_grid_layer`/`_wilderness_layer` presenter branches that are the only
  // producers of real coordinates. A future layer with validated coordinates
  // MUST amend presenter + payload schema + spec together; the client
  // resolver never guesses from payload shape.
  function variantForLayer(layer) {
    return layer === "grid" || layer === "wilderness" ? "lattice" : "graph";
  }

  // ---------------------------------------------------------------------------
  // Edge direction markers — design D3b.
  //
  // The bearing is computed from RAW payload coordinates, never from the
  // lattice's compressed col/row ranks: rank compression preserves order,
  // not ratios, and (100,1) must not render as 45 degrees. +y = north;
  // bearing theta = ((atan2(dx, dy) deg mod 360) + 360) mod 360, octant
  // k = floor(theta/45 + 0.5) mod 8 over the half-open sector
  // [k*45 - 22.5, k*45 + 22.5), so boundary vectors are deterministic.
  // Octants clockwise from north: 0 N, 1 NE, 2 E, 3 SE, 4 S, 5 SW, 6 W, 7 NW.
  function remoteDirection(current, remote) {
    var dx = remote.x - current.x;
    var dy = remote.y - current.y;
    var theta = ((Math.atan2(dx, dy) * 180) / Math.PI % 360 + 360) % 360;
    return { dx: dx, dy: dy, octant: Math.floor(theta / 45 + 0.5) % 8, theta: theta };
  }

  // Edge markers for the remembered nodes STRICTLY outside the in-view
  // coordinate bounding box, against an EXPLICIT surface geometry:
  // { canvasWidth, canvasHeight, current: {x, y}, markerHalf, nameWidth,
  // nameHeight } in the units the renderer actually draws. The model NEVER
  // assumes a surface's pitch or scale — each surface passes its own numbers.
  //
  // Packing policy (closed form, design D3b). The memory diamond is a rect
  // drawn with rotate(45), so its reach along the axes — and its L1 radius —
  // is REACH = sqrt(2) * markerHalf, not the markerHalf itself; two diamonds
  // are disjoint once their centre-to-centre L1 distance exceeds 2 * REACH.
  // With NAME_PAD = max(nameWidth, nameHeight) for surfaces that render
  // visible marker names (0 otherwise):
  //   gutter   >= 2 * REACH + 1 + NAME_PAD        (every diamond, with its
  //               outward name box, sits wholly inside the gutter band, its
  //               canvas-side tip >= 1 unit outside the canvas rect — node
  //               markers, labels and axes all live inside that rect)
  //   outset   = REACH + NAME_PAD                  (centre inset from the
  //               outer rect, so the outward name box stays in the band)
  //   inset    = max(19, outset + REACH + 1)       (two markers on adjacent
  //               edges nearest a corner are L1 >= 2 * (inset - outset) >=
  //               2 * REACH + 1 apart, hence disjoint)
  //   slotMin  = max(2 * REACH + 1, nameWidth + 2) (along-edge spacing)
  //   need     = ceil((n * slotMin + 2 * inset - edgeLength) / 2) per edge
  // The payload's 64-node bound caps every count, so the gutter is a closed
  // number — no marker is ever dropped, overlapped, or placed inside the
  // canvas at any legal input.
  var MARKER_INSET_FLOOR = 19;
  function edgeMarkersFor(inView, remembered, geometry) {
    var view = Array.isArray(inView) ? inView : [];
    var remember = Array.isArray(remembered) ? remembered : [];
    var empty = { markers: [], gutter: 0, width: 0, height: 0 };
    if (!geometry || view.length === 0 || remember.length === 0) {
      return Object.assign({}, empty, {
        width: geometry ? geometry.canvasWidth : 0,
        height: geometry ? geometry.canvasHeight : 0
      });
    }
    var canvasWidth = geometry.canvasWidth;
    var canvasHeight = geometry.canvasHeight;
    var origin = geometry.current;
    if (!(canvasWidth > 0) || !(canvasHeight > 0) || !origin
        || typeof origin.x !== "number" || typeof origin.y !== "number") {
      return Object.assign({}, empty, { width: canvasWidth, height: canvasHeight });
    }
    var markerHalf = typeof geometry.markerHalf === "number" && geometry.markerHalf > 0
      ? geometry.markerHalf : 9;
    var nameWidth = typeof geometry.nameWidth === "number" && geometry.nameWidth > 0
      ? geometry.nameWidth : 0;
    var nameHeight = typeof geometry.nameHeight === "number" && geometry.nameHeight > 0
      ? geometry.nameHeight : 0;
    // Rotated-diamond reach along the axes (see D3b): the 45-degree rotated
    // marker is an L1 ball of this radius, not one of markerHalf.
    var reach = Math.SQRT2 * markerHalf;
    // Outward name boxes carry a 2-unit margin, like the along-edge slots.
    var namePad = (nameWidth > 0 || nameHeight > 0)
      ? Math.max(nameWidth, nameHeight) + 2 : 0;
    // Along-edge spacing: horizontal edges stack name boxes side by side
    // (width-driven); vertical edges stack them end to end (height-driven).
    var slotMinH = Math.max(2 * reach + 1, nameWidth + 2);
    var slotMinV = 2 * reach + 1 + nameHeight;
    if (slotMinV < slotMinH && nameHeight === 0) {
      slotMinV = slotMinH;
    }
    var outset = reach + namePad;
    var inset = Math.max(MARKER_INSET_FLOOR, outset + reach + 1);
    var gutterMin = 2 * reach + 1 + namePad;
    // Eligibility: raw coordinates strictly outside the in-view bounding
    // box. A zero-delta remote (coincident with current) and any extent-
    // interior remembered node never mark — the list entry stays canonical.
    var minX = Infinity;
    var maxX = -Infinity;
    var minY = Infinity;
    var maxY = -Infinity;
    view.forEach(function (node) {
      if (typeof node.x !== "number" || typeof node.y !== "number") {
        return;
      }
      if (node.x < minX) minX = node.x;
      if (node.x > maxX) maxX = node.x;
      if (node.y < minY) minY = node.y;
      if (node.y > maxY) maxY = node.y;
    });
    if (!isFinite(minX)) {
      // Coordinate-free payload: a direction claim would fabricate a place.
      return Object.assign({}, empty, { width: canvasWidth, height: canvasHeight });
    }
    var rawCurrent = null;
    view.forEach(function (node) {
      if (node.visibility === "current" && rawCurrent === null
          && typeof node.x === "number" && typeof node.y === "number") {
        rawCurrent = { x: node.x, y: node.y };
      }
    });
    if (rawCurrent === null) {
      // No coordinate-bearing current node: a ray has no origin, so no
      // direction claim is made.
      return Object.assign({}, empty, { width: canvasWidth, height: canvasHeight });
    }
    var candidates = [];
    remember.forEach(function (node, i) {
      if (typeof node.x !== "number" || typeof node.y !== "number") {
        return;
      }
      if (node.x === rawCurrent.x && node.y === rawCurrent.y) {
        return; // zero-delta: coincident, not a direction
      }
      if (node.x < minX || node.x > maxX || node.y < minY || node.y > maxY) {
        candidates.push({ node: node, index: i, dir: remoteDirection(rawCurrent, node) });
      }
    });
    if (candidates.length === 0) {
      return Object.assign({}, empty, { width: canvasWidth, height: canvasHeight });
    }
    // Ray/canvas-rect crossing: the marker's edge is where the true bearing
    // leaves the canvas. Canvas coordinates take +y downward (screen), so
    // the screen vector is (dx, -dy).
    var edges = {
      top: { length: canvasWidth, count: 0 },
      bottom: { length: canvasWidth, count: 0 },
      left: { length: canvasHeight, count: 0 },
      right: { length: canvasHeight, count: 0 }
    };
    candidates.forEach(function (candidate) {
      var sx = candidate.dir.dx;
      var sy = -candidate.dir.dy;
      var current = geometry.current;
      var tX = sx > 0 ? (canvasWidth - current.x) / sx : sx < 0 ? (0 - current.x) / sx : Infinity;
      var tY = sy > 0 ? (canvasHeight - current.y) / sy : sy < 0 ? (0 - current.y) / sy : Infinity;
      // Exact-corner ties resolve horizontally (deterministic).
      candidate.side = tX <= tY ? (sx > 0 ? "right" : "left") : (sy > 0 ? "bottom" : "top");
      if (sx === 0 && sy === 0) {
        candidate.side = "top"; // unreachable: zero-delta is never eligible
      }
      edges[candidate.side].count += 1;
    });
    var gutter = gutterMin;
    Object.keys(edges).forEach(function (side) {
      var edge = edges[side];
      if (edge.count === 0) {
        return;
      }
      var edgeSlotMin = side === "top" || side === "bottom" ? slotMinH : slotMinV;
      var need = Math.ceil((edge.count * edgeSlotMin + 2 * inset - edge.length) / 2);
      if (need > gutter) {
        gutter = need;
      }
    });
    var outerWidth = canvasWidth + 2 * gutter;
    var outerHeight = canvasHeight + 2 * gutter;
    // Slot centres: uniform along the usable length, inset from the outer
    // rect corners, ordered by bearing then payload index. The usable length
    // is max(physical span, n * the edge slot minimum): when the gutter was
    // grown for this edge both formulas agree exactly on n * slotMin;
    // otherwise uniform centres still sit no closer than half a slot to a
    // corner.
    var bySide = {};
    candidates.forEach(function (candidate) {
      (bySide[candidate.side] = bySide[candidate.side] || []).push(candidate);
    });
    var markers = [];
    Object.keys(bySide).forEach(function (side) {
      var group = bySide[side];
      group.sort(function (a, b) {
        return a.dir.theta - b.dir.theta || a.index - b.index;
      });
      var horizontal = side === "top" || side === "bottom";
      var usable = Math.max(
        (horizontal ? outerWidth : outerHeight) - 2 * inset,
        group.length * (horizontal ? slotMinH : slotMinV)
      );
      group.forEach(function (candidate, slot) {
        var centre = inset + ((slot + 0.5) * usable) / group.length;
        var marker = {
          id: candidate.node.id,
          name: candidate.node.label,
          landmark: !!candidate.node.landmark,
          dx: candidate.dir.dx,
          dy: candidate.dir.dy,
          octant: candidate.dir.octant,
          side: side,
          x: 0,
          y: 0
        };
        if (side === "top") {
          marker.x = centre;
          marker.y = outset;
        } else if (side === "bottom") {
          marker.x = centre;
          marker.y = outerHeight - outset;
        } else if (side === "left") {
          marker.x = outset;
          marker.y = centre;
        } else {
          marker.x = outerWidth - outset;
          marker.y = centre;
        }
        markers.push(marker);
      });
    });
    return { markers: markers, gutter: gutter, width: outerWidth, height: outerHeight };
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
      // Additive wave-2 fields (designs D1/D3): the resolved layout variant
      // and the radial placement. The store spreads the reducer output, so
      // both flow to the surfaces without any store change.
      layoutVariant: variantForLayer(panel && panel.layer || null),
      radial: layoutRadial(inView, edges),
    };
    model.focusTargets = focusTargets(model);
    return model;
  }

  // The echo label for one traversal (complete-ui-command-echo D3): the label
  // of the UNIQUE traversable edge from `fromNode` to `toNode` — the committed
  // edge model carries no exit_ref and the schema does not forbid parallel
  // edges, so an ambiguous match must never pick one arbitrarily — falling
  // back to the destination node's label. Neither available → null (the echo
  // stays silent; nothing is invented).
  function exitLabelFor(model, fromNode, toNode) {
    if (!model || fromNode === null || fromNode === undefined || toNode === null || toNode === undefined) {
      return null;
    }
    var matches = [];
    (model.edges || []).forEach(function (edge) {
      if (
        edge &&
        edge.traversable &&
        String(edge.source) === String(fromNode) &&
        String(edge.destination) === String(toNode) &&
        edge.label
      ) {
        matches.push(edge.label);
      }
    });
    if (matches.length === 1) {
      return matches[0];
    }
    var nodes = [].concat(model.nodes || [], model.remembered || []);
    for (var i = 0; i < nodes.length; i += 1) {
      if (nodes[i] && String(nodes[i].id) === String(toNode)) {
        return nodes[i].label || null;
      }
    }
    return null;
  }

  return {
    MAX_LATTICE: MAX_LATTICE,
    MAX_FOCUS_TARGETS: MAX_FOCUS_TARGETS,
    MAX_NODES: MAX_NODES,
    STATE_INDICATORS: Object.assign({}, STATE_INDICATORS),
    reducePanel: reducePanel,
    focusTargets: focusTargets,
    layoutNodes: layoutNodes,
    exitLabelFor: exitLabelFor,
    layoutRadial: layoutRadial,
    RADIAL_GEOMETRY: Object.assign({}, RADIAL_GEOMETRY),
    variantForLayer: variantForLayer,
    remoteDirection: remoteDirection,
    edgeMarkersFor: edgeMarkersFor,
  };
});
