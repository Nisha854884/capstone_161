import { useState } from "react";
import axios from "axios";

const API = "http://localhost:8000";

export default function Signup({
  onSignupSuccess,
  onLogin
}) {

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSignup(e) {

    e.preventDefault();

    setError("");
    setSuccess("");

    if (!username.trim() || !password || !confirm) {
      setError("Please fill all fields.");
      return;
    }

    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }

    try {

      setLoading(true);

      await axios.post(
        `${API}/auth/signup`,
        {
          username: username.trim(),
          password
        }
      );

      setSuccess(
        "Account created successfully. Please login."
      );

      setTimeout(() => {
        onSignupSuccess();
      }, 1000);

    } catch (err) {

      setError(
        err.response?.data?.detail ||
        "Signup failed."
      );

    } finally {

      setLoading(false);

    }
  }

  return (
    <div style={styles.page}>

      <div style={styles.card}>

        <h1>Create Account</h1>

        <p style={styles.subtitle}>
          Join CyberGuard
        </p>

        <form onSubmit={handleSignup}>

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

          <input
            style={styles.input}
            type="password"
            placeholder="Confirm password"
            value={confirm}
            onChange={e => setConfirm(e.target.value)}
          />

          {error && (
            <div style={styles.error}>
              {error}
            </div>
          )}

          {success && (
            <div style={styles.success}>
              {success}
            </div>
          )}

          <button
            style={styles.button}
            disabled={loading}
          >
            {loading ? "Creating..." : "Create Account"}
          </button>

        </form>

        <button
          style={styles.back}
          onClick={onLogin}
        >
          ← Back to Login
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
    background: "#1d4ed8",
    border: "none",
    borderRadius: 7,
    color: "white",
    cursor: "pointer"
  },

  back: {
    marginTop: 20,
    background: "transparent",
    border: "none",
    color: "#64748b",
    cursor: "pointer"
  },

  error: {
    color: "#f87171",
    fontSize: 12,
    marginBottom: 10
  },

  success: {
    color: "#4ade80",
    fontSize: 12,
    marginBottom: 10
  }

};