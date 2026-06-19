import { motion } from "framer-motion";
import LoginForm from "../components/auth/LoginForm";
import "./Login.css";

export default function Login({ onLogin }) {
  return (
    <div className="login-page">
      <div className="login-bg-blob login-bg-blob-1" />
      <div className="login-bg-blob login-bg-blob-2" />

      <motion.div
        className="login-card"
        initial={{ opacity: 0, y: 32, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
      >
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <div className="login-logo">RegBot</div>
          <p className="login-subtitle">Assistant documentaire interne</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <LoginForm onLogin={onLogin} />
        </motion.div>

        <motion.p
          className="login-notice"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          Connexion réservée aux employés de l&apos;AMMPS
        </motion.p>
      </motion.div>
    </div>
  );
}
