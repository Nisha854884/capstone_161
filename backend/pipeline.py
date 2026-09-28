"""
pipeline.py
All classification pipeline functions ported from Colab.
Loaded once at startup by main.py — do not import heavy libraries at the top
of other files, import from here instead.
"""

import torch
import numpy as np
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from scipy.special import softmax
from pathlib import Path
from .memory import (
    search_local_memory,
    search_global_memory
)

# ── Paths ─────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent   # cyberbullying_app/
MODEL_PATH = BASE_DIR / "model" / "global_model" / "muril_cyberbullying"
MAX_LEN    = 128
THRESHOLD  = 0.7
TEMPERATURE = 1.5

# ── Device ────────────────────────────────────────────────────────────────
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ── Global model/tokenizer (loaded once at startup) ───────────────────────
print(f"Loading MuRIL from {MODEL_PATH} ...")
muril_tokenizer = AutoTokenizer.from_pretrained(str(MODEL_PATH))
muril_model     = AutoModelForSequenceClassification.from_pretrained(
                      str(MODEL_PATH)
                  ).to(DEVICE)
muril_model.eval()
print(f"✅ MuRIL loaded on {DEVICE}")

# ── Local model ────────────────────────────────────────────────────────────
LOCAL_MODEL_PATH = (
    BASE_DIR / "model" / "local_model" / "muril_student_4layer"
)

print(f"Loading Local Model from {LOCAL_MODEL_PATH} ...")

local_tokenizer = AutoTokenizer.from_pretrained(
    str(LOCAL_MODEL_PATH)
)

local_model = AutoModelForSequenceClassification.from_pretrained(
    str(LOCAL_MODEL_PATH)
).to(DEVICE)

local_model.eval()

print(
    f"✅ Local Model loaded: "
    f"{sum(p.numel() for p in local_model.parameters()) / 1e6:.1f}M parameters"
)

vader = SentimentIntensityAnalyzer()
print("✅ VADER loaded")

# ── Banter/laughter signals ───────────────────────────────────────────────
LAUGH_EMOJIS  = ['😂', '🤣', '💀', '☠️', '😆', '😛', '😜', '🙃', '😄']
LAUGH_TEXT    = ['lol', 'lmao', 'lmfao', 'haha', 'hehe', 'hahaha',
                 'xd', 'rofl']
PLAYFUL_WORDS = ['jk', 'kidding', 'joking', 'bro', 'yaar', 'dude',
                 'bestie', 'ok ok', 'fine fine', 'you win']

# ── Offensive signals (English + Hinglish) ────────────────────────────────
OFFENSIVE_SIGNALS = [
    # English
    'stupid', 'idiot', 'dumb', 'loser', 'pathetic', 'hate',
    'shut up', 'nobody likes', 'worthless', 'ugly', 'disgusting',
    'kill yourself', 'die', 'freak',
    # Hinglish
    'bc', 'mc', 'sala', 'saali', 'bewakoof', 'gadha', 'ullu',
    'kuch nahi', 'bakwas', 'bekar', 'fail', 'nikal',
    'teri toh', 'chup kar', 'izzat nahi', 'koi nahi chahta',
]

LAUGHTER_SIGNALS = ['lol', 'haha', 'lmao', '😂', '💀', '😆', 'hehe', 'xd']

def get_offensive_signal(text: str) -> float:
    """
    Detect explicit offensive / abusive language.

    Returns:
        0.0 = no offensive signal
        1.0 = strong offensive signal
    """

    text_lower = text.lower().strip()

    if not text_lower:
        return 0.0

    hits = sum(
        1
        for signal in OFFENSIVE_SIGNALS
        if signal in text_lower
    )

    if hits == 0:
        return 0.0

    # One explicit offensive term is already meaningful.
    if hits == 1:
        return 0.75

    if hits == 2:
        return 0.90

    return 1.0
