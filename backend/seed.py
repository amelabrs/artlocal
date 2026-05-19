"""Seed the database with demo listings for testing."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from models import get_db, init_db
from auth import hash_password

# Sample art images from Unsplash (free, no API key needed for hotlinking demos)
DEMO_IMAGES = [
    "https://images.unsplash.com/photo-1579783902614-a3fb3927b6a5?w=600",
    "https://images.unsplash.com/photo-1547826039-bfc35e0f1ea8?w=600",
    "https://images.unsplash.com/photo-1578301978693-85fa9c0320b9?w=600",
    "https://images.unsplash.com/photo-1549289524-06cf8837ace5?w=600",
    "https://images.unsplash.com/photo-1541961017774-22349e4a1262?w=600",
    "https://images.unsplash.com/photo-1513364776144-60967b0f800f?w=600",
    "https://images.unsplash.com/photo-1460661419201-fd4cecdf8a8b?w=600",
    "https://images.unsplash.com/photo-1605721911519-3dfeb3be25e7?w=600",
    "https://images.unsplash.com/photo-1582201942988-13e60e4556ee?w=600",
    "https://images.unsplash.com/photo-1574182245530-967d9b3831af?w=600",
    "https://images.unsplash.com/photo-1501472312651-726afe119dad?w=600",
    "https://images.unsplash.com/photo-1518998053901-5348d3961a04?w=600",
]

# Demo artists (lat/lng near San Francisco for testing)
ARTISTS = [
    {"email": "luna@demo.com", "username": "luna_creates", "display_name": "Luna Martinez", "bio": "Oil painter inspired by the Bay Area coastline"},
    {"email": "kai@demo.com", "username": "kai.art", "display_name": "Kai Chen", "bio": "Digital artist & illustrator"},
    {"email": "river@demo.com", "username": "riverstone_art", "display_name": "River Stone", "bio": "Mixed media sculptor working with found objects"},
]

# Demo listings (spread around a central point)
# Using SF area coordinates with slight variations
BASE_LAT, BASE_LNG = 37.7749, -122.4194

LISTINGS = [
    {"title": "Golden Hour on the Bay", "price": 37500, "medium": "Oil", "dimensions": "24x36 in", "description": "Sunset over the San Francisco Bay, painted en plein air.", "lat_offset": 0.01, "lng_offset": -0.005},
    {"title": "Urban Bloom", "price": 9999, "medium": "Acrylic", "dimensions": "16x20 in", "description": "Abstract florals inspired by city gardens.", "lat_offset": -0.008, "lng_offset": 0.003},
    {"title": "Digital Dreams #7", "price": 6500, "medium": "Digital", "dimensions": "4000x3000 px", "description": "Generative art piece, printed on archival paper.", "lat_offset": 0.015, "lng_offset": 0.01},
    {"title": "Driftwood Sculpture", "price": 54000, "medium": "Sculpture", "dimensions": "18x12x8 in", "description": "Found driftwood assembled into an abstract form.", "lat_offset": -0.02, "lng_offset": -0.01},
    {"title": "Morning Fog", "price": 23000, "medium": "Watercolor", "dimensions": "11x14 in", "description": "Soft watercolor of fog rolling through the hills.", "lat_offset": 0.005, "lng_offset": 0.008},
    {"title": "Neon Nights", "price": 14500, "medium": "Digital", "dimensions": "3000x4000 px", "description": "Cyberpunk-inspired cityscape.", "lat_offset": -0.012, "lng_offset": 0.015},
    {"title": "Ceramic Bowl — Ocean Glaze", "price": 7800, "medium": "Other", "dimensions": "8x8x4 in", "description": "Handthrown stoneware with custom blue glaze.", "lat_offset": 0.025, "lng_offset": -0.008},
    {"title": "Abstract in Red", "price": 26500, "medium": "Acrylic", "dimensions": "30x40 in", "description": "Bold gestural painting on stretched canvas.", "lat_offset": -0.003, "lng_offset": -0.02},
    {"title": "Portrait Commission Sample", "price": 42000, "medium": "Oil", "dimensions": "16x20 in", "description": "Oil portrait — commissions open!", "lat_offset": 0.018, "lng_offset": 0.005},
    {"title": "Collage: City Layers", "price": 12500, "medium": "Mixed Media", "dimensions": "12x16 in", "description": "Newspaper and acrylic on wood panel.", "lat_offset": -0.015, "lng_offset": 0.012},
    {"title": "Sunset Print (Limited Ed.)", "price": 3750, "medium": "Print", "dimensions": "8x10 in", "description": "Giclée print, edition of 50. Signed & numbered.", "lat_offset": 0.008, "lng_offset": -0.015},
    {"title": "Wire & Stone Pendant", "price": 5400, "medium": "Other", "dimensions": "2x1 in", "description": "Wearable art — sterling silver wire with beach stone.", "lat_offset": -0.005, "lng_offset": 0.002},
]


def seed():
    init_db()
    conn = get_db()

    # Check if already seeded
    existing = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    if existing > 0:
        # Re-seed: drop old data
        conn.execute("DELETE FROM listings")
        conn.execute("DELETE FROM users")
        conn.commit()

    # Create demo artists
    artist_ids = []
    for artist in ARTISTS:
        hashed = hash_password("demo1234")
        cursor = conn.execute(
            "INSERT INTO users (email, username, password_hash, display_name, bio, is_artist) VALUES (?, ?, ?, ?, ?, 1)",
            (artist["email"], artist["username"], hashed, artist["display_name"], artist["bio"])
        )
        artist_ids.append(cursor.lastrowid)

    # Create demo listings
    for i, listing in enumerate(LISTINGS):
        artist_id = artist_ids[i % len(artist_ids)]
        lat = BASE_LAT + listing["lat_offset"]
        lng = BASE_LNG + listing["lng_offset"]
        image_url = DEMO_IMAGES[i % len(DEMO_IMAGES)]

        conn.execute(
            """INSERT INTO listings (artist_id, title, price, medium, dimensions, description, image_url, lat, lng)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (artist_id, listing["title"], listing["price"], listing["medium"],
             listing["dimensions"], listing["description"], image_url, lat, lng)
        )

    conn.commit()
    conn.close()
    print(f"✅ Seeded {len(ARTISTS)} artists and {len(LISTINGS)} listings!")
    print(f"   Demo login: luna@demo.com / demo1234")
    print(f"   Open http://127.0.0.1:8888 to see the feed")


if __name__ == "__main__":
    seed()
