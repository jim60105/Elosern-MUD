/*
 * Elosern narrative stream-end block controller.
 *
 * The narrative choice-point (webclient-options-choicepoints) is a stream-end
 * block owned by the `window.Elosern.narrativeInput` facade: the facade mounts,
 * replaces, and unmounts exactly one block element, and every narrative text
 * append flows through this controller so the stream's end geometry,
 * scroll-keep, and the polite unread marker stay one owner.
 *
 * The controller is DOM-abstracted (`container` with appendChild/removeChild/
 * insertBefore/lastChild plus the three callbacks) so Node tests exercise the
 * full geometry and unread semantics without a browser; goldenlayout.js binds
 * it to the real narrative container and its scroll/unread state.
 *
 * Geometry contract:
 * - `appendNode` inserts before the mounted block (the block always stays
 *   last) and performs exactly one scroll/unread decision: at the bottom it
 *   scrolls to keep the end visible, otherwise it invokes `onUnread` once.
 *   This is the ONLY path that ever increments the unread count and the ONLY
 *   relocation mechanism the choice-point needs — there is no separate
 *   move-to-end operation.
 * - `mount`/`replace` keep the end visible when the viewport is already at the
 *   bottom (the block is presentation chrome, never an unread event).
 * - `unmount` never scrolls and never touches the unread count.
 */
(function (root, factory) {
  "use strict";
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.Elosern = root.Elosern || {};
    root.Elosern.StreamEndBlock = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // `container` is the narrative element; `callbacks` provides
  // `atBottom() -> boolean`, `scrollToBottom()`, and `onUnread()`.
  function createStreamEndBlock(container, callbacks) {
    callbacks = callbacks || {};
    var block = null;

    function atBottom() {
      return typeof callbacks.atBottom === "function"
        ? !!callbacks.atBottom()
        : true;
    }

    function scrollToBottom() {
      if (typeof callbacks.scrollToBottom === "function") {
        callbacks.scrollToBottom();
      }
    }

    function onUnread() {
      if (typeof callbacks.onUnread === "function") {
        callbacks.onUnread();
      }
    }

    function mounted() {
      return (
        block !== null &&
        container !== null &&
        block.parentNode === container
      );
    }

    function isNode(value) {
      return value !== null && typeof value === "object";
    }

    // Append one narrative node before the mounted block (or at the end when
    // no block is mounted) with a single scroll/unread decision. `wasAtBottom`
    // optionally pins the decision to a value computed before any other
    // insertion of the same event (the input line's divider precedes the
    // line); when omitted, the decision is taken immediately before the
    // insertion. Returns the node on success, false when the container is
    // unusable.
    function appendNode(node, wasAtBottom) {
      if (!container || !isNode(node)) {
        return false;
      }
      if (typeof wasAtBottom !== "boolean") {
        wasAtBottom = atBottom();
      }
      if (mounted()) {
        container.insertBefore(node, block);
      } else {
        container.appendChild(node);
      }
      if (wasAtBottom) {
        scrollToBottom();
      } else {
        onUnread();
      }
      return node;
    }

    // Attach a block at the stream end. A second mount replaces the first in
    // place (idempotent: never two blocks). Keeps the end visible when the
    // viewport is already at the bottom; never increments the unread count.
    // The bottom decision is taken BEFORE the insertion: appending changes
    // scrollHeight, so a post-insert check would never see the bottom.
    function mount(element) {
      if (!container || !isNode(element)) {
        return false;
      }
      if (mounted()) {
        return replace(element);
      }
      var wasAtBottom = atBottom();
      block = element;
      container.appendChild(element);
      if (wasAtBottom) {
        scrollToBottom();
      }
      return element;
    }

    // Swap the mounted block node for a new one in place (position kept).
    // No-op when nothing is mounted. Keeps the end visible when the viewport
    // is already at the bottom (the decision is taken before the swap, since
    // the block's height change moves scrollHeight); never increments the
    // unread count.
    function replace(element) {
      if (!container || !mounted() || !isNode(element)) {
        return false;
      }
      var wasAtBottom = atBottom();
      container.insertBefore(element, block);
      container.removeChild(block);
      block = element;
      if (wasAtBottom) {
        scrollToBottom();
      }
      return element;
    }

    // Remove the mounted block and leave the container contiguous. No scroll
    // and no unread change; no-op when nothing is mounted.
    function unmount() {
      if (!mounted()) {
        return false;
      }
      container.removeChild(block);
      block = null;
      return true;
    }

    return {
      appendNode: appendNode,
      mount: mount,
      replace: replace,
      unmount: unmount,
      hasBlock: mounted,
      block: function () {
        return block;
      },
    };
  }

  return {
    createStreamEndBlock: createStreamEndBlock,
  };
});
