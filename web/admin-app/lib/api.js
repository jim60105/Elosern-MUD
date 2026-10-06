// The single GM fetch boundary (gm-portal-s1-foundation, design D6).
//
// Every GM API call goes through a client made here: same-origin requests
// with the Django session cookie, `X-CSRFToken` from the `csrftoken` cookie on
// POST writes, strict envelope validation, and code-based failures. 401 hands
// off to the configured login page with a GM return path; 403 `forbidden`
// selects the permission-denied view (a 403 `csrf_failed` is a transport
// failure, surfaced by its code). Network failures and malformed bodies are
// explicit client errors — never fabricated data. No retries, no cache.

export const API_BASE = "/gm/api";
export const GM_BASE = "/gm/";

export class GmApiError extends Error {
  constructor(code, { status = 0, message = "" } = {}) {
    super(message || code);
    this.name = "GmApiError";
    this.code = code;
    this.status = status;
  }
}

export const CLIENT_MESSAGES = Object.freeze({
  network_error: "無法連線到伺服器，請確認服務是否運作中。",
  malformed_response: "伺服器回應的格式不正確。",
});

export function readCookie(name, cookieString = "") {
  for (const part of cookieString.split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === name) return decodeURIComponent(rest.join("="));
  }
  return "";
}

// The return path handed to the login page. Only a same-origin path under the
// GM base qualifies; anything else (including protocol-relative `//host`)
// falls back to the GM home.
export function gmReturnPath(location) {
  const path = `${location?.pathname ?? ""}${location?.search ?? ""}${location?.hash ?? ""}`;
  if (path.startsWith(GM_BASE) && !path.startsWith("//")) return path;
  return GM_BASE;
}

export function loginRedirectUrl(loginUrl, location) {
  const separator = loginUrl.includes("?") ? "&" : "?";
  return `${loginUrl}${separator}next=${encodeURIComponent(gmReturnPath(location))}`;
}

function isEnvelope(body) {
  if (body === null || typeof body !== "object" || Array.isArray(body)) return false;
  if (body.ok === true) return Object.hasOwn(body, "data");
  if (body.ok === false) {
    const error = body.error;
    return (
      error !== null &&
      typeof error === "object" &&
      typeof error.code === "string" &&
      error.code.length > 0 &&
      typeof error.message === "string"
    );
  }
  return false;
}

export function createGmApi({
  fetchImpl = (...args) => globalThis.fetch(...args),
  loginUrl = "/auth/login/",
  location = globalThis.location,
  navigate = (url) => globalThis.location.assign(url),
  onForbidden = () => {},
  cookies = () => globalThis.document?.cookie ?? "",
} = {}) {
  // One login hand-off per page: parallel calls that all see 401 navigate once.
  let loginStarted = false;

  async function request(path, { method = "GET", body } = {}) {
    const headers = { Accept: "application/json" };
    const init = { method, credentials: "same-origin", headers };
    if (method !== "GET" && method !== "HEAD") {
      headers["X-CSRFToken"] = readCookie("csrftoken", cookies());
      headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(body ?? {});
    }

    let response;
    try {
      response = await fetchImpl(`${API_BASE}${path}`, init);
    } catch {
      throw new GmApiError("network_error", { message: CLIENT_MESSAGES.network_error });
    }

    if (response.status === 401) {
      if (!loginStarted) {
        loginStarted = true;
        navigate(loginRedirectUrl(loginUrl, location));
      }
      throw new GmApiError("unauthenticated", { status: 401, message: "請先登入。" });
    }

    let parsed;
    try {
      parsed = JSON.parse(await response.text());
    } catch {
      parsed = undefined;
    }
    // The envelope's `ok` must agree with the HTTP outcome.
    if (!isEnvelope(parsed) || parsed.ok !== response.ok) {
      throw new GmApiError("malformed_response", {
        status: response.status,
        message: CLIENT_MESSAGES.malformed_response,
      });
    }
    if (parsed.ok) return parsed.data;

    const { code, message } = parsed.error;
    if (response.status === 403 && code !== "csrf_failed") onForbidden();
    throw new GmApiError(code, { status: response.status, message });
  }

  return {
    get: (path) => request(path),
    post: (path, body) => request(path, { method: "POST", body }),
  };
}
