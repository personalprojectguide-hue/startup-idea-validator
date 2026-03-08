"""
Startup Idea Validator — Reality-check your idea in 2 minutes

Setup:
  pip install -r requirements.txt
  cp .env.example .env          # add your GROQ_API_KEY
  uvicorn main:app --reload
  open http://localhost:8000
"""
import os, sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DB_FILE      = "startup_idea_validator.db"
SYSTEM_PROMPT = "You are an expert Startup Idea Validator assistant. Describe your startup idea. Get an honest validation with market size, competition, and key risks."

app = FastAPI(title="Startup Idea Validator")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── Database ───────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS queries (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT NOT NULL,
                result TEXT,
                ts     TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()

init_db()


# ── Frontend (injected HTML app) ───────────────────────────────────────────────

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Startup Idea Validator</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --acc:#f5c842;
  --acc2:#ffd96a;
  --bg:#09080a;
  --s1:color-mix(in srgb,var(--bg) 60%,#111);
  --s2:color-mix(in srgb,var(--bg) 40%,#1a1a1a);
  --s3:color-mix(in srgb,var(--bg) 20%,#222);
  --b1:rgba(255,255,255,.06);
  --b2:rgba(255,255,255,.11);
  --text:#e8eaef;
  --muted:#6b7280;
  --dim:#374151;
  --ok:#34d399;
  --err:#f87171;
  --r:12px;
}
html{scroll-behavior:smooth}
body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}

/* ── Auth overlay ─────────────────────────────────────────────────── */
#auth-overlay{
  position:fixed;inset:0;z-index:200;
  background:var(--bg);
  display:flex;align-items:center;justify-content:center;
  padding:24px;
}
.auth-box{
  width:100%;max-width:400px;
  background:var(--s1);border:1px solid var(--b2);border-radius:16px;
  padding:36px 32px;
}
.auth-logo{
  font-family:'Syne',sans-serif;font-size:22px;font-weight:800;
  color:var(--acc);margin-bottom:6px;letter-spacing:-.5px;
}
.auth-sub{color:var(--muted);font-size:13px;margin-bottom:28px;font-weight:300}
.auth-tabs{display:flex;gap:0;margin-bottom:24px;background:var(--s2);border-radius:8px;padding:3px}
.auth-tab{
  flex:1;padding:8px;text-align:center;font-size:13px;font-weight:500;
  border-radius:6px;cursor:pointer;transition:all .15s;color:var(--muted);
}
.auth-tab.active{background:var(--s1);color:var(--text);box-shadow:0 1px 4px rgba(0,0,0,.3)}
.auth-field{margin-bottom:14px}
.auth-field label{display:block;font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:6px}
.auth-field input{
  width:100%;background:var(--s2);border:1px solid var(--b1);border-radius:8px;
  color:var(--text);padding:11px 14px;font-size:14px;font-family:'DM Sans',sans-serif;
  outline:none;transition:border-color .2s;
}
.auth-field input:focus{border-color:var(--acc)}
.auth-btn{
  width:100%;background:var(--acc);color:var(--bg);border:none;border-radius:8px;
  padding:12px;font-weight:700;font-size:14px;font-family:'DM Sans',sans-serif;
  cursor:pointer;transition:all .15s;margin-top:4px;
}
.auth-btn:hover{filter:brightness(1.1);transform:translateY(-1px)}
.auth-err{color:var(--err);font-size:12px;margin-top:10px;text-align:center}

/* ── API key banner (html mode only) ─────────────────────────────── */
#apikey-banner{
  display:none;background:rgba(248,113,113,.1);border-bottom:1px solid rgba(248,113,113,.2);
  padding:10px 24px;font-size:12px;color:var(--err);
  align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;
}
#apikey-banner input{
  background:var(--s2);border:1px solid var(--b2);border-radius:6px;
  color:var(--text);padding:7px 12px;font-size:12px;font-family:monospace;
  width:280px;outline:none;
}
#apikey-banner button{
  background:var(--err);color:#fff;border:none;border-radius:6px;
  padding:7px 14px;font-size:12px;cursor:pointer;font-family:'DM Sans',sans-serif;font-weight:600;
}

/* ── Header ───────────────────────────────────────────────────────── */
header{
  position:sticky;top:0;z-index:100;
  display:flex;align-items:center;justify-content:space-between;
  padding:13px 28px;
  background:rgba(0,0,0,.7);backdrop-filter:blur(20px);
  border-bottom:1px solid var(--b1);
}
.hdr-left{display:flex;align-items:center;gap:12px}
.logo{font-family:'Syne',sans-serif;font-size:17px;font-weight:800;color:var(--acc);letter-spacing:-.4px}
.mode-badge{
  font-size:9px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--muted);border:1px solid var(--b2);border-radius:99px;padding:3px 10px;
}
.hdr-right{display:flex;align-items:center;gap:14px}
.user-chip{
  display:flex;align-items:center;gap:7px;
  font-size:12px;color:var(--muted);
}
.user-avatar{
  width:26px;height:26px;border-radius:50%;
  background:var(--acc);color:var(--bg);
  display:flex;align-items:center;justify-content:center;
  font-size:11px;font-weight:700;
}
.btn-logout{
  font-size:11px;color:var(--dim);cursor:pointer;
  background:none;border:1px solid var(--b1);border-radius:6px;
  padding:5px 10px;transition:all .15s;font-family:'DM Sans',sans-serif;
}
.btn-logout:hover{border-color:var(--err);color:var(--err)}

