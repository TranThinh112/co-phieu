# AI STOCK SCANNER — HỆ THỐNG PHÂN TÍCH ĐỊNH LƯỢNG CHỨNG KHOÁN VIỆT NAM

Hệ thống AI Stock Scanner được xây dựng bằng Python nhằm tự động quét thị trường chứng khoán Việt Nam (HOSE, HNX, UPCoM), tính toán chỉ báo kỹ thuật, lọc thanh khoản, chấm điểm tín hiệu định lượng (Rule Score), dự báo xác suất tăng giá bằng Machine Learning (LightGBM) và mô phỏng giao dịch backtest.

---

## 📌 CẤU TRÚC DỰ ÁN

```text
ai-stock-scanner/
├── app.py                      # Giao diện Dashboard Streamlit & Plotly
├── run_scanner.py              # CLI runner (Scan, Train, Backtest)
├── config/
│   ├── settings.yaml           # Cấu hình tham số hệ thống, trọng số score, backtest
│   └── universe.yaml           # Danh sách danh mục cổ phiếu, ngành và chỉ số
├── data/
│   ├── providers/              # Lớp Data Providers (Base, YFinance, CSV, Synthetic)
│   ├── downloader.py           # Bộ tải dữ liệu tích hợp cache & validation
│   ├── validator.py            # Kiểm tra chất lượng & làm sạch dữ liệu
│   ├── cache.py                # Cache SQLite lưu dữ liệu lịch sử
│   └── storage.py              # SQLite storage lưu kết quả scan, watchlist, paper trades
├── universe/
│   └── stock_universe.py       # Quản lý Universe cổ phiếu, ngành và sàn
├── features/
│   ├── technical.py            # Chỉ báo kỹ thuật (SMA, EMA, ADX, Slopes, Returns)
│   ├── momentum.py             # Chỉ báo động lượng (RSI, MACD, ROC)
│   ├── volatility.py           # Chỉ báo biến động (ATR, Bollinger Bands, Volatility 20D)
│   ├── liquidity.py            # Chỉ báo thanh khoản (SMA Vol 20D, Trading Value 20D)
│   └── market_regime.py        # Phân tích trạng thái & độ rộng thị trường
├── strategies/
│   ├── trend_following.py      # Phân loại xu hướng (Tăng, Giảm, Đi ngang)
│   ├── breakout.py             # Phát hiện bùng nổ kháng cự (Không dính lookahead bias)
│   ├── pullback.py             # Phát hiện nhịp kéo ngược về đường hỗ trợ
│   └── relative_strength.py    # Sức mạnh tương đối so với VN-Index (Mansfield RS)
├── models/
│   ├── dataset.py              # Xây dựng ma trận đặc trưng & nhãn mục tiêu (5D, 10D, 20D)
│   ├── train.py                # Train & Calibrate mô hình LightGBM
│   ├── predict.py              # Dự báo xác suất (Trả về N/A nếu chưa train)
│   ├── evaluate.py             # Đánh giá out-of-sample (Brier score, Precision@K, Log Loss)
│   └── model_registry.py       # Quản lý phiên bản & metadata mô hình
├── scanner/
│   ├── filters.py              # Bộ lọc độc lập tiêu chuẩn
│   ├── scoring.py              # Bộ chấm điểm định lượng 0-100
│   ├── ranking.py              # Xếp hạng & phân loại (Strong, Potential, Watchlist, Excluded)
│   └── explanations.py         # Giải thích lý do tích cực & rủi ro bằng tiếng Việt
├── backtest/
│   ├── engine.py               # Engine mô phỏng giao dịch sự kiện
│   ├── costs.py                # Mô hình chi phí (Phí mua/bán, thuế, trượt giá)
│   └── metrics.py              # Chỉ số hiệu năng (Return, CAGR, Max Drawdown, Sharpe, Win Rate)
├── broker/
│   ├── base.py                 # Interface Adapter môi giới
│   ├── paper.py                # Paper Broker hoạt động đầy đủ trên SQLite
│   └── vndirect.py             # Placeholder Adapter tích hợp VNDirect Open API tương lai
├── reports/
│   └── export.py               # Xuất báo cáo CSV / JSON
├── database/                   # SQLite databases (cache.db, scanner.db)
├── tests/                      # Bộ kiểm thử tự động pytest
├── requirements.txt            # Danh sách thư viện phụ thuộc
├── .env.example                # Cấu hình biến môi trường mẫu
└── README.md                   # Hướng dẫn sử dụng
```

---

## 🚀 HƯỚNG DẪN CÀI ĐẶT

