import { useEffect, useState } from "react";

import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Chat from "./pages/Chat";
import api from "./api";
import Admin from "./pages/Admin";

export default function App() {

  const savedUser = localStorage.getItem("user");

  const [user, setUser] = useState(
    savedUser ? JSON.parse(savedUser) : null
  );

  const [page, setPage] = useState(() => {

    if (!savedUser) {
      return "login";
    }

    const saved = JSON.parse(savedUser);

    return saved.role === "admin"
      ? "admin"
      : "friends";
  });

  // Friends
  const [friends, setFriends] = useState([]);

  // People who can receive a request
  const [availableUsers, setAvailableUsers] = useState([]);

  // Incoming requests
  const [requests, setRequests] = useState([]);

  const [selectedUser, setSelectedUser] = useState(null);

  const [loadingFriends, setLoadingFriends] = useState(false);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [loadingRequests, setLoadingRequests] = useState(false);


  // ==================================================
  // LOAD FRIEND DATA
  // ==================================================

  useEffect(() => {

    if (!user || user.role === "admin") {
      return;
    }

    loadFriendData();

  }, [user]);


  async function loadFriendData() {

    await Promise.all([
      loadFriends(),
      loadAvailableUsers(),
      loadRequests()
    ]);

  }


  // ==================================================
  // LOAD FRIENDS
  // ==================================================

  async function loadFriends() {

    try {

      setLoadingFriends(true);

      const response = await api.get("/friends");

      setFriends(
        response.data.friends || []
      );

    } catch (error) {

      console.error(
        "Could not load friends:",
        error
      );

    } finally {

      setLoadingFriends(false);

    }
  }


  // ==================================================
  // LOAD AVAILABLE USERS
  // ==================================================

  async function loadAvailableUsers() {

    try {

      setLoadingUsers(true);

      const response = await api.get(
        "/friends/available"
      );

      setAvailableUsers(
        response.data.users || []
      );

    } catch (error) {

      console.error(
        "Could not load available users:",
        error
      );

    } finally {

      setLoadingUsers(false);

    }
  }


  // ==================================================
  // LOAD FRIEND REQUESTS
  // ==================================================

  async function loadRequests() {

    try {

      setLoadingRequests(true);

      const response = await api.get(
        "/friends/requests"
      );

      setRequests(
        response.data.requests || []
      );

    } catch (error) {

      console.error(
        "Could not load friend requests:",
        error
      );

    } finally {

      setLoadingRequests(false);

    }
  }


  // ==================================================
  // SEND FRIEND REQUEST
  // ==================================================

  async function sendFriendRequest(userId) {

    try {

      await api.post(
        `/friends/request/${userId}`
      );

      alert("Friend request sent!");

      await loadFriendData();

    } catch (error) {

      console.error(
        "Could not send friend request:",
        error
      );

      alert(
        error.response?.data?.detail ||
        "Could not send friend request."
      );

    }
  }


  // ==================================================
  // ACCEPT FRIEND REQUEST
  // ==================================================

  async function acceptRequest(requestId) {

    try {

      await api.post(
        `/friends/accept/${requestId}`
      );

      await loadFriendData();

    } catch (error) {

      console.error(
        "Could not accept friend request:",
        error
      );

      alert(
        error.response?.data?.detail ||
        "Could not accept friend request."
      );

    }
  }


  // ==================================================
  // REJECT FRIEND REQUEST
  // ==================================================

  async function rejectRequest(requestId) {

    try {

      await api.post(
        `/friends/reject/${requestId}`
      );

      await loadFriendData();

    } catch (error) {

      console.error(
        "Could not reject friend request:",
        error
      );

      alert(
        error.response?.data?.detail ||
        "Could not reject friend request."
      );

    }
  }


  // ==================================================
  // LOGIN
  // ==================================================

  function handleLogin(loggedInUser) {

    setUser(loggedInUser);

    localStorage.setItem(
      "user",
      JSON.stringify(loggedInUser)
    );

    if (loggedInUser.role === "admin") {
      setPage("admin");
    } else {
      setPage("friends");
    }
  }


  // ==================================================
  // LOGOUT
  // ==================================================

  function logout() {

    localStorage.removeItem("token");
    localStorage.removeItem("user");

    setUser(null);

    setFriends([]);
    setAvailableUsers([]);
    setRequests([]);
    setSelectedUser(null);

    setPage("login");
  }


  // ==================================================
  // LOGIN PAGE
  // ==================================================

  if (!user && page === "login") {

    return (
      <Login
        onLogin={handleLogin}
        onSignup={() => setPage("signup")}
      />
    );
  }


  // ==================================================
  // SIGNUP PAGE
  // ==================================================

  if (!user && page === "signup") {

    return (
      <Signup
        onSignupSuccess={() => setPage("login")}
        onLogin={() => setPage("login")}
      />
    );
  }


  // ==================================================
  // FRIENDS PAGE
  // ==================================================

  if (user && page === "friends") {

    return (

      <div style={styles.page}>

        <div style={styles.container}>

          {/* ================= HEADER ================= */}

          <div style={styles.topBar}>

            <div style={styles.logo}>
              🛡️ <b>CyberGuard</b>
            </div>

            <div style={styles.loggedIn}>
              Logged in as{" "}
              <b>{user.username}</b>
            </div>

            <button
              style={styles.logout}
              onClick={logout}
            >
              Logout
            </button>

          </div>


          <div style={styles.content}>

            {/* ================= TITLE ================= */}

            <div style={styles.pageHeader}>

              <div>

                <h2 style={styles.title}>
                  Friends
                </h2>

                <p style={styles.subtitle}>
                  Chat only with users who have accepted
                  your friend request.
                </p>

              </div>

              <button
                style={styles.refreshButton}
                onClick={loadFriendData}
              >
                ↻ Refresh
              </button>

            </div>


            {/* =================================================
                FRIEND REQUESTS
            ================================================= */}

            <section style={styles.section}>

              <div style={styles.sectionHeader}>

                <div>

                  <h3 style={styles.sectionTitle}>
                    📨 Friend Requests
                  </h3>

                  <p style={styles.sectionSubtitle}>
                    Requests waiting for your response
                  </p>

                </div>

                {requests.length > 0 && (

                  <span style={styles.requestCount}>
                    {requests.length}
                  </span>

                )}

              </div>


              {loadingRequests ? (

                <p style={styles.muted}>
                  Loading requests...
                </p>

              ) : requests.length === 0 ? (

                <div style={styles.emptyBox}>
                  <div style={styles.emptyIcon}>
                    ✓
                  </div>

                  <div>
                    <b>No pending requests</b>

                    <p style={styles.muted}>
                      New friend requests will appear here.
                    </p>
                  </div>
                </div>

              ) : (

                <div>

                  {requests.map((request) => (

                    <div
                      key={request.id}
                      style={styles.requestCard}
                    >

                      <div style={styles.userInfo}>

                        <div style={styles.avatar}>
                          {request.username
                            ?.charAt(0)
                            .toUpperCase()}
                        </div>

                        <div>

                          <div style={styles.username}>
                            {request.username}
                          </div>

                          <div style={styles.requestText}>
                            Wants to be your friend
                          </div>

                        </div>

                      </div>


                      <div style={styles.requestActions}>

                        <button
                          style={styles.acceptButton}
                          onClick={() =>
                            acceptRequest(request.id)
                          }
                        >
                          ✓ Accept
                        </button>

                        <button
                          style={styles.rejectButton}
                          onClick={() =>
                            rejectRequest(request.id)
                          }
                        >
                          ✕ Reject
                        </button>

                      </div>

                    </div>

                  ))}

                </div>

              )}

            </section>


            {/* =================================================
                FRIENDS
            ================================================= */}

            <section style={styles.section}>

              <div style={styles.sectionHeader}>

                <div>

                  <h3 style={styles.sectionTitle}>
                    👥 My Friends
                  </h3>

                  <p style={styles.sectionSubtitle}>
                    People you can chat with
                  </p>

                </div>

                <span style={styles.friendCount}>
                  {friends.length} friend
                  {friends.length !== 1 ? "s" : ""}
                </span>

              </div>


              {loadingFriends ? (

                <p style={styles.muted}>
                  Loading friends...
                </p>

              ) : friends.length === 0 ? (

                <div style={styles.emptyBox}>

                  <div style={styles.emptyIcon}>
                    👥
                  </div>

                  <div>

                    <b>You don't have any friends yet.</b>

                    <p style={styles.muted}>
                      Find users below and send them a
                      friend request.
                    </p>

                  </div>

                </div>

              ) : (

                <div style={styles.userList}>

                  {friends.map((friend) => (

                    <div
                      key={friend.id}
                      style={styles.friendCard}
                    >

                      <div style={styles.userInfo}>

                        <div style={styles.avatar}>
                          {friend.username
                            ?.charAt(0)
                            .toUpperCase()}
                        </div>

                        <div>

                          <div style={styles.username}>
                            {friend.username}
                          </div>

                          <div style={styles.onlineText}>
                            ● Friend
                          </div>

                        </div>

                      </div>


                      <button
                        style={styles.chatButton}
                        onClick={() => {

                          setSelectedUser(friend);
                          setPage("chat");

                        }}
                      >
                        💬 Chat
                      </button>

                    </div>

                  ))}

                </div>

              )}

            </section>


            {/* =================================================
                FIND PEOPLE
            ================================================= */}

            <section style={styles.section}>

              <div style={styles.sectionHeader}>

                <div>

                  <h3 style={styles.sectionTitle}>
                    🔎 Find People
                  </h3>

                  <p style={styles.sectionSubtitle}>
                    Send a friend request to start connecting
                  </p>

                </div>

              </div>


              {loadingUsers ? (

                <p style={styles.muted}>
                  Loading users...
                </p>

              ) : availableUsers.length === 0 ? (

                <div style={styles.emptyBox}>

                  <div style={styles.emptyIcon}>
                    🔎
                  </div>

                  <div>

                    <b>No new users available</b>

                    <p style={styles.muted}>
                      You've already sent requests to,
                      or are friends with, all available users.
                    </p>

                  </div>

                </div>

              ) : (

                <div style={styles.userList}>

                  {availableUsers.map((person) => (

                    <div
                      key={person.id}
                      style={styles.userCard}
                    >

                      <div style={styles.userInfo}>

                        <div style={styles.avatar}>
                          {person.username
                            ?.charAt(0)
                            .toUpperCase()}
                        </div>

                        <div>

                          <div style={styles.username}>
                            {person.username}
                          </div>

                          <div style={styles.onlineText}>
                            Available to connect
                          </div>

                        </div>

                      </div>


                      <button
                        style={styles.addButton}
                        onClick={() =>
                          sendFriendRequest(person.id)
                        }
                      >
                        + Add Friend
                      </button>

                    </div>

                  ))}

                </div>

              )}

            </section>

          </div>

        </div>

      </div>
    );
  }


  // ==================================================
  // CHAT PAGE
  // ==================================================

  if (
    user &&
    page === "chat" &&
    selectedUser
  ) {

    return (

      <div>

        <div style={styles.chatTopBar}>

          <button
            style={styles.backButton}
            onClick={() => {

              setSelectedUser(null);
              setPage("friends");

            }}
          >
            ← Friends
          </button>


          <span>
            {user.username}
            {" → "}
            {selectedUser.username}
          </span>


          <button
            style={styles.logout}
            onClick={logout}
          >
            Logout
          </button>

        </div>


        <Chat
          currentUser={user}
          otherUser={selectedUser}
        />

      </div>
    );
  }


  // ==================================================
  // ADMIN
  // ==================================================

  if (user && page === "admin") {

    return (
      <Admin
        user={user}
        onLogout={logout}
      />
    );
  }


  return null;
}


