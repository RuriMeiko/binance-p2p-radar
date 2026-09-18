#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Entry Point for Binance P2P VIP Radar
Ultra-Fast In-Memory Cache Web Dashboard (port 8000) + Telegram Bot & P2P Background Scanner
"""

import os
import sys
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import binance_p2p_telebot

PORT = int(os.getenv("PORT", "8000"))

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Binance P2P Radar • Real-Time Market Monitor</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #12151a; }
        ::-webkit-scrollbar-thumb { background: #2b313a; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #3c4450; }
    </style>
</head>
<body class="bg-[#0b0e11] text-gray-100 min-h-screen">
    <!-- Navbar -->
    <header class="border-b border-[#1e2329] bg-[#181a20] px-4 sm:px-8 py-4 flex flex-wrap items-center justify-between gap-4 sticky top-0 z-50 backdrop-blur">
        <div class="flex items-center gap-3">
            <span class="text-2xl">⚡</span>
            <div>
                <h1 class="text-base sm:text-lg font-bold text-yellow-400">Binance P2P Radar</h1>
                <p class="text-xs text-gray-400">Hệ thống quét toàn sàn siêu tốc &lt; 0.05s</p>
            </div>
        </div>
        <div class="flex items-center gap-3 sm:gap-4">
            <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-green-500/10 text-green-400 border border-green-500/20">
                <span class="w-2 h-2 rounded-full bg-green-400 animate-pulse"></span>
                Live 24/7
            </span>
            <a href="https://t.me/testbinancenotibot" target="_blank" class="bg-yellow-400 hover:bg-yellow-500 text-black font-semibold text-xs px-3.5 py-1.5 rounded-lg transition-all flex items-center gap-1.5 shadow-md shadow-yellow-400/10">
                <span>✈️</span> Bot Telegram
            </a>
        </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
        <!-- Stats Cards -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            <div class="bg-[#181a20] border border-[#2b313a] rounded-xl p-4 sm:p-5">
                <p class="text-xs text-gray-400 font-medium uppercase tracking-wider">Thị Trường</p>
                <p class="text-xl sm:text-2xl font-bold text-white mt-1">USDT / VND</p>
                <p class="text-xs text-yellow-400/80 mt-1">Nạp P2P (Mua USDT)</p>
            </div>
            <div class="bg-[#181a20] border border-[#2b313a] rounded-xl p-4 sm:p-5">
                <p class="text-xs text-gray-400 font-medium uppercase tracking-wider">Phản Hồi Cache</p>
                <p class="text-xl sm:text-2xl font-bold text-green-400 mt-1" id="response-time">~1ms</p>
                <p class="text-xs text-gray-400 mt-1">Tức thì không độ trễ</p>
            </div>
            <div class="bg-[#181a20] border border-[#2b313a] rounded-xl p-4 sm:p-5">
                <p class="text-xs text-gray-400 font-medium uppercase tracking-wider">Tổng Người Bán</p>
                <p class="text-xl sm:text-2xl font-bold text-blue-400 mt-1" id="sellers-count">Đang tải...</p>
                <p class="text-xs text-gray-400 mt-1">Quét sạch 24 trang</p>
            </div>
            <div class="bg-[#181a20] border border-[#2b313a] rounded-xl p-4 sm:p-5">
                <p class="text-xs text-gray-400 font-medium uppercase tracking-wider">Cảnh Báo Đã Phát</p>
                <p class="text-xl sm:text-2xl font-bold text-purple-400 mt-1" id="alerts-count">0</p>
                <p class="text-xs text-gray-400 mt-1">Tức thì qua Telegram</p>
            </div>
        </div>

        <!-- Toolbar: Search & Filter Tabs -->
        <div class="bg-[#181a20] border border-[#2b313a] rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
            <!-- Search input -->
            <div class="relative flex-1 min-w-[240px]">
                <span class="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400 text-sm">🔍</span>
                <input type="text" id="search-input" placeholder="Tìm kiếm tên người bán (VD: Bi0702, SpeedMaster...)" 
                    class="w-full bg-[#12151a] border border-[#2b313a] rounded-lg pl-9 pr-4 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-yellow-400 transition-colors">
            </div>

            <!-- Filter Buttons -->
            <div class="flex items-center gap-2 flex-wrap">
                <button onclick="setFilter('all')" id="btn-filter-all" class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-yellow-400 text-black transition-all">
                    Tất Cả (<span id="count-all">0</span>)
                </button>
                <button onclick="setFilter('top20')" id="btn-filter-top20" class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-[#2b313a] text-gray-300 hover:text-white transition-all">
                    Top 20 Rẻ Nhất
                </button>
                <button onclick="setFilter('merchant')" id="btn-filter-merchant" class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-[#2b313a] text-gray-300 hover:text-white transition-all">
                    🏅 Tích Vàng (<span id="count-merchant">0</span>)
                </button>
                <button onclick="refreshData()" title="Làm mới" class="p-2 rounded-lg bg-[#2b313a] hover:bg-[#363d47] text-gray-300 hover:text-white transition-all">
                    🔄
                </button>
            </div>
        </div>

        <!-- Sellers Table -->
        <div class="bg-[#181a20] border border-[#2b313a] rounded-xl overflow-hidden shadow-2xl">
            <div class="px-6 py-4 border-b border-[#2b313a] flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <span class="text-yellow-400 font-bold">📋</span>
                    <h2 class="font-bold text-sm sm:text-base text-white">Danh Sách Người Bán Trên Sàn</h2>
                    <span class="text-xs bg-[#2b313a] text-gray-300 px-2 py-0.5 rounded-full font-medium" id="display-count">Đang hiển thị: 0</span>
                </div>
                <span class="text-xs text-gray-400" id="last-update">Cập nhật: vừa xong</span>
            </div>
            <div class="overflow-x-auto max-h-[650px]">
                <table class="w-full text-left text-sm">
                    <thead class="bg-[#1e2329] text-gray-400 text-xs uppercase font-semibold sticky top-0 z-10">
                        <tr>
                            <th class="px-6 py-3.5">Hạng / Người Bán</th>
                            <th class="px-6 py-3.5">Đơn Giá</th>
                            <th class="px-6 py-3.5">Khả Dụng</th>
                            <th class="px-6 py-3.5">Hạn Mức (VND)</th>
                            <th class="px-6 py-3.5">Độ Uy Tín</th>
                            <th class="px-6 py-3.5">Vị Trí</th>
                            <th class="px-6 py-3.5 text-right">Thao Tác</th>
                        </tr>
                    </thead>
                    <tbody id="sellers-table-body" class="divide-y divide-[#2b313a] text-gray-200">
                        <tr>
                            <td colspan="7" class="px-6 py-12 text-center text-gray-400">
                                <span class="animate-pulse">Đang tải dữ liệu bộ nhớ đệm siêu tốc...</span>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </main>

    <footer class="border-t border-[#1e2329] text-center text-xs text-gray-500 py-6">
        Binance P2P VIP Radar Monitor System • In-Memory Zero-Latency Cache
    </footer>

    <script>
        let allSellers = [];
        let currentFilter = 'all';

        function setFilter(f) {
            currentFilter = f;
            ['all', 'top20', 'merchant'].forEach(name => {
                const btn = document.getElementById('btn-filter-' + name);
                if (btn) {
                    if (name === f) {
                        btn.className = "px-3 py-1.5 text-xs font-semibold rounded-lg bg-yellow-400 text-black transition-all";
                    } else {
                        btn.className = "px-3 py-1.5 text-xs font-semibold rounded-lg bg-[#2b313a] text-gray-300 hover:text-white transition-all";
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
            }

            document.getElementById('display-count').innerText = `Đang hiển thị: ${filtered.length} người bán`;

            const tbody = document.getElementById('sellers-table-body');
            if (filtered.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" class="px-6 py-12 text-center text-gray-400">Không tìm thấy người bán nào phù hợp.</td></tr>`;
                return;
            }

            tbody.innerHTML = filtered.map((s, idx) => {
                const rankBadge = idx === 0 ? '<span class="text-base">🥇</span>' :
                                  idx === 1 ? '<span class="text-base">🥈</span>' :
                                  idx === 2 ? '<span class="text-base">🥉</span>' :
                                  `<span class="text-xs px-2 py-0.5 rounded bg-gray-800 text-gray-400 font-mono">#${idx + 1}</span>`;

                const merchantBadge = s.userType === 'merchant' ? 
                    '<span class="px-1.5 py-0.5 text-[10px] font-bold rounded bg-yellow-400/10 text-yellow-400 border border-yellow-400/30">TÍCH VÀNG 🏅</span>' : 
                    '<span class="text-xs text-gray-500">Thường</span>';

                return `
                    <tr class="hover:bg-[#1e2329]/60 transition-colors">
                        <td class="px-6 py-3.5 font-semibold text-white flex items-center gap-2.5">
                            ${rankBadge}
                            <div>
                                <div class="font-bold text-gray-100 flex items-center gap-1.5">
                                    <span>${s.nickName}</span>
                                </div>
                                <div class="mt-0.5">${merchantBadge}</div>
                            </div>
                        </td>
                        <td class="px-6 py-3.5 text-green-400 font-bold text-base whitespace-nowrap">
                            ${Number(s.price).toLocaleString()} <span class="text-xs text-gray-400 font-normal">VND</span>
                        </td>
                        <td class="px-6 py-3.5 font-medium whitespace-nowrap">
                            ${Number(s.surplusAmount).toLocaleString(undefined, {minimumFractionDigits: 2})} <span class="text-xs text-gray-400">USDT</span>
                        </td>
                        <td class="px-6 py-3.5 text-gray-300 text-xs whitespace-nowrap font-mono">
                            ${Number(s.minAmount).toLocaleString()} ~ ${Number(s.maxAmount).toLocaleString()} đ
                        </td>
                        <td class="px-6 py-3.5 text-xs whitespace-nowrap">
                            <span class="text-yellow-400 font-bold">${(Number(s.monthFinishRate || 0) * 100).toFixed(1)}%</span>
                            <span class="text-gray-400 block text-[11px]">(${Number(s.monthOrderCount || 0).toLocaleString()} đơn 30d)</span>
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

                document.getElementById('response-time').innerText = Math.round(t1 - t0) + 'ms';

                allSellers = data.sellers || [];
                document.getElementById('sellers-count').innerText = allSellers.length + ' sellers';
                document.getElementById('count-all').innerText = allSellers.length;
                document.getElementById('count-merchant').innerText = allSellers.filter(s => s.userType === 'merchant').length;
                document.getElementById('alerts-count').innerText = (data.stats.alerts_sent || 0) + ' lần';
                document.getElementById('last-update').innerText = 'Cập nhật: ' + new Date().toLocaleTimeString();

                renderTable();
            } catch (err) {
                console.error('Lỗi tải dữ liệu:', err);
            }
        }

        refreshData();
        setInterval(refreshData, 3000);
    </script>
</body>
</html>
"""

class RadarHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))

        elif self.path == "/api/debug":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            debug_results = {}
            for target_url in [
                "https://www.binance.com/bapi/c2c/v2/friendly/c2c/adv/search",
                "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
            ]:
                try:
                    t0 = time.time()
                    payload = {"asset": "USDT", "fiat": "VND", "tradeType": "BUY", "page": 1, "rows": 5, "payTypes": []}
                    resp = requests.post(target_url, json=payload, headers={"Content-Type": "application/json", "clientType": "android"}, timeout=6)
                    debug_results[target_url] = {
                        "status": resp.status_code,
                        "cost": round(time.time() - t0, 3),
                        "data_len": len(resp.text),
                        "code": resp.json().get("code") if resp.status_code == 200 else None
                    }
                except Exception as e:
                    debug_results[target_url] = {"error": str(e)}
            self.wfile.write(json.dumps(debug_results, indent=2).encode("utf-8"))

        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            res = {
                "status": "ok",
                "uptime": int(time.time() - binance_p2p_telebot.stats["start_time"]),
                "known_sellers": len(binance_p2p_telebot.known_sellers),
                "total_scans": binance_p2p_telebot.stats["total_scans"]
            }
            self.wfile.write(json.dumps(res).encode("utf-8"))

        elif self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            # Use In-Memory Cache (INSTANT 1ms RESPONSE, NEVER LAGS)
            cur = binance_p2p_telebot.latest_sellers
            if not cur:
                cur, tp, ta = binance_p2p_telebot.fetch_all_sellers()
                binance_p2p_telebot.latest_sellers = cur

            # Sort all sellers by price ascending
            sorted_sellers = sorted(cur.values(), key=lambda x: float(x.get("price", 99999999)))
            
            payload = {
                "known_sellers_count": len(binance_p2p_telebot.known_sellers),
                "subscribers_count": len(binance_p2p_telebot.subscribers),
                "stats": binance_p2p_telebot.stats,
                "sellers": sorted_sellers,
                "config": binance_p2p_telebot.config
            }
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def main():
    print("=" * 68)
    print("🚀 STARTING BINANCE P2P VIP RADAR & WEB DASHBOARD")
    print(f"• Web Server Port : {PORT}")
    print(f"• Telegram Bot    : Active")
    print("=" * 68)

    binance_p2p_telebot.start_background_threads()

    server = HTTPServer(("0.0.0.0", PORT), RadarHandler)
    print(f"[+] Web Dashboard listening on http://0.0.0.0:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[!] Stopping server...")
        server.server_close()

if __name__ == "__main__":
    main()