### 1. Yêu cầu hệ thống
- Python 3.11 trở lên.
- Hệ điều hành: Windows / macOS / Linux.

### 2. Cài đặt các thư viện phụ thuộc
```bash
pip install -r requirements.txt
```

---

## ⚙️ CẤU HÌNH NGUỒN DỮ LIỆU

Mặc định hệ thống hỗ trợ 3 Nguồn Dữ Liệu:
1. **Public API (Yahoo Finance .VN)**: Tự động truy xuất dữ liệu giá điều chỉnh cho mã Việt Nam (VD: `FPT.VN`, `HPG.VN`).
2. **CSV Local Storage**: Đọc file dữ liệu lịch sử dạng CSV từ thư mục `data/csv_storage/{SYMBOL}.csv`.
3. **Synthetic Data**: Dữ liệu giả lập chuẩn hóa **chỉ dùng cho Unit Test và chạy Offline**, được đánh dấu rõ ràng `[SYNTHETIC DATA]` và không đưa vào kết quả khuyến nghị thực tế.

---

## 💻 HƯỚNG DẪN SỬ DỤNG

### 1. Khởi chạy Giao Diện Dashboard (Streamlit)
```bash
streamlit run app.py
```
Dashboard mở trên trình duyệt tại `http://localhost:8501` với các trang chính:
- **📊 Tổng Quan Thị Trường**: Trạng thái VN-Index, độ rộng thị trường, tỷ lệ cổ phiếu trên SMA20/50.
- **🔍 Market Scanner**: Chạy Scan, lọc theo sàn/ngành/điểm số, sắp xếp theo Rule Score hoặc AI Probability, xuất CSV.
- **📈 Chi Tiết Cổ Phiếu**: Biểu đồ Nến, SMA, Volume, RSI, MACD và giải thích chi tiết lý do tăng/rủi ro.
- **⭐ Watchlist Danh Mục**: Lưu danh mục theo dõi và ghi chú cá nhân.
- **🎯 AI Model & Backtest**: Huấn luyện AI LightGBM out-of-sample và chạy mô phỏng backtest lợi nhuận/Max Drawdown/Sharpe.
- **💼 Paper Trading Broker**: Đặt lệnh giả lập không dùng tiền thật và quản lý tài khoản paper trading.

### 2. Chạy Scan Thị Trường Từ Dòng Lệnh (CLI)
```bash
# Quét thị trường với dữ liệu Yahoo Finance thực tế và xuất file CSV
python run_scanner.py --mode scan --provider public --export

# Quét kiểm thử nhanh bằng dữ liệu Synthetic
python run_scanner.py --mode scan --provider synthetic

# Huấn luyện toàn bộ mô hình AI LightGBM (5D, 10D, 20D)
python run_scanner.py --mode train --provider synthetic

# Chạy mô phỏng Backtest chiến lược
python run_scanner.py --mode backtest --provider synthetic
```

---

## 🧪 CHẠY KIỂM THỬ TỰ ĐỘNG (UNIT TESTS)

Để chạy toàn bộ bộ kiểm thử pytest:
```bash
pytest tests/
```

---

## 🛡️ HƯỚNG DẪN TÍCH HỢP VNDIRECT OPEN API TRONG TƯƠNG LAI

Hệ thống đã chuẩn bị sẵn lớp `VNDirectAdapter` kế thừa `BaseBrokerAdapter` với đầy đủ giao diện:
- `get_account_balance()`
- `get_positions()`
- `get_open_orders()`
- `place_order()`
- `cancel_order()`
- `get_order_status()`

**Quy trình kết nối chính thức khi có API key:**
1. Cấu hình `VNDirect_API_KEY` và `VNDIRECT_API_SECRET` trong `.env`.
2. Khai báo Certificate & OAuth token endpoint chính thức của VNDirect.
3. Kích hoạt chuyển đổi `is_paper_trading = False` khi môi trường được xác minh an toàn.
4. Cơ chế chống lệnh trùng lặp (Anti-duplicate check) trong vòng 5 giây đã được tích hợp sẵn tại lớp Adapter.

---

## ⚠️ CẢNH BÁO RỦI RO & KHUYÊN CÁO

- Ứng dụng cung cấp tín hiệu phân tích định lượng và xác suất thống kê dựa trên dữ liệu quá khứ.
- Không có cổ phiếu nào chắc chắn tăng giá 100%. Mọi quyết định đầu tư thực tế hoàn toàn thuộc trách nhiệm của người dùng.
- Phiên bản hiện tại chỉ sử dụng tài khoản Paper Trading (không đặt lệnh tiền thật).
"# co-phieu" 
