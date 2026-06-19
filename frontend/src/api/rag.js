const BASE = "http://localhost:8001";

export async function queryStream({ question, service_id, bot_id, conversation_id, history, token, onToken, onDone, signal, provider = "groq", llm_model }) {
  const res = await fetch(`${BASE}/rag/query/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ question, service_id, bot_id, conversation_id, history, provider, llm_model }),
    signal,
  });

  const reader = res.body.getReader();
  const decoder = new TextDecoder();

  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop();
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data: ")) continue;
      try {
        const data = JSON.parse(line.slice(6));
        if (data.replace) onToken(data.replace, true);
        else if (data.token) onToken(data.token, false);
        if (data.done) onDone(data);
      } catch {}
    }
  }
}

export async function getFaq(service_id, token) {
  const res = await fetch(`${BASE}/rag/faq?service_id=${service_id}&limit=4`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return [];
  const data = await res.json();
  return data.faq || [];
}
