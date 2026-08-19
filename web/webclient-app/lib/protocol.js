// ESM wrapper over the preserved OOB protocol reducer
// (web/static/webclient/js/elosern/protocol.js). The UMD source and the
// dependency-free Node gate are never edited; the bundle imports them through
// Vite's CommonJS interop (design D1).
import Protocol from "../../static/webclient/js/elosern/protocol.js";

export default Protocol;