# ─────────────────────────────────────────────────────────────────────────
# SIGNAL 1 — MuRIL harmful score
# ─────────────────────────────────────────────────────────────────────────
def get_muril_score(text: str, conversation_history: list = None) -> float:
    """
    Returns probability (0→1) that the message is harmful.
    Uses [SEP]-concatenated context if history is provided.
    """
    if conversation_history:
        recent     = [m if isinstance(m, str) else m.get('text', '')
                      for m in conversation_history[-4:]]
        input_text = f" {muril_tokenizer.sep_token} ".join(recent + [text])
    else:
        input_text = text

    encoding = muril_tokenizer(
        input_text,
        max_length     = MAX_LEN,
        padding        = 'max_length',
        truncation     = True,
        return_tensors = 'pt'
    )
    input_ids      = encoding['input_ids'].to(DEVICE)
    attention_mask = encoding['attention_mask'].to(DEVICE)

    with torch.no_grad():
        output        = muril_model(input_ids=input_ids,
                                    attention_mask=attention_mask)
        scaled_logits = output.logits / TEMPERATURE
        probs         = softmax(scaled_logits.cpu().numpy()[0])

    return float(probs[1])   # probability of HARMFUL


# ─────────────────────────────────────────────────────────────────────────
# SIGNAL 2 — Banter signal (emoji + laughter detector)
# ─────────────────────────────────────────────────────────────────────────
def get_banter_signal(text: str, conversation_history: list = None) -> float:
    """
    Detects banter/laughter signals in current message + recent history.
    Returns 0.0 (no banter) → 1.0 (strong banter).
    Language-agnostic — works on emojis and laughter text in any language.
    """
    text_lower = text.lower()

    emoji_hits   = sum(1 for e in LAUGH_EMOJIS  if e in text)
    laugh_hits   = sum(1 for l in LAUGH_TEXT    if l in text_lower)
    playful_hits = sum(1 for p in PLAYFUL_WORDS if p in text_lower)

    current_score = min(1.0, (emoji_hits   * 0.40) +
                              (laugh_hits   * 0.35) +
                              (playful_hits * 0.15))

    history_bonus = 0.0
    if conversation_history:
        recent = conversation_history[-2:]
        for msg in recent:
            t = (msg.get('text', msg) if isinstance(msg, dict) else msg).lower()
            if any(e in t for e in LAUGH_EMOJIS) or \
               any(l in t for l in LAUGH_TEXT):
                history_bonus += 0.15

    return round(min(1.0, current_score + history_bonus), 4)


