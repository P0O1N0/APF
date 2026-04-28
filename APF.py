#!/usr/bin/env python3
"""
   ╔══════════════════════════════════════════════════════════╗
   ║                Admin Panel Finder v1.0                   ║
   ║                    #Author: P0O1N0                       ║
   ╚══════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import uuid
import time
import threading
import subprocess
import importlib
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse

def install(package: str) -> None:
    """Install a pip package if not already present."""
    subprocess.check_call([sys.executable, "-m", "pip", "install", package],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

for lib in ["flask", "requests"]:
    try:
        importlib.import_module(lib)
    except ImportError:
        print(f"[+] Installing {lib} …")
        install(lib)

import flask
import requests
from flask import Flask, request, jsonify, render_template_string

HOST = "127.0.0.1"
PORT = 5000
SCAN_TIMEOUT = 5
MAX_WORKERS = 20

PATHS_FILE = "PATHS_LIST.txt"

def load_paths_from_file(file_path: str) -> list:
    paths = []
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        paths.append(line)
            if paths:
                print(f"[+] {len(paths)} paths loaded from {file_path}")
                return paths
            else:
                print(f"[!] {file_path} is empty. Please add paths (one per line).")
        except Exception as e:
            print(f"[!] Error reading {file_path}: {e}")
    else:
        print(f"[!] {file_path} not found. Creating an empty file. Please add your admin paths.")
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("# Admin Panel Paths\n# One path per line\n\n")
        except Exception as e:
            print(f"[!] Could not create {file_path}: {e}")
    
    return paths

ADMIN_PATHS = load_paths_from_file(PATHS_FILE)

# ------------------------------------------------------------------------------
# Flask app
# ------------------------------------------------------------------------------
app = Flask(__name__)

scans: dict[str, dict] = {}

# ------------------------------------------------------------------------------
# HTML template
# ------------------------------------------------------------------------------
HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel Finder Pro</title>
    <style>
        /* ---------- Base & Variables ---------- */
        :root {
            --bg-dark: #0c0c1d;
            --bg-card: rgba(20, 20, 45, 0.65);
            --green-neon: #00ff88;
            --purple-neon: #bb00ff;
            --red-error: #ff4d6a;
            --text: #e0e0f0;
            --border: rgba(187, 0, 255, 0.3);
            --glow: 0 0 12px rgba(187, 0, 255, 0.5);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            background: radial-gradient(ellipse at top, #1a1a3a, #0c0c1d);
            font-family: 'Segoe UI', 'Inter', system-ui, -apple-system, sans-serif;
            color: var(--text);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
            overflow-x: hidden;
        }

        .glass-card {
            background: var(--bg-card);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            border: 1px solid var(--border);
            border-radius: 24px;
            box-shadow: 0 25px 60px rgba(0,0,0,0.7), var(--glow);
            padding: 40px 30px;
            max-width: 800px;
            width: 100%;
            margin: 20px auto;
            animation: fadeInUp 0.7s ease;
        }

        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(40px); }
            to   { opacity: 1; transform: translateY(0); }
        }

        .logo-container {
            text-align: center;
            margin-bottom: 25px;
        }
        .logo-svg {
            width: 120px;
            height: 120px;
            filter: drop-shadow(0 0 25px var(--purple-neon));
        }

        h1 {
            text-align: center;
            font-size: 2.1rem;
            font-weight: 700;
            letter-spacing: 1px;
            background: linear-gradient(135deg, var(--green-neon), var(--purple-neon));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #a0a0c0;
            font-size: 0.95rem;
            margin-bottom: 30px;
        }

        .input-group {
            margin-bottom: 20px;
            position: relative;
        }
        label {
            display: block;
            font-weight: 600;
            margin-bottom: 8px;
            color: var(--purple-neon);
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        input, textarea, select {
            width: 100%;
            padding: 14px 18px;
            border-radius: 16px;
            border: 1px solid var(--border);
            background: rgba(15, 15, 35, 0.75);
            backdrop-filter: blur(8px);
            color: #f0f0ff;
            font-size: 0.95rem;
            transition: all 0.3s ease;
            outline: none;
            resize: vertical;
        }
        input:focus, textarea:focus {
            border-color: var(--green-neon);
            box-shadow: 0 0 18px rgba(0, 255, 136, 0.3);
        }
        textarea {
            height: 150px;
            font-family: 'Courier New', monospace;
            line-height: 1.5;
        }

        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 18px 0;
        }
        .checkbox-group input[type="checkbox"] {
            width: auto;
            margin: 0;
            accent-color: var(--purple-neon);
            transform: scale(1.2);
        }
        .checkbox-group label {
            margin: 0;
            color: #d0d0e8;
            text-transform: none;
            font-size: 0.95rem;
            font-weight: 500;
        }

        .btn {
            background: linear-gradient(135deg, var(--purple-neon), #5e00b3);
            border: none;
            color: white;
            padding: 16px 28px;
            border-radius: 50px;
            font-weight: 700;
            font-size: 1.1rem;
            letter-spacing: 0.8px;
            cursor: pointer;
            width: 100%;
            transition: all 0.4s ease;
            box-shadow: 0 10px 25px rgba(187, 0, 255, 0.4);
            text-transform: uppercase;
            margin-top: 10px;
        }
        .btn:hover {
            background: linear-gradient(135deg, #d000ff, var(--purple-neon));
            box-shadow: 0 15px 35px rgba(187, 0, 255, 0.6);
            transform: translateY(-2px);
        }
        .btn:active {
            transform: scale(0.97);
        }

        .progress-bar {
            width: 100%;
            height: 10px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 10px;
            margin: 25px 0 15px;
            overflow: hidden;
            display: none;
        }
        .progress-fill {
            height: 100%;
            width: 0%;
            background: linear-gradient(to right, var(--purple-neon), var(--green-neon));
            border-radius: 10px;
            transition: width 0.5s ease;
        }

        .results-container {
            max-height: 350px;
            overflow-y: auto;
            padding-right: 5px;
            margin-top: 20px;
            display: none;
        }
        .result-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 14px;
            border-radius: 12px;
            margin-bottom: 8px;
            background: rgba(255,255,255,0.04);
            border-left: 5px solid transparent;
            transition: all 0.2s;
        }
        .result-item.found {
            border-left-color: var(--green-neon);
            background: rgba(0, 255, 136, 0.08);
            box-shadow: 0 0 15px rgba(0,255,136,0.15);
        }
        .result-item.not-found {
            border-left-color: var(--red-error);
            background: rgba(255, 77, 106, 0.06);
        }
        .result-path {
            font-family: monospace;
            font-weight: 600;
            color: #d0d0ff;
        }
        .result-status {
            padding: 4px 12px;
            border-radius: 20px;
            font-weight: 700;
            font-size: 0.8rem;
        }
        .status-found { background: #00ff8833; color: var(--green-neon); }
        .status-redirect { background: #ffaa0033; color: #ffaa00; }
        .status-notfound { background: #ff4d6a33; color: var(--red-error); }

        .empty-message {
            text-align: center;
            color: #888;
            padding: 20px;
        }

        .footer {
            text-align: center;
            margin-top: 30px;
            font-size: 0.85rem;
            color: #777;
        }
        .footer a {
            color: var(--purple-neon);
            text-decoration: none;
            font-weight: 700;
            transition: 0.3s;
        }
        .footer a:hover {
            color: var(--green-neon);
            text-shadow: 0 0 8px var(--green-neon);
        }
    </style>
</head>
<body>
    <div class="glass-card">
        <div class="logo-container">
            <svg class="logo-svg" viewBox="0 0 100 100">
                <defs>
                    <linearGradient id="targetGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stop-color="#00ff88"/>
                        <stop offset="100%" stop-color="#bb00ff"/>
                    </linearGradient>
                </defs>

                <!-- Outer circle -->
                <circle cx="50" cy="50" r="40"
                        stroke="url(#targetGrad)"
                        stroke-width="2"
                        fill="none"
                        opacity="0.6"/>

                <!-- Inner circle -->
                <circle cx="50" cy="50" r="20"
                        stroke="url(#targetGrad)"
                        stroke-width="2"
                        fill="none"
                        opacity="0.8"/>

                <!-- Crosshair lines -->
                <line x1="50" y1="15" x2="50" y2="35" stroke="url(#targetGrad)" stroke-width="2"/>
                <line x1="50" y1="65" x2="50" y2="85" stroke="url(#targetGrad)" stroke-width="2"/>
                <line x1="15" y1="50" x2="35" y2="50" stroke="url(#targetGrad)" stroke-width="2"/>
                <line x1="65" y1="50" x2="85" y2="50" stroke="url(#targetGrad)" stroke-width="2"/>

                <!-- Center dot -->
                <circle cx="50" cy="50" r="3" fill="#00ff88"/>

                <!-- Pulse animation -->
                <circle cx="50" cy="50" r="20"
                        stroke="#00ff88"
                        stroke-width="1"
                        fill="none"
                        opacity="0.4">
                    <animate attributeName="r" values="20;38;20" dur="2s" repeatCount="indefinite"/>
                    <animate attributeName="opacity" values="0.4;0;0.4" dur="2s" repeatCount="indefinite"/>
                </circle>
            </svg>
        </div>
        <h1>Admin Panel Finder</h1>
        <p class="subtitle">It's easy.</p>

        <div class="input-group">
            <label>Target URL</label>
            <input type="text" id="targetUrl" placeholder="https://example.com" value="">
        </div>
        <div class="input-group" style="display:flex; gap:15px;">
            <div style="flex:1;">
                <label>Timeout (sec)</label>
                <input type="number" id="timeout" value="5" min="1" max="20">
            </div>
            <div class="checkbox-group" style="flex:1; align-self:flex-end; margin-bottom:10px;">
                <input type="checkbox" id="followRedirects" checked>
                <label>Follow Redirects</label>
            </div>
        </div>
        <div class="checkbox-group">
            <input type="checkbox" id="smartDetection">
            <label>Smart Detection (check for login keywords – slower)</label>
        </div>
        <div class="input-group">
            <label>Admin Paths (one per line)</label>
            <textarea id="pathList">{{ default_paths }}</textarea>
        </div>

        <button class="btn" id="scanBtn">Start Scan</button>

        <div class="progress-bar" id="progressBar">
            <div class="progress-fill" id="progressFill"></div>
        </div>
        <div id="progressText" style="text-align:center; color:#aaa; margin-top:5px; display:none;"></div>

        <div class="results-container" id="resultsContainer"></div>
    </div>

    <div class="footer">
        Author: <a href="https://t.me/P0O1N0" target="_blank">P0O1N0</a>
    </div>

    <script>
        const scanBtn = document.getElementById('scanBtn');
        const progressBar = document.getElementById('progressBar');
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        const resultsContainer = document.getElementById('resultsContainer');

        scanBtn.addEventListener('click', async () => {
            const target = document.getElementById('targetUrl').value.trim();
            if (!target) return alert('Please enter a target URL.');
            const pathsRaw = document.getElementById('pathList').value;
            const paths = pathsRaw.split('\n').map(p => p.trim()).filter(p => p.length > 0);
            if (paths.length === 0) return alert('Provide at least one path.');

            const payload = {
                url: target,
                paths: paths,
                timeout: parseInt(document.getElementById('timeout').value) || 5,
                follow_redirects: document.getElementById('followRedirects').checked,
                smart_detection: document.getElementById('smartDetection').checked,
            };

            resultsContainer.innerHTML = '';
            resultsContainer.style.display = 'none';
            progressBar.style.display = 'block';
            progressText.style.display = 'block';
            progressFill.style.width = '0%';
            progressText.textContent = 'Starting scan…';
            scanBtn.disabled = true;
            scanBtn.textContent = 'Scanning…';

            try {
                const initRes = await fetch('/scan', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                if (!initRes.ok) throw new Error('Failed to start scan');
                const { scan_id } = await initRes.json();

                const poll = setInterval(async () => {
                    try {
                        const res = await fetch(`/result/${scan_id}`);
                        const data = await res.json();
                        const { done, total, results } = data;
                        const pct = total ? Math.round((done / total) * 100) : 0;
                        progressFill.style.width = `${pct}%`;
                        progressText.textContent = `Checked ${done} of ${total} paths (${pct}%)`;
                        renderResults(results);
                        if (data.status === 'done') {
                            clearInterval(poll);
                            progressText.textContent = `Scan complete – ${total} paths checked.`;
                            scanBtn.disabled = false;
                            scanBtn.textContent = 'Start Scan';
                        }
                    } catch (err) {
                        clearInterval(poll);
                        console.error(err);
                    }
                }, 600);
            } catch (err) {
                alert('Error: ' + err.message);
                scanBtn.disabled = false;
                scanBtn.textContent = 'Start Scan';
            }
        });

        function renderResults(results) {
            if (!results || results.length === 0) {
                resultsContainer.style.display = 'block';
                resultsContainer.innerHTML = '<div class="empty-message">No results yet.</div>';
                return;
            }
            resultsContainer.style.display = 'block';
            resultsContainer.innerHTML = results.map(r => {
                const statusClass = r.found ? 'found' : (r.status_code >= 300 && r.status_code < 400 ? 'redirect' : 'not-found');
                const statusText = r.found ? 'FOUND' : (r.status_code >= 300 && r.status_code < 400 ? 'REDIRECT' : 'NOT FOUND');
                const itemClass = r.found ? 'found' : 'not-found';
                const badgeClass = r.found ? 'status-found' : (r.status_code >= 300 && r.status_code < 400 ? 'status-redirect' : 'status-notfound');
                let extra = '';
                if (r.content_match) extra = ' login form detected';
                return `<div class="result-item ${itemClass}">
                    <span class="result-path">${escapeHtml(r.path)} → <strong>${r.url}</strong></span>
                    <span class="result-status ${badgeClass}">${statusText} (${r.status_code})${extra}</span>
                </div>`;
            }).join('');
        }

        function escapeHtml(text) {
            const map = {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'};
            return text.replace(/[&<>"']/g, m => map[m]);
        }
    </script>
</body>
</html>
"""

