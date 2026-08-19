// ESM façade over the preserved DOM-independent logic (design D1).
// The A2 build stub imports it so the production bundle genuinely carries
// the preserved UMD modules through Vite's CommonJS interop; C2's
// browser-bridge replaces this transient surface with the window.Elosern.*
// public façades backed by the same imported modules.
import Protocol from "./lib/protocol.js";
import KeyboardRouter from "./lib/keyboard_router.js";
import NarrativeMarkup from "./lib/narrative_markup.js";
import LocalMap from "./lib/local_map.js";
import ChoicePointLogic from "./lib/choicepoint.js";
import OptionCards from "./lib/option_cards.js";

export {
  Protocol,
  KeyboardRouter,
  NarrativeMarkup,
  LocalMap,
  ChoicePointLogic,
  OptionCards,
};