# ─────────────────────────────────────────────────────────────────────────
# SIGNAL 3 — Reciprocity score
# ─────────────────────────────────────────────────────────────────────────
DEFENSIVE_SIGNALS = [

    # --- Core Direct Defensive ---
    'thats not true', 'thats not fair', 'just stop', 'please stop',
    'leave me alone', 'thats enough', 'i said stop', 'stop it',
    'thats harsh', 'thats mean', 'ur being mean', 'you are being mean',
    'that doesnt make it okay', 'im not weird', 'just leave me',
    'make it stop', 'seriously stop',

    # --- Strong Pushback & Boundaries ---
    'idc just stop', 'can you not', 'can u not', 'just dont',
    'dont start', 'what is your problem', 'whats your problem',
    'why are you like this', 'why are u like this',
    'stop texting me', 'dont text me',
    'this isnt funny', 'not funny', 'its not funny',
    'youre not funny', 'ur not funny',
    'stop acting like that', 'dont talk to me like that',
    'talk properly', 'be respectful', 'thats rude',
    'low blow', 'too far', 'you crossed the line',
    'this is too much',
    'why me', 'why always me',
    'leave me out of this', 'dont involve me',
    'stop targeting me', 'why are you targeting me',
    'im serious stop', 'seriously just stop',
    'stop messing with me', 'dont mess with me',
    'back off', 'just back off',
    'can you just stop', 'can you please stop',
    'what did i do', 'what did i even do',
    'how is that funny',

    # --- Gen-Z Slang (Filtered but Useful) ---
    'bro stop', 'bruh stop', 'nah stop', 'wtf stop',
    'wtf is wrong with you',
    'thats messed up', 'thats messed',
    'youre weird for that', 'ur weird for that',
    'this aint funny', 'aint funny',
    'youre doing too much', 'ur doing too much',
    'why you doing this',
    'stop bro seriously', 'im not playing', 'im not joking',
    'deadass stop', 'im fr stop', 'stop fr', 'actually stop',

    # --- Emotional & Vulnerable ---
    'why are you doing this to me', 'i didnt do anything',
    'what did i do to you', 'why are you like this with me',
    'this actually hurts', 'that hurt', 'youre hurting me',
    'stop hurting me', 'i dont like this',
    'this makes me uncomfortable', 'i dont feel okay',
    'im tired of this',

    # --- Hinglish (Strong + Natural) ---
    'band karo', 'chup karo', 'yaar band karo',
    'sach nahi hai', 'yeh sahi nahi', 'kyu bol rahe ho',
    'mujhe akela chhodo', 'please mat karo', 'aisa mat karo',
    'yeh galat hai', 'bahut hua', 'mat karo yaar',
    'bas karo', 'ab bas', 'kyu kar rahe ho',
    'mere pe kyu', 'kyu mere saath', 'mujhe kyu bol rahe ho',
    'itna bhi mat bolo', 'zyada ho raha hai',
    'limit mein raho', 'had ho gayi',
    'mazaak mat banao', 'mazaak mat udaao',
    'seriously mat karo',
    'bakwas band karo', 'faltu mat bolo',
    'samajh nahi aa raha kya', 'samajh nahi aata kya',
    'dekh bhai mat kar', 'fazool baat mat kar',
    'limit cross mat kar', 'dimaag mat khao',
    'kya masla hai', 'kya dikkat hai',
    'tamiz se baat kar', 'over mat ho',

    # --- Kannada & Mixed (Stronger Signals Only) ---
    'beda', 'sari illa',
    'yen maadtiya', 'yaake',
    'beda please', 'beda maga', 'beda guru',
    'saaku', 'saaku aaytu',
    'matad beda', 'hinge matad beda',
    'nange beda', 'nange ishta illa',
    'yake hing maadtiya', 'yake hinge',
    'nanna target maad beda',
    'please bidi', 'bittu bidi',
    'innu saaku', 'nidu jaasti aytu',
    'yako ashtu hogo', 'sumne irappa', 'vaasi bidi'
]

