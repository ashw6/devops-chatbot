const BASE = import.meta.env.VITE_API_URL || "";

export async function api(path, { method = "GET", body, form, raw } = {}) {
  const headers = {};
  const token = localStorage.getItem("token");
  if (token) headers.Authorization = `Bearer ${token}`;
  let payload;
  if (form) payload = form;
  else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  let res;
  try {
    res = await fetch(`${BASE}/api${path}`, { method, headers, body: payload });
  } catch {
    throw new Error("Cannot reach the server. Check that the backend is running.");
  }
  if (res.status === 401 && token && !path.startsWith("/auth/login")) {
    localStorage.removeItem("token");
    window.location.href = "/login";
  }
  if (raw) return res;
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) {
    const d = data?.detail;
    throw new Error(typeof d === "string" ? d : "Something went wrong. Please try again.");
  }
  return data;
}

export async function download(path, filename) {
  const res = await api(path, { raw: true });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(data?.detail || "Download failed");
  }
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
