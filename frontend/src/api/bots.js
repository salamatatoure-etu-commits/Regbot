const BASE = "http://localhost:8001";

export async function listBots(token) {
  const res = await fetch(`${BASE}/bots/`, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error("Erreur chargement bots");
  return res.json();
}

export async function createBot(token, data) {
  const res = await fetch(`${BASE}/bots/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Erreur création bot");
  }
  return res.json();
}

export async function updateBotPrompt(token, botId, prompt) {
  const res = await fetch(`${BASE}/bots/${botId}/prompt`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ prompt }),
  });
  if (!res.ok) throw new Error("Erreur mise à jour prompt");
  return res.json();
}

export async function deleteBot(token, botId) {
  const res = await fetch(`${BASE}/bots/${botId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Erreur suppression bot");
}
