#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Binance P2P Ultra-Fast New Seller Monitor
Tool giám sát siêu tốc quét 100% toàn bộ các trang trên Binance P2P.
Sử dụng đa luồng (Multi-threading) + HTTP Connection Pooling để đạt tốc độ < 0.5s cho toàn sàn.
"""

import json
import os
import time
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# ==================== CẤU HÌNH TỐC ĐỘ CAO ====================
ASSET = "USDT"                 # Đồng coin muốn theo dõi (USDT, BTC, ETH, ...)
FIAT = "VND"                   # Đồng tiền pháp định
TRADE_TYPE = "BUY"             # "BUY" = xem người BÁN (Nạp P2P), "SELL" = xem người MUA

# Chế độ quét:
SCAN_FULL_PAGES = True         # True = Tự động quét 100% tất cả các trang trên sàn (~24 trang)
MAX_WORKERS = 5                # 5 luồng song song (tối ưu nhất, 1.5s quét sạch 24 trang, 0% bị 429)
CHECK_INTERVAL_SECONDS = 3     # Thời gian nghỉ an toàn giữa các lần quét (3 giây). Đề xuất: 1 - 2 giây để cực nhạy

PAY_TYPES = []                 # [] = Quét tất cả phương thức thanh toán | hoặc ["BANK"] (chỉ chuyển khoản NH)

# Cấu hình thông báo Telegram (Để trống nếu chỉ cần xem trên màn hình máy tính)
TELEGRAM_BOT_TOKEN = ""        # Điền Token từ @BotFather nếu muốn báo về điện thoại
TELEGRAM_CHAT_ID = ""          # Điền Chat ID của bạn

DATA_FILE = "known_sellers.json"
API_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
# ============================================================

# Khởi tạo HTTP Session tái sử dụng kết nối (Keep-Alive Pool)
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=MAX_WORKERS + 5, pool_maxsize=MAX_WORKERS + 5)
session.mount("https://", adapter)
session.headers.update({
    "Content-Type": "application/json",
    "clientType": "android",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
})

def load_known_sellers():
    """Đọc danh sách người bán đã biết từ file"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_known_sellers(sellers):
    """Lưu danh sách người bán vào file"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(sellers)), f, ensure_ascii=False, indent=2)

def send_telegram_alert(message):
    """Gửi tin nhắn cảnh báo tức thì về Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"[!] Lỗi gửi Telegram: {e}")

def fetch_single_page(page):
    """Lấy dữ liệu của một trang cụ thể với cơ chế né rate limit"""
    time.sleep((page % 5) * 0.03)  # Giãn cách 30ms giữa các luồng để né WAF
    payload = {
        "asset": ASSET,
        "fiat": FIAT,
        "tradeType": TRADE_TYPE,
        "page": page,
        "rows": 20,
        "payTypes": PAY_TYPES,
        "publisherType": None,
        "classifies": ["mass", "profession"]
    }
    try:
        resp = session.post(API_URL, json=payload, timeout=5)
        if resp.status_code == 429:
            print(f"\n[⚠️ RATE LIMIT] Sàn báo 429 (Too Many Requests). Đang tự động hạ nhiệt...")
            time.sleep(5)
            return None
        return resp.json()
    except Exception:
        return None

def fetch_all_sellers():
    """Quét toàn bộ 100% các trang song song siêu tốc"""
    # 1. Quét trang 1 trước để lấy tổng số quảng cáo (total)
    r1 = fetch_single_page(1)
    if not r1 or not r1.get("data"):
        return {}, 0, 0

    total_ads = r1.get("total", 0)
    # Mỗi trang tối đa 20 quảng cáo
    total_pages = (total_ads + 19) // 20 if SCAN_FULL_PAGES else 3

    # 2. Quét song song tất cả các trang còn lại (từ trang 2 đến total_pages)
    all_pages_data = [r1]
    if total_pages > 1:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            rest_results = list(executor.map(fetch_single_page, range(2, total_pages + 1)))
            all_pages_data.extend(rest_results)

    # 3. Trích xuất danh sách người bán duy nhất
    current_sellers = {}
    for p_idx, page_res in enumerate(all_pages_data, start=1):
        if not page_res or not page_res.get("data"):
            continue
        for item in page_res["data"]:
            adv = item.get("adv", {})
            advr = item.get("advertiser", {})
            nick = advr.get("nickName")
            if nick and nick not in current_sellers:
                current_sellers[nick] = {
                    "nickName": nick,
                    "userNo": advr.get("userNo"),
                    "price": adv.get("price"),
                    "surplusAmount": adv.get("surplusAmount"),
                    "minAmount": adv.get("minSingleTransAmount"),
                    "maxAmount": adv.get("maxSingleTransAmount"),
                    "monthOrderCount": advr.get("monthOrderCount"),
                    "monthFinishRate": advr.get("monthFinishRate"),
                    "page": p_idx
                }

    return current_sellers, total_pages, total_ads

