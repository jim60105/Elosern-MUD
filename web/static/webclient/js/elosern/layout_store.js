/*
 * Elosern versioned layout persistence.
 *
 * DOM-independent. localStorage holds ONLY a bounded wrapper containing the
 * project layout version, safe GoldenLayout dimensions, open-tab state for
 * optional components, and harmless display preferences. It never stores a
 * transport generation, active or retired epoch, revision, panel payload,
 * actor identifier, request result, command text, credential, or canonical
 * game state.
 *
 * A storage object is injected for tests; in the browser it defaults to
 * localStorage. Stock Evennia GoldenLayout keys are never read.
 */
(function (root, factory) {
  "use strict";
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.Elosern = root.Elosern || {};
    root.Elosern.LayoutStore = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var CURRENT_LAYOUT_VERSION = 1;
  var STORAGE_KEY = "elosern.layout";
  // Stock Evennia pre-project keys are never imported by version 1.
  var STOCK_KEYS = [
    "evenniaGoldenLayoutSavedState",
    "evenniaGoldenLayoutSavedStateName",
  ];

  var MAX_STORAGE_BYTES = 2048;
  var MIN_DIMENSION = 5;
  var MAX_DIMENSION = 95;
  var MIN_FONT_SCALE = 0.5;
  var MAX_FONT_SCALE = 2;

  var REQUIRED_COMPONENTS = [
    "header",
    "narrative",
    "art",
    "status",
    "local-map",
    "action-dock",
    "command-drawer",
  ];

  // Only harmless display preferences may be persisted.
  var PREFERENCE_TYPES = {
    text2html: "boolean",
    fontScale: "number",
  };

  var REQUIRED_SET = {};
  REQUIRED_COMPONENTS.forEach(function (name) {
    REQUIRED_SET[name] = true;
  });

  // The approved version-1 desktop layout. Required components and the action
  // dock are non-closable; narrative is the primary, largest surface.
  var DEFAULT_LAYOUT_CONFIG = {
    settings: {
      hasHeaders: true,
      constrainDragToContainer: true,
      reorderEnabled: false,
      selectionEnabled: false,
      showPopoutIcon: false,
      showMaximiseIcon: false,
      showCloseIcon: false,
    },
    dimensions: {
      headerHeight: 28,
      borderWidth: 3,
    },
    content: [
      {
        type: "row",
        content: [
          {
            type: "column",
            content: [
              { type: "component", componentName: "header", isClosable: false, height: 7 },
              {
                type: "row",
                content: [
                  { type: "component", componentName: "narrative", isClosable: false, width: 62 },
                  {
                    type: "column",
                    content: [
                      { type: "component", componentName: "art", isClosable: false, height: 34 },
                      { type: "component", componentName: "status", isClosable: false, height: 33 },
                      { type: "component", componentName: "local-map", isClosable: false, height: 33 },
                    ],
                  },
                ],
              },
              { type: "component", componentName: "action-dock", isClosable: false, height: 9 },
              {
                type: "component",
                componentName: "command-drawer",
                isClosable: false,
                height: 9,
                id: "inputComponent",
              },
            ],
          },
        ],
      },
    ],
  };

  function isPlainObject(value) {
    return typeof value === "object" && value !== null && !Array.isArray(value);
  }

  function isSafeInteger(value) {
    return (
      typeof value === "number" &&
      Number.isInteger(value) &&
      value >= 0 &&
      value <= Number.MAX_SAFE_INTEGER
    );
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function defaultWrapper() {
    return {
      layout_version: CURRENT_LAYOUT_VERSION,
      dimensions: {},
      tabs: {},
      preferences: { text2html: true },
    };
  }

  function normalizePreferences(raw) {
    var cleaned = {};
    if (!isPlainObject(raw)) {
      return cleaned;
    }
    Object.keys(PREFERENCE_TYPES).forEach(function (key) {
      if (Object.prototype.hasOwnProperty.call(raw, key)) {
        var value = raw[key];
        if (PREFERENCE_TYPES[key] === "boolean" && typeof value === "boolean") {
          cleaned[key] = value;
        } else if (
          PREFERENCE_TYPES[key] === "number" &&
          typeof value === "number" &&
          isFinite(value) &&
          key === "fontScale" &&
          value >= MIN_FONT_SCALE &&
          value <= MAX_FONT_SCALE
        ) {
          cleaned[key] = value;
        }
      }
    });
    return cleaned;
  }

  function normalizeDimensions(raw) {
    var cleaned = {};
    if (!isPlainObject(raw)) {
      return cleaned;
    }
    Object.keys(raw).forEach(function (key) {
      if (Object.prototype.hasOwnProperty.call(REQUIRED_SET, key)) {
        var value = raw[key];
        if (
          typeof value === "number" &&
          isFinite(value) &&
          value >= MIN_DIMENSION &&
          value <= MAX_DIMENSION
        ) {
          cleaned[key] = value;
        }
      }
    });
    return cleaned;
  }

  function normalizeTabs(raw) {
    var cleaned = {};
    if (!isPlainObject(raw)) {
      return cleaned;
    }
    Object.keys(raw).forEach(function (key) {
      if (Object.prototype.hasOwnProperty.call(REQUIRED_SET, key)) {
        if (typeof raw[key] === "boolean") {
          cleaned[key] = raw[key];
        }
      }
    });
    return cleaned;
  }

  // Validate and clean a stored wrapper. Returns the cleaned wrapper, or null
  // when the value is missing, malformed, oversized, an unknown version, or
  // carries a field outside the presentation-only whitelist.
  function validateWrapper(raw) {
    if (!isPlainObject(raw)) {
      return null;
    }
    // Oversized stored values always reset regardless of content.
    if (JSON.stringify(raw).length > MAX_STORAGE_BYTES) {
      return null;
    }
    // Reject canonical state / identity / request / command / epoch /
    // revision / panel fields by whitelisting the only allowed keys.
    var allowed = { layout_version: true, dimensions: true, tabs: true, preferences: true };
    var keys = Object.keys(raw);
    for (var i = 0; i < keys.length; i++) {
      if (!allowed[keys[i]]) {
        return null;
      }
    }
    if (!isSafeInteger(raw.layout_version)) {
      return null;
    }
    var cleaned = {
      layout_version: raw.layout_version,
      dimensions: normalizeDimensions(raw.dimensions),
      tabs: normalizeTabs(raw.tabs),
      preferences: normalizePreferences(raw.preferences),
    };
    if (JSON.stringify(cleaned).length > MAX_STORAGE_BYTES) {
      return null;
    }
    return cleaned;
  }

  function walkConfigItems(config, visitor) {
    if (!isPlainObject(config)) {
      return;
    }
    if (Array.isArray(config.content)) {
      config.content.forEach(function (item) {
        walkConfigItems(item, visitor);
      });
    }
    visitor(config);
  }

  // Extract the bounded per-required-component width/height percentages from a
  // GoldenLayout-serialized config. Only required component names are kept.
  function extractDimensions(config) {
    var dimensions = {};
    walkConfigItems(config, function (item) {
      if (
        item.type === "component" &&
        Object.prototype.hasOwnProperty.call(REQUIRED_SET, item.componentName)
      ) {
        if (
          typeof item.width === "number" &&
          item.width >= MIN_DIMENSION &&
          item.width <= MAX_DIMENSION
        ) {
          dimensions[item.componentName] = item.width;
        }
        if (
          typeof item.height === "number" &&
          item.height >= MIN_DIMENSION &&
          item.height <= MAX_DIMENSION
        ) {
          dimensions[item.componentName] = item.height;
        }
      }
    });
    return dimensions;
  }

  // Apply persisted dimensions onto a config tree (never removes components).
  function applyDimensions(config, dimensions) {
    var dims = normalizeDimensions(dimensions);
    walkConfigItems(config, function (item) {
      if (
        item.type === "component" &&
        Object.prototype.hasOwnProperty.call(dims, item.componentName)
      ) {
        item.width = dims[item.componentName];
        item.height = dims[item.componentName];
      }
    });
    return config;
  }

  // Ensure every required component appears in the config; required components
  // are never closable. Missing ones are appended to the outermost column.
  function restoreRequiredComponents(config) {
    var present = {};
    walkConfigItems(config, function (item) {
      if (item.type === "component") {
        present[item.componentName] = true;
      }
    });
    var missing = REQUIRED_COMPONENTS.filter(function (name) {
      return !present[name];
    });
    if (missing.length === 0) {
      return config;
    }
    var outer = config;
    while (Array.isArray(outer.content) && outer.content.length === 1) {
      outer = outer.content[0];
    }
    var column = outer;
    if (!isPlainObject(column) || column.type !== "column") {
      if (!Array.isArray(column.content)) {
        column = { type: "column", content: [] };
        outer.content = [column];
      } else {
        var found = null;
        walkConfigItems(column, function (item) {
          if (item.type === "column" && !found) {
            found = item;
          }
        });
        column = found || { type: "column", content: [] };
        outer.content.push(column);
      }
    }
    missing.forEach(function (name) {
      var item = { type: "component", componentName: name, isClosable: false };
      if (name === "command-drawer") {
        item.id = "inputComponent";
      }
      column.content.push(item);
    });
    return config;
  }

  function buildConfig(wrapper) {
    var config = restoreRequiredComponents(applyDimensions(clone(DEFAULT_LAYOUT_CONFIG), wrapper.dimensions));
    return config;
  }

  function createStore(options) {
    options = options || {};
    var storage = options.storage;
    var key = options.key || STORAGE_KEY;
    var migrations = options.migrations || { 1: function (raw) { return raw; } };
    var currentVersion = options.currentVersion || CURRENT_LAYOUT_VERSION;

    function migrate(wrapper) {
      var version = wrapper.layout_version;
      if (!Object.prototype.hasOwnProperty.call(migrations, version)) {
        return null;
      }
      var candidate;
      try {
        candidate = migrations[version](clone(wrapper));
      } catch (error) {
        return null;
      }
      if (!isPlainObject(candidate)) {
        return null;
      }
      candidate.layout_version = currentVersion;
      return validateWrapper(candidate);
    }

    function read() {
      if (!storage || typeof storage.getItem !== "function") {
        return { wrapper: defaultWrapper(), migrated: false };
      }
      var raw;
      try {
        raw = storage.getItem(key);
      } catch (error) {
        return { wrapper: defaultWrapper(), migrated: false };
      }
      if (raw === null || raw === undefined) {
        return { wrapper: defaultWrapper(), migrated: false };
      }
      var parsed;
      try {
        parsed = JSON.parse(raw);
      } catch (error) {
        return { wrapper: null, migrated: false };
      }
      var validated = validateWrapper(parsed);
      if (validated === null) {
        return { wrapper: null, migrated: false };
      }
      if (validated.layout_version === currentVersion) {
        return { wrapper: validated, migrated: false };
      }
      var migrated = migrate(validated);
      if (migrated === null) {
        return { wrapper: null, migrated: false };
      }
      return { wrapper: migrated, migrated: true };
    }

    function write(wrapper) {
      var cleaned = validateWrapper(wrapper);
      // Only the current layout version may be persisted; an unknown or stale
      // version must never overwrite the approved default.
      if (
        cleaned === null ||
        cleaned.layout_version !== currentVersion ||
        !storage ||
        typeof storage.setItem !== "function"
      ) {
        return false;
      }
      try {
        storage.setItem(key, JSON.stringify(cleaned));
      } catch (error) {
        return false;
      }
      return true;
    }

    function defaultResult() {
      return { state: defaultWrapper(), config: buildConfig(defaultWrapper()) };
    }

    return {
      // Load the stored wrapper, resetting to the version-1 default when the
      // stored value is missing, malformed, oversized, stock, or unknown.
      load: function () {
        var result = read();
        if (result.wrapper === null) {
          return this.reset();
        }
        // Persist a migration so the next load starts from the current version.
        if (result.migrated) {
          write(result.wrapper);
        }
        return { state: result.wrapper, config: buildConfig(result.wrapper) };
      },
      save: function (wrapper) {
        return write(wrapper);
      },
      reset: function () {
        var result = defaultResult();
        write(result.state);
        return result;
      },
      buildConfig: buildConfig,
      extractDimensions: extractDimensions,
      restoreRequiredComponents: restoreRequiredComponents,
      validateWrapper: validateWrapper,
      get storage() {
        return storage;
      },
      get currentVersion() {
        return currentVersion;
      },
    };
  }

  return {
    CURRENT_LAYOUT_VERSION: CURRENT_LAYOUT_VERSION,
    STORAGE_KEY: STORAGE_KEY,
    STOCK_KEYS: STOCK_KEYS.slice(),
    MAX_STORAGE_BYTES: MAX_STORAGE_BYTES,
    REQUIRED_COMPONENTS: REQUIRED_COMPONENTS.slice(),
    PREFERENCE_TYPES: Object.assign({}, PREFERENCE_TYPES),
    DEFAULT_LAYOUT_CONFIG: clone(DEFAULT_LAYOUT_CONFIG),
    defaultWrapper: defaultWrapper,
    validateWrapper: validateWrapper,
    extractDimensions: extractDimensions,
    applyDimensions: applyDimensions,
    restoreRequiredComponents: restoreRequiredComponents,
    buildConfig: buildConfig,
    createStore: createStore,
  };
});
