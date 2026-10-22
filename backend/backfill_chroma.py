# Run from the project root with the backend STOPPED:
# .\venv\Scripts\python.exe -m backend.backfill_chroma

from .chat import get_connection
from .database import chroma_client, get_or_create_collection
from .pipeline import get_message_embedding


def rebuild():

    conn = get_connection()

    conversations = conn.execute(
        "SELECT id FROM conversations"
    ).fetchall()

    total = 0

    for conv in conversations:

        conv_id = conv["id"]

        messages = conn.execute(
            """
            SELECT id, sender_id, message, flagged, score, created_at
            FROM chat_messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            """,
            (conv_id,)
        ).fetchall()

        if not messages:
            continue

        # wipe and rebuild so reruns never create duplicates
        try:
            chroma_client.delete_collection(f"conv_{conv_id}")
        except Exception:
            pass

        collection = get_or_create_collection(conv_id)

        for i, m in enumerate(messages, start=1):

            collection.add(
                ids=[m["id"]],
                embeddings=[get_message_embedding(m["message"])],
                documents=[m["message"]],
                metadatas=[{
                    "sender_id": m["sender_id"],
                    "text": m["message"],
                    "timestamp": m["created_at"],
                    "message_number": str(i),
                    "muril_score": "None",
                    "adjusted_score": str(round(m["score"] or 0.0, 4)),
                    "banter_signal": "0.0",
                    "reciprocity_score": "0.0",
                    "reduction_applied": "0.0",
                    "flagged": str(bool(m["flagged"])),
                    "conversation_id": conv_id
                }]
            )

            total += 1

        print(f"conv {conv_id[:8]}: {len(messages)} messages")

    conn.close()

    print(f"Done. {total} messages stored in ChromaDB.")


if __name__ == "__main__":
    rebuild()