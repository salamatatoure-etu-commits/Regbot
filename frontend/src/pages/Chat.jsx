import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Sidebar from "../components/chat/Sidebar";
import MessageList from "../components/chat/MessageList";
import InputBar from "../components/chat/InputBar";
import { useStream } from "../hooks/useStream";
import { getFaq } from "../api/rag";
import { uploadTempDoc } from "../api/documents";
import { myConversations, startConversation, getConversationMessages, saveMessagePair, getConversationDocuments } from "../api/conversations";
import "./Chat.css";

const FAQ_ICONS = ["📅", "📋", "🏠", "❤️"];

export default function Chat({ user, token, onLogout }) {
  const [conversations, setConversations]   = useState([]);
  const [activeConv, setActiveConv]         = useState(null);
  const [messages, setMessages]             = useState([]);
  const [faq, setFaq]                       = useState([]);
  const [uploadedFiles, setUploadedFiles]   = useState([]);
  const { streaming, stream, abort }        = useStream(token);
  const convIdRef                           = useRef(null);
  const msgCacheRef                         = useRef({});

  const serviceId = user?.service_id || 1;
  const [provider, setProvider] = useState("groq");
  const llmModel = provider === "groq" ? "llama-3.3-70b-versatile" : "llama3.1:8b";
  const backendProvider = provider === "groq" ? "groq" : "ollama";

  useEffect(() => {
    getFaq(serviceId, token).then(setFaq).catch(() => {});
    myConversations(token)
      .then(data => {
        const mapped = data.map(c => ({
          conversationId: c.conversationid,
          titre: c.titre || `Conv. #${c.conversationid}`,
          dbId: c.conversationid,
          createdAt: c.last_activity ? new Date(c.last_activity).getTime() : Date.now(),
        }));
        setConversations(mapped);
      })
      .catch(() => {});
  }, [serviceId]);

  async function newConversation() {
    if (activeConv?.titre === "Nouvelle conversation" && messages.length === 0) {
      return;
    }

    abort();
    setUploadedFiles([]);
    try {
      const created = await startConversation(token);
      const conv = { conversationId: created.conversationid, titre: "Nouvelle conversation", dbId: created.conversationid, createdAt: Date.now() };
      setConversations(prev => [conv, ...prev]);
      setActiveConv(conv);
      setMessages([]);
      convIdRef.current = created.conversationid;
    } catch {
      const conv = { conversationId: Date.now(), titre: "Nouvelle conversation", dbId: null, createdAt: Date.now() };
      setConversations(prev => [conv, ...prev]);
      setActiveConv(conv);
      setMessages([]);
    }
  }

  async function selectConversation(conv) {
    abort();
    setUploadedFiles([]);
    const targetId = conv.dbId || conv.conversationId;

    // Affiche immédiatement depuis le cache si disponible
    if (msgCacheRef.current[targetId]) {
      setActiveConv(conv);
      setMessages(msgCacheRef.current[targetId]);
      convIdRef.current = targetId;
      return;
    }

    setActiveConv(conv);
    setMessages([]);
    convIdRef.current = targetId;
    try {
      const [msgs, docs] = await Promise.all([
        getConversationMessages(token, targetId),
        getConversationDocuments(token, targetId).catch(() => []),
      ]);
      if (convIdRef.current !== targetId) return;
      const docsById = Object.fromEntries(docs.map(d => [String(d.id), { name: d.filename, id: d.id }]));
      const mapped = msgs.map(m => ({
        role: m.type_message === "user" ? "user" : "bot",
        content: m.contenu,
        files: m.temp_document_ids
          ? m.temp_document_ids.split(",").map(id => docsById[id]).filter(Boolean)
          : undefined,
      }));
      msgCacheRef.current[targetId] = mapped;
      setMessages(mapped);
    } catch {
      setMessages([]);
    }
  }

  async function handleSend(question) {
    let conv = activeConv;

    if (!conv) {
      try {
        const created = await startConversation(token);
        conv = { conversationId: created.conversationid, titre: question.slice(0, 40), dbId: created.conversationid, createdAt: Date.now() };
      } catch {
        conv = { conversationId: Date.now(), titre: question.slice(0, 40), dbId: null, createdAt: Date.now() };
      }
      setConversations(prev => [conv, ...prev]);
      setActiveConv(conv);
      setMessages([]);
      convIdRef.current = conv.dbId;
    } else if (conv.titre === "Nouvelle conversation" && messages.length === 0) {
      const updated = { ...conv, titre: question.slice(0, 40) };
      setConversations(prev => prev.map(c => c.conversationId === conv.conversationId ? updated : c));
      setActiveConv(updated);
      conv = updated;
    }

    const attachedFileIds = uploadedFiles.map(f => f.id);
    setMessages(prev => [...prev, { role: "user", content: question, files: uploadedFiles.length > 0 ? [...uploadedFiles] : undefined }]);
    setMessages(prev => [...prev, { role: "bot", content: "" }]);
    setUploadedFiles([]);
    let botContent = "";

    await stream({
      question,
      service_id: serviceId,
      conversation_id: conv.dbId || conv.conversationId,
      history: messages
        .filter(m => m.role === "user" || (m.content && !m.content.startsWith("⚠")))
        .slice(-10)
        .map(m => ({ role: m.role, content: m.content })),
      provider: backendProvider,
      llm_model: llmModel,
      onAbort: () => {
        if (conv.dbId && question && botContent) {
          saveMessagePair(token, conv.dbId, question, botContent, attachedFileIds).catch(() => {});
        }
      },
      onToken: (t, isReplace = false) => {
        if (convIdRef.current !== (conv.dbId || conv.conversationId)) return;
        if (isReplace) botContent = t;
        else botContent += t;
        setMessages(prev => {
          const u = [...prev];
          u[u.length - 1] = { role: "bot", content: botContent };
          return u;
        });
      },
      onDone: (d) => {
        if (convIdRef.current !== (conv.dbId || conv.conversationId)) return;
        setMessages(prev => {
          const u = [...prev];
          u[u.length - 1] = { role: "bot", content: botContent, sources: d.sources, confidence: d.confidence, is_reliable: d.is_reliable };
          msgCacheRef.current[conv.dbId || conv.conversationId] = u;
          return u;
        });
        if (conv.dbId) {
          saveMessagePair(token, conv.dbId, question, botContent, attachedFileIds)
            .then(res => {
              setConversations(prev => {
                const updated = prev.map(c =>
                  c.conversationId === conv.conversationId
                    ? { ...c, titre: res?.titre || c.titre, createdAt: Date.now() }
                    : c
                );
                // Remonte la conversation active en tête de liste
                const idx = updated.findIndex(c => c.conversationId === conv.conversationId);
                if (idx > 0) {
                  const [active] = updated.splice(idx, 1);
                  updated.unshift(active);
                }
                return updated;
              });
              if (res?.titre) {
                setActiveConv(prev => prev?.conversationId === conv.conversationId
                  ? { ...prev, titre: res.titre }
                  : prev
                );
              }
            })
            .catch(() => {});
        }
      },
    });
  }

  async function handleUpload(file) {
    let conv = activeConv;
    if (!conv) {
      try {
        const created = await startConversation(token);
        conv = { conversationId: created.conversationid, titre: file.name.replace(/\.[^.]+$/, ""), dbId: created.conversationid, createdAt: Date.now() };
      } catch {
        conv = { conversationId: Date.now(), titre: file.name.replace(/\.[^.]+$/, ""), dbId: null, createdAt: Date.now() };
      }
      setConversations(prev => [conv, ...prev]);
      setActiveConv(conv);
      setMessages([]);
    }
    try {
      const result = await uploadTempDoc(token, conv.dbId || conv.conversationId, file);
      setUploadedFiles(prev => [{ name: file.name, id: result.id }, ...prev]);
    } catch (err) {
      console.error(err.message);
    }
  }

  function handleRemoveFile(fileId) {
    setUploadedFiles(prev => prev.filter(f => f.id !== fileId));
  }

  function handleDeleteConv(conversationId) {
    delete msgCacheRef.current[conversationId];
    setConversations(prev => prev.filter(c => c.conversationId !== conversationId));
    if (activeConv?.conversationId === conversationId) {
      setActiveConv(null);
      setMessages([]);
    }
  }

  function handleRenameConv(conversationId, titre) {
    setConversations(prev => prev.map(c => c.conversationId === conversationId ? { ...c, titre } : c));
    if (activeConv?.conversationId === conversationId) {
      setActiveConv(prev => prev ? { ...prev, titre } : prev);
    }
  }

  const showWelcome = messages.length === 0;
  const convTitle   = activeConv?.titre || "Nouvelle conversation";

  return (
    <div className="chat-layout">
      <Sidebar
        conversations={conversations}
        activeId={activeConv?.conversationId}
        onSelect={selectConversation}
        onNew={newConversation}
        onLogout={onLogout}
        onDeleteConv={handleDeleteConv}
        onRenameConv={handleRenameConv}
        user={user}
        token={token}
        uploadedFiles={uploadedFiles}
      />

      <main className="chat-main">
        {/* Header */}
        <header className="chat-header">
          <span className="chat-header-title">{convTitle}</span>
          <div className="chat-header-actions">
            <span className="chat-service-badge">
              <svg width="11" height="11" viewBox="0 0 16 16" fill="none">
                <rect x="2" y="5" width="12" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.5"/>
                <path d="M5 5V4a1 1 0 011-1h4a1 1 0 011 1v1" stroke="currentColor" strokeWidth="1.5"/>
              </svg>
              {user?.service_nom || "—"}
            </span>

            <span className="chat-llm-badge">{llmModel}</span>
          </div>
        </header>

        {/* Messages or Welcome */}
        <AnimatePresence>
          {showWelcome && (
            <motion.div
              className="welcome-section"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.35 }}
            >
              <div className="welcome-avatar">
                <svg width="36" height="40" viewBox="0 0 40 44" fill="none">
                  <path d="M20 1L3 8.5V22c0 10.5 7.5 19.5 17 21.5C30.5 41.5 38 32.5 38 22V8.5L20 1z" fill="#5c4ed8"/>
                  <rect x="11" y="14" width="15" height="3" rx="1.5" fill="rgba(255,255,255,0.85)"/>
                  <rect x="11" y="20" width="11" height="3" rx="1.5" fill="rgba(255,255,255,0.85)"/>
                  <rect x="11" y="26" width="7" height="3" rx="1.5" fill="rgba(255,255,255,0.85)"/>
                  <circle cx="27" cy="27.5" r="4.5" fill="#5c4ed8" stroke="rgba(255,255,255,0.85)" strokeWidth="2.5"/>
                </svg>
              </div>

              <h2 className="welcome-title">Bonjour, {user?.nom?.split(" ")[0] || "là"} !</h2>
              <p className="welcome-sub">Posez une question sur vos documents internes.</p>

              {faq.length > 0 && (
                <div className="faq-section">
                  <p className="faq-label">Questions fréquentes</p>
                  <div className="faq-cards">
                    {faq.slice(0, 4).map((f, i) => (
                      <motion.button
                        key={i}
                        className="faq-card"
                        onClick={() => handleSend(f.question)}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 + i * 0.07 }}
                        whileHover={{ y: -2, boxShadow: "0 4px 16px rgba(92,78,216,0.15)" }}
                        whileTap={{ scale: 0.98 }}
                      >
                        <span className="faq-card-icon">{FAQ_ICONS[i] || "💬"}</span>
                        <span className="faq-card-text">{f.question}</span>
                        <svg className="faq-card-arrow" width="14" height="14" viewBox="0 0 16 16" fill="none">
                          <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                      </motion.button>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        <MessageList messages={messages} streaming={streaming} user={user} />
        <InputBar onSend={handleSend} disabled={streaming} onUpload={handleUpload} onStop={abort} uploadedFiles={uploadedFiles} onRemoveFile={handleRemoveFile} llmModel={llmModel} provider={provider} onProviderChange={setProvider} />
      </main>
    </div>
  );
}