/* ── Layout ───────────────────────────────────────────────────────── */
.wrap{max-width:780px;margin:0 auto;padding:44px 24px 80px}

/* ── Hero ─────────────────────────────────────────────────────────── */
.hero{margin-bottom:40px}
.hero-kicker{
  display:inline-flex;align-items:center;gap:7px;
  font-size:10px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;
  color:var(--acc);opacity:.8;margin-bottom:12px;
}
.hero h1{
  font-family:'Syne',sans-serif;
  font-size:clamp(24px,4.5vw,40px);
  font-weight:800;line-height:1.1;letter-spacing:-1px;margin-bottom:10px;
}
.hero h1 em{
  font-style:normal;
  background:linear-gradient(120deg,var(--acc),var(--acc2));
  -webkit-background-clip:text;background-clip:text;color:transparent;
}
.hero p{color:var(--muted);font-size:14px;line-height:1.75;font-weight:300}

/* ── Cards ────────────────────────────────────────────────────────── */
.card{
  background:var(--s1);border:1px solid var(--b1);
  border-radius:var(--r);padding:24px;margin-bottom:14px;
  transition:border-color .2s;
}
.card:focus-within{border-color:var(--b2)}
.card-hd{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px}
.card-lbl{font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--dim)}
.card-action{font-size:11px;color:var(--dim);cursor:pointer;transition:color .15s;background:none;border:none;font-family:'DM Sans',sans-serif}
.card-action:hover{color:var(--muted)}

/* ── Inputs ───────────────────────────────────────────────────────── */
.field{margin-bottom:16px}
.field:last-child{margin-bottom:0}
.field label{display:block;font-size:11px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);margin-bottom:7px}
.field input[type=text],
.field textarea,
.field select{
  width:100%;background:var(--s2);border:1px solid var(--b1);border-radius:9px;
  color:var(--text);padding:12px 14px;font-size:14px;
  font-family:'DM Sans',sans-serif;font-weight:300;
  outline:none;transition:border-color .2s,box-shadow .2s;
}
.field input[type=text]:focus,
.field textarea:focus,
.field select:focus{
  border-color:color-mix(in srgb,var(--acc) 60%,transparent);
  box-shadow:0 0 0 3px color-mix(in srgb,var(--acc) 8%,transparent);
}
.field input[type=text]::placeholder,
.field textarea::placeholder{color:var(--dim)}
.field textarea{resize:vertical;min-height:110px;line-height:1.6}
.field select{cursor:pointer;appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 14px center;padding-right:36px}
.field select option{background:var(--s2)}

/* ── Buttons ──────────────────────────────────────────────────────── */
.btn-row{display:flex;align-items:center;gap:10px;margin-top:20px;flex-wrap:wrap}
.btn-primary{
  font-family:'DM Sans',sans-serif;
  background:var(--acc);color:var(--bg);
  border:none;border-radius:8px;padding:11px 26px;
  font-weight:700;font-size:14px;cursor:pointer;
  transition:all .15s;display:inline-flex;align-items:center;gap:7px;
  box-shadow:0 2px 14px color-mix(in srgb,var(--acc) 30%,transparent);
}
.btn-primary:hover{filter:brightness(1.08);transform:translateY(-1px);box-shadow:0 6px 22px color-mix(in srgb,var(--acc) 40%,transparent)}
.btn-primary:active{transform:none;box-shadow:none}
.btn-primary:disabled{opacity:.3;cursor:not-allowed;transform:none;box-shadow:none}
.btn-ghost{
  font-family:'DM Sans',sans-serif;background:transparent;
  color:var(--muted);border:1px solid var(--b2);border-radius:8px;
  padding:11px 18px;font-size:13px;cursor:pointer;transition:all .15s;
}
.btn-ghost:hover{border-color:var(--b2);color:var(--text);background:var(--s2)}
.hint{font-size:11px;color:var(--dim)}

/* ── Loading ──────────────────────────────────────────────────────── */
.loading{
  display:none;align-items:center;gap:10px;
  margin-top:16px;color:var(--acc);font-size:13px;font-weight:400;
}
.spin{
  width:16px;height:16px;flex-shrink:0;
  border:2px solid color-mix(in srgb,var(--acc) 20%,transparent);
  border-top-color:var(--acc);border-radius:50%;
  animation:spin .55s linear infinite;
}
@keyframes spin{to{transform:rotate(360deg)}}

