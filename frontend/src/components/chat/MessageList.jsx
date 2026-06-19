import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";

function ThinkingBubble() {
  return (
    <div className="thinking-bubble">
      {[0, 1, 2].map(i => (
        <motion.span
          key={i}
          className="thinking-dot"
          animate={{ y: [0, -5, 0], opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 0.7, repeat: Infinity, delay: i * 0.15, ease: "easeInOut" }}
        />
      ))}
    </div>
  );
}


function getInitials(name) {
  if (!name) return "?";
  return name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
}

function formatContent(text) {
  if (!text) return text;
  // Convertit les puces inline "• item • item" en liste markdown "- item\n- item"
  return text
    .split("\n")
    .map(line => {
      // Si la ligne contient plusieurs • séparés, on les éclate en lignes
      if ((line.match(/•/g) || []).length > 1) {
        return line
          .split("•")
          .map(s => s.trim())
          .filter(Boolean)
          .map(s => `- ${s}`)
          .join("\n");
      }
      // Si la ligne commence par •, on remplace par -
      if (/^\s*•\s+/.test(line)) {
        return line.replace(/^\s*•\s+/, "- ");
      }
      return line;
    })
    .join("\n");
}

export default function MessageList({ messages, streaming, user }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  const lastIsEmptyBot =
    messages.length > 0 &&
    messages[messages.length - 1].role === "bot" &&
    messages[messages.length - 1].content === "";

  return (
    <div className="message-list">
      <AnimatePresence initial={false}>
        {messages.map((msg, i) => {
          const isBot = msg.role === "bot";
          const isLastEmptyBot = i === messages.length - 1 && isBot && msg.content === "" && streaming;

          return (
            <motion.div
              key={i}
              className={`message message-${msg.role}`}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            >
              {isBot && (
                <div className="msg-bot-avatar">R</div>
              )}

              <div className={`message-bubble ${isBot ? "bubble-bot" : "bubble-user"}`}>
                {isLastEmptyBot ? (
                  <ThinkingBubble />
                ) : (
                  <>
                    {!isBot && msg.files?.length > 0 && (
                      <div className="msg-file-attachments">
                        {msg.files.map(f => (
                          <div key={f.id} className="msg-file-card">
                            <div className="msg-file-card-icon">
                              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/>
                                <path d="M14 2v6h6" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/>
                              </svg>
                            </div>
                            <div className="msg-file-card-info">
                              <span className="msg-file-card-name">{f.name}</span>
                              <span className="msg-file-card-type">Document</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    <div className="message-text">
                      <ReactMarkdown>{formatContent(msg.content)}</ReactMarkdown>
                      {streaming && i === messages.length - 1 && isBot && msg.content && (
                        <motion.span
                          className="typing-cursor"
                          animate={{ opacity: [1, 0] }}
                          transition={{ duration: 0.5, repeat: Infinity, repeatType: "reverse" }}
                        >▌</motion.span>
                      )}
                    </div>
                  </>
                )}
              </div>

              {!isBot && (
                <div className="msg-user-avatar">
                  {getInitials(user?.nom || user?.email)}
                </div>
              )}
            </motion.div>
          );
        })}
      </AnimatePresence>

      {streaming && !lastIsEmptyBot && (
        <motion.div
          className="message message-bot"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="msg-bot-avatar">R</div>
          <div className="message-bubble bubble-bot">
            <ThinkingBubble />
          </div>
        </motion.div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
