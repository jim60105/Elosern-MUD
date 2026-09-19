// CharacterStatusDrawer persona-editing group (add-persona-edit-surface D4):
// the inline editor state machine extracted verbatim from
// `CharacterStatusDrawer.vue`. Owns the at-most-one-open editing field, the
// code-point-bound draft, and the refresh-reseeding watcher (the watch stays
// with the state it mutates). Consumes the character group's `personaSections`
// computed and the SFC's `persona-edit` emit explicitly.
import { ref, watch } from "vue";

export function useStatusDrawerPersona(emit, personaSections) {
  // Inline editing state: at most one section is open; the draft is seeded
  // from the committed value on open. Submitting emits exactly one
  // `persona-edit` intent ({ field, text }) — AppClient turns it into a
  // single character.persona.update action. A blank draft submits null
  // (clearing); the shared 600-code-point bound is enforced client-side by
  // code-point truncation on input (never the UTF-16-unit `maxlength`, which
  // would reject astral text the server accepts) and re-validated
  // deterministically server-side.
  const PERSONA_FIELD_BOUND = 600;
  const editingField = ref(null);
  const editDraft = ref("");
  // The committed value the open draft was seeded from. If a completion
  // publication refreshes the edited field from elsewhere (e.g. a Telnet
  // edit), the refresh wins: the watcher re-seeds the draft so a stale
  // editor can never overwrite a newer committed value.
  const editBaseline = ref(null);

  function committedValue(key) {
    const section = personaSections.value.find((s) => s.key === key);
    return section ? section.value : null;
  }

  // Code-point truncation: the bound counts Unicode code points (matching
  // world/rules/character_creation.MAX_PERSONA_FIELD_LENGTH), so an astral
  // character consumes ONE unit here, not two.
  function onPersonaInput(event) {
    const chars = Array.from(event.target.value);
    if (chars.length > PERSONA_FIELD_BOUND) {
      editDraft.value = chars.slice(0, PERSONA_FIELD_BOUND).join("");
    }
  }

  watch(
    () => (editingField.value === null ? null : committedValue(editingField.value)),
    (value) => {
      if (editingField.value !== null && value !== editBaseline.value) {
        editDraft.value = value ?? "";
        editBaseline.value = value;
      }
    }
  );

  function openPersonaEdit(section) {
    editingField.value = section.key;
    editDraft.value = section.value ?? "";
    editBaseline.value = section.value;
  }

  function cancelPersonaEdit() {
    editingField.value = null;
    editDraft.value = "";
    editBaseline.value = null;
  }

  function submitPersonaEdit(section) {
    const trimmed = editDraft.value.trim();
    emit("persona-edit", { field: section.key, text: trimmed === "" ? null : trimmed });
    cancelPersonaEdit();
  }

  return {
    editingField,
    editDraft,
    onPersonaInput,
    openPersonaEdit,
    cancelPersonaEdit,
    submitPersonaEdit,
  };
}
