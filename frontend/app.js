/* ── ArtLocal — App Logic (Stage 2) ──────────────────────────────── */

const API = "";  // Same origin
let token = localStorage.getItem("artlocal_token");
let currentUser = JSON.parse(localStorage.getItem("artlocal_user") || "null");
let userLat = null;
let userLng = null;
let listings = [];
let currentDetailItem = null;  // full detail object for follow/msg/fave
let currentChatUser = null;    // username of active chat partner

// ── Init ────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("build-id").textContent = "build " + new Date().toISOString().slice(0,16).replace("T"," ");
    updateAuthUI();
    setupEventListeners();
    loadListings();
    requestLocation();
});

function setupEventListeners() {
    document.querySelectorAll(".nav-btn").forEach(btn => {
        btn.addEventListener("click", () => handleNav(btn.dataset.view));
    });
    document.getElementById("auth-btn").addEventListener("click", () => {
        if (token) { logout(); } else { openModal("auth-modal"); }
    });
    document.getElementById("auth-form").addEventListener("submit", handleAuth);
    document.getElementById("auth-toggle-link").addEventListener("click", toggleAuthMode);
    document.getElementById("post-form").addEventListener("submit", handlePost);
    document.getElementById("post-image").addEventListener("change", handleImagePreview);
    document.getElementById("location-btn").addEventListener("click", requestLocation);
    document.getElementById("search-input").addEventListener("input", debounce(handleSearch, 300));
}

// ── Geolocation ─────────────────────────────────────────────────────

function requestLocation() {
    const status = document.getElementById("location-status");
    if (!navigator.geolocation) { status.textContent = "📍 Showing all art"; return; }
    status.textContent = "📍 Getting your location...";
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            userLat = pos.coords.latitude;
            userLng = pos.coords.longitude;
            status.textContent = "📍 Showing art near you";
            loadListings();
        },
        () => { status.textContent = "📍 Showing all art"; },
        { enableHighAccuracy: false, timeout: 5000 }
    );
}

// ── Load & Render Feed ──────────────────────────────────────────────

