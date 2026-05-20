# ArtLocal — Implementation Strategy

## TL;DR Difficulty Rating

| Aspect | Difficulty (1-5) | Notes |
|--------|:-:|-------|
| Overall concept | ⭐⭐⭐⭐ | Multi-sided marketplace with payments — not trivial |
| MVP (Stage 1-2) | ⭐⭐ | Very achievable with your current skills |
| Payments/Escrow | ⭐⭐⭐⭐ | Stripe Connect is well-documented but requires care |
| AR Preview | ⭐⭐⭐⭐⭐ | Skip for now. Future feature. |
| Geo-location feed | ⭐⭐ | Browser geolocation API is straightforward |

---

## Do You Need React? No.

The spec says "React Native" or "Flutter" because it assumes a native mobile app. **You don't need either.** Here's why:

- Your existing apps (BirdBrain, LetterBrain) are **Progressive Web Apps (PWAs)** — vanilla HTML/CSS/JS with a manifest.json
- A PWA can do everything ArtLocal Stage 1-3 needs: camera access, GPS, push notifications, installable on phone
- React is a JavaScript framework that adds complexity (build tools, node_modules, JSX syntax). It's useful for very large apps but overkill for getting started
- **You can always migrate later** if the app grows massive

**Recommended stack (matches your skills):**

| Layer | Choice | Why |
|-------|--------|-----|
| Frontend | PWA (vanilla JS + CSS) | You already know this. Works on all phones. |
| Backend | Python (Flask or FastAPI) | You already know Python. FastAPI is modern & fast. |
| Database | SQLite → PostgreSQL | Start simple, migrate when you have users |
| Hosting | Render.com | You already use this (LetterBrain) |
| Payments | Stripe Connect | Industry standard, great docs |
| Maps | Leaflet.js + OpenStreetMap | Free. No API key needed to start |
| File Storage | Cloudinary (free tier) | Image uploads/resizing without managing servers |

---

## Staged Implementation Plan

### Stage 1: "The Gallery" (1-2 weeks) ✅ EASIEST START

**Goal:** Artists can list artwork, anyone nearby can browse. No payments yet.

Build:
- [ ] Landing page with masonry grid (CSS Grid or a tiny lib like Masonry.js)
- [ ] Artist signup/login (email + password via Flask-Login or simple JWT)
- [ ] Upload form: photo, title, price, medium, dimensions
- [ ] Store images on Cloudinary (free tier: 25GB)
- [ ] Geo-location: ask browser for GPS → store lat/lng with each listing
- [ ] Discovery feed: sort listings by distance from viewer
- [ ] Distance badge on each card ("1.2 mi away")
- [ ] Basic artist profile page (bio, gallery of their work)

**What you'll learn:** File uploads, geolocation API, distance math (haversine formula)

**Can demo:** "Look, art near me!" — this alone is interesting.

---

### Stage 2: "The Marketplace" (2-3 weeks)

**Goal:** Buyers can contact artists. Artists manage listings.

Build:
- [ ] "Message Artist" button → in-app messaging (WebSocket or simple polling)
- [ ] Artist dashboard: active listings, mark as sold, edit
- [ ] Buyer profile: saved/favorites, purchase intent
- [ ] Search & filters: price range, distance slider, category, color
- [ ] "Follow" an artist
- [ ] Push notifications (PWA supports this)

**What you'll learn:** Real-time messaging, more complex queries

---

### Stage 3: "The Money" (3-4 weeks)

**Goal:** Payments flow through the app. This is where it becomes a real business.

Build:
- [ ] Stripe Connect onboarding (artists link their bank accounts)
- [ ] "Buy Now" button → Stripe Checkout
- [ ] Escrow logic: hold funds, release on confirmation
- [ ] QR code generation (per transaction) — use `qrcode` Python library
- [ ] QR scanner in browser (use `html5-qrcode` JS library)
- [ ] Scan → confirms receipt → releases funds to artist
- [ ] Platform fee (your cut: typically 5-15%)

**What you'll learn:** Payment APIs, escrow patterns, QR codes

---

### Stage 4: "The Polish" (ongoing)

**Goal:** Make it feel premium.

Build:
- [ ] Image carousel on detail view
- [ ] Artist analytics (views, clicks — simple counter in DB)
- [ ] "Commission Request" button + form
- [ ] Verified artist badges
- [ ] Response time tracking
- [ ] Email notifications (SendGrid free tier)

---

### Stage 5: "The Future" (way later)

- AR Wall Preview (needs ARKit/WebXR — complex)
- Native mobile app (if PWA limitations become a problem)
- AI-powered color search
- Delivery logistics integration

---

## Architecture Diagram (Simple)

```
┌─────────────────────────────────────────────┐
│              BROWSER (PWA)                   │
│  index.html / app.js / style.css            │
│  manifest.json + service-worker.js          │
└─────────────────┬───────────────────────────┘
                  │ HTTPS (JSON API)
                  ▼
┌─────────────────────────────────────────────┐
│         PYTHON BACKEND (FastAPI)            │
│  /api/listings  /api/auth  /api/messages    │
│  /api/payments  /api/profile                │
└──────┬──────────┬───────────────┬───────────┘
       │          │               │
       ▼          ▼               ▼
   ┌───────┐  ┌──────────┐  ┌──────────┐
   │ SQLite │  │Cloudinary│  │  Stripe  │
   │  (DB)  │  │ (images) │  │ Connect  │
   └───────┘  └──────────┘  └──────────┘
```

