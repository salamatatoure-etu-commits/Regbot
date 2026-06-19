import { useState, useRef } from "react";
import { queryStream } from "../api/rag";

export function useStream(token) {
  const [streaming, setStreaming] = useState(false);
  const controllerRef = useRef(null);
  const onAbortRef = useRef(null);

  async function stream({ question, service_id, bot_id, conversation_id, history, onToken, onDone, onAbort, provider = "groq", llm_model }) {
    const controller = new AbortController();
    controllerRef.current = controller;
    onAbortRef.current = onAbort ?? null;
    setStreaming(true);
    try {
      await queryStream({
        question, service_id, bot_id, conversation_id, history, token,
        signal: controller.signal,
        onToken,
        onDone,
        provider,
        llm_model,
      });
    } catch (err) {
      if (err.name === "AbortError") {
        onAbortRef.current?.();
      } else {
        throw err;
      }
    } finally {
      setStreaming(false);
      onAbortRef.current = null;
    }
  }

  function abort() {
    controllerRef.current?.abort();
    setStreaming(false);
  }

  return { streaming, stream, abort };
}
