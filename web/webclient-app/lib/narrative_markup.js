// ESM wrapper over the preserved narrative markup tokenizer
// (web/static/webclient/js/elosern/narrative_markup.js). The UMD source and the
// dependency-free Node gate are never edited; the bundle imports it through
// Vite's CommonJS interop (design D1).
import NarrativeMarkup from "../../static/webclient/js/elosern/narrative_markup.js";

export default NarrativeMarkup;