def get_reciprocity_score(conversation_history: list) -> tuple:
    """
    Updated to include victim defense detection.

    Three signals combined:
    1. Offensive reciprocity — are both sides using offensive language?
       If only one side is → bullying signal
    2. Defensive imbalance — is one person repeatedly defending themselves?
       If yes → strong bullying signal
    3. Laughter bonus — if both sides are laughing → banter signal

    Key insight: in bullying, the victim defends while the bully attacks.
    This asymmetry is detectable even when no offensive keywords are used.
    """
    if len(conversation_history) < 2:
        return 0.5, {}

    sender_scores = {}

    for msg in conversation_history:
        sender = msg.get('sender', 'unknown') if isinstance(msg, dict) \
                 else 'unknown'
        text   = (msg.get('text', '') if isinstance(msg, dict) \
                  else str(msg)).lower()

        if sender not in sender_scores:
            sender_scores[sender] = {
                'offensive' : 0,
                'defensive' : 0,
                'laughter'  : 0
            }

        if any(signal in text for signal in OFFENSIVE_SIGNALS):
            sender_scores[sender]['offensive'] += 1

        if any(signal in text for signal in DEFENSIVE_SIGNALS):
            sender_scores[sender]['defensive'] += 1

        if any(signal in text for signal in LAUGHTER_SIGNALS):
            sender_scores[sender]['laughter'] += 1

    if not sender_scores:
        return 0.5, sender_scores

    senders = list(sender_scores.keys())
    if len(senders) < 2:
        return 0.0, sender_scores

    offensive_counts = [sender_scores[s]['offensive'] for s in senders]
    defensive_counts = [sender_scores[s]['defensive'] for s in senders]
    laughter_counts  = [sender_scores[s]['laughter']  for s in senders]

    # ── Signal 1: Offensive reciprocity ──────────────────────────────
    max_off = max(offensive_counts)
    min_off = min(offensive_counts)

    if max_off == 0:
        offensive_reciprocity = 0.5   # neutral — no offensive keywords used
    else:
        offensive_reciprocity = min_off / max_off

    # ── Signal 2: Defensive imbalance ────────────────────────────────
    # If one person has significantly more defensive messages than the other,
    # they are being targeted — this is a bullying signal
    max_def = max(defensive_counts)
    min_def = min(defensive_counts)
    total_def = sum(defensive_counts)

    if total_def == 0:
        defense_penalty = 0.0   # nobody defending — no signal either way
    elif max_def == 0:
        defense_penalty = 0.0
    else:
        # How imbalanced is the defense?
        # Perfect balance: both defend equally → penalty = 0
        # Complete imbalance: only one defends → penalty = 1.0
        defense_imbalance = 1.0 - (min_def / max_def)

        # Scale by how many defensive messages there are
        # 1 defensive message = small signal
        # 4+ defensive messages = strong signal
        defense_weight = min(1.0, total_def / 4)

        defense_penalty = defense_imbalance * defense_weight

    # ── Signal 3: Laughter bonus ──────────────────────────────────────
    both_laughing  = all(c > 0 for c in laughter_counts)
    laughter_bonus = 0.3 if both_laughing else 0.0

    # ── Combine ───────────────────────────────────────────────────────
    # Start from offensive reciprocity
    # Subtract defense penalty (imbalanced defense → lower reciprocity → more likely bullying)
    # Add laughter bonus (mutual laughter → more likely banter)
    final_score = offensive_reciprocity - defense_penalty + laughter_bonus
    final_score = round(max(0.0, min(1.0, final_score)), 4)

    return final_score, sender_scores

# ─────────────────────────────────────────────────────────────────────────
# SIGNAL 4 — Sentiment trajectory
# ─────────────────────────────────────────────────────────────────────────
def get_sentiment_trajectory(conversation_history: list) -> tuple:
    """
    Measures whether sentiment is oscillating (banter) or
    monotonically declining (bullying).

    Returns:
        (trajectory_score, sentiment_scores_list)
        score: 0.0 = declining, 1.0 = oscillating
    """
    if len(conversation_history) < 2:
        return 0.5, []

    scores = []
    for msg in conversation_history:
        text  = (msg.get('text', '') if isinstance(msg, dict) \
                 else str(msg))
        score = vader.polarity_scores(text)['compound']
        scores.append(score)

    if len(scores) < 2:
        return 0.5, scores

    direction_changes = 0
    for i in range(1, len(scores)):
        prev_diff = scores[i-1] - scores[i-2] if i >= 2 else 1
        curr_diff = scores[i]   - scores[i-1]
        if curr_diff * prev_diff < 0:
            direction_changes += 1

    max_changes      = len(scores) - 1
    oscillation_rate = direction_changes / max_changes if max_changes > 0 \
                       else 0
    overall_trend    = scores[-1] - scores[0]
    trend_score      = max(0, min(1, (overall_trend + 1) / 2))
    trajectory_score = round((oscillation_rate * 0.6) +
                              (trend_score      * 0.4), 4)

    return trajectory_score, scores


# ─────────────────────────────────────────────────────────────────────────
# LGS-MT — MEMORY SCORES
# ─────────────────────────────────────────────────────────────────────────
def get_memory_scores(
    conversation_id: str,
    embedding: list
) -> tuple:
    """
    Retrieve relevant Local and Global memories.

    Local memory:
        Conversation-specific previous messages.

    Global memory:
        Generalized cyberbullying patterns shared across conversations.
    """

    local_memories = search_local_memory(
        conversation_id=conversation_id,
        query_embedding=embedding,
        n_results=5
    )

    global_memories = search_global_memory(
        query_embedding=embedding,
        n_results=5
    )

    # Highest similarity = strongest matching memory
    local_score = None

    if local_memories:
        local_score = max(
            m["similarity"]
            for m in local_memories
        )

    global_score = None

    if global_memories:
        # Only use memories indicating harmful patterns
        harmful_memories = [
            m for m in global_memories
            if m.get("label", 0) == 1
        ]

        if harmful_memories:
            global_score = max(
                m["similarity"]
                for m in harmful_memories
            )

    return (
        local_score,
        global_score,
        local_memories,
        global_memories
    )