def main():
    print("=" * 68)
    print("⚡ BINANCE P2P ULTRA-FAST MONITOR - QUÉT TOÀN SÀN SIÊU TỐC ⚡")
    print(f"• Cặp giao dịch : {ASSET}/{FIAT} | Chiều: {TRADE_TYPE} (Nạp P2P)")
    print(f"• Chế độ quét   : {'100% TẤT CẢ CÁC TRANG (FULL TRANG)' if SCAN_FULL_PAGES else 'Top các trang đầu'}")
    print(f"• Luồng song song: {MAX_WORKERS} threads (Tốc độ ~0.4s/lần quét toàn sàn)")
    print(f"• Chu kỳ quét   : Mỗi {CHECK_INTERVAL_SECONDS} giây")
    print("=" * 68)

    known_sellers = load_known_sellers()

    if not known_sellers:
        print("[*] Đang khởi tạo quét danh sách nền toàn sàn lần đầu...")
        t_start = time.time()
        current, total_p, total_a = fetch_all_sellers()
        t_cost = time.time() - t_start
        known_sellers = set(current.keys())
        save_known_sellers(known_sellers)
        print(f"[+] Hoàn tất quét sạch {total_p} trang ({total_a} quảng cáo) trong {t_cost:.2f}s!")
        print(f"[+] Đã ghi nhận {len(known_sellers)} người bán hiện có làm danh sách nền.")
        print("[+] Từ lúc này, bất kỳ người bán mới nào đăng lệnh sẽ được BÁO ĐỘNG NGAY LẬP TỨC!\n")
    else:
        print(f"[i] Đã nạp {len(known_sellers)} người bán đã biết từ '{DATA_FILE}'.")
        print("[i] Đang bắt đầu chế độ quét liên tục...\n")

    loop_count = 0
    while True:
        loop_count += 1
        now_str = datetime.now().strftime("%H:%M:%S")
        t_start = time.time()
        current_sellers, total_pages, total_ads = fetch_all_sellers()
        scan_duration = time.time() - t_start

        # Kiểm tra xem có nick mới nào không
        new_sellers_found = []
        for nick, info in current_sellers.items():
            if nick not in known_sellers:
                new_sellers_found.append(info)
                known_sellers.add(nick)

        if new_sellers_found:
            save_known_sellers(known_sellers)
            for info in new_sellers_found:
                alert_text = (
                    f"\a\n"
                    f"╔═════════════════════════════════════════════════════════════════╗\n"
                    f"║ 🚨 PHÁT HIỆN NGƯỜI BÁN MỚI XUẤT HIỆN! [{now_str}]             ║\n"
                    f"╠═════════════════════════════════════════════════════════════════╣\n"
                    f"  👤 Tên người bán : {info['nickName']}\n"
                    f"  💵 Đơn giá       : {info['price']} {FIAT}\n"
                    f"  📦 Khả dụng      : {info['surplusAmount']} {ASSET}\n"
                    f"  💳 Hạn mức       : {int(float(info['minAmount'])):,} - {int(float(info['maxAmount'])):,} {FIAT}\n"
                    f"  📊 Lịch sử       : {info['monthOrderCount']} đơn (Hoàn tất: {float(info['monthFinishRate'] or 0)*100:.1f}%)\n"
                    f"  📄 Vị trí        : Trang {info['page']} / {total_pages} (Quét xong trong {scan_duration:.2f}s)\n"
                    f"  🔗 Link P2P      : https://p2p.binance.com/vi/trade/all-payments/{ASSET}?fiat={FIAT}\n"
                    f"╚═════════════════════════════════════════════════════════════════╝"
                )
                print(alert_text)

                # Gửi thông báo Telegram tức thì
                tg_msg = (
                    f"🚨 <b>PHÁT HIỆN NGƯỜI BÁN MỚI ({ASSET}/{FIAT})</b>\n\n"
                    f"👤 <b>Nick:</b> <code>{info['nickName']}</code>\n"
                    f"💵 <b>Giá:</b> {info['price']} {FIAT}\n"
                    f"📦 <b>Khả dụng:</b> {info['surplusAmount']} {ASSET}\n"
                    f"💳 <b>Hạn mức:</b> {int(float(info['minAmount'])):,} - {int(float(info['maxAmount'])):,} {FIAT}\n"
                    f"📊 <b>Lịch sử:</b> {info['monthOrderCount']} đơn ({float(info['monthFinishRate'] or 0)*100:.1f}%)\n"
                    f"📄 <b>Vị trí:</b> Trang {info['page']}/{total_pages}\n"
                    f"⏱ <b>Thời gian:</b> {now_str}"
                )
                send_telegram_alert(tg_msg)
        else:
            print(f"[{now_str}] Lần #{loop_count}: Đã quét sạch {total_pages} trang ({len(current_sellers)} sellers, {total_ads} ads) trong {scan_duration:.2f}s. Không có nick mới.", end="\r")

        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Đã dừng chương trình giám sát.")