---

## File Structure (Target)

```
artsy/
├── ArtLocal.md                 ← spec (exists)
├── IMPLEMENTATION_STRATEGY.md  ← this file
├── backend/
│   ├── app.py                  ← FastAPI main
│   ├── models.py               ← DB models
│   ├── auth.py                 ← login/signup
│   ├── listings.py             ← CRUD for artwork
│   ├── geo.py                  ← distance calculations
│   ├── payments.py             ← Stripe integration
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   ├── manifest.json
│   └── service-worker.js
└── data/
    └── artlocal.db             ← SQLite database
```

---

## Quick Wins (Do These First)

1. **Masonry image grid** — visually impressive, just CSS. Takes 30 min.
2. **Geolocation badge** — `navigator.geolocation.getCurrentPosition()` is 5 lines of JS.
3. **Image upload to Cloudinary** — free account, 10 lines of Python.
4. **Distance sorting** — haversine formula is a copy-paste function.

These 4 things together = a working demo that looks like a real app.

---

## Key Decisions to Make Later

| Decision | Options | When to decide |
|----------|---------|----------------|
| Domain name | artlocal.app? | Before launch |
| Platform fee % | 5-15% | Before Stage 3 |
| Max listing distance | 10mi? 25mi? 50mi? | Can be user-configurable |
| Moderation | Manual? AI? Community? | When you have >50 users |
| Legal | Terms of service, liability | Before real money flows |

---

## Summary

You absolutely can build this. The spec looks big but it's really just:
- A gallery website (you've done this) +
- Location awareness (browser API, easy) +
- Payments (Stripe, medium difficulty) +
- Messaging (doable)

Start with Stage 1. Get art on a map. Everything else is incremental.

---

## Test Cases

### Stage 1 — "The Gallery"

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1.1 | Feed loads without login | Open app | Masonry grid shows seed listings with images, prices in ₹, artist names |
| 1.2 | Geolocation distance | Allow location permission | Distance badges appear (e.g. "2.3 mi"); feed sorts by proximity |
| 1.3 | Feed works without location | Deny location | Feed still loads, "Showing all art" status, no distance badges |
| 1.4 | Sign up | Click Sign In → Sign Up → fill form → submit | Token stored, button shows "Sign Out" |
| 1.5 | Login | Sign in with `priya@demo.com` / `demo1234` | Succeeds, auth state persists on reload |
| 1.6 | Post artwork | Tap ➕ → fill title/price/photo → submit | New card appears in feed; shows in profile |
| 1.7 | Post without image | Try to submit without selecting a photo | Validation prevents submit (required attribute) |
| 1.8 | Detail view | Tap any card | Modal shows full image, title, price, medium, artist name |
| 1.9 | Delete listing | Open your own listing → tap Delete → confirm | Listing removed from feed |
| 1.10 | Mark sold | Open your own listing → tap Mark as Sold | Listing disappears from feed (is_sold filter) |
| 1.11 | Profile view | Tap 👤 Profile | Shows your display name, all your listings (including sold) |
| 1.12 | Search | Type "crochet" in search bar | Only listings matching "crochet" in title/medium/artist shown |
| 1.13 | Modal close on backdrop | Click dark area outside any modal | Modal closes |

### Stage 2 — "The Marketplace"

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 2.1 | Filter by medium | Select "Oil" from Filter dropdown → tap Filter | Only oil paintings shown |
| 2.2 | Filter by price | Set min ₹500 max ₹5000 → Filter | Only listings in that range |
| 2.3 | Clear filters | Tap ✕ clear button | All listings reload |
| 2.4 | Combined filters | Set medium + price range → Filter | Both filters applied together |
| 2.5 | Save to favorites | Open listing detail → tap ❤️ Save | Button changes to "💖 Saved" |
| 2.6 | Remove favorite | Tap "💖 Saved" on already-saved item | Button reverts to "❤️ Save" |
| 2.7 | Follow artist | Open another artist's listing → tap ➕ Follow | Button changes to "✓ Following" |
| 2.8 | Unfollow artist | Tap "✓ Following" | Button reverts to "➕ Follow" |
| 2.9 | Message from detail | Open listing → tap 💬 Message Artist | Chat opens with that artist in message modal |
| 2.10 | Send message | Type text in chat → Send | Message appears in chat as "mine" bubble |
| 2.11 | Receive message | Log in as another user and reply | Message appears in chat as "theirs" bubble |
| 2.12 | Conversations list | Tap 💬 Messages in nav | Shows list of all conversations with last message preview |
| 2.13 | Unread badge | Receive a message → check conversations list | Unread count badge shown next to sender's name |
| 2.14 | Own listing hides social buttons | Open your own listing | Follow/Message/Save buttons not shown; Delete/Sold shown |
| 2.15 | Auth required for social | Without logging in, tap Follow/Message/Save | "Please sign in" alert and auth modal opens |
| 2.16 | PostgreSQL persistence | Redeploy app on Render | All data (users, listings, messages) survives |

### Stage 2 — Database Upgrade

| # | Test | Steps | Expected |
|---|------|-------|----------|
| DB.1 | Local dev uses SQLite | Run locally without DATABASE_URL | App works with SQLite file |
| DB.2 | Render uses PostgreSQL | Set DATABASE_URL env var on Render | App connects to PG, tables auto-created |
| DB.3 | Seed data on fresh DB | First deploy with empty PG | Seed data (14 listings, 4 artists) auto-inserted |
