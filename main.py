#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Entry Point for Binance P2P VIP Radar
High-Frequency In-Memory Cache Web Dashboard (port 8000) + Telegram Bot & Multi-Worker Scanner
"""

import os
import sys
import json
import time
import requests
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import binance_p2p_telebot

PORT = int(os.getenv("PORT", "8000"))

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Binance P2P Radar • Real-Time High Frequency Monitor</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #12151a; }
        ::-webkit-scrollbar-thumb { background: #2b313a; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #3c4450; }
        
        @keyframes pulse-ring {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(74, 222, 128, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(74, 222, 128, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(74, 222, 128, 0); }
        }
        .pulse-live { animation: pulse-ring 1.8s infinite; }
        
        @keyframes flash-green {
            0% { background-color: rgba(34, 197, 94, 0.35); }
            100% { background-color: transparent; }
        }
        .row-flash-green { animation: flash-green 1.2s ease-out; }
        
        @keyframes flash-red {
            0% { background-color: rgba(239, 68, 68, 0.35); }
            100% { background-color: transparent; }
        }
        .row-flash-red { animation: flash-red 1.2s ease-out; }

        @keyframes scan-line {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }
        .scan-line { animation: scan-line 2s cubic-bezier(0.4, 0, 0.2, 1) infinite; }
    </style>
</head>
<body class="bg-[#0b0e11] text-gray-100 min-h-screen">
    <!-- Navbar -->
    <header class="border-b border-[#1e2329] bg-[#181a20]/95 px-4 sm:px-8 py-3.5 flex flex-wrap items-center justify-between gap-4 sticky top-0 z-50 backdrop-blur">
        <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-yellow-400 to-amber-600 flex items-center justify-center text-black font-black text-lg shadow-lg shadow-yellow-400/20">
                ⚡
            </div>
            <div>
                <div class="flex items-center gap-2">
                    <h1 class="text-base sm:text-lg font-bold text-yellow-400 leading-tight">Binance P2P Radar</h1>
                    <span class="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-yellow-400/10 text-yellow-400 border border-yellow-400/30">Ultra Realtime</span>
                </div>
                <p class="text-xs text-gray-400 flex items-center gap-2 mt-0.5">
                    <span>Cổng chuyên dụng P2P</span> • <span class="text-green-400 font-mono" id="scan-rate-badge">1.0s/vòng</span>
                </p>
            </div>
        </div>

        <div class="flex items-center gap-2 sm:gap-3 flex-wrap">
            <!-- Server Log Button -->
            <button onclick="toggleLogsModal()" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#2b313a] text-gray-300 hover:text-white transition-all flex items-center gap-1.5 border border-[#363d47]">
                📋 Log Server
            </button>

            <!-- Audio toggle -->
            <button onclick="toggleAudio()" id="btn-audio" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#2b313a] text-gray-300 hover:text-white transition-all flex items-center gap-1.5">
                🔕 Âm Báo: <b>TẮT</b>
            </button>

            <!-- Live badge with pulse -->
            <span class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold bg-green-500/10 text-green-400 border border-green-500/20">
                <span class="w-2.5 h-2.5 rounded-full bg-green-400 pulse-live"></span>
                <span id="live-indicator-text">Realtime 1s</span>
            </span>

            <a href="https://t.me/testbinancenotibot" target="_blank" class="bg-yellow-400 hover:bg-yellow-500 text-black font-bold text-xs px-3.5 py-1.5 rounded-lg transition-all flex items-center gap-1.5 shadow-md shadow-yellow-400/20">
                <span>✈️</span> Telegram Bot
            </a>
        </div>
    </header>

    <!-- Scanner Progress Bar -->
    <div class="w-full h-1 bg-[#181a20] overflow-hidden relative">
        <div class="w-1/3 h-full bg-gradient-to-r from-transparent via-yellow-400 to-transparent scan-line absolute"></div>
    </div>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
        <!-- Toast Notification Area -->
        <div id="toast-container" class="fixed top-20 right-4 z-50 space-y-2 pointer-events-none max-w-sm w-full"></div>

        <!-- Stats Cards -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            <div class="bg-[#181a20] border border-[#2b313a] rounded-xl p-4 sm:p-5 relative overflow-hidden">
                <p class="text-xs text-gray-400 font-medium uppercase tracking-wider">Cặp Giao Dịch</p>
                <p class="text-xl sm:text-2xl font-bold text-white mt-1">USDT / VND</p>
                <div class="flex items-center gap-1.5 mt-1">
                    <span class="w-1.5 h-1.5 rounded-full bg-green-400"></span>
                    <p class="text-xs text-green-400/90 font-medium">Nạp P2P (Mua USDT)</p>
                </div>
            </div>

            <div class="bg-[#181a20] border border-[#2b313a] rounded-xl p-4 sm:p-5 relative overflow-hidden">
                <p class="text-xs text-gray-400 font-medium uppercase tracking-wider">Tốc Độ Quét Sàn</p>
                <p class="text-xl sm:text-2xl font-bold text-green-400 mt-1 font-mono" id="scan-cost">~1.0s</p>
                <p class="text-xs text-gray-400 mt-1">Quét sạch 24 trang song song</p>
            </div>

            <div class="bg-[#181a20] border border-[#2b313a] rounded-xl p-4 sm:p-5 relative overflow-hidden">
                <p class="text-xs text-gray-400 font-medium uppercase tracking-wider">Người Bán Online</p>
                <p class="text-xl sm:text-2xl font-bold text-blue-400 mt-1 font-mono" id="sellers-count">Đang tải...</p>
                <p class="text-xs text-gray-400 mt-1"><span id="total-ads-count">450+</span> quảng cáo toàn sàn</p>
            </div>

            <div class="bg-[#181a20] border border-[#2b313a] rounded-xl p-4 sm:p-5 relative overflow-hidden">
                <p class="text-xs text-gray-400 font-medium uppercase tracking-wider">Cảnh Báo Phát Ra</p>
                <p class="text-xl sm:text-2xl font-bold text-yellow-400 mt-1 font-mono" id="alerts-count">0</p>
                <p class="text-xs text-gray-400 mt-1">Push tức thì &lt; 1s tới Tele</p>
            </div>
        </div>

        <!-- Toolbar: Search & Filter Tabs -->
        <div class="bg-[#181a20] border border-[#2b313a] rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
            <!-- Search input -->
            <div class="relative flex-1 min-w-[240px]">
                <span class="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400 text-sm">🔍</span>
                <input type="text" id="search-input" placeholder="Tìm theo tên (VD: King, GDNhanh, AutoPay...)" 
                    class="w-full bg-[#12151a] border border-[#2b313a] rounded-lg pl-9 pr-4 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-yellow-400 transition-colors">
            </div>

            <!-- Filter Buttons -->
            <div class="flex items-center gap-2 flex-wrap">
                <button onclick="setFilter('all')" id="btn-filter-all" class="px-3.5 py-1.5 text-xs font-bold rounded-lg bg-yellow-400 text-black transition-all">
                    Tất Cả (<span id="count-all">0</span>)
                </button>
                <button onclick="setFilter('recent')" id="btn-filter-recent" class="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-[#2b313a] text-gray-300 hover:text-white transition-all flex items-center gap-1.5">
                    <span>⚡ Mới Vào</span> (<span id="count-recent">0</span>)
                </button>
                <button onclick="setFilter('top20')" id="btn-filter-top20" class="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-[#2b313a] text-gray-300 hover:text-white transition-all">
                    Top 20 Rẻ Nhất
                </button>
                <button onclick="setFilter('merchant')" id="btn-filter-merchant" class="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-[#2b313a] text-gray-300 hover:text-white transition-all flex items-center gap-1">
                    🏅 Tích Vàng (<span id="count-merchant">0</span>)
                </button>
                <button onclick="refreshData()" title="Làm mới ngay" class="p-2 rounded-lg bg-[#2b313a] hover:bg-[#363d47] text-gray-300 hover:text-white transition-all active:scale-95">
                    🔄
                </button>
            </div>
        </div>

        <!-- Sellers Table -->
        <div class="bg-[#181a20] border border-[#2b313a] rounded-xl overflow-hidden shadow-2xl">
            <div class="px-6 py-4 border-b border-[#2b313a] flex flex-wrap items-center justify-between gap-2">
                <div class="flex items-center gap-2.5">
                    <span class="text-yellow-400 font-bold">📋</span>
                    <h2 class="font-bold text-sm sm:text-base text-white">Sổ Lệnh P2P Toàn Thị Trường</h2>
                    <span class="text-xs bg-[#2b313a] text-gray-300 px-2.5 py-0.5 rounded-full font-medium font-mono" id="display-count">0 sellers</span>
                </div>
                <div class="flex items-center gap-3 text-xs text-gray-400">
                    <span class="flex items-center gap-1.5">
                        <span class="w-1.5 h-1.5 rounded-full bg-green-400 animate-ping"></span>
                        <span id="last-update" class="font-mono">Đang kết nối...</span>
                    </span>
                    <span class="text-gray-600">•</span>
                    <span class="text-gray-400 font-mono" id="latency-badge">RAM 1ms</span>
                </div>
            </div>
            <div class="overflow-x-auto max-h-[700px]">
                <table class="w-full text-left text-sm">
                    <thead class="bg-[#1e2329] text-gray-400 text-xs uppercase font-semibold sticky top-0 z-10">
                        <tr>
                            <th class="px-6 py-3.5">Hạng / Người Bán</th>
                            <th class="px-6 py-3.5">Đơn Giá (VND)</th>
                            <th class="px-6 py-3.5">Khả Dụng</th>
                            <th class="px-6 py-3.5">Hạn Mức Đơn (VND)</th>
                            <th class="px-6 py-3.5">Độ Uy Tín</th>
                            <th class="px-6 py-3.5">Trang</th>
                            <th class="px-6 py-3.5 text-right">Thao Tác</th>
                        </tr>
                    </thead>
                    <tbody id="sellers-table-body" class="divide-y divide-[#2b313a] text-gray-200">
                        <tr>
                            <td colspan="7" class="px-6 py-16 text-center text-gray-400">
                                <div class="flex flex-col items-center justify-center gap-3">
                                    <div class="w-7 h-7 border-2 border-yellow-400 border-t-transparent rounded-full animate-spin"></div>
                                    <span class="text-sm font-medium">Đang đồng bộ dữ liệu siêu tốc từ Binance...</span>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </main>

    <!-- Server Logs Modal -->
    <div id="logs-modal" class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm hidden flex items-center justify-center p-4">
        <div class="bg-[#181a20] border border-[#2b313a] rounded-2xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div class="px-6 py-4 border-b border-[#2b313a] flex items-center justify-between bg-[#1f242c]">
                <div class="flex items-center gap-2">
                    <span class="text-green-400 font-mono text-base">●</span>
                    <h3 class="font-bold text-white text-sm sm:text-base">Nhật Ký Máy Chủ (Server Live Logs)</h3>
                    <span class="text-xs bg-[#2b313a] text-gray-400 px-2 py-0.5 rounded font-mono">/api/logs</span>
                </div>
                <div class="flex items-center gap-2">
                    <button onclick="fetchServerLogs()" class="px-2.5 py-1 rounded-lg bg-[#2b313a] hover:bg-[#363d47] text-gray-300 hover:text-white text-xs font-semibold flex items-center gap-1">
                        🔄 Cập nhật
                    </button>
                    <button onclick="toggleLogsModal()" class="p-1 rounded-lg bg-[#2b313a] hover:bg-red-500/20 hover:text-red-400 text-gray-400 text-base">
                        ✕
                    </button>
                </div>
            </div>
            <pre class="p-4 flex-1 overflow-y-auto font-mono text-xs text-gray-300 bg-[#0d1015] select-text leading-relaxed whitespace-pre-wrap" id="logs-content">Đang tải log...</pre>
            <div class="px-6 py-3 border-t border-[#2b313a] bg-[#181a20] flex items-center justify-between text-xs text-gray-500">
                <span>Tự động làm mới mỗi 3s khi mở modal</span>
                <button onclick="copyLogs()" class="hover:text-yellow-400 transition-colors font-medium">
                    📋 Sao chép log
                </button>
            </div>
        </div>
    </div>

    <footer class="border-t border-[#1e2329] text-center text-xs text-gray-500 py-6">
        Binance P2P VIP Radar Monitor System • In-Memory Zero-Latency Cache Engine
    </footer>

    <script>
        let allSellers = [];
        let recentNewSellers = [];
        let currentFilter = 'all';
        let prevPrices = {};
        let knownNicks = new Set();
        let isFirstLoad = true;
        let audioEnabled = localStorage.getItem('radar_audio') === 'true';
        let logsModalOpen = false;
        let logsInterval = null;

        // Logs modal handler
        function toggleLogsModal() {
            const modal = document.getElementById('logs-modal');
            logsModalOpen = !logsModalOpen;
            if (logsModalOpen) {
                modal.classList.remove('hidden');
                fetchServerLogs();
                logsInterval = setInterval(fetchServerLogs, 3000);
            } else {
                modal.classList.add('hidden');
                clearInterval(logsInterval);
            }
        }

        async function fetchServerLogs() {
            try {
                const res = await fetch('/api/logs');
                const text = await res.text();
                const pre = document.getElementById('logs-content');
                pre.innerText = text;
                pre.scrollTop = pre.scrollHeight;
            } catch (err) {
                document.getElementById('logs-content').innerText = "Lỗi khi lấy log: " + err;
            }
        }

        function copyLogs() {
            const text = document.getElementById('logs-content').innerText;
            navigator.clipboard.writeText(text).then(() => {
                alert('Đã sao chép log vào clipboard!');
            });
        }

        // Web Audio API notification sound
        function playAlertChime() {
            if (!audioEnabled) return;
            try {
                const AudioContext = window.AudioContext || window.webkitAudioContext;
                if (!AudioContext) return;
                const ctx = new AudioContext();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);
                
                osc.type = 'sine';
                osc.frequency.setValueAtTime(784, ctx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(1175, ctx.currentTime + 0.12);
                
                gain.gain.setValueAtTime(0.2, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
                
                osc.start();
                osc.stop(ctx.currentTime + 0.25);
            } catch (e) {}
        }

        function toggleAudio() {
            audioEnabled = !audioEnabled;
            localStorage.setItem('radar_audio', audioEnabled);
            updateAudioBtn();
            if (audioEnabled) playAlertChime();
        }

        function updateAudioBtn() {
            const btn = document.getElementById('btn-audio');
            if (!btn) return;
            if (audioEnabled) {
                btn.innerHTML = '🔔 Âm Báo: <b>BẬT</b>';
                btn.className = "px-3 py-1.5 rounded-lg text-xs font-semibold bg-green-500/20 text-green-300 border border-green-500/30 transition-all flex items-center gap-1.5";
            } else {
                btn.innerHTML = '🔕 Âm Báo: <b>TẮT</b>';
                btn.className = "px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#2b313a] text-gray-400 hover:text-gray-200 transition-all flex items-center gap-1.5";
            }
        }
        updateAudioBtn();

        function showToast(title, body) {
            const container = document.getElementById('toast-container');
            if (!container) return;
            const toast = document.createElement('div');
            toast.className = "bg-[#1f242c] border border-yellow-400/40 rounded-xl p-3.5 shadow-2xl text-white transform transition-all duration-300 translate-y-2 opacity-0 pointer-events-auto flex items-start gap-3";
            toast.innerHTML = `
                <div class="text-yellow-400 text-lg">⚡</div>
                <div class="flex-1 min-w-0">
                    <p class="text-xs font-bold text-yellow-400">${title}</p>
                    <p class="text-xs text-gray-200 mt-0.5 truncate">${body}</p>
                </div>
            `;
            container.appendChild(toast);
            requestAnimationFrame(() => {
                toast.classList.remove('translate-y-2', 'opacity-0');
            });
            setTimeout(() => {
                toast.classList.add('opacity-0', '-translate-y-2');
                setTimeout(() => toast.remove(), 300);
            }, 4000);
        }

        function setFilter(f) {
            currentFilter = f;
            ['all', 'recent', 'top20', 'merchant'].forEach(name => {
                const btn = document.getElementById('btn-filter-' + name);
                if (btn) {
                    if (name === f) {
                        btn.className = "px-3.5 py-1.5 text-xs font-bold rounded-lg bg-yellow-400 text-black transition-all";
                    } else {
                        btn.className = "px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-[#2b313a] text-gray-300 hover:text-white transition-all";
                    }
                }
            });
            renderTable();
        }

        document.getElementById('search-input').addEventListener('input', renderTable);

        function renderTable() {
            const query = (document.getElementById('search-input').value || '').trim().toLowerCase();
            let filtered = allSellers.filter(s => {
                const nick = (s.nickName || '').toLowerCase();
                return nick.includes(query);
            });

            if (currentFilter === 'top20') {
                filtered = filtered.slice(0, 20);
            } else if (currentFilter === 'merchant') {
                filtered = filtered.filter(s => s.userType === 'merchant');
            } else if (currentFilter === 'recent') {
                const recentSet = new Set(recentNewSellers.map(r => r.nickName));
                filtered = filtered.filter(s => recentSet.has(s.nickName));
            }

            document.getElementById('display-count').innerText = `${filtered.length} người bán`;

            const tbody = document.getElementById('sellers-table-body');
            if (filtered.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" class="px-6 py-12 text-center text-gray-400">Không tìm thấy người bán nào phù hợp bộ lọc.</td></tr>`;
                return;
            }

            const recentNickMap = {};
            recentNewSellers.forEach(r => {
                recentNickMap[r.nickName] = r.discovered_str;
            });

            tbody.innerHTML = filtered.map((s, idx) => {
                const rankBadge = idx === 0 ? '<span class="text-base">🥇</span>' :
                                  idx === 1 ? '<span class="text-base">🥈</span>' :
                                  idx === 2 ? '<span class="text-base">🥉</span>' :
                                  `<span class="text-xs px-2 py-0.5 rounded bg-gray-800 text-gray-400 font-mono">#${idx + 1}</span>`;

                const merchantBadge = s.userType === 'merchant' ? 
                    '<span class="px-1.5 py-0.5 text-[10px] font-bold rounded bg-yellow-400/10 text-yellow-400 border border-yellow-400/30">TÍCH VÀNG 🏅</span>' : 
                    '<span class="text-xs text-gray-500">Thường</span>';

                const isNewRecent = recentNickMap[s.nickName];
                const newBadge = isNewRecent ? 
                    `<span class="px-1.5 py-0.5 text-[10px] font-bold rounded bg-green-500/20 text-green-300 border border-green-500/30 animate-pulse">⚡ MỚI (${isNewRecent})</span>` : '';

                // Price change highlight
                const curPrice = parseFloat(s.price) || 0;
                const oldPrice = prevPrices[s.nickName];
                let priceDirectionClass = '';
                let priceIcon = '';
                if (oldPrice !== undefined && curPrice !== oldPrice) {
                    if (curPrice < oldPrice) {
                        priceDirectionClass = 'row-flash-green';
                        priceIcon = ' <span class="text-xs text-green-300">↓</span>';
                    } else {
                        priceDirectionClass = 'row-flash-red';
                        priceIcon = ' <span class="text-xs text-red-400">↑</span>';
                    }
                }

                return `
                    <tr class="hover:bg-[#1e2329]/60 transition-colors ${priceDirectionClass}">
                        <td class="px-6 py-3.5 font-semibold text-white flex items-center gap-2.5">
                            ${rankBadge}
                            <div>
                                <div class="font-bold text-gray-100 flex items-center gap-2">
                                    <span>${s.nickName}</span>
                                    ${newBadge}
                                </div>
                                <div class="mt-0.5">${merchantBadge}</div>
                            </div>
                        </td>
                        <td class="px-6 py-3.5 text-green-400 font-bold text-base whitespace-nowrap">
                            ${Number(s.price).toLocaleString()} ${priceIcon} <span class="text-xs text-gray-400 font-normal">VND</span>
                        </td>
                        <td class="px-6 py-3.5 font-medium whitespace-nowrap font-mono">
                            ${Number(s.surplusAmount).toLocaleString(undefined, {minimumFractionDigits: 2})} <span class="text-xs text-gray-400 font-sans">USDT</span>
                        </td>
                        <td class="px-6 py-3.5 text-gray-300 text-xs whitespace-nowrap font-mono">
                            ${Number(s.minAmount).toLocaleString()} ~ ${Number(s.maxAmount).toLocaleString()} đ
                        </td>
                        <td class="px-6 py-3.5 text-xs whitespace-nowrap">
                            <span class="text-yellow-400 font-bold">${(Number(s.monthFinishRate || 0) * 100).toFixed(1)}%</span>
                            <span class="text-gray-400 block text-[11px]">(${Number(s.monthOrderCount || 0).toLocaleString()} đơn)</span>
                        </td>
                        <td class="px-6 py-3.5 text-xs text-gray-400 whitespace-nowrap">
                            Trang ${s.page || 1}
                        </td>
                        <td class="px-6 py-3.5 text-right whitespace-nowrap">
                            <a href="https://p2p.binance.com/vi/trade/all-payments/USDT?fiat=VND" target="_blank" 
                               class="text-xs bg-[#2b313a] hover:bg-yellow-400 hover:text-black text-white px-3 py-1.5 rounded-lg transition-all font-semibold">
                                Khớp Lệnh ⚡
                            </a>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        async function refreshData() {
            const t0 = performance.now();
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                const t1 = performance.now();

                const latencyMs = Math.round(t1 - t0);
                document.getElementById('latency-badge').innerText = `RAM ${latencyMs}ms`;

                allSellers = data.sellers || [];
                recentNewSellers = data.recent_new_sellers || [];

                // Detect newly arrived sellers
                if (!isFirstLoad) {
                    for (const s of allSellers) {
                        if (!knownNicks.has(s.nickName)) {
                            knownNicks.add(s.nickName);
                            playAlertChime();
                            showToast("Người Bán Mới Xuất Hiện!", `${s.nickName} - Giá: ${Number(s.price).toLocaleString()} VND`);
                        }
                    }
                } else {
                    allSellers.forEach(s => knownNicks.add(s.nickName));
                    isFirstLoad = false;
                }

                // Update counts & metrics
                document.getElementById('sellers-count').innerText = allSellers.length + ' sellers';
                document.getElementById('count-all').innerText = allSellers.length;
                document.getElementById('count-recent').innerText = recentNewSellers.length;
                document.getElementById('count-merchant').innerText = allSellers.filter(s => s.userType === 'merchant').length;
                document.getElementById('alerts-count').innerText = (data.stats.alerts_sent || 0);
                
                const lastCost = data.stats.last_scan_cost || 1.0;
                document.getElementById('scan-cost').innerText = lastCost + 's';
                document.getElementById('scan-rate-badge').innerText = lastCost + 's/vòng';
                if (data.stats.last_total_ads) {
                    document.getElementById('total-ads-count').innerText = data.stats.last_total_ads;
                }

                const d = new Date();
                document.getElementById('last-update').innerText = d.toTimeString().split(' ')[0] + '.' + String(d.getMilliseconds()).padStart(3, '0').slice(0, 2);

                renderTable();

                // Save price map for next diff check
                allSellers.forEach(s => {
                    prevPrices[s.nickName] = parseFloat(s.price) || 0;
                });

            } catch (err) {
                console.error('Lỗi tải dữ liệu:', err);
            }
        }

        refreshData();
        // High frequency poll: 1 second interval
        setInterval(refreshData, 1000);
    </script>
</body>
</html>
"""

