// ESM wrapper over the preserved DOM-independent combat-menu model
// (web/static/webclient/js/elosern/combat_menu.js). The UMD source and its
// Node gate are never edited; the bundle imports it through Vite's CommonJS
// interop (design D1) exactly like the keyboard router wrapper.
import CombatMenu from "../../static/webclient/js/elosern/combat_menu.js";

export default CombatMenu;
