import { useEffect, useRef, useState } from "react";
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

function FeedbackButtons({ messageId, onFeedback }) {
  const [voted, setVoted] = useState(null);

  if (!messageId) return null;

  function handle(value) {
    if (voted !== null) return;
    setVoted(value);
    onFeedback(messageId, value);
  }

  return (
    <div className="msg-feedback">
      <motion.button
        className={`msg-feedback-btn ${voted === 5 ? "msg-feedback-active-up" : ""}`}
        onClick={() => handle(5)}
        disabled={voted !== null}
        whileHover={voted === null ? { scale: 1.15 } : {}}
        whileTap={voted === null ? { scale: 0.9 } : {}}
        title="Bonne réponse"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill={voted === 5 ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 9V5a3 3 0 00-3-3l-4 9v11h11.28a2 2 0 002-1.7l1.38-9a2 2 0 00-2-2.3H14z"/>
          <path d="M7 22H4a2 2 0 01-2-2v-7a2 2 0 012-2h3"/>
        </svg>
      </motion.button>
      <motion.button
        className={`msg-feedback-btn ${voted === 1 ? "msg-feedback-active-down" : ""}`}
        onClick={() => handle(1)}
        disabled={voted !== null}
        whileHover={voted === null ? { scale: 1.15 } : {}}
        whileTap={voted === null ? { scale: 0.9 } : {}}
        title="Mauvaise réponse"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill={voted === 1 ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M10 15v4a3 3 0 003 3l4-9V2H5.72a2 2 0 00-2 1.7l-1.38 9a2 2 0 002 2.3H10z"/>
          <path d="M17 2h2.67A2.31 2.31 0 0122 4v7a2.31 2.31 0 01-2.33 2H17"/>
        </svg>
      </motion.button>
    </div>
  );
}

export default function MessageList({ messages, streaming, user, onFeedback }) {
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
                    {isBot && !streaming && msg.content && (
                      <FeedbackButtons messageId={msg.messageId} onFeedback={onFeedback} />
                    )}
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
