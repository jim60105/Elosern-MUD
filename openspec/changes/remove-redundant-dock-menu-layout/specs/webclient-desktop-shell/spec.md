# webclient-desktop-shell — delta

## ADDED Requirements

### Requirement: The dock's row region and detail panes are direct children of their host
The action dock's pane host and the drawer body that hosts a dock frame SHALL
lay out the active frame's focusable row region and any displayed detail pane
as direct children of that host, side by side when a detail pane is displayed.
The dock menu component SHALL NOT contribute any anonymous layout container
between the host and either child: its rendered roots are the row region and,
when shown, the detail pane itself. A frame that displays no detail pane SHALL
have the row region as the host's only dock-menu child, filling the host's
full width. When the combat skill detail pane replaces the generic detail, it
SHALL be a sibling of the row region under the same host, and the row region
SHALL NOT gain a wrapper for either case.

#### Scenario: A frame with a detail pane pairs direct children under the host
- **WHEN** the active dock frame shows a detail pane beside the rows (a generic
  detail frame or the combat skill frame with its dedicated detail)
- **THEN** the focusable row region and the visible detail pane are siblings
  whose parent is the pane host, no intermediate layout element wraps either
  of them, and the pair renders side by side

#### Scenario: A frame without a detail pane renders the row region directly
- **WHEN** the active dock frame renders without a detail pane (an exit-outlet
  frame or any full-width frame)
- **THEN** the focusable row region is the pane host's only dock-menu child and
  fills the host's full width, with no wrapper element rendered

#### Scenario: The drawer-hosted frame keeps the same direct-child rule
- **WHEN** a service submenu frame is hosted in a drawer body instead of the
  action dock
- **THEN** the row region and any displayed detail pane are direct children of
  the drawer body and render side by side, with no component-level layout
  wrapper between them
