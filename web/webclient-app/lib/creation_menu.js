// ESM wrapper over the preserved DOM-independent character-creation menu model
// (web/static/webclient/js/elosern/creation_menu.js). The UMD source and its
// Node gate are never edited; the bundle imports it through Vite's CommonJS
// interop (design D1) exactly like the keyboard router and combat menu wrappers.
import CreationMenu from "../../static/webclient/js/elosern/creation_menu.js";

export default CreationMenu;
