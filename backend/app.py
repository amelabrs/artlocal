"""ArtLocal — Main FastAPI App."""

import os
import uuid
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Header, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from typing import Optional

from models import get_db, init_db, query, query_one, execute, DATABASE_URL
from auth import hash_password, verify_password, create_token, decode_token
from geo import haversine_miles

import cloudinary
import cloudinary.uploader

# ── Config ──────────────────────────────────────────────────────────────

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME", ""),
    api_key=os.environ.get("CLOUDINARY_API_KEY", ""),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET", ""),
)

app = FastAPI(title="ArtLocal API")

# Serve frontend
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# Placeholder param for SQL (? for sqlite, %s for postgres)
P = "%s" if DATABASE_URL else "?"


@app.on_event("startup")
def startup():
    init_db()
    conn = get_db()
    count = query_one(conn, "SELECT COUNT(*) as c FROM listings")
    conn.close()
    if count and count["c"] == 0:
        from seed import seed
        seed()


# ── Auth dependency ─────────────────────────────────────────────────────

def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    tok = authorization.split(" ", 1)[1]
    payload = decode_token(tok)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"id": int(payload["sub"]), "username": payload["username"]}


def get_optional_user(authorization: str = Header(None)):
    """Like get_current_user but returns None instead of raising."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    tok = authorization.split(" ", 1)[1]
    payload = decode_token(tok)
    if not payload:
        return None
    return {"id": int(payload["sub"]), "username": payload["username"]}


# ── Schemas ─────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: str
    username: str
    password: str
    display_name: str = ""
    is_artist: bool = False


class LoginRequest(BaseModel):
    email: str
    password: str


class MessageRequest(BaseModel):
    receiver_username: str
    listing_id: Optional[int] = None
    body: str


# ── Auth Endpoints ──────────────────────────────────────────────────────

@app.post("/api/signup")
def signup(req: SignupRequest):
    conn = get_db()
    existing = query_one(conn, f"SELECT id FROM users WHERE email = {P} OR username = {P}", (req.email, req.username))
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Email or username already taken")

    hashed = hash_password(req.password)
    user_id = execute(conn,
        f"INSERT INTO users (email, username, password_hash, display_name, is_artist) VALUES ({P}, {P}, {P}, {P}, {P})",
        (req.email, req.username, hashed, req.display_name or req.username, int(req.is_artist))
    )
    conn.commit()
    conn.close()

    token = create_token(user_id, req.username)
    return {"token": token, "user_id": user_id, "username": req.username}


@app.post("/api/login")
def login(req: LoginRequest):
    conn = get_db()
    user = query_one(conn, f"SELECT id, username, password_hash FROM users WHERE email = {P}", (req.email,))
    conn.close()

    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(user["id"], user["username"])
    return {"token": token, "user_id": user["id"], "username": user["username"]}


# ── Profile Endpoints ───────────────────────────────────────────────────

@app.get("/api/profile/{username}")
def get_profile(username: str, authorization: str = Header(None)):
    current = get_optional_user(authorization)
    conn = get_db()
    user = query_one(conn, f"SELECT id, username, display_name, bio, is_artist, created_at FROM users WHERE username = {P}", (username,))
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    listings = query(conn,
        f"SELECT id, title, price, medium, image_url, is_sold, created_at FROM listings WHERE artist_id = {P} ORDER BY created_at DESC",
        (user["id"],))

    # Follower count
    followers = query_one(conn, f"SELECT COUNT(*) as c FROM follows WHERE artist_id = {P}", (user["id"],))
    follower_count = followers["c"] if followers else 0

    # Is current user following?
    is_following = False
    if current:
        fol = query_one(conn, f"SELECT id FROM follows WHERE follower_id = {P} AND artist_id = {P}", (current["id"], user["id"]))
        is_following = fol is not None

    conn.close()

    return {
        "username": user["username"],
        "display_name": user["display_name"],
        "bio": user["bio"],
        "is_artist": bool(user["is_artist"]),
        "member_since": str(user["created_at"]),
        "followers": follower_count,
        "is_following": is_following,
        "listings": listings,
    }


@app.put("/api/profile")
def update_profile(
    display_name: str = Form(None),
    bio: str = Form(None),
    user=Depends(get_current_user),
):
    conn = get_db()
    if display_name is not None:
        execute(conn, f"UPDATE users SET display_name = {P} WHERE id = {P}", (display_name, user["id"]))
    if bio is not None:
        execute(conn, f"UPDATE users SET bio = {P} WHERE id = {P}", (bio, user["id"]))
    conn.commit()
    conn.close()
    return {"ok": True}


# ── Listing Endpoints ───────────────────────────────────────────────────

@app.post("/api/listings")
async def create_listing(
    title: str = Form(...),
    price: float = Form(...),
    medium: str = Form(""),
    dimensions: str = Form(""),
    description: str = Form(""),
    lat: float = Form(...),
    lng: float = Form(...),
    image: UploadFile = File(...),
    user=Depends(get_current_user),
):
    contents = await image.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 10MB)")

    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
    if cloud_name:
        upload_result = cloudinary.uploader.upload(contents, folder="artlocal", transformation=[{"width": 1200, "crop": "limit"}])
        image_url = upload_result["secure_url"]
        public_id = upload_result["public_id"]
    else:
        uploads_dir = Path(__file__).parent.parent / "data" / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        ext = image.filename.rsplit(".", 1)[-1] if "." in image.filename else "jpg"
        filename = f"{uuid.uuid4().hex}.{ext}"
        with open(uploads_dir / filename, "wb") as f:
            f.write(contents)
        image_url = f"/uploads/{filename}"
        public_id = None

    conn = get_db()
    listing_id = execute(conn,
        f"""INSERT INTO listings (artist_id, title, price, medium, dimensions, description, image_url, image_public_id, lat, lng)
           VALUES ({P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P})""",
        (user["id"], title, price, medium, dimensions, description, image_url, public_id, lat, lng))
    conn.commit()
    conn.close()
    return {"id": listing_id, "image_url": image_url}


@app.get("/api/listings")
def get_listings(
    lat: float = 0, lng: float = 0, radius: float = 50, limit: int = 50,
    medium: str = "", min_price: float = 0, max_price: float = 0,
    q: str = "",
):
    """Get listings with optional filters."""
    conn = get_db()
    rows = query(conn,
        f"""SELECT l.id, l.title, l.price, l.medium, l.dimensions, l.image_url,
                  l.lat, l.lng, l.created_at, l.is_sold,
                  u.username, u.display_name
           FROM listings l
           JOIN users u ON l.artist_id = u.id
           WHERE l.is_sold = 0
           ORDER BY l.created_at DESC
           LIMIT {P}""",
        (limit * 2,))
    conn.close()

    results = []
    for row in rows:
        # Apply filters
        if medium and row.get("medium", "").lower() != medium.lower():
            continue
        if min_price and row["price"] < min_price:
            continue
        if max_price and row["price"] > max_price:
            continue
        if q and q.lower() not in (row.get("title", "") + " " + (row.get("medium") or "") + " " + (row.get("display_name") or "")).lower():
            continue

        item = dict(row)
        if lat != 0 or lng != 0:
            dist = haversine_miles(lat, lng, row["lat"], row["lng"])
            item["distance_miles"] = round(dist, 1)
        else:
            item["distance_miles"] = None
        results.append(item)

    if lat != 0 or lng != 0:
        results.sort(key=lambda x: x["distance_miles"])
    return results[:limit]


@app.get("/api/listings/{listing_id}")
def get_listing(listing_id: int):
    conn = get_db()
    row = query_one(conn,
        f"""SELECT l.*, u.username, u.display_name
           FROM listings l JOIN users u ON l.artist_id = u.id
           WHERE l.id = {P}""", (listing_id,))
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Listing not found")
    return row


@app.put("/api/listings/{listing_id}/sold")
def mark_sold(listing_id: int, user=Depends(get_current_user)):
    conn = get_db()
    listing = query_one(conn, f"SELECT artist_id FROM listings WHERE id = {P}", (listing_id,))
    if not listing or listing["artist_id"] != user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Not your listing")
    execute(conn, f"UPDATE listings SET is_sold = 1 WHERE id = {P}", (listing_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.delete("/api/listings/{listing_id}")
def delete_listing(listing_id: int, user=Depends(get_current_user)):
    conn = get_db()
    listing = query_one(conn, f"SELECT artist_id, image_public_id FROM listings WHERE id = {P}", (listing_id,))
    if not listing or listing["artist_id"] != user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Not your listing")
    if listing.get("image_public_id"):
        try:
            cloudinary.uploader.destroy(listing["image_public_id"])
        except Exception:
            pass
    execute(conn, f"DELETE FROM listings WHERE id = {P}", (listing_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


# ── Messaging Endpoints ─────────────────────────────────────────────────

@app.post("/api/messages")
def send_message(req: MessageRequest, user=Depends(get_current_user)):
    conn = get_db()
    receiver = query_one(conn, f"SELECT id FROM users WHERE username = {P}", (req.receiver_username,))
    if not receiver:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    if receiver["id"] == user["id"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Cannot message yourself")

    execute(conn,
        f"INSERT INTO messages (sender_id, receiver_id, listing_id, body) VALUES ({P}, {P}, {P}, {P})",
        (user["id"], receiver["id"], req.listing_id, req.body))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/api/messages")
def get_conversations(user=Depends(get_current_user)):
    """Get list of conversations (unique users you've chatted with)."""
    conn = get_db()
    rows = query(conn, f"""
        SELECT DISTINCT
            CASE WHEN sender_id = {P} THEN receiver_id ELSE sender_id END as other_id
        FROM messages
        WHERE sender_id = {P} OR receiver_id = {P}
    """, (user["id"], user["id"], user["id"]))

    conversations = []
    for row in rows:
        other = query_one(conn, f"SELECT id, username, display_name FROM users WHERE id = {P}", (row["other_id"],))
        if other:
            # Get last message
            last = query_one(conn, f"""
                SELECT body, created_at, sender_id FROM messages
                WHERE (sender_id = {P} AND receiver_id = {P}) OR (sender_id = {P} AND receiver_id = {P})
                ORDER BY created_at DESC LIMIT 1
            """, (user["id"], other["id"], other["id"], user["id"]))
            # Unread count
            unread = query_one(conn, f"""
                SELECT COUNT(*) as c FROM messages
                WHERE sender_id = {P} AND receiver_id = {P} AND is_read = 0
            """, (other["id"], user["id"]))
            conversations.append({
                "username": other["username"],
                "display_name": other["display_name"],
                "last_message": last["body"] if last else "",
                "last_time": str(last["created_at"]) if last else "",
                "unread": unread["c"] if unread else 0,
            })
    conn.close()
    return conversations


@app.get("/api/messages/{username}")
def get_messages(username: str, user=Depends(get_current_user)):
    """Get message history with a specific user."""
    conn = get_db()
    other = query_one(conn, f"SELECT id FROM users WHERE username = {P}", (username,))
    if not other:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    messages = query(conn, f"""
        SELECT m.id, m.body, m.created_at, m.sender_id, m.listing_id,
               u.username as sender_username
        FROM messages m JOIN users u ON m.sender_id = u.id
        WHERE (m.sender_id = {P} AND m.receiver_id = {P})
           OR (m.sender_id = {P} AND m.receiver_id = {P})
        ORDER BY m.created_at ASC
    """, (user["id"], other["id"], other["id"], user["id"]))

    # Mark as read
    execute(conn, f"UPDATE messages SET is_read = 1 WHERE sender_id = {P} AND receiver_id = {P} AND is_read = 0",
            (other["id"], user["id"]))
    conn.commit()
    conn.close()
    return messages


# ── Follow Endpoints ────────────────────────────────────────────────────

@app.post("/api/follow/{username}")
def follow_artist(username: str, user=Depends(get_current_user)):
    conn = get_db()
    artist = query_one(conn, f"SELECT id FROM users WHERE username = {P}", (username,))
    if not artist:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    if artist["id"] == user["id"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Cannot follow yourself")

    existing = query_one(conn, f"SELECT id FROM follows WHERE follower_id = {P} AND artist_id = {P}", (user["id"], artist["id"]))
    if existing:
        conn.close()
        return {"ok": True, "action": "already_following"}

    execute(conn, f"INSERT INTO follows (follower_id, artist_id) VALUES ({P}, {P})", (user["id"], artist["id"]))
    conn.commit()
    conn.close()
    return {"ok": True, "action": "followed"}


@app.delete("/api/follow/{username}")
def unfollow_artist(username: str, user=Depends(get_current_user)):
    conn = get_db()
    artist = query_one(conn, f"SELECT id FROM users WHERE username = {P}", (username,))
    if not artist:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    execute(conn, f"DELETE FROM follows WHERE follower_id = {P} AND artist_id = {P}", (user["id"], artist["id"]))
    conn.commit()
    conn.close()
    return {"ok": True, "action": "unfollowed"}


# ── Favorites Endpoints ─────────────────────────────────────────────────

@app.post("/api/favorites/{listing_id}")
def add_favorite(listing_id: int, user=Depends(get_current_user)):
    conn = get_db()
    existing = query_one(conn, f"SELECT id FROM favorites WHERE user_id = {P} AND listing_id = {P}", (user["id"], listing_id))
    if existing:
        conn.close()
        return {"ok": True, "action": "already_saved"}
    execute(conn, f"INSERT INTO favorites (user_id, listing_id) VALUES ({P}, {P})", (user["id"], listing_id))
    conn.commit()
    conn.close()
    return {"ok": True, "action": "saved"}


@app.delete("/api/favorites/{listing_id}")
def remove_favorite(listing_id: int, user=Depends(get_current_user)):
    conn = get_db()
    execute(conn, f"DELETE FROM favorites WHERE user_id = {P} AND listing_id = {P}", (user["id"], listing_id))
    conn.commit()
    conn.close()
    return {"ok": True, "action": "removed"}


@app.get("/api/favorites")
def get_favorites(user=Depends(get_current_user)):
    conn = get_db()
    rows = query(conn, f"""
        SELECT l.id, l.title, l.price, l.medium, l.image_url, l.is_sold,
               u.username, u.display_name
        FROM favorites f
        JOIN listings l ON f.listing_id = l.id
        JOIN users u ON l.artist_id = u.id
        WHERE f.user_id = {P}
        ORDER BY f.created_at DESC
    """, (user["id"],))
    conn.close()
    return rows


# ── Serve Frontend ──────────────────────────────────────────────────────

UPLOADS_DIR = Path(__file__).parent.parent / "data" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/uploads/{filename}")
def serve_upload(filename: str):
    filepath = UPLOADS_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404)
    return FileResponse(str(filepath))


@app.get("/")
def serve_index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))
