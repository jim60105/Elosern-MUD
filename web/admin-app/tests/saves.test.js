// The 存檔 page (gm-portal-s5-saves): metadata and latest restore result,
// labelled creation, restore/delete confirmation and cancellation, danger
// styling and consequence copy, code-based failures that never become a
// permission denial, and downloads through the binary API boundary.
import { afterEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import GmSaveSlot from "../components/GmSaveSlot.vue";
import { GmApiError } from "../lib/api.js";
import { formatBytes, formatGameDate } from "../lib/saves.js";
import SavesView from "../views/SavesView.vue";
import { FAILED_RESULT, SAVES, SAVES_LISTING } from "../stories/saves-fixtures.js";

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function fakeApi({ listing = SAVES_LISTING, post, download } = {}) {
  return {
    get: vi.fn(async () => clone(listing)),
    post: vi.fn(post ?? (async () => ({}))),
    download: vi.fn(download ?? (async () => ({ blob: {}, filename: "x.tar" }))),
  };
}

async function mountPage(api) {
  const wrapper = mount(SavesView, {
    props: { timeZone: "Asia/Taipei" },
    global: { provide: { gmApi: api } },
    attachTo: document.body,
  });
  await flushPromises();
  return wrapper;
}

function row(wrapper, id) {
  return wrapper.get(`[data-save="${id}"]`);
}

afterEach(() => {
  document.body.innerHTML = "";
  document.documentElement.classList.remove("gm-scroll-locked");
});

describe("save formatting", () => {
  it("formats sizes and in-game dates", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(88_473_600)).toBe("84.4 MB");
    expect(formatGameDate({ tick: 1, year: 2, season: "冬", day: 9, hour: 7, minute: 5 })).toBe("第 2 年 冬 第 9 日 07:05");
    expect(formatGameDate(null)).toBeNull();
  });
});

