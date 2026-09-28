import { useEffect, useState } from "react";
import api from "../api";

export default function Chat({ currentUser, otherUser }) {

  const [conversationId, setConversationId] = useState(null);
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

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

      const response = await api.get(
        `/chat/${conversationId}`
      );

      setMessages(
        response.data.messages || []
      );

    } catch (error) {

      console.error(
        "Could not load messages:",
        error
      );

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


  // --------------------------------------------------
  // SEND MESSAGE
  // --------------------------------------------------

  async function sendMessage(e) {

    e.preventDefault();

    if (!message.trim() || !conversationId) {
      return;
    }

    try {

      setLoading(true);

      await api.post(
        "/chat/send",
        {
          conversation_id: conversationId,
          receiver_id: otherUser.id,
          message: message.trim()
        }
      );

      setMessage("");

      await loadMessages();

    } catch (error) {

      console.error(
        "Message failed:",
        error
      );

      alert(
        error.response?.data?.detail ||
        "Could not send message."
      );

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
            onChange={(e) =>
              setMessage(e.target.value)
            }
            placeholder="Type a message..."
            style={styles.input}
          />

          <button
            type="submit"
            disabled={loading || !conversationId}
            style={styles.button}
          >
            {loading ? "..." : "Send"}
          </button>

        </form>

      </div>

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
  }
};