def check_path(session: requests.Session, base_url: str, path: str, timeout: int,
               follow_redirects: bool, smart: bool) -> dict:
    url = urljoin(base_url, path)
    result = {
        "path": path,
        "url": url,
        "status_code": None,
        "found": False,
        "content_match": False,
        "error": None
    }
    try:
        resp = session.get(url, timeout=timeout, allow_redirects=follow_redirects,
                           headers={"User-Agent": "Mozilla/5.0 (compatible; AdminFinder/1.0)"})
        result["status_code"] = resp.status_code
        if 200 <= resp.status_code < 300:
            result["found"] = True
            if smart:
                text = resp.text.lower()
                if any(keyword in text for keyword in ["password", "username", "login", "sign in"]):
                    result["content_match"] = True
        elif resp.status_code in (403, 401):
            result["found"] = True
    except requests.exceptions.Timeout:
        result["error"] = "timeout"
    except requests.exceptions.ConnectionError:
        result["error"] = "connection_error"
    except Exception as e:
        result["error"] = str(e)
    return result

def run_scan(scan_id: str, url: str, paths: list, timeout: int, follow_redirects: bool,
             smart_detection: bool) -> None:
    session = requests.Session()
    total = len(paths)
    results = []
    done = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(check_path, session, url, p, timeout,
                                   follow_redirects, smart_detection): p for p in paths}
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            done += 1
            scans[scan_id]["results"] = results[:]
            scans[scan_id]["progress"] = (done, total)

    scans[scan_id]["status"] = "done"
    scans[scan_id]["results"] = results