/* ── Result ───────────────────────────────────────────────────────── */
#result-card{display:none}
.result-actions-bar{display:flex;gap:8px;margin-top:14px;padding-top:14px;border-top:1px solid var(--b1);flex-wrap:wrap}
.result-action-btn{display:inline-flex;align-items:center;gap:5px;background:transparent;border:1px solid var(--b2);color:var(--muted);border-radius:6px;padding:6px 13px;font-size:11px;font-weight:600;cursor:pointer;transition:all .15s;font-family:inherit}
.result-action-btn:hover{border-color:var(--acc);color:var(--acc)}
.result-hd{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}
.result-lbl{font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--dim)}
.copy-btn{
  display:inline-flex;align-items:center;gap:5px;
  font-size:11px;color:var(--muted);background:none;
  border:1px solid var(--b1);border-radius:6px;padding:5px 10px;
  cursor:pointer;transition:all .15s;font-family:'DM Sans',sans-serif;
}
.copy-btn:hover{border-color:var(--acc);color:var(--acc)}
.copy-btn.copied{border-color:var(--ok);color:var(--ok)}

/* result format: text */
.result-text{
  background:var(--s2);border:1px solid var(--b1);
  border-left:2px solid var(--acc);
  border-radius:0 9px 9px 0;padding:18px 20px;
  font-size:14px;line-height:1.8;white-space:pre-wrap;
  color:var(--text);font-weight:300;
  animation:fadeUp .2s ease;
}

/* result format: list */
.result-list{list-style:none;display:flex;flex-direction:column;gap:10px}
.result-list li{
  background:var(--s2);border:1px solid var(--b1);border-radius:9px;
  padding:14px 16px;font-size:14px;line-height:1.7;color:var(--text);
  font-weight:300;animation:fadeUp .2s ease both;
}
.result-list li strong{color:var(--acc);display:block;font-size:13px;margin-bottom:4px}
.result-list .item-num{
  display:inline-flex;align-items:center;justify-content:center;
  width:20px;height:20px;border-radius:50%;
  background:color-mix(in srgb,var(--acc) 15%,transparent);
  color:var(--acc);font-size:10px;font-weight:700;flex-shrink:0;margin-right:8px;
}

/* result format: steps */
.result-steps{display:flex;flex-direction:column;gap:10px}
.result-step{
  display:flex;gap:14px;
  background:var(--s2);border:1px solid var(--b1);border-radius:9px;
  padding:14px 16px;animation:fadeUp .2s ease both;
}
.step-num{
  display:flex;align-items:center;justify-content:center;flex-shrink:0;
  width:28px;height:28px;border-radius:50%;
  background:var(--acc);color:var(--bg);
  font-size:12px;font-weight:700;margin-top:1px;
}
.step-body{font-size:14px;line-height:1.7;color:var(--text);font-weight:300}
.step-body strong{display:block;color:var(--text);font-weight:600;margin-bottom:3px;font-size:13px}

@keyframes fadeUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}

