import { h } from "vue";
import GmPager from "../components/GmPager.vue";

// GmPager: forward-only cursor paging. The opaque cursor already carries the
// filter fingerprint, so the control can only ask for the next page or restart.
export default {
  title: "GM/GmPager",
  component: GmPager,
  args: { nextCursor: "t_cursor_1", limit: 50, shown: 50, page: 1, busy: false },
  render: (args) => ({
    setup: () => () =>
      h("div", { style: { padding: "32px", maxWidth: "1040px" } }, [h(GmPager, args)]),
  }),
};

export const MorePages = {};

export const EndOfList = { args: { nextCursor: null, shown: 12, page: 3 } };

export const Busy = { args: { busy: true, page: 2 } };

export const SecondPage = { args: { nextCursor: "t_cursor_2", shown: 50, page: 2 } };
