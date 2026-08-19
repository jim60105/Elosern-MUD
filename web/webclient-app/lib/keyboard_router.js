// ESM wrapper over the preserved DOM-independent keyboard focus router
// (web/static/webclient/js/elosern/keyboard_router.js). The UMD source and the
// dependency-free Node gate are never edited; the bundle imports it through
// Vite's CommonJS interop (design D1).
import KeyboardRouter from "../../static/webclient/js/elosern/keyboard_router.js";

export default KeyboardRouter;
