"""
main.py
FastAPI backend for the CyberGuard / LGS-MT cyberbullying detection app.

Run from the backend folder:
    uvicorn main:app --reload --port 8000
"""

from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import torch

# -------------------------------------------------------------------
# LGS-MT / DATABASE IMPORTS
# -------------------------------------------------------------------

from .lgs_pipeline import lgs_pipeline

from .pipeline import (
    THRESHOLD,
    get_message_embedding
)

from .database import (
    store_message,
    fetch_conversation_history,
    get_all_messages,
    list_all_conversations,
    delete_conversation,
    get_stats
)

from .chat import (
    init_chat_db,
    get_or_create_conversation,
    save_chat_message,
    get_chat_messages
)

# -------------------------------------------------------------------
# AUTH IMPORTS
# -------------------------------------------------------------------

from .auth import (
    init_auth_db,
    create_user,
    authenticate_user,
    create_token,
    decode_token,
    get_user,
    get_all_users,
    add_strike,
    send_friend_request,
    get_pending_requests,
    accept_friend_request,
    reject_friend_request,
    get_friends,
    get_available_users,
    are_friends
)


# ===================================================================
# FASTAPI APP
# ===================================================================

app = FastAPI(
    title="CyberGuard - Cyberbullying Detection API",
    description=(
        "Context-aware cyberbullying detection using "
        "LGS-MT, MuRIL, local/global memory, "
        "reciprocity analysis and sentiment trajectory."
    ),
    version="1.0.0",
)


# ===================================================================
# INITIALIZE DATABASES
# ===================================================================

init_auth_db()
init_chat_db()


# ===================================================================
# AUTHENTICATION
# ===================================================================

security = HTTPBearer()


def require_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token."
        )

    user = get_user(payload["sub"])

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found."
        )

    return user


# ===================================================================
# CORS
# ===================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===================================================================
# REQUEST MODELS
# ===================================================================

class SignupRequest(BaseModel):
    username: str
    password: str
    role: str = "user"


class LoginRequest(BaseModel):
    username: str
    password: str


class ClassifyRequest(BaseModel):
    conversation_id: str
    sender_id: str
    message: str
    threshold: Optional[float] = THRESHOLD
    history_limit: Optional[int] = 5


class SendMessageRequest(BaseModel):
    conversation_id: str
    receiver_id: str
    message: str


# ===================================================================
# RESPONSE MODEL
# ===================================================================

class ClassifyResponse(BaseModel):
    flagged: bool
    label: int
    adjusted_score: float
    action: str

    signals: dict
    moderation: dict
    message: dict


# ===================================================================
# AUTHENTICATION ENDPOINTS
# ===================================================================

@app.post("/auth/signup")
async def signup(req: SignupRequest):

    username = req.username.strip()

    if not username:
        raise HTTPException(
            status_code=400,
            detail="Username is required."
        )

    if not req.password:
        raise HTTPException(
            status_code=400,
            detail="Password is required."
        )

    # Frontend registrations are always normal users.
    role = "user"

    try:

        user = create_user(
            username=username,
            password=req.password,
            role=role
        )

        if not user:
            raise HTTPException(
                status_code=400,
                detail="Username already exists."
            )

        return {
            "success": True,
            "message": "Account created successfully.",
            "user": user
        }

    except HTTPException:
        raise

    except Exception as e:

        error_text = str(e).lower()

        if "exist" in error_text or "unique" in error_text:
            raise HTTPException(
                status_code=400,
                detail="Username already exists."
            )

        raise HTTPException(
            status_code=500,
            detail=f"Could not create account: {str(e)}"
        )


@app.post("/auth/login")
async def login(req: LoginRequest):

    username = req.username.strip()

    if not username or not req.password:
        raise HTTPException(
            status_code=400,
            detail="Username and password are required."
        )

    user = authenticate_user(
        username=username,
        password=req.password
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password."
        )

    token = create_token(user)

    return {
        "success": True,
        "message": "Login successful.",
        "token": token,
        "user": user
    }


@app.get("/auth/me")
async def current_user(
    user=Depends(require_user)
):
    return user


