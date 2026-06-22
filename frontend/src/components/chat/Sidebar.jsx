import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { changePassword } from "../../api/auth";
import { deleteMyConversation, renameConversation } from "../../api/conversations";

function getInitials(name) {
  if (!name) return "?";
  return name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
}

function relativeDate(ts) {
  const now = Date.now();
  const diff = now - ts;
  const mins = Math.floor(diff / 60000);
  if (mins < 2) return "maintenant";
  if (mins < 60) return `${mins}min`;
  const hours = Math.floor(diff / 3600000);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(diff / 86400000);
  if (days === 1) return "hier";
  const days_fr = ["dim.", "lun.", "mar.", "mer.", "jeu.", "ven.", "sam."];
  if (days < 7) return days_fr[new Date(ts).getDay()];
  return new Date(ts).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
}

const LANGS = [
  { code: "fr", label: "Français", flag: "🇫🇷" },
  { code: "en", label: "English",  flag: "🇬🇧" },
];

function ConvList({ conversations, search, activeId, hoveredConv, openMenuConv, onSelect, setOpenMenuConv, setHoveredConv, onDeleteConv, onRenameConv, token }) {
  const [renamingId, setRenamingId] = useState(null);
  const [renameVal,  setRenameVal]  = useState("");
  const renameRef = useRef(null);

  useEffect(() => { if (renamingId) renameRef.current?.focus(); }, [renamingId]);

  function startRename(c) {
    setOpenMenuConv(null);
    setRenamingId(c.conversationId);
    setRenameVal(c.titre || "");
  }

  function submitRename(c) {
    const titre = renameVal.trim();
    if (titre && titre !== c.titre) {
      renameConversation(token, c.dbId || c.conversationId, titre)
        .then(() => onRenameConv(c.conversationId, titre))
        .catch(() => {});
    }
    setRenamingId(null);
  }

  const filtered = search
    ? conversations.filter(c => (c.titre || "").toLowerCase().includes(search.toLowerCase()))
    : conversations;

  return (
    <>
      <div className="sidebar-section-label">
        {"Récent"}
      </div>
      <div className="sidebar-list">
        <AnimatePresence>
          {filtered.length === 0 ? (
            <div className="sidebar-no-results">Aucune conversation trouvée</div>
          ) : filtered.map((c, i) => (
            <motion.div
              key={c.conversationId}
              className={`sidebar-item ${c.conversationId === activeId ? "active" : ""}`}
              style={{ display: "flex", alignItems: "center", cursor: renamingId === c.conversationId ? "default" : "pointer", position: "relative" }}
              onClick={() => { if (renamingId !== c.conversationId) { onSelect(c); setOpenMenuConv(null); } }}
              onMouseEnter={() => setHoveredConv(c.conversationId)}
              onMouseLeave={() => setHoveredConv(null)}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.04 }}
            >
              <span className={`sidebar-dot ${c.conversationId === activeId ? "dot-active" : ""}`} />

              {renamingId === c.conversationId ? (
                <input
                  ref={renameRef}
                  className="sidebar-rename-input"
                  value={renameVal}
                  onChange={e => setRenameVal(e.target.value)}
                  onBlur={() => submitRename(c)}
                  onKeyDown={e => {
                    if (e.key === "Enter") submitRename(c);
                    if (e.key === "Escape") setRenamingId(null);
                  }}
                  onClick={e => e.stopPropagation()}
                />
              ) : (
                <span className="sidebar-item-title" style={{ flex: 1 }}>{c.titre}</span>
              )}

              {renamingId !== c.conversationId && (
                <AnimatePresence>
                  {hoveredConv === c.conversationId || openMenuConv === c.conversationId ? (
                    <motion.button key="dots" className="sidebar-dots-btn"
                      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                      transition={{ duration: 0.1 }}
                      onClick={e => { e.stopPropagation(); setOpenMenuConv(prev => prev === c.conversationId ? null : c.conversationId); }}
                    >⋮</motion.button>
                  ) : (
                    <motion.span key="date" className="sidebar-item-date"
                      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                      transition={{ duration: 0.1 }}
                    >
                      {relativeDate(c.createdAt || c.conversationId)}
                    </motion.span>
                  )}
                </AnimatePresence>
              )}

              <AnimatePresence>
                {openMenuConv === c.conversationId && (
                  <motion.div className="conv-action-menu"
                    initial={{ opacity: 0, scale: 0.95, y: -4 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95, y: -4 }}
                    transition={{ duration: 0.12 }}
                    onClick={e => e.stopPropagation()}
                  >
                    <button className="conv-action-item" onClick={() => startRename(c)}>
                      <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
                        <path d="M11 2l3 3-8 8H3v-3l8-8z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
                      </svg>
                      Renommer
                    </button>
                    <div className="user-menu-divider" />
                    <button className="conv-action-item conv-action-delete"
                      onClick={() => {
                        setOpenMenuConv(null);
                        if (window.confirm("Supprimer cette conversation ?")) {
                          deleteMyConversation(token, c.dbId || c.conversationId)
                            .then(() => onDeleteConv(c.conversationId))
                            .catch(() => {});
                        }
                      }}
                    >
                      <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
                        <path d="M2 4h12M6 4V2h4v2M13 4l-1 10H4L3 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                      Supprimer
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </>
  );
}

export default function Sidebar({ conversations, activeId, onSelect, onNew, onLogout, onDeleteConv, onRenameConv, user, token, uploadedFiles = [] }) {
  const [showUserMenu,  setShowUserMenu]  = useState(false);
  const [showProfil,    setShowProfil]    = useState(false);
  const [showLangMenu,  setShowLangMenu]  = useState(false);
  const [lang,          setLang]          = useState(() => localStorage.getItem("regbot-lang") || "fr");
  const [dark,          setDark]          = useState(() => localStorage.getItem("regbot-theme") === "dark");

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("regbot-theme", dark ? "dark" : "light");
  }, [dark]);
  const [hoveredConv,   setHoveredConv]   = useState(null);
  const [openMenuConv,  setOpenMenuConv]  = useState(null);
  const [search, setSearch] = useState("");
  const searchRef = useRef(null);

  const [oldPwd,    setOldPwd]    = useState("");
  const [newPwd,    setNewPwd]    = useState("");
  const [pwdMsg,    setPwdMsg]    = useState(null);
  const [pwdLoading, setPwdLoading] = useState(false);
  const pwdPendingRef = useRef(false);

  function selectLang(code) {
    setLang(code);
    localStorage.setItem("regbot-lang", code);
    setShowLangMenu(false);
  }

  async function handleChangePassword(e) {
    e.preventDefault();
    if (pwdPendingRef.current) return;
    pwdPendingRef.current = true;
    setPwdMsg(null);
    setPwdLoading(true);
    try {
      await changePassword(token, oldPwd, newPwd);
      setPwdMsg({ ok: true, text: "Mot de passe modifié avec succès." });
      setOldPwd("");
      setNewPwd("");
      setTimeout(() => setPwdMsg(null), 2000);
    } catch (err) {
      setPwdMsg({ ok: false, text: err.message });
    } finally {
      setPwdLoading(false);
      pwdPendingRef.current = false;
    }
  }

  return (
    <>
      <aside className="chat-sidebar">
        {/* Logo */}
        <div className="sidebar-logo-row">
          <svg width="26" height="28" viewBox="0 0 40 44" fill="none">
            <path d="M20 1L3 8.5V22c0 10.5 7.5 19.5 17 21.5C30.5 41.5 38 32.5 38 22V8.5L20 1z" fill="#5c4ed8"/>
            <rect x="11" y="14" width="15" height="2.5" rx="1.25" fill="rgba(255,255,255,0.9)"/>
            <rect x="11" y="20" width="11" height="2.5" rx="1.25" fill="rgba(255,255,255,0.9)"/>
            <rect x="11" y="26" width="7" height="2.5" rx="1.25" fill="rgba(255,255,255,0.9)"/>
          </svg>
          <span className="sidebar-logo-name">RegBot</span>
          <span className="sidebar-logo-tag">Employé</span>
        </div>

        {/* New conversation */}
        <motion.button
          className="sidebar-new"
          onClick={onNew}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
        >
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
          Nouvelle question
        </motion.button>

        {/* Search + conversations */}
        {conversations.length > 0 && (
          <>
            <div className="sidebar-search-wrap">
              <svg width="13" height="13" viewBox="0 0 16 16" fill="none" className="sidebar-search-icon">
                <circle cx="6.5" cy="6.5" r="4.5" stroke="currentColor" strokeWidth="1.5"/>
                <path d="M10 10l3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
              <input
                ref={searchRef}
                className="sidebar-search-input"
                type="text"
                placeholder="Rechercher…"
                value={search}
                onChange={e => setSearch(e.target.value)}
                onKeyDown={e => e.key === "Escape" && setSearch("")}
              />
              {search && (
                <button className="sidebar-search-clear" onClick={() => setSearch("")}>
                  <svg width="10" height="10" viewBox="0 0 16 16" fill="none">
                    <path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                  </svg>
                </button>
              )}
            </div>
            <ConvList conversations={conversations} search={search} activeId={activeId} hoveredConv={hoveredConv} openMenuConv={openMenuConv} onSelect={onSelect} setOpenMenuConv={setOpenMenuConv} setHoveredConv={setHoveredConv} onDeleteConv={onDeleteConv} onRenameConv={onRenameConv} token={token} />
          </>
        )}


        {/* User section */}
        <div className="sidebar-user-wrap">
          <button className="sidebar-user" onClick={() => { setShowUserMenu(v => !v); setShowLangMenu(false); }}>
            <div className="sidebar-avatar">{getInitials(user?.nom || user?.email)}</div>
            <div className="sidebar-user-info">
              <span className="sidebar-username">{user?.nom || user?.email}</span>
              <span className="sidebar-role">{user?.service_nom || "—"}</span>
            </div>
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0, color: "#aaa" }}>
              <path d={showUserMenu ? "M4 10l4-4 4 4" : "M4 6l4 4 4-4"} stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>

          <AnimatePresence>
            {showUserMenu && !showLangMenu && (
              <motion.div
                className="user-menu"
                initial={{ opacity: 0, y: 6, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 6, scale: 0.97 }}
                transition={{ duration: 0.15 }}
              >
                <button className="user-menu-item" onClick={() => { setShowUserMenu(false); setShowProfil(true); }}>
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                    <circle cx="8" cy="5" r="3" stroke="currentColor" strokeWidth="1.5"/>
                    <path d="M2 13c0-3 2.5-5 6-5s6 2 6 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  </svg>
                  Profil
                </button>
                <button className="user-menu-item" onClick={() => setDark(v => !v)}>
                  {dark ? (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
                    </svg>
                  ) : (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>
                    </svg>
                  )}
                  {dark ? "Mode clair" : "Mode sombre"}
                </button>
                <button className="user-menu-item" onClick={() => setShowLangMenu(true)}>
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                    <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5"/>
                    <ellipse cx="8" cy="8" rx="2.5" ry="6" stroke="currentColor" strokeWidth="1.5"/>
                    <path d="M2 8h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  </svg>
                  Langue
                  <span className="user-menu-lang-badge">{lang.toUpperCase()}</span>
                </button>
                <div className="user-menu-divider" />
                <button className="user-menu-item user-menu-logout" onClick={() => { setShowUserMenu(false); onLogout(); }}>
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                    <path d="M6 14H3a1 1 0 01-1-1V3a1 1 0 011-1h3M10 11l3-3-3-3M13 8H6"
                      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  Se déconnecter
                </button>
              </motion.div>
            )}

            {showLangMenu && (
              <motion.div
                className="user-menu"
                initial={{ opacity: 0, y: 6, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 6, scale: 0.97 }}
                transition={{ duration: 0.15 }}
              >
                <button className="user-menu-item user-menu-back" onClick={() => setShowLangMenu(false)}>
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                    <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  Langue
                </button>
                <div className="user-menu-divider" />
                {LANGS.map(l => (
                  <button
                    key={l.code}
                    className={`user-menu-item ${lang === l.code ? "user-menu-lang-active" : ""}`}
                    onClick={() => selectLang(l.code)}
                  >
                    <span>{l.flag}</span>
                    {l.label}
                    {lang === l.code && (
                      <svg width="13" height="13" viewBox="0 0 16 16" fill="none" style={{ marginLeft: "auto" }}>
                        <path d="M3 8l4 4 6-7" stroke="#5c4ed8" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    )}
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </aside>

      {/* Profil modal */}
      <AnimatePresence>
        {showProfil && (
          <motion.div
            className="profil-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowProfil(false)}
          >
            <motion.div
              className="profil-modal"
              initial={{ opacity: 0, scale: 0.94, y: 16 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.94, y: 16 }}
              transition={{ duration: 0.2 }}
              onClick={e => e.stopPropagation()}
            >
              <button className="profil-close" onClick={() => setShowProfil(false)}>
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
                </svg>
              </button>

              <div className="profil-avatar">{getInitials(user?.nom || user?.email)}</div>
              <h3 className="profil-name">{user?.nom || "—"}</h3>
              <span className="profil-service-badge">{user?.service_nom || "—"}</span>

              <div className="profil-fields">
                <div className="profil-field">
                  <span className="profil-field-label">Email</span>
                  <span className="profil-field-value">{user?.email || "—"}</span>
                </div>
                <div className="profil-field">
                  <span className="profil-field-label">Service</span>
                  <span className="profil-field-value">{user?.service_nom || "—"}</span>
                </div>
                <div className="profil-field">
                  <span className="profil-field-label">Rôle</span>
                  <span className="profil-field-value">{user?.role || "Employé"}</span>
                </div>
              </div>

              <div className="profil-pwd-section">
                <h4 className="profil-pwd-title">Changer le mot de passe</h4>
                <form className="profil-pwd-form" onSubmit={handleChangePassword}>
                  <input
                    className="profil-pwd-input"
                    type="password"
                    placeholder="Mot de passe actuel"
                    value={oldPwd}
                    onChange={e => setOldPwd(e.target.value)}
                    required
                  />
                  <input
                    className="profil-pwd-input"
                    type="password"
                    placeholder="Nouveau mot de passe (6 car. min.)"
                    value={newPwd}
                    onChange={e => setNewPwd(e.target.value)}
                    required
                    minLength={6}
                  />
                  <AnimatePresence>
                    {pwdMsg && (
                      <motion.p
                        className={pwdMsg.ok ? "profil-pwd-success" : "profil-pwd-error"}
                        initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                      >
                        {pwdMsg.text}
                      </motion.p>
                    )}
                  </AnimatePresence>
                  <button className="profil-pwd-btn" type="submit" disabled={pwdLoading}>
                    {pwdLoading ? "Enregistrement…" : "Enregistrer"}
                  </button>
                </form>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
