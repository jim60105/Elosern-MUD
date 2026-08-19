// ESM wrapper over the preserved narrative choice-point state machine
// (web/static/webclient/js/elosern/choicepoint_logic.js). The UMD source and the
// dependency-free Node gate are never edited; the bundle imports it through
// Vite's CommonJS interop (design D1).
import ChoicePointLogic from "../../static/webclient/js/elosern/choicepoint_logic.js";

export default ChoicePointLogic;
