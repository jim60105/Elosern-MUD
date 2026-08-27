import { h } from "vue";
import HudDrawer from "../../components/HudDrawer.vue";

// HudDrawer (H4, webclient-hud-04-reference-drawers, design D1): the
// right-anchored drawer chrome shared by the six reference drawers. The
// showcase stories are deterministic and offline: closed, open with a short
// body, open with an overflowing (scrollable) body, and open with a footer.

const LONG_BODY = Array.from({ length: 40 }, (_, i) => `line ${i + 1}`).join("\n");

function stage(children) {
  return h(
    "div",
    {
      style:
        "position: relative; width: 100%; height: 480px; background: var(--ink-950); overflow: hidden;",
    },
    children,
  );
}

function renderDrawer(args) {
  const bodyContent = args.overflow ? LONG_BODY : (args.bodyText || "Short body content.");
  const slots = {
    default: () => h("pre", { style: "margin: 0; font-family: var(--f-mono); font-size: 0.85em; color: var(--paper-100); white-space: pre-wrap;" }, [bodyContent]),
  };
  if (args.skillDrawer) {
    // The skill drawer's composed chrome: the `skills` head icon, the
    // skill-count subtitle, and the static cast-syntax footer hint — the
    // same combination AppClient wires for `hudDrawer === 'skill'`.
    slots.foot = () =>
      h("p", { class: "hud-drawer__cast-hint" }, "施放入口：cast <技法>[@威力]=<代號>");
  } else if (args.hasFooter) {
    slots.foot = () => h("span", { class: "hud-drawer__foot-text" }, "Drawer footer");
  }
  return {
    render: () =>
      stage([
        h(
          HudDrawer,
          {
            open: args.open,
            title: args.title,
            subtitle: args.subtitle || "",
            icon: args.skillDrawer ? "skills" : (args.icon || null),
            drawerKey: args.drawerKey || "",
            onClose: () => {},
          },
          slots,
        ),
      ]),
  };
}

export default {
  title: "Core/HudDrawer",
  component: HudDrawer,
  parameters: {
    docs: {
      description: {
        component:
          "The right-anchored drawer chrome (fixed to the stage's right edge, full height, " +
          "width min(560px,94vw), solid panel background, left border + left-cast shadow). " +
          "Slides in over a blurred scrim, traps focus, closes on Escape/close-control/scrim " +
          "with focus restored to the opener. At most one drawer is open at a time.",
      },
    },
  },
};

export const Closed = {
  render: renderDrawer,
  args: { open: false, title: "角色狀態", drawerKey: "status" },
};

export const OpenShortBody = {
  render: renderDrawer,
  args: { open: true, title: "角色狀態", subtitle: "status", drawerKey: "status" },
};

export const OpenOverflowBody = {
  render: renderDrawer,
  args: { open: true, title: "任務", drawerKey: "quest", overflow: true },
};

export const OpenWithFooter = {
  render: renderDrawer,
  args: { open: true, title: "商店", drawerKey: "shop", hasFooter: true },
};

// The skill drawer's composed chrome (the offline showcase): the `skills`
// head icon, the active/passive skill-count subtitle, and the static
// cast-syntax footer hint — the combination AppClient now wires.
export const SkillDrawer = {
  render: renderDrawer,
  args: {
    open: true,
    title: "技能書",
    subtitle: "主動 91 · 被動 23",
    drawerKey: "skill",
    skillDrawer: true,
  },
};