/* ── History ──────────────────────────────────────────────────────── */
#history-section{margin-top:10px}
.history-empty{color:var(--dim);font-size:13px;text-align:center;padding:16px 0}
.history-item{
  padding:14px 0;border-bottom:1px solid var(--b1);
  display:grid;grid-template-columns:1fr auto;gap:12px;align-items:start;
  cursor:pointer;transition:opacity .15s;
}
.history-item:last-child{border:none}
.history-item:hover{opacity:.8}
.hi-prompt{font-size:12px;color:var(--muted);margin-bottom:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hi-preview{font-size:12px;color:var(--dim);line-height:1.5;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.hi-time{font-size:10px;color:var(--dim);white-space:nowrap;padding-top:2px}
.hi-del{background:none;border:none;color:var(--dim);cursor:pointer;font-size:14px;padding:0 4px;line-height:1;transition:color .15s}
.hi-del:hover{color:var(--err)}

/* ── Footer ───────────────────────────────────────────────────────── */
footer{
  margin-top:60px;padding-top:18px;border-top:1px solid var(--b1);
  display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;
}
.foot-note{font-size:11px;color:var(--dim)}
.foot-links{display:flex;gap:14px}
.foot-links a{font-size:11px;color:var(--dim);text-decoration:none;transition:color .15s}
.foot-links a:hover{color:var(--muted)}

/* ── Responsive ───────────────────────────────────────────────────── */
@media(max-width:600px){
  .wrap{padding:28px 16px 60px}
  .hero h1{font-size:26px}
  .auth-box{padding:28px 20px}
}
</style>
</head>
<body>

<!-- ── Auth Overlay ──────────────────────────────────────────────── -->
<div id="auth-overlay">
  <div class="auth-box">
    <div class="auth-logo">Startup Idea Validator</div>
    <div class="auth-sub">Reality-check your idea in 2 minutes</div>
    <div class="auth-tabs">
      <div class="auth-tab active" onclick="switchTab('login')">Log in</div>
      <div class="auth-tab" onclick="switchTab('signup')">Sign up</div>
    </div>
    <div id="login-form">
      <div class="auth-field"><label>Email</label><input type="email" id="login-email" placeholder="you@example.com"></div>
      <div class="auth-field"><label>Password</label><input type="password" id="login-pw" placeholder="••••••••"></div>
      <button class="auth-btn" onclick="login()">Log in</button>
    </div>
    <div id="signup-form" style="display:none">
      <div class="auth-field"><label>Your name</label><input type="text" id="signup-name" placeholder="Jane Smith"></div>
      <div class="auth-field"><label>Email</label><input type="email" id="signup-email" placeholder="you@example.com"></div>
      <div class="auth-field"><label>Password</label><input type="password" id="signup-pw" placeholder="Min 6 characters"></div>
      <button class="auth-btn" onclick="signup()">Create account</button>
    </div>
    <div class="auth-err" id="auth-err"></div>
  </div>
</div>

<!-- ── API Key Banner (html mode) ───────────────────────────────── -->
<div id="setup-overlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.85);backdrop-filter:blur(12px);z-index:200;align-items:center;justify-content:center;">
  <!-- LOCAL: key input (only shown on localhost) -->
  <div id="setup-local" style="background:var(--s1);border:1px solid var(--b2);border-radius:16px;padding:40px;max-width:460px;width:90%;text-align:center;display:none;">
    <div style="font-size:36px;margin-bottom:12px;">🔑</div>
    <h2 style="font-family:'Syne',sans-serif;font-size:20px;font-weight:800;margin-bottom:8px;">One-time setup</h2>
    <p style="color:var(--muted);font-size:13px;line-height:1.7;margin-bottom:6px;">Paste your free Groq API key below and you're done.<br>You'll never need to touch a config file.</p>
    <p style="margin-bottom:24px;"><a href="https://console.groq.com" target="_blank" style="color:var(--acc);font-size:12px;font-weight:600;">Get a free key at console.groq.com →</a></p>
    <input id="setup-key-input" type="password" placeholder="gsk_..."
      style="width:100%;background:var(--s2);border:1px solid var(--b2);border-radius:8px;color:var(--text);padding:12px 16px;font-size:14px;outline:none;margin-bottom:12px;font-family:monospace;letter-spacing:.05em;box-sizing:border-box;">
    <div id="setup-err" style="color:#ff6b6b;font-size:12px;margin-bottom:10px;min-height:18px;"></div>
    <button onclick="saveSetupKey()"
      style="width:100%;background:var(--acc);color:#fff;border:none;border-radius:8px;padding:12px;font-weight:700;font-size:14px;cursor:pointer;font-family:'Syne',sans-serif;">
      Save &amp; Start Using the App
    </button>
    <p style="color:var(--dim);font-size:11px;margin-top:14px;">Your key is stored in a .env file on your machine only.</p>
  </div>
  <!-- DEPLOYED: not configured message (shown on any non-localhost domain) -->
  <div id="setup-deployed" style="background:var(--s1);border:1px solid var(--b2);border-radius:16px;padding:40px;max-width:460px;width:90%;text-align:center;display:none;">
    <div style="font-size:36px;margin-bottom:12px;">⚙️</div>
    <h2 style="font-family:'Syne',sans-serif;font-size:20px;font-weight:800;margin-bottom:8px;">App not configured</h2>
    <p style="color:var(--muted);font-size:13px;line-height:1.7;margin-bottom:20px;">This app needs a Groq API key to work. If you're the owner, add <code style="background:var(--s2);padding:2px 6px;border-radius:4px;font-size:12px;">GROQ_API_KEY</code> as an environment variable in your hosting dashboard (Railway, Render, or Replit).</p>
    <a href="https://console.groq.com" target="_blank"
      style="display:inline-block;background:var(--acc);color:#fff;text-decoration:none;border-radius:8px;padding:10px 20px;font-weight:700;font-size:13px;font-family:'Syne',sans-serif;">
      Get a free Groq key →
    </a>
  </div>
</div>

<div id="apikey-banner">
  <span>⚡ Enter your free Groq API key to use this app</span>
  <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
    <input type="password" id="apikey-input" placeholder="gsk_..." style="">
    <button onclick="saveApiKey()">Save key</button>
    <a href="https://console.groq.com" target="_blank" style="font-size:11px;color:var(--muted);text-decoration:none">Get free key →</a>
  </div>
</div>

<!-- ── Header ────────────────────────────────────────────────────── -->
<header id="main-header" style="display:none">
  <div class="hdr-left">
    <div class="logo">Startup Idea Validator</div>
    <div class="mode-badge" id="mode-badge">HTML App</div>
  </div>
  <div class="hdr-right">
    <div class="user-chip">
      <div class="user-avatar" id="user-avatar">?</div>
      <span id="user-name"></span>
    </div>
    <button class="btn-logout" onclick="logout()">Log out</button>
  </div>
</header>

<!-- ── Main App ───────────────────────────────────────────────────── -->
<div class="wrap" id="main-app" style="display:none">
  <div class="hero">
    <div class="hero-kicker">AI Tool</div>
    <h1><em>Startup Idea Validator</em><br>Reality-check your idea in 2 minutes</h1>
    <p>Describe your startup idea. Get an honest validation with market size, competition, and key risks. Built for users.</p>
  </div>

  <!-- Input Card -->
  <div class="card" id="input-card">
    <div class="card-hd">
      <div class="card-lbl">Your inputs</div>
      <button class="card-action" onclick="clearForm()">Clear</button>
    </div>
        <div class="field">
      <label for="field-idea_description">Idea Description</label>
      <textarea id="field-idea_description" placeholder="Enter idea description..." required></textarea>
    </div>
    <div class="field">
      <label for="field-target_market">Target Market</label>
      <input type="text" id="field-target_market" placeholder="e.g. your target market">
    </div>
    <div class="field">
      <label for="field-revenue_model">Revenue Model</label>
      <input type="text" id="field-revenue_model" placeholder="e.g. your revenue model">
    </div>
    <div class="btn-row">
      <button class="btn-primary" onclick="generate()" id="gen-btn">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><polygon points="5,3 19,12 5,21"/></svg>
        Generate
      </button>
      <span class="hint">Ctrl + Enter</span>
    </div>
    <div class="loading" id="loading">
      <div class="spin"></div>
      <span id="loading-text">Generating...</span>
    </div>
  </div>

  <!-- Result Card -->
  <div class="card" id="result-card">
    <div class="result-hd">
      <div class="result-lbl">Result</div>
      <button class="copy-btn" id="copy-btn" onclick="copyResult()">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
        Copy
      </button>
    </div>
    <div id="result-content"></div>
    <div class="result-actions-bar">
      <button class="result-action-btn" onclick="regenerate()">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
        Regenerate
      </button>
      <button class="result-action-btn" onclick="improveResult()">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
        Improve
      </button>
      <button class="result-action-btn" onclick="differentStyle()">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/><path d="M4.93 4.93a10 10 0 0 0 0 14.14"/></svg>
        Different Style
      </button>
    </div>
  </div>

  <!-- History Card -->
  <div class="card" id="history-section">
    <div class="card-hd">
      <div class="card-lbl">History</div>
      <button class="card-action" onclick="clearHistory()">Clear all</button>
    </div>
    <div id="history-list"><div class="history-empty">No history yet — generate something above.</div></div>
  </div>

  <footer>
    <div class="foot-note">Startup Idea Validator &middot; Powered by Groq llama-3.3-70b</div>
    <div class="foot-links">
      <a href="#" onclick="logout();return false">Log out</a>
      
    </div>
  </footer>
</div>

<script>
// ── App config (injected by generator) ─────────────────────────────
const APP = {
  name:           'Startup Idea Validator',
  mode:           'fastapi',          // 'html' or 'fastapi'
  auth:           false,    // true | false
  systemPrompt:   "You are an expert Startup Idea Validator assistant. Describe your startup idea. Get an honest validation with market size, competition, and key risks.",
  promptTemplate: "Idea Description: {{idea_description}}\\nTarget Market: {{target_market}}\\nRevenue Model: {{revenue_model}}",
  resultFormat:   'steps', // text | list | steps
  resultConfig:   {"label": "Result", "copyable": true},
  inputs:         [{"id": "idea_description", "label": "Idea Description", "type": "textarea", "placeholder": "Enter idea description...", "required": true}, {"id": "target_market", "label": "Target Market", "type": "text", "placeholder": "e.g. your target market", "required": false}, {"id": "revenue_model", "label": "Revenue Model", "type": "text", "placeholder": "e.g. your revenue model", "required": false}],
};

// ── Auth (localStorage) ────────────────────────────────────────────
const USERS_KEY = APP.name + ':users';
const SESSION_KEY = APP.name + ':session';

function getUsers(){ try{ return JSON.parse(localStorage.getItem(USERS_KEY)||'{}') }catch{return {}} }
function getSession(){ try{ return JSON.parse(localStorage.getItem(SESSION_KEY)||'null') }catch{return null} }
function saveSession(s){ localStorage.setItem(SESSION_KEY, JSON.stringify(s)) }

function switchTab(tab){
  document.getElementById('login-form').style.display = tab==='login'?'':'none';
  document.getElementById('signup-form').style.display = tab==='signup'?'':'none';
  document.querySelectorAll('.auth-tab').forEach((t,i)=>t.classList.toggle('active',i===(tab==='login'?0:1)));
  document.getElementById('auth-err').textContent='';
}

function signup(){
  const name=document.getElementById('signup-name').value.trim();
  const email=document.getElementById('signup-email').value.trim().toLowerCase();
  const pw=document.getElementById('signup-pw').value;
  if(!name||!email||!pw){setAuthErr('All fields required.');return}
  if(pw.length<6){setAuthErr('Password must be 6+ characters.');return}
  const users=getUsers();
  if(users[email]){setAuthErr('Account already exists. Log in instead.');return}
  users[email]={name,pw,created:Date.now()};
  localStorage.setItem(USERS_KEY, JSON.stringify(users));
  saveSession({email,name});
  onLoggedIn({email,name});
}

function login(){
  const email=document.getElementById('login-email').value.trim().toLowerCase();
  const pw=document.getElementById('login-pw').value;
  if(!email||!pw){setAuthErr('Enter your email and password.');return}
  const users=getUsers();
  if(!users[email]||users[email].pw!==pw){setAuthErr('Incorrect email or password.');return}
  const session={email,name:users[email].name};
  saveSession(session);
  onLoggedIn(session);
}

function logout(){
  localStorage.removeItem(SESSION_KEY);
  document.getElementById('auth-overlay').style.display='flex';
  document.getElementById('main-header').style.display='none';
  document.getElementById('main-app').style.display='none';
  document.getElementById('auth-err').textContent='';
  document.getElementById('login-email').value='';
  document.getElementById('login-pw').value='';
}

function setAuthErr(msg){ document.getElementById('auth-err').textContent=msg }

function onLoggedIn(session){
  document.getElementById('auth-overlay').style.display='none';
  document.getElementById('main-header').style.display='flex';
  document.getElementById('main-app').style.display='block';
  document.getElementById('user-name').textContent=session.name.split(' ')[0];
  document.getElementById('user-avatar').textContent=session.name[0].toUpperCase();
  checkApiKey();
  renderHistory();
}

// ── API key (html mode) ────────────────────────────────────────────
function checkApiKey(){
  if(APP.mode!=='html') return;
  const key=localStorage.getItem(APP.name+':apikey')||'';
  document.getElementById('apikey-banner').style.display = key ? 'none' : 'flex';
  if(key) document.getElementById('apikey-input').value=key;
}
function saveApiKey(){
  const key=document.getElementById('apikey-input').value.trim();
  if(!key){return}
  localStorage.setItem(APP.name+':apikey', key);
  document.getElementById('apikey-banner').style.display='none';
}

// ── Prompt assembly ────────────────────────────────────────────────
function buildPrompt(){
  let prompt=APP.promptTemplate;
  for(const inp of APP.inputs){
    const el=document.getElementById('field-'+inp.id);
    const val=el ? el.value.trim() : '';
    if(inp.required && !val){
      throw new Error(`Please fill in "${inp.label}"`);
    }
    prompt=prompt.replace(new RegExp('\\\\{\\\\{'+inp.id+'\\\\}\\\\}','g'), val||'(not specified)');
  }
  return prompt;
}

// ── Groq API call ──────────────────────────────────────────────────
async function callGroq(userPrompt){
  if(APP.mode==='html'){
    const key=localStorage.getItem(APP.name+':apikey')||'';
    if(!key) throw new Error('Please enter your Groq API key above.');
    const r=await fetch('https://api.groq.com/openai/v1/chat/completions',{
      method:'POST',
      headers:{'Authorization':'Bearer '+key,'Content-Type':'application/json'},
      body:JSON.stringify({
        model:'llama-3.3-70b-versatile',
        messages:[
          {role:'system',content:APP.systemPrompt},
          {role:'user',content:userPrompt}
        ],
        max_tokens:1500
      })
    });
    if(!r.ok){
      const e=await r.json().catch(()=>({}));
      throw new Error(e?.error?.message||'Groq API error '+r.status);
    }
    const d=await r.json();
    return d.choices[0].message.content;
  } else {
    const r=await fetch('/api/generate',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({prompt:userPrompt})
    });
    if(!r.ok){
      const e=await r.json().catch(()=>({}));
      if(e?.detail==='NO_KEY'){ showSetup(); throw new Error('__SILENT__'); }
      throw new Error(e?.detail||'Server error '+r.status);
    }
    const d=await r.json();
    return d.result;
  }
}

// ── Generate ───────────────────────────────────────────────────────
let lastResult='';
let lastPrompt='';

async function generate(){
  let prompt;
  try{ prompt=buildPrompt() }catch(e){ showErr(e.message); return; }
  lastPrompt = prompt;
  setLoading(true);
  document.getElementById('result-card').style.display='none';
  try{
    const result=await callGroq(prompt);
    lastResult=result;
    renderResult(result);
    saveToHistory(prompt, result);
    renderHistory();
  }catch(e){
    if(e.message!=="__SILENT__") showErr(e.message);
  }finally{
    setLoading(false);
  }
}

// ── Result rendering ───────────────────────────────────────────────
function renderResult(text){
  const card=document.getElementById('result-card');
  const content=document.getElementById('result-content');
  card.style.display='block';
  card.scrollIntoView({behavior:'smooth',block:'nearest'});

  if(APP.resultFormat==='text'){
    content.innerHTML=`<div class="result-text">${esc(text)}</div>`;
  }
  else if(APP.resultFormat==='list'){
    // Split on double newlines or numbered lines
    const items=parseList(text);
    const ul=document.createElement('ul');
    ul.className='result-list';
    items.forEach((item,i)=>{
      const li=document.createElement('li');
      li.style.animationDelay=(i*0.04)+'s';
      // Bold the first line if multi-line
      const lines=item.trim().split('\\n');
      if(lines.length>1){
        li.innerHTML=`<span class="item-num">${i+1}</span><strong>${esc(lines[0])}</strong>${esc(lines.slice(1).join('\\n'))}`;
      } else {
        li.innerHTML=`<span class="item-num">${i+1}</span>${esc(item)}`;
      }
      ul.appendChild(li);
    });
    content.innerHTML='';
    content.appendChild(ul);
  }
  else if(APP.resultFormat==='steps'){
    const steps=parseSteps(text);
    const wrap=document.createElement('div');
    wrap.className='result-steps';
    steps.forEach((step,i)=>{
      const div=document.createElement('div');
      div.className='result-step';
      div.style.animationDelay=(i*0.05)+'s';
      div.innerHTML=`<div class="step-num">${i+1}</div><div class="step-body">${formatStepBody(step)}</div>`;
      wrap.appendChild(div);
    });
    content.innerHTML='';
    content.appendChild(wrap);
  }
}

function parseList(text){
  // Try numbered list first: "1. item" or "1) item"
  const numbered=text.match(/^\\d+[\\.\\)]\\s+.+/mg);
  if(numbered && numbered.length>=2){
    // Group multi-line items
    const items=[];
    let cur='';
    for(const line of text.split('\\n')){
      if(/^\\d+[\\.\\)]\\s/.test(line)){
        if(cur) items.push(cur.trim());
        cur=line.replace(/^\\d+[\\.\\)]\\s+/,'');
      } else if(cur){
        cur+='\\n'+line;
      }
    }
    if(cur) items.push(cur.trim());
    return items.filter(Boolean);
  }
  // Fall back to double-newline split
  const blocks=text.split(/\\n{2,}/).filter(b=>b.trim());
  if(blocks.length>=2) return blocks;
  // Last resort: single newlines
  return text.split('\\n').filter(l=>l.trim());
}

