// ESM wrapper over the preserved narrative stream-end block controller
// (web/static/webclient/js/elosern/stream_end_block.js). The UMD source and the
// dependency-free Node gate are never edited; the bundle imports it through
// Vite's CommonJS interop (design D1).
import StreamEndBlock from "../../static/webclient/js/elosern/stream_end_block.js";

export default StreamEndBlock;