# ─────────────────────────────────────────────────────────────────────────
# SCORE FUSION
# ─────────────────────────────────────────────────────────────────────────
def fuse_scores(
    muril_score: float,
    local_model_score: float,
    banter_signal: float,
    reciprocity_score: float,
    trajectory_score: float,
    local_memory_score=None,
    global_memory_score=None,
    history_length: int = 0,
    threshold: float = THRESHOLD,
    offensive_signal: float = 0.0
) -> dict:

    # ------------------------------------------------------------
    # 1. Determine base model score
    # ------------------------------------------------------------

    if muril_score is None:
        base_score = local_model_score
    else:
        base_score = (
            0.4 * local_model_score +
            0.6 * muril_score
        )

    # ------------------------------------------------------------
    # 2. Memory evidence
    # ------------------------------------------------------------

    local_mem = (
        local_memory_score
        if local_memory_score is not None
        else 0.0
    )

    global_mem = (
        global_memory_score
        if global_memory_score is not None
        else 0.0
    )

    memory_bonus = (
        0.10 * local_mem +
        0.05 * global_mem
    )

    score_with_memory = min(
        1.0,
        base_score + memory_bonus
    )
    # ------------------------------------------------------------
    # EXPLICIT OFFENSIVE LANGUAGE BOOST
    # ------------------------------------------------------------

    offensive_boost = 0.20 * offensive_signal

    score_with_offensive = min(
        1.0,
        score_with_memory + offensive_boost
    )
    # ------------------------------------------------------------
    # 3. History-dependent contextual weights
    # ------------------------------------------------------------

    if history_length < 2:

        W_RECIP = 0.10
        W_BANTER = 0.25
        W_TRAJ = 0.15
        max_reduction = 0.20

    elif history_length < 4:

        W_RECIP = 0.15
        W_BANTER = 0.20
        W_TRAJ = 0.15
        max_reduction = 0.30

    else:

        W_RECIP = 0.20
        W_BANTER = 0.15
        W_TRAJ = 0.10
        max_reduction = 0.35

    # ------------------------------------------------------------
    # 4. Contextual reduction
    # ------------------------------------------------------------
    weighted_reduction = min(
        max_reduction,
        (
            reciprocity_score * W_RECIP
            + banter_signal * W_BANTER
            + trajectory_score * W_TRAJ
        )
    )

    # Do not allow banter/context reduction to hide
    # explicit offensive language.
    if offensive_signal >= 0.75:
        weighted_reduction = min(
            weighted_reduction,
            0.15
        )

    # ------------------------------------------------------------
    # 5. Protect strong model evidence
    # ------------------------------------------------------------

    if base_score >= 0.90:

        weighted_reduction = min(
            weighted_reduction,
            0.15
        )

    elif base_score >= 0.80:

        weighted_reduction = min(
            weighted_reduction,
            0.20
        )

    # ------------------------------------------------------------
    # 6. Apply reduction
    # ------------------------------------------------------------

    adjusted_score = (
        score_with_offensive *
        (1 - weighted_reduction)
    )

    adjusted_score = max(
        0.0,
        min(1.0, adjusted_score)
    )

    # ------------------------------------------------------------
    # 7. Final decision
    # ------------------------------------------------------------

    flagged = adjusted_score >= threshold

    # ------------------------------------------------------------
    # 8. RETURN RESULT
    #
    # IMPORTANT:
    # This must be aligned with the rest of the function.
    # ------------------------------------------------------------

    return {
        "muril_score": (
            round(muril_score, 4)
            if muril_score is not None
            else None
        ),

        "local_model_score":
            round(local_model_score, 4),

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

        "memory_bonus":
            round(memory_bonus, 4),

        "banter_signal":
            round(banter_signal, 4),

        "reciprocity_score":
            round(reciprocity_score, 4),

        "trajectory_score":
            round(trajectory_score, 4),

        "base_score":
            round(base_score, 4),

        "reduction_applied":
            round(weighted_reduction, 4),

        "adjusted_score":
            round(adjusted_score, 4),

        "offensive_signal":
            round(offensive_signal, 4),

        "offensive_boost":
            round(offensive_boost, 4),

        "flagged":
            flagged,

        "label":
            1 if flagged else 0,
    }
