import sqlite3
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
import jwt
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "users.db")
JWT_SECRET = "change-this-secret-for-your-project"
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_auth_db():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            strikes INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS friend_requests (
            id TEXT PRIMARY KEY,
            sender_id TEXT NOT NULL,
            receiver_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,

            FOREIGN KEY (sender_id) REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id),

            UNIQUE(sender_id, receiver_id)
        )
    """)
    conn.commit()
    conn.close()
# ---------------------------------------------------------
# PASSWORD HASHING
# ---------------------------------------------------------
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)

    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        100000
    )
    return salt.hex() + ":" + hashed.hex()

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, hash_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        new_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt,
            100000
        )
        return secrets.compare_digest(
            new_hash.hex(),
            hash_hex
        )
    except Exception:
        return False

# ---------------------------------------------------------
# USERS
# ---------------------------------------------------------
def create_user(username: str, password: str, role="user"):
    conn = get_connection()

    user_id = str(uuid.uuid4())

    password_hash = hash_password(password)

    try:
        conn.execute(
            """
            INSERT INTO users
            (id, username, password_hash, role, strikes, created_at)
            VALUES (?, ?, ?, ?, 0, ?)
            """,
            (
                user_id,
                username,
                password_hash,
                role,
                datetime.now(timezone.utc).isoformat()
            )
        )

        conn.commit()

    except sqlite3.IntegrityError:
        conn.close()
        return None

    conn.close()

    return {
        "id": user_id,
        "username": username,
        "role": role,
        "strikes": 0
    }


def authenticate_user(username: str, password: str):

    conn = get_connection()

    row = conn.execute(
        """
        SELECT id, username, password_hash, role, strikes
        FROM users
        WHERE username = ?
        """,
        (username,)
    ).fetchone()

    conn.close()

    if not row:
        return None

    user_id, username, password_hash, role, strikes = row

    if not verify_password(password, password_hash):
        return None

    return {
        "id": user_id,
        "username": username,
        "role": role,
        "strikes": strikes
    }


def get_user(user_id: str):

    conn = get_connection()

    row = conn.execute(
        """
        SELECT id, username, role, strikes
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "username": row[1],
        "role": row[2],
        "strikes": row[3]
    }


def get_all_users():

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT id, username, role, strikes, created_at
        FROM users
        ORDER BY created_at DESC
        """
    ).fetchall()

    conn.close()

    return [
        {
            "id": row[0],
            "username": row[1],
            "role": row[2],
            "strikes": row[3],
            "created_at": row[4]
        }
        for row in rows
    ]


def add_strike(user_id: str):

    conn = get_connection()

    conn.execute(
        """
        UPDATE users
        SET strikes = strikes + 1
        WHERE id = ?
        """,
        (user_id,)
    )

    conn.commit()

    row = conn.execute(
        """
        SELECT strikes
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    conn.close()

    return row[0] if row else 0

# ---------------------------------------------------------
# FRIEND SYSTEM
# ---------------------------------------------------------
def are_friends(user_id: str, other_user_id: str):

    conn = get_connection()

    row = conn.execute(
        """
        SELECT id
        FROM friend_requests
        WHERE
            (
                (sender_id = ? AND receiver_id = ?)
                OR
                (sender_id = ? AND receiver_id = ?)
            )
            AND status = 'accepted'
        LIMIT 1
        """,
        (
            user_id,
            other_user_id,
            other_user_id,
            user_id
        )
    ).fetchone()

    conn.close()

    return row is not None
    
def send_friend_request(sender_id: str, receiver_id: str):

    if sender_id == receiver_id:
        return {
            "success": False,
            "detail": "You cannot send a friend request to yourself."
        }

    conn = get_connection()

    # Check receiver exists
    receiver = conn.execute(
        """
        SELECT id, username, role
        FROM users
        WHERE id = ?
        """,
        (receiver_id,)
    ).fetchone()

    if not receiver:
        conn.close()
        return {
            "success": False,
            "detail": "User not found."
        }

    # Do not allow friend requests to admins
    if receiver[2] == "admin":
        conn.close()
        return {
            "success": False,
            "detail": "You cannot send a friend request to an admin."
        }

    # Check existing request in either direction
    existing = conn.execute(
        """
        SELECT id, sender_id, receiver_id, status
        FROM friend_requests
        WHERE
            (sender_id = ? AND receiver_id = ?)
            OR
            (sender_id = ? AND receiver_id = ?)
        """,
        (
            sender_id,
            receiver_id,
            receiver_id,
            sender_id
        )
    ).fetchone()

    if existing:

        request_id, existing_sender, existing_receiver, status = existing

        if status == "accepted":
            conn.close()
            return {
                "success": False,
                "detail": "You are already friends."
            }

        if status == "pending":
            conn.close()
            return {
                "success": False,
                "detail": "A friend request already exists."
            }

        # If rejected, allow a new request
        conn.execute(
            """
            DELETE FROM friend_requests
            WHERE id = ?
            """,
            (request_id,)
        )

    request_id = str(uuid.uuid4())

    conn.execute(
        """
        INSERT INTO friend_requests
        (
            id,
            sender_id,
            receiver_id,
            status,
            created_at
        )
        VALUES (?, ?, ?, 'pending', ?)
        """,
        (
            request_id,
            sender_id,
            receiver_id,
            datetime.now(timezone.utc).isoformat()
        )
    )

    conn.commit()
    conn.close()

    return {
        "success": True,
        "request_id": request_id
    }


