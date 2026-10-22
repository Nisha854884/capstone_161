import { useEffect, useState } from "react";
import api from "../api";
export default function Admin({ user, onLogout }) {
  const [users, setUsers] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);

  // ==================================================
  // LOAD ADMIN DASHBOARD
  // ==================================================
  useEffect(() => {
    loadDashboard();
  }, []);

  async function loadDashboard() {
    try {
      setLoading(true);

      const [usersResponse, statsResponse] = await Promise.all([
        api.get("/auth/users"),
        api.get("/admin/stats")
      ]);

      setUsers(usersResponse.data.users || []);
      setConversations(statsResponse.data.conversations || []);
      setStats(statsResponse.data || {});

    } catch (error) {
      console.error("Could not load admin dashboard:", error);
    } finally {
      setLoading(false);
    }
  }


  // ==================================================
  // ADD STRIKE
  // ==================================================

  async function addStrike(username) {

    try {

      await api.post(
        `/auth/strike/${username}`
      );

      await loadDashboard();

    } catch (error) {

      console.error(
        "Could not add strike:",
        error
      );

      alert(
        error.response?.data?.detail ||
        "Could not add strike."
      );

    }
  }

  async function resetStrikes(userId) {

    try {

      await api.post(`/auth/reset-strikes/${userId}`);

      await loadDashboard();

    } catch (error) {

      console.error("Could not reset strikes:", error);

      alert(
        error.response?.data?.detail ||
        "Could not reset strikes."
      );

    }
  }

  // ==================================================
  // LOADING
  // ==================================================

  if (loading) {

    return (
      <div style={styles.page}>

        <div style={styles.loading}>
          Loading Admin Dashboard...
        </div>

      </div>
    );

  }


  // ==================================================
  // STATISTICS
  // ==================================================

  const totalUsers = users.length;
  const totalConversations = stats.total_conversations ?? 0;
  const totalMessages = stats.total_messages ?? 0;
  const flaggedMessages = stats.flagged_messages ?? 0;

  const allowedMessages = Math.max(0, totalMessages - flaggedMessages);

  const flagRate =
    totalMessages > 0
      ? (flaggedMessages / totalMessages) * 100
      : 0;


  // ==================================================
  // DASHBOARD
  // ==================================================

  return (

    <div style={styles.page}>

      {/* ==================================================
          HEADER
      ================================================== */}

      <div style={styles.header}>

        <div>

          <h1 style={styles.title}>
            🛡️ CyberGuard Admin
          </h1>

          <p style={styles.subtitle}>
            Logged in as <b>{user.username}</b>
          </p>

        </div>


        <div style={styles.headerButtons}>

          <button
            style={styles.refreshButton}
            onClick={loadDashboard}
          >
            ↻ Refresh
          </button>


          <button
            style={styles.logout}
            onClick={onLogout}
          >
            Logout
          </button>

        </div>

      </div>


      <div style={styles.content}>


        {/* ==================================================
            PRIVACY NOTICE
        ================================================== */}

        <div style={styles.privacyNotice}>

          <div style={styles.privacyTitle}>
            🔒 Privacy-Preserving Moderation
          </div>

          <div style={styles.privacyText}>
            Private chat messages are not displayed on
            the administrator dashboard. Only aggregate
            moderation statistics are shown.
          </div>

        </div>


        {/* ==================================================
            STAT CARDS
        ================================================== */}

        <div style={styles.cards}>

          <div style={styles.card}>

            <div style={styles.cardTitle}>
              Total Users
            </div>

            <div style={styles.cardValue}>
              {totalUsers}
            </div>

          </div>


          <div style={styles.card}>

            <div style={styles.cardTitle}>
              Conversations
            </div>

            <div style={styles.cardValue}>
              {totalConversations}
            </div>

          </div>


          <div style={styles.card}>

            <div style={styles.cardTitle}>
              Total Messages
            </div>

            <div style={styles.cardValue}>
              {totalMessages}
            </div>

          </div>


          <div style={styles.card}>

            <div style={styles.cardTitle}>
              Flagged Messages
            </div>

            <div style={styles.cardValue}>
              {flaggedMessages}
            </div>

          </div>

        </div>


        {/* ==================================================
            MODERATION OVERVIEW
        ================================================== */}

        <section style={styles.section}>

          <div style={styles.sectionHeader}>

            <div>

              <h2 style={styles.sectionTitle}>
                📊 Moderation Overview
              </h2>

              <p style={styles.sectionSubtitle}>
                Aggregate moderation statistics only
              </p>

            </div>

          </div>


          <div style={styles.moderationGrid}>

            <div style={styles.statBox}>

              <div style={styles.statLabel}>
                Allowed Messages
              </div>

              <div style={styles.statNumber}>
                {allowedMessages}
              </div>

            </div>


            <div style={styles.statBox}>

              <div style={styles.statLabel}>
                Flagged Messages
              </div>

              <div style={styles.statNumber}>
                {flaggedMessages}
              </div>

            </div>


            <div style={styles.statBox}>

              <div style={styles.statLabel}>
                Overall Flag Rate
              </div>

              <div style={styles.statNumber}>
                {flagRate.toFixed(1)}%
              </div>

            </div>

          </div>

        </section>


        {/* ==================================================
            USERS TABLE
        ================================================== */}

        <section style={styles.section}>

          <div style={styles.sectionHeader}>

            <div>

              <h2 style={styles.sectionTitle}>
                👥 Users
              </h2>

              <p style={styles.sectionSubtitle}>
                Registered users and moderation strikes
              </p>

            </div>


            <div style={styles.userCount}>
              {users.length} users
            </div>

          </div>


          <div style={styles.tableWrapper}>

            <table style={styles.table}>

              <thead>

                <tr>

                  <th style={styles.th}>
                    User
                  </th>

                  <th style={styles.th}>
                    Role
                  </th>

                  <th style={styles.th}>
                    Strikes
                  </th>

                  <th style={styles.th}>
                    Status
                  </th>

                  <th style={styles.th}>
                    Action
                  </th>

                </tr>

              </thead>


              <tbody>

                {users.map((u) => (

                  <tr
                    key={u.id}
                    style={styles.tableRow}
                  >

                    {/* USER */}

                    <td style={styles.td}>

                      <div style={styles.usernameCell}>

                        <div style={styles.avatar}>
                          {u.username
                            ? u.username
                                .charAt(0)
                                .toUpperCase()
                            : "?"}
                        </div>

                        <div>

                          <div style={styles.username}>
                            {u.username}
                          </div>

                          <div style={styles.userId}>
                            {u.id}
                          </div>

                        </div>

                      </div>

                    </td>


                    {/* ROLE */}

                    <td style={styles.td}>

                      <span
                        style={
                          u.role === "admin"
                            ? styles.adminBadge
                            : styles.userBadge
                        }
                      >
                        {u.role}
                      </span>

                    </td>


                    {/* STRIKES */}

                    <td style={styles.td}>

                      <span
                        style={
                          Number(u.strikes || 0) > 0
                            ? styles.strikeBadge
                            : styles.noStrikeBadge
                        }
                      >
                        {u.strikes || 0}
                      </span>

                    </td>


                    {/* STATUS */}

                    <td style={styles.td}>

                      <span style={styles.activeBadge}>
                        ● Active
                      </span>

                    </td>


                    {/* ACTION */}

                    <td style={styles.td}>

                      {u.role !== "admin" ? (

                        <div style={{ display: "flex", gap: 8 }}>

                          <button
                            style={styles.strikeButton}
                            onClick={() =>
                              addStrike(u.username)
                            }
                          >
                            + Strike
                          </button>
                          
                          <button
                            style={{
                              ...styles.resetButton,
                              opacity: Number(u.strikes || 0) > 0 ? 1 : 0.4,
                              cursor: Number(u.strikes || 0) > 0 ? "pointer" : "not-allowed"
                            }}
                            disabled={Number(u.strikes || 0) === 0}
                            onClick={() => resetStrikes(u.id)}
                          >
                            ↺ Reset
                          </button>
                        </div>

                      ) : (

                        <span style={styles.protectedText}>
                          🔒 Protected
                        </span>

                      )}

                    </td>

                  </tr>

                ))}

              </tbody>

            </table>

          </div>

        </section>


        {/* ==================================================
            CONVERSATIONS TABLE
        ================================================== */}

        <section style={styles.section}>

          <div style={styles.sectionHeader}>

            <div>

              <h2 style={styles.sectionTitle}>
                💬 Conversations
              </h2>

              <p style={styles.sectionSubtitle}>
                Aggregate conversation-level moderation data
              </p>

            </div>

          </div>


          {conversations.length === 0 ? (

            <div style={styles.empty}>
              No conversations yet.
            </div>

          ) : (

            <div style={styles.tableWrapper}>

              <table style={styles.table}>

                <thead>

                  <tr>

                    <th style={styles.th}>
                      Conversation
                    </th>

                    <th style={styles.th}>
                      Messages
                    </th>

                    <th style={styles.th}>
                      Flagged
                    </th>

                    <th style={styles.th}>
                      Flag Rate
                    </th>

                  </tr>

                </thead>


                <tbody>

                  {conversations.map((conversation) => {

                    const messages = Number(conversation.total_messages || 0);
                    const flagged = Number(conversation.flagged_messages || 0);
                    const rate = messages > 0 ? (flagged / messages) * 100 : 0;

                    return (

                      <tr key={conversation.id} style={styles.tableRow}>

                        <td style={styles.td}>
                          <div style={styles.conversationCell}>
                            <span style={styles.chatIcon}>💬</span>
                            <span>{conversation.user1} ↔ {conversation.user2}</span>
                          </div>
                        </td>

                        <td style={styles.td}>{messages}</td>

                        <td style={styles.td}>
                          <span style={flagged > 0 ? styles.flaggedBadge : styles.safeBadge}>
                            {flagged}
                          </span>
                        </td>

                        <td style={styles.td}>
                          <span style={flagged > 0 ? styles.warningRate : styles.safeRate}>
                            {rate.toFixed(1)}%
                          </span>
                        </td>

                      </tr>

                    );

                  })}

                </tbody>

              </table>

            </div>

          )}

        </section>

      </div>

    </div>

  );

}


