import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { login } from "../../api/auth";

export default function LoginForm({ onLogin }) {
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [showPwd, setShowPwd]   = useState(false);
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const tokens = await login(email, password);
      onLogin(tokens.access_token, tokens.refresh_token);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="login-form">
      <AnimatePresence>
        {error && (
          <motion.div
            className="login-error"
            initial={{ opacity: 0, y: -8, height: 0 }}
            animate={{ opacity: 1, y: 0, height: "auto" }}
            exit={{ opacity: 0, y: -8, height: 0 }}
            transition={{ duration: 0.2 }}
          >
            ⚠ {error}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="login-field">
        <label className="login-label">Adresse email</label>
        <input
          className="login-input"
          type="email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          placeholder="nom.prenom@entreprise.ma"
          autoComplete="email"
          required
        />
      </div>

      <div className="login-field">
        <label className="login-label">Mot de passe</label>
        <div className="login-input-wrap">
          <input
            className="login-input"
            type={showPwd ? "text" : "password"}
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder="••••••••"
            autoComplete="current-password"
            required
          />
          <button
            type="button"
            className="login-eye"
            onClick={() => setShowPwd(v => !v)}
            tabIndex={-1}
          >
            {showPwd ? "🙈" : "👁️"}
          </button>
        </div>
      </div>

      <motion.button
        className="login-btn"
        type="submit"
        disabled={loading}
        whileTap={{ scale: 0.98 }}
      >
        {loading ? (
          <>
            <span className="login-spinner" />
            Connexion…
          </>
        ) : (
          <>Se connecter <span>→</span></>
        )}
      </motion.button>
    </form>
  );
}
