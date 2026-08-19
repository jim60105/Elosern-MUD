// ESM wrapper over the preserved local-map render model
// (web/static/webclient/js/elosern/local_map.js). The UMD source and the
// dependency-free Node gate are never edited; the bundle imports it through
// Vite's CommonJS interop (design D1).
import LocalMap from "../../static/webclient/js/elosern/local_map.js";

export default LocalMap;