function parseSteps(text){
  // Try to find bold headers or numbered steps
  const numbered=[];
  let cur='';
  for(const line of text.split('\\n')){
    if(/^\\d+[\\.\\)]\\s/.test(line)||/^\\*\\*[\\w]/.test(line)){
      if(cur.trim()) numbered.push(cur.trim());
      cur=line.replace(/^\\d+[\\.\\)]\\s+/,'').replace(/^\\*\\*/,'').replace(/\\*\\*$/,'');
    } else {
      cur+='\\n'+line;
    }
  }
  if(cur.trim()) numbered.push(cur.trim());
  if(numbered.length>=2) return numbered;
  // Fall back to paragraphs
  return text.split(/\\n{2,}/).filter(b=>b.trim());
}

function formatStepBody(text){
  // Convert **bold** to <strong>
  return esc(text).replace(/\\*\\*(.+?)\\*\\*/g,'<strong>$1</strong>');
}

function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\\n/g,'<br>')}

// ── Copy ───────────────────────────────────────────────────────────
async function copyResult(){
  try{
    await navigator.clipboard.writeText(lastResult);
    const btn=document.getElementById('copy-btn');
    btn.textContent='✓ Copied!';
    btn.classList.add('copied');
    setTimeout(()=>{btn.innerHTML='<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg> Copy';btn.classList.remove('copied')},2000);
  }catch{}
}

