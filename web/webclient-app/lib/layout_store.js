// ESM wrapper over the preserved versioned layout-persistence UMD
// (web/static/webclient/js/elosern/layout_store.js). The UMD source is
// imported through Vite's CommonJS interop (design D1), mirroring
// lib/protocol.js so the browser-acceptance tests can reach
// `Elosern.LayoutStore` on `window.Elosern`.
import LayoutStore from "../../static/webclient/js/elosern/layout_store.js";

export default LayoutStore;
