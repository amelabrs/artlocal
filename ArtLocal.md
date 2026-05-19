# ArtLocal

**Tagline:** See it. Buy it. Keep it Local.

**Core Objective:** A geo-fenced marketplace allowing artists to instantly list and sell work to nearby buyers, with artists assuming fulfillment responsibility.

---

## 1. Product Overview

| Field | Detail |
|---|---|
| App Name | ArtLocal |
| Tagline | See it. Buy it. Keep it Local. |
| Core Objective | Geo-fenced marketplace for artists to list and sell work to nearby buyers; artists handle fulfillment. |

---

## 2. Complete Feature Specifications

### A. User Roles & Profiles

**Artist Profile**
- Portfolio gallery
- "Follow" count
- Artist bio
- Verified badge
- "Typically responds in X hours"

**Buyer Profile**
- Saved/Favorite art
- Purchase history
- Location settings

### B. Core Marketplace Features

- **Instant Listing Engine:** Upload photos/videos, set price, medium, and dimensions.
- **Geo-Location Engine:** Listings sorted by proximity (using GPS/Zip Code).
- **The "Sold" Manager:** Artists manually toggle "Sold" (if sold off-platform) or auto-toggle (if sold via app).
- **Smart Search:** Filter by price, distance (1–50 miles), color, and category (e.g., Oil, Digital, Sculptures).

### C. Advanced & Future Features ("The Full Product")

- **In-App Messaging:** Secure chat for coordinating pickups/deliveries.
- **AR Wall Preview:** Using the camera to see art at scale on a wall.
- **Commission Requests:** A dedicated button for users to hire an artist for custom work.
- **Artist Analytics:** Weekly report on listing views and profile clicks.

### D. Transaction & Risk Management

- **Payment Gateway:** Stripe Connect integration (split payments: X% to Artist, Y% to Platform).
- **Escrow Logic:** Funds held until "Confirmation of Receipt."
- **QR Code Verification:** For local pickups, the Buyer scans the Artist's QR code to finalize the sale and release funds.

---

## 3. Detailed Workflow

### Step 1: Listing

Artist snaps a photo → Enters price → Selects "Local Pickup Only" or "Shipping Available" → **Post.**

### Step 2: Discovery

Buyer opens app → App detects location → Buyer sees a feed of art within a 10-mile radius → Clicks "Buy Now."

### Step 3: Payment & Escrow

Buyer pays via App Gateway → Money is held by the platform → Artist receives notification: *"Item sold! Coordinate pickup."*

### Step 4: Fulfillment & Payout

Artist & Buyer chat to meet → At meeting, Artist presents QR Code → Buyer scans code → **Transaction Complete** → Funds are released to Artist's bank account.

---

## 4. Wireframe Layouts

### Screen 1: Discovery Feed (Home)

- **Top Bar:** Search bar + Filter icon + Location settings
- **Body:** Two-column masonry grid (uneven image heights, Pinterest-style)
- **Overlay:** Small distance badge on each image (e.g., "1.2 miles away")
- **Bottom Nav:** Home | Search | **[+] Post** | Messages | Profile

### Screen 2: Artwork Detail View

- **Top:** Image carousel (swipe for more angles/video)
- **Mid:** Title, price, and distance map (blurred for privacy until purchase)
- **Bottom:** "Buy Now" (primary button) and "Message Artist" (secondary)

### Screen 3: Artist Dashboard

- **Stats:** Total Sales | Profile Views
- **Listings:**
  - *Active Tab:* List of current art with "Edit" or "Mark as Sold" buttons
  - *Sold Tab:* History of past sales with receipt details

### Screen 4: QR Verification (Post-Purchase)

- **Artist View:** A large, unique QR code generated for that specific transaction
- **Buyer View:** A camera scanner with a "Scan to Confirm Pickup" label

---

## 5. Technical Requirements

| Layer | Choice |
|---|---|
| Framework | Flutter or React Native (cross-platform) |
| Backend | Firebase (real-time chat & notifications) or AWS |
| Database | NoSQL (Firestore) for flexible artwork attributes |
| Payment API | Stripe Connect (Express or Custom) for multi-party payouts |
| Maps API | Google Maps or Mapbox for geo-sorting |
