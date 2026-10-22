"""
lgs_pipeline.py

Local-Global Split-Memory Transformer (LGS-MT)

Architecture:

                    Current Message
                          |
              +-----------+-----------+
              |                       |
              v                       v
        LOCAL MEMORY            GLOBAL MEMORY
        Conversation            Generalized
        specific                 patterns
              |                       |
              v                       v
        LOCAL MODEL              GLOBAL MODEL
        4-layer MuRIL            12-layer MuRIL
              |                       |
              +-----------+-----------+
                          |
                          v
                    Score Fusion
                          |
                          v
                    Final Decision
"""

"""
lgs_pipeline.py — LGS-MT confidence-based router
"""
from .pipeline import (
    get_local_model_score,
    get_muril_score,
    get_banter_signal,
    get_reciprocity_score,
    get_sentiment_trajectory,
    get_message_embedding,
    get_offensive_signal,
    fuse_scores,
    THRESHOLD,
)

from .memory import search_local_memory, search_global_memory

CONFIDENCE_THRESHOLD = 0.95   # tune this empirically once you have eval data


def local_confidence(local_score: float) -> float:
    """0.0 = totally uncertain (score near 0.5), 1.0 = fully confident."""
    return abs(local_score - 0.5) * 2


def lgs_pipeline(
    conversation_id,
    conversation_history,
    current_message,
    threshold=THRESHOLD
):
    text = current_message["text"]
    full_history = conversation_history + [current_message]
    # ------------------------------------------------------------
    # EXPLICIT OFFENSIVE LANGUAGE
    # ------------------------------------------------------------

    offensive_signal = get_offensive_signal(text)
    # ------------------------------------------------------------
    # 1. ALWAYS-ON LOCAL SIGNALS
    # ------------------------------------------------------------
    local_score = get_local_model_score(
        text,
        conversation_history
    )

    banter = get_banter_signal(
        text,
        conversation_history
    )

    recip, sender_counts = get_reciprocity_score(
        full_history
    )

    traj, sentiments = get_sentiment_trajectory(
        full_history
    )

    # ------------------------------------------------------------
    # 2. LOCAL MEMORY
    # ------------------------------------------------------------
    embedding = get_message_embedding(text)

    local_memories = (
        search_local_memory(
            conversation_id,
            embedding,
            n_results=5
        )
        if conversation_id
        else []
    )

    flagged_local = [
        m for m in local_memories
        if m.get("flagged")
    ]

    local_memory_score = max(
        (
            max(0.0, min(1.0, m.get("similarity", 0.0)))
            for m in flagged_local
        ),
        default=None
    )

    # ------------------------------------------------------------
    # 3. LOCAL MODEL CONFIDENCE
    # ------------------------------------------------------------
    confidence = local_confidence(local_score)

    # ------------------------------------------------------------
    # 4. CONTEXT-AWARE ROUTING
    # ------------------------------------------------------------
    contextual_risk = (
        recip < 0.4
        or traj < 0.25
        or banter >= 0.7
    )

    use_global = (
        confidence < CONFIDENCE_THRESHOLD
        or contextual_risk
    )

    # ------------------------------------------------------------
    # 5. DEFAULT VALUES
    # ------------------------------------------------------------
    global_score = None
    global_memory_score = None
    global_memories = []

    # ------------------------------------------------------------
    # 6. LOCAL-ONLY PATH
    # ------------------------------------------------------------
    if not use_global:

        result = fuse_scores(
            muril_score=local_score,
            local_model_score=local_score,
            banter_signal=banter,
            reciprocity_score=recip,
            trajectory_score=traj,
            local_memory_score=local_memory_score,
            global_memory_score=None,
            history_length=len(conversation_history),
            threshold=threshold,
        )

        source = "local_only"

        router_reason = "high_local_confidence"

    # ------------------------------------------------------------
    # 7. GLOBAL FALLBACK PATH
    # ------------------------------------------------------------
    else:

        global_score = get_muril_score(
            text,
            [
                m.get("text", "")
                if isinstance(m, dict)
                else str(m)
                for m in conversation_history
            ]
        )

        global_memories = search_global_memory(
            embedding,
            n_results=5
        )

        # --------------------------------------------------------
        # GLOBAL MEMORY SCORE
        # --------------------------------------------------------
        harmful_memories = []

        for memory in global_memories:
            label = memory.get("label", 0)
            try:
                label = int(label)
            except (TypeError, ValueError):
                label = 0

            if label == 1:
                harmful_memories.append(memory)

        if harmful_memories:
            similarities = [
                max(0.0, min(1.0, m.get("similarity", 0.0)))
                for m in harmful_memories
            ]
            global_memory_score = max(similarities)
        else:
            global_memory_score = None

        # --------------------------------------------------------
        # FUSE GLOBAL SCORE + OTHER SIGNALS
        # --------------------------------------------------------
        result = fuse_scores(
            muril_score=global_score,
            local_model_score=local_score,
            banter_signal=banter,
            reciprocity_score=recip,
            trajectory_score=traj,
            local_memory_score=local_memory_score,
            global_memory_score=global_memory_score,
            history_length=len(conversation_history),
            threshold=threshold,
        )

        source = "global_fallback"

        if confidence < CONFIDENCE_THRESHOLD:
            router_reason = "low_local_confidence"
        else:
            router_reason = "contextual_risk"

    # ------------------------------------------------------------
    # 8. COMMON RESULT FIELDS
    #
    # IMPORTANT:
    # This is OUTSIDE the if/else.
    # Therefore BOTH paths receive these fields.
    # ------------------------------------------------------------
    result.update({

        "confidence": round(confidence, 4),

        "source": source,

        "local_score": round(
            local_score,
            4
        ),

        "global_score": (
            round(global_score, 4)
            if global_score is not None
            else None
        ),

        "local_memory_score": (
            round(local_memory_score, 4)
            if local_memory_score is not None
            else None
        ),

        "global_memory_score": (
            round(global_memory_score, 4)
            if global_memory_score is not None
            else None
        ),

        "final_score": result["adjusted_score"],

        "threshold": threshold,

        "local_memories": local_memories,

        "global_memories": global_memories,

        "sender_counts": sender_counts,

        "history_length": len(conversation_history),

        "contextual_risk": contextual_risk,

        "router_reason": router_reason,

        "embedding": embedding,

    })

    return result