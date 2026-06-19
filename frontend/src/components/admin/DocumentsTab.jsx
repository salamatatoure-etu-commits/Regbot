import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { listDocuments, uploadDocument, deleteDocument } from "../../api/documents";
import { listServices } from "../../api/services";

const MIME_LABELS = {
  "text/plain":                                                          "TXT",
  "application/pdf":                                                     "PDF",
  "application/msword":                                                  "Word",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Word",
  "application/vnd.ms-excel":                                            "Excel",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":  "Excel",
  "application/vnd.ms-powerpoint":                                       "PPT",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation": "PPT",
  "text/csv":                                                            "CSV",
  "application/json":                                                    "JSON",
  "text/markdown":                                                       "MD",
};

function stripExt(name) {
  if (!name) return "—";
  return name.replace(/\.[^.]+$/, "");
}

function formatMime(mime) {
  if (!mime) return "—";
  return MIME_LABELS[mime] || mime.split("/")[1]?.toUpperCase() || mime;
}

function ActionMenu({ docId, onDelete }) {
  const [open, setOpen] = useState(false);
  const [dropUp, setDropUp] = useState(false);
  const ref = useRef(null);
  const btnRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  function handleOpen() {
    if (btnRef.current) {
      const rect = btnRef.current.getBoundingClientRect();
      setDropUp(rect.bottom + 120 > window.innerHeight);
    }
    setOpen(v => !v);
  }

  return (
    <div ref={ref} style={{ position: "relative", display: "inline-block" }}>
      <motion.button
        ref={btnRef}
        className="btn-menu-dots"
        onClick={handleOpen}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.92 }}
        title="Actions"
      >
        ⋮
      </motion.button>
      <AnimatePresence>
        {open && (
          <motion.div
            className="doc-action-menu"
            style={dropUp ? { bottom: "calc(100% + 4px)", top: "auto" } : {}}
            initial={{ opacity: 0, y: dropUp ? 6 : -6, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.15 }}
          >
            <button
              className="doc-action-item doc-action-delete"
              onClick={() => { setOpen(false); onDelete(docId); }}
            >
              🗑 Supprimer
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function DocumentsTab({ token }) {
  const [docs,        setDocs]        = useState([]);
  const [services,    setServices]    = useState([]);
  const [loading,     setLoading]     = useState(true);
  const [uploading,   setUploading]   = useState(false);
  const [error,       setError]       = useState("");
  const [showForm,    setShowForm]    = useState(false);
  const [serviceId,   setServiceId]   = useState("");
  const [pendingFile, setPendingFile] = useState(null);

  // search & filter
  const [search,      setSearch]      = useState("");
  const [showFilters, setShowFilters] = useState(true);
  const [filterSvc,   setFilterSvc]   = useState("");
  const [filterType,  setFilterType]  = useState("");

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    try {
      const [data, svcs] = await Promise.all([listDocuments(token), listServices(token)]);
      setDocs(data.sort((a, b) => a.name.localeCompare(b.name, "fr")));
      setServices(svcs);
    }
    catch { setError("Erreur chargement documents"); }
    finally { setLoading(false); }
  }

  function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setPendingFile(file);
    setShowForm(true);
    e.target.value = "";
  }

  async function handleUpload(e) {
    e.preventDefault();
    if (!pendingFile) return;
    setUploading(true);
    setError("");
    try {
      await uploadDocument(token, pendingFile, serviceId);
      await load();
      setShowForm(false);
      setPendingFile(null);
      setServiceId("");
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(id) {
    if (!confirm("Supprimer ce document ?")) return;
    try { await deleteDocument(token, id); await load(); }
    catch { setError("Erreur suppression"); }
  }

  const hasFilter = filterSvc || filterType;

  const visible = docs.filter(d => {
    const q = search.toLowerCase();
    if (q && !stripExt(d.name).toLowerCase().includes(q)) return false;
    if (filterSvc  && String(d.service_id) !== filterSvc)  return false;
    if (filterType && formatMime(d.mime_type) !== filterType) return false;
    return true;
  });

  const mimeOptions = [...new Set(docs.map(d => formatMime(d.mime_type)).filter(t => t !== "—"))];

  if (loading) return <p className="tab-loading">Chargement…</p>;

  return (
    <div className="tab-section">
      <div className="tab-toolbar">
        <div>
          <h2 className="tab-title">Documents</h2>
          <p className="tab-subtitle">Gérez et organisez tous vos documents.</p>
        </div>

        {/* search + filtres + importer */}
        <div className="doc-toolbar-right">
          <div className="doc-search-wrap">
            <span className="doc-search-icon">🔍</span>
            <input
              className="doc-search-input"
              placeholder="Rechercher un document…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            {search && (
              <button className="doc-search-clear" onClick={() => setSearch("")}>✕</button>
            )}
          </div>

          <motion.button
            className={`btn-filter ${showFilters || hasFilter ? "btn-filter-active" : ""}`}
            onClick={() => setShowFilters(v => !v)}
            whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
          >
            ▼ Filtres{hasFilter ? " •" : ""}
          </motion.button>

          <motion.label className="btn-primary" whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }} style={{ cursor: "pointer" }}>
            + Importer
            <input type="file" hidden onChange={handleFileChange}
              accept=".pdf,.txt,.md,.docx,.doc,.xlsx,.xls,.html" />
          </motion.label>
        </div>
      </div>

      {/* filter panel */}
      <AnimatePresence>
        {showFilters && (
          <motion.div
            className="doc-filter-panel"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            style={{ overflow: "hidden" }}
          >
            <div className="form-row" style={{ marginBottom: 0 }}>
              <div className="form-group">
                <label>Service</label>
                <select className="inline-input" value={filterSvc} onChange={e => setFilterSvc(e.target.value)}>
                  <option value="">Tous</option>
                  {services.map(s => (
                    <option key={s.serviceId} value={String(s.serviceId)}>{s.nom}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Type</label>
                <select className="inline-input" value={filterType} onChange={e => setFilterType(e.target.value)}>
                  <option value="">Tous</option>
                  {mimeOptions.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              {hasFilter && (
                <div className="form-group" style={{ justifyContent: "flex-end", display: "flex", alignItems: "flex-end" }}>
                  <button className="btn-danger-sm" onClick={() => { setFilterSvc(""); setFilterType(""); }}>
                    Réinitialiser
                  </button>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* import form */}
      <AnimatePresence>
        {showForm && (
          <motion.form
            className="create-user-form"
            onSubmit={handleUpload}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.22 }}
            style={{ overflow: "hidden" }}
          >
            <div className="form-row" style={{ alignItems: "center" }}>
              <div className="form-group">
                <label>Fichier sélectionné</label>
                <input className="inline-input" value={pendingFile?.name || ""} readOnly style={{ color: "#888" }} />
              </div>
              <div className="form-group">
                <label>Service *</label>
                <select className="inline-input" value={serviceId} onChange={e => setServiceId(e.target.value)} required>
                  <option value="">— Choisir un service —</option>
                  {services.map(s => (
                    <option key={s.serviceId} value={s.serviceId}>{s.nom}</option>
                  ))}
                </select>
              </div>
            </div>
            <div style={{ display: "flex", gap: "0.6rem" }}>
              <motion.button className="btn-primary" type="submit" disabled={uploading}
                whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}>
                {uploading ? "Envoi…" : "Confirmer l'import"}
              </motion.button>
              <button type="button" className="btn-danger-sm"
                onClick={() => { setShowForm(false); setPendingFile(null); setServiceId(""); }}>
                Annuler
              </button>
            </div>
          </motion.form>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {error && (
          <motion.div className="tab-error"
            initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      <table className="admin-table">
        <thead>
          <tr><th>Nom</th><th>Service</th><th>Type</th><th>Chunks</th><th></th></tr>
        </thead>
        <tbody>
          <AnimatePresence>
            {visible.map((d, i) => (
              <motion.tr key={d.documentId}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                transition={{ delay: i * 0.03 }}
              >
                <td>{stripExt(d.name)}</td>
                <td>{services.find(s => s.serviceId === d.service_id)?.nom ?? "—"}</td>
                <td><span className="badge">{formatMime(d.mime_type)}</span></td>
                <td>{d.chunk_count}</td>
                <td style={{ textAlign: "right" }}>
                  <ActionMenu docId={d.documentId} onDelete={handleDelete} />
                </td>
              </motion.tr>
            ))}
          </AnimatePresence>
          {visible.length === 0 && (
            <tr><td colSpan={5} className="table-empty">
              {docs.length === 0 ? "Aucun document" : "Aucun résultat"}
            </td></tr>
          )}
        </tbody>
      </table>

      {docs.length > 0 && (
        <p className="tab-total-count">
          {(search || hasFilter)
            ? `≡ ${visible.length} / ${docs.length} document${docs.length > 1 ? "s" : ""}`
            : `≡ ${docs.length} document${docs.length > 1 ? "s" : ""} au total`}
        </p>
      )}
    </div>
  );
}
