const BASE = "http://localhost:8001";

export async function listDocuments(token, service_id) {
  const url = service_id
    ? `${BASE}/documents/?service_id=${service_id}&limit=50`
    : `${BASE}/documents/?limit=50`;
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error("Erreur chargement documents");
  return res.json();
}

export async function uploadDocument(token, file, service_id) {
  const form = new FormData();
  form.append("file", file);
  form.append("name", file.name);
  if (service_id) form.append("service_id", service_id);
  const res = await fetch(`${BASE}/documents/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Erreur upload");
  }
  return res.json();
}

export async function uploadTempDoc(token, conversationId, file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`http://localhost:8001/conversations/${conversationId}/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Erreur upload");
  }
  return res.json();
}

export async function deleteDocument(token, documentId) {
  const res = await fetch(`${BASE}/documents/${documentId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Erreur suppression");
}
