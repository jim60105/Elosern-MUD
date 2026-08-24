// ESM wrapper over the preserved DOM-independent service-menu model
// (web/static/webclient/js/elosern/service_menu.js). The UMD source and its
// Node gate are never edited; the bundle imports it through Vite's CommonJS
// interop exactly like the combat/creation/exploration menu wrappers.
import ServiceMenu from "../../static/webclient/js/elosern/service_menu.js";

export default ServiceMenu;
