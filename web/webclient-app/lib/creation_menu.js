// ESM wrapper over the preserved DOM-independent character-creation menu model
// (web/static/webclient/js/elosern/creation_menu.js). The UMD source keeps its
// own Node gate (creation-preset-card-wall retired its preset mutation rows
// there); the bundle imports it through Vite's CommonJS interop (design D1)
// exactly like the keyboard router and combat menu wrappers.
import CreationMenu from "../../static/webclient/js/elosern/creation_menu.js";

export default CreationMenu;
