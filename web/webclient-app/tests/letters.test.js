import { afterEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { nextTick, reactive } from "vue";
import LettersPanel from "../components/LettersPanel.vue";
import { NAV_TOOLS } from "../components/nav-tools.js";
import CommandEcho from "../../static/webclient/js/elosern/command_echo.js";

const wrappers = [];
afterEach(() => wrappers.splice(0).forEach((wrapper) => wrapper.unmount()));
function fixture() {
  let seq = 0;
  const store = { view: reactive({ epoch: "a", generation: 1, connected: true, dispatch: { inFlight: null }, lastActionResult: null }),
    dispatchAction: vi.fn(() => `request-${++seq}`) };
  const wrapper = mount(LettersPanel, { props: { store } }); wrappers.push(wrapper);
  async function result(data, extra = {}) {
    store.view.lastActionResult = { requestId: store.dispatchAction.mock.results.at(-1).value, epoch: "a", outcome: "success", data, ...extra };
    await nextTick();
  }
  return { store, wrapper, result };
}
const page = (branch = false) => ({ branch, letters: [{ source_id: "synthetic-letter", sender_id: "12", read_tick: null, sent_tick: 17 }], next: null });

describe("personal letter folio", () => {
  it("only lists on mount, exposes collected choices, and explicitly reads portable prose", async () => {
    const f = fixture(); await f.result(page());
    expect(f.store.dispatchAction.mock.calls[0]).toEqual(["letters.list", { after: 0 }, null]);
    expect(f.wrapper.find("textarea").exists()).toBe(false);
    expect(f.wrapper.text()).toContain("未讀");
    expect(f.wrapper.text()).not.toContain("synthetic private prose");
    await f.wrapper.find(".letters-folio__letter").trigger("click");
    expect(f.store.dispatchAction.mock.calls.at(-1)).toEqual(["letters.read", { source_id: "synthetic-letter" }, null]);
    await f.result({ source_id: "synthetic-letter", sender_id: "12", body_parts: ["<script>synthetic private prose</script>"] });
    expect(f.wrapper.find(".letters-folio__reading").text()).toContain("<script>synthetic private prose</script>");
    expect(f.wrapper.find("script").exists()).toBe(false);
  });
  it("sends all 8000 Unicode code points with a stable identity on explicit retry", async () => {
    const f = fixture(); await f.result(page(true));
    await f.wrapper.find("input").setValue("#12");
    await f.wrapper.find("textarea").setValue("𐀀".repeat(8000));
    await f.wrapper.find("form").trigger("submit");
    const first = f.store.dispatchAction.mock.calls.at(-1);
    expect(first[0]).toBe("letters.send");
    expect(first[1].body_parts).toHaveLength(4);
    expect(first[1].body_parts.every((part) => Array.from(part).length === 2000)).toBe(true);
    await f.result(null, { outcome: "rejected", message: "Synthetic refusal" });
    expect(f.wrapper.find("textarea").element.value).toBe("𐀀".repeat(8000));
    await f.wrapper.find("form").trigger("submit");
    expect(f.store.dispatchAction.mock.calls.at(-1)[1].source_id).toBe(first[1].source_id);
    await f.result(page(true));
    expect(f.wrapper.find("textarea").element.value).toBe("");
  });
  it("rejects stale correlation and clears private data on transport/identity replacement", async () => {
    const f = fixture();
    await f.result(page(true), { requestId: "wrong" });
    expect(f.wrapper.find("input").exists()).toBe(false);
    await f.result(page(true));
    await f.wrapper.find("input").setValue("Synthetic recipient");
    await f.wrapper.find("textarea").setValue("Synthetic secret draft");
    f.store.view.epoch = "b"; await nextTick();
    expect(f.wrapper.find("textarea").exists()).toBe(false);
    expect(f.wrapper.text()).not.toContain("Synthetic secret draft");
    expect(f.store.dispatchAction).toHaveBeenCalledTimes(1);
  });
  it("provides a keyboard tool and actual text-equivalent echoes", () => {
    expect(NAV_TOOLS.find((tool) => tool.key === "letters").drawer).toBe("letters");
    expect(CommandEcho.commandLine("letters.collect", {})).toBe("信件 領取");
    expect(CommandEcho.commandLine("letters.list", { after: 41 })).toBe("信件 更多 41");
    expect(CommandEcho.commandLine("letters.read", { source_id: "synthetic-letter" })).toBe("信件 讀 synthetic-letter");
    expect(CommandEcho.commandLine("letters.send", { recipient: "#12", body_parts: ["a=", "b"] })).toBe("信件 寄 #12=a=b");
  });
});
