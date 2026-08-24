// ESM wrapper over the preserved DOM-independent command-line catalog
// (web/static/webclient/js/elosern/command_echo.js). The UMD source and its
// Node gate are never edited; the bundle imports it through Vite's CommonJS
// interop exactly like the other preserved-module wrappers.
import CommandEcho from "../../static/webclient/js/elosern/command_echo.js";

export default CommandEcho;
