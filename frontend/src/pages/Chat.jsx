import { useEffect, useState } from "react";
import api from "../api";

export default function Chat({ currentUser, otherUser }) {

  const [conversationId, setConversationId] = useState(null);
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modal, setModal] = useState(null);
  const [otherRestricted, setOtherRestricted] = useState(false);

  // --------------------------------------------------
  // GET / CREATE CONVERSATION
  // --------------------------------------------------

  useEffect(() => {

    if (!currentUser || !otherUser) {
      return;
    }

    async function createConversation() {

      try {

        const response = await api.get(
          `/chat/conversation/${otherUser.id}`
        );

        setConversationId(
          response.data.conversation.id
        );

      } catch (error) {

        console.error(
          "Could not create/load conversation:",
          error
        );

      }

    }

    createConversation();

  }, [currentUser, otherUser]);


  // --------------------------------------------------
  // LOAD MESSAGES
  // --------------------------------------------------

  async function loadMessages() {

    if (!conversationId) {
      return;
    }

    try {

      const [msgRes, statusRes] = await Promise.all([
        api.get(`/chat/${conversationId}`),
        api.get(`/chat/status/${otherUser.id}`)
      ]);

      setMessages(msgRes.data.messages || []);
      setOtherRestricted(statusRes.data.restricted);

    } catch (error) {

      console.error("Could not load messages:", error);

    }
  }


  useEffect(() => {

    if (!conversationId) {
      return;
    }

    loadMessages();

    const interval = setInterval(
      loadMessages,
      2000
    );

    return () => clearInterval(interval);

  }, [conversationId]);

  const [strikes, setStrikes] = useState(0);
  const STRIKE_LIMIT = 3;
  const restricted = strikes >= STRIKE_LIMIT;

  useEffect(() => {
    async function loadStrikes() {
      try {
        const res = await api.get("/auth/me");
        setStrikes(res.data.strikes || 0);
      } catch (error) {
        console.error("Could not load strikes:", error);
      }
    }
    loadStrikes();
  }, []);

  useEffect(() => {
    if (restricted) {
      setModal({ type: "restricted", strikes });
    }
  }, [restricted]);

  useEffect(() => {
    if (otherRestricted && !restricted) {
      setModal({ type: "other_blocked", strikes: 0 });
    }
  }, [otherRestricted]);

  // --------------------------------------------------
  // SEND MESSAGE
  // --------------------------------------------------

  async function sendMessage(e) {

    e.preventDefault();

    if (!message.trim() || !conversationId || restricted || otherRestricted) {
      return;
    }

    try {

      setLoading(true);

      const res = await api.post("/chat/send", {
        conversation_id: conversationId,
        receiver_id: otherUser.id,
        message: message.trim()
      });

      const mod = res.data.moderation;
      setStrikes(mod.strikes);

      if (mod.restricted) {
        setModal({ type: "restricted", strikes: mod.strikes });
      } else if (mod.flagged) {
        setModal({ type: "warning", strikes: mod.strikes });
      }

      setMessage("");

      await loadMessages();

    } catch (error) {

      console.error(
        "Message failed:",
        error
      );

      const detail = error.response?.data?.detail || "";

      if (error.response?.status === 403 && detail.includes("other user has been blocked")) {
        setOtherRestricted(true);
        setModal({ type: "other_blocked", strikes: 0 });
      } else if (error.response?.status === 403 && detail.toLowerCase().includes("restricted")) {
        setStrikes(STRIKE_LIMIT);
        setModal({ type: "restricted", strikes: STRIKE_LIMIT });
      } else {
        alert(detail || "Could not send message.");
      }

    } finally {

      setLoading(false);

    }

  }


  // --------------------------------------------------
  // SAFETY CHECK
  // --------------------------------------------------

  if (!currentUser || !otherUser) {

    return (
      <div style={styles.page}>
        <div style={styles.empty}>
          Select a user to start chatting.
        </div>
      </div>
    );

  }

  const chatLocked = restricted || otherRestricted;

  const modalConfig = {
    warning: {
      icon: "⚠️",
      title: "Message flagged",
      text: "Your last message was flagged as potentially harmful. Please keep conversations respectful.",
      border: "#78350f",
      button: "#b45309",
      dot: "#fb923c",
      label: "Got it",
      showStrikes: true
    },
    restricted: {
      icon: "🔒",
      title: "Account restricted",
      text: "You have reached 3 strikes for harmful messages, so you can no longer send messages. Contact an admin if you think this is a mistake.",
      border: "#7f1d1d",
      button: "#991b1b",
      dot: "#f87171",
      label: "Understood",
      showStrikes: true
    },
    other_blocked: {
      icon: "🚫",
      title: "Chat unavailable",
      text: `${otherUser.username} has been blocked, so you can't chat with them anymore.`,
      border: "#334155",
      button: "#1d4ed8",
      dot: "#334155",
      label: "OK",
      showStrikes: false
    }
  };

  const cfg = modal ? modalConfig[modal.type] : null;


  // --------------------------------------------------
  // UI
  // --------------------------------------------------

  return (
    <div style={styles.page}>

      <div style={styles.chatBox}>

        <div style={styles.header}>

          <strong>
            🛡️ CyberGuard Chat
          </strong>

          <div style={styles.subHeader}>
            {currentUser.username} → {otherUser.username}
            {"  "}
            <span style={{ color: chatLocked ? "#f87171" : strikes > 0 ? "#fb923c" : "#64748b" }}>
              {restricted
                ? "🔒 Restricted"
                : otherRestricted
                ? "🚫 Chat closed"
                : `${strikes}/${STRIKE_LIMIT} strikes`}
            </span>
          </div>

        </div>


        <div style={styles.messages}>

          {messages.length === 0 && (
            <div style={styles.empty}>
              No messages yet.
            </div>
          )}


          {messages.map((msg) => {

            const isMine =
              msg.sender_id === currentUser.id;

            const flagged =
              msg.flagged === true;

            return (

              <div
                key={msg.id}
                style={{
                  ...styles.messageRow,
                  justifyContent: isMine
                    ? "flex-end"
                    : "flex-start"
                }}
              >

                <div
                  style={{
                    ...styles.message,

                    background: isMine
                      ? "#1d4ed8"
                      : "#1e293b",

                    border: flagged
                      ? "1px solid #ef4444"
                      : "1px solid transparent"
                  }}
                >

                  <div style={styles.sender}>
                    {isMine
                      ? "You"
                      : otherUser.username}
                  </div>

                  <div>
                    {msg.message}
                  </div>

                  {flagged && (
                    <div style={styles.warning}>
                      ⚠️ Flagged by AI
                    </div>
                  )}

                </div>

              </div>

            );

          })}

        </div>


        <form
          onSubmit={sendMessage}
          style={styles.inputArea}
        >

          <input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={
              restricted
                ? "Restricted: too many violations"
                : otherRestricted
                ? `${otherUser.username} was blocked, so this chat is closed`
                : "Type a message..."
            }
            disabled={chatLocked}
            style={{ ...styles.input, opacity: chatLocked ? 0.5 : 1 }}
          />

          <button
            type="submit"
            disabled={loading || !conversationId || chatLocked}
            style={{ ...styles.button, opacity: chatLocked ? 0.5 : 1 }}
          >
            {loading ? "..." : "Send"}
          </button>

        </form>

      </div>
      
      {modal && cfg && (
        <div style={styles.overlay} onClick={() => setModal(null)}>

          <div
            style={{ ...styles.modal, borderColor: cfg.border }}
            onClick={(e) => e.stopPropagation()}
          >

            <div style={styles.modalIcon}>{cfg.icon}</div>

            <h2 style={styles.modalTitle}>{cfg.title}</h2>

            <p style={styles.modalText}>{cfg.text}</p>

            {cfg.showStrikes && (
              <div style={styles.modalStrikes}>
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    style={{
                      ...styles.modalDot,
                      background: i < modal.strikes ? cfg.dot : "#334155"
                    }}
                  />
                ))}
                <span style={styles.modalStrikeText}>
                  {modal.strikes}/{STRIKE_LIMIT} strikes
                </span>
              </div>
            )}

            <button
              style={{ ...styles.modalButton, background: cfg.button }}
              onClick={() => setModal(null)}
            >
              {cfg.label}
            </button>

          </div>

        </div>
      )}

    </div>
  );
}