class RadarHandler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html_text):
        body = html_text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, text_str):
        body = text_str.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        try:
            if self.path in ("/", "/index.html"):
                self.send_html(DASHBOARD_HTML)

            elif self.path == "/api/logs":
                logs_text = "\n".join(binance_p2p_telebot.LOG_BUFFER)
                self.send_text(logs_text or "Chưa có nhật ký ghi nhận.")

            elif self.path == "/api/debug":
                debug_results = {}
                for target_url in [binance_p2p_telebot.API_URL]:
                    try:
                        t0 = time.time()
                        payload = {"asset": "USDT", "fiat": "VND", "tradeType": "BUY", "page": 1, "rows": 5, "payTypes": []}
                        resp = requests.post(target_url, json=payload, headers={"Content-Type": "application/json", "clientType": "android"}, timeout=5)
                        debug_results[target_url] = {
                            "status": resp.status_code,
                            "cost": round(time.time() - t0, 3),
                            "data_len": len(resp.text),
                            "code": resp.json().get("code") if resp.status_code == 200 else None
                        }
                    except Exception as e:
                        debug_results[target_url] = {"error": str(e)}
                self.send_json(debug_results)

            elif self.path == "/health":
                res = {
                    "status": "ok",
                    "uptime": int(time.time() - binance_p2p_telebot.stats["start_time"]),
                    "known_sellers": len(binance_p2p_telebot.known_sellers),
                    "total_scans": binance_p2p_telebot.stats["total_scans"]
                }
                self.send_json(res)

            elif self.path == "/api/status":
                # 100% Non-blocking instant RAM read (< 1ms)
                cur = binance_p2p_telebot.latest_sellers or {}
                sellers_list = list(cur.values())
                sorted_sellers = sorted(sellers_list, key=lambda x: float(x.get("price") or 99999999))
                
                payload = {
                    "known_sellers_count": len(binance_p2p_telebot.known_sellers),
                    "subscribers_count": len(binance_p2p_telebot.subscribers),
                    "stats": binance_p2p_telebot.stats,
                    "sellers": sorted_sellers,
                    "recent_new_sellers": list(binance_p2p_telebot.recent_new_sellers),
                    "config": binance_p2p_telebot.config
                }
                self.send_json(payload)

            else:
                self.send_response(404)
                self.end_headers()

        except Exception as e:
            binance_p2p_telebot.log_event("ERROR", f"HTTP Handler Error on {self.path}: {e}")

    def log_message(self, format, *args):
        msg = format % args
        # Only log errors or specific endpoints to avoid buffer noise
        if " 404 " in msg or " 500 " in msg or "/api/logs" not in msg:
            binance_p2p_telebot.log_event("HTTP", msg)

def main():
    binance_p2p_telebot.log_event("SYSTEM", "=" * 60)
    binance_p2p_telebot.log_event("SYSTEM", "🚀 STARTING BINANCE P2P VIP RADAR & REALTIME DASHBOARD")
    binance_p2p_telebot.log_event("SYSTEM", f"• Web Server Port : {PORT}")
    binance_p2p_telebot.log_event("SYSTEM", f"• Mode            : ThreadingHTTPServer (High-Frequency)")
    binance_p2p_telebot.log_event("SYSTEM", f"• API Gateway     : {binance_p2p_telebot.API_URL}")
    binance_p2p_telebot.log_event("SYSTEM", "=" * 60)

    binance_p2p_telebot.start_background_threads()

    server = ThreadingHTTPServer(("0.0.0.0", PORT), RadarHandler)
    binance_p2p_telebot.log_event("SYSTEM", f"[+] Real-Time Web Dashboard listening on http://0.0.0.0:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        binance_p2p_telebot.log_event("SYSTEM", "[!] Stopping server...")
        server.server_close()

if __name__ == "__main__":
    main()
