#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Entry Point for Binance P2P VIP Radar
Combines Web Dashboard (port 8000) with Telegram Bot & P2P Background Scanner
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
    <title>Binance P2P VIP Radar Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
    </style>
</head>
<body class="bg-[#0b0e11] text-gray-100 min-h-screen">
    <!-- Navbar -->
    <header class="border-b border-[#1e2329] bg-[#181a20] px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div class="flex items-center gap-3">
            <span class="text-2xl">⚡</span>
            <div>
                <h1 class="text-lg font-bold text-yellow-400">Binance P2P Radar</h1>
                <p class="text-xs text-gray-400">Enterprise High-Speed Market Scanner</p>
            </div>
        </div>
        <div class="flex items-center gap-4">
            <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-green-500/10 text-green-400 border border-green-500/20">
                <span class="w-2 h-2 rounded-full bg-green-400 animate-pulse"></span>
                Hệ thống 24/7 đang chạy
            </span>
            <a href="https://t.me/testbinancenotibot" target="_blank" class="bg-yellow-400 hover:bg-yellow-500 text-black font-semibold text-xs px-4 py-2 rounded-lg transition-all flex items-center gap-1.5">
                <span>✈️</span> Mở Telegram Bot
            </a>
        </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-6xl mx-auto px-4 py-8 space-y-6">
        <!-- Stats Cards -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div class="bg-[#181a20] border border-[#2b313a] rounded-xl p-5">
                <p class="text-xs text-gray-400 font-medium uppercase tracking-wider">Thị Trường Giám Sát</p>
                <p class="text-2xl font-bold text-white mt-1">USDT / VND</p>
                <p class="text-xs text-yellow-400/80 mt-1">Chiều: Nạp P2P (Mua)</p>
            </div>
            <div class="bg-[#181a20] border border-[#2b313a] rounded-xl p-5">
                <p class="text-xs text-gray-400 font-medium uppercase tracking-wider">Tốc Độ Quét Sàn</p>
                <p class="text-2xl font-bold text-green-400 mt-1" id="scan-speed">~1.4s</p>
                <p class="text-xs text-gray-400 mt-1">Full 24 trang song song</p>
            </div>
            <div class="bg-[#181a20] border border-[#2b313a] rounded-xl p-5">
                <p class="text-xs text-gray-400 font-medium uppercase tracking-wider">Người Bán Ghi Nhận</p>
                <p class="text-2xl font-bold text-blue-400 mt-1" id="sellers-count">...</p>
                <p class="text-xs text-gray-400 mt-1">Danh sách nền chống lặp</p>
            </div>
            <div class="bg-[#181a20] border border-[#2b313a] rounded-xl p-5">
                <p class="text-xs text-gray-400 font-medium uppercase tracking-wider">Cảnh Báo Đã Phát</p>
                <p class="text-2xl font-bold text-purple-400 mt-1" id="alerts-count">0</p>
                <p class="text-xs text-gray-400 mt-1">Tức thì qua Telegram</p>
            </div>
        </div>

        <!-- Top Sellers Table -->
        <div class="bg-[#181a20] border border-[#2b313a] rounded-xl overflow-hidden shadow-xl">
            <div class="px-6 py-4 border-b border-[#2b313a] flex items-center justify-between">
                <h2 class="font-bold text-base text-white flex items-center gap-2">
                    <span>⚡</span> Top 5 Người Bán Giá Rẻ Nhất Sàn Hiện Tại
                </h2>
                <span class="text-xs text-gray-400" id="last-update">Đang tải...</span>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full text-left text-sm">
                    <thead class="bg-[#1e2329] text-gray-400 text-xs uppercase font-semibold">
                        <tr>
                            <th class="px-6 py-3">Người Bán</th>
                            <th class="px-6 py-3">Đơn Giá</th>
                            <th class="px-6 py-3">Khả Dụng</th>
                            <th class="px-6 py-3">Hạn Mức (VND)</th>
                            <th class="px-6 py-3">Độ Uy Tín</th>
                            <th class="px-6 py-3 text-right">Thao Tác</th>
                        </tr>
                    </thead>
                    <tbody id="sellers-table-body" class="divide-y divide-[#2b313a] text-gray-200">
                        <tr>
                            <td colspan="6" class="px-6 py-8 text-center text-gray-400">Đang quét dữ liệu P2P...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Bot Info Banner -->
        <div class="bg-gradient-to-r from-yellow-500/10 via-yellow-500/5 to-transparent border border-yellow-500/20 rounded-xl p-6 flex flex-wrap items-center justify-between gap-4">
            <div>
                <h3 class="font-bold text-yellow-400 text-base">Cảnh báo tự động về điện thoại 24/7</h3>
                <p class="text-sm text-gray-300 mt-1">Nhận ngay thông báo khi có nick mới xả USDT giá rẻ chỉ sau 1-2 giây.</p>
            </div>
            <a href="https://t.me/testbinancenotibot" target="_blank" class="bg-yellow-400 hover:bg-yellow-500 text-black font-bold text-sm px-5 py-2.5 rounded-lg transition-all shadow-lg shadow-yellow-400/20">
                Mở Bot @testbinancenotibot 🚀
            </a>
        </div>
    </main>

    <footer class="border-t border-[#1e2329] text-center text-xs text-gray-500 py-6">
        Binance P2P Radar Monitor System • Powered by Dokploy & Cloudflare
    </footer>

    <script>
        async function updateDashboard() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                
                document.getElementById('sellers-count').innerText = (data.known_sellers_count || 0) + ' sellers';
                document.getElementById('alerts-count').innerText = (data.stats.alerts_sent || 0) + ' lần';
                document.getElementById('scan-speed').innerText = (data.stats.last_scan_cost ? data.stats.last_scan_cost.toFixed(2) + 's' : '~1.4s');
                document.getElementById('last-update').innerText = 'Cập nhật lúc: ' + new Date().toLocaleTimeString();

                const tbody = document.getElementById('sellers-table-body');
                if (data.top_sellers && data.top_sellers.length > 0) {
                    tbody.innerHTML = data.top_sellers.map((s, idx) => `
                        <tr class="hover:bg-[#1e2329]/50 transition-colors">
                            <td class="px-6 py-4 font-semibold text-white flex items-center gap-2">
                                <span class="text-xs px-2 py-0.5 rounded bg-yellow-400/10 text-yellow-400 border border-yellow-400/20">#${idx + 1}</span>
                                <span>${s.nickName}</span>
                                ${s.userType === 'merchant' ? '<span title="Tích vàng">🏅</span>' : ''}
                            </td>
                            <td class="px-6 py-4 text-green-400 font-bold text-base">${Number(s.price).toLocaleString()} đ</td>
                            <td class="px-6 py-4 font-medium">${Number(s.surplusAmount).toLocaleString(undefined, {minimumFractionDigits: 2})} USDT</td>
                            <td class="px-6 py-4 text-gray-300 text-xs">${Number(s.minAmount).toLocaleString()} - ${Number(s.maxAmount).toLocaleString()} đ</td>
                            <td class="px-6 py-4 text-xs">
                                <span class="text-yellow-400 font-semibold">${(Number(s.monthFinishRate || 0) * 100).toFixed(1)}%</span>
                                <span class="text-gray-400">(${s.monthOrderCount} đơn)</span>
                            </td>
                            <td class="px-6 py-4 text-right">
                                <a href="https://p2p.binance.com/vi/trade/all-payments/USDT?fiat=VND" target="_blank" class="text-xs bg-[#2b313a] hover:bg-[#363d47] text-white px-3 py-1.5 rounded transition-all font-medium">Khớp Lệnh ⚡</a>
                            </td>
                        </tr>
                    `).join('');
                }
            } catch (err) {
                console.error('Error fetching status:', err);
            }
        }

        updateDashboard();
        setInterval(updateDashboard, 5000);
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
            
            cur, tp, ta = binance_p2p_telebot.fetch_all_sellers()
            sorted_sellers = sorted(cur.values(), key=lambda x: float(x.get("price", 99999999)))[:5]
            
            payload = {
                "known_sellers_count": len(binance_p2p_telebot.known_sellers),
                "subscribers_count": len(binance_p2p_telebot.subscribers),
                "stats": binance_p2p_telebot.stats,
                "top_sellers": sorted_sellers,
                "config": binance_p2p_telebot.config
            }
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Silence standard HTTP access logging to keep console clean
        pass

def main():
    print("=" * 68)
    print("🚀 STARTING BINANCE P2P VIP RADAR & WEB DASHBOARD")
    print(f"• Web Server Port : {PORT}")
    print(f"• Telegram Bot    : Active")
    print("=" * 68)

    # 1. Start background Telegram Bot and P2P Scanner threads
    binance_p2p_telebot.start_background_threads()

    # 2. Start HTTP Web Server
    server = HTTPServer(("0.0.0.0", PORT), RadarHandler)
    print(f"[+] Web Dashboard listening on http://0.0.0.0:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[!] Stopping server...")
        server.server_close()

if __name__ == "__main__":
    main()
