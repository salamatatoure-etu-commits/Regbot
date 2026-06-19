import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

export default function InputBar({ onSend, disabled, onUpload, onStop, uploadedFiles = [], onRemoveFile, llmModel, provider = "groq", onProviderChange }) {
  const [text, setText] = useState("");
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const dropdownRef = useRef(null);

  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 130) + "px";
  }, [text]);

  useEffect(() => {
    function handleClickOutside(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleSubmit(e) {
    e.preventDefault();
    const q = text.trim();
    if (!q || disabled) return;
    onSend(q);
    setText("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  }

  function handleKey(e) {
    if (e.key === "Enter" && !e.shiftKey) handleSubmit(e);
  }

  function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    onUpload?.(file);
  }

  const canSend = text.trim().length > 0 && !disabled;
  const providerLabel = provider === "groq" ? "Groq" : "Llama local";

  return (
    <div className="input-bar-wrap">
      <AnimatePresence>
        {uploadedFiles.length > 0 && (
          <motion.div
            className="input-files-chips"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 6 }}
            transition={{ duration: 0.18 }}
          >
            {uploadedFiles.map(f => (
              <div key={f.id} className="input-file-chip">
                <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
                  <path d="M4 2h6l4 4v8H4V2z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
                  <path d="M10 2v4h4" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
                </svg>
                <span className="input-file-chip-name">{f.name}</span>
                {onRemoveFile && (
                  <button
                    type="button"
                    className="input-file-chip-remove"
                    onClick={() => onRemoveFile(f.id)}
                    title="Retirer le fichier"
                  >
                    <svg width="10" height="10" viewBox="0 0 16 16" fill="none">
                      <path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                    </svg>
                  </button>
                )}
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      <form className="input-bar" onSubmit={handleSubmit}>
        <textarea
          ref={textareaRef}
          className="input-bar-textarea"
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Posez votre question…"
          rows={1}
          disabled={disabled}
        />

        <div className="input-bar-bottom">
          {/* Dropdown provider — bas gauche */}
          <div className="input-model-dropdown" ref={dropdownRef}>
            <button
              type="button"
              className="input-model-trigger"
              onClick={() => setDropdownOpen(o => !o)}
            >
              {providerLabel}
              <svg width="10" height="10" viewBox="0 0 16 16" fill="none"
                style={{ transform: dropdownOpen ? "rotate(180deg)" : "none", transition: "transform 0.2s" }}>
                <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>

            <AnimatePresence>
              {dropdownOpen && (
                <motion.div
                  className="input-model-menu"
                  initial={{ opacity: 0, y: 6, scale: 0.97 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 6, scale: 0.97 }}
                  transition={{ duration: 0.15 }}
                >
                  <button
                    type="button"
                    className={`input-model-item${provider === "groq" ? " input-model-item--active" : ""}`}
                    onClick={() => { onProviderChange?.("groq"); setDropdownOpen(false); }}
                  >
                    <div className="input-model-item-info">
                      <span className="input-model-item-name">Groq</span>
                      <span className="input-model-item-desc">llama-3.3-70b-versatile · Cloud</span>
                    </div>
                    {provider === "groq" && (
                      <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
                        <path d="M3 8l4 4 6-7" stroke="#5c4ed8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    )}
                  </button>
                  <button
                    type="button"
                    className={`input-model-item${provider === "ollama" ? " input-model-item--active" : ""}`}
                    onClick={() => { onProviderChange?.("ollama"); setDropdownOpen(false); }}
                  >
                    <div className="input-model-item-info">
                      <span className="input-model-item-name">Llama local</span>
                      <span className="input-model-item-desc">llama3.1:8b · Ollama</span>
                    </div>
                    {provider === "ollama" && (
                      <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
                        <path d="M3 8l4 4 6-7" stroke="#5c4ed8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    )}
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Actions — bas droite */}
          <div className="input-bar-actions">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.txt,.md,.docx,.doc,.xlsx,.xls,.html,.htm"
              style={{ display: "none" }}
              onChange={handleFileChange}
            />
            <button type="button" className="input-icon-btn" title="Joindre un fichier"
              onClick={() => fileInputRef.current?.click()}>
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"
                  stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>

            {disabled ? (
              <motion.button
                className="input-send-btn input-stop-btn"
                type="button"
                onClick={onStop}
                whileHover={{ scale: 1.08 }}
                whileTap={{ scale: 0.92 }}
                title="Arrêter la génération"
              >
                <motion.svg key="stop" width="14" height="14" viewBox="0 0 24 24" fill="currentColor"
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                  <rect x="4" y="4" width="16" height="16" rx="2"/>
                </motion.svg>
              </motion.button>
            ) : (
              <motion.button
                className={`input-send-btn ${canSend ? "active" : ""}`}
                type="submit"
                disabled={!canSend}
                whileHover={canSend ? { scale: 1.08 } : {}}
                whileTap={canSend ? { scale: 0.92 } : {}}
              >
                <motion.svg key="arrow" width="16" height="16" viewBox="0 0 24 24" fill="none"
                  initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                  <path d="M12 19V5M5 12l7-7 7 7" stroke="currentColor" strokeWidth="2.2"
                    strokeLinecap="round" strokeLinejoin="round"/>
                </motion.svg>
              </motion.button>
            )}
          </div>
        </div>
      </form>
    </div>
  );
}
