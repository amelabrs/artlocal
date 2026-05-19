/* ── ArtLocal — App Logic ─────────────────────────────────────────── */

const API = "";  // Same origin
let token = localStorage.getItem("artlocal_token");
let currentUser = JSON.parse(localStorage.getItem("artlocal_user") || "null");
let userLat = null;
let userLng = null;
let listings = [];

// ── Init ────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
    updateAuthUI();
    requestLocation();
    setupEventListeners();
});

function setupEventListeners() {
    // Nav buttons
    document.querySelectorAll(".nav-btn").forEach(btn => {
        btn.addEventListener("click", () => handleNav(btn.dataset.view));
    });

    // Auth
    document.getElementById("auth-btn").addEventListener("click", () => {
        if (token) { logout(); } else { openModal("auth-modal"); }
    });
    document.getElementById("auth-form").addEventListener("submit", handleAuth);
    document.getElementById("auth-toggle-link").addEventListener("click", toggleAuthMode);

    // Post form
    document.getElementById("post-form").addEventListener("submit", handlePost);
    document.getElementById("post-image").addEventListener("change", handleImagePreview);

    // Location button
    document.getElementById("location-btn").addEventListener("click", requestLocation);

    // Search
    document.getElementById("search-input").addEventListener("input", debounce(handleSearch, 300));
}

// ── Geolocation ─────────────────────────────────────────────────────

function requestLocation() {
    const status = document.getElementById("location-status");
    if (!navigator.geolocation) {
        status.textContent = "📍 Geolocation not supported";
        loadListings();
        return;
    }
    status.textContent = "📍 Getting your location...";
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            userLat = pos.coords.latitude;
            userLng = pos.coords.longitude;
            status.textContent = `📍 Showing art near you`;
            loadListings();
        },
        (err) => {
            status.textContent = "📍 Location unavailable — showing all";
            userLat = 0;
            userLng = 0;
            loadListings();
        },
        { enableHighAccuracy: true, timeout: 10000 }
    );
}

// ── Load & Render Feed ──────────────────────────────────────────────

async function loadListings() {
    try {
        const params = new URLSearchParams({
            lat: userLat || 0,
            lng: userLng || 0,
            radius: 50,
            limit: 50,
        });
        const res = await fetch(`${API}/api/listings?${params}`);
        listings = await res.json();
        renderFeed(listings);
    } catch (err) {
        console.error("Failed to load listings:", err);
    }
}

function renderFeed(items) {
    const grid = document.getElementById("masonry-grid");
    const empty = document.getElementById("empty-state");
    const count = document.getElementById("listing-count");

    if (items.length === 0) {
        grid.innerHTML = "";
        empty.classList.remove("hidden");
        count.textContent = "";
        return;
    }

    empty.classList.add("hidden");
    count.textContent = `${items.length} artwork${items.length > 1 ? "s" : ""}`;

    grid.innerHTML = items.map(item => `
        <div class="card" onclick="showDetail(${item.id})">
            <img src="${escapeHtml(item.image_url)}" alt="${escapeHtml(item.title)}" loading="lazy">
            <span class="card-badge">${item.distance_miles} mi</span>
            <div class="card-info">
                <div class="card-title">${escapeHtml(item.title)}</div>
                <div class="card-price">$${Number(item.price).toFixed(0)}</div>
                <div class="card-artist">by ${escapeHtml(item.display_name || item.username)}</div>
            </div>
        </div>
    `).join("");
}

// ── Detail View ─────────────────────────────────────────────────────

async function showDetail(id) {
    try {
        const res = await fetch(`${API}/api/listings/${id}`);
        const item = await res.json();

        document.getElementById("detail-image").src = item.image_url;
        document.getElementById("detail-title").textContent = item.title;
        document.getElementById("detail-price").textContent = `$${Number(item.price).toFixed(2)}`;
        document.getElementById("detail-meta").textContent =
            [item.medium, item.dimensions].filter(Boolean).join(" · ");
        document.getElementById("detail-desc").textContent = item.description || "";
        document.getElementById("detail-artist").textContent =
            `by ${item.display_name || item.username}`;
        document.getElementById("detail-distance").textContent =
            item.distance_miles != null ? `📍 ${item.distance_miles} miles away` : "";

        openModal("detail-modal");
    } catch (err) {
        console.error("Failed to load detail:", err);
    }
}

// ── Auth ────────────────────────────────────────────────────────────

let isSignup = false;