describe("SavesView", () => {
  it("renders every save's metadata and the latest restore result", async () => {
    const api = fakeApi();
    const wrapper = await mountPage(api);
    expect(api.get).toHaveBeenCalledWith("/saves/");
    const first = row(wrapper, SAVES[0].id);
    expect(first.text()).toContain("決戰之前：港口倉庫的密會");
    expect(first.text()).toContain(SAVES[0].id);
    expect(first.text()).toContain("第 1 年 夏 第 4 日 21:40");
    expect(first.text()).toContain("tick 1987200");
    expect(first.text()).toContain("艾琳");
    expect(first.text()).toContain("harbor_warehouse");
    expect(first.text()).toContain("84.4 MB");
    expect(first.text()).toMatch(/2026\/10\/07\s14:15:30/);
    expect(first.text()).toContain("手動");
    expect(row(wrapper, SAVES[1].id).text()).toContain("讀檔前自動");
    expect(row(wrapper, SAVES[1].id).text()).toContain("另 1 位");
    expect(row(wrapper, SAVES[2].id).text()).toContain("未命名存檔");
    const banner = wrapper.get(".gm-saves__result");
    expect(banner.classes()).toContain("is-restored");
    expect(banner.text()).toContain("上次讀檔成功");
    expect(banner.text()).toContain("港口初到");
  });

  it("shows a failed restore result with its reason", async () => {
    const wrapper = await mountPage(fakeApi({ listing: { ...SAVES_LISTING, restore_result: FAILED_RESULT } }));
    const banner = wrapper.get(".gm-saves__result");
    expect(banner.classes()).toContain("is-failed");
    expect(banner.text()).toContain("size mismatch: forest.webp");
    expect(banner.text()).toContain("目前世界維持原狀");
  });

  it("offers deletion only for manual saves", async () => {
    const wrapper = await mountPage(fakeApi());
    for (const save of SAVES) {
      const slot = row(wrapper, save.id);
      expect(slot.find("[data-action='restore']").exists()).toBe(true);
      expect(slot.find("[data-action='download']").exists()).toBe(true);
      expect(slot.find("[data-action='delete']").exists()).toBe(save.kind === "manual");
    }
  });

  it("filters by kind through the tablist", async () => {
    const wrapper = await mountPage(fakeApi());
    await wrapper.get("[data-filter='auto_restore']").trigger("click");
    expect(wrapper.findAll("[data-save]").map((node) => node.attributes("data-save"))).toEqual([SAVES[1].id]);
    await wrapper.get("[data-filter='auto_restore']").trigger("keydown", { key: "ArrowRight" });
    expect(wrapper.get("[data-filter='auto_intervention']").attributes("aria-selected")).toBe("true");
  });

  it("creates a labelled manual save and reloads the list", async () => {
    const created = { ...SAVES[0], id: "20261007T090000-abcdef", label: "新的存檔" };
    const api = fakeApi({ post: async () => created });
    const wrapper = await mountPage(api);
    await wrapper.get("#gm-save-label").setValue("新的存檔");
    await wrapper.get("form").trigger("submit");
    await flushPromises();
    expect(api.post).toHaveBeenCalledWith("/saves/", { label: "新的存檔" });
    expect(api.get).toHaveBeenCalledTimes(2);
    expect(wrapper.get("#gm-save-label").element.value).toBe("");
    expect(wrapper.text()).toContain("已建立存檔「新的存檔」");
    expect(wrapper.get("#gm-save-label").attributes("maxlength")).toBe("80");
  });

  it("surfaces a create failure by its code", async () => {
    const api = fakeApi({
      post: async () => {
        throw new GmApiError("save_in_progress", { status: 409, message: "另一項存檔作業正在進行。" });
      },
    });
    const wrapper = await mountPage(api);
    await wrapper.get("form").trigger("submit");
    await flushPromises();
    const error = wrapper.get(".gm-saves__create .gm-error");
    expect(error.text()).toContain("save_in_progress");
    expect(error.text()).toContain("另一項存檔作業正在進行");
  });

  it("cancelling the restore confirmation sends no POST", async () => {
    const api = fakeApi();
    const wrapper = await mountPage(api);
    await row(wrapper, SAVES[0].id).get("[data-action='restore']").trigger("click");
    await flushPromises();
    const dialog = wrapper.findAll(".gm-confirm").find((node) => node.text().includes("讀取這份存檔"));
    expect(dialog.classes()).toContain("gm-confirm--danger");
    expect(dialog.get("[data-confirm]").classes()).toContain("ui-btn--danger");
    const copy = dialog.text();
    expect(copy).toContain("讀檔前自動存檔");
    expect(copy).toContain("伺服器會關閉");
    expect(copy).toContain("手動重新啟動伺服器");
    await dialog.findAll("button").find((node) => node.text() === "取消").trigger("click");
    await flushPromises();
    expect(api.post).not.toHaveBeenCalled();
    expect(wrapper.find(".gm-confirm .gm-confirm__frame").exists()).toBe(false);
  });

  it("an accepted restore shows the shutdown state with the pre-restore save", async () => {
    const api = fakeApi({
      post: async () => ({ save: SAVES[0].id, pre_restore_save: "20261007T100000-123456", shutdown: true }),
    });
    const wrapper = await mountPage(api);
    await row(wrapper, SAVES[0].id).get("[data-action='restore']").trigger("click");
    await flushPromises();
    await wrapper.get(".gm-confirm [data-confirm]").trigger("click");
    await flushPromises();
    expect(api.post).toHaveBeenCalledWith(`/saves/${SAVES[0].id}/restore`, {});
    const shutdown = wrapper.get(".gm-saves__shutdown");
    expect(shutdown.text()).toContain("伺服器正在關閉");
    expect(shutdown.text()).toContain("20261007T100000-123456");
    expect(wrapper.find("[data-save]").exists()).toBe(false);
  });

  it("keeps a refused restore in the dialog by its code", async () => {
    const api = fakeApi({
      post: async () => {
        throw new GmApiError("save_incompatible", { status: 409, message: "無法讀取。" });
      },
    });
    const wrapper = await mountPage(api);
    await row(wrapper, SAVES[0].id).get("[data-action='restore']").trigger("click");
    await flushPromises();
    await wrapper.get(".gm-confirm [data-confirm]").trigger("click");
    await flushPromises();
    const dialog = wrapper.get(".gm-confirm .gm-confirm__frame");
    expect(dialog.text()).toContain("save_incompatible");
    expect(wrapper.find(".gm-saves__shutdown").exists()).toBe(false);
  });

  it("cancelling deletion sends no POST; confirming deletes and reloads", async () => {
    const api = fakeApi();
    const wrapper = await mountPage(api);
    await row(wrapper, SAVES[0].id).get("[data-action='delete']").trigger("click");
    await flushPromises();
    let dialog = wrapper.findAll(".gm-confirm").find((node) => node.text().includes("刪除存檔"));
    expect(dialog.text()).toContain("此動作無法復原");
    await dialog.findAll("button").find((node) => node.text() === "取消").trigger("click");
    await flushPromises();
    expect(api.post).not.toHaveBeenCalled();

    await row(wrapper, SAVES[0].id).get("[data-action='delete']").trigger("click");
    await flushPromises();
    dialog = wrapper.findAll(".gm-confirm").find((node) => node.text().includes("刪除存檔"));
    await dialog.get("[data-confirm]").trigger("click");
    await flushPromises();
    expect(api.post).toHaveBeenCalledWith(`/saves/${SAVES[0].id}/delete`, {});
    expect(api.get).toHaveBeenCalledTimes(2);
  });

  it("presents save_delete_forbidden as an operation result, not a permission page", async () => {
    const api = fakeApi({
      post: async () => {
        throw new GmApiError("save_delete_forbidden", { status: 409, message: "自動存檔不能手動刪除。" });
      },
    });
    const wrapper = await mountPage(api);
    await row(wrapper, SAVES[0].id).get("[data-action='delete']").trigger("click");
    await flushPromises();
    await wrapper.get(".gm-confirm [data-confirm]").trigger("click");
    await flushPromises();
    const dialog = wrapper.get(".gm-confirm .gm-confirm__frame");
    expect(dialog.text()).toContain("save_delete_forbidden");
    expect(dialog.text()).toContain("自動存檔不能手動刪除");
    expect(wrapper.text()).not.toContain("權限不足");
  });

  it("downloads through the binary boundary and reports failures on the row", async () => {
    const createObjectURL = vi.fn(() => "blob:test");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", Object.assign(globalThis.URL, { createObjectURL, revokeObjectURL }));
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    const api = fakeApi();
    const wrapper = await mountPage(api);
    await row(wrapper, SAVES[0].id).get("[data-action='download']").trigger("click");
    await flushPromises();
    expect(api.download).toHaveBeenCalledWith(`/saves/${SAVES[0].id}/download`);
    expect(click).toHaveBeenCalledTimes(1);
    expect(row(wrapper, SAVES[0].id).get("[data-action='download']").text()).toBe("已下載 ✓");

    api.download.mockRejectedValueOnce(new GmApiError("save_not_found", { status: 404, message: "找不到。" }));
    await row(wrapper, SAVES[1].id).get("[data-action='download']").trigger("click");
    await flushPromises();
    expect(row(wrapper, SAVES[1].id).text()).toContain("save_not_found");
    click.mockRestore();
    vi.unstubAllGlobals();
  });

  it("a pending restore locks every mutation and marks its slot", async () => {
    const listing = {
      ...SAVES_LISTING,
      pending: SAVES[0].id,
      saves: SAVES.map((save, index) => ({ ...save, pending: index === 0 })),
    };
    const api = fakeApi({ listing });
    const wrapper = await mountPage(api);
    expect(wrapper.get(".gm-saves__pending").text()).toContain(SAVES[0].id);
    expect(row(wrapper, SAVES[0].id).text()).toContain("待套用");
    await row(wrapper, SAVES[3].id).get("[data-action='restore']").trigger("click");
    await wrapper.get("form").trigger("submit");
    await flushPromises();
    expect(api.post).not.toHaveBeenCalled();
    expect(wrapper.find(".gm-confirm .gm-confirm__frame").exists()).toBe(false);
  });

  it("shows the empty state", async () => {
    const wrapper = await mountPage(fakeApi({ listing: { saves: [], restore_result: null, pending: null, autosave_keep: 10 } }));
    expect(wrapper.text()).toContain("尚無存檔");
  });
});

describe("GmSaveSlot", () => {
  it("emits its actions and hides deletion for automatic saves", async () => {
    const manual = mount(GmSaveSlot, { props: { save: SAVES[0] } });
    await manual.get("[data-action='restore']").trigger("click");
    await manual.get("[data-action='delete']").trigger("click");
    expect(manual.emitted("restore")[0][0].id).toBe(SAVES[0].id);
    expect(manual.emitted("delete")[0][0].id).toBe(SAVES[0].id);
    const automatic = mount(GmSaveSlot, { props: { save: SAVES[1] } });
    expect(automatic.find("[data-action='delete']").exists()).toBe(false);
    expect(automatic.text()).toContain("保留規則");
    const locked = mount(GmSaveSlot, { props: { save: SAVES[0], locked: true } });
    await locked.get("[data-action='restore']").trigger("click");
    expect(locked.emitted("restore")).toBeUndefined();
  });
});
