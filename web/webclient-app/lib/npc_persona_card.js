// ESM wrapper over the DOM-independent compact NPC card contract mirror
// (web/static/webclient/js/elosern/npc_persona_card.js). The UMD source and
// its Node gate stay the single implementation; the bundle imports it through
// Vite's CommonJS interop exactly like the other shared-module wrappers.
import NpcPersonaCard from "../../static/webclient/js/elosern/npc_persona_card.js";

export default NpcPersonaCard;
