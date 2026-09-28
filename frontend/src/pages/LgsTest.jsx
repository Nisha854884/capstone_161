import { useState, useRef, useEffect } from "react";
import axios from "axios";

const API = "http://localhost:8000";

// ── Conversation ID — shared between both users ───────────────────────────
const CONVERSATION_ID = "conv_demo_001";

// ── Strike system thresholds ──────────────────────────────────────────────
const STRIKE_WARNING    = 1;
const STRIKE_RESTRICT   = 3;

export default function App() {
  const [messages,    setMessages]    = useState([]);
  const [inputA,      setInputA]      = useState("");
  const [inputB,      setInputB]      = useState("");
  const [strikesA,    setStrikesA]    = useState(0);
  const [strikesB,    setStrikesB]    = useState(0);
  const [loadingA,    setLoadingA]    = useState(false);
  const [loadingB,    setLoadingB]    = useState(false);
  const [dbMessages,  setDbMessages]  = useState([]);
  const [showDb,      setShowDb]      = useState(false);
  const [dbLoading,   setDbLoading]   = useState(false);
  const [stats,       setStats]       = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Send a message ────────────────────────────────────────────────────
  async function sendMessage(sender) {
    const text  = sender === "A" ? inputA.trim() : inputB.trim();
    const setLoading = sender === "A" ? setLoadingA : setLoadingB;
    const setInput   = sender === "A" ? setInputA   : setInputB;

    if (!text) return;
    if (sender === "A" && strikesA >= STRIKE_RESTRICT) return;
    if (sender === "B" && strikesB >= STRIKE_RESTRICT) return;

    setLoading(true);
    setInput("");

    // Optimistic message while API runs
    const tempId = Date.now();
    setMessages(prev => [...prev, {
      id: tempId, sender, text,
      flagged: null, score: null,
      signals: null, pending: true
    }]);

    try {
      const res = await axios.post(`${API}/classify`, {
        conversation_id: CONVERSATION_ID,
        sender_id      : `user_${sender}`,
        message        : text,
        threshold      : 0.7,
        history_limit  : 5
      });

      const r = res.data;

      // Update message with result
      setMessages(prev => prev.map(m =>
        m.id === tempId ? {
          ...m,
          flagged : r.flagged,
          score   : r.adjusted_score,
          signals : r.signals,
          action  : r.action,
          pending : false
        } : m
      ));

      // Update strikes
      if (r.flagged) {
        if (sender === "A") setStrikesA(s => s + 1);
        else                setStrikesB(s => s + 1);
      }

    } catch (err) {
      setMessages(prev => prev.map(m =>
        m.id === tempId ? { ...m, error: true, pending: false } : m
      ));
    } finally {
      setLoading(false);
    }
  }

  // ── Fetch DB view ─────────────────────────────────────────────────────
  async function fetchDb() {
    setDbLoading(true);
    try {
      const [dbRes, statsRes] = await Promise.all([
        axios.get(`${API}/db/view/${CONVERSATION_ID}`),
        axios.get(`${API}/db/stats`)
      ]);
      setDbMessages(dbRes.data.messages || []);
      setStats(statsRes.data);
      setShowDb(true);
    } catch (e) {
      alert("Could not fetch DB — is the server running?");
    } finally {
      setDbLoading(false);
    }
  }

  // ── Clear conversation ────────────────────────────────────────────────
  async function clearConversation() {
    try {
      await axios.delete(`${API}/db/${CONVERSATION_ID}`);
      setMessages([]);
      setStrikesA(0);
      setStrikesB(0);
      setDbMessages([]);
      setShowDb(false);
    } catch (e) {
      // Conversation might not exist yet, just clear UI
      setMessages([]);
      setStrikesA(0);
      setStrikesB(0);
    }
  }

  const restrictedA = strikesA >= STRIKE_RESTRICT;
  const restrictedB = strikesB >= STRIKE_RESTRICT;

  return (
    <div style={styles.root}>
      {/* ── Header ─────────────────────────────────────────────────── */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <div style={styles.logo}>🛡️</div>
          <div>
            <div style={styles.headerTitle}>CyberGuard</div>
            <div style={styles.headerSub}>Context-aware bullying detection</div>
          </div>
        </div>
        <div style={styles.headerRight}>
          <button style={styles.btnOutline}
                  onClick={fetchDb} disabled={dbLoading}>
            {dbLoading ? "Loading…" : "📊 View DB"}
          </button>
          <button style={{...styles.btnOutline, color: "#f87171"}}
                  onClick={clearConversation}>
            🗑 Clear
          </button>
        </div>
      </header>

      <div style={styles.body}>
        {/* ── Chat Panel ─────────────────────────────────────────── */}
        <div style={styles.chatPanel}>

          {/* User labels + strikes */}
          <div style={styles.userRow}>
            <UserBadge name="User A" strikes={strikesA}
                       restricted={restrictedA} side="left" />
            <div style={styles.vsLabel}>vs</div>
            <UserBadge name="User B" strikes={strikesB}
                       restricted={restrictedB} side="right" />
          </div>

          {/* Messages */}
          <div style={styles.messageArea}>
            {messages.length === 0 && (
              <div style={styles.emptyState}>
                <div style={styles.emptyIcon}>💬</div>
                <div style={styles.emptyText}>
                  Start a conversation below.<br />
                  <span style={styles.emptyHint}>
                    Try some friendly banter — or actual bullying — and
                    watch the system decide.
                  </span>
                </div>
              </div>
            )}

            {messages.map(msg => (
              <MessageBubble key={msg.id} msg={msg} />
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Input row */}
          <div style={styles.inputRow}>
            <InputPanel
              label="User A"
              value={inputA}
              onChange={setInputA}
              onSend={() => sendMessage("A")}
              loading={loadingA}
              restricted={restrictedA}
              strikes={strikesA}
              side="left"
            />
            <InputPanel
              label="User B"
              value={inputB}
              onChange={setInputB}
              onSend={() => sendMessage("B")}
              loading={loadingB}
              restricted={restrictedB}
              strikes={strikesB}
              side="right"
            />
          </div>
        </div>

        {/* ── DB Panel ───────────────────────────────────────────── */}
        {showDb && (
          <div style={styles.dbPanel}>
            <div style={styles.dbHeader}>
              <div style={styles.dbTitle}>📦 ChromaDB View</div>
              <button style={styles.closeBtn}
                      onClick={() => setShowDb(false)}>✕</button>
            </div>

            {stats && (
              <div style={styles.statsRow}>
                {[
                  ["Conversations", stats.total_conversations],
                  ["Messages",      stats.total_messages],
                  ["Flagged",       stats.total_flagged],
                  ["Flag rate",     `${(stats.flag_rate*100).toFixed(1)}%`]
                ].map(([k,v]) => (
                  <div key={k} style={styles.statBox}>
                    <div style={styles.statVal}>{v}</div>
                    <div style={styles.statKey}>{k}</div>
                  </div>
                ))}
              </div>
            )}

            <div style={styles.dbList}>
              {dbMessages.length === 0
                ? <div style={styles.dbEmpty}>No messages stored yet.</div>
                : dbMessages.map(m => (
                    <div key={m.message_id}
                         style={{
                           ...styles.dbRow,
                           borderLeft: `3px solid ${m.flagged
                             ? "#f87171" : "#4ade80"}`
                         }}>
                      <div style={styles.dbRowTop}>
                        <span style={styles.dbSender}>{m.sender_id}</span>
                        <span style={{
                          ...styles.dbFlag,
                          background: m.flagged ? "#f871711a" : "#4ade801a",
                          color:      m.flagged ? "#f87171"   : "#4ade80"
                        }}>
                          {m.flagged ? "🚨 FLAGGED" : "✅ safe"}
                        </span>
                        <span style={styles.dbTime}>
                          {new Date(m.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      <div style={styles.dbText}>{m.text}</div>
                      <div style={styles.dbScores}>
                        <ScorePill label="MuRIL"    val={m.muril_score} />
                        <ScorePill label="Adjusted" val={m.adjusted_score}
                                   highlight />
                      </div>
                    </div>
                  ))
              }
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────

function UserBadge({ name, strikes, restricted, side }) {
  const align = side === "left" ? "flex-start" : "flex-end";
  return (
    <div style={{ display:"flex", flexDirection:"column",
                  alignItems: align, gap: 4 }}>
      <div style={styles.userName}>{name}</div>
      <div style={styles.strikeRow}>
        {[0,1,2].map(i => (
          <div key={i} style={{
            ...styles.strikeDot,
            background: i < strikes
              ? (strikes >= STRIKE_RESTRICT ? "#f87171" : "#fb923c")
              : "#334155"
          }} />
        ))}
        <span style={{
          ...styles.strikeLabel,
          color: strikes >= STRIKE_RESTRICT ? "#f87171"
               : strikes >= STRIKE_WARNING  ? "#fb923c" : "#64748b"
        }}>
          {strikes >= STRIKE_RESTRICT ? "🔒 Restricted"
           : strikes >= STRIKE_WARNING ? "⚠️ Warning"
           : `${strikes}/3 strikes`}
        </span>
      </div>
    </div>
  );
}

function MessageBubble({ msg }) {
  const isA    = msg.sender === "A";
  const align  = isA ? "flex-start" : "flex-end";
  const bg     = msg.flagged    ? "#3b0d0d"
               : msg.pending    ? "#1e293b"
               : msg.error      ? "#1c1917"
               : isA            ? "#1e3a5f"
               :                  "#1a3a2e";
  const border = msg.flagged ? "1px solid #f8717166"
               : msg.pending ? "1px solid #334155"
               :               "1px solid transparent";

  return (
    <div style={{ display:"flex", justifyContent: align,
                  marginBottom: 12, animation: "fadeIn 0.2s ease" }}>
      <div style={{ maxWidth:"65%", display:"flex",
                    flexDirection:"column",
                    alignItems: isA ? "flex-start" : "flex-end" }}>

        <div style={{ fontSize:11, color:"#64748b",
                      marginBottom:3, paddingLeft:4 }}>
          User {msg.sender}
        </div>

        <div style={{ background: bg, border, borderRadius: isA
                        ? "4px 16px 16px 16px"
                        : "16px 4px 16px 16px",
                      padding: "10px 14px", color: "#e2e8f0",
                      fontSize: 14, lineHeight: 1.5 }}>
          {msg.text}
        </div>

        {/* Score + signals */}
        {!msg.pending && !msg.error && msg.score !== null && (
          <div style={{ marginTop:6, display:"flex",
                        flexWrap:"wrap", gap:4,
                        justifyContent: isA ? "flex-start" : "flex-end" }}>
            <div style={{
              ...styles.scoreBadge,
              background: msg.flagged ? "#f8717122" : "#4ade8022",
              color:      msg.flagged ? "#f87171"   : "#4ade80",
              border:     `1px solid ${msg.flagged ? "#f87171" : "#4ade80"}44`
            }}>
              {msg.flagged ? "🚨" : "✅"} {msg.flagged ? "Flagged" : "Safe"}
              &nbsp;·&nbsp;{(msg.score*100).toFixed(0)}%
            </div>

            {msg.signals && (
              <>
                <SignalPill label="MuRIL"
                            val={msg.signals.muril_score} />
                <SignalPill label="banter"
                            val={msg.signals.banter_signal} invert />
                <SignalPill label="recip"
                            val={msg.signals.reciprocity_score} invert />
                <SignalPill label="−reduc"
                            val={msg.signals.reduction_applied} invert />
              </>
            )}
          </div>
        )}

        {msg.pending && (
          <div style={{ fontSize:11, color:"#64748b", marginTop:4 }}>
            analysing…
          </div>
        )}
        {msg.error && (
          <div style={{ fontSize:11, color:"#f87171", marginTop:4 }}>
            API error
          </div>
        )}
      </div>
    </div>
  );
}

function SignalPill({ label, val, invert }) {
  // invert = higher is safer (banter, reciprocity, reduction)
  const pct   = Math.round(val * 100);
  const color = invert
    ? (val > 0.5 ? "#4ade80" : val > 0.2 ? "#fb923c" : "#94a3b8")
    : (val > 0.7 ? "#f87171" : val > 0.4 ? "#fb923c" : "#4ade80");
  return (
    <div style={{ fontSize:10, color, background: color + "15",
                  border: `1px solid ${color}30`,
                  borderRadius:4, padding:"1px 6px" }}>
      {label} {pct}%
    </div>
  );
}

function ScorePill({ label, val, highlight }) {
  const color = highlight
    ? (val >= 0.7 ? "#f87171" : val >= 0.5 ? "#fb923c" : "#4ade80")
    : "#94a3b8";
  return (
    <span style={{ fontSize:10, color,
                   background: color + "15",
                   borderRadius:4, padding:"1px 6px",
                   border: `1px solid ${color}30` }}>
      {label} {(val*100).toFixed(0)}%
    </span>
  );
}

function InputPanel({ label, value, onChange, onSend, loading,
                       restricted, strikes, side }) {
  const borderColor = restricted ? "#f87171"
                    : strikes >= STRIKE_WARNING ? "#fb923c" : "#334155";

  function handleKey(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  }

  return (
    <div style={{ flex:1, display:"flex", flexDirection:"column", gap:6 }}>
      <div style={{ fontSize:11, color:"#64748b",
                    textAlign: side === "right" ? "right" : "left" }}>
        {label} {restricted ? "🔒" : ""}
      </div>
      <div style={{ display:"flex", gap:6 }}>
        <input
          style={{
            ...styles.input,
            borderColor,
            opacity: restricted ? 0.5 : 1,
            cursor:  restricted ? "not-allowed" : "text"
          }}
          placeholder={
            restricted
              ? "Restricted — too many violations"
              : `${label} message… (Enter to send)`
          }
          value={value}
          onChange={e => onChange(e.target.value)}
          onKeyDown={handleKey}
          disabled={restricted || loading}
        />
        <button
          style={{
            ...styles.sendBtn,
            opacity: (restricted || loading || !value.trim()) ? 0.4 : 1,
            cursor:  (restricted || loading || !value.trim())
                      ? "not-allowed" : "pointer"
          }}
          onClick={onSend}
          disabled={restricted || loading || !value.trim()}
        >
          {loading ? "…" : "Send"}
        </button>
      </div>
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────
const styles = {
  root: {
    minHeight:"100vh", background:"#0a0f1a",
    color:"#e2e8f0", fontFamily:"'DM Mono', 'Fira Code', monospace",
    display:"flex", flexDirection:"column"
  },
  header: {
    display:"flex", alignItems:"center",
    justifyContent:"space-between",
    padding:"14px 24px",
    borderBottom:"1px solid #1e293b",
    background:"#0d1424"
  },
  headerLeft: { display:"flex", alignItems:"center", gap:12 },
  logo: { fontSize:28 },
  headerTitle: { fontSize:18, fontWeight:700,
                  letterSpacing:"0.02em", color:"#f1f5f9" },
  headerSub: { fontSize:11, color:"#64748b", marginTop:1 },
  headerRight: { display:"flex", gap:8 },
  btnOutline: {
    background:"transparent", border:"1px solid #334155",
    color:"#94a3b8", padding:"6px 14px", borderRadius:6,
    cursor:"pointer", fontSize:12, fontFamily:"inherit"
  },
  body: {
    display:"flex", flex:1, gap:0, overflow:"hidden"
  },
  chatPanel: {
    flex:1, display:"flex", flexDirection:"column",
    minWidth:0, padding:"0 0 16px 0"
  },
  userRow: {
    display:"flex", justifyContent:"space-between",
    alignItems:"flex-start", padding:"16px 24px 8px",
    borderBottom:"1px solid #1e293b"
  },
  vsLabel: {
    fontSize:11, color:"#334155", alignSelf:"center",
    letterSpacing:"0.1em"
  },
  userName: { fontSize:13, fontWeight:600, color:"#cbd5e1" },
  strikeRow: { display:"flex", alignItems:"center", gap:4 },
  strikeDot: { width:8, height:8, borderRadius:"50%",
                transition:"background 0.3s" },
  strikeLabel: { fontSize:10, marginLeft:4 },
  messageArea: {
    flex:1, overflowY:"auto", padding:"16px 24px",
    display:"flex", flexDirection:"column"
  },
  emptyState: {
    flex:1, display:"flex", flexDirection:"column",
    alignItems:"center", justifyContent:"center",
    textAlign:"center", color:"#334155", paddingTop:60
  },
  emptyIcon: { fontSize:40, marginBottom:12, opacity:0.4 },
  emptyText: { fontSize:14, lineHeight:1.7 },
  emptyHint: { fontSize:12, color:"#1e293b" },
  scoreBadge: {
    fontSize:11, padding:"2px 8px", borderRadius:4,
    fontWeight:600
  },
  inputRow: {
    display:"flex", gap:12, padding:"12px 24px 0",
    borderTop:"1px solid #1e293b"
  },
  input: {
    flex:1, background:"#111827", border:"1px solid #334155",
    borderRadius:8, padding:"9px 12px", color:"#e2e8f0",
    fontSize:13, fontFamily:"inherit", outline:"none",
    transition:"border-color 0.2s"
  },
  sendBtn: {
    background:"#1d4ed8", color:"#fff", border:"none",
    borderRadius:8, padding:"9px 18px", fontFamily:"inherit",
    fontSize:13, fontWeight:600, transition:"opacity 0.2s"
  },
  // DB panel
  dbPanel: {
    width:380, borderLeft:"1px solid #1e293b",
    background:"#0d1424", display:"flex",
    flexDirection:"column", overflow:"hidden"
  },
  dbHeader: {
    display:"flex", justifyContent:"space-between",
    alignItems:"center", padding:"14px 16px",
    borderBottom:"1px solid #1e293b"
  },
  dbTitle: { fontSize:13, fontWeight:600, color:"#94a3b8" },
  closeBtn: {
    background:"transparent", border:"none", color:"#64748b",
    cursor:"pointer", fontSize:16, fontFamily:"inherit"
  },
  statsRow: {
    display:"grid", gridTemplateColumns:"1fr 1fr 1fr 1fr",
    gap:1, background:"#1e293b", borderBottom:"1px solid #1e293b"
  },
  statBox: {
    background:"#0d1424", padding:"10px 8px",
    textAlign:"center"
  },
  statVal: { fontSize:18, fontWeight:700, color:"#f1f5f9" },
  statKey: { fontSize:9, color:"#64748b", marginTop:2,
              textTransform:"uppercase", letterSpacing:"0.05em" },
  dbList: { flex:1, overflowY:"auto", padding:12,
             display:"flex", flexDirection:"column", gap:8 },
  dbEmpty: { color:"#334155", fontSize:13, textAlign:"center",
              paddingTop:40 },
  dbRow: {
    background:"#111827", borderRadius:6,
    padding:"10px 12px", display:"flex",
    flexDirection:"column", gap:6
  },
  dbRowTop: { display:"flex", alignItems:"center",
               gap:8, flexWrap:"wrap" },
  dbSender: { fontSize:11, color:"#94a3b8", fontWeight:600 },
  dbFlag: { fontSize:10, padding:"2px 6px", borderRadius:3 },
  dbTime: { fontSize:10, color:"#475569", marginLeft:"auto" },
  dbText: { fontSize:13, color:"#e2e8f0", lineHeight:1.5 },
  dbScores: { display:"flex", gap:6 }
};