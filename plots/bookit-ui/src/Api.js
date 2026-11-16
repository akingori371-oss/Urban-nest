const VITE_ENV = import.meta.env || {};
const DEFAULT_API_URL = VITE_ENV.PROD
  ? "https://urban-nest-backend-50z5.onrender.com"
  : "/api";
const API_URL = (VITE_ENV.VITE_API_URL || DEFAULT_API_URL).replace(/\/+$/, "");
const BASE = /\/api$/i.test(API_URL) ? API_URL : `${API_URL}/api`;
const DEFAULT_TIMEOUT_MS = 20000;

export class ApiError extends Error {
  constructor(message, { status = 0, url = "", data = null, cause } = {}) {
    super(message, { cause });
    this.name = "ApiError";
    this.status = status;
    this.url = url;
    this.data = data;
  }
}

export function saveSession(data) {
  localStorage.setItem("access", data.access);
  localStorage.setItem("refresh", data.refresh);
  localStorage.setItem("username", data.username);
}

export function clearSession() {
  localStorage.removeItem("access");
  localStorage.removeItem("refresh");
  localStorage.removeItem("username");
}

export function errorText(data) {
  if (data instanceof Error) return data.message;
  if (data == null) return "Something went wrong.";
  if (typeof data === "string") return data;
  if (data.detail) return String(data.detail);
  return Object.entries(data)
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.map(String).join(" ") : typeof value === "object" ? JSON.stringify(value) : value}`)
    .join(" | ") || "Something went wrong.";
}

function responseUrl(response, fallback) {
  return response.url || fallback;
}

async function parseResponse(response, requestUrl) {
  const url = responseUrl(response, requestUrl);
  if (response.status === 204 || response.status === 205) return null;

  const contentType = response.headers.get("content-type") || "";
  const raw = await response.text();
  if (!raw.trim()) return null;

  const looksJson = /(^|\/)json(?:\s*;|$)/i.test(contentType) || /\+json(?:\s*;|$)/i.test(contentType);
  const looksHtml = /text\/html/i.test(contentType) || /^\s*(?:<!doctype\s+html|<html\b)/i.test(raw);
  if (!looksJson) {
    const description = looksHtml ? "HTML" : (contentType || "non-JSON content");
    throw new ApiError(`The server returned an unexpected ${description} response (HTTP ${response.status}) for ${url}. Check that the backend API is running and the URL is correct.`, {
      status: response.status,
      url,
    });
  }

  try {
    return JSON.parse(raw);
  } catch (cause) {
    throw new ApiError(`The server returned invalid JSON (HTTP ${response.status}) for ${url}.`, {
      status: response.status,
      url,
      cause,
    });
  }
}

function responseView(response, data, requestUrl) {
  // Keep the familiar Response fields used by current pages, but parse its body
  // once here so no page can accidentally parse an HTML error document as JSON.
  return {
    ok: response.ok,
    status: response.status,
    statusText: response.statusText,
    headers: response.headers,
    url: responseUrl(response, requestUrl),
    data,
    json: async () => data,
  };
}

async function fetchJson(url, options, timeoutMs) {
  const controller = new AbortController();
  let timedOut = false;
  const externalSignal = options.signal;
  const abortFromCaller = () => controller.abort(externalSignal.reason);
  if (externalSignal?.aborted) abortFromCaller();
  else externalSignal?.addEventListener("abort", abortFromCaller, { once: true });
  const timeout = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);

  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    const data = await parseResponse(response, url);
    return responseView(response, data, url);
  } catch (cause) {
    if (cause instanceof ApiError) throw cause;
    if (timedOut) {
      throw new ApiError(`The request timed out while contacting ${url}. Please try again.`, { url, cause });
    }
    if (cause?.name === "AbortError") throw cause;
    throw new ApiError(`Could not reach the server at ${url}. Check your connection and try again.`, { url, cause });
  } finally {
    clearTimeout(timeout);
    externalSignal?.removeEventListener("abort", abortFromCaller);
  }
}

async function refreshAccess() {
  const refresh = localStorage.getItem("refresh");
  if (!refresh) return false;
  try {
    const response = await fetchJson(`${BASE}/auth/token/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    }, DEFAULT_TIMEOUT_MS);
    if (!response.ok || !response.data?.access) return false;
    localStorage.setItem("access", response.data.access);
    return true;
  } catch {
    return false;
  }
}

// All UI requests go through this helper. Pass { auth: false } for login/register.
export async function api(path, options = {}) {
  const { auth = true, timeoutMs = DEFAULT_TIMEOUT_MS, ...fetchOptions } = options;
  const url = /^https?:\/\//i.test(path) ? path : `${BASE}${path.startsWith("/") ? path : `/${path}`}`;
  const headers = {
    ...(fetchOptions.body && !(fetchOptions.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
    ...(fetchOptions.headers || {}),
  };

  if (auth && localStorage.getItem("access")) {
    headers.Authorization = `Bearer ${localStorage.getItem("access")}`;
  }

  let response;
  try {
    response = await fetchJson(url, { ...fetchOptions, headers }, timeoutMs);
  } catch (error) {
    response = failedResponse(error, url);
  }
  if (auth && response.status === 401) {
    if (await refreshAccess()) {
      headers.Authorization = `Bearer ${localStorage.getItem("access")}`;
      try {
        response = await fetchJson(url, { ...fetchOptions, headers }, timeoutMs);
      } catch (error) {
        response = failedResponse(error, url);
      }
    } else {
      clearSession();
      if (window.location.pathname !== "/login") window.location.assign("/login");
    }
  }
  return response;
}

function failedResponse(error, url) {
  const status = error instanceof ApiError ? error.status : 0;
  const data = { detail: errorText(error) };
  return {
    ok: false,
    status,
    statusText: error.message,
    headers: new Headers({ "Content-Type": "application/json" }),
    url: error.url || url,
    data,
    json: async () => data,
  };
}