// ── History ────────────────────────────────────────────────────────
const HIST_KEY = APP.name + ':history';
function loadHistory(){ try{return JSON.parse(localStorage.getItem(HIST_KEY)||'[]')}catch{return []} }
function saveToHistory(prompt,result){
  const hist=loadHistory();
  hist.unshift({id:Date.now(),prompt:prompt.substring(0,120),result,ts:new Date().toLocaleString()});
  localStorage.setItem(HIST_KEY, JSON.stringify(hist.slice(0,50)));
}
function deleteHistoryItem(id){
  const hist=loadHistory().filter(h=>h.id!==id);
  localStorage.setItem(HIST_KEY, JSON.stringify(hist));
  renderHistory();
}
function clearHistory(){
  localStorage.removeItem(HIST_KEY);
  renderHistory();
}
function renderHistory(){
  const hist=loadHistory();
  const el=document.getElementById('history-list');
  if(!hist.length){el.innerHTML='<div class="history-empty">No history yet — generate something above.</div>';return}
  el.innerHTML=hist.map(h=>`
    <div class="history-item" onclick="loadHistoryItem(${h.id})">
      <div>
        <div class="hi-prompt">${esc(h.prompt)}</div>
        <div class="hi-preview">${esc((h.result||'').substring(0,100))}</div>
      </div>
      <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px">
        <span class="hi-time">${h.ts}</span>
        <button class="hi-del" onclick="event.stopPropagation();deleteHistoryItem(${h.id})" title="Delete">✕</button>
      </div>
    </div>
  `).join('');
}
function loadHistoryItem(id){
  const item=loadHistory().find(h=>h.id===id);
  if(!item) return;
  lastResult=item.result;
  renderResult(item.result);
}