@app.route("/")
def index():
    try:
        with open(PATHS_FILE, 'r', encoding='utf-8') as f:
            paths_content = f.read()
    except:
        paths_content = ""
    return render_template_string(HTML_TEMPLATE, default_paths=paths_content)

@app.route("/scan", methods=["POST"])
def start_scan():
    data = request.get_json(force=True)
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "URL is required"}), 400
    paths = data.get("paths", [])
    if not paths:
        return jsonify({"error": "At least one path is required"}), 400
    timeout = int(data.get("timeout", SCAN_TIMEOUT))
    follow_redirects = bool(data.get("follow_redirects", True))
    smart = bool(data.get("smart_detection", False))

    scan_id = str(uuid.uuid4())
    scans[scan_id] = {
        "status": "running",
        "progress": (0, len(paths)),
        "results": []
    }

    thread = threading.Thread(target=run_scan, args=(scan_id, url, paths, timeout,
                                                     follow_redirects, smart))
    thread.daemon = True
    thread.start()

    return jsonify({"scan_id": scan_id, "message": "Scan started"})

@app.route("/result/<scan_id>")
def get_result(scan_id):
    job = scans.get(scan_id)
    if not job:
        return jsonify({"error": "Scan not found"}), 404
    done, total = job["progress"]
    return jsonify({
        "status": job["status"],
        "done": done,
        "total": total,
        "results": job["results"]
    })

if __name__ == "__main__":
    print("Admin Panel Finder — starting server…")
    threading.Timer(1.5, lambda: webbrowser.open(f"http://{HOST}:{PORT}")).start()
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)