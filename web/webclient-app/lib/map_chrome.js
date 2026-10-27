// The map drawer's own chrome policy: how wide the detail panel is and what
// rectangle the floating chrome and off-screen pointers may use. The shared
// primitives only subtract an already-decided reservation; the width and the
// "reserve it while open" rule are this game's.

import { DEFAULT_MARGIN_PX, insetRect } from "@elosern/map-view";

/** Detail drawer width the edge pointers avoid when something is selected. */
export const DETAIL_DRAWER_WIDTH = 360;

/**
 * The rectangle edge pointers and the pill may use: the frame minus a margin,
 * the host-measured floating-control insets, and the open detail drawer on the
 * right. A rectangle squeezed below zero collapses to its midpoint.
 */
export function usableRect(frame, {
  drawerOpen = false,
  drawerWidth = DETAIL_DRAWER_WIDTH,
  marginPx = DEFAULT_MARGIN_PX,
  insets = null,
} = {}) {
  return insetRect(frame, { marginPx, insets, reservedRight: drawerOpen ? drawerWidth : 0 });
}
