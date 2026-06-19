import { useAuth } from "./hooks/useAuth";
import Login from "./pages/Login";
import Chat from "./pages/Chat";
import Admin from "./pages/Admin";

function App() {
  const { user, token, loading, signIn, signOut } = useAuth();

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh" }}>
        <p style={{ color: "#888" }}>Chargement…</p>
      </div>
    );
  }

  if (!user) return <Login onLogin={signIn} />;

  if (user.role === "admin") {
    return <Admin user={user} token={token} onLogout={signOut} />;
  }

  return <Chat user={user} token={token} onLogout={signOut} />;
}

export default App
