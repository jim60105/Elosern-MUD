# Standalone Map Editor Frontend Design Requirements

**Date:** 2026-10-26
**Status:** Design decisions approved in conversation; written-spec review pending.
**Audience:** Frontend/UX/visual designer and subsequent implementers.
**Authority:** [Standalone Developer Map Editor Design](2026-10-26-map-editor-design.md).

This brief defines the information, operations, states, and acceptance criteria that the editor design must support. Panel arrangement, visual theme, typography, component appearance, and detailed responsive composition belong to the subsequent designer. This document is a requirements handoff, not an implemented interface or a visual mockup.

## 1. Product and user context

The user is a developer editing the complete static world from a local browser. They use external OMP in another window to discuss changes with an AI that edits the same YAML files. Manual editing and AI editing take turns. The editor neither hosts the conversation nor starts or controls that external process.

The developer needs to understand where an object belongs, change it, inspect its connections and validation results, and tell whether the visible result is saved and current. Navigating, inspecting, and preparing context must remain useful during an AI turn.

The interface covers continental geography/locations/districts, settlement graphs, permanent coordinate-free interiors, and cross-layer entrances. It must not require a running game, game account, Evennia/Django installation, or game database.

Excluded surfaces are embedded chat, code/YAML editing, model settings, AI execution, diff/merge review, Git management, live game state, NPC/dialogue authoring, and shop/economy/quest editors. Do not allocate navigation or empty placeholders for those excluded products.

Use Traditional Chinese interface copy with English stable identifiers and standard technical units. Do not add a multilingual subsystem as part of this scope. Preserve canonical authored names and prose.

## 2. Target environment and accessibility

Design for current stable desktop Chromium and Firefox with mouse and keyboard. Provide primary layouts at 1280 by 800 and 1920 by 1080 CSS pixels, plus a compact 960 by 720 variant usable alongside OMP. The compact variant may disclose tools progressively; it must not make essential actions or state inaccessible.

Mobile/touch-first and gamepad designs are outside scope. Do not inherit the game client's fixed stage composition, decorative theme, or player-facing controls.

Target WCAG 2.2 AA for the application, including keyboard access and visible focus. Essential operations must have an alternative to dragging. Map meaning must have a textual inspection path; direction, errors, ownership, stale state, and selection cannot depend solely on color. Support browser zoom to 200 percent by reflowing/disclosing application controls instead of requiring all surfaces to remain open.

The future designer must specify focus order, focus restoration after dialogs/navigation, accessible action names, field error association, and a usable text/list alternative to map-only interaction. Hover must not be the only way to discover an action or read a full name.

## 3. Required functional surfaces

A surface is an information/interaction responsibility, not a required page or panel position.

| Surface | Information and actions |
| --- | --- |
| Workspace state | Workspace identity, service connection, current turn, save status, current/stale preview status, and explicit resume/reload actions. |
| World navigation | Domain/map selection, location-to-local-map navigation, source-document ownership, search, and return navigation. |
| Map workspace | Layer visibility, domain tools, viewport controls, selection/multi-selection, direct manipulation, and geometric previews. |
| Object inspection | Name, stable qualified identity, source path, current field values, incoming/outgoing relationships, and contextual actions. |
| Explicit editing controls | Numeric coordinate/control-point inputs, endpoint/direction selectors, text fields, and add/remove controls equivalent to canvas tools. |
| Diagnostics | Error category, explanation, object/file/field location, and navigation to the affected data. |
| Derived-data status | Partition freshness, explicit regeneration, running/cancelled/failed status, and the input revision represented by an output. |
| External collaboration | Save-before-handoff, read-only AI turn, reread-and-resume, and copy-only selection context for external OMP. |

Reading priority must make ownership, failed saves, and stale previews discoverable before the user mistakes a preview for saved current data. A transient toast alone is insufficient for those conditions.

Names can be duplicated. Search results and inspection must include enough parent-map/source context to distinguish them. Stable IDs and source paths must be readable/copyable without becoming the primary display label everywhere.

## 4. Domain requirements

### 4.1 Continental geography and locations

The developer must be able to select, add/remove, and reposition supported geometry vertices/control points, with numeric alternatives. Expose the existing model's mainland boundary, waterways, forest/terrain boundaries, ridge parameters, passes and fords. Distinguish a control point from the feature it controls.