// ==================================================
// STYLES
// ==================================================

const styles = {

  page: {
    minHeight: "100vh",
    background: "#0a0f1a",
    color: "#e2e8f0",
    fontFamily: "monospace",
    padding: "30px 0"
  },

  container: {
    width: "92%",
    maxWidth: 1000,
    margin: "0 auto",
    background: "#0d1424",
    border: "1px solid #1e293b",
    borderRadius: 14,
    overflow: "hidden"
  },

  topBar: {
    padding: "18px 24px",
    background: "#111827",
    borderBottom: "1px solid #1e293b",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 20
  },

  logo: {
    fontSize: 17,
    color: "#e2e8f0"
  },

  loggedIn: {
    color: "#64748b",
    fontSize: 13
  },

  content: {
    padding: 30
  },

  pageHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 25
  },

  title: {
    margin: 0,
    fontSize: 25
  },

  subtitle: {
    color: "#64748b",
    marginTop: 7,
    fontSize: 13
  },

  refreshButton: {
    background: "#1e293b",
    border: "1px solid #334155",
    borderRadius: 7,
    color: "#94a3b8",
    padding: "9px 14px",
    cursor: "pointer",
    fontFamily: "monospace"
  },

  section: {
    background: "#0f172a",
    border: "1px solid #1e293b",
    borderRadius: 10,
    padding: 20,
    marginBottom: 20
  },

  sectionHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 15
  },

  sectionTitle: {
    margin: 0,
    fontSize: 17,
    color: "#e2e8f0"
  },

  sectionSubtitle: {
    margin: "5px 0 0",
    color: "#64748b",
    fontSize: 12
  },

  friendCount: {
    color: "#60a5fa",
    fontSize: 12
  },

  requestCount: {
    background: "#2563eb",
    color: "white",
    minWidth: 25,
    height: 25,
    borderRadius: 20,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 12,
    fontWeight: "bold"
  },

  userList: {
    display: "flex",
    flexDirection: "column",
    gap: 10
  },

  userCard: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "14px 16px",
    background: "#111827",
    border: "1px solid #1e293b",
    borderRadius: 8
  },

  friendCard: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "14px 16px",
    background: "#111827",
    border: "1px solid #1e293b",
    borderRadius: 8
  },

  requestCard: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "14px 16px",
    background: "#111827",
    border: "1px solid #1e293b",
    borderRadius: 8,
    marginBottom: 10
  },

  userInfo: {
    display: "flex",
    alignItems: "center",
    gap: 12
  },

  avatar: {
    width: 40,
    height: 40,
    borderRadius: "50%",
    background: "#1e293b",
    border: "1px solid #334155",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "#60a5fa",
    fontWeight: "bold",
    fontSize: 16
  },

  username: {
    color: "#e2e8f0",
    fontSize: 14,
    fontWeight: "bold"
  },

  onlineText: {
    color: "#64748b",
    fontSize: 11,
    marginTop: 4
  },

  requestText: {
    color: "#64748b",
    fontSize: 11,
    marginTop: 4
  },

  addButton: {
    background: "#1d4ed8",
    border: "1px solid #2563eb",
    borderRadius: 7,
    color: "white",
    padding: "8px 13px",
    cursor: "pointer",
    fontFamily: "monospace",
    fontSize: 12
  },

  chatButton: {
    background: "#0f766e",
    border: "1px solid #14b8a6",
    borderRadius: 7,
    color: "white",
    padding: "8px 14px",
    cursor: "pointer",
    fontFamily: "monospace",
    fontSize: 12
  },

  requestActions: {
    display: "flex",
    gap: 8
  },

  acceptButton: {
    background: "#166534",
    border: "1px solid #22c55e",
    borderRadius: 7,
    color: "#dcfce7",
    padding: "8px 12px",
    cursor: "pointer",
    fontFamily: "monospace",
    fontSize: 12
  },

  rejectButton: {
    background: "transparent",
    border: "1px solid #7f1d1d",
    borderRadius: 7,
    color: "#f87171",
    padding: "8px 12px",
    cursor: "pointer",
    fontFamily: "monospace",
    fontSize: 12
  },

  emptyBox: {
    display: "flex",
    alignItems: "center",
    gap: 14,
    padding: 18,
    background: "#111827",
    border: "1px dashed #334155",
    borderRadius: 8
  },

  emptyIcon: {
    fontSize: 22
  },

  muted: {
    color: "#64748b",
    fontSize: 12,
    margin: "5px 0"
  },

  logout: {
    background: "transparent",
    border: "1px solid #334155",
    borderRadius: 6,
    color: "#f87171",
    padding: "7px 12px",
    cursor: "pointer",
    fontFamily: "monospace"
  },

  chatTopBar: {
    height: 55,
    padding: "0 20px",
    background: "#0d1424",
    borderBottom: "1px solid #1e293b",
    color: "#94a3b8",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    fontFamily: "monospace"
  },

  backButton: {
    background: "transparent",
    border: "1px solid #334155",
    borderRadius: 6,
    color: "#94a3b8",
    padding: "6px 12px",
    cursor: "pointer",
    fontFamily: "monospace"
  }
};

