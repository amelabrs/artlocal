/* ── ArtLocal — App Logic ─────────────────────────────────────────── */

const API = "";  // Same origin
let token = localStorage.getItem("artlocal_token");
let currentUser = JSON.parse(localStorage.getItem("artlocal_user") || "null");
let userLat = null;
let userLng = null;
let listings = [];

// ── Init ────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("build-id").textContent = "build " + new Date().toISOString().slice(0,16).replace("T"," ");
    updateAuthUI();
    setupEventListeners();
    loadListings();  // Load feed immediately, don't wait for location
    requestLocation();  // Try to get location in background
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
        status.textContent = "📍 Showing all art";
        return;
    }
    status.textContent = "📍 Getting your location...";
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            userLat = pos.coords.latitude;
            userLng = pos.coords.longitude;
            status.textContent = `📍 Showing art near you`;
            loadListings();  // Reload with distance sorting
        },
        (err) => {
            status.textContent = "📍 Showing all art";
        },
        { enableHighAccuracy: false, timeout: 5000 }
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
            ${item.distance_miles != null ? `<span class="card-badge">${item.distance_miles} mi</span>` : ''}
            <div class="card-info">
                <div class="card-title">${escapeHtml(item.title)}</div>
                <div class="card-price">₹${Number(item.price).toLocaleString('en-IN')}</div>
                <div class="card-artist">by ${escapeHtml(item.display_name || item.username)}</div>
            </div>
        </div>
    `).join("");
}

// ── Detail View ─────────────────────────────────────────────────────

let currentDetailId = null;

async function showDetail(id) {
    try {
        const res = await fetch(`${API}/api/listings/${id}`);
        const item = await res.json();
        currentDetailId = id;

        document.getElementById("detail-image").src = item.image_url;
        document.getElementById("detail-title").textContent = item.title;
        document.getElementById("detail-price").textContent = `\u20b9${Number(item.price).toLocaleString('en-IN')}`;
        document.getElementById("detail-meta").textContent =
            [item.medium, item.dimensions].filter(Boolean).join(" · ");
        document.getElementById("detail-desc").textContent = item.description || "";
        document.getElementById("detail-artist").textContent =
            `by ${item.display_name || item.username}`;
        document.getElementById("detail-distance").textContent =
            item.distance_miles != null ? `📍 ${item.distance_miles} miles away` : "";

        // Show delete/sold buttons if this is the current user's listing
        const actions = document.getElementById("detail-actions");
        if (currentUser && currentUser.username === item.username) {
            actions.classList.remove("hidden");
        } else {
            actions.classList.add("hidden");
        }

        openModal("detail-modal");
    } catch (err) {
        console.error("Failed to load detail:", err);
    }
}

async function deleteListing() {
    if (!currentDetailId || !confirm("Delete this listing?")) return;
    try {
        const res = await fetch(`${API}/api/listings/${currentDetailId}`, {
            method: "DELETE",
            headers: { "Authorization": `Bearer ${token}` },
        });
        if (res.ok) {
            closeModal("detail-modal");
            loadListings();
        } else {
            const data = await res.json();
            alert(data.detail || "Failed to delete");
        }
    } catch (err) {
        alert("Network error");
    }
}

async function markSold() {
    if (!currentDetailId) return;
    try {
        const res = await fetch(`${API}/api/listings/${currentDetailId}/sold`, {
            method: "PUT",
            headers: { "Authorization": `Bearer ${token}` },
        });
        if (res.ok) {
            closeModal("detail-modal");
            loadListings();
        } else {
            const data = await res.json();
            alert(data.detail || "Failed to mark as sold");
        }
    } catch (err) {
        alert("Network error");
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
    // Use current location or default
    const postLat = userLat || 37.7749;
    const postLng = userLng || -122.4194;

    const form = new FormData();
    form.append("title", document.getElementById("post-title").value);
    form.append("price", document.getElementById("post-price").value);
    form.append("medium", document.getElementById("post-medium").value);
    form.append("dimensions", document.getElementById("post-dimensions").value);
    form.append("description", document.getElementById("post-description").value);
    form.append("lat", postLat);
    form.append("lng", postLng);
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
    } else if (view === "profile") {
        if (!token || !currentUser) {
            alert("Please sign in first");
            openModal("auth-modal");
            return;
        }
        showProfile(currentUser.username);
    } else if (view === "search") {
        document.getElementById("search-input").focus();
    }
}

// ── Profile View ────────────────────────────────────────────────────

async function showProfile(username) {
    try {
        const res = await fetch(`${API}/api/profile/${username}`);
        const profile = await res.json();

        const grid = document.getElementById("masonry-grid");
        const empty = document.getElementById("empty-state");
        const count = document.getElementById("listing-count");
        const status = document.getElementById("location-status");

        status.textContent = `👤 ${profile.display_name} — ${profile.bio || ""}`;
        empty.classList.add("hidden");

        const items = profile.listings || [];
        count.textContent = `${items.length} listing${items.length !== 1 ? "s" : ""}`;

        if (items.length === 0) {
            grid.innerHTML = "";
            empty.classList.remove("hidden");
            return;
        }

        grid.innerHTML = items.map(item => `
            <div class="card" onclick="showDetail(${item.id})">
                <img src="${escapeHtml(item.image_url)}" alt="${escapeHtml(item.title)}" loading="lazy">
                ${item.is_sold ? '<span class="card-badge">SOLD</span>' : ''}
                <div class="card-info">
                    <div class="card-title">${escapeHtml(item.title)}</div>
                    <div class="card-price">₹${Number(item.price).toLocaleString('en-IN')}</div>
                </div>
            </div>
        `).join("");
    } catch (err) {
        console.error("Failed to load profile:", err);
    }
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

// Close modals by clicking the dark backdrop
document.addEventListener("click", (e) => {
    if (e.target.classList.contains("modal")) {
        e.target.classList.add("hidden");
    }
});

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