Preview deterministic terrain and passability. Show the coordinate frame/unit where an input or measurement is edited. Wilderness cell indices, geographic kilometre geometry, and absolute metres must never appear as an unlabelled common coordinate field.

Support static geographic location creation, naming, placement and inspection, including locations that have no built local map. Offer navigation to an authored local map when present; otherwise show that absence without fabricating rooms or blocking geographic authoring.

Provide settlement footprint-mask editing with an explicit cell-based alternative, district/landmark editing, and local/world binding inspection. Distinguish authored inputs from derived national/district boundaries. Derived output must not display handles that imply unrelated direct editing.

Partition regeneration is an explicit action. Relevant source changes mark the output stale; do not silently regenerate at each drag. The old output may be inspected only with its stale status visible.

### 4.2 Settlement graphs

Support creating, moving, duplicating and deleting room nodes, and editing map-owned name, description, prototype fields and scene references. New nodes receive new stable IDs. Moving or renaming the display label does not rename the identity.

Show and edit directed roads, including an explicit create-bidirectional option. Expose source/destination, authored compass direction, optional bends, and physical length. A two-way street must remain understandable as two directed travel directions. Dragging a node must not silently recompute the compass exit.

Support single-document multi-selection, including selection through a list without a box gesture. Multi-node movement is one completed command within that source document. Cross-document selection may be inspected/copied, but cross-document batch mutation is unavailable with an explained reason.

Offer explicit endpoint/direction selectors and bend-point controls. Canvas length is not travel geometry; measurements and route checks come from the shared core.

### 4.3 Permanent interiors

Show rooms and directed/named connections without suggesting physical distance. Label layout positions as editor-only and keep world metre/kilometre coordinate inputs absent.

Support room creation/duplication/deletion, name/description/scene references, internal connections, and exterior entrances. Existing service-room identity must remain inspectable, but an interior must not require a shop/NPC/service record.

Room layout may be rearranged and saved separately from world geometry. A newly added room may use an automatic initial placement without implying that it has a physical coordinate. Layout-only edits must not change game geometry or route lengths.

### 4.4 Cross-layer relationships

Both entrance endpoints must be identifiable and navigable. Show their map/domain, stable identity, directional labels and one-way/two-way meaning. Persist one owning relationship; do not imply that the user must manually edit a mirrored reverse record.

Following an entrance must preserve useful return context. Editing an endpoint uses a qualified object selector rather than a display-name match or unlabelled coordinate string. Invalid endpoints identify the offending relationship and location.

## 5. Editing, persistence, and validation

### 5.1 Manual operation flow

The design must communicate the following operation boundary:

1. Select an object or complete a creation/connection tool.
2. Change draft fields or geometry.
3. Confirm the field, release the drag, or finish the operation.
4. Validate the complete one-document command and save it.
5. Show the saved result or a persistent, recoverable failure.

A drag is one undoable operation. Text entry does not write on every keystroke. Escape cancels an incomplete tool or field edit without turning the partial value into a save. Save can explicitly flush completed work, but must not force invalid drafts into files.

Distinguish an uncommitted field draft, in-flight save, confirmed save, failed save, and uncertain/paused persistence. Do not use one undifferentiated dirty marker for all of them. A failed handoff must leave an intelligible manual state with its cause visible.

Undo/redo applies to the current manual segment and is saved through the same command path. Show its availability and explain that handoff/external reload clears the history. Do not offer replay of a previous segment against AI-modified files.

### 5.2 Diagnostic classes

| Class | Required presentation |
| --- | --- |
| Field/authoring-structure failure | Explain the value or structure preventing save/editing, identify its source, and support correction/cancellation or external repair as appropriate. |
| Saveable semantic work-in-progress | Permit saving/manual repair while showing the issue; do not claim playable/valid runtime data. |
| External reference invalid | Identify the scene/service/quest/lore reference and source when known; keep map-only and external results distinct. |
| External reference unavailable | State that the read-only index is missing/stale/incompatible. Do not present unknown as valid; explain why deletion is disabled. |
| Partition stale | Separate saved source from generated-output freshness; offer explicit regeneration when permitted. |
| Service/save failure | Retain understandable saved-versus-visible state, block unsafe writes, and provide an explicit recovery path. |

Diagnostics must locate their object when possible, even if a layer is hidden. Reveal or offer to reveal that layer; do not navigate silently to an invisible selection. A source-only parse error must still expose file/line information without requiring an embedded source editor.

