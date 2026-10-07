import { describe, expect, it, vi } from "vitest";
import { createGmApi, gmReturnPath, GmApiError, readCookie } from "../lib/api.js";

function reply(status, body, { raw = false } = {}) {
  return {
    status,
    ok: status >= 200 && status < 300,
    text: async () => (raw ? body : JSON.stringify(body)),
  };
}

function client(response, overrides = {}) {
  const fetchImpl = vi.fn(async () => (response instanceof Error ? Promise.reject(response) : response));
  const navigate = vi.fn();
  const onForbidden = vi.fn();
  const api = createGmApi({
    fetchImpl,
    navigate,
    onForbidden,
    loginUrl: "/auth/login/",
    location: { pathname: "/gm/", search: "?tab=1", hash: "" },
    cookies: () => "sessionid=abc; csrftoken=tok%2Ben",
    ...overrides,
  });
  return { api, fetchImpl, navigate, onForbidden };
}

async function failure(promise) {
  try {
    await promise;
  } catch (error) {
    return error;
  }
  throw new Error("expected the call to fail");
}

describe("GM fetch boundary", () => {
  it("unwraps the success envelope and sends same-origin credentials", async () => {
    const { api, fetchImpl } = client(reply(200, { ok: true, data: { django: "ok" } }));
    await expect(api.get("/dashboard")).resolves.toEqual({ django: "ok" });
    const [url, init] = fetchImpl.mock.calls[0];
    expect(url).toBe("/gm/api/dashboard");
    expect(init.method).toBe("GET");
    expect(init.credentials).toBe("same-origin");
    expect(init.headers["X-CSRFToken"]).toBeUndefined();
  });

  it("attaches the csrftoken cookie as X-CSRFToken on POST writes", async () => {
    const { api, fetchImpl } = client(reply(200, { ok: true, data: { accepted: true } }));
    await expect(api.post("/_test/write", { a: 1 })).resolves.toEqual({ accepted: true });
    const [, init] = fetchImpl.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("same-origin");
    expect(init.headers["X-CSRFToken"]).toBe("tok+en");
    expect(init.headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(init.body)).toEqual({ a: 1 });
  });

  it("sends a 401 to the configured login page with an encoded GM return path", async () => {
    const { api, navigate, onForbidden } = client(
      reply(401, { ok: false, error: { code: "unauthenticated", message: "請先登入。" } }),
      { loginUrl: "/accounts/sign-in/" },
    );
    const error = await failure(api.get("/session"));
    expect(error).toBeInstanceOf(GmApiError);
    expect(error.code).toBe("unauthenticated");
    expect(navigate).toHaveBeenCalledWith("/accounts/sign-in/?next=%2Fgm%2F%3Ftab%3D1");
    expect(onForbidden).not.toHaveBeenCalled();
  });

  it("hands off to login once even when parallel calls all see 401", async () => {
    const { api, navigate } = client(
      reply(401, { ok: false, error: { code: "unauthenticated", message: "請先登入。" } }),
    );
    const results = await Promise.allSettled([api.get("/session"), api.get("/health")]);
    expect(results.map((result) => result.reason.code)).toEqual(["unauthenticated", "unauthenticated"]);
    expect(navigate).toHaveBeenCalledTimes(1);
  });

  it("routes a 403 forbidden to the permission-denied view, not login", async () => {
    const { api, navigate, onForbidden } = client(
      reply(403, { ok: false, error: { code: "forbidden", message: "權限不足" } }),
    );
    const error = await failure(api.get("/session"));
    expect(error.code).toBe("forbidden");
    expect(error.status).toBe(403);
    expect(onForbidden).toHaveBeenCalledTimes(1);
    expect(navigate).not.toHaveBeenCalled();
  });

  it("surfaces a 403 csrf_failed by its code without the permission view", async () => {
    const { api, onForbidden } = client(
      reply(403, { ok: false, error: { code: "csrf_failed", message: "安全驗證失敗" } }),
    );
    const error = await failure(api.post("/_test/write"));
    expect(error.code).toBe("csrf_failed");
    expect(onForbidden).not.toHaveBeenCalled();
  });

  it("surfaces a 404 envelope by its server code", async () => {
    const { api } = client(reply(404, { ok: false, error: { code: "not_found", message: "找不到" } }));
    const error = await failure(api.get("/missing"));
    expect(error.code).toBe("not_found");
    expect(error.status).toBe(404);
    expect(error.message).toBe("找不到");
  });

  it("reports a network failure as an explicit client error", async () => {
    const { api } = client(new TypeError("Failed to fetch"));
    const error = await failure(api.get("/health"));
    expect(error.code).toBe("network_error");
    expect(error.status).toBe(0);
  });

  it.each([
    ["non-JSON body", reply(200, "<html>proxy</html>", { raw: true })],
    ["empty body", reply(200, "", { raw: true })],
    ["missing data", reply(200, { ok: true })],
    ["non-boolean ok", reply(200, { ok: "yes", data: {} })],
    ["error without code", reply(500, { ok: false, error: { message: "x" } })],
    ["ok envelope on an error status", reply(503, { ok: true, data: { database: "readable" } })],
    ["error envelope on a 2xx status", reply(200, { ok: false, error: { code: "x", message: "y" } })],
    ["array body", reply(200, [1, 2])],
  ])("rejects a malformed response (%s) instead of treating it as data", async (_label, response) => {
    const { api } = client(response);
    const error = await failure(api.get("/health"));
    expect(error.code).toBe("malformed_response");
  });
});

