// Cell geometry for provider cell layers (a wilderness grid of one cell per
// unit). Col/row are cell indices; a cell spans [n, n+1) in cell units and its
// representative centre is n + 0.5, the convention every marker uses.

import { FREEZE, requireFinite } from "./values.js";
import { project } from "./projection.js";

/** The frame pixel rectangle covered by one cell (col,row)-(col+1,row+1). */
export function cellRect(view, frame, col, row) {
  const sw = project(view, frame, { x: col, y: row });
  const ne = project(view, frame, { x: col + 1, y: row + 1 });
  return FREEZE({ left: sw.x, top: ne.y, right: ne.x, bottom: sw.y });
}

/** A cell's representative centre in cell units; markers use this convention. */
export function cellCentre(col, row) {
  return FREEZE({ x: requireFinite(col, "col") + 0.5, y: requireFinite(row, "row") + 0.5 });
}

/** The cell (col, row) a cell-unit position falls in. */
export function cellOf(position) {
  return { col: Math.floor(position.x), row: Math.floor(position.y) };
}
