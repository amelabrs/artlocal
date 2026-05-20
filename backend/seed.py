"""Seed the database with demo listings for testing."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from models import get_db, init_db
from auth import hash_password

# Sample art images from Unsplash (Indian art, crochet, handmade)
DEMO_IMAGES = [
    "https://images.unsplash.com/photo-1605721911519-3dfeb3be25e7?w=600",  # mandala
    "https://images.unsplash.com/photo-1582738411706-bfc8e691d1c2?w=600",  # indian art
    "https://images.unsplash.com/photo-1567361808960-dec9cb578182?w=600",  # crochet
    "https://images.unsplash.com/photo-1596727147705-61a532a659bd?w=600",  # madhubani style
    "https://images.unsplash.com/photo-1578301978693-85fa9c0320b9?w=600",  # colorful abstract
    "https://images.unsplash.com/photo-1615729947596-a598e5de0ab3?w=600",  # yarn/crochet
    "https://images.unsplash.com/photo-1579783902614-a3fb3927b6a5?w=600",  # painting
    "https://images.unsplash.com/photo-1513364776144-60967b0f800f?w=600",  # watercolor
    "https://images.unsplash.com/photo-1582201942988-13e60e4556ee?w=600",  # ceramic
    "https://images.unsplash.com/photo-1574182245530-967d9b3831af?w=600",  # textile
    "https://images.unsplash.com/photo-1549289524-06cf8837ace5?w=600",  # abstract
    "https://images.unsplash.com/photo-1547826039-bfc35e0f1ea8?w=600",  # handmade
    "https://images.unsplash.com/photo-1601121141461-9d6647bca1ed?w=600",  # rangoli
    "https://images.unsplash.com/photo-1518998053901-5348d3961a04?w=600",  # colorful
]

# Demo artists
ARTISTS = [
    {"email": "priya@demo.com", "username": "priya_arts", "display_name": "Priya Sharma", "bio": "Madhubani & mandala artist from Jaipur. Traditional meets modern."},
    {"email": "ananya@demo.com", "username": "ananya.crochet", "display_name": "Ananya Nair", "bio": "Crochet artist & fiber art lover. Custom orders welcome 🧶"},
    {"email": "vikram@demo.com", "username": "vikram.studio", "display_name": "Vikram Patel", "bio": "Contemporary Indian art — oils, acrylics & mixed media"},
    {"email": "meera@demo.com", "username": "meera_creates", "display_name": "Meera Iyer", "bio": "Warli art, Kalamkari prints & handmade pottery"},
]

# Demo listings — Indian coordinates (Mumbai area)
BASE_LAT, BASE_LNG = 19.0760, 72.8777

LISTINGS = [
    {"title": "Madhubani Peacock", "price": 8500, "medium": "Acrylic", "dimensions": "18x24 in", "description": "Traditional Madhubani peacock motif on handmade paper. Vibrant natural dyes.", "lat_offset": 0.01, "lng_offset": -0.005},
    {"title": "Crochet Mandala Wall Hanging", "price": 3200, "medium": "Other", "dimensions": "24 in diameter", "description": "Handmade crochet mandala in sunset colours. Cotton yarn, wooden hoop.", "lat_offset": -0.008, "lng_offset": 0.003},
    {"title": "Mumbai Monsoon", "price": 15000, "medium": "Oil", "dimensions": "24x36 in", "description": "Oil painting capturing the magic of Mumbai rains. Marine Drive at dusk.", "lat_offset": 0.015, "lng_offset": 0.01},
    {"title": "Crochet Amigurumi Set — Indian Animals", "price": 2800, "medium": "Other", "dimensions": "6 in each", "description": "Set of 3: elephant, peacock, and tiger. Handmade with love 🧶", "lat_offset": -0.02, "lng_offset": -0.01},
    {"title": "Warli Tribal Art — Harvest Dance", "price": 6500, "medium": "Acrylic", "dimensions": "16x20 in", "description": "Contemporary Warli painting on canvas. White on terracotta background.", "lat_offset": 0.005, "lng_offset": 0.008},
    {"title": "Crochet Market Bag — Boho", "price": 1500, "medium": "Other", "dimensions": "14x16 in", "description": "Reusable crochet tote in earthy tones. Sturdy cotton cord.", "lat_offset": -0.012, "lng_offset": 0.015},
    {"title": "Terracotta Diya Set (6)", "price": 1200, "medium": "Other", "dimensions": "3 in each", "description": "Hand-painted terracotta diyas. Perfect for Diwali or home decor.", "lat_offset": 0.025, "lng_offset": -0.008},
    {"title": "Ganesha in Gold Leaf", "price": 28000, "medium": "Mixed Media", "dimensions": "20x24 in", "description": "Contemporary Ganesha with gold leaf accents on textured canvas.", "lat_offset": -0.003, "lng_offset": -0.02},
    {"title": "Crochet Baby Blanket — Rainbow", "price": 4500, "medium": "Other", "dimensions": "36x42 in", "description": "Soft granny-square blanket in pastel rainbow. Hypoallergenic acrylic yarn.", "lat_offset": 0.018, "lng_offset": 0.005},
    {"title": "Kalamkari Tree of Life", "price": 12000, "medium": "Other", "dimensions": "24x36 in", "description": "Hand-painted Kalamkari on cotton fabric. Natural vegetable dyes.", "lat_offset": -0.015, "lng_offset": 0.012},
    {"title": "Rajasthani Miniature — Radha Krishna", "price": 18500, "medium": "Watercolor", "dimensions": "8x10 in", "description": "Detailed miniature painting on silk. 22k gold detailing.", "lat_offset": 0.008, "lng_offset": -0.015},
    {"title": "Crochet Coasters Set (6) — Chai Time", "price": 850, "medium": "Other", "dimensions": "4 in each", "description": "Colourful crochet coasters shaped like teacups. Great housewarming gift!", "lat_offset": -0.005, "lng_offset": 0.002},
    {"title": "Pichwai Lotus Pond", "price": 35000, "medium": "Oil", "dimensions": "30x40 in", "description": "Traditional Pichwai style lotus pond. Rich colours on cotton cloth.", "lat_offset": 0.009, "lng_offset": -0.007},
    {"title": "Crochet Jhumka Earrings", "price": 650, "medium": "Other", "dimensions": "2.5 in drop", "description": "Handmade crochet jhumkas with beads. Lightweight & colourful!", "lat_offset": -0.011, "lng_offset": 0.009},
]


def seed():
    from models import DATABASE_URL, query_one, execute
    init_db()
    conn = get_db()
    P = "%s" if DATABASE_URL else "?"

    # Check if already seeded
    existing = query_one(conn, "SELECT COUNT(*) as c FROM users")
    if existing and existing["c"] > 0:
        # Re-seed: drop old data (order matters for FK)
        execute(conn, "DELETE FROM favorites")
        execute(conn, "DELETE FROM follows")
        execute(conn, "DELETE FROM messages")
        execute(conn, "DELETE FROM listings")
        execute(conn, "DELETE FROM users")
        conn.commit()

    # Create demo artists
    artist_ids = []
    for artist in ARTISTS:
        hashed = hash_password("demo1234")
        aid = execute(conn,
            f"INSERT INTO users (email, username, password_hash, display_name, bio, is_artist) VALUES ({P}, {P}, {P}, {P}, {P}, 1)",
            (artist["email"], artist["username"], hashed, artist["display_name"], artist["bio"]))
        artist_ids.append(aid)

    # Create demo listings
    for i, listing in enumerate(LISTINGS):
        artist_id = artist_ids[i % len(artist_ids)]
        lat = BASE_LAT + listing["lat_offset"]
        lng = BASE_LNG + listing["lng_offset"]
        image_url = DEMO_IMAGES[i % len(DEMO_IMAGES)]

        execute(conn,
            f"""INSERT INTO listings (artist_id, title, price, medium, dimensions, description, image_url, lat, lng)
               VALUES ({P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P})""",
            (artist_id, listing["title"], listing["price"], listing["medium"],
             listing["dimensions"], listing["description"], image_url, lat, lng))

    conn.commit()
    conn.close()
    print(f"✅ Seeded {len(ARTISTS)} artists and {len(LISTINGS)} listings!")
    print(f"   Demo login: priya@demo.com / demo1234")
    print(f"   Open http://127.0.0.1:8888 to see the feed")


if __name__ == "__main__":
    seed()
