import { motion, AnimatePresence } from "framer-motion";

function ConfidenceBadge({ pct }) {
  const color = pct >= 70 ? "#10b981" : pct >= 40 ? "#f59e0b" : "#ef4444";
  const label = pct >= 70 ? "Fiable" : pct >= 40 ? "Incertain" : "Faible";
  return (
    <div className="conf-section">
      <div className="conf-header">
        <span className="conf-label">Fiabilité</span>
        <span className="conf-badge" style={{ color, background: `${color}18` }}>{label}</span>
      </div>
      <div className="conf-bar-bg">
        <motion.div
          className="conf-bar-fill"
          style={{ background: `linear-gradient(90deg, ${color}99, ${color})` }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        />
      </div>
      <span className="conf-pct" style={{ color }}>{pct}%</span>
    </div>
  );
}

export default function SourcesPanel({ sources, confidence, model }) {
  const pct = Math.round((confidence || 0) * 100);

  return (
    <motion.aside
      className="sources-panel"
      initial={{ x: 40, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="sources-header">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
          <path d="M4 2h6l4 4v8H4V2z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
          <path d="M10 2v4h4" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
        </svg>
        Sources
      </div>

      <AnimatePresence mode="wait">
        {!sources ? (
          <motion.div
            key="empty"
            className="sources-empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div className="sources-empty-icon">📋</div>
            <p className="sources-hint">Les sources de la réponse apparaîtront ici.</p>
          </motion.div>
        ) : (
          <motion.div
            key="sources"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            {sources.length === 0 ? null : (
              <div className="sources-list">
                {sources.map((s, i) => (
                  <motion.div
                    key={i}
                    className="source-card"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.08 }}
                  >
                    <div className="source-rank">{i + 1}</div>
                    <div className="source-info">
                      <span className="source-name">{s.titre}</span>
                      {s.page && <span className="source-page">Page {s.page}</span>}
                      <div className="source-score-bar-bg">
                        <motion.div
                          className="source-score-bar"
                          initial={{ width: 0 }}
                          animate={{ width: `${Math.round(s.score * 100)}%` }}
                          transition={{ delay: i * 0.08 + 0.1, duration: 0.4 }}
                        />
                      </div>
                      <span className="source-score">{Math.round(s.score * 100)}%</span>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}

            {sources.length > 0 && <ConfidenceBadge pct={pct} />}

            {model && (
              <div className="sources-model">
                <svg width="10" height="10" viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5"/>
                  <path d="M8 5v3l2 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
                {model}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.aside>
  );
}
