import sqlite3
import uuid
from datetime import datetime, timezone
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "users.db")
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------------------------------------------------
# CHAT TABLES
# ---------------------------------------------------------
def init_chat_db():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user1_id TEXT NOT NULL,
            user2_id TEXT NOT NULL,
            created_at TEXT NOT NULL,

            UNIQUE(user1_id, user2_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            sender_id TEXT NOT NULL,
            receiver_id TEXT NOT NULL,
            message TEXT NOT NULL,
            flagged INTEGER NOT NULL DEFAULT 0,
            score REAL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
# ---------------------------------------------------------
# CONVERSATION
# ---------------------------------------------------------
def get_or_create_conversation(user1_id: str, user2_id: str):
    # Always store IDs in the same order
    # so A-B and B-A are the same conversation.
    first, second = sorted([user1_id, user2_id])
    conn = get_connection()
    row = conn.execute("""
        SELECT *
        FROM conversations
        WHERE user1_id = ?
        AND user2_id = ?
    """, (first, second)).fetchone()
    if row:
        conn.close()
        return dict(row)
    conversation_id = str(uuid.uuid4())
    conn.execute("""
        INSERT INTO conversations
        (id, user1_id, user2_id, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        conversation_id,
        first,
        second,
        datetime.now(timezone.utc).isoformat()
    ))
    conn.commit()

    row = conn.execute("""
        SELECT *
        FROM conversations
        WHERE id = ?
    """, (conversation_id,)).fetchone()
    conn.close()
    return dict(row)
# ---------------------------------------------------------
# SAVE MESSAGE
# ---------------------------------------------------------

def save_chat_message(
    conversation_id,
    sender_id,
    receiver_id,
    message,
    flagged=False,
    score=0
):

    conn = get_connection()

    message_id = str(uuid.uuid4())

    conn.execute("""
        INSERT INTO chat_messages
        (
            id,
            conversation_id,
            sender_id,
            receiver_id,
            message,
            flagged,
            score,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        message_id,
        conversation_id,
        sender_id,
        receiver_id,
        message,
        int(flagged),
        float(score),
        datetime.now(timezone.utc).isoformat()
    ))

    conn.commit()
    conn.close()

    return {
        "id": message_id,
        "conversation_id": conversation_id,
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "message": message,
        "flagged": flagged,
        "score": score
    }


# ---------------------------------------------------------
# GET MESSAGES
# ---------------------------------------------------------

def get_chat_messages(conversation_id):

    conn = get_connection()

    rows = conn.execute("""
        SELECT
            id,
            conversation_id,
            sender_id,
            receiver_id,
            message,
            flagged,
            score,
            created_at
        FROM chat_messages
        WHERE conversation_id = ?
        ORDER BY created_at ASC
    """, (conversation_id,)).fetchall()

    conn.close()
    messages=[dict(row) for row in rows]
    for m in messages:
        m["flagged"]=bool(m["flagged"])
    return messages

def get_admin_stats():
    """Aggregate moderation stats from SQLite. No message content."""

    conn = get_connection()

    rows = conn.execute("""
        SELECT
            c.id,
            u1.username AS user1,
            u2.username AS user2,
            COUNT(m.id) AS total_messages,
            COALESCE(SUM(m.flagged), 0) AS flagged_messages,
            MAX(m.created_at) AS last_activity
        FROM conversations c
        LEFT JOIN users u1 ON u1.id = c.user1_id
        LEFT JOIN users u2 ON u2.id = c.user2_id
        LEFT JOIN chat_messages m ON m.conversation_id = c.id
        GROUP BY c.id
        HAVING COUNT(m.id) > 0
        ORDER BY last_activity DESC
    """).fetchall()

    conn.close()

    conversations = [dict(r) for r in rows]

    return {
        "total_conversations": len(conversations),
        "total_messages": sum(c["total_messages"] for c in conversations),
        "flagged_messages": sum(c["flagged_messages"] for c in conversations),
        "conversations": conversations
    }
