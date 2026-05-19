"""ArtLocal — Main FastAPI App."""

import os
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path

from models import get_db, init_db
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


@app.on_event("startup")
def startup():
    init_db()
    # Auto-seed demo data if DB is empty
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) as c FROM listings").fetchone()["c"]
    conn.close()
    if count == 0:
        from seed import seed
        seed()


# ── Auth dependency ─────────────────────────────────────────────────────

def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
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


# ── Auth Endpoints ──────────────────────────────────────────────────────

@app.post("/api/signup")
def signup(req: SignupRequest):
    conn = get_db()
    # Check existing
    existing = conn.execute(
        "SELECT id FROM users WHERE email = ? OR username = ?",
        (req.email, req.username)
    ).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Email or username already taken")

    hashed = hash_password(req.password)
    cursor = conn.execute(
        "INSERT INTO users (email, username, password_hash, display_name, is_artist) VALUES (?, ?, ?, ?, ?)",
        (req.email, req.username, hashed, req.display_name or req.username, int(req.is_artist))
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()

    token = create_token(user_id, req.username)
    return {"token": token, "user_id": user_id, "username": req.username}


@app.post("/api/login")
def login(req: LoginRequest):
    conn = get_db()
    user = conn.execute(
        "SELECT id, username, password_hash FROM users WHERE email = ?",
        (req.email,)
    ).fetchone()
    conn.close()

    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(user["id"], user["username"])
    return {"token": token, "user_id": user["id"], "username": user["username"]}


# ── Profile Endpoints ───────────────────────────────────────────────────

@app.get("/api/profile/{username}")
def get_profile(username: str):
    conn = get_db()
    user = conn.execute(
        "SELECT id, username, display_name, bio, is_artist, created_at FROM users WHERE username = ?",
        (username,)
    ).fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    listings = conn.execute(
        "SELECT id, title, price, medium, image_url, is_sold, created_at FROM listings WHERE artist_id = ? ORDER BY created_at DESC",
        (user["id"],)
    ).fetchall()
    conn.close()

    return {
        "username": user["username"],
        "display_name": user["display_name"],
        "bio": user["bio"],
        "is_artist": bool(user["is_artist"]),
        "member_since": user["created_at"],
        "listings": [dict(l) for l in listings],
    }


@app.put("/api/profile")
def update_profile(
    display_name: str = Form(None),
    bio: str = Form(None),
    user=Depends(get_current_user),
):
    conn = get_db()
    if display_name is not None:
        conn.execute("UPDATE users SET display_name = ? WHERE id = ?", (display_name, user["id"]))
    if bio is not None:
        conn.execute("UPDATE users SET bio = ? WHERE id = ?", (bio, user["id"]))
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
    # Upload image to Cloudinary
    contents = await image.read()
    if len(contents) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="Image too large (max 10MB)")

    upload_result = cloudinary.uploader.upload(
        contents,
        folder="artlocal",
        transformation=[{"width": 1200, "crop": "limit"}],
    )
    image_url = upload_result["secure_url"]
    public_id = upload_result["public_id"]

    conn = get_db()
    cursor = conn.execute(
        """INSERT INTO listings (artist_id, title, price, medium, dimensions, description, image_url, image_public_id, lat, lng)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user["id"], title, price, medium, dimensions, description, image_url, public_id, lat, lng)
    )
    conn.commit()
    listing_id = cursor.lastrowid
    conn.close()

    return {"id": listing_id, "image_url": image_url}


@app.get("/api/listings")
def get_listings(lat: float = 0, lng: float = 0, radius: float = 25, limit: int = 50):
    """Get listings sorted by distance from the given coordinates."""
    conn = get_db()
    rows = conn.execute(
        """SELECT l.id, l.title, l.price, l.medium, l.dimensions, l.image_url,
                  l.lat, l.lng, l.created_at, l.is_sold,
                  u.username, u.display_name
           FROM listings l
           JOIN users u ON l.artist_id = u.id
           WHERE l.is_sold = 0
           ORDER BY l.created_at DESC
           LIMIT ?""",
        (limit,)
    ).fetchall()
    conn.close()

    results = []
    for row in rows:
        item = dict(row)
        if lat != 0 or lng != 0:
            dist = haversine_miles(lat, lng, row["lat"], row["lng"])
            item["distance_miles"] = round(dist, 1)
        else:
            item["distance_miles"] = None
        results.append(item)

    # Sort by distance if location available
    if lat != 0 or lng != 0:
        results.sort(key=lambda x: x["distance_miles"])
    return results


@app.get("/api/listings/{listing_id}")
def get_listing(listing_id: int):
    conn = get_db()
    row = conn.execute(
        """SELECT l.*, u.username, u.display_name
           FROM listings l
           JOIN users u ON l.artist_id = u.id
           WHERE l.id = ?""",
        (listing_id,)
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Listing not found")
    return dict(row)


@app.put("/api/listings/{listing_id}/sold")
def mark_sold(listing_id: int, user=Depends(get_current_user)):
    conn = get_db()
    listing = conn.execute(
        "SELECT artist_id FROM listings WHERE id = ?", (listing_id,)
    ).fetchone()
    if not listing or listing["artist_id"] != user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Not your listing")
    conn.execute("UPDATE listings SET is_sold = 1 WHERE id = ?", (listing_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.delete("/api/listings/{listing_id}")
def delete_listing(listing_id: int, user=Depends(get_current_user)):
    conn = get_db()
    listing = conn.execute(
        "SELECT artist_id, image_public_id FROM listings WHERE id = ?", (listing_id,)
    ).fetchone()
    if not listing or listing["artist_id"] != user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Not your listing")

    # Delete from Cloudinary
    if listing["image_public_id"]:
        try:
            cloudinary.uploader.destroy(listing["image_public_id"])
        except Exception:
            pass  # Non-critical

    conn.execute("DELETE FROM listings WHERE id = ?", (listing_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


# ── Serve Frontend ──────────────────────────────────────────────────────

@app.get("/")
def serve_index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))
