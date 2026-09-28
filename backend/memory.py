"""
memory.py

LGS-MT Memory Layer

Local Memory:
    Stores and retrieves conversation-specific information.

Global Memory:
    Stores generalized/anonymized cyberbullying patterns
    shared across conversations.

IMPORTANT:
    Global memory should NOT store raw private conversation
    messages from users.
"""

import chromadb
from pathlib import Path


# ============================================================
# CHROMADB
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_DIR = BASE_DIR / "chroma_db"

chroma_client = chromadb.PersistentClient(
    path=str(CHROMA_DIR)
)


# ============================================================
# LOCAL MEMORY
# ============================================================

def get_local_memory(conversation_id: str):

    collection_name = f"conv_{conversation_id}"

    try:
        return chroma_client.get_collection(
            name=collection_name
        )
    except Exception:

        return chroma_client.create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

def get_existing_local_memory(conversation_id: str):
    """Get an existing conversation memory without creating one."""

    collection_name = f"conv_{conversation_id}"

    try:
        return chroma_client.get_collection(
            name=collection_name
        )
    except Exception:
        return None

def search_local_memory(
    conversation_id: str,
    query_embedding: list,
    n_results: int = 5
):

    collection = get_existing_local_memory(conversation_id)

    if collection is None:
        return []

    if collection.count() == 0:
        return []

    n_results = min(
        n_results,
        collection.count()
    )

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=[
            "metadatas",
            "documents",
            "distances"
        ]
    )

    memories = []

    for i in range(len(results["ids"][0])):

        metadata = results["metadatas"][0][i]

        memories.append({
            "text": results["documents"][0][i],
            "sender": metadata.get(
                "sender_id",
                "unknown"
            ),
            "timestamp": metadata.get(
                "timestamp",
                ""
            ),
            "flagged": metadata.get(
                "flagged",
                "False"
            ) == "True",
            "similarity": 1.0 - results["distances"][0][i]
        })

    return memories


# ============================================================
# GLOBAL MEMORY
# ============================================================

GLOBAL_COLLECTION_NAME = "global_memory"


def get_global_memory():

    try:

        return chroma_client.get_collection(
            name=GLOBAL_COLLECTION_NAME
        )

    except Exception:

        return chroma_client.create_collection(
            name=GLOBAL_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )


def add_global_pattern(
    pattern_id: str,
    embedding: list,
    label: int,
    pattern_type: str = "cyberbullying"
):

    collection = get_global_memory()

    collection.add(
        ids=[pattern_id],
        embeddings=[embedding],
        metadatas=[{
            "label": str(label),
            "pattern_type": pattern_type
        }]
    )


def search_global_memory(
    query_embedding: list,
    n_results: int = 5
):

    collection = get_global_memory()

    if collection.count() == 0:
        return []

    n_results = min(
        n_results,
        collection.count()
    )

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=[
            "metadatas",
            "distances"
        ]
    )

    memories = []

    for i in range(len(results["ids"][0])):

        metadata = results["metadatas"][0][i]

        memories.append({
            "label": int(
                metadata.get("label", 0)
            ),
            "pattern_type": metadata.get(
                "pattern_type",
                "unknown"
            ),
            "similarity":
                1.0 - results["distances"][0][i]
        })

    return memories