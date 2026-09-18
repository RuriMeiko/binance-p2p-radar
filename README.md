# ⚡ Binance P2P VIP Monitor & Radar

Hệ thống giám sát đa luồng và bắt người bán mới trên sàn Binance P2P theo thời gian thực (Real-time Market Radar).

## 🚀 Tính năng nổi bật
- **Quét Đa Luồng Toàn Sàn (Multi-threading)**: Quét sạch 100% tất cả ~24 trang (400+ quảng cáo) trong chưa đầy **1.5 giây**.
- **Bot Telegram Tương Tác 2 Chiều**: Quản lý bật/tắt, lọc giá, lọc số lượng USDT khả dụng, tra cứu Top 5 giá rẻ 100% trên điện thoại.
- **Nút Khớp Lệnh Siêu Tốc**: Nhận tin nhắn cảnh báo kèm nút bấm 1 chạm nhảy thẳng vào ứng dụng Binance để khớp lệnh ngay.
- **Web Dashboard**: Bảng điều khiển trực quan hiển thị số liệu thị trường thời gian thực trên port `8000`.
- **Tự động né Rate Limit**: Cơ chế Connection Pooling và Auto-Backoff đảm bảo hoạt động 24/7 không bị khóa IP.

## 🛠 Hướng dẫn chạy

### Chạy bằng Docker:
```bash
docker build -t binance-p2p-radar .
docker run -d -p 8000:8000 --env TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN" binance-p2p-radar
```

### Chạy trực tiếp với Python:
```bash
pip install -r requirements.txt
python3 main.py
```
