/*
 * Elosern dependency-free vanilla text console (design D10, webclient-vue-01-foundation).
 *
 * The authoritative text path of the WebClient: a small input/output bound
 * directly to the retained `evennia.js` transport, loaded independent of Vue
 * and jQuery. `createModel` is a DOM-independent pure model (line buffer,
 * prompt, transport state) so the dependency-free Node gate can exercise it;
 * `attach` is the browser adapter that builds the DOM and binds the Evennia
 * emitter — it touches `document` only at call time, never at load.
 *
 * Transport contract (Evennia 6.1 `evennia.js`, jQuery-free apart from its
 * `$(document).ready` bootstrap, which the ready shim satisfies in the Vue
 * branch): `Evennia.msg("text", [line], {})` sends a command; the emitter
 * delivers `text`/`prompt` lines and `connection_open`/`connection_close`/
 * `logged_in` transport events.
 */
(function (root, factory) {
  "use strict";
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.Elosern = root.Elosern || {};
    root.Elosern.TextConsole = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var MAX_LINES = 500;

  function createModel(maxLines) {
    var cap = typeof maxLines === "number" && maxLines > 0 ? maxLines : MAX_LINES;
    var lines = [];
    var prompt = "";
    var connected = false;
    var loggedIn = false;

    function trim() {
      if (lines.length > cap) {
        lines = lines.slice(lines.length - cap);
      }
    }

    return {
      appendOut: function (html) {
        lines.push({ kind: "out", body: String(html) });
        trim();
      },
      appendIn: function (text) {
        lines.push({ kind: "in", body: String(text) });
        trim();
      },
      setPrompt: function (value) {
        prompt = String(value || "");
      },
      setConnected: function (value) {
        connected = !!value;
        if (!connected) {
          loggedIn = false;
        }
      },
      setLoggedIn: function (value) {
        loggedIn = !!value;
      },
      reset: function () {
        lines = [];
        prompt = "";
      },
      lines: function () {
        return lines.slice();
      },
      prompt: function () {
        return prompt;
      },
      // "offline" before the first transport open, "ready" once the account
      // is attached, "waiting" when the socket is up but not logged in.
      status: function () {
        if (loggedIn) {
          return "ready";
        }
        return connected ? "waiting" : "offline";
      },
    };
  }

  var STATUS_TEXT = {
    offline: "連線中…",
    waiting: "等待登入…",
    ready: "就緒",
  };

  function render(model, log, promptEl, statusEl, wrapper) {
    while (log.firstChild) {
      log.removeChild(log.firstChild);
    }
    model.lines().forEach(function (line) {
      var row = document.createElement("div");
      row.className = "text-console__row text-console__row--" + line.kind;
      if (line.kind === "out") {
        // Plain text: transport payload is rendered as data, never as markup.
        // Rich (ANSI/Evennia) markup rendering lands with the shell wave
        // through the allowlisted NarrativeMarkup pipeline.
        row.textContent = line.body;
      } else {
        var prefix = document.createElement("span");
        prefix.className = "text-console__echo-prefix";
        prefix.textContent = "> ";
        var echo = document.createElement("span");
        echo.textContent = line.body;
        row.appendChild(prefix);
        row.appendChild(echo);
      }
      log.appendChild(row);
    });
    promptEl.textContent = model.prompt();
    statusEl.textContent = STATUS_TEXT[model.status()];
    var status = model.status();
    wrapper.setAttribute("data-status", status);
    wrapper.setAttribute("data-connected", status === "ready" ? "true" : "false");
  }

  function attach(root, transport) {
    var model = createModel();
    var wrapper = document.createElement("div");
    wrapper.className = "text-console";
    wrapper.setAttribute("data-testid", "text-console");
    wrapper.innerHTML =
      '<div class="text-console__log" data-testid="text-console-log" aria-live="polite"></div>' +
      '<div class="text-console__line">' +
      '<span class="text-console__prompt" data-testid="text-console-prompt"></span>' +
      '<input class="text-console__input" data-testid="text-console-input" ' +
      'type="text" autocomplete="off" spellcheck="false"' +
      ' aria-label="輸入命令" disabled>' +
      "</div>" +
      '<div class="text-console__status" data-testid="text-console-status" ' +
      'role="status"></div>';
    var log = wrapper.querySelector("[data-testid='text-console-log']");
    var promptEl = wrapper.querySelector("[data-testid='text-console-prompt']");
    var input = wrapper.querySelector("[data-testid='text-console-input']");
    var statusEl = wrapper.querySelector("[data-testid='text-console-status']");
    root.appendChild(wrapper);

    function paint() {
      input.disabled = model.status() !== "ready";
      render(model, log, promptEl, statusEl, wrapper);
    }

    function send() {
      var text = input.value.replace(/^\s+|\s+$/g, "");
      input.value = "";
      if (!text) {
        return;
      }
      model.appendIn(text);
      paint();
      transport.msg("text", [text], {});
    }

    input.addEventListener("keydown", function (event) {
      if (event.key === "Enter") {
        event.preventDefault();
        send();
      }
    });

    if (transport && transport.emitter && typeof transport.emitter.on === "function") {
      transport.emitter.on("text", function (args) {
        model.appendOut(args && args[0]);
        paint();
      });
      transport.emitter.on("prompt", function (args) {
        model.setPrompt(args && args[0]);
        paint();
      });
      transport.emitter.on("connection_open", function () {
        model.setConnected(true);
        paint();
      });
      transport.emitter.on("connection_close", function () {
        model.setConnected(false);
        paint();
      });
      transport.emitter.on("logged_in", function () {
        model.reset();
        model.setLoggedIn(true);
        paint();
      });
    }
    paint();
    // C3: expose the repaint handle so the live transport coordinator can
    // repaint the console DOM after driving the model (the evennia emitter
    // keeps one listener per name, so the coordinator owns the shared events).
    return { model: model, wrapper: wrapper, send: send, paint: paint };
  }

  return {
    MAX_LINES: MAX_LINES,
    createModel: createModel,
    attach: attach,
  };
});
