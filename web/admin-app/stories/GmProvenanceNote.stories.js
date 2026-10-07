import { h } from "vue";
import GmProvenanceNote from "../components/GmProvenanceNote.vue";

// GmProvenanceNote: every world-data page names its source path and how a
// change takes effect — loaded registry data (edit, then restart), disk text
// (not necessarily what is loaded) and the prompt library's reload exception.
export default {
  title: "GM/GmProvenanceNote",
  component: GmProvenanceNote,
  args: { path: "world/lore/monster_species.py", variant: "loaded" },
  render: (args) => ({
    setup: () => () => h("div", { style: { padding: "32px", maxWidth: "880px" } }, [h(GmProvenanceNote, args)]),
  }),
};

export const LoadedRegistry = {};

export const DiskRulebook = { args: { path: "world/rules/rulebook/t_rules.yaml", variant: "disk" } };

export const ReloadablePrompts = { args: { path: "prompts/t_voice.yaml", variant: "reloadable" } };

export const LongPath = {
  args: { path: "world/lore/settlements/places_altoria_lower_t_fixture_with_a_very_long_name.py" },
};