const styles = {

  page: {
    minHeight: "100vh",
    background: "#0a0f1a",
    color: "#e2e8f0",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    fontFamily: "monospace"
  },

  chatBox: {
    width: 650,
    height: 650,
    background: "#0d1424",
    border: "1px solid #1e293b",
    borderRadius: 12,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden"
  },

  header: {
    padding: 18,
    borderBottom: "1px solid #1e293b",
    background: "#111827"
  },

  subHeader: {
    color: "#64748b",
    fontSize: 12,
    marginTop: 5
  },

  messages: {
    flex: 1,
    padding: 20,
    overflowY: "auto"
  },

  messageRow: {
    display: "flex",
    marginBottom: 12
  },

  message: {
    maxWidth: "70%",
    padding: 10,
    borderRadius: 9,
    fontSize: 14
  },

  sender: {
    fontSize: 10,
    color: "#94a3b8",
    marginBottom: 5
  },

  warning: {
    color: "#f87171",
    fontSize: 10,
    marginTop: 6
  },

  empty: {
    textAlign: "center",
    color: "#64748b",
    marginTop: 50
  },

  inputArea: {
    display: "flex",
    padding: 15,
    borderTop: "1px solid #1e293b"
  },

  input: {
    flex: 1,
    padding: 12,
    background: "#111827",
    border: "1px solid #334155",
    borderRadius: 7,
    color: "#e2e8f0",
    fontFamily: "monospace"
  },

  button: {
    marginLeft: 10,
    padding: "0 20px",
    background: "#1d4ed8",
    border: "none",
    borderRadius: 7,
    color: "white",
    cursor: "pointer"
  },

  overlay: {
    position: "fixed",
    inset: 0,
    background: "rgba(2, 6, 15, 0.75)",
    backdropFilter: "blur(3px)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1000,
    animation: "fadeIn 0.2s ease"
  },

  modal: {
    width: 380,
    maxWidth: "90%",
    background: "#0d1424",
    border: "1px solid #78350f",
    borderRadius: 14,
    padding: "30px 28px",
    textAlign: "center",
    boxShadow: "0 20px 60px rgba(0, 0, 0, 0.6)"
  },

  modalIcon: {
    fontSize: 38,
    marginBottom: 10
  },

  modalTitle: {
    margin: "0 0 10px",
    fontSize: 20,
    color: "#f1f5f9"
  },

  modalText: {
    margin: "0 0 20px",
    color: "#94a3b8",
    fontSize: 13,
    lineHeight: 1.6
  },

  modalStrikes: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    marginBottom: 22
  },

  modalDot: {
    width: 10,
    height: 10,
    borderRadius: "50%"
  },

  modalStrikeText: {
    marginLeft: 6,
    fontSize: 12,
    color: "#64748b"
  },

  modalButton: {
    width: "100%",
    padding: 11,
    border: "none",
    borderRadius: 8,
    color: "white",
    cursor: "pointer",
    fontFamily: "monospace",
    fontSize: 13
  }
};
