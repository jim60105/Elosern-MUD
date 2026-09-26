## MODIFIED Requirements

### Requirement: The action dock's row region and detail panes are direct children of its pane host
The action dock's pane host SHALL
lay out the active frame's focusable row region and any displayed detail pane
as direct children of that host, side by side when a detail pane is displayed.
The dock menu component SHALL NOT contribute any anonymous layout container
between the host and either child: its rendered roots are the row region and,
when shown, the detail pane itself. A frame that displays no detail pane SHALL
have the row region as the host's only dock-menu child, filling the host's
full width. When the combat skill detail pane replaces the generic detail, it
SHALL be a sibling of the row region under the same host, and the row region
SHALL NOT gain a wrapper for either case. The scene overview is the one exception to the
direct-child rule for row regions: it SHALL render as a single component that is a direct child of the
pane host and that holds its labelled chip rows and its reason strip, it SHALL display no detail
pane, and it SHALL fill the host's full width. A target's verb popover SHALL render in the dock's
overlay layer over the pane region, not inside the pane host, so the pane host's children are the
same while it is open. The action dock's pane host SHALL be
the only host of the dock's row region: no reference drawer body renders it.

#### Scenario: A frame with a detail pane pairs direct children under the host
- **WHEN** the active dock frame shows a detail pane beside the rows (a generic
  detail frame or the combat skill frame with its dedicated detail)
- **THEN** the focusable row region and the visible detail pane are siblings
  whose parent is the pane host, no intermediate layout element wraps either
  of them, and the pair renders side by side

#### Scenario: A frame without a detail pane renders the row region directly
- **WHEN** the active dock frame renders without a detail pane (any full-width
  frame)
- **THEN** the focusable row region is the pane host's only dock-menu child and
  fills the host's full width, with no wrapper element rendered

#### Scenario: A reference drawer body never hosts the row region
- **WHEN** any reference drawer is open in exploration or combat mode
- **THEN** the page contains no dock-menu row region and no dock detail pane
  outside the action dock's pane host

#### Scenario: The scene overview is the host's only child
- **WHEN** the dock is at the exploration root, and then a target's verb popover opens over it
- **THEN** the scene overview component is the pane host's only child, fills its width, and renders
  no detail pane, and the popover's card renders in the dock's overlay layer while the pane host's
  children stay unchanged