The standalone UI may report that static checks have passed using a current external index. It must still state that authoritative game adoption occurs in the game environment; passing editor checks does not certify live save-game dependents.

### 5.3 Deletion and references

Refuse deletion while map or current-index external static references remain. List the references and provide navigation to address them. A missing/stale external index disables deletion conservatively, while ordinary inspection, placement and property editing remain available.

Deletion does not cascade into other documents or non-map content. Communicate affected objects and undo availability before a destructive operation. Avoid a confirmation modal for every reversible ordinary edit; the designer must identify which destructive transitions need confirmation.

## 6. External AI turn and recovery

### 6.1 Handoff

The user requests an external turn. Resolve active field drafts, finish admitted saves, and grant the turn only after successful persistence. No new manual mutation is admitted while the handoff is completing.

During the external turn, disable every mutation path, including shortcuts, context menus, paste, undo/redo, layout edits and generated-output publication. Keep browsing, search, selection, inspection, layer visibility and viewport controls useful.

State plainly that OMP runs externally. Do not display invented process progress, a stop-AI button, or a completion claim inferred from filesystem silence.

### 6.2 Live file preview

Reload after short notification coalescing. A successful reload preserves the current map, view and selection where stable identities still exist. Do not reset to the whole continent after each file update.

If parsing/authoring loading fails, retain the last previewable snapshot with a persistent stale label and current-file diagnostics. Inspector values from that snapshot must not appear to be confirmed current disk values. With no prior snapshot, show unavailable preview, not a valid-looking empty map.

If a selected object disappears, clear selection and explain its removal. Do not select an object with the same display name as a substitute.

### 6.3 Return and interruption

The user first stops the external writer, then explicitly requests reread and return to manual editing. Load current files before enabling writes. A loadable world with semantic diagnostics can return for repair; malformed structure remains read-only pending external correction.

There is no action that saves AI results by rewriting an older browser snapshot. A return action confirms adoption of disk state, not an extra serialization of pre-AI memory.

Unexpected external writes in manual mode pause mutations and require reload. Explain any draft/history loss before explicit reload; no merge or diff surface is introduced.

A disconnected service retains the last preview as an inspection aid with a disconnected/stale indication. Startup, browser reconnection and service restart require fresh authoritative state and explicit resume. Do not replay pending commands or restore write permission from browser storage. View preferences can survive within the live session; persistent cross-refresh workspace/view restoration is not required.

## 7. Copy-only OMP context

Provide a user-triggered action that copies plain text for the current selection, including multi-selection. Include workspace-relative source paths, domain/map, qualified stable IDs, relevant coordinate frame/units, and whether the context comes from current files or a stale preview.

The copied text also states the current manual/external ownership and the save-before/stop-before-return agreement. It must not imply an AI prompt was submitted or a task started. It contains no session token, credentials, or external conversation history.

This clipboard action is the required context bridge. Do not add an automatic selection-file protocol, model integration, or editor-control API for OMP as part of this scope.

## 8. Keyboard and focus contract

Specify accessible controls for zoom/fit, object selection, geometry numeric entry, adding/removing vertices/bends, road/entrance endpoint selection, undo/redo, handoff and reload. A keyboard user must complete the same essential edits without dragging.

Use conventional platform-aware undo/redo and save shortcuts. Define Escape cancellation and scope shortcuts so that typing in an input does not delete a map object, switch tools, or steal text-editor undo. Disabled actions must have discoverable reasons.

After a failed field submission, focus stays with or returns to the relevant field. After closing a dialog, restore its trigger. After following a diagnostic or cross-map relationship, expose the destination context without losing the ability to return. Selection and inspection must be readable without pointer hover.

The designer may choose the exact object-list/graph keyboard-navigation pattern, but must demonstrate all required workflows with it and document focus behavior. Color-only direction arrows, icon-only unexplained mode states, and inaccessible canvas-only controls fail acceptance.

## 9. Required state inventory

Design the actual content and available actions for each state; do not supply only happy-path screens.