def get_pending_requests(user_id: str):

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT
            fr.id,
            fr.sender_id,
            u.username,
            u.role,
            fr.created_at
        FROM friend_requests fr
        JOIN users u
            ON u.id = fr.sender_id
        WHERE
            fr.receiver_id = ?
            AND fr.status = 'pending'
        ORDER BY fr.created_at DESC
        """,
        (user_id,)
    ).fetchall()

    conn.close()

    return [
        {
            "id": row[0],
            "sender_id": row[1],
            "username": row[2],
            "role": row[3],
            "created_at": row[4]
        }
        for row in rows
    ]


def accept_friend_request(
    request_id: str,
    user_id: str
):

    conn = get_connection()

    row = conn.execute(
        """
        SELECT sender_id, receiver_id, status
        FROM friend_requests
        WHERE id = ?
        """,
        (request_id,)
    ).fetchone()

    if not row:
        conn.close()
        return {
            "success": False,
            "detail": "Friend request not found."
        }

    sender_id, receiver_id, status = row

    # Only receiver can accept
    if receiver_id != user_id:
        conn.close()
        return {
            "success": False,
            "detail": "You cannot accept this request."
        }

    if status != "pending":
        conn.close()
        return {
            "success": False,
            "detail": "This request is no longer pending."
        }

    conn.execute(
        """
        UPDATE friend_requests
        SET status = 'accepted'
        WHERE id = ?
        """,
        (request_id,)
    )

    conn.commit()
    conn.close()

    return {
        "success": True
    }


def reject_friend_request(
    request_id: str,
    user_id: str
):

    conn = get_connection()

    row = conn.execute(
        """
        SELECT receiver_id, status
        FROM friend_requests
        WHERE id = ?
        """,
        (request_id,)
    ).fetchone()

    if not row:
        conn.close()
        return {
            "success": False,
            "detail": "Friend request not found."
        }

    receiver_id, status = row

    if receiver_id != user_id:
        conn.close()
        return {
            "success": False,
            "detail": "You cannot reject this request."
        }

    if status != "pending":
        conn.close()
        return {
            "success": False,
            "detail": "This request is no longer pending."
        }

    conn.execute(
        """
        UPDATE friend_requests
        SET status = 'rejected'
        WHERE id = ?
        """,
        (request_id,)
    )

    conn.commit()
    conn.close()

    return {
        "success": True
    }


def get_friends(user_id: str):

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT
            u.id,
            u.username,
            u.role,
            u.strikes
        FROM friend_requests fr
        JOIN users u
            ON (
                CASE
                    WHEN fr.sender_id = ?
                    THEN u.id = fr.receiver_id
                    ELSE u.id = fr.sender_id
                END
            )
        WHERE
            (
                fr.sender_id = ?
                OR fr.receiver_id = ?
            )
            AND fr.status = 'accepted'
            AND u.role != 'admin'
        ORDER BY u.username
        """,
        (
            user_id,
            user_id,
            user_id
        )
    ).fetchall()

    conn.close()

    return [
        {
            "id": row[0],
            "username": row[1],
            "role": row[2],
            "strikes": row[3]
        }
        for row in rows
    ]


def get_available_users(user_id: str):

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT
            u.id,
            u.username,
            u.role,
            u.strikes
        FROM users u
        WHERE
            u.id != ?
            AND u.role != 'admin'
            AND u.id NOT IN (

                SELECT
                    CASE
                        WHEN sender_id = ?
                        THEN receiver_id
                        ELSE sender_id
                    END

                FROM friend_requests

                WHERE
                    (
                        sender_id = ?
                        OR receiver_id = ?
                    )
                    AND status IN ('pending', 'accepted')
            )

        ORDER BY u.username
        """,
        (
            user_id,
            user_id,
            user_id,
            user_id
        )
    ).fetchall()

    conn.close()

    return [
        {
            "id": row[0],
            "username": row[1],
            "role": row[2],
            "strikes": row[3]
        }
        for row in rows
    ]
# ---------------------------------------------------------
# JWT
# ---------------------------------------------------------

def create_token(user):

    payload = {
        "sub": user["id"],
        "username": user["username"],
        "role": user["role"],
        "exp": datetime.now(timezone.utc)
               + timedelta(hours=TOKEN_EXPIRE_HOURS)
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )


def decode_token(token):

    try:
        return jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )

    except jwt.InvalidTokenError:
        return None