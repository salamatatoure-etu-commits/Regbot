const BASE = "http://localhost:8001";

export async function listConversations(token) {
  const res = await fetch(`${BASE}/conversations/`, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error("Erreur chargement conversations");
  return res.json();
}

export async function myConversations(token) {
  const res = await fetch(`${BASE}/conversations/me`, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error("Erreur chargement historique");
  return res.json();
}

export async function startConversation(token) {
  const res = await fetch(`${BASE}/conversations/start`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Erreur création conversation");
  return res.json();
}

export async function getConversationMessages(token, conversationId) {
  const res = await fetch(`${BASE}/conversations/${conversationId}/messages`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Erreur chargement messages");
  return res.json();
}

export async function saveMessagePair(token, conversationId, question, answer, tempDocumentIds = []) {
  const res = await fetch(`${BASE}/conversations/${conversationId}/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ question, answer, temp_document_ids: tempDocumentIds }),
  });
  if (!res.ok) throw new Error("Erreur sauvegarde");
  return res.json();
}

export async function deleteConversation(token, id) {
  const res = await fetch(`${BASE}/conversations/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Erreur suppression conversation");
}

export async function renameConversation(token, id, titre) {
  const res = await fetch(`${BASE}/conversations/${id}/titre`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ titre }),
  });
  if (!res.ok) throw new Error("Erreur renommage conversation");
  return res.json();
}

export async function deleteMyConversation(token, id) {
  const res = await fetch(`${BASE}/conversations/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Erreur suppression conversation");
}

export async function getConversationDocuments(token, conversationId) {
  const res = await fetch(`${BASE}/conversations/${conversationId}/documents`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Erreur chargement documents");
  return res.json();
}

export async function cleanupConversations(token) {
  const res = await fetch(`${BASE}/conversations/cleanup`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Erreur nettoyage");
  return res.json();
}