// ── Utils ──────────────────────────────────────────────────────────
function setLoading(on){
  document.getElementById('gen-btn').disabled=on;
  document.getElementById('loading').style.display=on?'flex':'none';
}
function showErr(msg){
  alert(msg); // simple for now — could be a toast
}
function clearForm(){
  APP.inputs.forEach(inp=>{
    const el=document.getElementById('field-'+inp.id);
    if(el) el.value='';
  });
  document.getElementById('result-card').style.display='none';
}

// ── Keyboard shortcut ──────────────────────────────────────────────
document.addEventListener('keydown',e=>{
  if(e.ctrlKey&&e.key==='Enter'&&document.getElementById('main-app').style.display!=='none'){
    generate();
  }
});

// ── Result actions ─────────────────────────────────────────────────
async function regenerate(){
  if(!lastPrompt) return;
  setLoading(true);
  document.getElementById('result-card').style.display='none';
  try{
    const result = await callGroq(lastPrompt);
    lastResult = result;
    renderResult(result);
    saveToHistory(lastPrompt, result);
    renderHistory();
  }catch(e){
    if(e.message!=='__SILENT__') showErr(e.message);
  }finally{ setLoading(false); }
}

async function improveResult(){
  if(!lastResult) return;
  setLoading(true);
  document.getElementById('result-card').style.display='none';
  const improvePrompt = 'Improve and expand this result, making it significantly better:\\n\\n' + lastResult;
  try{
    const result = await callGroq(improvePrompt);
    lastResult = result;
    renderResult(result);
    saveToHistory(improvePrompt, result);
    renderHistory();
  }catch(e){
    if(e.message!=='__SILENT__') showErr(e.message);
  }finally{ setLoading(false); }
}

