import { useState } from "react";
import api from "../api";

const API = "http://localhost:8000";

export default function Login({ onLogin, onSignup }) {

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin(e) {

    e.preventDefault();

    setError("");

    if (!username.trim() || !password) {
      setError("Please enter username and password.");
      return;
    }

    try {

      setLoading(true);

      const response = await api.post(
        `${API}/auth/login`,
        {
          username: username.trim(),
          password
        }
      );

      const data = response.data;

      localStorage.setItem(
        "token",
        data.token
      );

      localStorage.setItem(
        "user",
        JSON.stringify(data.user)
      );

      onLogin(data.user);

    } catch (err) {

      setError(
        err.response?.data?.detail ||
        "Login failed."
      );

    } finally {

      setLoading(false);

    }
  }

  return (
    <div style={styles.page}>

      <div style={styles.card}>

        <h1>🛡️ CyberGuard</h1>

        <p style={styles.subtitle}>
          AI-Powered Cyberbullying Detection
        </p>

        <form onSubmit={handleLogin}>

          <input
            style={styles.input}
            placeholder="Username"
            value={username}
            onChange={e => setUsername(e.target.value)}
          />

          <input
            style={styles.input}
            type="password"
            placeholder="Password"
            value={password}
            onChange={e => setPassword(e.target.value)}
          />

          {error && (
            <div style={styles.error}>
              {error}
            </div>
          )}

          <button
            style={styles.button}
            disabled={loading}
          >
            {loading ? "Logging in..." : "Login"}
          </button>

        </form>

        <p style={styles.signupText}>
          Don't have an account?
        </p>

        <button
          style={styles.signupButton}
          onClick={onSignup}
        >
          Create Account
        </button>

      </div>

    </div>
  );
}


const styles = {

  page: {
    minHeight: "100vh",
    background: "#0a0f1a",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    color: "#e2e8f0",
    fontFamily: "monospace"
  },

  card: {
    width: 360,
    padding: 32,
    background: "#0d1424",
    border: "1px solid #1e293b",
    borderRadius: 12,
    textAlign: "center"
  },

  subtitle: {
    color: "#64748b",
    fontSize: 13,
    marginBottom: 25
  },

  input: {
    width: "100%",
    boxSizing: "border-box",
    marginBottom: 12,
    padding: 11,
    background: "#111827",
    border: "1px solid #334155",
    borderRadius: 7,
    color: "#e2e8f0",
    fontFamily: "monospace"
  },

  button: {
    width: "100%",
    padding: 11,
    marginTop: 5,
    background: "#1d4ed8",
    border: "none",
    borderRadius: 7,
    color: "white",
    cursor: "pointer"
  },

  signupButton: {
    background: "transparent",
    border: "1px solid #334155",
    borderRadius: 7,
    padding: "9px 20px",
    color: "#94a3b8",
    cursor: "pointer"
  },

  signupText: {
    color: "#64748b",
    fontSize: 12,
    marginTop: 22
  },

  error: {
    color: "#f87171",
    fontSize: 12,
    marginBottom: 10
  }

};