async function loadListings(filterParams) {
    try {
        const params = new URLSearchParams({
            lat: userLat || 0,
            lng: userLng || 0,
            radius: 50,
            limit: 50,
        });
        if (filterParams) {
            for (const [k, v] of Object.entries(filterParams)) {
                if (v) params.set(k, v);
            }
        }
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

async function showDetail(id) {
    try {
        const res = await fetch(`${API}/api/listings/${id}`);
        const item = await res.json();
        currentDetailItem = item;

        document.getElementById("detail-image").src = item.image_url;
        document.getElementById("detail-title").textContent = item.title;
        document.getElementById("detail-price").textContent = `₹${Number(item.price).toLocaleString('en-IN')}`;
        document.getElementById("detail-meta").textContent =
            [item.medium, item.dimensions].filter(Boolean).join(" · ");
        document.getElementById("detail-desc").textContent = item.description || "";
        document.getElementById("detail-artist").textContent =
            `by ${item.display_name || item.username}`;
        document.getElementById("detail-distance").textContent =
            item.distance_miles != null ? `📍 ${item.distance_miles} miles away` : "";

        // Owner actions
        const actions = document.getElementById("detail-actions");
        const isOwner = currentUser && currentUser.username === item.username;
        actions.classList.toggle("hidden", !isOwner);

        // Show/hide social buttons for non-owners
        const faveBtn = document.getElementById("detail-fave-btn");
        const msgBtn = document.getElementById("detail-msg-btn");
        const followBtn = document.getElementById("detail-follow-btn");
        if (isOwner) {
            faveBtn.style.display = "none";
            msgBtn.style.display = "none";
            followBtn.style.display = "none";
        } else {
            faveBtn.style.display = "";
            msgBtn.style.display = "";
            followBtn.style.display = "";
            faveBtn.textContent = "❤️ Save";
            followBtn.textContent = "➕ Follow";
        }

        openModal("detail-modal");
    } catch (err) {
        console.error("Failed to load detail:", err);
    }
}

async function deleteListing() {
    if (!currentDetailItem || !confirm("Delete this listing?")) return;
    try {
        const res = await fetch(`${API}/api/listings/${currentDetailItem.id}`, {
            method: "DELETE",
            headers: { "Authorization": `Bearer ${token}` },
        });
        if (res.ok) { closeModal("detail-modal"); loadListings(); }
        else { const d = await res.json(); alert(d.detail || "Failed to delete"); }
    } catch (err) { alert("Network error"); }
}

async function markSold() {
    if (!currentDetailItem) return;
    try {
        const res = await fetch(`${API}/api/listings/${currentDetailItem.id}/sold`, {
            method: "PUT",
            headers: { "Authorization": `Bearer ${token}` },
        });
        if (res.ok) { closeModal("detail-modal"); loadListings(); }
        else { const d = await res.json(); alert(d.detail || "Failed to mark as sold"); }
    } catch (err) { alert("Network error"); }
}

// ── Favorites ───────────────────────────────────────────────────────

async function toggleFavorite() {
    if (!token) { alert("Please sign in first"); openModal("auth-modal"); return; }
    if (!currentDetailItem) return;
    const btn = document.getElementById("detail-fave-btn");
    const isSaved = btn.textContent.includes("Saved");
    try {
        const res = await fetch(`${API}/api/favorites/${currentDetailItem.id}`, {
            method: isSaved ? "DELETE" : "POST",
            headers: { "Authorization": `Bearer ${token}` },
        });
        if (res.ok) {
            btn.textContent = isSaved ? "❤️ Save" : "💖 Saved";
        }
    } catch (err) { console.error(err); }
}

// ── Follow ──────────────────────────────────────────────────────────

async function toggleFollowFromDetail() {
    if (!token) { alert("Please sign in first"); openModal("auth-modal"); return; }
    if (!currentDetailItem) return;
    const btn = document.getElementById("detail-follow-btn");
    const isFollowing = btn.textContent.includes("Following");
    const artistUsername = currentDetailItem.username;
    try {
        const res = await fetch(`${API}/api/follow/${artistUsername}`, {
            method: isFollowing ? "DELETE" : "POST",
            headers: { "Authorization": `Bearer ${token}` },
        });
        if (res.ok) {
            btn.textContent = isFollowing ? "➕ Follow" : "✓ Following";
        }
    } catch (err) { console.error(err); }
}

// ── Messaging ───────────────────────────────────────────────────────

function openMessageFromDetail() {
    if (!token) { alert("Please sign in first"); openModal("auth-modal"); return; }
    if (!currentDetailItem) return;
    closeModal("detail-modal");
    openChat(currentDetailItem.username, currentDetailItem.display_name || currentDetailItem.username);
}

async function loadConversations() {
    if (!token) return;
    try {
        const res = await fetch(`${API}/api/messages`, {
            headers: { "Authorization": `Bearer ${token}` },
        });
        const convos = await res.json();
        const list = document.getElementById("msg-conversations");
        const chat = document.getElementById("msg-chat");
        chat.classList.add("hidden");
        list.classList.remove("hidden");
        document.getElementById("msg-modal-title").textContent = "💬 Messages";

        if (convos.length === 0) {
            list.innerHTML = '<p style="text-align:center;opacity:0.6;padding:24px;">No conversations yet</p>';
            return;
        }
        list.innerHTML = convos.map(c => `
            <div class="msg-convo-item" onclick="openChat('${escapeHtml(c.username)}', '${escapeHtml(c.display_name || c.username)}')">
                <div class="msg-convo-name">${escapeHtml(c.display_name || c.username)}${c.unread > 0 ? ` <span class="msg-badge">${c.unread}</span>` : ''}</div>
                <div class="msg-convo-preview">${escapeHtml(c.last_message).slice(0, 50)}</div>
            </div>
        `).join("");
    } catch (err) { console.error(err); }
}

async function openChat(username, displayName) {
    currentChatUser = username;
    document.getElementById("msg-conversations").classList.add("hidden");
    document.getElementById("msg-chat").classList.remove("hidden");
    document.getElementById("msg-modal-title").textContent = `💬 ${displayName || username}`;
    openModal("message-modal");
    await refreshChat();
}

async function refreshChat() {
    if (!currentChatUser || !token) return;
    try {
        const res = await fetch(`${API}/api/messages/${currentChatUser}`, {
            headers: { "Authorization": `Bearer ${token}` },
        });
        const msgs = await res.json();
        const area = document.getElementById("msg-chat-messages");
        if (msgs.length === 0) {
            area.innerHTML = '<p style="text-align:center;opacity:0.5;padding:24px;">Start the conversation!</p>';
            return;
        }
        area.innerHTML = msgs.map(m => `
            <div class="msg-bubble ${m.sender_username === currentUser.username ? 'msg-mine' : 'msg-theirs'}">
                <span>${escapeHtml(m.body)}</span>
                <small>${new Date(m.created_at).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</small>
            </div>
        `).join("");
        area.scrollTop = area.scrollHeight;
    } catch (err) { console.error(err); }
}

async function sendMessage(e) {
    e.preventDefault();
    const input = document.getElementById("msg-input");
    const body = input.value.trim();
    if (!body || !currentChatUser) return;
    try {
        const res = await fetch(`${API}/api/messages`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`,
            },
            body: JSON.stringify({
                receiver_username: currentChatUser,
                body: body,
                listing_id: currentDetailItem ? currentDetailItem.id : null,
            }),
        });
        if (res.ok) {
            input.value = "";
            await refreshChat();
        }
    } catch (err) { console.error(err); }
}

// ── Filters ─────────────────────────────────────────────────────────

function applyFilters() {
    const medium = document.getElementById("filter-medium").value;
    const minPrice = document.getElementById("filter-min-price").value;
    const maxPrice = document.getElementById("filter-max-price").value;
    loadListings({ medium, min_price: minPrice, max_price: maxPrice });
}

function clearFilters() {
    document.getElementById("filter-medium").value = "";
    document.getElementById("filter-min-price").value = "";
    document.getElementById("filter-max-price").value = "";
    loadListings();
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
        if (!res.ok) { alert(data.detail || "Error"); return; }
        token = data.token;
        currentUser = { id: data.user_id, username: data.username };
        localStorage.setItem("artlocal_token", token);
        localStorage.setItem("artlocal_user", JSON.stringify(currentUser));
        updateAuthUI();
        closeModal("auth-modal");
    } catch (err) { alert("Network error"); }
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
    btn.textContent = (token && currentUser) ? "Sign Out" : "Sign In";
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
    if (!token) { alert("Please sign in first"); openModal("auth-modal"); return; }
    const postLat = userLat || 19.076;
    const postLng = userLng || 72.8777;

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
        if (!res.ok) { alert(data.detail || "Upload failed"); return; }
        closeModal("post-modal");
        document.getElementById("post-form").reset();
        document.getElementById("upload-preview").classList.add("hidden");
        document.querySelector("#upload-area p").classList.remove("hidden");
        loadListings();
    } catch (err) { alert("Network error"); }
    finally { submitBtn.disabled = false; submitBtn.textContent = "🎨 Post It"; }
}

// ── Navigation ──────────────────────────────────────────────────────

function handleNav(view) {
    document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
    document.querySelector(`[data-view="${view}"]`).classList.add("active");

    const filterBar = document.getElementById("filter-bar");

    if (view === "post") {
        if (!token) { alert("Please sign in to post artwork"); openModal("auth-modal"); return; }
        openModal("post-modal");
    } else if (view === "feed") {
        filterBar.classList.remove("hidden");
        clearFilters();
    } else if (view === "profile") {
        filterBar.classList.add("hidden");
        if (!token || !currentUser) { alert("Please sign in first"); openModal("auth-modal"); return; }
        showProfile(currentUser.username);
    } else if (view === "search") {
        filterBar.classList.remove("hidden");
        document.getElementById("search-input").focus();
    } else if (view === "messages") {
        filterBar.classList.add("hidden");
        if (!token) { alert("Please sign in first"); openModal("auth-modal"); return; }
        loadConversations();
        openModal("message-modal");
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

        status.textContent = `👤 ${profile.display_name || profile.username} — ${profile.bio || "Artist"}`;
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
    } catch (err) { console.error("Failed to load profile:", err); }
}

// ── Search ──────────────────────────────────────────────────────────

async function handleSearch(e) {
    const q = e.target.value.trim();
    if (!q) { renderFeed(listings); return; }
    loadListings({ q });
}

// ── Modal Helpers ───────────────────────────────────────────────────

function openModal(id) { document.getElementById(id).classList.remove("hidden"); }
function closeModal(id) { document.getElementById(id).classList.add("hidden"); }

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