describe("GM fetch helpers", () => {
  it("reads a named cookie", () => {
    expect(readCookie("csrftoken", "a=1; csrftoken=xyz")).toBe("xyz");
    expect(readCookie("csrftoken", "a=1")).toBe("");
  });

  it("only returns same-origin GM paths to the login page", () => {
    expect(gmReturnPath({ pathname: "/gm/deep/link", search: "?q=1", hash: "#h" })).toBe("/gm/deep/link?q=1#h");
    expect(gmReturnPath({ pathname: "/elsewhere", search: "", hash: "" })).toBe("/gm/");
    expect(gmReturnPath({ pathname: "//evil.example/gm/", search: "", hash: "" })).toBe("/gm/");
    expect(gmReturnPath(undefined)).toBe("/gm/");
  });
});

describe("GM binary downloads (S5 save archives)", () => {
  function fileReply(status, body, headers) {
    return {
      status,
      ok: status >= 200 && status < 300,
      headers: new Headers(headers),
      blob: async () => ({ body }),
      text: async () => body,
    };
  }

  it("resolves a binary success to its blob and attachment filename", async () => {
    const { api, fetchImpl } = client(
      fileReply(200, "tar-bytes", {
        "Content-Type": "application/x-tar",
        "Content-Disposition": 'attachment; filename="elosern-save-x.tar"',
      }),
    );
    const result = await api.download("/saves/x/download");
    expect(result.filename).toBe("elosern-save-x.tar");
    expect(result.blob).toEqual({ body: "tar-bytes" });
    const [url, init] = fetchImpl.mock.calls[0];
    expect(url).toBe("/gm/api/saves/x/download");
    expect(init.credentials).toBe("same-origin");
  });

  it("surfaces JSON failures by code and keeps auth handling", async () => {
    const notFound = client(
      fileReply(404, JSON.stringify({ ok: false, error: { code: "save_not_found", message: "找不到" } }), {
        "Content-Type": "application/json",
      }),
    );
    const error = await failure(notFound.api.download("/saves/x/download"));
    expect(error.code).toBe("save_not_found");
    expect(notFound.onForbidden).not.toHaveBeenCalled();

    const anonymous = client(fileReply(401, "{}", { "Content-Type": "application/json" }));
    expect((await failure(anonymous.api.download("/saves/x/download"))).code).toBe("unauthenticated");
    expect(anonymous.navigate).toHaveBeenCalledTimes(1);

    const denied = client(
      fileReply(403, JSON.stringify({ ok: false, error: { code: "forbidden", message: "權限不足" } }), {
        "Content-Type": "application/json",
      }),
    );
    expect((await failure(denied.api.download("/saves/x/download"))).code).toBe("forbidden");
    expect(denied.onForbidden).toHaveBeenCalledTimes(1);
  });

  it("never treats a JSON success body as a file", async () => {
    const { api } = client(fileReply(200, JSON.stringify({ ok: true, data: {} }), { "Content-Type": "application/json" }));
    expect((await failure(api.download("/saves/x/download"))).code).toBe("malformed_response");
  });

  it("keeps a domain refusal away from the permission-denied view", async () => {
    const { api, onForbidden } = client(
      reply(409, { ok: false, error: { code: "save_delete_forbidden", message: "自動存檔不能刪除" } }),
    );
    expect((await failure(api.post("/saves/x/delete"))).code).toBe("save_delete_forbidden");
    expect(onForbidden).not.toHaveBeenCalled();
  });
});