@app.get("/auth/users")
async def all_users():

    try:

        users = get_all_users()

        return {
            "success": True,
            "total": len(users),
            "users": users
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Could not fetch users: {str(e)}"
        )


@app.post("/auth/strike/{username}")
async def user_strike(username: str):

    try:

        # Find user by username first.
        conn_user = None

        users = get_all_users()

        target = next(
            (
                u for u in users
                if u["username"] == username
            ),
            None
        )

        if not target:
            raise HTTPException(
                status_code=404,
                detail="User not found."
            )

        result = add_strike(target["id"])

        return {
            "success": True,
            "username": username,
            "result": result
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Could not add strike: {str(e)}"
        )


# ===================================================================
# FRIEND SYSTEM
# ===================================================================

@app.get("/friends")
async def friends(
    user=Depends(require_user)
):

    return {
        "success": True,
        "friends": get_friends(user["id"])
    }


@app.get("/friends/available")
async def available_users(
    user=Depends(require_user)
):

    return {
        "success": True,
        "users": get_available_users(user["id"])
    }


@app.get("/friends/requests")
async def pending_requests(
    user=Depends(require_user)
):

    return {
        "success": True,
        "requests": get_pending_requests(user["id"])
    }


@app.post("/friends/request/{receiver_id}")
async def request_friend(
    receiver_id: str,
    user=Depends(require_user)
):

    result = send_friend_request(
        user["id"],
        receiver_id
    )

    if not result["success"]:

        raise HTTPException(
            status_code=400,
            detail=result["detail"]
        )

    return result


@app.post("/friends/accept/{request_id}")
async def accept_request(
    request_id: str,
    user=Depends(require_user)
):

    result = accept_friend_request(
        request_id,
        user["id"]
    )

    if not result["success"]:

        raise HTTPException(
            status_code=400,
            detail=result["detail"]
        )

    return result


@app.post("/friends/reject/{request_id}")
async def reject_request(
    request_id: str,
    user=Depends(require_user)
):

    result = reject_friend_request(
        request_id,
        user["id"]
    )

    if not result["success"]:

        raise HTTPException(
            status_code=400,
            detail=result["detail"]
        )

    return result


# ===================================================================
# LGS-MT CLASSIFICATION
# ===================================================================

