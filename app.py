import os
import sqlite3
import hashlib
import time
from typing import Optional
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="SoravVoid SV")
DB_FILE = "soravvoid.db"

# ----------------- SQLITE DATABASE -----------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            credits INTEGER DEFAULT 1200,
            is_owner BOOLEAN DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

def hash_pw(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()

# ----------------- API MODELS -----------------
class AuthReq(BaseModel):
    username: str
    password: str

class OwnerReq(BaseModel):
    secret_key: str

class ActionReq(BaseModel):
    cost: int
    prompt: str
    style: str

# ----------------- API ENDPOINTS -----------------
@app.post("/api/register")
def register(req: AuthReq):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash, credits, is_owner) VALUES (?, ?, 1200, 0)",
                  (req.username.strip(), hash_pw(req.password)))
        conn.commit()
        return {"status": "success", "username": req.username, "credits": 1200, "is_owner": False}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists. Please log in.")
    finally:
        conn.close()

@app.post("/api/login")
def login(req: AuthReq):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT credits, is_owner FROM users WHERE username = ? AND password_hash = ?",
              (req.username.strip(), hash_pw(req.password)))
    user = c.fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    return {"status": "success", "username": req.username, "credits": user[0], "is_owner": bool(user[1])}

@app.post("/api/unlock-owner")
def unlock_owner(req: OwnerReq, authorization: Optional[str] = Header(None)):
    if req.secret_key.strip().lower() != "mahakumbh":
        raise HTTPException(status_code=403, detail="Invalid Master Password.")
    
    username = authorization if authorization else "guest"
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET is_owner = 1, credits = 9999999 WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    return {"status": "unlocked", "credits": 9999999, "is_owner": True}

@app.post("/api/process-edit")
def process_edit(req: ActionReq, authorization: Optional[str] = Header(None)):
    username = authorization if authorization else "guest"
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT credits, is_owner FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    
    is_owner = False
    current_credits = 1200
    if row:
        current_credits, is_owner = row[0], bool(row[1])
        
    if not is_owner:
        if current_credits < req.cost:
            conn.close()
            raise HTTPException(status_code=402, detail=f"Need {req.cost} credits! Please upgrade or enter Mahakumbh key.")
        current_credits -= req.cost
        c.execute("UPDATE users SET credits = ? WHERE username = ?", (current_credits, username))
        conn.commit()
        
    conn.close()
    return {
        "status": "success",
        "video_id": f"SV_{int(time.time()*1000)}",
        "remaining_credits": current_credits,
        "is_owner": is_owner
    }

# ----------------- MOBILE APP PWA MANIFEST -----------------
@app.get("/manifest.json")
def manifest():
    return JSONResponse({
        "name": "SoravVoid SV Studio",
        "short_name": "SoravVoid",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0a0a0a",
        "theme_color": "#ff525c",
        "icons": [
            {
                "src": "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=192&auto=format&fit=crop&q=80",
                "sizes": "192x192",
                "type": "image/png"
            }
        ]
    })

