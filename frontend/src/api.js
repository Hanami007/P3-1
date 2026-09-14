const BASE = "/api";

async function request(path, { method = "GET", body, cardUid } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (cardUid) headers["X-Card-UID"] = cardUid;

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      // response had no JSON body
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  scanCard: (cardUid) => request("/cards/scan", { method: "POST", body: { card_uid: cardUid } }),
  getSchedule: (cardUid) => request(`/students/${encodeURIComponent(cardUid)}/schedule`, { cardUid }),
  getExams: (cardUid) => request(`/students/${encodeURIComponent(cardUid)}/exams`, { cardUid }),
  getBuildings: () => request("/buildings"),
  getAnnouncements: (cardUid) => request("/announcements", { cardUid }),
  getLogs: (cardUid) => request("/logs", { cardUid }),
  chat: (message, cardUid) => request("/chat", { method: "POST", body: { message, card_uid: cardUid } }),
  getPresence: () => request("/presence"),
  simulatePresence: () => request("/presence/simulate", { method: "POST" }),
  simulateFaceRecognition: (cardUid) =>
    request("/presence/simulate-recognition", { method: "POST", body: { card_uid: cardUid } }),
};

export const DAY_NAMES_TH = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"];

export function roleToPath(role) {
  if (role === "cs_student") return "/student";
  if (role === "staff" || role === "admin") return "/staff";
  return "/guest";
}
