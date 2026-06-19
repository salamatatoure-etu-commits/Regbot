const BASE = "http://localhost:8001";

export async function getStats(token) {
  const res = await fetch(`${BASE}/stats/`, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error("Erreur chargement stats");
  return res.json();
}

export async function getLogs(token, limit = 50) {
  const res = await fetch(`${BASE}/stats/logs?limit=${limit}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error("Erreur chargement logs");
  return res.json();
}

export async function getStatsByService(token) {
  const res = await fetch(`${BASE}/stats/by-service`, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error("Erreur chargement stats par service");
  return res.json();
}