async function differentStyle(){
  if(!lastResult) return;
  setLoading(true);
  document.getElementById('result-card').style.display='none';
  const stylePrompt = 'Rewrite this in a completely different style, tone, and format — same content, fresh approach:\\n\\n' + lastResult;
  try{
    const result = await callGroq(stylePrompt);
    lastResult = result;
    renderResult(result);
    saveToHistory(stylePrompt, result);
    renderHistory();
  }catch(e){
    if(e.message!=='__SILENT__') showErr(e.message);
  }finally{ setLoading(false); }
}

// ── Setup (first-run API key) ───────────────────────────────────────
function showSetup(){
  const overlay = document.getElementById('setup-overlay');
  const isLocal = location.hostname === 'localhost' || location.hostname === '127.0.0.1';
  document.getElementById('setup-local').style.display = isLocal ? 'block' : 'none';
  document.getElementById('setup-deployed').style.display = isLocal ? 'none' : 'block';
  overlay.style.display = 'flex';
  if(isLocal) setTimeout(()=>document.getElementById('setup-key-input').focus(), 100);
}
async function saveSetupKey(){
  const key=document.getElementById('setup-key-input').value.trim();
  const errEl=document.getElementById('setup-err');
  errEl.textContent='';
  if(!key){errEl.textContent='Please paste your API key.';return;}
  if(!key.startsWith('gsk_')){errEl.textContent="That doesn't look right — Groq keys start with gsk_";return;}
  try{
    const r=await fetch('/api/setup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_key:key})});
    if(!r.ok){const e=await r.json().catch(()=>({}));errEl.textContent=e?.detail||'Error saving key.';return;}
    document.getElementById('setup-overlay').style.display='none';
  }catch(e){errEl.textContent='Could not save key: '+e.message;}
}

// ── Boot ───────────────────────────────────────────────────────────
(function init(){
  // Preview mode: Launchpad injects __LP_PREVIEW__ to bypass auth
  if(typeof __LP_PREVIEW__ !== 'undefined' && __LP_PREVIEW__){
    const previewSession = {email:'preview@launchpad.app', name:'Preview'};
    saveSession(previewSession);
    onLoggedIn(previewSession);
    return;
  }
  // No-auth mode: skip login entirely
  if(!APP.auth){
    document.getElementById('auth-overlay').style.display='none';
    document.getElementById('main-header').style.display='flex';
    document.getElementById('main-app').style.display='block';
    document.querySelector('.btn-logout') && (document.querySelector('.btn-logout').style.display='none');
    document.getElementById('user-section') && (document.getElementById('user-section').style.display='none');
    if(APP.mode==='fastapi'){
      fetch('/api/health').then(r=>r.json()).then(d=>{
        if(!d.ai_ready) showSetup();
      }).catch(()=>{});
    }
    return;
  }
  const session=getSession();
  if(session){
    onLoggedIn(session);
    // Check if API key is set — show setup screen if not
    if(APP.mode==='fastapi'){
      fetch('/api/health').then(r=>r.json()).then(d=>{
        if(!d.ai_ready) showSetup();
      }).catch(()=>{});
    }
  }
})();
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML_PAGE


# ── API ────────────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str

class SetupRequest(BaseModel):
    api_key: str

@app.post("/api/setup")
def setup(req: SetupRequest):
    """Write the API key to .env so user never has to touch a file."""
    key = req.api_key.strip()
    if not key.startswith("gsk_"):
        raise HTTPException(400, detail="Invalid key. Groq keys start with gsk_")
    # Write .env file
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    with open(env_path, "w") as f:
        f.write("GROQ_API_KEY=" + key + chr(10))
    # Reload into current process
    os.environ["GROQ_API_KEY"] = key
    global GROQ_API_KEY
    GROQ_API_KEY = key
    return {"ok": True}

@app.post("/api/generate")
async def generate(req: GenerateRequest):
    if not GROQ_API_KEY:
        raise HTTPException(400, detail="NO_KEY")
    async with httpx.AsyncClient(timeout=40) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": req.prompt},
                ],
                "max_tokens": 1500,
            },
        )
        r.raise_for_status()
        result = r.json()["choices"][0]["message"]["content"]
    with get_db() as conn:
        conn.execute("INSERT INTO queries (prompt, result) VALUES (?, ?)", (req.prompt, result))
        conn.commit()
    return {"result": result}

@app.get("/api/history")
def history():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, prompt, result, ts FROM queries ORDER BY ts DESC LIMIT 20"
        ).fetchall()
    return [dict(r) for r in rows]

@app.get("/api/health")
def health():
    return {"status": "ok", "app": "Startup Idea Validator", "ai_ready": bool(GROQ_API_KEY)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
