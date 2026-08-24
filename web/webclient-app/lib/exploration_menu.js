// ESM wrapper over the preserved DOM-independent exploration-menu model
// (web/static/webclient/js/elosern/exploration_menu.js). The UMD source and
// its Node gate are never edited; the bundle imports it through Vite's
// CommonJS interop (design D1) exactly like the combat/creation menu wrappers.
import ExplorationMenu from "../../static/webclient/js/elosern/exploration_menu.js";

export default ExplorationMenu;