// ==================================================
// STYLES
// ==================================================

const styles = {

  page: {
    minHeight: "100vh",
    background: "#0a0f1a",
    color: "#e2e8f0",
    fontFamily: "monospace"
  },


  loading: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "#94a3b8"
  },


  header: {
    padding: "20px 35px",
    background: "#0d1424",
    borderBottom: "1px solid #1e293b",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between"
  },


  title: {
    margin: 0,
    fontSize: 24
  },


  subtitle: {
    marginTop: 6,
    color: "#64748b"
  },


  headerButtons: {
    display: "flex",
    gap: 10
  },


  content: {
    maxWidth: 1200,
    margin: "0 auto",
    padding: 30
  },


  privacyNotice: {
    background: "#0f172a",
    border: "1px solid #1e3a5f",
    borderRadius: 10,
    padding: 18,
    marginBottom: 25
  },


  privacyTitle: {
    color: "#60a5fa",
    fontWeight: "bold",
    marginBottom: 6
  },


  privacyText: {
    color: "#94a3b8",
    fontSize: 13,
    lineHeight: 1.6
  },


  cards: {
    display: "grid",
    gridTemplateColumns: "repeat(4, 1fr)",
    gap: 15,
    marginBottom: 25
  },


  card: {
    background: "#111827",
    border: "1px solid #1e293b",
    borderRadius: 10,
    padding: 20
  },


  cardTitle: {
    color: "#64748b",
    fontSize: 13
  },


  cardValue: {
    fontSize: 30,
    fontWeight: "bold",
    marginTop: 8
  },


  section: {
    background: "#0d1424",
    border: "1px solid #1e293b",
    borderRadius: 12,
    marginBottom: 25,
    overflow: "hidden"
  },


  sectionHeader: {
    padding: "18px 22px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    borderBottom: "1px solid #1e293b"
  },


  sectionTitle: {
    margin: 0,
    fontSize: 18,
    color: "#f1f5f9"
  },


  sectionSubtitle: {
    margin: "5px 0 0",
    color: "#64748b",
    fontSize: 12
  },


  userCount: {
    color: "#60a5fa",
    fontSize: 12,
    background: "#172554",
    padding: "6px 10px",
    borderRadius: 6
  },


  moderationGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
    gap: 15,
    padding: 20
  },


  statBox: {
    background: "#111827",
    border: "1px solid #1e293b",
    borderRadius: 8,
    padding: 18
  },


  statLabel: {
    color: "#64748b",
    fontSize: 12,
    marginBottom: 8
  },


  statNumber: {
    fontSize: 24,
    fontWeight: "bold",
    color: "#e2e8f0"
  },


  tableWrapper: {
    width: "100%",
    overflowX: "auto"
  },


  table: {
    width: "100%",
    borderCollapse: "collapse"
  },


  th: {
    textAlign: "left",
    padding: "14px 18px",
    background: "#111827",
    color: "#64748b",
    fontSize: 12,
    fontWeight: "normal",
    borderBottom: "1px solid #1e293b"
  },


  tableRow: {
    borderBottom: "1px solid #1e293b"
  },


  td: {
    padding: "15px 18px",
    fontSize: 13,
    color: "#cbd5e1"
  },


  usernameCell: {
    display: "flex",
    alignItems: "center",
    gap: 12
  },


  avatar: {
    width: 34,
    height: 34,
    borderRadius: "50%",
    background: "#1e3a8a",
    color: "#93c5fd",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: "bold"
  },


  username: {
    color: "#f1f5f9",
    fontWeight: "bold"
  },


  userId: {
    color: "#475569",
    fontSize: 9,
    marginTop: 3,
    maxWidth: 220,
    overflow: "hidden",
    textOverflow: "ellipsis"
  },


  adminBadge: {
    display: "inline-block",
    background: "#3b1d69",
    color: "#c4b5fd",
    padding: "5px 10px",
    borderRadius: 6,
    fontSize: 11
  },


  userBadge: {
    display: "inline-block",
    background: "#172554",
    color: "#60a5fa",
    padding: "5px 10px",
    borderRadius: 6,
    fontSize: 11
  },


  strikeBadge: {
    display: "inline-block",
    background: "#451a03",
    color: "#fbbf24",
    padding: "5px 10px",
    borderRadius: 6,
    fontWeight: "bold"
  },


  noStrikeBadge: {
    display: "inline-block",
    background: "#052e16",
    color: "#4ade80",
    padding: "5px 10px",
    borderRadius: 6
  },


  activeBadge: {
    color: "#4ade80",
    fontSize: 11
  },


  strikeButton: {
    background: "#7f1d1d",
    border: "1px solid #991b1b",
    color: "#fca5a5",
    padding: "7px 11px",
    borderRadius: 6,
    cursor: "pointer",
    fontFamily: "monospace"
  },

  resetButton: {
    background: "#052e16",
    border: "1px solid #166534",
    color: "#4ade80",
    padding: "7px 11px",
    borderRadius: 6,
    fontFamily: "monospace"
  },

  protectedText: {
    color: "#64748b",
    fontSize: 11
  },


  flaggedBadge: {
    display: "inline-block",
    background: "#451a03",
    color: "#fbbf24",
    padding: "5px 9px",
    borderRadius: 6
  },


  safeBadge: {
    display: "inline-block",
    background: "#052e16",
    color: "#4ade80",
    padding: "5px 9px",
    borderRadius: 6
  },


  warningRate: {
    color: "#fbbf24"
  },


  safeRate: {
    color: "#4ade80"
  },


  conversationCell: {
    display: "flex",
    alignItems: "center",
    gap: 10
  },


  chatIcon: {
    fontSize: 16
  },


  empty: {
    padding: 30,
    textAlign: "center",
    color: "#64748b"
  },


  refreshButton: {
    background: "#1d4ed8",
    border: "none",
    color: "white",
    padding: "8px 14px",
    borderRadius: 6,
    cursor: "pointer",
    fontFamily: "monospace"
  },


  logout: {
    background: "transparent",
    border: "1px solid #334155",
    borderRadius: 6,
    color: "#f87171",
    padding: "8px 14px",
    cursor: "pointer",
    fontFamily: "monospace"
  }

};



