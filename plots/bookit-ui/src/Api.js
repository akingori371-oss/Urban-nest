const BASE = "/api";

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
  if (!data) return "Something went wrong.";
  if (typeof data === "string") return data;
  if (data.detail) return data.detail;
  return Object.entries(data)
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(" ") : value}`)
    .join(" | ");
}

async function refreshAccess() {
  const refresh = localStorage.getItem("refresh");
  if (!refresh) return false;
  const res = await fetch(`${BASE}/auth/token/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) return false;
  const data = await res.json();
  localStorage.setItem("access", data.access);
  return true;
}

// Use api("/houses/") for normal calls. Pass { auth: false } for login and register.
export async function api(path, options = {}) {
  const { auth = true, ...fetchOptions } = options;
  const headers = { "Content-Type": "application/json", ...(fetchOptions.headers || {}) };

  if (auth && localStorage.getItem("access")) {
    headers.Authorization = `Bearer ${localStorage.getItem("access")}`;
  }

  let res = await fetch(BASE + path, { ...fetchOptions, headers });

  // Access token expired: get a new one with the refresh token and retry once.
  if (auth && res.status === 401) {
    if (await refreshAccess()) {
      headers.Authorization = `Bearer ${localStorage.getItem("access")}`;
      res = await fetch(BASE + path, { ...fetchOptions, headers });
    } else {
      clearSession();
      window.location.href = "/login";
    }
  }
  return res;
}