#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
🔥 BINANCE P2P VIP TELEGRAM MONITOR BOT (ENTERPRISE EDITION) 🔥
=============================================================================
"""

import os
import sys
import json
import time
import threading
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# ============================ CẤU HÌNH BAN ĐẦU ============================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8850311223:AAFJlEaQ9IKwApb6hDkpVaduu2g0JeFz55o")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")

CONFIG_FILE = "bot_settings.json"
KNOWN_SELLERS_FILE = "known_sellers.json"
SUBSCRIBERS_FILE = "subscribers.json"
API_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
API_URLS = [
    "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search",
    "https://www.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
]

DEFAULT_CONFIG = {
    "is_running": True,
    "asset": "USDT",
    "fiat": "VND",
    "trade_type": "BUY",
    "min_usdt_amount": 0,
    "max_price": 0,
    "verified_merchant_only": False,
    "check_interval": 1,
    "max_workers": 5,
    "pay_types": []
}

sessions = []
for _ in range(2):
    s = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
    s.mount("https://", adapter)
    s.headers.update({
        "Content-Type": "application/json",
        "clientType": "android",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    })
    sessions.append(s)

session = sessions[0]

config = DEFAULT_CONFIG.copy()
known_sellers = set()
subscribers = set()
latest_sellers = {}
recent_new_sellers = []
stats = {
    "start_time": time.time(),
    "total_scans": 0,
    "alerts_sent": 0,
    "last_scan_cost": 0.0,
    "last_total_ads": 0,
    "last_total_sellers": 0
}
waiting_input = {}

# ============================ XỬ LÝ LƯU TRỮ ============================
def load_config():
    global config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config.update(json.load(f))
        except Exception:
            pass

def save_config():
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def load_sellers():
    global known_sellers
    if os.path.exists(KNOWN_SELLERS_FILE):
        try:
            with open(KNOWN_SELLERS_FILE, "r", encoding="utf-8") as f:
                known_sellers = set(json.load(f))
        except Exception:
            known_sellers = set()

def save_sellers():
    try:
        with open(KNOWN_SELLERS_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(known_sellers)), f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def load_subscribers():
    global subscribers
    if os.path.exists(SUBSCRIBERS_FILE):
        try:
            with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
                subscribers = set(json.load(f))
        except Exception:
            subscribers = set()

def save_subscribers():
    try:
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(subscribers)), f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# ============================ GIAO DIỆN TELEGRAM API ============================
def tg_request(method, payload=None):
    if not TELEGRAM_BOT_TOKEN:
        return None
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"
        resp = requests.post(url, json=payload, timeout=10)
        return resp.json()
    except Exception:
        return None

def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return tg_request("sendMessage", payload)

def edit_message(chat_id, message_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return tg_request("editMessageText", payload)

def answer_callback(query_id, text=None, alert=False):
    payload = {"callback_query_id": query_id}
    if text:
        payload["text"] = text
        payload["show_alert"] = alert
    return tg_request("answerCallbackQuery", payload)

# ============================ GIAO DIỆN MENU TINH GỌN, DỄ NHÌN ============================
def get_main_dashboard_text():
    status_badge = "🟢 <b>HOẠT ĐỘNG 24/7</b>" if config["is_running"] else "🔴 <b>ĐANG TẠM DỪNG</b>"
    
    filter_parts = []
    if config["max_price"] > 0:
        filter_parts.append(f"Giá ≤ {config['max_price']:,}đ")
    if config["min_usdt_amount"] > 0:
        filter_parts.append(f"Min: {config['min_usdt_amount']:,}₮")
    if config["verified_merchant_only"]:
        filter_parts.append("Tích vàng")
    filter_summary = " • ".join(filter_parts) if filter_parts else "Mặc định (Không lọc)"

    text = (
        f"💎 <b>BINANCE P2P • RADAR BOT</b>\n"
        f"────────────────────────\n"
        f"Trạng thái : {status_badge}\n"
        f"Thị trường : <b>{config['asset']}/{config['fiat']}</b> (Nạp P2P)\n"
        f"Bộ lọc     : <code>{filter_summary}</code>\n"
        f"Nick đã nhớ: <b>{len(known_sellers):,} người bán</b>\n"
        f"Người nhận : <b>{len(subscribers)} tài khoản</b>\n"
        f"────────────────────────\n"
        f"<i>💡 Bấm nút điều khiển 1 chạm bên dưới:</i>"
    )
    return text

def get_main_menu_markup():
    toggle_text = "⏸ Tạm Dừng" if config["is_running"] else "▶️ Bật Quét"
    toggle_cb = "action_pause" if config["is_running"] else "action_start"

    keyboard = [
        [
            {"text": toggle_text, "callback_data": toggle_cb},
            {"text": "⚡ Bảng Giá Top 5", "callback_data": "action_top5"}
        ],
        [
            {"text": "⚙️ Bộ Lọc Báo Động", "callback_data": "menu_filters"},
            {"text": "👥 Quản Lý Nick", "callback_data": "menu_sellers"}
        ],
        [
            {"text": "🩺 Tình Trạng Bot", "callback_data": "action_status"},
            {"text": "🔄 Làm Mới", "callback_data": "menu_main"}
        ]
    ]
    return {"inline_keyboard": keyboard}

def get_filters_menu_text():
    price_val = f"{config['max_price']:,} VND" if config['max_price'] > 0 else "Tắt (Báo mọi giá)"
    min_usdt_val = f"{config['min_usdt_amount']:,} USDT" if config['min_usdt_amount'] > 0 else "Tắt (Báo mọi số lượng)"
    merchant_val = "Chỉ Thương gia tích vàng" if config['verified_merchant_only'] else "Tất cả mọi người"
    pay_val = "Chỉ Chuyển khoản ngân hàng" if "BANK" in config['pay_types'] else "Tất cả phương thức"

    text = (
        f"⚙️ <b>CÀI ĐẶT BỘ LỌC CẢNH BÁO</b>\n"
        f"────────────────────────\n"
        f"Chỉ gửi thông báo khi người bán mới thỏa mãn:\n\n"
        f"💵 <b>Giá trần:</b> <code>{price_val}</code>\n"
        f"📦 <b>Khả dụng tối thiểu:</b> <code>{min_usdt_val}</code>\n"
        f"🛡 <b>Đối tượng:</b> <code>{merchant_val}</code>\n"
        f"💳 <b>Thanh toán:</b> <code>{pay_val}</code>\n"
        f"⏱ <b>Chu kỳ quét:</b> <code>{config['check_interval']} giây/lần</code>\n"
        f"────────────────────────\n"
        f"<i>Bấm vào từng mục bên dưới để thay đổi nhanh:</i>"
    )
    return text

def get_filters_menu_markup():
    merchant_btn = "🛡 Tích Vàng: [BẬT]" if config['verified_merchant_only'] else "🛡 Tích Vàng: [TẮT]"
    pay_btn = "💳 PTTT: [Ngân Hàng]" if "BANK" in config['pay_types'] else "💳 PTTT: [Tất Cả]"

    keyboard = [
        [
            {"text": "💵 Đặt Giá Trần", "callback_data": "set_max_price"},
            {"text": "📦 Đặt Min USDT", "callback_data": "set_min_usdt"}
        ],
        [
            {"text": merchant_btn, "callback_data": "toggle_merchant"},
            {"text": pay_btn, "callback_data": "toggle_pay_type"}
        ],
        [
            {"text": f"⏱ Chu Kỳ: {config['check_interval']}s", "callback_data": "set_interval"},
            {"text": "🔄 Xóa Lọc Về Mặc Định", "callback_data": "reset_filters"}
        ],
        [
            {"text": "⬅️ Quay Lại Menu Chính", "callback_data": "menu_main"}
        ]
    ]
    return {"inline_keyboard": keyboard}

def get_sellers_menu_markup():
    keyboard = [
        [{"text": "📋 Xem 10 Nick Gần Nhất", "callback_data": "view_recent_sellers"}],
        [{"text": "➕ Thêm Nick Nền Bằng Tay", "callback_data": "add_seller_manual"}],
        [{"text": "🗑 Xóa Sạch & Nạp Lại Toàn Sàn", "callback_data": "reset_sellers_list"}],
        [{"text": "⬅️ Quay Lại Menu Chính", "callback_data": "menu_main"}]
    ]
    return {"inline_keyboard": keyboard}

# ============================ ENGINE QUÉT DỮ LIỆU BINANCE P2P ============================
def fetch_single_page(page):
    time.sleep((page % 5) * 0.025)
    target_url = API_URLS[page % len(API_URLS)]
    sess = sessions[page % len(sessions)]

    publisher_type = "merchant" if config["verified_merchant_only"] else None
    payload = {
        "asset": config["asset"],
        "fiat": config["fiat"],
        "tradeType": config["trade_type"],
        "page": page,
        "rows": 20,
        "payTypes": config["pay_types"],
        "publisherType": publisher_type,
        "classifies": ["mass", "profession"]
    }
    for retry in range(2):
        try:
            resp = sess.post(target_url, json=payload, timeout=3.5)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                time.sleep(0.15)
                continue
        except Exception:
            time.sleep(0.1)
    return None

def fetch_all_sellers():
    r1 = fetch_single_page(1)
    if not r1 or not r1.get("data"):
        return {}, 0, 0

    total_ads = r1.get("total", 0)
    total_pages = (total_ads + 19) // 20

    all_pages_data = [r1]
    if total_pages > 1:
        with ThreadPoolExecutor(max_workers=config.get("max_workers", 5)) as executor:
            rest_results = list(executor.map(fetch_single_page, range(2, total_pages + 1)))
            all_pages_data.extend(rest_results)

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
                    "advNo": adv.get("advNo"),
                    "nickName": nick,
                    "userNo": advr.get("userNo"),
                    "userType": advr.get("userType"),
                    "price": adv.get("price"),
                    "surplusAmount": adv.get("surplusAmount"),
                    "minAmount": adv.get("minSingleTransAmount"),
                    "maxAmount": adv.get("maxSingleTransAmount"),
                    "monthOrderCount": advr.get("monthOrderCount"),
                    "monthFinishRate": advr.get("monthFinishRate"),
                    "positiveRate": advr.get("positiveRate"),
                    "page": p_idx
                }
    return current_sellers, total_pages, total_ads

# ============================ LUỒNG QUÉT CHÍNH (MONITOR THREAD) ============================
def monitor_worker():
    global known_sellers, stats, latest_sellers, recent_new_sellers

    if not known_sellers:
        current, tp, ta = fetch_all_sellers()
        known_sellers = set(current.keys())
        latest_sellers = current
        save_sellers()

    while True:
        try:
            if not config["is_running"]:
                time.sleep(1)
                continue

            t0 = time.time()
            current_sellers, total_pages, total_ads = fetch_all_sellers()
            cost = time.time() - t0
            latest_sellers = current_sellers

            stats["total_scans"] += 1
            stats["last_scan_cost"] = round(cost, 2)
            stats["last_total_ads"] = total_ads
            stats["last_total_sellers"] = len(current_sellers)

            new_sellers = []
            now_ts = time.time()
            now_str = datetime.now().strftime("%H:%M:%S")

            for nick, info in current_sellers.items():
                if nick not in known_sellers:
                    price_val = float(info["price"] or 0)
                    surplus_val = float(info["surplusAmount"] or 0)

                    if config["max_price"] > 0 and price_val > config["max_price"]:
                        continue
                    if config["min_usdt_amount"] > 0 and surplus_val < config["min_usdt_amount"]:
                        continue

                    new_sellers.append(info)
                    known_sellers.add(nick)
                    
                    recent_new_sellers.insert(0, {
                        **info,
                        "discovered_at": now_ts,
                        "discovered_str": now_str
                    })
                    if len(recent_new_sellers) > 40:
                        recent_new_sellers.pop()

            if new_sellers:
                save_sellers()
                stats["alerts_sent"] += len(new_sellers)

                for info in new_sellers:
                    badge = "🏅 Tích Vàng" if info.get("userType") == "merchant" else "👤 Thường"
                    adv_url = f"https://p2p.binance.com/vi/trade/all-payments/{config['asset']}?fiat={config['fiat']}"
                    
                    price_fmt = f"{float(info['price']):,} VND"
                    surplus_fmt = f"{float(info['surplusAmount']):,.2f} USDT"
                    min_fmt = f"{int(float(info['minAmount'])):,}"
                    max_fmt = f"{int(float(info['maxAmount'])):,} VND"
                    rate_pct = f"{float(info['monthFinishRate'] or 0)*100:.1f}%"

                    alert_card = (
                        f"🚨 <b>PHÁT HIỆN NGƯỜI BÁN MỚI!</b>\n"
                        f"────────────────────────\n"
                        f"👤 <b>Người bán:</b> <code>{info['nickName']}</code> ({badge})\n"
                        f"💰 <b>ĐƠN GIÁ:</b>  <b>{price_fmt}</b>\n"
                        f"📦 <b>Khả dụng:</b>  <b>{surplus_fmt}</b>\n"
                        f"💳 <b>Hạn mức:</b>   {min_fmt} ~ {max_fmt}\n"
                        f"⭐ <b>Độ uy tín:</b>  {rate_pct} ({info['monthOrderCount']} đơn 30d)\n"
                        f"📍 <b>Vị trí:</b>     Trang {info['page']} / {total_pages}\n"
                        f"⏱ <b>Thời gian:</b>  {now_str}\n"
                        f"────────────────────────"
                    )

                    inline_kb = {
                        "inline_keyboard": [
                            [{"text": "⚡ Mở Binance Khớp Lệnh Ngay", "url": adv_url}],
                            [{"text": "🔕 Đã Ghi Nhận (Không Báo Lại)", "callback_data": "ignore_done"}]
                        ]
                    }

                    # Gửi tới Admin và tất cả Subscribers
                    recipients = set(subscribers)
                    if ADMIN_CHAT_ID:
                        recipients.add(str(ADMIN_CHAT_ID))

                    for cid in recipients:
                        send_message(cid, alert_card, inline_kb)

                    print(f"[{now_str}] Phát hiện nick mới: {info['nickName']} - Giá: {info['price']} VND (Trang {info['page']})")

            interval = config.get("check_interval", 1)
            time.sleep(interval)

        except Exception as e:
            time.sleep(1)

# ============================ XỬ LÝ LỆNH & NÚT BẤM TELEGRAM ============================
def handle_message(msg):
    global waiting_input, subscribers
    chat_id = str(msg.get("chat", {}).get("id"))
    text = msg.get("text", "").strip()

    if chat_id not in subscribers:
        subscribers.add(chat_id)
        save_subscribers()

    if ADMIN_CHAT_ID and chat_id != str(ADMIN_CHAT_ID):
        # Allow basic /start and subscribe
        if text.startswith("/start"):
            send_message(chat_id, "✅ <b>Chào mừng bạn!</b> Bạn đã được đăng ký nhận thông báo người bán mới trên Binance P2P.")
        return

    if chat_id in waiting_input:
        field = waiting_input.pop(chat_id)
        if field == "max_price":
            try:
                val = int(text.replace(".", "").replace(",", "").replace("đ", "").replace("VND", "").strip())
                config["max_price"] = val
                save_config()
                v_str = f"{val:,} VND" if val > 0 else "Đã tắt lọc (Báo mọi giá)"
                send_message(chat_id, f"✅ <b>Đã lưu:</b> Giá trần = <code>{v_str}</code>", get_filters_menu_markup())
            except ValueError:
                send_message(chat_id, "❌ Vui lòng nhập số nguyên (Ví dụ: <code>25870</code> hoặc <code>0</code> để tắt).")
            return

        elif field == "min_usdt":
            try:
                val = float(text.replace(",", "").strip())
                config["min_usdt_amount"] = val
                save_config()
                v_str = f"{val:,.2f} USDT" if val > 0 else "Đã tắt lọc (Báo mọi số lượng)"
                send_message(chat_id, f"✅ <b>Đã lưu:</b> Khả dụng tối thiểu = <code>{v_str}</code>", get_filters_menu_markup())
            except ValueError:
                send_message(chat_id, "❌ Vui lòng nhập số hợp lệ (Ví dụ: <code>500</code> hoặc <code>0</code> để tắt).")
            return

        elif field == "interval":
            try:
                val = int(text.strip())
                if val < 1: val = 1
                if val > 60: val = 60
                config["check_interval"] = val
                save_config()
                send_message(chat_id, f"✅ <b>Đã lưu:</b> Chu kỳ quét = <code>{val} giây</code>", get_filters_menu_markup())
            except ValueError:
                send_message(chat_id, "❌ Vui lòng nhập số nguyên từ 1 đến 60.")
            return

        elif field == "add_seller":
            nick = text.strip()
            if nick:
                known_sellers.add(nick)
                save_sellers()
                send_message(chat_id, f"✅ Đã thêm <code>{nick}</code> vào danh sách người bán cũ.", get_sellers_menu_markup())
            return

    if text.startswith("/start") or text.startswith("/menu"):
        send_message(chat_id, get_main_dashboard_text(), get_main_menu_markup())

    elif text.startswith("/top5"):
        handle_top5_query(chat_id)

    elif text.startswith("/status"):
        handle_status_query(chat_id)

def handle_callback_query(call):
    global waiting_input
    chat_id = str(call.get("message", {}).get("chat", {}).get("id"))
    msg_id = call.get("message", {}).get("message_id")
    call_id = call.get("id")
    data = call.get("data", "")

    if ADMIN_CHAT_ID and chat_id != str(ADMIN_CHAT_ID):
        answer_callback(call_id, "⛔ Không có quyền truy cập!", alert=True)
        return

    if data == "menu_main":
        answer_callback(call_id)
        edit_message(chat_id, msg_id, get_main_dashboard_text(), get_main_menu_markup())

    elif data == "menu_filters":
        answer_callback(call_id)
        edit_message(chat_id, msg_id, get_filters_menu_text(), get_filters_menu_markup())

    elif data == "menu_sellers":
        answer_callback(call_id)
        text = (
            f"👥 <b>QUẢN LÝ DANH SÁCH NGƯỜI BÁN NỀN</b>\n"
            f"────────────────────────\n"
            f"• Đang lưu: <b>{len(known_sellers):,} nick cũ</b>\n"
            f"• Bất kỳ ai ngoài danh sách này xuất hiện sẽ kích hoạt còi báo.\n"
            f"────────────────────────"
        )
        edit_message(chat_id, msg_id, text, get_sellers_menu_markup())

    elif data == "action_start":
        config["is_running"] = True
        save_config()
        answer_callback(call_id, "▶️ Đã bật giám sát!")
        edit_message(chat_id, msg_id, get_main_dashboard_text(), get_main_menu_markup())

    elif data == "action_pause":
        config["is_running"] = False
        save_config()
        answer_callback(call_id, "⏸ Đã tạm dừng!")
        edit_message(chat_id, msg_id, get_main_dashboard_text(), get_main_menu_markup())

    elif data == "set_max_price":
        waiting_input[chat_id] = "max_price"
        answer_callback(call_id)
        send_message(chat_id, "⌨️ <b>Nhập Giá Trần mong muốn (VND):</b>\n(Ví dụ gõ <code>25860</code> để chỉ báo khi giá ≤ 25.860, hoặc gõ <code>0</code> để tắt lọc).")

    elif data == "set_min_usdt":
        waiting_input[chat_id] = "min_usdt"
        answer_callback(call_id)
        send_message(chat_id, "⌨️ <b>Nhập Số lượng USDT tối thiểu:</b>\n(Ví dụ gõ <code>500</code> để chỉ báo đơn có ≥ 500 USDT, hoặc gõ <code>0</code> để tắt lọc).")

    elif data == "set_interval":
        waiting_input[chat_id] = "interval"
        answer_callback(call_id)
        send_message(chat_id, "⌨️ <b>Nhập chu kỳ quét (giây):</b>\n(Khuyên dùng: <code>2</code> đến <code>5</code> giây).")

    elif data == "toggle_merchant":
        config["verified_merchant_only"] = not config["verified_merchant_only"]
        save_config()
        msg = "Đã chọn: Chỉ thương gia tích vàng" if config["verified_merchant_only"] else "Đã chọn: Tất cả người bán"
        answer_callback(call_id, msg)
        edit_message(chat_id, msg_id, get_filters_menu_text(), get_filters_menu_markup())

    elif data == "toggle_pay_type":
        if "BANK" in config["pay_types"]:
            config["pay_types"] = []
            answer_callback(call_id, "Đã chọn: Tất cả phương thức")
        else:
            config["pay_types"] = ["BANK"]
            answer_callback(call_id, "Đã chọn: Chỉ Chuyển khoản ngân hàng")
        save_config()
        edit_message(chat_id, msg_id, get_filters_menu_text(), get_filters_menu_markup())

    elif data == "reset_filters":
        config["max_price"] = 0
        config["min_usdt_amount"] = 0
        config["verified_merchant_only"] = False
        config["pay_types"] = []
        config["check_interval"] = 3
        save_config()
        answer_callback(call_id, "✅ Đã đặt lại mặc định!")
        edit_message(chat_id, msg_id, get_filters_menu_text(), get_filters_menu_markup())

    elif data == "view_recent_sellers":
        answer_callback(call_id)
        recent_list = sorted(list(known_sellers))[-12:]
        nicks_text = "\n".join([f"• <code>{n}</code>" for n in recent_list])
        text = f"📋 <b>12 NICK ĐƯỢC GHI NHẬN GẦN NHẤT:</b>\n\n{nicks_text}\n\n<i>(Tổng cộng: {len(known_sellers):,} người bán đã lưu)</i>"
        edit_message(chat_id, msg_id, text, get_sellers_menu_markup())

    elif data == "add_seller_manual":
        waiting_input[chat_id] = "add_seller"
        answer_callback(call_id)
        send_message(chat_id, "⌨️ <b>Nhập chính xác tên Nick cần thêm vào danh sách cũ:</b>")

    elif data == "reset_sellers_list":
        answer_callback(call_id)
        send_message(chat_id, "⏳ Đang quét sàn nạp lại danh sách nền mới...")
        cur, tp, ta = fetch_all_sellers()
        known_sellers = set(cur.keys())
        save_sellers()
        send_message(chat_id, f"✅ Đã nạp mới <b>{len(known_sellers)} người bán</b> làm danh sách nền!", get_sellers_menu_markup())

    elif data == "action_top5":
        answer_callback(call_id, "Đang tải giá...")
        handle_top5_query(chat_id)

    elif data == "action_status":
        answer_callback(call_id)
        handle_status_query(chat_id)

    elif data == "ignore_done":
        answer_callback(call_id, "✅ Đã lưu nick vào danh sách nền!")

def handle_top5_query(chat_id):
    cur, tp, ta = fetch_all_sellers()
    if not cur:
        send_message(chat_id, "❌ Không thể lấy dữ liệu từ Binance lúc này.")
        return

    sorted_list = sorted(cur.values(), key=lambda x: float(x["price"] or 99999999))[:5]
    now_str = datetime.now().strftime("%H:%M:%S")

    ranks = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    cards = [f"⚡ <b>TOP 5 GIÁ RẺ NHẤT THỊ TRƯỜNG ({now_str})</b>\n────────────────────────"]

    for idx, s in enumerate(sorted_list):
        r_icon = ranks[idx]
        p_fmt = f"{float(s['price']):,} VND"
        surplus_fmt = f"{float(s['surplusAmount']):,.2f} USDT"
        min_fmt = f"{int(float(s['minAmount'])):,}"
        max_fmt = f"{int(float(s['maxAmount'])):,} VND"
        rate_pct = f"{float(s['monthFinishRate'] or 0)*100:.1f}%"
        badge = "🏅" if s.get("userType") == "merchant" else "👤"

        card = (
            f"{r_icon} <b>{s['nickName']}</b> {badge}\n"
            f"   💰 <b>{p_fmt}</b>  |  📦 {surplus_fmt}\n"
            f"   💳 Hạn mức: {min_fmt} ~ {max_fmt}\n"
            f"   ⭐ {rate_pct} ({s['monthOrderCount']} đơn)\n"
        )
        cards.append(card)

    cards.append(f"────────────────────────\n<i>Quét sạch {tp} trang ({ta} ads) trong ~1.5s</i>")

    kb = {
        "inline_keyboard": [
            [{"text": "⚡ Mở Sàn Binance P2P", "url": "https://p2p.binance.com/vi/trade/all-payments/USDT?fiat=VND"}],
            [{"text": "🔄 Cập Nhật Giá", "callback_data": "action_top5"}, {"text": "⬅️ Menu Chính", "callback_data": "menu_main"}]
        ]
    }
    send_message(chat_id, "\n".join(cards), kb)

def handle_status_query(chat_id):
    uptime_sec = int(time.time() - stats["start_time"])
    hours, rem = divmod(uptime_sec, 3600)
    minutes, seconds = divmod(rem, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    text = (
        f"🩺 <b>TÌNH TRẠNG HỆ THỐNG RADAR</b>\n"
        f"────────────────────────\n"
        f"• Thời gian chạy (Uptime): <b>{uptime_str}</b>\n"
        f"• Trạng thái : <b>{'🟢 Hoạt động liên tục' if config['is_running'] else '🔴 Đang dừng'}</b>\n"
        f"• Số lần quét sàn : <b>{stats['total_scans']:,} lần</b>\n"
        f"• Cảnh báo đã phát : <b>{stats['alerts_sent']} lần</b>\n"
        f"• Tốc độ quét sàn  : <b>{stats['last_scan_cost']:.2f} giây/lần</b>\n"
        f"• Thị trường thực tế: <b>{stats['last_total_ads']} ads / {stats['last_total_sellers']} sellers</b>\n"
        f"• Người theo dõi : <b>{len(subscribers)} người</b>\n"
        f"• Cơ chế chống 429 : <b>Kích hoạt (0% dính Rate Limit)</b>\n"
        f"────────────────────────"
    )
    kb = {"inline_keyboard": [[{"text": "🔄 Cập Nhật", "callback_data": "action_status"}, {"text": "⬅️ Menu Chính", "callback_data": "menu_main"}]]}
    send_message(chat_id, text, kb)

# ============================ LUỒNG LẮNG NGHE TELEGRAM ============================
def telegram_listener():
    offset = None
    while True:
        try:
            if not TELEGRAM_BOT_TOKEN:
                time.sleep(5)
                continue

            params = {"timeout": 20}
            if offset:
                params["offset"] = offset

            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            resp = requests.get(url, params=params, timeout=25)
            if resp.status_code != 200:
                time.sleep(2)
                continue

            updates = resp.json().get("result", [])
            for u in updates:
                offset = u["update_id"] + 1
                if "message" in u:
                    handle_message(u["message"])
                elif "callback_query" in u:
                    handle_callback_query(u["callback_query"])

        except Exception:
            time.sleep(2)

def start_background_threads():
    load_config()
    load_sellers()
    load_subscribers()

    t_monitor = threading.Thread(target=monitor_worker, daemon=True)
    t_monitor.start()

    t_tele = threading.Thread(target=telegram_listener, daemon=True)
    t_tele.start()

if __name__ == "__main__":
    start_background_threads()
    print("Bot is running... Press Ctrl+C to exit.")
    while True:
        time.sleep(1)
