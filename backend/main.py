"""
main.py
FastAPI backend for the cyberbullying detection app.

Run with:
    uvicorn main:app --reload --port 8000

Endpoints:
    POST /classify          — classify a message
    GET  /db/conversations  — list all conversations
    GET  /db/view/{id}      — view all messages in a conversation
    GET  /db/stats          — overall database statistics
    DELETE /db/{id}         — delete a conversation
    GET  /health            — health check
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# Import pipeline and database
# These are loaded once when the server starts
from .lgs_pipeline import lgs_pipeline
from .pipeline import THRESHOLD
from .pipeline import get_message_embedding
from .database import (
    store_message,
    fetch_conversation_history,
    get_all_messages,
    list_all_conversations,
    delete_conversation,
    get_stats
)

# ── FastAPI app ───────────────────────────────────────────────────────────
app = FastAPI(
    title       = "Cyberbullying Detection API",
    description = "Context-aware cyberbullying detection using MuRIL + "
                  "reciprocity analysis + sentiment trajectory",
    version     = "1.0.0"
)

# ── CORS — allow React frontend to call this API ──────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:3000",
                         "http://localhost:5173"],  # React dev servers
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


# ─────────────────────────────────────────────────────────────────────────
# REQUEST / RESPONSE MODELS
# ─────────────────────────────────────────────────────────────────────────
class ClassifyRequest(BaseModel):
    conversation_id : str
    sender_id       : str
    message         : str
    threshold       : Optional[float] = THRESHOLD
    history_limit   : Optional[int]   = 5

    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "conv_001",
                "sender_id"      : "user_A",
                "message"        : "you're so dumb 😂",
                "threshold"      : 0.7,
                "history_limit"  : 5
            }
        }


class ClassifyResponse(BaseModel):

    # Final decision
    flagged: bool
    label: int
    adjusted_score: float
    action: str

    # LGS-MT information
    signals: dict

    # Routing / memory information
    moderation: dict

    # Original message
    message: dict


@app.post("/classify", response_model=ClassifyResponse)
async def classify_message(req: ClassifyRequest):
    """
    Classify a message using the LGS-MT architecture.

    Flow:
    1. Fetch recent conversation history
    2. Run Local model
    3. Calculate local confidence
    4. If confident -> local-only path
    5. Otherwise -> global model + global memory fallback
    6. Store the message
    7. Return the complete LGS-MT result
    """

    # ============================================================
    # STEP 1 — FETCH CONVERSATION HISTORY
    # ============================================================

    history = fetch_conversation_history(
        req.conversation_id,
        last_n=req.history_limit
    )

    # ============================================================
    # STEP 2 — BUILD CURRENT MESSAGE
    # ============================================================

    current_message = {
        "sender": req.sender_id,
        "text": req.message
    }

    # ============================================================
    # STEP 3 — RUN LGS-MT
    # ============================================================

    result = lgs_pipeline(
        conversation_id=req.conversation_id,
        conversation_history=history,
        current_message=current_message,
        threshold=req.threshold
    )

    # ============================================================
    # STEP 4 — STORE MESSAGE
    # ============================================================

    embedding = get_message_embedding(req.message)

    store_message(
        conversation_id=req.conversation_id,
        sender_id=req.sender_id,
        message_text=req.message,
        embedding=embedding,

        # Global model score.
        # None when local-only path was used.
        muril_score=result.get("global_score"),

        adjusted_score=result["final_score"],

        banter_signal=result.get(
            "banter_signal",
            0.0
        ),

        reciprocity_score=result.get(
            "reciprocity_score",
            0.5
        ),

        reduction_applied=result.get(
            "reduction_applied",
            0.0
        ),

        flagged=result["flagged"]
    )

    # ============================================================
    # STEP 5 — RETURN RESPONSE
    # ============================================================

    return ClassifyResponse(

        flagged=result["flagged"],

        label=result["label"],

        adjusted_score=result["final_score"],

        action=(
            "flag"
            if result["flagged"]
            else "allow"
        ),

        # --------------------------------------------------------
        # SIGNALS
        # --------------------------------------------------------

        signals={

            "local_score": result.get(
                "local_score"
            ),

            "global_score": result.get(
                "global_score"
            ),

            "local_memory_score": result.get(
                "local_memory_score"
            ),

            "global_memory_score": result.get(
                "global_memory_score"
            ),

            "banter_signal": result.get(
                "banter_signal"
            ),

            "reciprocity_score": result.get(
                "reciprocity_score"
            ),

            "trajectory_score": result.get(
                "trajectory_score"
            ),

            "reduction_applied": result.get(
                "reduction_applied"
            ),

            "confidence": result.get(
                "confidence"
            )
        },

        # --------------------------------------------------------
        # MODERATION
        # --------------------------------------------------------

        moderation={

            "source": result.get(
                "source"
            ),

            "threshold_used": req.threshold,

            "history_used": result.get(
                "history_length",
                len(history)
            ),

            "sender_counts": str(
                result.get(
                    "sender_counts",
                    {}
                )
            ),

            "local_memories_retrieved": len(
                result.get(
                    "local_memories",
                    []
                )
            ),

            "global_memories_retrieved": len(
                result.get(
                    "global_memories",
                    []
                )
            )
        },

        # --------------------------------------------------------
        # MESSAGE
        # --------------------------------------------------------

        message={

            "conversation_id":
                req.conversation_id,

            "sender_id":
                req.sender_id,

            "text":
                req.message
        }
    )

# ─────────────────────────────────────────────────────────────────────────
# DATABASE VIEW ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────
@app.get("/db/conversations")
async def get_conversations():
    """
    List all conversations with message counts and flag counts.
    Open http://localhost:8000/db/conversations in your browser to see this.
    """
    conversations = list_all_conversations()
    return {
        "total"        : len(conversations),
        "conversations": conversations
    }


@app.get("/db/view/{conversation_id}")
async def view_conversation(conversation_id: str):
    """
    View ALL messages in a conversation with full metadata.
    Open http://localhost:8000/db/view/conv_001 in your browser.

    Shows:
    - Every message text
    - Who sent it
    - When it was sent
    - MuRIL score
    - Adjusted score after fusion
    - Whether it was flagged
    """
    messages = get_all_messages(conversation_id)

    if not messages:
        return {
            "conversation_id": conversation_id,
            "total"          : 0,
            "flagged"        : 0,
            "messages"       : []
        }

    flagged_count = sum(1 for m in messages if m['flagged'])

    return {
        "conversation_id": conversation_id,
        "total"          : len(messages),
        "flagged"        : flagged_count,
        "flag_rate"      : round(flagged_count / len(messages), 3),
        "messages"       : messages
    }


@app.get("/db/stats")
async def database_stats():
    """
    Overall database statistics.
    Open http://localhost:8000/db/stats in your browser.
    """
    return get_stats()


@app.delete("/db/{conversation_id}")
async def clear_conversation(conversation_id: str):
    """Delete all messages for a conversation."""
    deleted = delete_conversation(conversation_id)
    if deleted:
        return {"message": f"Conversation {conversation_id} deleted"}
    raise HTTPException(status_code=404,
                        detail=f"Conversation {conversation_id} not found")


# ─────────────────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    """Quick ping to confirm the server is running."""
    return {
        "status" : "ok",
        "model"  : "muril-base-cased",
        "device" : "cuda" if __import__('torch').cuda.is_available()
                   else "cpu"
    }


# ─────────────────────────────────────────────────────────────────────────
# ROOT
# ─────────────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "message"  : "Cyberbullying Detection API",
        "docs"     : "http://localhost:8000/docs",
        "endpoints": {
            "classify"     : "POST /classify",
            "conversations": "GET  /db/conversations",
            "view_conv"    : "GET  /db/view/{conversation_id}",
            "stats"        : "GET  /db/stats",
            "health"       : "GET  /health"
        }
    }