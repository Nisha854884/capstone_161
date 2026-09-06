"""
database.py
ChromaDB setup and all database operations.
Persistent storage — data survives app restarts.

Each conversation is stored as a ChromaDB collection named conv_{id}.
Each message stores:
  - 768-dim MuRIL embedding (for semantic similarity search)
  - Full metadata: sender, text, timestamp, all pipeline scores, flagged status
"""

import chromadb
import uuid
from datetime import datetime
from pathlib import Path

# ── Persistent ChromaDB (stores to disk) ─────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent
CHROMA_DIR = BASE_DIR / "chroma_db"
CHROMA_DIR.mkdir(exist_ok=True)

chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
print(f"✅ ChromaDB initialized at {CHROMA_DIR}")


# ─────────────────────────────────────────────────────────────────────────
# COLLECTION HELPERS
# ─────────────────────────────────────────────────────────────────────────
def get_or_create_collection(conversation_id: str):
    """Get existing conversation collection or create a new one."""
    name = f"conv_{conversation_id}"
    try:
        return chroma_client.get_collection(name=name)
    except Exception:
        return chroma_client.create_collection(
            name     = name,
            metadata = {"hnsw:space": "cosine"}
        )


def delete_conversation(conversation_id: str) -> bool:
    """Delete all messages for a conversation. Returns True if deleted."""
    try:
        chroma_client.delete_collection(f"conv_{conversation_id}")
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────
# STORE MESSAGE
# ─────────────────────────────────────────────────────────────────────────
def store_message(
    conversation_id  : str,
    sender_id        : str,
    message_text     : str,
    embedding        : list,
    muril_score      : float = None,
    adjusted_score   : float = 0.0,
    banter_signal    : float = 0.0,
    reciprocity_score: float = 0.0,
    reduction_applied: float = 0.0,
    flagged          : bool  = False
) -> str:
    """
    Store a message with its MuRIL embedding and full pipeline scores.

    Stored metadata per message:
      sender_id          — who sent the message
      text               — message content
      timestamp          — ISO format datetime
      message_number     — sequential position in conversation
      muril_score        — raw MuRIL harmful probability (0 to 1)
      adjusted_score     — final score after signal fusion (0 to 1)
      banter_signal      — emoji/laughter signal strength (0 to 1)
      reciprocity_score  — one-sided vs mutual exchange (0 to 1)
      reduction_applied  — how much the score was reduced (0 to 1)
      flagged            — final flag decision (True/False)
      conversation_id    — which conversation this belongs to

    Returns:
        message_id (UUID string)
    """
    collection     = get_or_create_collection(conversation_id)
    message_id     = str(uuid.uuid4())
    message_number = collection.count() + 1

    collection.add(
        ids        = [message_id],
        embeddings = [embedding],
        metadatas  = [{
            "sender_id"        : sender_id,
            "text"             : message_text,
            "timestamp"        : datetime.now().isoformat(),
            "message_number"   : str(message_number),
            "muril_score": (
                            str(round(muril_score, 4))
                            if muril_score is not None
                            else "None"
                        ),
            "adjusted_score"   : str(round(adjusted_score,     4)),
            "banter_signal"    : str(round(banter_signal,      4)),
            "reciprocity_score": str(round(reciprocity_score,  4)),
            "reduction_applied": str(round(reduction_applied,  4)),
            "flagged"          : str(flagged),
            "conversation_id"  : conversation_id
        }],
        documents = [message_text]
    )

    return message_id


# ─────────────────────────────────────────────────────────────────────────
# FETCH CONVERSATION HISTORY
# ─────────────────────────────────────────────────────────────────────────
def fetch_conversation_history(
    conversation_id: str,
    last_n:          int = 5
) -> list:
    """
    Fetch last N messages from a conversation for pipeline context.

    Returns list ordered oldest to newest:
    [{"sender": str, "text": str, "timestamp": str, "flagged": bool}, ...]
    """
    collection = get_or_create_collection(conversation_id)

    if collection.count() == 0:
        return []

    results = collection.get(include=["metadatas"])

    messages = []
    for meta in results['metadatas']:
        messages.append({
            "sender"   : meta.get('sender_id',  'unknown'),
            "text"     : meta.get('text',        ''),
            "timestamp": meta.get('timestamp',   ''),
            "flagged"  : meta.get('flagged', 'False') == 'True'
        })

    messages.sort(key=lambda x: x['timestamp'])
    return messages[-last_n:]


