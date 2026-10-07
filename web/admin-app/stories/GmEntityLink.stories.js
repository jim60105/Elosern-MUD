import { h } from "vue";
import GmEntityLink from "../components/GmEntityLink.vue";

// GmEntityLink: the one renderer for the wire link descriptor. A curated kind
// becomes a router link, an object becomes raw inspection, a call id becomes a
// button for the S2 drawer, and media becomes an external link.
export default {
  title: "GM/GmEntityLink",
  component: GmEntityLink,
  args: { link: { kind: "npcs", id: "12", label: "合成守衛" } },
  render: (args) => ({
    setup: () => () =>
      h("p", { style: { padding: "32px" } }, [h(GmEntityLink, args)]),
  }),
};

export const CuratedEntity = {};

export const EveryTargetKind = {
  args: {},
  render: () => ({
    setup: () => () =>
      h("ul", { style: { padding: "32px", display: "grid", gap: "8px", listStyle: "none" } }, [
        h("li", [
          h(GmEntityLink, { link: { kind: "npcs", id: "12", label: "合成守衛" } }),
          h("span", { style: { color: "var(--paper-500)", marginLeft: "8px" } }, "NPC"),
        ]),
        h("li", [
          h(GmEntityLink, { link: { kind: "memories", id: "owner:12", owner: "12", label: "記憶清單" } }),
          h("span", { style: { color: "var(--paper-500)", marginLeft: "8px" } }, "帶擁有者的紀錄"),
        ]),
        h("li", [
          h(GmEntityLink, { link: { kind: "object", id: "#7", label: "t_plain_object" } }),
          h("span", { style: { color: "var(--paper-500)", marginLeft: "8px" } }, "未列入策展的物件"),
        ]),
        h("li", [
          h(GmEntityLink, { link: { kind: "call", id: "ab".repeat(16) } }),
          h("span", { style: { color: "var(--paper-500)", marginLeft: "8px" } }, "S2 呼叫明細"),
        ]),
        h("li", [
          h(GmEntityLink, { link: { kind: "media", id: "/art/showcase/portrait-01.webp", label: "縮圖" } }),
          h("span", { style: { color: "var(--paper-500)", marginLeft: "8px" } }, "媒體檔案"),
        ]),
      ]),
  }),
};

export const Unaddressable = {
  args: { link: { kind: "unknown", id: "1", label: "無法開啟的識別碼" } },
};

export const NoTarget = { args: { link: null, label: "—" } };

// Authored world-data targets (gm-portal-s4): ◇ opens the entry page; a
// declared reference whose target key is absent is broken text, not a link.
export const AuthoredEntry = {
  args: { link: { kind: "registry", registry: "t_hollows", id: "t_hollow_east" } },
};

export const MissingAuthoredTarget = {
  args: { link: { kind: "registry", registry: "t_hollows", id: "t_hollow_gone", missing: true } },
};
