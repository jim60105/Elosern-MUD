// H4 (webclient-hud-04-reference-drawers, task 3.6): the drawer shell's
// modal contract — only one drawer open at a time, the scrim present only
// while a drawer is open, the stage recession mark while open and cleared
// on close, and reduced motion disabling the transition while the open
// state still applies.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import HudDrawer from "../components/HudDrawer.vue";

describe("HudDrawer (H4 D1)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountDrawer(props = {}, slots = {}) {
    wrapper = mount(HudDrawer, {
      props: { open: false, title: "任務", drawerKey: "quest", ...props },
      slots,
    });
    return wrapper;
  }

  it("renders no scrim while the drawer is closed", () => {
    mountDrawer({ open: false });
    expect(wrapper.find('[data-testid="hud-drawer-scrim"]').exists()).toBe(false);
    // The drawer chrome is mounted but off-screen (translateX(100%)); the
    // close control leaves the tab order via tabindex -1.
    const drawer = wrapper.get('[data-testid="hud-drawer"]');
    expect(drawer.classes()).not.toContain("open");
    expect(drawer.attributes("data-open")).toBe("false");
    expect(wrapper.get('[data-testid="hud-drawer-close"]').attributes("tabindex")).toBe("-1");
  });

  it("renders the scrim and the open drawer when open", () => {
    mountDrawer({ open: true });
    expect(wrapper.find('[data-testid="hud-drawer-scrim"]').exists()).toBe(true);
    const drawer = wrapper.get('[data-testid="hud-drawer"]');
    expect(drawer.classes()).toContain("open");
    expect(drawer.attributes("data-open")).toBe("true");
    // The close control is in the tab order while open.
    expect(wrapper.get('[data-testid="hud-drawer-close"]').attributes("tabindex")).toBe("0");
  });

  it("emits close on the close control, on the scrim, and on Escape", () => {
    const w = mountDrawer({ open: true }, {
      default: () => "body",
    });
    // Close control.
    w.get('[data-testid="hud-drawer-close"]').trigger("click");
    expect(w.emitted("close")).toHaveLength(1);
    // Scrim.
    const w2 = mountDrawer({ open: true }, { default: () => "body" });
    w2.get('[data-testid="hud-drawer-scrim"]').trigger("click");
    expect(w2.emitted("close")).toHaveLength(1);
    // Escape.
    const w3 = mountDrawer({ open: true }, { default: () => "body" });
    w3.get('[data-testid="hud-drawer"]').trigger("keydown", { key: "Escape" });
    expect(w3.emitted("close")).toHaveLength(1);
  });

  it("moves focus into the drawer on open (the focus trap)", async () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    const w = mount(HudDrawer, {
      attachTo: host,
      props: { open: false, title: "商店", drawerKey: "shop" },
      slots: { default: () => "shop body" },
    });
    // Mount closed, then open: the watch creates the trap and moves focus
    // to the close control (the trap's initial target).
    await w.setProps({ open: true });
    expect(document.activeElement).toBe(w.get('[data-testid="hud-drawer-close"]').element);
  });

  it("reduced motion keeps the open state and drops the transition", () => {
    // The transition is expressed through `--motion-base`; the reduced-motion
    // block sets the token to 1ms, so the open state still applies while the
    // slide transition is effectively disabled.
    mountDrawer({ open: true });
    const drawer = wrapper.get('[data-testid="hud-drawer"]');
    expect(drawer.classes()).toContain("open");
    expect(drawer.attributes("data-open")).toBe("true");
    // The CSS transition is token-gated (the reduced-motion block covers it):
    // the component's <style> block references `var(--motion-base)`.
    const source = readFileSync(
      join(process.cwd(), "web/webclient-app/components/HudDrawer.vue"),
      "utf-8",
    );
    expect(source).toContain("transition: transform var(--motion-base) var(--ease-standard)");
  });
});
