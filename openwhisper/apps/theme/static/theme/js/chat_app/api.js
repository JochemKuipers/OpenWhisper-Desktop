const STORAGE_ACCESS = "openwhisper_access";
const STORAGE_REFRESH = "openwhisper_refresh";

function getCsrf() {
  const inp = document.querySelector('[name="csrfmiddlewaretoken"]');
  return inp ? inp.value : "";
}

export function setTokens(access, refresh) {
  sessionStorage.setItem(STORAGE_ACCESS, access);
  sessionStorage.setItem(STORAGE_REFRESH, refresh);
}

export function clearTokens() {
  sessionStorage.removeItem(STORAGE_ACCESS);
  sessionStorage.removeItem(STORAGE_REFRESH);
}

export function getAccess() {
  return sessionStorage.getItem(STORAGE_ACCESS);
}

export async function apiFetch(path, options) {
  options = options || {};
  const headers = new Headers(options.headers || {});
  const token = getAccess();
  if (token) headers.set("Authorization", "Bearer " + token);
  const csrftoken = getCsrf();
  if (csrftoken) headers.set("X-CSRFToken", csrftoken);
  let body = options.body;
  if (
    body !== undefined &&
    body !== null &&
    typeof body === "object" &&
    !(body instanceof FormData)
  ) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(body);
  }
  const res = await fetch(path, {
    method: options.method || "GET",
    credentials: "same-origin",
    headers: headers,
    body: body,
  });
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch (_) {
    data = text;
  }
  if (res.status === 401) {
    clearTokens();
    window.location.href = "/login/";
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    let msg = res.status + " " + res.statusText;
    if (data && typeof data.detail === "string") msg = data.detail;
    else if (data && data.detail) msg = JSON.stringify(data.detail);
    else if (data && typeof data === "object") msg = JSON.stringify(data);
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data;
}

export async function bootstrapSessionJwt() {
  clearTokens();
  const data = await apiFetch("/api/auth/session-token/", {
    method: "POST",
    body: {},
  });
  setTokens(data.access, data.refresh);
}