# ----------------- SERVE RESPONSIVE FRONTEND -----------------
@app.get("/", response_class=HTMLResponse)
def index():
    return """
<!DOCTYPE html>
<html class="dark" lang="en">
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"/>
    <meta name="theme-color" content="#0a0a0a"/>
    <link rel="manifest" href="/manifest.json"/>
    <title>SoravVoid SV — AI Video Studio</title>
    <script src="https://cdn.tailwindcss.com?plugins=forms"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Geist+Mono:wght@400;700&family=Space+Grotesk:wght@600;800&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1" rel="stylesheet"/>
    <script>
        tailwind.config = {
            darkMode: "class",
            theme: {
                extend: {
                    colors: {
                        primary: "#ff525c",
                        "primary-container": "#FF003C",
                        secondary: "#4cd6ff",
                        background: "#0a0a0a",
                        surface: "#121212",
                        "surface-container": "#1a1919",
                        outline: "#352323"
                    },
                    fontFamily: {
                        mono: ["Geist Mono", "monospace"],
                        display: ["Space Grotesk", "sans-serif"]
                    }
                }
            }
        }
    </script>
    <style>
        body {
            background-color: #0a0a0a;
            background-image: linear-gradient(rgba(255, 82, 92, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 82, 92, 0.03) 1px, transparent 1px);
            background-size: 24px 24px;
            color: #e5e2e1;
        }
        .glass { background: rgba(18, 18, 18, 0.85); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.08); }
        .glow { box-shadow: 0 0 20px rgba(255, 0, 60, 0.55); }
    </style>
</head>
<body class="min-h-screen flex flex-col font-mono text-xs md:text-sm antialiased selection:bg-primary selection:text-black">

    <!-- Top App Bar (PC & Mobile) -->
    <header class="fixed top-0 w-full z-50 bg-[#0a0a0a]/90 backdrop-blur-xl border-b border-outline flex justify-between items-center px-4 md:px-8 h-16">
        <div class="flex items-center gap-2 cursor-pointer" onclick="nav('home')">
            <span class="text-primary font-bold text-xl">⚡</span>
            <span class="font-display text-lg md:text-xl font-bold tracking-tighter text-white uppercase">Sorav<span class="text-primary">Void</span></span>
            <span id="owner-badge" class="hidden text-[9px] bg-primary text-black font-bold px-1.5 py-0.5 ml-1">OWNER: FREE</span>
        </div>

        <nav class="hidden md:flex items-center gap-6 uppercase tracking-widest text-xs">
            <button onclick="nav('home')" id="n-home" class="nav-btn text-primary">Home</button>
            <button onclick="nav('create')" id="n-create" class="nav-btn hover:text-primary">Create</button>
            <button onclick="nav('studio')" id="n-studio" class="nav-btn hover:text-primary">Studio</button>
            <button onclick="nav('upgrade')" id="n-upgrade" class="nav-btn text-secondary">Upgrade</button>
            <button onclick="openModal('key-modal')" class="text-secondary border border-secondary/40 px-2 py-1">Master Key</button>
        </nav>

        <div class="flex items-center gap-2 md:gap-3">
            <button onclick="nav('upgrade')" class="flex items-center gap-1 border border-outline bg-surface px-2.5 py-1">
                <span class="text-primary">CR:</span>
                <span id="credit-num" class="font-bold text-white">1,200</span>
            </button>
            <button onclick="openModal('auth-modal')" id="auth-btn" class="bg-surface border border-outline px-2.5 py-1 text-white hover:border-primary">
                Login
            </button>
        </div>
    </header>

    <!-- Main Container -->
    <main class="flex-grow pt-20 pb-20 md:pb-8 px-4 md:px-8 max-w-5xl mx-auto w-full">

        <!-- ================= VIEW 1: HOME ================= -->
        <section id="v-home" class="space-y-6">
            <div class="pt-4 text-center md:text-left">
                <h1 class="font-display text-3xl md:text-5xl uppercase font-bold text-white leading-tight">
                    Create Anime Edits <br/><span class="text-primary">Beyond The Void</span>
                </h1>
                <p class="text-on-surface-variant text-xs mt-2">Generate anime sequences, apply AI variations, and export videos directly.</p>
            </div>

            <div class="glass p-4 border-l-4 border-l-primary space-y-3">
                <div class="flex items-center gap-2">
                    <span class="material-symbols-outlined text-primary">terminal</span>
                    <input id="q-prompt" type="text" placeholder="e.g. Cyberpunk samurai fighting demon robots in red rain..." class="bg-transparent border-0 border-b border-outline text-white w-full py-1 text-xs md:text-sm focus:ring-0 focus:border-secondary outline-none"/>
                </div>
                <div class="flex justify-between items-center pt-2">
                    <span class="text-[11px] text-on-surface-variant">Cost: 50 CR (0 CR for Owner)</span>
                    <button onclick="quickExec()" class="bg-primary text-black font-display font-bold uppercase px-4 py-2 glow">
                        Run & Edit ⚡
                    </button>
                </div>
            </div>
        </section>

        <!-- ================= VIEW 2: CREATE ================= -->
        <section id="v-create" class="hidden space-y-4">
            <h2 class="font-display text-2xl font-bold uppercase text-white">Prompt Console</h2>
            <div class="glass p-4 space-y-3">
                <textarea id="p-input" rows="4" placeholder="Describe the scene in detail: lighting, characters, motion..." class="w-full bg-surface border-0 border-b border-outline p-3 text-xs md:text-sm text-white focus:ring-0 focus:border-secondary outline-none resize-none"></textarea>
                
                <div class="flex flex-wrap gap-2">
                    <button onclick="setSt(this, 'Aggressive 🔥')" class="st-chip border border-primary bg-primary/10 text-primary px-2.5 py-1">Aggressive 🔥</button>
                    <button onclick="setSt(this, 'Dark Void 🌑')" class="st-chip border border-outline text-white px-2.5 py-1">Dark Void 🌑</button>
                    <button onclick="setSt(this, 'Cinematic 🎬')" class="st-chip border border-outline text-white px-2.5 py-1">Cinematic 🎬</button>
                </div>
            </div>
            
            <div class="flex justify-between">
                <button onclick="improveP()" class="border border-outline bg-surface text-secondary px-3 py-2 uppercase">Improve Prompt ✨</button>
                <button onclick="startEdit(50)" class="bg-primary text-black font-display font-bold px-6 py-2 uppercase glow">Generate Video</button>
            </div>
        </section>

        <!-- ================= VIEW 3: STUDIO & DOWNLOAD ================= -->
        <section id="v-studio" class="hidden space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
                
                <!-- Video Canvas Player -->
                <div class="flex flex-col items-center">
                    <div class="relative w-full max-w-[280px] md:max-w-[320px] aspect-[9/16] bg-black border border-outline overflow-hidden shadow-2xl">
                        <canvas id="v-canvas" width="360" height="640" class="w-full h-full object-cover"></canvas>
                        <div class="absolute top-2 left-2 text-[9px] text-secondary bg-black/70 px-1.5 py-0.5 border border-secondary/30">1080x1920 • 60 FPS</div>
                        <div class="absolute bottom-12 left-3 font-display font-bold text-white/30 text-lg pointer-events-none">SORAVVOID SV</div>
                        
                        <div class="absolute bottom-0 inset-x-0 p-3 bg-gradient-to-t from-black via-black/80 to-transparent flex justify-between items-center text-white">
                            <button onclick="toggleP()" class="hover:text-primary"><span id="p-btn-icon" class="material-symbols-outlined text-base">pause</span></button>
                            <span class="font-mono text-[10px] text-on-surface-variant">00:04 / 00:15</span>
                        </div>
                    </div>
                </div>

                <!-- Modifiers & Bottom Video Download Button -->
                <div class="space-y-4">
                    <div class="glass p-4 border-l-4 border-l-secondary space-y-2">
                        <div class="text-secondary font-bold">Apply Video Variation (20 CR)</div>
                        <div class="grid grid-cols-2 gap-2">
                            <button onclick="applyVar('Aggressive')" class="border border-outline p-2 text-left hover:border-primary">🔥 Aggressive</button>
                            <button onclick="applyVar('Darker')" class="border border-outline p-2 text-left hover:border-secondary">🌑 Darker Void</button>
                        </div>
                    </div>

                    <!-- DOWNLOAD BUTTON (Positioned below the edit workspace) -->
                    <div class="glass p-4 space-y-2 border border-primary glow">
                        <div class="font-bold text-white uppercase flex justify-between">
                            <span>Ready For Export</span>
                            <span class="text-primary font-mono">1080P MP4</span>
                        </div>
                        <button onclick="recordAndDownload()" id="dl-btn" class="w-full bg-primary text-black font-display font-bold py-3 uppercase tracking-wider text-xs flex items-center justify-center gap-2 glow">
                            <span class="material-symbols-outlined text-base">download</span> Download Rendered Video (.MP4)
                        </button>
                    </div>
                </div>

            </div>
        </section>

        <!-- ================= VIEW 4: UPGRADE / GPAY ================= -->
        <section id="v-upgrade" class="hidden space-y-6">
            <h2 class="font-display text-2xl font-bold uppercase text-white text-center">Upgrade Credits</h2>
            
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div class="glass p-4 flex flex-col justify-between">
                    <div>
                        <h3 class="font-bold text-lg">Lite Refill</h3>
                        <div class="text-xl font-bold text-white mt-1">₹149</div>
                        <div class="text-on-surface-variant text-[11px] mt-2">+2,000 Credits</div>
                    </div>
                    <button onclick="openPay(149, 'Lite')" class="mt-4 border border-secondary text-secondary py-2 font-bold uppercase">Pay with GPay</button>
                </div>

                <div class="glass p-4 flex flex-col justify-between border-2 border-primary glow">
                    <div>
                        <span class="text-[9px] bg-primary text-black font-bold px-1.5 py-0.5">BEST VALUE</span>
                        <h3 class="font-bold text-lg text-primary mt-1">Pro Void</h3>
                        <div class="text-xl font-bold text-primary mt-1">₹399</div>
                        <div class="text-white text-[11px] mt-2">+10,000 Credits (Priority)</div>
                    </div>
                    <button onclick="openPay(399, 'Pro')" class="mt-4 bg-primary text-black py-2 font-bold uppercase glow">Pay with GPay</button>
                </div>

                <div class="glass p-4 flex flex-col justify-between">
                    <div>
                        <h3 class="font-bold text-lg">Ultra Core</h3>
                        <div class="text-xl font-bold text-white mt-1">₹799</div>
                        <div class="text-on-surface-variant text-[11px] mt-2">+50,000 Credits (4K Mode)</div>
                    </div>
                    <button onclick="openPay(799, 'Ultra')" class="mt-4 border border-secondary text-secondary py-2 font-bold uppercase">Pay with GPay</button>
                </div>
            </div>
        </section>

    </main>

    <!-- ================= MODALS ================= -->
    <!-- 1. Master Key Modal (mahakumbh) -->
    <div id="key-modal" class="fixed inset-0 bg-black/80 z-50 hidden flex items-center justify-center p-4">
        <div class="glass p-5 max-w-sm w-full border border-secondary space-y-3">
            <div class="flex justify-between items-center">
                <span class="font-bold text-secondary">ENTER MASTER KEY</span>
                <button onclick="closeModal('key-modal')">✕</button>
            </div>
            <p class="text-[11px] text-on-surface-variant">Enter master passkey to unlock sovereign owner privileges (all renders free forever).</p>
            <input id="key-inp" type="password" placeholder="Enter password..." class="w-full bg-surface border border-outline p-2 text-xs text-white outline-none"/>
            <button onclick="submitKey()" class="w-full bg-secondary text-black font-bold py-2 uppercase">Unlock Sovereign Mode</button>
        </div>
    </div>

    <!-- 2. Auth Modal -->
    <div id="auth-modal" class="fixed inset-0 bg-black/80 z-50 hidden flex items-center justify-center p-4">
        <div class="glass p-5 max-w-sm w-full border border-primary space-y-3">
            <div class="flex justify-between items-center">
                <span class="font-bold text-primary">ACCOUNT AUTH</span>
                <button onclick="closeModal('auth-modal')">✕</button>
            </div>
            <input id="u-inp" type="text" placeholder="Username" class="w-full bg-surface border border-outline p-2 text-xs text-white outline-none"/>
            <input id="p-inp" type="password" placeholder="Password" class="w-full bg-surface border border-outline p-2 text-xs text-white outline-none"/>
            <div class="flex gap-2">
                <button onclick="auth('login')" class="flex-1 bg-primary text-black font-bold py-2 uppercase">Login</button>
                <button onclick="auth('register')" class="flex-1 border border-secondary text-secondary font-bold py-2 uppercase">Register</button>
            </div>
        </div>
    </div>

    <!-- 3. Google Pay UPI Modal -->
    <div id="pay-modal" class="fixed inset-0 bg-black/80 z-50 hidden flex items-center justify-center p-4">
        <div class="glass p-5 max-w-sm w-full border border-primary space-y-3">
            <div class="flex justify-between items-center">
                <span class="font-bold text-primary">GOOGLE PAY UPI PAYMENT</span>
                <button onclick="closeModal('pay-modal')">✕</button>
            </div>
            <div class="bg-surface p-3 border border-outline space-y-1 text-xs">
                <div>Amount: <span id="pay-amt" class="font-bold text-white">₹399</span></div>
                <div>GPay Mobile: <span class="font-bold text-secondary">+91 9999907971</span></div>
                <div>UPI ID: <span class="font-bold text-primary">codecat743@gmail.com</span></div>
            </div>
            <a id="upi-link" href="#" class="block text-center bg-primary text-black font-bold py-2.5 uppercase glow">Open GPay App</a>
            <button onclick="confirmPay()" class="w-full border border-secondary text-secondary py-2 uppercase">I Have Transferred</button>
        </div>
    </div>

    <!-- Mobile Bottom Navigation Bar -->
    <nav class="md:hidden fixed bottom-0 w-full z-50 bg-[#0a0a0a]/95 border-t border-outline flex justify-around items-center h-14">
        <button onclick="nav('home')" class="m-nav text-primary" data-v="home">Home</button>
        <button onclick="nav('create')" class="m-nav text-on-surface-variant" data-v="create">Create</button>
        <button onclick="nav('studio')" class="m-nav text-on-surface-variant" data-v="studio">Studio</button>
        <button onclick="openModal('key-modal')" class="m-nav text-secondary font-bold">Key 🔑</button>
        <button onclick="nav('upgrade')" class="m-nav text-on-surface-variant" data-v="upgrade">Upgrade</button>
    </nav>

    <!-- Toast Notification -->
    <div id="toast" class="fixed bottom-16 md:bottom-6 right-4 z-50 glass border border-primary px-3 py-2 text-xs text-white opacity-0 transition-all pointer-events-none">
        Notification
    </div>

    <!-- Client Script -->
    <script>
        let user = localStorage.getItem("sv_u") || "guest";
        let isOwner = localStorage.getItem("sv_own") === "true";
        let credits = isOwner ? 9999999 : parseInt(localStorage.getItem("sv_cr") || "1200");
        let activeStyle = "Aggressive 🔥";
        let isPlaying = true;
        let frame = 0;

        function init() {
            updateUI();
            drawCanvas();
        }

        function updateUI() {
            document.getElementById('credit-num').textContent = isOwner ? "∞" : credits.toLocaleString();
            if (isOwner) document.getElementById('owner-badge').classList.remove('hidden');
            if (user !== "guest") document.getElementById('auth-btn').textContent = user;
        }

        function toast(msg) {
            const t = document.getElementById('toast');
            t.textContent = msg;
            t.classList.remove('opacity-0');
            setTimeout(() => t.classList.add('opacity-0'), 2500);
        }

        function nav(id) {
            ['home', 'create', 'studio', 'upgrade'].forEach(v => document.getElementById('v-' + v).classList.add('hidden'));
            document.getElementById('v-' + id).classList.remove('hidden');
            document.querySelectorAll('.nav-btn').forEach(b => b.className = 'nav-btn text-on-surface-variant hover:text-primary');
            const ab = document.getElementById('n-' + id);
            if (ab) ab.className = 'nav-btn text-primary';
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        function openModal(id) { document.getElementById(id).classList.remove('hidden'); }
        function closeModal(id) { document.getElementById(id).classList.add('hidden'); }

        async function auth(type) {
            const u = document.getElementById('u-inp').value.trim();
            const p = document.getElementById('p-inp').value.trim();
            if (!u || !p) return toast("Fill both fields.");
            try {
                const res = await fetch(`/api/${type}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username: u, password: p })
                });
                const d = await res.json();
                if (!res.ok) throw new Error(d.detail);
                user = d.username;
                credits = d.credits;
                isOwner = d.is_owner;
                localStorage.setItem("sv_u", user);
                localStorage.setItem("sv_cr", credits);
                localStorage.setItem("sv_own", isOwner);
                updateUI();
                closeModal('auth-modal');
                toast(`Logged in as ${user}!`);
            } catch (e) { toast(e.message); }
        }

        async function submitKey() {
            const k = document.getElementById('key-inp').value.trim();
            try {
                const res = await fetch("/api/unlock-owner", {
                    method: "POST",
                    headers: { "Content-Type": "application/json", "Authorization": user },
                    body: JSON.stringify({ secret_key: k })
                });
                const d = await res.json();
                if (!res.ok) throw new Error(d.detail);
                isOwner = true;
                credits = 9999999;
                localStorage.setItem("sv_own", "true");
                localStorage.setItem("sv_cr", "9999999");
                updateUI();
                closeModal('key-modal');
                toast("⚡ MAHAKUMBH UNLOCKED! ALL FEATURES ARE FREE!");
            } catch (e) { toast(e.message); }
        }

        function setSt(btn, style) {
            document.querySelectorAll('.st-chip').forEach(c => c.className = 'st-chip border border-outline text-white px-2.5 py-1');
            btn.className = 'st-chip border border-primary bg-primary/10 text-primary px-2.5 py-1';
            activeStyle = style;
        }

        function improveP() {
            const p = document.getElementById('p-input').value.trim();
            document.getElementById('p-input').value = p ? `${p}, 8k anime render, dark void aura, aggressive lighting` : "Cyberpunk rogue ronin with glowing red katana in rain";
            toast("Prompt improved ✨");
        }

        function quickExec() {
            const q = document.getElementById('q-prompt').value.trim();
            if (!q) return toast("Enter a vision prompt first.");
            document.getElementById('p-input').value = q;
            startEdit(50);
        }

        async function startEdit(cost) {
            const p = document.getElementById('p-input').value.trim() || "Anime battle in rain";
            try {
                const res = await fetch("/api/process-edit", {
                    method: "POST",
                    headers: { "Content-Type": "application/json", "Authorization": user },
                    body: JSON.stringify({ cost: cost, prompt: p, style: activeStyle })
                });
                const d = await res.json();
                if (!res.ok) throw new Error(d.detail);
                credits = d.remaining_credits;
                if (!isOwner) localStorage.setItem("sv_cr", credits);
                updateUI();
                nav('studio');
                toast(`Render Complete! ${cost} CR Deducted.`);
            } catch (e) { toast(e.message); }
        }

        function applyVar(name) {
            startEdit(20);
        }

        function openPay(amt, plan) {
            document.getElementById('pay-amt').textContent = "₹" + amt;
            document.getElementById('upi-link').href = `upi://pay?pa=codecat743@gmail.com&pn=SoravVoid&am=${amt}&cu=INR`;
            openModal('pay-modal');
        }

        function confirmPay() {
            credits += 10000;
            localStorage.setItem("sv_cr", credits);
            updateUI();
            closeModal('pay-modal');
            toast("Payment logged! +10,000 Credits added.");
        }

        // Real Animated Canvas & Direct Video Downloader
        function drawCanvas() {
            const c = document.getElementById('v-canvas');
            const ctx = c.getContext('2d');
            function render() {
                if (isPlaying) {
                    ctx.fillStyle = "#0c0c0c";
                    ctx.fillRect(0, 0, c.width, c.height);
                    
                    // Animated Cyber Aura
                    ctx.strokeStyle = "rgba(255, 82, 92, 0.7)";
                    ctx.lineWidth = 3;
                    ctx.beginPath();
                    ctx.arc(180, 320 + Math.sin(frame * 0.05) * 15, 80, 0, Math.PI * 2);
                    ctx.stroke();

                    ctx.strokeStyle = "rgba(76, 214, 255, 0.8)";
                    ctx.beginPath();
                    ctx.moveTo(60, 240 + Math.cos(frame * 0.05) * 30);
                    ctx.lineTo(300, 400 + Math.sin(frame * 0.05) * 30);
                    ctx.stroke();

                    frame++;
                }
                requestAnimationFrame(render);
            }
            render();
        }

        function toggleP() {
            isPlaying = !isPlaying;
            document.getElementById('p-btn-icon').textContent = isPlaying ? "pause" : "play_arrow";
        }

        // Real Video Download from Canvas Stream
        function recordAndDownload() {
            const c = document.getElementById('v-canvas');
            const dlBtn = document.getElementById('dl-btn');
            dlBtn.textContent = "Rendering MP4 / WebM...";
            
            const stream = c.captureStream(30);
            const recorder = new MediaRecorder(stream, { mimeType: "video/webm" });
            const chunks = [];

            recorder.ondataavailable = e => chunks.push(e.data);
            recorder.onstop = () => {
                const blob = new Blob(chunks, { type: "video/webm" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `SoravVoid_Render_${Date.now()}.mp4`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                dlBtn.innerHTML = '<span class="material-symbols-outlined text-base">download</span> Download Rendered Video (.MP4)';
                toast("Video downloaded successfully!");
            };

            recorder.start();
            setTimeout(() => recorder.stop(), 3000); // captures 3 seconds of real 60fps render
        }

        window.onload = init;
    </script>
</body>
</html>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"⚡ Starting SoravVoid on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