@app.post(
    "/classify",
    response_model=ClassifyResponse
)
async def classify_message(
    req: ClassifyRequest
):

    message_text = req.message.strip()

    if not message_text:

        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty."
        )

    # ---------------------------------------------------------------
    # FETCH HISTORY
    # ---------------------------------------------------------------

    history = fetch_conversation_history(
        req.conversation_id,
        last_n=req.history_limit
    )

    # ---------------------------------------------------------------
    # CURRENT MESSAGE
    # ---------------------------------------------------------------

    current_message = {
        "sender": req.sender_id,
        "text": message_text
    }

    # ---------------------------------------------------------------
    # RUN LGS-MT
    # ---------------------------------------------------------------

    result = lgs_pipeline(
        conversation_id=req.conversation_id,
        conversation_history=history,
        current_message=current_message,
        threshold=req.threshold
    )

    # ---------------------------------------------------------------
    # CREATE EMBEDDING
    # ---------------------------------------------------------------

    embedding = get_message_embedding(
        message_text
    )

    # ---------------------------------------------------------------
    # STORE MESSAGE
    # ---------------------------------------------------------------

    store_message(
        conversation_id=req.conversation_id,
        sender_id=req.sender_id,
        message_text=message_text,
        embedding=embedding,

        muril_score=result.get(
            "global_score"
        ),

        adjusted_score=result.get(
            "final_score",
            result.get(
                "adjusted_score",
                0.0
            )
        ),

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

        flagged=result.get(
            "flagged",
            False
        )
    )

    # ---------------------------------------------------------------
    # RESULT
    # ---------------------------------------------------------------

    final_score = result.get(
        "final_score",
        result.get(
            "adjusted_score",
            0.0
        )
    )

    flagged = result.get(
        "flagged",
        False
    )

    return ClassifyResponse(

        flagged=flagged,

        label=result.get(
            "label",
            1 if flagged else 0
        ),

        adjusted_score=final_score,

        action=(
            "flag"
            if flagged
            else "allow"
        ),

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
                "banter_signal",
                0.0
            ),

            "reciprocity_score": result.get(
                "reciprocity_score",
                0.5
            ),

            "trajectory_score": result.get(
                "trajectory_score",
                0.5
            ),

            "reduction_applied": result.get(
                "reduction_applied",
                0.0
            ),

            "confidence": result.get(
                "confidence"
            )
        },

        moderation={

            "source": result.get(
                "source"
            ),

            "threshold_used": req.threshold,

            "history_used": result.get(
                "history_length",
                len(history)
            ),

            "sender_counts": result.get(
                "sender_counts",
                {}
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

        message={

            "conversation_id":
                req.conversation_id,

            "sender_id":
                req.sender_id,

            "text":
                message_text
        }
    )


# ===================================================================
# CHAT ENDPOINTS
# ===================================================================
#
# IMPORTANT:
# The specific route /chat/conversation/{other_user_id}
# MUST appear BEFORE /chat/{conversation_id}.
#
# Otherwise "/chat/conversation/123" can be interpreted as:
# conversation_id = "conversation"
#
# ===================================================================


@app.get("/chat/conversation/{other_user_id}")
async def get_chat_conversation(
    other_user_id: str,
    user=Depends(require_user)
):

    current_user_id = user["id"]

    # Cannot chat with yourself.
    if current_user_id == other_user_id:

        raise HTTPException(
            status_code=400,
            detail="Cannot create a conversation with yourself."
        )

    # ---------------------------------------------------------------
    # FRIEND CHECK
    # ---------------------------------------------------------------

    if not are_friends(
        current_user_id,
        other_user_id
    ):

        raise HTTPException(
            status_code=403,
            detail="You can only chat with accepted friends."
        )

    # ---------------------------------------------------------------
    # CHECK OTHER USER
    # ---------------------------------------------------------------

    other_user = get_user(
        other_user_id
    )

    if not other_user:

        raise HTTPException(
            status_code=404,
            detail="Other user not found."
        )

    # ---------------------------------------------------------------
    # GET / CREATE CONVERSATION
    # ---------------------------------------------------------------

    conversation = get_or_create_conversation(
        current_user_id,
        other_user_id
    )

    return {
        "success": True,
        "conversation": conversation
    }


@app.get("/chat/{conversation_id}")
async def get_chat(
    conversation_id: str,
    user=Depends(require_user)
):

    messages = get_chat_messages(
        conversation_id
    )

    return {
        "success": True,
        "conversation_id": conversation_id,
        "messages": messages
    }


@app.post("/chat/send")
async def send_chat_message(
    req: SendMessageRequest,
    user=Depends(require_user)
):

    sender_id = user["id"]

    # ---------------------------------------------------------------
    # FRIEND CHECK
    # ---------------------------------------------------------------

    if not are_friends(
        sender_id,
        req.receiver_id
    ):

        raise HTTPException(
            status_code=403,
            detail="You can only message accepted friends."
        )

    # ---------------------------------------------------------------
    # VALIDATE MESSAGE
    # ---------------------------------------------------------------

    message_text = req.message.strip()

    if not message_text:

        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty."
        )

    # ---------------------------------------------------------------
    # CHECK RECEIVER
    # ---------------------------------------------------------------

    receiver = get_user(
        req.receiver_id
    )

    if not receiver:

        raise HTTPException(
            status_code=404,
            detail="Receiver not found."
        )

    # ---------------------------------------------------------------
    # GET CHAT HISTORY
    # ---------------------------------------------------------------

    previous_messages = get_chat_messages(
        req.conversation_id
    )

    history = [

        {
            "sender": msg["sender_id"],
            "text": msg["message"]
        }

        for msg in previous_messages[-5:]
    ]

    # ---------------------------------------------------------------
    # CURRENT MESSAGE
    # ---------------------------------------------------------------

    current_message = {
        "sender": sender_id,
        "text": message_text
    }

    # ---------------------------------------------------------------
    # RUN LGS-MT
    # ---------------------------------------------------------------

    result = lgs_pipeline(
        conversation_id=req.conversation_id,
        conversation_history=history,
        current_message=current_message,
        threshold=THRESHOLD
    )

    flagged = result.get(
        "flagged",
        False
    )

    score = result.get(
        "final_score",
        result.get(
            "adjusted_score",
            0.0
        )
    )

    # ---------------------------------------------------------------
    # SAVE CHAT MESSAGE
    # ---------------------------------------------------------------

    saved_message = save_chat_message(
        conversation_id=req.conversation_id,
        sender_id=sender_id,
        receiver_id=req.receiver_id,
        message=message_text,
        flagged=flagged,
        score=score
    )

    return {

        "success": True,

        "message": saved_message,

        "moderation": {

            "flagged": flagged,

            "score": score,

            "label": result.get(
                "label",
                1 if flagged else 0
            ),

            "action": (
                "flag"
                if flagged
                else "allow"
            )
        }
    }


