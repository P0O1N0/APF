#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
   ╔══════════════════════════════════════════════════════════╗
   ║                Admin Panel Finder v2.0                   ║
   ║                    #Author: P0O1N0                       ║
   ║           Cyberpunk Intelligence Edition                 ║
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
        print(f"[+] Installing {lib} ...")
        install(lib)

import flask
import requests
from flask import Flask, request, jsonify, render_template_string

HOST = "127.0.0.1"
PORT = 5000
SCAN_TIMEOUT = 5
MAX_WORKERS = 20

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PATHS_FILE = os.path.join(SCRIPT_DIR, "PATHS_LIST.txt")

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
        except Exception as e:
            print(f"[!] Error reading {file_path}: {e}")
    return paths

ADMIN_PATHS = load_paths_from_file(PATHS_FILE)

# ------------------------------------------------------------------------------
# Flask Application & Global State
# ------------------------------------------------------------------------------
app = Flask(__name__)
scans: dict[str, dict] = {}

HTML_TEMPLATE = r'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>APF | Advanced Admin Panel Intelligence</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Inter:wght@300;400;500;600&family=Fira+Code:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #050508;
            --bg-panel: #0d0d14;
            --bg-card: rgba(18, 18, 28, 0.75);
            --border-color: rgba(0, 229, 255, 0.15);
            --cyber-cyan: #00e5ff;
            --cyber-blue: #0077ff;
            --cyber-purple: #b026ff;
            --text-bright: #ffffff;
            --text-normal: #c7c7d4;
            --text-muted: #8b8b9e;
            --success: #00ff88;
            --warning: #ffb800;
            --danger: #ff3366;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            background-color: var(--bg-dark);
            background-image: 
                linear-gradient(rgba(0, 229, 255, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 229, 255, 0.03) 1px, transparent 1px);
            background-size: 30px 30px;
            color: var(--text-normal);
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            overflow-x: hidden;
            display: flex;
            flex-direction: column;
        }

        h1, h2, h3, h4, h5, h6, .cyber-font {
            font-family: 'Rajdhani', sans-serif;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-bright);
        }

        /* Navbar & Logo */
        .navbar {
            background: rgba(5, 5, 8, 0.9) !important;
            backdrop-filter: blur(10px);
            border-bottom: 1px solid var(--border-color);
            padding: 1rem 0;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
        }
        .logo-container {
            display: flex;
            align-items: center;
            gap: 12px;
            text-decoration: none;
        }
        .logo-text {
            font-family: 'Rajdhani', sans-serif;
            font-weight: 700;
            font-size: 1.8rem;
            letter-spacing: 2px;
            background: linear-gradient(90deg, var(--text-bright), var(--cyber-cyan));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .version-badge {
            background: rgba(0, 229, 255, 0.1);
            color: var(--cyber-cyan);
            border: 1px solid var(--cyber-cyan);
            font-family: 'Fira Code', monospace;
            box-shadow: 0 0 10px rgba(0, 229, 255, 0.2);
        }

        /* Cyber Cards */
        .cyber-card {
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
            position: relative;
            overflow: hidden;
            transition: all 0.3s ease;
        }
        .cyber-card::before {
            content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 2px;
            background: linear-gradient(90deg, transparent, var(--border-color), transparent);
            transition: all 0.3s ease;
        }
        .cyber-card:hover {
            border-color: rgba(0, 229, 255, 0.35);
            box-shadow: 0 8px 32px rgba(0, 229, 255, 0.08);
            transform: translateY(-2px);
        }
        .cyber-card:hover::before {
            background: linear-gradient(90deg, transparent, var(--cyber-cyan), transparent);
        }

        /* Input Area */
        .input-label {
            color: var(--text-bright);
            font-size: 0.95rem;
            font-weight: 500;
            letter-spacing: 1px;
            margin-bottom: 10px;
            display: block;
        }
        .cyber-input-group {
            display: flex;
            background: var(--bg-panel);
            border: 1px solid rgba(0, 229, 255, 0.3);
            border-radius: 6px;
            padding: 6px;
            box-shadow: inset 0 0 15px rgba(0, 0, 0, 0.5), 0 0 15px rgba(0, 229, 255, 0.05);
            transition: all 0.3s;
        }
        .cyber-input-group:focus-within {
            border-color: var(--cyber-cyan);
            box-shadow: inset 0 0 15px rgba(0, 0, 0, 0.5), 0 0 20px rgba(0, 229, 255, 0.2);
        }
        .target-icon {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 0 15px;
            color: var(--cyber-cyan);
            font-size: 1.2rem;
        }
        .cyber-input-group input {
            background: transparent;
            border: none;
            color: var(--text-bright);
            padding: 12px 10px;
            font-size: 1.05rem;
            flex-grow: 1;
            outline: none;
            font-family: 'Fira Code', monospace;
        }
        .cyber-input-group input::placeholder {
            color: #636378;
        }
        .btn-cyber {
            background: linear-gradient(45deg, var(--cyber-blue), var(--cyber-cyan));
            border: none;
            color: #000;
            font-family: 'Rajdhani', sans-serif;
            font-weight: 700;
            font-size: 1.1rem;
            padding: 0 28px;
            border-radius: 4px;
            letter-spacing: 1px;
            cursor: pointer;
            transition: all 0.2s;
            text-transform: uppercase;
        }
        .btn-cyber:hover:not(:disabled) {
            box-shadow: 0 0 20px rgba(0, 229, 255, 0.6);
            transform: scale(1.02);
            color: #fff;
        }
        .btn-cyber:disabled {
            background: #2a2a35;
            color: #666;
            cursor: not-allowed;
        }

        /* Config Controls */
        .config-card {
            background: rgba(10, 10, 16, 0.6);
            border: 1px solid rgba(0, 229, 255, 0.1);
            border-radius: 6px;
            padding: 15px 20px;
            margin-top: 15px;
        }
        .cyber-label {
            font-family: 'Rajdhani', sans-serif;
            font-size: 0.9rem;
            letter-spacing: 1px;
            color: var(--text-muted);
            text-transform: uppercase;
            margin-bottom: 5px;
            display: block;
        }
        .cyber-input-sm {
            background: rgba(10, 10, 15, 0.85);
            border: 1px solid #2a2a35;
            color: var(--text-bright);
            border-radius: 4px;
            padding: 8px 12px;
            font-family: 'Fira Code', monospace;
            font-size: 0.9rem;
            width: 100%;
            transition: border-color 0.3s;
        }
        .cyber-input-sm:focus {
            border-color: var(--cyber-cyan);
            outline: none;
        }
        .cyber-checkbox-group {
            display: flex;
            align-items: center;
            gap: 10px;
            padding-top: 25px;
        }
        .cyber-checkbox-group input[type="checkbox"] {
            width: 18px;
            height: 18px;
            accent-color: var(--cyber-cyan);
            cursor: pointer;
        }
        .cyber-checkbox-group label {
            color: var(--text-bright);
            font-size: 0.9rem;
            cursor: pointer;
            margin-bottom: 0;
        }
        .cyber-textarea {
            background: rgba(8, 8, 12, 0.9);
            border: 1px solid #2a2a35;
            border-radius: 4px;
            color: #a0a0c0;
            font-family: 'Fira Code', monospace;
            font-size: 0.82rem;
            padding: 12px;
            width: 100%;
            height: 110px;
            resize: vertical;
            line-height: 1.5;
            outline: none;
            transition: border-color 0.3s;
        }
        .cyber-textarea:focus {
            border-color: var(--cyber-cyan);
            color: var(--text-bright);
        }

        /* Progress Panel */
        .progress-panel {
            background: var(--bg-panel);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 15px 20px;
            margin-top: 20px;
            display: none;
            animation: fadeIn 0.4s ease-out;
        }
        .progress-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .progress-status {
            color: var(--cyber-cyan);
            font-family: 'Fira Code', monospace;
            font-size: 0.9rem;
        }
        .progress-percent {
            color: var(--text-bright);
            font-weight: 700;
            font-family: 'Rajdhani', sans-serif;
            font-size: 1.2rem;
        }
        .cyber-progress-track {
            height: 6px;
            background: #1a1a24;
            border-radius: 3px;
            overflow: hidden;
            box-shadow: inset 0 1px 3px rgba(0,0,0,0.8);
        }
        .cyber-progress-fill {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, var(--cyber-purple), var(--cyber-cyan));
            box-shadow: 0 0 10px var(--cyber-cyan);
            transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
        }
        .cyber-progress-fill::after {
            content: '';
            position: absolute;
            top: 0; right: 0; bottom: 0; left: 0;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
            animation: shimmer 1.5s infinite;
        }
        @keyframes shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }

        /* Terminal Console */
        .terminal-container {
            background: #09090d;
            border: 1px solid #1f1f2e;
            border-radius: 6px;
            margin-top: 20px;
            box-shadow: inset 0 0 20px rgba(0,0,0,0.8);
        }
        .terminal-header {
            background: #111118;
            padding: 8px 15px;
            border-bottom: 1px solid #1f1f2e;
            display: flex;
            align-items: center;
            border-radius: 6px 6px 0 0;
        }
        .terminal-title {
            color: #636378;
            font-family: 'Fira Code', monospace;
            font-size: 0.8rem;
            margin-left: 10px;
        }
        .terminal-body {
            font-family: 'Fira Code', monospace;
            font-size: 0.85rem;
            padding: 15px;
            height: 200px;
            overflow-y: auto;
            color: var(--text-normal);
            line-height: 1.6;
        }

        /* Metrics & Telemetry Cards */
        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 18px 20px;
            text-align: center;
            transition: all 0.3s;
        }
        .stat-card:hover {
            border-color: rgba(0, 229, 255, 0.4);
            transform: translateY(-2px);
        }
        .stat-label {
            font-family: 'Rajdhani', sans-serif;
            text-transform: uppercase;
            font-size: 0.85rem;
            letter-spacing: 1px;
            color: var(--text-muted);
            margin-bottom: 6px;
        }
        .stat-value {
            font-family: 'Rajdhani', sans-serif;
            font-size: 2.2rem;
            font-weight: 700;
            color: var(--text-bright);
            line-height: 1;
        }

        /* Results Display */
        .filter-tabs {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }
        .tab-btn {
            background: rgba(18, 18, 28, 0.8);
            border: 1px solid rgba(0, 229, 255, 0.15);
            color: var(--text-normal);
            font-family: 'Rajdhani', sans-serif;
            font-weight: 600;
            font-size: 0.9rem;
            letter-spacing: 1px;
            padding: 6px 16px;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .tab-btn.active, .tab-btn:hover {
            background: rgba(0, 229, 255, 0.15);
            border-color: var(--cyber-cyan);
            color: var(--cyber-cyan);
            box-shadow: 0 0 10px rgba(0, 229, 255, 0.2);
        }
        .result-item {
            background: rgba(13, 13, 20, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 6px;
            padding: 12px 18px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 15px;
            transition: all 0.2s ease;
        }
        .result-item:hover {
            border-color: rgba(0, 229, 255, 0.3);
            background: rgba(18, 18, 28, 0.85);
            transform: translateX(3px);
        }
        .result-item.found {
            border-left: 4px solid var(--success);
            background: rgba(0, 255, 136, 0.03);
        }
        .result-item.redirect {
            border-left: 4px solid var(--warning);
            background: rgba(255, 184, 0, 0.03);
        }
        .result-item.forbidden {
            border-left: 4px solid var(--cyber-purple);
            background: rgba(176, 38, 255, 0.03);
        }
        .result-item.error {
            border-left: 4px solid var(--danger);
            background: rgba(255, 51, 102, 0.03);
        }
        .result-path {
            font-family: 'Fira Code', monospace;
            font-size: 0.95rem;
            color: var(--text-bright);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .status-badge {
            font-family: 'Fira Code', monospace;
            font-size: 0.8rem;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 4px;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            white-space: nowrap;
        }
        .status-badge.badge-success { background: rgba(0, 255, 136, 0.12); color: var(--success); border: 1px solid var(--success); }
        .status-badge.badge-warning { background: rgba(255, 184, 0, 0.12); color: var(--warning); border: 1px solid var(--warning); }
        .status-badge.badge-purple  { background: rgba(176, 38, 255, 0.12); color: var(--cyber-purple); border: 1px solid var(--cyber-purple); }
        .status-badge.badge-danger  { background: rgba(255, 51, 102, 0.12); color: var(--danger); border: 1px solid var(--danger); }
        .action-link {
            color: var(--cyber-cyan);
            text-decoration: none;
            padding: 6px 12px;
            border-radius: 4px;
            background: rgba(0, 229, 255, 0.08);
            border: 1px solid rgba(0, 229, 255, 0.2);
            font-size: 0.85rem;
            font-family: 'Fira Code', monospace;
            cursor: pointer;
            transition: all 0.2s;
        }
        .action-link:hover {
            background: var(--cyber-cyan);
            color: #000;
            box-shadow: 0 0 10px var(--cyber-cyan);
        }

        /* Animations & Utilities */
        @keyframes fadeIn { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
        .fade-in { animation: fadeIn 0.5s ease-out forwards; }
        .text-cyan { color: var(--cyber-cyan); }
        .text-purple { color: var(--cyber-purple); }

        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: var(--bg-dark); }
        ::-webkit-scrollbar-thumb { background: #2a2a35; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--cyber-cyan); }

        /* Footer */
        .cyber-footer {
            margin-top: auto;
            padding: 1.5rem 0 1rem;
            text-align: center;
            border-top: 1px solid rgba(0, 229, 255, 0.1);
        }
        .cyber-footer small {
            color: var(--text-muted);
            font-family: 'Fira Code', monospace;
            font-size: 0.8rem;
        }
        .cyber-footer a {
            color: var(--cyber-cyan);
            text-decoration: none;
            font-weight: 500;
            transition: all 0.2s;
        }
        .cyber-footer a:hover {
            text-shadow: 0 0 8px var(--cyber-cyan);
            text-decoration: underline;
        }
    </style>
</head>
<body>

<nav class="navbar sticky-top">
    <div class="container">
        <a class="logo-container" href="#">
            <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="url(#cyber-grad)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <defs>
                    <linearGradient id="cyber-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stop-color="#00e5ff" />
                        <stop offset="100%" stop-color="#b026ff" />
                    </linearGradient>
                </defs>
                <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                <polyline points="2 17 12 22 22 17"></polyline>
                <polyline points="2 12 12 17 22 12"></polyline>
            </svg>
            <span class="logo-text">APF // ADMIN FINDER</span>
        </a>
        <div>
            <span class="badge version-badge px-3 py-2 rounded-pill">v2.0_CORE</span>
        </div>
    </div>
</nav>

<div class="container mt-4 mb-5">
    <div class="row justify-content-center">
        <div class="col-lg-10">
            <div class="cyber-card p-4 p-md-5">
                <div>
                    <label class="input-label"><i class="fa-solid fa-satellite-dish me-2 text-cyan"></i>TARGET SPECIFICATION</label>
                    <div class="cyber-input-group">
                        <div class="target-icon">
                            <i class="fa-solid fa-crosshairs"></i>
                        </div>
                        <input type="text" id="targetUrl" placeholder="Enter target URL (e.g. https://target.com)" autocomplete="off">
                        <button class="btn-cyber" id="scanBtn">INITIATE SCAN</button>
                    </div>
                </div>

                <div class="config-card">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <span class="cyber-font text-cyan" style="font-size:0.95rem;"><i class="fa-solid fa-sliders me-2"></i>SCAN PARAMETERS & WORDLIST</span>
                        <a href="javascript:void(0)" id="toggleOptionsBtn" class="text-cyan text-decoration-none" style="font-family:'Fira Code',monospace; font-size:0.8rem;"><i class="fa-solid fa-chevron-up me-1"></i>Hide Options</a>
                    </div>
                    
                    <div id="optionsPanel">
                        <div class="row g-3">
                            <div class="col-md-3">
                                <label class="cyber-label">Timeout (sec)</label>
                                <input type="number" id="timeout" class="cyber-input-sm" value="5" min="1" max="30">
                            </div>
                            <div class="col-md-3">
                                <label class="cyber-label">Threads / Workers</label>
                                <input type="number" id="workers" class="cyber-input-sm" value="20" min="1" max="100">
                            </div>
                            <div class="col-md-3">
                                <div class="cyber-checkbox-group">
                                    <input type="checkbox" id="followRedirects" checked>
                                    <label for="followRedirects">Follow Redirects</label>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="cyber-checkbox-group">
                                    <input type="checkbox" id="smartDetection">
                                    <label for="smartDetection">Smart Auth Check</label>
                                </div>
                            </div>
                            <div class="col-12 mt-3">
                                <div class="d-flex justify-content-between align-items-center mb-1">
                                    <label class="cyber-label mb-0">Admin Paths (one per line)</label>
                                    <span id="pathCountBadge" class="text-muted" style="font-family:'Fira Code',monospace; font-size:0.75rem;">Loading paths...</span>
                                </div>
                                <textarea id="pathList" class="cyber-textarea" spellcheck="false">{{ default_paths }}</textarea>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="progress-panel" id="progressPanel">
                    <div class="progress-header">
                        <div class="progress-status" id="scanStatus"><i class="fa-solid fa-circle-notch fa-spin me-2"></i>Target locked. Launching scan thread...</div>
                        <div class="progress-percent" id="progressPercent">0%</div>
                    </div>
                    <div class="cyber-progress-track">
                        <div class="cyber-progress-fill" id="progressBar"></div>
                    </div>
                </div>

                <div class="terminal-container">
                    <div class="terminal-header">
                        <i class="fa-solid fa-terminal text-cyan" style="font-size: 0.8rem;"></i>
                        <span class="terminal-title">apf@system:~/scanner$</span>
                    </div>
                    <div class="terminal-body" id="logContainer">
                        <span style="color: #636378;">[SYS] Ready for target acquisition. Enter target URL and initiate scan...</span>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Telemetry & Metrics Area -->
    <div id="resultsArea" class="mt-4" style="display: none;">
        <div class="row justify-content-center">
            <div class="col-lg-10">
                <div class="row g-3 mb-4">
                    <div class="col-6 col-md-3">
                        <div class="stat-card">
                            <div class="stat-label"><i class="fa-solid fa-list-check me-1 text-cyan"></i>Total Paths</div>
                            <div class="stat-value text-cyan" id="metricTotal">0</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="stat-card">
                            <div class="stat-label"><i class="fa-solid fa-unlock me-1" style="color:var(--success)"></i>Panels Found</div>
                            <div class="stat-value" style="color:var(--success)" id="metricFound">0</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="stat-card">
                            <div class="stat-label"><i class="fa-solid fa-arrows-split-up-and-left me-1" style="color:var(--warning)"></i>Redirects</div>
                            <div class="stat-value" style="color:var(--warning)" id="metricRedirect">0</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="stat-card">
                            <div class="stat-label"><i class="fa-solid fa-shield-halved me-1 text-purple"></i>Protected 403</div>
                            <div class="stat-value text-purple" id="metricProtected">0</div>
                        </div>
                    </div>
                </div>

                <div class="cyber-card p-4">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h5 class="cyber-font mb-0"><i class="fa-solid fa-database me-2 text-cyan"></i>Discovered Admin Panels</h5>
                        <div class="filter-tabs mb-0">
                            <button class="tab-btn active" data-filter="all">All (<span id="countAll">0</span>)</button>
                            <button class="tab-btn" data-filter="found">Found (<span id="countFound">0</span>)</button>
                            <button class="tab-btn" data-filter="redirect">Redirect (<span id="countRedirect">0</span>)</button>
                            <button class="tab-btn" data-filter="protected">403/401 (<span id="countProtected">0</span>)</button>
                        </div>
                    </div>

                    <div id="resultsList" style="max-height: 480px; overflow-y: auto; padding-right: 5px;"></div>
                </div>
            </div>
        </div>
    </div>
</div>

<footer class="cyber-footer">
    <small>
        Author: <a href="https://t.me/P0O1N0" target="_blank" rel="noopener noreferrer">P0O1N0 <i class="fa-brands fa-telegram ms-1"></i></a>
    </small>
</footer>

<script>
    const targetUrlInput = document.getElementById('targetUrl');
    const scanBtn = document.getElementById('scanBtn');
    const pathList = document.getElementById('pathList');
    const pathCountBadge = document.getElementById('pathCountBadge');
    const toggleOptionsBtn = document.getElementById('toggleOptionsBtn');
    const optionsPanel = document.getElementById('optionsPanel');

    const progressPanel = document.getElementById('progressPanel');
    const progressBar = document.getElementById('progressBar');
    const progressPercent = document.getElementById('progressPercent');
    const scanStatus = document.getElementById('scanStatus');
    const logContainer = document.getElementById('logContainer');

    const resultsArea = document.getElementById('resultsArea');
    const resultsList = document.getElementById('resultsList');
    const metricTotal = document.getElementById('metricTotal');
    const metricFound = document.getElementById('metricFound');
    const metricRedirect = document.getElementById('metricRedirect');
    const metricProtected = document.getElementById('metricProtected');

    const countAll = document.getElementById('countAll');
    const countFound = document.getElementById('countFound');
    const countRedirect = document.getElementById('countRedirect');
    const countProtected = document.getElementById('countProtected');

    let allResults = [];
    let currentFilter = 'all';

    function updatePathCount() {
        const lines = pathList.value.split('\n').filter(l => l.trim() && !l.trim().startsWith('#'));
        pathCountBadge.textContent = `${lines.length} paths active`;
    }
    pathList.addEventListener('input', updatePathCount);
    updatePathCount();

    toggleOptionsBtn.addEventListener('click', () => {
        const isHidden = optionsPanel.style.display === 'none';
        optionsPanel.style.display = isHidden ? 'block' : 'none';
        toggleOptionsBtn.innerHTML = isHidden 
            ? '<i class="fa-solid fa-chevron-up me-1"></i>Hide Options' 
            : '<i class="fa-solid fa-chevron-down me-1"></i>Toggle Options';
    });

    function log(msg, level = 'info') {
        const line = document.createElement('div');
        let color = 'var(--text-normal)';
        let prefix = '[*]';
        if (level === 'error') { color = 'var(--danger)'; prefix = '[-]'; }
        else if (level === 'warning') { color = 'var(--warning)'; prefix = '[!]'; }
        else if (level === 'success') { color = 'var(--success)'; prefix = '[+]'; }
        else if (level === 'purple') { color = 'var(--cyber-purple)'; prefix = '[#]'; }

        line.style.color = color;
        const time = new Date().toLocaleTimeString('en-US', {hour12: false, hour: "numeric", minute: "numeric", second: "numeric"});
        line.innerHTML = `<span style="color:#636378">[${time}]</span> ${prefix} ${msg}`;
        logContainer.appendChild(line);
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    scanBtn.addEventListener('click', async () => {
        let url = targetUrlInput.value.trim();
        if (!url) {
            targetUrlInput.style.borderColor = 'var(--danger)';
            setTimeout(() => targetUrlInput.style.borderColor = '', 1000);
            return;
        }
        if (!url.startsWith('http://') && !url.startsWith('https://')) {
            url = 'http://' + url;
            targetUrlInput.value = url;
        }

        const paths = pathList.value.split('\n')
            .map(p => p.trim())
            .filter(p => p.length > 0 && !p.startsWith('#'));

        if (paths.length === 0) {
            alert('Please provide at least one admin path to scan.');
            return;
        }

        const payload = {
            url: url,
            paths: paths,
            timeout: parseInt(document.getElementById('timeout').value) || 5,
            workers: parseInt(document.getElementById('workers').value) || 20,
            follow_redirects: document.getElementById('followRedirects').checked,
            smart_detection: document.getElementById('smartDetection').checked
        };

        allResults = [];
        resultsList.innerHTML = '';
        resultsArea.style.display = 'none';
        logContainer.innerHTML = '<span style="color: #636378;">[SYS] Initializing reconnaissance matrix...</span>';

        progressPanel.style.display = 'block';
        progressBar.style.width = '0%';
        progressPercent.textContent = '0%';
        scanStatus.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin me-2"></i>Initiating probe against ${url}`;

        scanBtn.disabled = true;
        scanBtn.textContent = 'SCANNING...';

        log(`Target acquired: ${url}`, 'info');
        log(`Loaded ${paths.length} target vectors into worker pool (${payload.workers} threads)...`, 'info');

        try {
            const initRes = await fetch('/scan', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            if (!initRes.ok) throw new Error('Server returned error initiating scan');
            const { scan_id } = await initRes.json();

            let lastRenderCount = 0;
            const poll = setInterval(async () => {
                try {
                    const res = await fetch(`/result/${scan_id}`);
                    const data = await res.json();
                    const { done, total, results, status } = data;
                    allResults = results || [];

                    const pct = total ? Math.round((done / total) * 100) : 0;
                    progressBar.style.width = `${pct}%`;
                    progressPercent.textContent = `${pct}%`;
                    scanStatus.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin me-2"></i>Processed ${done} of ${total} paths (${pct}%)`;

                    // Output new discoveries to terminal log
                    if (allResults.length > lastRenderCount) {
                        for (let i = lastRenderCount; i < allResults.length; i++) {
                            const r = allResults[i];
                            if (r.found) {
                                if (r.status_code === 200) {
                                    log(`FOUND: ${r.path} [${r.status_code}]${r.content_match ? ' [LOGIN KEYWORD]' : ''}`, 'success');
                                } else if (r.status_code === 403 || r.status_code === 401) {
                                    log(`PROTECTED: ${r.path} [${r.status_code}]`, 'purple');
                                }
                            } else if (r.status_code >= 300 && r.status_code < 400) {
                                log(`REDIRECT: ${r.path} -> [${r.status_code}]`, 'warning');
                            }
                        }
                        lastRenderCount = allResults.length;
                    }

                    renderMetrics();
                    renderResultsList();

                    if (status === 'done') {
                        clearInterval(poll);
                        scanStatus.innerHTML = `<i class="fa-solid fa-check text-success me-2"></i>Scan Sequence Finished (${total} checks completed)`;
                        log(`Scan sequence completed. Processed ${total} paths.`, 'success');
                        scanBtn.disabled = false;
                        scanBtn.textContent = 'INITIATE SCAN';
                    }
                } catch (err) {
                    clearInterval(poll);
                    log(`Polling connection severed: ${err.message}`, 'error');
                    scanBtn.disabled = false;
                    scanBtn.textContent = 'INITIATE SCAN';
                }
            }, 500);

        } catch (err) {
            log(`Initialization failed: ${err.message}`, 'error');
            scanBtn.disabled = false;
            scanBtn.textContent = 'INITIATE SCAN';
        }
    });

    function renderMetrics() {
        const found = allResults.filter(r => r.status_code === 200).length;
        const redirect = allResults.filter(r => r.status_code >= 300 && r.status_code < 400).length;
        const protectedCount = allResults.filter(r => r.status_code === 403 || r.status_code === 401).length;

        metricTotal.textContent = allResults.length;
        metricFound.textContent = found;
        metricRedirect.textContent = redirect;
        metricProtected.textContent = protectedCount;

        countAll.textContent = allResults.length;
        countFound.textContent = found;
        countRedirect.textContent = redirect;
        countProtected.textContent = protectedCount;

        if (allResults.length > 0) {
            resultsArea.style.display = 'block';
        }
    }

    function renderResultsList() {
        let filtered = allResults;
        if (currentFilter === 'found') {
            filtered = allResults.filter(r => r.status_code === 200);
        } else if (currentFilter === 'redirect') {
            filtered = allResults.filter(r => r.status_code >= 300 && r.status_code < 400);
        } else if (currentFilter === 'protected') {
            filtered = allResults.filter(r => r.status_code === 403 || r.status_code === 401);
        }

        if (filtered.length === 0) {
            resultsList.innerHTML = `<div class="text-center py-4 text-muted" style="font-family:'Fira Code',monospace;"><i class="fa-solid fa-ghost me-2"></i>No endpoints match this category yet.</div>`;
            return;
        }

        resultsList.innerHTML = filtered.map(r => {
            let itemClass = 'error';
            let badgeClass = 'badge-danger';
            let statusLabel = r.status_code ? `${r.status_code} OK` : 'ERR';

            if (r.status_code === 200) {
                itemClass = 'found';
                badgeClass = 'badge-success';
                statusLabel = '200 FOUND';
            } else if (r.status_code >= 300 && r.status_code < 400) {
                itemClass = 'redirect';
                badgeClass = 'badge-warning';
                statusLabel = `${r.status_code} REDIRECT`;
            } else if (r.status_code === 403 || r.status_code === 401) {
                itemClass = 'forbidden';
                badgeClass = 'badge-purple';
                statusLabel = `${r.status_code} FORBIDDEN`;
            }

            return `
                <div class="result-item ${itemClass}">
                    <div style="min-width:0; flex-grow:1;">
                        <div class="d-flex align-items-center gap-2 mb-1">
                            <span class="status-badge ${badgeClass}">${statusLabel}</span>
                            ${r.content_match ? '<span class="status-badge badge-success"><i class="fa-solid fa-key me-1"></i>Login Form</span>' : ''}
                        </div>
                        <div class="result-path" title="${r.full_url}">${r.path} <span style="color:#636378; font-size:0.8rem;">(${r.full_url})</span></div>
                    </div>
                    <div class="d-flex gap-2">
                        <button class="action-link" onclick="copyUrl('${r.full_url}')"><i class="fa-regular fa-copy me-1"></i>Copy</button>
                        <a href="${r.full_url}" target="_blank" rel="noopener noreferrer" class="action-link"><i class="fa-solid fa-arrow-up-right-from-square me-1"></i>Open</a>
                    </div>
                </div>
            `;
        }).join('');
    }

    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.getAttribute('data-filter');
            renderResultsList();
        });
    });

    window.copyUrl = (url) => {
        navigator.clipboard.writeText(url).then(() => {
            alert(`Copied to clipboard: ${url}`);
        }).catch(() => {
            prompt('Copy URL:', url);
        });
    };
</script>
</body>
</html>
'''

# ------------------------------------------------------------------------------
# Scan Engine
# ------------------------------------------------------------------------------
def check_single_path(base_url: str, path: str, timeout: int, follow_redirects: bool, smart_detect: bool) -> dict:
    url = urljoin(base_url, path)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    result = {
        "path": path,
        "full_url": url,
        "status_code": None,
        "found": False,
        "redirect_to": None,
        "content_match": False,
        "error": None
    }

    try:
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=follow_redirects, verify=False)
        result["status_code"] = resp.status_code

        if resp.history:
            result["redirect_to"] = resp.url

        if resp.status_code == 200:
            result["found"] = True
            if smart_detect:
                text = resp.text.lower()
                login_keywords = ["username", "password", "login", "admin", "sign in", "auth", "dashboard"]
                if any(kw in text for kw in login_keywords):
                    result["content_match"] = True
        elif resp.status_code in [401, 403]:
            result["found"] = True
        elif 300 <= resp.status_code < 400:
            result["found"] = False

    except requests.RequestException as exc:
        result["error"] = str(exc)

    return result

def run_scan_worker(scan_id: str, base_url: str, paths: list, timeout: int, workers: int, follow_redirects: bool, smart_detect: bool):
    scans[scan_id]["total"] = len(paths)
    scans[scan_id]["status"] = "running"

    with ThreadPoolExecutor(max_workers=min(workers, 50)) as executor:
        future_map = {
            executor.submit(check_single_path, base_url, p, timeout, follow_redirects, smart_detect): p
            for p in paths
        }

        for future in as_completed(future_map):
            res = future.result()
            scans[scan_id]["done"] += 1
            if res["status_code"] or res["error"]:
                scans[scan_id]["results"].append(res)

    scans[scan_id]["status"] = "done"

# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------
@app.route("/")
def index():
    default_paths_str = "\n".join(ADMIN_PATHS[:100]) if ADMIN_PATHS else "admin/\nadmin/login.php\nadministrator/\ncpanel/"
    return render_template_string(HTML_TEMPLATE, default_paths=default_paths_str)

@app.route("/scan", methods=["POST"])
def start_scan():
    data = request.get_json(force=True)
    target = data.get("url", "").strip()
    paths = data.get("paths", [])
    timeout = int(data.get("timeout", SCAN_TIMEOUT))
    workers = int(data.get("workers", MAX_WORKERS))
    follow_redirects = bool(data.get("follow_redirects", True))
    smart_detect = bool(data.get("smart_detection", False))

    if not target or not paths:
        return jsonify({"error": "Target URL and paths are required"}), 400

    if not urlparse(target).scheme:
        target = "http://" + target

    scan_id = str(uuid.uuid4())
    scans[scan_id] = {
        "status": "pending",
        "total": len(paths),
        "done": 0,
        "results": []
    }

    t = threading.Thread(
        target=run_scan_worker,
        args=(scan_id, target, paths, timeout, workers, follow_redirects, smart_detect),
        daemon=True
    )
    t.start()

    return jsonify({"scan_id": scan_id})

@app.route("/result/<scan_id>")
def get_result(scan_id):
    scan = scans.get(scan_id)
    if not scan:
        return jsonify({"error": "Scan not found"}), 404
    return jsonify(scan)

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()

    import argparse
    parser = argparse.ArgumentParser(description="APF - Admin Panel Finder")
    parser.add_argument("--port", type=int, default=PORT, help="Port to run web UI on")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically launch browser")
    args = parser.parse_args()

    port = args.port

    print(f"\n==================================================")
    print(f"       APF // ADMIN PANEL FINDER v2.0            ")
    print(f"       Cyberpunk Intelligence Dashboard           ")
    print(f"==================================================")
    print(f"[+] Initializing server on http://{HOST}:{port}")
    print(f"[+] Active dictionary: {len(ADMIN_PATHS)} default admin paths")
    
    if not args.no_browser:
        threading.Timer(1.2, lambda: webbrowser.open(f"http://{HOST}:{port}")).start()

    app.run(host=HOST, port=port, debug=False)
