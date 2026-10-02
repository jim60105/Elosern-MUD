import NpcPersonaEditor from "../../components/NpcPersonaEditor.vue";
import { npcPersonaEditorStates } from "../npc-persona-fixtures.js";

// NpcPersonaEditor (npc-persona-editor-window D7): the NPC author editor on
// the shared drawer frame, one story per editor state. Deterministic and
// offline: every story is a fixed view model computed through the shared
// card-contract mirror. Interactions are inert here (the live client wires
// them to the correlated read/update state machine).

export default {
  title: "Overlays/NpcPersonaEditor",
  component: NpcPersonaEditor,
  parameters: { layout: "fullscreen" },
};

export const Loading = { args: { editor: npcPersonaEditorStates.loading() } };

export const Clean = { args: { editor: npcPersonaEditorStates.clean() } };
export const Dirty = { args: { editor: npcPersonaEditorStates.dirty() } };

// A dirty draft whose speech style overflows its 600-code-point leaf and the
// card total, with an emptied required field: save is disabled and nothing is
// truncated.
export const DirtyOverBudget = { args: { editor: npcPersonaEditorStates.dirtyOverBudget() } };

// Saving with a filled offline greeting over a table-backed default.
export const SavingWithGreeting = { args: { editor: npcPersonaEditorStates.saving() } };

export const FieldRejected = { args: { editor: npcPersonaEditorStates.rejected() } };

export const Conflict = { args: { editor: npcPersonaEditorStates.conflict() } };

export const Unavailable = { args: { editor: npcPersonaEditorStates.departed() } };
export const ResyncRejected = { args: { editor: npcPersonaEditorStates.resyncFailed() } };

export const ReadFailed = { args: { editor: npcPersonaEditorStates.readFailed() } };

// A free-form NPC: no authored default (the preview reads 無) and a stored
// override in the greeting field.
export const FreeFormNoDefault = { args: { editor: npcPersonaEditorStates.freeFormNoDefault() } };

// The narrow single-column layout (the dossier collapses to a fixed strip
// above the scrolling form; save and cancel stay in the fixed foot).
export const NarrowViewport = {
  args: { editor: npcPersonaEditorStates.dirtyOverBudget() },
  parameters: { viewport: { defaultViewport: "mobile2" } },
  globals: { viewport: { value: "mobile2", isRotated: false } },
};