# ===================================================================
# DATABASE ENDPOINTS
# ===================================================================

@app.get("/db/conversations")
async def get_conversations():

    conversations = list_all_conversations()

    return {
        "total": len(conversations),
        "conversations": conversations
    }


@app.get("/db/view/{conversation_id}")
async def view_conversation(
    conversation_id: str
):

    messages = get_all_messages(
        conversation_id
    )

    if not messages:

        return {
            "conversation_id":
                conversation_id,

            "total":
                0,

            "flagged":
                0,

            "flag_rate":
                0.0,

            "messages":
                []
        }

    flagged_count = sum(
        1
        for message in messages
        if message.get("flagged")
    )

    return {

        "conversation_id":
            conversation_id,

        "total":
            len(messages),

        "flagged":
            flagged_count,

        "flag_rate":
            round(
                flagged_count /
                len(messages),
                3
            ),

        "messages":
            messages
    }


@app.get("/db/stats")
async def database_stats():

    return get_stats()


@app.delete("/db/{conversation_id}")
async def clear_conversation(
    conversation_id: str
):

    deleted = delete_conversation(
        conversation_id
    )

    if deleted:

        return {
            "success": True,
            "message":
                f"Conversation "
                f"{conversation_id} deleted"
        }

    raise HTTPException(
        status_code=404,
        detail=
            f"Conversation "
            f"{conversation_id} not found"
    )


# ===================================================================
# HEALTH CHECK
# ===================================================================

@app.get("/health")
async def health_check():

    return {

        "status":
            "ok",

        "model":
            "MuRIL + LGS-MT",

        "device":
            (
                "cuda"
                if torch.cuda.is_available()
                else "cpu"
            )
    }


# ===================================================================
# ROOT
# ===================================================================

@app.get("/")
async def root():

    return {

        "message":
            "CyberGuard Cyberbullying Detection API",

        "docs":
            "http://localhost:8000/docs",

        "endpoints": {

            "signup":
                "POST /auth/signup",

            "login":
                "POST /auth/login",

            "current_user":
                "GET /auth/me",

            "users":
                "GET /auth/users",

            "strike":
                "POST /auth/strike/{username}",

            "friends":
                "GET /friends",

            "available_users":
                "GET /friends/available",

            "friend_requests":
                "GET /friends/requests",

            "send_friend_request":
                "POST /friends/request/{receiver_id}",

            "accept_friend_request":
                "POST /friends/accept/{request_id}",

            "reject_friend_request":
                "POST /friends/reject/{request_id}",

            "create_chat":
                "GET /chat/conversation/{other_user_id}",

            "get_chat":
                "GET /chat/{conversation_id}",

            "send_chat":
                "POST /chat/send",

            "classify":
                "POST /classify",

            "conversations":
                "GET /db/conversations",

            "view_conversation":
                "GET /db/view/{conversation_id}",

            "stats":
                "GET /db/stats",

            "delete_conversation":
                "DELETE /db/{conversation_id}",

            "health":
                "GET /health"
        }
    }