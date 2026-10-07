import { describe, expect, it } from "vitest";
import { flushPromises } from "@vue/test-utils";
import GmEntityLink from "../components/GmEntityLink.vue";
import { linkTarget, targetHref } from "../lib/runtime.js";
import { mountWith, stubRouter } from "./runtime-helpers.js";

describe("GmEntityLink", () => {
  it("renders every curated kind as a link to its entity page", () => {
    const link = { kind: "npcs", id: "12", label: "合成守衛" };
    const wrapper = mountWith(GmEntityLink, { props: { link } });
    const anchor = wrapper.get("a");
    expect(anchor.attributes("href")).toBe("/gm/runtime/npcs/12");
    expect(anchor.attributes("data-kind")).toBe("npcs");
    expect(anchor.text()).toBe("合成守衛");
    expect(anchor.get("span").classes()).toContain("gm-mono");
    expect(anchor.attributes("title")).toBe("12");
  });

  it("carries the owner identity a record-backed id needs", () => {
    const link = { kind: "memories", id: "31", owner: "12", label: "記憶" };
    const wrapper = mountWith(GmEntityLink, { props: { link } });
    expect(wrapper.get("a").attributes("href")).toBe("/gm/runtime/memories/31?owner=%2312");
    expect(linkTarget(link)).toEqual({
      name: "runtime-entity",
      params: { kind: "memories", id: "31" },
      query: { owner: "#12" },
    });
  });

  it("routes an uncurated object to raw inspection and a media id to its file", () => {
    const object = mountWith(GmEntityLink, {
      props: { link: { kind: "object", id: "#7", label: "t_plain" } },
    });
    expect(object.get("a").attributes("href")).toBe("/gm/runtime/object/7/raw");
    const media = mountWith(GmEntityLink, {
      props: { link: { kind: "media", id: "/art/t_image.webp", label: "縮圖" } },
    });
    const anchor = media.get("a");
    expect(anchor.attributes("href")).toBe("/art/t_image.webp");
    expect(anchor.attributes("target")).toBe("_blank");
    expect(anchor.attributes("rel")).toBe("noopener");
  });

  it("turns a call identifier into a button that asks the host to open the drawer", async () => {
    const wrapper = mountWith(GmEntityLink, {
      props: { link: { kind: "call", id: "ab".repeat(16) } },
    });
    expect(wrapper.find("a").exists()).toBe(false);
    const button = wrapper.get("button");
    expect(button.classes()).toContain("gm-entity-link--call");
    await button.trigger("click");
    expect(wrapper.emitted("open-call")[0]).toEqual(["ab".repeat(16)]);
    expect(targetHref(linkTarget({ kind: "call", id: "x" }))).toBeNull();
  });

  it("degrades an unaddressable link to verbatim text, never a fabricated target", () => {
    const unknown = mountWith(GmEntityLink, { props: { link: { kind: "nope", id: "1", label: "x" } } });
    expect(unknown.find("a").exists()).toBe(false);
    expect(unknown.get("span").classes()).toContain("gm-entity-link--plain");
    const empty = mountWith(GmEntityLink, { props: { link: null, label: "—" } });
    expect(empty.text()).toBe("—");
  });

  it("opens the owner's own tab for a collection descriptor", () => {
    // The curated summaries link a collection through the owning entity: the
    // sentinel id is not a record id, so it must never become one.
    expect(linkTarget({ kind: "memories", id: "owner:12", label: "記憶" })).toEqual({
      name: "runtime-entity",
      params: { kind: "npcs", id: "12" },
      query: { tab: "memory" },
    });
    expect(targetHref(linkTarget({ kind: "snapshots", id: "owner:#12" }))).toBe(
      "/gm/runtime/npcs/12?tab=memory",
    );
    expect(linkTarget({ kind: "dialogue", id: "12" })).toEqual({
      name: "runtime-entity",
      params: { kind: "npcs", id: "12" },
      query: { tab: "dialogue" },
    });
    expect(targetHref(linkTarget({ kind: "quests", id: "owner:12" }))).toBe(
      "/gm/runtime/quests?owner=%2312",
    );
    expect(linkTarget({ kind: "memories", id: "owner:" })).toBeNull();
  });

  it("pushes the SPA route on a plain click and leaves modified clicks alone", async () => {
    const router = stubRouter();
    await router.push("/runtime/accounts");
    await router.isReady();
    const wrapper = mountWith(GmEntityLink, {
      props: { link: { kind: "npcs", id: "12", label: "合成守衛" } },
      router,
    });
    const anchor = wrapper.get("a");
    await anchor.trigger("click", { button: 0, ctrlKey: true });
    expect(router.currentRoute.value.name).toBe("runtime-list");
    await anchor.trigger("click", { button: 0 });
    await flushPromises();
    expect(router.currentRoute.value.name).toBe("runtime-entity");
    expect(router.currentRoute.value.params).toMatchObject({ kind: "npcs", id: "12" });
  });
});