| State | Required distinction |
| --- | --- |
| First open / no loaded data | Loading, invalid source, absent local map, and a valid unfinished map are different states. |
| No selection / single / multi | Applicable tools, source ownership, mixed properties and selection summary. |
| Incomplete field/tool | Draft value, confirm/cancel, and safe departure behavior. |
| Saving / saved / failed / uncertain | Persistence state separate from semantic validation. |
| Manual / handoff pending / external / return pending | Writer permission and next user action. |
| Current / stale / unavailable preview | Which disk content the displayed information represents. |
| External index current / invalid / unavailable | What reference claims are supported and why deletion may be disabled. |
| Partition current / stale / generating / cancelled / failed | Output/input relationship and explicit regeneration. |
| Unexpected external write | Paused mutation, reload requirement, and draft/history consequences. |
| Service disconnected / restarted | Inspection-only status and explicit resume after reread. |
| Referenced deletion | Identified dependents; no implicit cascade. |
| Hidden diagnostic target / removed selection | Reveal/navigation action or an explanation of absence. |

Generation runs with world-data mutations and AI handoff unavailable. Browsing remains available, and cancellation/failure does not replace the last artifact. Do not show a completed output as current if its input changed.

## 10. Acceptance scenarios

These are planned design/implementation acceptance cases. They were not executed for this document.

| Scenario | Observable acceptance |
| --- | --- |
| Move a river control point | The correct coordinate frame is labelled; release completes one operation; derived terrain preview and freshness status reflect the change. |
| Add a geographic location without a local map | It is editable/searchable; the UI states that no local map exists instead of inventing one. |
| Move a settlement node | ID and authored compass direction remain unchanged; its gate, interior, district and scene relationships still resolve to the moved object. |
| Create a bidirectional street | Both directed meanings can be inspected; one completed command saves their common document. |
| Rearrange an interior | Only editor layout changes; no physical world coordinates or distances are introduced. |
| Edit an entrance | Both endpoints and return semantics are identifiable; navigation works in both relevant directions. |
| Enter an incomplete number or duplicate identity | No invalid file save; the error and correction/cancel path are visible. |
| Save semantic work-in-progress | Save succeeds while runtime-blocking diagnostics remain; the interface does not claim game adoption. |
| Remove a referenced object | Deletion is refused with locatable references, without cascading changes. |
| Use a stale/missing external index | External validation is unavailable and deletion is disabled; ordinary non-destructive editing remains possible. |
| Fail a save during handoff | External ownership is not granted; the failure remains visible. |
| Browse while AI edits | Browse/search/select/inspect work; every manual mutation path is unavailable. |
| Replace YAML with malformed then corrected contents | The last preview is visibly stale with file diagnostics, then updates from corrected disk data without writing old memory. |
| Return after AI leaves an inaccessible landmark | Loadable data returns to manual repair with a semantic diagnostic; game readiness is not implied. |
| Receive an unexpected manual-mode file change | Writing pauses; explicit reload explains draft/history consequences; no merging occurs. |
| Reconnect an old tab or restart the service | Old writes are rejected; fresh state and explicit resume precede new writes. |
| Change source while partition generation is running | The result is not labelled or published as current; failure/cancellation retains the prior artifact. |
| Reload after a selected object moves/disappears | Stable identity preserves selection/view when possible; removal clears selection with an explanation. |
| Copy context for OMP | Copied text identifies selection/source/units/currentness without executing a task or leaking service credentials. |
| Complete edits using keyboard and explicit inputs | Geometry, roads, entrances, diagnostics and handoff remain usable without dragging. |
| Use compact dimensions, long Chinese names and 200 percent zoom | Essential controls/status remain reachable, with no requirement for all tool surfaces to stay open. |

## 11. Deliverables required from the subsequent designer

Provide annotated designs for continental, settlement and interior editing, including cross-layer relationships. Include first-use/unavailable data, normal editing, AI read-only, stale-preview, reference failure, regeneration and disconnected states from the inventory.

Deliver a content hierarchy and navigation model, annotated interaction flows including failure/recovery, component/state specifications, keyboard/focus behavior, and primary/compact/zoomed variants. Use representative long names/IDs, dense graphs, multiline descriptions, multiple diagnostics and footprint masks instead of only sparse ideal examples.

Map each acceptance scenario to the proposed design. Record choices about confirmations, responsive disclosure and graph keyboard navigation. Keep package boundaries and file-format details out of the user-facing navigation unless they explain source ownership or an error.

No particular panel placement, ornamental style, color palette, icon treatment or game-theme resemblance is mandated. Any proposed visual design must preserve the architecture and turn-taking/save guarantees in the companion design.