# ─────────────────────────────────────────────────────────────────────────
# LOCAL MODEL
# ─────────────────────────────────────────────────────────────────────────



def get_local_model_score(
    text: str,
    conversation_history: list = None
) -> float:
    """
    Returns probability that the message is harmful
    according to the local student model.
    """

    if conversation_history:

        recent = [
            m.get("text", "")
            if isinstance(m, dict)
            else str(m)
            for m in conversation_history[-4:]
        ]

        input_text = (
            f" {local_tokenizer.sep_token} "
            .join(recent + [text])
        )

    else:

        input_text = text

    encoding = local_tokenizer(
        input_text,
        max_length=MAX_LEN,
        padding="max_length",
        truncation=True,
        return_tensors="pt"
    )

    input_ids = encoding["input_ids"].to(DEVICE)

    attention_mask = encoding[
        "attention_mask"
    ].to(DEVICE)

    with torch.no_grad():

        output = local_model(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

        scaled_logits = (
            output.logits / TEMPERATURE
        )

        probs = softmax(
            scaled_logits.cpu().numpy()[0]
        )

    return float(probs[1])

# ─────────────────────────────────────────────────────────────────────────
# FULL PIPELINE
# ─────────────────────────────────────────────────────────────────────────
def full_pipeline(
    conversation_history: list,
    current_message: dict,
    threshold: float = THRESHOLD
) -> dict:
    """
    Runs the complete LGS-MT pipeline.

    Components:
        1. Global MuRIL
        2. Local student model
        3. Local memory
        4. Global memory
        5. Banter signal
        6. Reciprocity signal
        7. Sentiment trajectory
        8. Score fusion

    Args:
        conversation_history:
            List of {"sender": str, "text": str}

        current_message:
            {
                "sender": str,
                "text": str,
                "conversation_id": str
            }

        threshold:
            Final bullying threshold.

    Returns:
        Complete LGS-MT result dictionary.
    """

    # ================================================================
    # BASIC INFORMATION
    # ================================================================

    text = current_message.get("text", "")
    sender = current_message.get("sender", "")

    conversation_id = current_message.get(
        "conversation_id",
        ""
    )

    # ================================================================
    # VICTIM DEFENSE CHECK
    # ================================================================

    text_lower = text.lower()

    if any(
        signal in text_lower
        for signal in DEFENSIVE_SIGNALS
    ):

        return {
            "muril_score": 0.0,
            "local_model_score": 0.0,
            "model_score": 0.0,

            "local_memory_score": None,
            "global_memory_score": None,

            "memory_bonus": 0.0,

            "banter_signal": 0.0,
            "reciprocity_score": 0.5,
            "trajectory_score": 0.5,

            "reduction_applied": 0.0,
            "adjusted_score": 0.0,

            "flagged": False,
            "label": 0,

            "sender_counts": {},
            "sentiments": [],

            "history_length": len(
                conversation_history
            ),

            "local_memories": [],
            "global_memories": [],

            "source": "victim_defense"
        }

    # ================================================================
    # SIGNAL 1 — GLOBAL MuRIL
    # ================================================================

    muril_score = get_muril_score(
        text,
        conversation_history=[
            m.get("text", "")
            if isinstance(m, dict)
            else str(m)
            for m in conversation_history
        ]
    )

    # ================================================================
    # SIGNAL 2 — LOCAL MODEL
    # ================================================================
    #
    # The local model should classify the current message.
    #
    # It uses the same tokenizer as the global model but its own
    # fine-tuned student weights.
    # ================================================================

    local_model_score = get_local_model_score(
        text,
        conversation_history
    )

    # ================================================================
    # SIGNAL 3 — BANTER
    # ================================================================

    banter_signal = get_banter_signal(
        text,
        conversation_history
    )

    # ================================================================
    # SIGNAL 4 — RECIPROCITY
    # ================================================================

    full_history = (
        conversation_history +
        [current_message]
    )

    recip_score, sender_counts = (
        get_reciprocity_score(
            full_history
        )
    )

    # ================================================================
    # SIGNAL 5 — SENTIMENT TRAJECTORY
    # ================================================================

    traj_score, sentiments = (
        get_sentiment_trajectory(
            full_history
        )
    )

    # ================================================================
    # EMBEDDING FOR MEMORY
    # ================================================================

    embedding = get_message_embedding(
        text
    )

    # ================================================================
    # LOCAL MEMORY
    # ================================================================

    local_memories = []

    local_memory_score = None

    if conversation_id:

        local_memories = search_local_memory(
            conversation_id=conversation_id,
            query_embedding=embedding,
            n_results=5
        )

        if local_memories:

            local_memory_score = max(
                0.0,
                max(
                    memory["similarity"]
                    for memory in local_memories
                )
            )

    # ================================================================
    # GLOBAL MEMORY
    # ================================================================

    global_memories = search_global_memory(
        query_embedding=embedding,
        n_results=5
    )

    global_memory_score = None

    if global_memories:

        global_memory_score = max(
            0.0,
            max(
                memory["similarity"]
                for memory in global_memories
            )
        )

    # ================================================================
    # SCORE FUSION
    # ================================================================

    result = fuse_scores(
        muril_score=muril_score,

        local_model_score=local_model_score,

        banter_signal=banter_signal,

        reciprocity_score=recip_score,

        trajectory_score=traj_score,

        local_memory_score=local_memory_score,

        global_memory_score=global_memory_score,

        history_length=len(
            conversation_history
        ),

        threshold=threshold
    )

    # ================================================================
    # ADD EXTRA INFORMATION
    # ================================================================

    result["sender_counts"] = sender_counts

    result["sentiments"] = [
        round(s, 2)
        for s in sentiments
    ]

    result["history_length"] = len(
        conversation_history
    )

    result["local_memories"] = (
        local_memories
    )

    result["global_memories"] = (
        global_memories
    )

    result["conversation_id"] = (
        conversation_id
    )

    result["sender"] = sender

    result["source"] = "lgs_mt"

    return result

# ─────────────────────────────────────────────────────────────────────────
# EMBEDDING HELPER (for ChromaDB storage)
# ─────────────────────────────────────────────────────────────────────────
def get_message_embedding(text: str) -> list:
    """
    Returns 768-dim MuRIL [CLS] embedding for a message.
    Used by database.py to store messages in ChromaDB.
    """
    encoding = muril_tokenizer(
        text,
        max_length     = MAX_LEN,
        padding        = 'max_length',
        truncation     = True,
        return_tensors = 'pt'
    )
    input_ids      = encoding['input_ids'].to(DEVICE)
    attention_mask = encoding['attention_mask'].to(DEVICE)

    with torch.no_grad():
        base_model = getattr(muril_model, 'bert',
                     getattr(muril_model, 'albert',
                     getattr(muril_model, 'roberta', None)))

        if base_model is not None:
            outputs   = base_model(input_ids=input_ids,
                                   attention_mask=attention_mask)
            embedding = outputs.last_hidden_state[:, 0, :] \
                               .cpu().numpy()[0].tolist()
        else:
            outputs   = muril_model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                output_hidden_states=True
            )
            embedding = outputs.hidden_states[-1][:, 0, :] \
                               .cpu().numpy()[0].tolist()

    return embedding