function toggleAuthMode(e) {
    e.preventDefault();
    isSignup = !isSignup;
    document.getElementById("auth-title").textContent = isSignup ? "Sign Up" : "Sign In";
    document.getElementById("auth-submit").textContent = isSignup ? "Sign Up" : "Sign In";
    document.getElementById("signup-fields").classList.toggle("hidden", !isSignup);
    document.getElementById("auth-toggle-text").textContent =
        isSignup ? "Already have an account?" : "Don't have an account?";
    document.getElementById("auth-toggle-link").textContent =
        isSignup ? "Sign In" : "Sign Up";
}

async function handleAuth(e) {
    e.preventDefault();
    const email = document.getElementById("auth-email").value;
    const password = document.getElementById("auth-password").value;

    const endpoint = isSignup ? "/api/signup" : "/api/login";
    const body = { email, password };

    if (isSignup) {
        body.username = document.getElementById("auth-username").value;
        body.display_name = document.getElementById("auth-displayname").value;
        body.is_artist = document.getElementById("auth-is-artist").checked;
    }

    try {
        const res = await fetch(`${API}${endpoint}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        const data = await res.json();
        if (!res.ok) {
            alert(data.detail || "Error");
            return;
        }
        token = data.token;
        currentUser = { id: data.user_id, username: data.username };
        localStorage.setItem("artlocal_token", token);
        localStorage.setItem("artlocal_user", JSON.stringify(currentUser));
        updateAuthUI();
        closeModal("auth-modal");
    } catch (err) {
        alert("Network error");
    }
}

function logout() {
    token = null;
    currentUser = null;
    localStorage.removeItem("artlocal_token");
    localStorage.removeItem("artlocal_user");
    updateAuthUI();
}

function updateAuthUI() {
    const btn = document.getElementById("auth-btn");
    if (token && currentUser) {
        btn.textContent = `Sign Out`;
    } else {
        btn.textContent = "Sign In";
    }
}

// ── Post Listing ────────────────────────────────────────────────────

function handleImagePreview(e) {
    const file = e.target.files[0];
    if (!file) return;
    const preview = document.getElementById("upload-preview");
    preview.src = URL.createObjectURL(file);
    preview.classList.remove("hidden");
    document.querySelector("#upload-area p").classList.add("hidden");
}

async function handlePost(e) {
    e.preventDefault();
    if (!token) {
        alert("Please sign in first");
        openModal("auth-modal");
        return;
    }
    if (!userLat || !userLng) {
        alert("Location required to post. Please enable location access.");
        return;
    }

    const form = new FormData();
    form.append("title", document.getElementById("post-title").value);
    form.append("price", document.getElementById("post-price").value);
    form.append("medium", document.getElementById("post-medium").value);
    form.append("dimensions", document.getElementById("post-dimensions").value);
    form.append("description", document.getElementById("post-description").value);
    form.append("lat", userLat);
    form.append("lng", userLng);
    form.append("image", document.getElementById("post-image").files[0]);

    const submitBtn = document.getElementById("post-submit");
    submitBtn.disabled = true;
    submitBtn.textContent = "Uploading...";

    try {
        const res = await fetch(`${API}/api/listings`, {
            method: "POST",
            headers: { "Authorization": `Bearer ${token}` },
            body: form,
        });
        const data = await res.json();
        if (!res.ok) {
            alert(data.detail || "Upload failed");
            return;
        }
        closeModal("post-modal");
        document.getElementById("post-form").reset();
        document.getElementById("upload-preview").classList.add("hidden");
        document.querySelector("#upload-area p").classList.remove("hidden");
        loadListings();  // Refresh feed
    } catch (err) {
        alert("Network error");
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "🎨 Post It";
    }
}

// ── Navigation ──────────────────────────────────────────────────────

function handleNav(view) {
    document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
    document.querySelector(`[data-view="${view}"]`).classList.add("active");

    if (view === "post") {
        if (!token) {
            alert("Please sign in to post artwork");
            openModal("auth-modal");
            return;
        }
        openModal("post-modal");
    } else if (view === "feed") {
        loadListings();
    }
    // search & profile to be expanded later
}

// ── Search ──────────────────────────────────────────────────────────

function handleSearch(e) {
    const query = e.target.value.toLowerCase().trim();
    if (!query) {
        renderFeed(listings);
        return;
    }
    const filtered = listings.filter(item =>
        item.title.toLowerCase().includes(query) ||
        (item.medium && item.medium.toLowerCase().includes(query)) ||
        (item.display_name && item.display_name.toLowerCase().includes(query))
    );
    renderFeed(filtered);
}

// ── Modal Helpers ───────────────────────────────────────────────────

function openModal(id) {
    document.getElementById(id).classList.remove("hidden");
}

function closeModal(id) {
    document.getElementById(id).classList.add("hidden");
}

// ── Utilities ───────────────────────────────────────────────────────

function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function debounce(fn, ms) {
    let timer;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), ms);
    };
}