# ─────────────────────────────────────────────────────────────────────────
# GET ALL MESSAGES (for /db/view endpoint)
# ─────────────────────────────────────────────────────────────────────────
def get_all_messages(conversation_id: str) -> list:
    """
    Returns ALL messages for a conversation with full pipeline metadata.
    Used by the /db/view/{conversation_id} endpoint.
    Sorted by message_number (sequential order).
    """
    collection = get_or_create_collection(conversation_id)

    if collection.count() == 0:
        return []

    results = collection.get(include=["metadatas"])

    messages = []
    for i, meta in enumerate(results['metadatas']):
        messages.append({
            "message_id"       : results['ids'][i],
            "message_number"   : int(meta.get('message_number', i + 1)),
            "sender_id"        : meta.get('sender_id',          'unknown'),
            "text"             : meta.get('text',                ''),
            "timestamp"        : meta.get('timestamp',           ''),
            "muril_score": (
                            float(meta["muril_score"])
                            if meta.get("muril_score") not in [None, "None", ""]
                            else None
                        ),
            "adjusted_score"   : float(meta.get('adjusted_score',      '0.0')),
            "banter_signal"    : float(meta.get('banter_signal',       '0.0')),
            "reciprocity_score": float(meta.get('reciprocity_score',   '0.0')),
            "reduction_applied": float(meta.get('reduction_applied',   '0.0')),
            "flagged"          : meta.get('flagged', 'False') == 'True',
            "conversation_id"  : meta.get('conversation_id', conversation_id)
        })

    messages.sort(key=lambda x: x['message_number'])
    return messages


# ─────────────────────────────────────────────────────────────────────────
# LIST ALL CONVERSATIONS
# ─────────────────────────────────────────────────────────────────────────
def list_all_conversations() -> list:
    """
    Returns a summary of all conversations in the database.
    Used by /db/conversations endpoint.
    Includes participant list and flag rate per conversation.
    """
    collections = chroma_client.list_collections()
    result      = []

    for col in collections:
        if not col.name.startswith("conv_"):
            continue

        conv_id    = col.name.replace("conv_", "", 1)
        collection = chroma_client.get_collection(col.name)
        count      = collection.count()

        if count > 0:
            all_meta     = collection.get(include=["metadatas"])['metadatas']
            flagged      = sum(1 for m in all_meta
                               if m.get('flagged', 'False') == 'True')
            last_ts      = max(m.get('timestamp', '') for m in all_meta)
            participants = sorted(set(
                m.get('sender_id', 'unknown') for m in all_meta
            ))
        else:
            flagged      = 0
            last_ts      = ''
            participants = []

        result.append({
            "conversation_id" : conv_id,
            "total_messages"  : count,
            "flagged_messages": flagged,
            "flag_rate"       : round(flagged / count, 3) if count > 0 else 0.0,
            "participants"    : participants,
            "last_activity"   : last_ts
        })

    result.sort(key=lambda x: x['last_activity'], reverse=True)
    return result


# ─────────────────────────────────────────────────────────────────────────
# GET STATS
# ─────────────────────────────────────────────────────────────────────────
def get_stats() -> dict:
    """Overall database statistics across all conversations."""
    conversations = list_all_conversations()
    total_msgs    = sum(c['total_messages']   for c in conversations)
    total_flagged = sum(c['flagged_messages'] for c in conversations)

    return {
        "total_conversations": len(conversations),
        "total_messages"     : total_msgs,
        "total_flagged"      : total_flagged,
        "flag_rate"          : round(total_flagged / total_msgs, 4)
                               if total_msgs > 0 else 0.0
    }

#ADDED EXTRA FOR LGSTM
# ─────────────────────────────────────────────────────────────────────────
# GLOBAL MEMORY
# ─────────────────────────────────────────────────────────────────────────

GLOBAL_MEMORY_COLLECTION = "global_memory"


def get_global_memory_collection():
    """
    Get or create the Global Memory collection.

    Global Memory stores generalized/anonymized patterns
    that can be used by the Global Model.
    """
    try:
        return chroma_client.get_collection(
            name=GLOBAL_MEMORY_COLLECTION
        )

    except Exception:
        return chroma_client.create_collection(
            name=GLOBAL_MEMORY_COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )


def store_global_pattern(
    embedding: list,
    pattern_text: str,
    label: int,
    confidence: float,
    language: str = "unknown",
    pattern_type: str = "unknown"
) -> str:
    """
    Store a generalized pattern in Global Memory.

    IMPORTANT:
    Do not store user IDs, conversation IDs, or other
    private conversation-specific information here.
    """

    collection = get_global_memory_collection()

    pattern_id = str(uuid.uuid4())

    collection.add(
        ids=[pattern_id],

        embeddings=[embedding],

        documents=[pattern_text],

        metadatas=[{
            "label": str(label),
            "confidence": str(round(confidence, 4)),
            "language": language,
            "pattern_type": pattern_type,
            "timestamp": datetime.now().isoformat()
        }]
    )

    return pattern_id

def search_global_memory(
    embedding: list,
    n_results: int = 5
) -> list:
    """
    Search Global Memory for semantically similar patterns.

    Converts ChromaDB cosine distance into similarity:
        similarity = 1 - distance
    """

    collection = get_global_memory_collection()

    if collection.count() == 0:
        return []

    results = collection.query(
        query_embeddings=[embedding],
        n_results=min(n_results, collection.count()),
        include=[
            "documents",
            "metadatas",
            "distances"
        ]
    )

    patterns = []

    for i in range(len(results["ids"][0])):

        distance = results["distances"][0][i]

        # Chroma cosine distance -> similarity
        similarity = max(
            0.0,
            min(1.0, 1.0 - distance)
        )

        patterns.append({
            "pattern": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": distance,
            "similarity": similarity
        })

    return patterns