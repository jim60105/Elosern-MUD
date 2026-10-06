import { h } from "vue";
import GmPageHeader from "../components/GmPageHeader.vue";
import { SESSION } from "./fixtures.js";

// GmPageHeader: title in the display face, the operator account verbatim in
// mono with its level, and a neutral 登出.
export default {
  title: "GM/GmPageHeader",
  component: GmPageHeader,
  args: {
    title: "總覽",
    eyebrow: "ELOSERN · 營運者介面",
    account: SESSION.account_name,
    permissionLevel: SESSION.permission_level,
    logoutUrl: "/auth/logout/",
  },
  render: (args) => ({ setup: () => () => h(GmPageHeader, args) }),
};

export const Operator = {};
export const Superuser = { args: { account: "root_admin", permissionLevel: "superuser" } };
export const Loading = { args: { account: "", permissionLevel: "" } };
