import sys
import datetime
import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

sys.stdout.reconfigure(encoding="utf-8")

st.set_page_config(
    page_title="AI Stock Scanner & Swing Bot - VN",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)



st.markdown("""
<style>
    .stApp { background-color: #0b0f17; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #e2e8f0; }
    div[data-testid="stMetric"] { background: #131b26; border: 1px solid #233044; border-radius: 10px; padding: 14px 18px; box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35); }
    div[data-testid="stMetricLabel"] { color: #94a3b8; font-size: 0.82rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.6px; }
    div[data-testid="stMetricValue"] { color: #f8fafc; font-size: 1.45rem; font-weight: 700; }
    .autopilot-bar { background: #131b26; border: 1px solid #233044; border-left: 4px solid #3b82f6; border-radius: 8px; padding: 12px 18px; margin-bottom: 20px; }
    .news-card { background-color: #131b26; border: 1px solid #233044; border-radius: 8px; padding: 14px 16px; margin-bottom: 12px; }
    .news-card:hover { border-color: #3b82f6; }
    .quick-pill-label { font-size: 0.82rem; color: #94a3b8; font-weight: 600; margin-bottom: 6px; }
</style>
""", unsafe_allow_html=True)

from universe.stock_universe import StockUniverse
from data.providers.vnstock_provider import VnstockProvider
from data.providers.yfinance_provider import YFinanceProvider
from data.providers.synthetic_provider import SyntheticDataProvider
from data.providers.csv_provider import CsvDataProvider
from data.downloader import DataDownloader
from data.storage import StorageEngine
from data.news import NewsProvider
from scanner.orchestrator import MarketScanner
from scanner.explanations import SignalExplanations
from reports.export import ReportExporter
from models.predict import ModelPredictor
from models.model_registry import ModelRegistry
from models.train import ModelTrainer
from backtest.engine import BacktestEngine
from broker.paper import PaperBroker
from broker.vndirect import VNDirectAdapter
from features.technical import TechnicalFeatures
from features.momentum import MomentumFeatures
from features.volatility import VolatilityFeatures
from features.liquidity import LiquidityFeatures
from strategies.trend_following import TrendFollowingStrategy
from strategies.breakout import BreakoutStrategy
from strategies.relative_strength import RelativeStrengthStrategy
from learning.tracker import RecommendationTracker
from learning.feedback_loop import SelfLearningEngine
from strategies.exit_strategy import ExitAdvisor
from features.limit_price import LimitPricePredictor
from automation.session_manager import MarketSessionManager, is_market_open_now, get_market_session_status
from automation.scheduler import MarketAutopilotScheduler, start_background_scheduler

def translate_trend(val: str) -> str:
    s = str(val or "")
    if "Strong Uptrend" in s or "Tăng mạnh" in s: return "Tăng mạnh"
    if "Uptrend" in s or "Tăng nhẹ" in s or "Tăng" in s: return "Tăng nhẹ"
    if "Downtrend" in s or "Giảm" in s: return "Giảm"
    if "Sideways" in s or "Đi ngang" in s: return "Đi ngang"
    return s or "Chưa rõ"

def translate_category(val: str) -> str:
    s = str(val or "")
    if "Strong Candidate" in s: return "Ứng viên rất mạnh"
    if "Potential Candidate" in s: return "Ứng viên tiềm năng"
    if "Watchlist" in s: return "Theo dõi chặt"
    if "Excluded" in s: return "Loại (Thanh khoản kém)" if "Thanh khoản" in s else "Loại trừ"
    return s

def translate_risk_level(val: str) -> str:
    s = str(val or "").strip()
    return "Cao" if s == "High" else ("Thấp" if s == "Low" else "Trung bình")

def translate_breakout(val: str) -> str:
    s = str(val or "")
    if "Strong Breakout" in s or "Breakout" in s: return "Bứt phá kháng cự"
    if "Consolidation" in s or "Tích lũy" in s: return "Đang tích lũy"
    if "Pullback" in s: return "Điều chỉnh kỹ thuật"
    if "None" in s or "Không" in s: return "Bình thường"
    return s or "Bình thường"


def translate_reasons(reason_str: str) -> str:
    if not reason_str: return "Đang theo dõi tín hiệu"
    text = str(reason_str)
    mapping = {
        "Rule Score below configured entry threshold": "Điểm định lượng chưa đạt chuẩn (tối thiểu 70)",
        "Market regime is bearish": "Thị trường chung đang trong xu hướng Giảm (Bearish)",
        "Market regime is Sideways": "Thị trường chung đang đi ngang (Sideways)",
        "RSI is above the configured overbought threshold": "RSI ở vùng quá mua rủi ro (>75)",
        "Estimated technical risk is high": "Mức độ rủi ro kỹ thuật cao",
        "Maximum simultaneous positions reached": "Đã đủ số vị thế danh mục tối đa",
        "No valid stop-loss level": "Chưa xác định được ngưỡng cắt lỗ",
        "Position below minimum board lot or order value": "Khối lượng dưới lô 100 cổ phiếu",
        "Rule, liquidity, market and position-risk criteria are satisfied": "Thỏa mãn tiêu chí kỹ thuật & quản trị rủi ro",
        "CẢNH BÁO PHÁP LÝ/TIN XẤU": "CẢNH BÁO PHÁP LÝ/TIN XẤU",
        "Nguy cơ bẫy 'Tin ra là bán'": "Nguy cơ bẫy 'Tin ra là bán': Tin tốt nhưng RSI quá mua",
        "Thỏa mãn toàn bộ tiêu chí kỹ thuật, dòng tiền và kiểm soát rủi ro": "Đạt chuẩn kỹ thuật, dòng tiền & quản trị rủi ro",
        "Close below stop-loss or risk limits are exceeded": "Giá thủng cắt lỗ hoặc vi phạm rủi ro",
        "Close below stop-loss, negative news breaks, or risk limits are exceeded": "Giá thủng cắt lỗ, có tin xấu hoặc vi phạm rủi ro"
    }
    for eng, vie in mapping.items():
        text = text.replace(eng, vie)
    return text


def safe_find_symbol(universe_obj, query_str: str) -> str:
    """Tim kiem ma co phieu an toan 100%, bat ke universe la phien ban nao."""
    if not query_str:
        return ""
    q = str(query_str).strip()
    if hasattr(universe_obj, "find_matching_symbol"):
        try:
            res = universe_obj.find_matching_symbol(q)
            if res:
                return res
        except Exception:
            pass

    # Fallback tu dong ho tro khong dau & ten thuong hieu
    import unicodedata
    def _norm(s):
        if not s: return ""
        n = unicodedata.normalize("NFKD", str(s))
        return "".join(c for c in n if not unicodedata.combining(c)).replace("đ", "d").replace("Đ", "d").strip().lower()

    norm_q = _norm(q)
    aliases = {
        "tpbank": "TPB", "tien phong": "TPB", "tien phong bank": "TPB",
        "vpbank": "VPB", "viet nam thinh vuong": "VPB",
        "vietcombank": "VCB", "ngoai thuong": "VCB",
        "techcombank": "TCB", "ky thuong": "TCB",
        "mbbank": "MBB", "quan doi": "MBB",
        "vietinbank": "CTG", "cong thuong": "CTG",
        "bidv": "BID", "a chau": "ACB", "sacombank": "STB",
        "hoa phat": "HPG", "the gioi di dong": "MWG", "tgdd": "MWG",
        "vinamilk": "VNM", "vinhomes": "VHM", "vingroup": "VIC",
        "vndirect": "VND", "ssi": "SSI", "fpt": "FPT"
    }
    if norm_q in aliases:
        return aliases[norm_q]

    all_symbols = getattr(universe_obj, "get_all_symbols", lambda: [])()
    for s in all_symbols:
        if s.upper() == q.upper():
            return s.upper()

    for s in all_symbols:
        lbl = getattr(universe_obj, "get_symbol_display_label", lambda x: x)(s)
        norm_lbl = _norm(lbl)
        if norm_q in norm_lbl or norm_lbl.startswith(norm_q):
            return s
    return ""

def style_table_colors(df: pd.DataFrame, target_columns=None):
    def color_cell(val):
        s = str(val).strip()
        if s.startswith("+") or ("%" in s and not s.startswith("-")):
            try:
                num = float(s.replace("%", "").replace("+", "").replace(",", "").strip())
                if num > 0: return "color: #10b981; font-weight: 700;"
                elif num < 0: return "color: #ef4444; font-weight: 700;"
            except Exception: pass
        if s.startswith("-"):
            try:
                num = float(s.replace("%", "").replace("+", "").replace(",", "").strip())
                if num < 0: return "color: #ef4444; font-weight: 700;"
            except Exception: pass
        if any(w in s for w in ["🟣", "TĂNG TRẦN", "Trần"]):
            return "color: #c084fc; font-weight: 700;"
        if any(w in s for w in ["🔵", "GIẢM SÀN"]):
            return "color: #38bdf8; font-weight: 700;"
        if any(w in s for w in ["🟢", "NÊN MUA", "Mua chuẩn", "Tăng mạnh", "Tăng nhẹ", "Ưu tiên"]):
            return "color: #10b981; font-weight: 700;"
        if any(w in s for w in ["🔴", "CẢNH BÁO", "Giảm", "BÁN", "Bẫy"]):
            return "color: #ef4444; font-weight: 700;"
        if any(w in s for w in ["🟡", "thăm dò", "Chờ điều chỉnh", "Đi ngang"]):
            return "color: #f59e0b; font-weight: 600;"
        return ""

    if target_columns:
        if isinstance(target_columns, str):
            target_columns = [target_columns]
        valid_cols = [c for c in target_columns if c in df.columns]
        if valid_cols:
            return df.style.map(color_cell, subset=valid_cols)
    return df.style.map(color_cell)

@st.cache_data(ttl=180, show_spinner=False)
def get_cached_stock_price(symbol: str) -> float:
    try:
        from data.providers.vnstock_provider import VnstockProvider
        p = VnstockProvider()
        df, _ = p.get_historical_data(symbol, start_date=None, end_date=None)
        if df is not None and not df.empty and "close" in df.columns:
            val = float(df["close"].iloc[-1])
            if val > 0:
                return val
    except Exception:
        pass
    return None
def get_current_stock_price(symbol: str, df_results: pd.DataFrame, scanner_obj=None) -> float:
    """Lấy thị giá mới nhất cho mã cổ phiếu từ scan_results hoặc downloader API trực tiếp."""
    sym = str(symbol).strip().upper()
    if not sym:
        return None
    # 1. Ưu tiên tra cứu từ kết quả quét hôm nay
    if df_results is not None and not df_results.empty and "symbol" in df_results.columns:
        m = df_results[df_results["symbol"] == sym]
        if not m.empty and "close_price" in m.columns:
            try:
                p = float(m.iloc[0]["close_price"])
                if p > 0:
                    return p
            except Exception:
                pass

    # 2. Tra cứu qua cache nhanh (TTL 180s)
    cached_p = get_cached_stock_price(sym)
    if cached_p is not None and cached_p > 0:
        return cached_p

    # 3. Tra cứu trực tiếp từ downloader
    if scanner_obj and hasattr(scanner_obj, "downloader"):
        try:
            df_sym, _ = scanner_obj.downloader.fetch_symbol_data(sym)
            if df_sym is not None and not df_sym.empty and "close" in df_sym.columns:
                p = float(df_sym["close"].iloc[-1])
                if p > 0:
                    return p
        except Exception:
            pass

    return None

if "universe" not in st.session_state or not hasattr(st.session_state.universe, "find_matching_symbol"):
    st.session_state.universe = StockUniverse()
if "provider_type" not in st.session_state: st.session_state.provider_type = "vnstock"
if "scan_results" not in st.session_state: st.session_state.scan_results = pd.DataFrame()
if "regime_info" not in st.session_state: st.session_state.regime_info = {}

st.sidebar.markdown("### ⚡ AI QUANT SCANNER")
st.sidebar.caption("Hệ thống Phân Tích Định Lượng & Lọc Cổ Phiếu VN")

provider_choice = st.sidebar.selectbox(
    "Nguồn Dữ Liệu:",
    ["Thị trường Việt Nam (VNDirect/DNSE - Chuẩn 3 Sàn)", "Public API (Yahoo Finance .VN)", "Dữ liệu Mẫu (Unit Test)", "File CSV Cục Bộ"],
    index=0
)

if "storage" not in st.session_state:
    st.session_state.storage = StorageEngine()
storage = st.session_state.storage
storage.seed_initial_market_data_if_empty()

if "paper_broker" not in st.session_state:
    st.session_state.paper_broker = PaperBroker()
paper_broker = st.session_state.paper_broker

if "tracker" not in st.session_state:
    st.session_state.tracker = RecommendationTracker(db_path=storage.db_path)
    st.session_state.tracker.seed_initial_knowledge()
tracker = st.session_state.tracker

if "learning_engine" not in st.session_state:
    st.session_state.learning_engine = SelfLearningEngine(db_path=storage.db_path)
learning_engine = st.session_state.learning_engine

# Khoi dong scheduler ngay khi Streamlit boot de chay ngam doc lap khong can mo tab
autopilot = start_background_scheduler()
st.session_state.autopilot_scheduler = autopilot

if provider_choice == "Dữ liệu Mẫu (Unit Test)":
    provider = SyntheticDataProvider(st.session_state.universe)
elif provider_choice == "File CSV Cục Bộ":
    provider = CsvDataProvider(universe=st.session_state.universe)
elif provider_choice == "Public API (Yahoo Finance .VN)":
    provider = YFinanceProvider(st.session_state.universe)
else:
    provider = VnstockProvider(st.session_state.universe)

if "scanner" not in st.session_state or st.session_state.get("_last_provider") != provider_choice:
    st.session_state.scanner = MarketScanner(provider=provider)
    st.session_state._last_provider = provider_choice
scanner = st.session_state.scanner

if "news_provider" not in st.session_state:
    st.session_state.news_provider = NewsProvider(storage=storage)
news_provider = st.session_state.news_provider

if st.session_state.scan_results.empty:
    latest_df = storage.get_latest_scan_results()
    if not latest_df.empty:
        st.session_state.scan_results = latest_df

if "latest_summary" not in st.session_state or not st.session_state.latest_summary:
    st.session_state.latest_summary = storage.get_latest_run_summary()

latest_summary = st.session_state.latest_summary
if not st.session_state.regime_info and latest_summary:
    st.session_state.regime_info = latest_summary

st.sidebar.markdown("---")
auto_st = autopilot.get_status()
st.sidebar.markdown(f"""
<div style="background:#0f172a; border:1px solid #1e293b; border-left:4px solid #10b981; border-radius:6px; padding:10px; margin-bottom:12px;">
    <span style="color:#10b981; font-weight:700; font-size:0.88rem;">🟢 BOT TỰ ĐỘNG (AUTOPILOT): ĐANG BẬT</span><br>
    <span style="color:#e2e8f0; font-size:0.8rem; font-weight:600;">⏰ Lịch quét tiếp theo:</span><br>
    <span style="color:#38bdf8; font-size:0.78rem; font-weight:700;">• {auto_st['next_time_str']} ({auto_st['next_action']})</span><br>
    <span style="color:#94a3b8; font-size:0.75rem;">• Lần chạy gần nhất: {auto_st['last_run_time']}</span><br>
    <span style="color:#64748b; font-size:0.73rem; font-style:italic;">{auto_st['last_action']}</span>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("#### 🤖 Khung Giờ Hoạt Động (Tiết Kiệm API)")
session_st = get_market_session_status()
learn_info = session_st.get("learning_details")
learn_snippet = f"<span style='color:#c084fc; font-size:0.77rem; font-weight:600;'>🧠 Tự học: Đang chạy ({learn_info.get('closed_trades', 0)} lệnh, Win rate {learn_info.get('win_rate_pct', 0.0)}%)</span><br>" if learn_info else ""

st.sidebar.markdown(f"""
<div style="background:#141a24; border:1px solid #283347; border-left:4px solid {session_st['badge_color']}; border-radius:6px; padding:10px; margin-bottom:12px;">
    <span style="color:{session_st['badge_color']}; font-weight:700; font-size:0.88rem;">{session_st['badge_label']}</span><br>
    <span style="color:#cbd5e1; font-size:0.8rem; font-weight:500;">⏰ Khung giờ hoạt động:</span><br>
    <span style="color:#94a3b8; font-size:0.77rem;">• Phiên sáng: 09:00 - 11:30<br>• Phiên chiều & ATC: 13:00 - 15:00<br>• Tổng kết sau phiên & Tin tức: 15:00 - 16:30<br>• Cuối tuần: Bot Tự Học & Tinh Chỉnh AI</span><br>
    {learn_snippet}
    <span style="color:#64748b; font-size:0.75rem; font-style:italic;">Ngắt toàn bộ API giá nến cuối tuần để tiết kiệm hạn mức.</span>
</div>
""", unsafe_allow_html=True)

if latest_summary:
    st.sidebar.caption(f"🕒 Cập nhật: {latest_summary.get('timestamp')}")

st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Danh Mục Quản Lý:",
    [
        "⚡ Cổ Phiếu Nên Mua & Quản Trị Vị Thế",
        "🧠 Bot Tự Học & Theo Dõi 14 Ngày",
        "🔍 Bộ Lọc Định Lượng Chuyên Sâu",
        "📈 Phân Tích Kỹ Thuật Chi Tiết",
        "💼 Danh Mục Paper Trading",
        "🎯 Kiểm Định AI & Backtest",
        "⭐ Danh Mục Theo Dõi (Watchlist)"
    ]
)

if page == "⚡ Cổ Phiếu Nên Mua & Quản Trị Vị Thế":
    st.title("🎯 Cổ Phiếu Nên Mua & Quản Trị Vị Thế")
    c_auto_info, c_auto_btn = st.columns([3.8, 1.2])
    auto_st_main = autopilot.get_status()
    c_auto_info.markdown(f"""
    <div style="background:#111b2b; border:1px solid #1e3a8a; border-left:4px solid #3b82f6; border-radius:6px; padding:8px 14px; margin-bottom:10px; font-size:0.84rem; color:#bfdbfe;">
        🤖 <strong>Hệ Thống Tự Động:</strong> Bot tự chạy ngầm lúc <strong>09:05</strong> (mở phiên sáng), <strong>13:05</strong> (mở phiên chiều) và <strong>15:05</strong> (chốt phiên & tin tức). Tiếp theo: <span style="color:#60a5fa; font-weight:700;">{auto_st_main['next_time_str']}</span>
    </div>
    """, unsafe_allow_html=True)
    c_auto_btn.write("<div style='height:2px;'></div>", unsafe_allow_html=True)
    if c_auto_btn.button("⚡ Quét Cập Nhật Ngay", use_container_width=True, key="btn_instant_manual_scan"):
        with st.spinner("Đang quét toàn thị trường..."):
            res = autopilot.trigger_scan_now("MANUAL")
            st.session_state.scan_results = storage.get_latest_scan_results()
            st.session_state.latest_summary = storage.get_latest_run_summary()
            st.session_state.regime_info = st.session_state.latest_summary
            st.success("Đã hoàn tất quét cập nhật thị trường!")
            st.rerun()
    curr_sess = get_market_session_status()
    st.markdown(f"""
    <div style="background:#131b26; border:1px solid #233044; border-left:4px solid {curr_sess['badge_color']}; border-radius:8px; padding:10px 16px; margin-bottom:14px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
        <div>
            <strong style="color:{curr_sess['badge_color']}; font-size:0.92rem;">{curr_sess['badge_label']} &nbsp;·&nbsp; {curr_sess['session_name']}</strong><br>
            <span style="color:#94a3b8; font-size:0.82rem;">{curr_sess['recommended_action']}</span>
        </div>
        <div style="text-align:right;">
            <span style="color:#60a5fa; font-size:0.8rem; font-weight:600; background:#172554; border:1px solid #1e40af; padding:4px 10px; border-radius:6px;">🛡️ BẢO TOÀN HẠN MỨC API</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    raw_regime = st.session_state.regime_info.get("regime", "Đang cập nhật")
    regime_vn = translate_trend(raw_regime)
    pct_20 = st.session_state.regime_info.get("pct_above_sma20", 0.0)
    df_results = st.session_state.scan_results
    bal = paper_broker.get_account_balance()
    trade_plans = storage.get_latest_trade_plans()
    buy_candidates = trade_plans[trade_plans["decision"] == "BUY_CANDIDATE"] if not trade_plans.empty else pd.DataFrame()
    high_count = len(df_results[df_results["rule_score"] >= 65]) if not df_results.empty else 0

    # Banner trạng thái thị trường rõ ràng, dễ hiểu
    if "Bearish" in raw_regime or "Giảm" in regime_vn:
        market_banner = f"""
        <div style="background:#201414; border-left:5px solid #ef4444; border-radius:6px; padding:12px 16px; margin-bottom:16px;">
            <strong style="color:#ef4444; font-size:1rem;">⚠️ THỊ TRƯỜNG CHUNG ĐANG ĐIỀU CHỈNH ({regime_vn} - {pct_20}% CP trên SMA20)</strong><br>
            <span style="color:#cbd5e1; font-size:0.88rem;">
            Thị trường chưa vào sóng tăng đồng thuận. Bot khuyến nghị: <strong>Ưu tiên giải ngân thăm dò 20-30% vị thế</strong> đối với các mã siêu mạnh có tin tốt hỗ trợ, hoặc kiên nhẫn quan sát bảo vệ vốn. Tuyệt đối không tất tay (All-in).
            </span>
        </div>
        """
    else:
        market_banner = f"""
        <div style="background:#141a24; border:1px solid #283347; border-left:5px solid #10b981; border-radius:6px; padding:12px 16px; margin-bottom:16px;">
            <strong style="color:#34d399; font-size:1rem;">🟢 THỊ TRƯỜNG CHUNG THUẬN LỢI ({regime_vn} - {pct_20}% CP trên SMA20)</strong><br>
            <span style="color:#cbd5e1; font-size:0.88rem;">
            Xu hướng thị trường tích cực, dòng tiền lan tỏa. Bạn có thể tự tin giải ngân đủ 100% vị thế chuẩn cho các mã đạt điểm định lượng cao nhất.
            </span>
        </div>
        """
    st.markdown(market_banner, unsafe_allow_html=True)

    # 4 Thẻ chỉ số tổng quan
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Xu Hướng Thị Trường", regime_vn, f"> SMA20: {pct_20}%")
    c2.metric("Cổ Phiếu Điểm Cao", f"{high_count} Mã Tiềm Năng", "Điểm định lượng >= 65")
    c3.metric("Lệnh Đạt Chuẩn Mua Đủ", f"{len(buy_candidates)} Cơ Hội", "Rủi ro: 0.5% vốn/lệnh")
    c4.metric("Tài Sản Giả Lập (NAV)", f"{bal['total_equity']:,.0f} đ", f"Tiền mặt: {bal['cash']:,.0f} đ")

    # =====================================================================
    # BẢNG 1 DUY NHẤT: BẢNG CỔ PHIẾU NÊN MUA (TỐI ƯU CỘT GỌN GÀNG, KHÔNG BỊ TRÀN)
    # =====================================================================
    st.markdown("---")
    st.subheader("⭐ BẢNG CỔ PHIẾU NÊN MUA & THEO DÕI HÔM NAY")
    st.caption("Danh sách các mã được chấm điểm cao nhất toàn thị trường kèm vùng mua, khối lượng đề xuất, điểm cắt lỗ / chốt lời và lý do chi tiết:")

    if not df_results.empty:
        high_score_stocks = df_results[df_results["rule_score"] >= 60].sort_values("rule_score", ascending=False).head(8).copy()
        if high_score_stocks.empty:
            high_score_stocks = df_results.sort_values("rule_score", ascending=False).head(5).copy()

        opp_list = []
        for _, r in high_score_stocks.iterrows():
            sym = r["symbol"]
            close_val = float(r["close_price"])
            rule_sc = float(r["rule_score"])
            chg_val = float(r["price_change"])
            rsi_val = float(r.get("rsi", 50.0))
            trend_vn = translate_trend(r.get("trend", ""))
            
            pos_factors = r.get("positive_factors", [])
            if isinstance(pos_factors, str):
                try: pos_factors = json.loads(pos_factors)
                except Exception: pos_factors = [pos_factors]
            
            thesis_parts = []
            if pos_factors:
                clean_factors = [
                    f.replace("Sự kiện doanh nghiệp hỗ trợ: ", "📰 ")
                     .replace("Sức mạnh tương đối vượt trội so với VN-Index", "💪 Mạnh hơn VN-Index")
                    for f in pos_factors[:3]
                ]
                thesis_parts.extend(clean_factors)
            else:
                thesis_parts.append(f"Điểm kỹ thuật cao ({rule_sc:.1f}/100), xu hướng {trend_vn}")

            if rsi_val >= 72:
                action_advice = f"🟡 Chờ chỉnh (RSI {rsi_val:.0f} cao)"
            elif "Bearish" in raw_regime or "Giảm" in regime_vn:
                action_advice = "🟡 Mua thăm dò 20-30%"
            elif rule_sc >= 75:
                action_advice = "🟢 MUA CHUẨN VỊ THẾ"
            else:
                action_advice = "🟢 Ưu tiên theo dõi mua"

            risk_budget = 500000.0
            per_share_risk = max(close_val * 0.05, 500.0)
            calc_qty = max(100, int((risk_budget / per_share_risk) // 100) * 100)
            max_pos_qty = max(100, int((15000000.0 / close_val) // 100) * 100)
            rec_qty = min(calc_qty, max_pos_qty)

            sl_p = round(close_val * 0.95, 0)
            tp1_p = round(close_val * 1.08, 0)
            tp2_p = round(close_val * 1.15, 0)

            # Tính toán Giá Trần / Giá Sàn & Đánh giá khả năng tăng trần hay giảm sàn
            limit_eval = LimitPricePredictor.evaluate_momentum(r)
            ceil_p = limit_eval["ceiling_price"]
            floor_p = limit_eval["floor_price"]
            next_pred = limit_eval["next_session_prediction"]
            detailed_limit_reason = limit_eval["detailed_reason"]

            opp_list.append({
                "Mã CP": f"{sym} ({r.get('exchange', 'HOSE')})",
                "Giá Đóng Cửa": f"{close_val:,.0f} đ",
                "Thay Đổi": f"{chg_val:+.2f}%",
                "Trần / Sàn Phiên Tới": f"🟣 Trần: {ceil_p:,.0f} đ | 🔵 Sàn: {floor_p:,.0f} đ",
                "Dự Báo Phiên Tới (Trần / Sàn)": next_pred,
                "Khuyến Nghị Mua": action_advice,
                "Vùng Mua & Số Lượng": f"{close_val:,.0f} đ ({rec_qty:,} CP)",
                "Chốt Lời | Cắt Lỗ": f"TP1: {tp1_p:,.0f} đ (+8%) | SL: {sl_p:,.0f} đ (-5%)",
                "Đánh Giá Xung Lực & Lý Do": f"{detailed_limit_reason}; {' | '.join(thesis_parts[:2])}"
            })

        df_opp = pd.DataFrame(opp_list)
        if "cached_styled_opp" not in st.session_state or st.session_state.get("_last_opp_count") != len(df_opp):
            st.session_state.cached_styled_opp = style_table_colors(df_opp, target_columns=["Thay Đổi", "Dự Báo Phiên Tới (Trần / Sàn)", "Khuyến Nghị Mua"])
            st.session_state._last_opp_count = len(df_opp)
        st.dataframe(
            st.session_state.cached_styled_opp,
            use_container_width=True,
            height=340
        )
    else:
        st.info("Chưa có dữ liệu quét trong Database. Hãy bấm quét lại ở cuối trang.")

    # =====================================================================
    # BẢNG 2: BẢNG DANH MỤC CỔ PHIẾU ĐANG NẮM GIỮ (TỰ ĐỘNG TÍNH CHỐT LỜI / CẮT LỖ)
    # =====================================================================
    st.markdown("---")
    st.subheader("💼 QUẢN LÝ DANH MỤC NẮM GIỮ & CỐ VẤN CHỐT LỜI / CẮT LỖ TỰ ĐỘNG")
    st.caption("Quản trị các vị thế cổ phiếu bạn đang nắm giữ. Bot tự động tính Lãi/Lỗ theo thị giá mới nhất và cố vấn chính xác thời điểm Chốt Lời (+8%, +15%) hoặc Cắt Lỗ (-5%):")

    saved_user_positions = storage.get_user_positions()
    active_tracked = tracker.get_active_recommendations()
    paper_positions = paper_broker.get_positions()

    tab_user_pos, tab_tracked_pos, tab_paper_pos = st.tabs([
        f"💼 Danh Mục Cá Nhân Của Bạn ({len(saved_user_positions)} mã)",
        f"🤖 Vị Thế Bot Đang Theo Dõi 14 Ngày ({len(active_tracked)} mã)",
        f"📜 Vị Thế Paper Trading ({len(paper_positions)} mã)"
    ])

    # ---------------- TAB 1: DANH MỤC CÁ NHÂN (USER-ENTERED) ----------------
    with tab_user_pos:
        user_symbols_list = [up["symbol"] for up in saved_user_positions]
        with st.expander("⚙️ Thao Tác Giao Dịch Vị Thế (Mua Thêm DCA • Bán Ra Chốt Lời/Cắt Lỗ • Thêm Mã Mới)", expanded=True):
            sub_tab_buy, sub_tab_sell, sub_tab_adjust, sub_tab_new = st.tabs([
                "🟢 Mua Thêm (DCA)",
                "🔴 Bán Ra (Chốt Lời / Cắt Lỗ)",
                "✏️ Điều Chỉnh Giá Vốn TB Khớp App (100%)",
                "➕ Thêm Mã Mới Nắm Giữ"
            ])
            # 1. SUB-TAB: MUA THEM (DCA)
            with sub_tab_buy:
                if user_symbols_list:
                    cb1, cb2, cb3, cb4 = st.columns([1.4, 1.2, 1.1, 1.3])
                    buy_sym = cb1.selectbox("Chọn mã mua thêm:", user_symbols_list, key="sel_dca_sym")
                    cur_pos = next((p for p in saved_user_positions if p["symbol"] == buy_sym), None)
                    c_old_qty = int(cur_pos["quantity"]) if cur_pos else 0
                    c_old_price = float(cur_pos["avg_buy_price"]) if cur_pos else 0.0

                    # Tu dong lay thi gia khop lenh truc tiep tu san lam mac dinh
                    auto_market_p = get_current_stock_price(buy_sym, df_results, scanner) or c_old_price

                    buy_price = cb2.number_input("Giá Mua Khớp Lệnh (VNĐ):", value=float(auto_market_p), step=100.0, key="num_dca_price")
                    buy_qty = cb3.number_input("Số Lượng Mua:", value=100, step=10, min_value=1, key="num_dca_qty")

                    # Cho phep tick chon co tinh phi giao dich/thue (0.15% chuan san) hay khong
                    col_opt1, col_opt2 = st.columns([2, 2])
                    inc_fee = col_opt1.checkbox("⚡ Tự động tính phí giao dịch & thuế CTCK (0.15%)", value=True, key="chk_dca_fee")
                    fee_pct = 0.0015 if inc_fee else 0.0

                    # Tinh toan mo phong gia von moi chuan xac 100%
                    sim_new_qty = c_old_qty + int(buy_qty)
                    sim_added_cost = int(buy_qty) * float(buy_price) * (1.0 + fee_pct)
                    sim_new_avg = round(((c_old_qty * c_old_price) + sim_added_cost) / sim_new_qty, 1) if sim_new_qty > 0 else float(buy_price)
                    delta_price = sim_new_avg - c_old_price
                    delta_color = "#10b981" if delta_price < 0 else "#ef4444"

                    cb4.write("<div style='height:28px;'></div>", unsafe_allow_html=True)
                    if cb4.button("🟢 Xác Nhận Mua Thêm", type="primary", use_container_width=True, key="btn_exec_buy_dca"):
                        res_buy = storage.execute_user_buy(buy_sym, int(buy_qty), float(buy_price), fee_rate=fee_pct, note="Mua them DCA")
                        st.session_state.pop("cached_styled_exit", None)
                        st.session_state.pop("_last_user_tag", None)
                        st.success(f"✅ Đã mua thêm {int(buy_qty):,} CP {buy_sym} tại {buy_price:,.0f} đ (Phí: {fee_pct*100:.2f}%)! Giá vốn TB mới: {res_buy['new_avg_price']:,.0f} đ (Tổng: {res_buy['new_qty']:,} CP)")
                        st.rerun()

                    st.markdown(f"""
                    <div style="background:#131c2b; border:1px solid #1e3a8a; border-left:4px solid {delta_color}; border-radius:6px; padding:10px 14px; margin-top:8px; font-size:0.9rem; color:#e2e8f0;">
                        💡 <strong>Hiện tại:</strong> {c_old_qty:,} CP @ {c_old_price:,.0f} đ &nbsp;➡️&nbsp; <strong>Sau mua thêm:</strong> {sim_new_qty:,} CP @ <strong>{sim_new_avg:,.0f} đ</strong> (Giá vốn thay đổi: <span style="color:{delta_color}; font-weight:bold;">{delta_price:+,.0f} đ</span> | Đã gồm phí CTCK: {fee_pct*100:.2f}%)
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("💡 Chưa có mã nào trong danh mục. Hãy chuyển sang tab '➕ Thêm Mã Mới Nắm Giữ' để nhập mã đầu tiên.")

            # 2. SUB-TAB: BAN RA (CHOT LOI / CAT LO)
            with sub_tab_sell:
                if user_symbols_list:
                    cs1, cs2, cs3, cs4 = st.columns([1.5, 1.2, 1.2, 1.2])
                    sell_sym = cs1.selectbox("Chọn mã bán ra:", user_symbols_list, key="sel_sell_sym")
                    cur_pos_s = next((p for p in saved_user_positions if p["symbol"] == sell_sym), None)
                    s_curr_qty = int(cur_pos_s["quantity"]) if cur_pos_s else 0
                    s_cost_price = float(cur_pos_s["avg_buy_price"]) if cur_pos_s else 0.0

                    suggested_sell_p = get_current_stock_price(sell_sym, df_results, scanner) or s_cost_price

                    sell_price = cs2.number_input("Giá Bán Thực Tế (VNĐ):", value=float(suggested_sell_p), step=100.0, key="num_sell_price")
                    sell_qty = cs3.number_input("Số Lượng Muốn Bán:", value=min(100, s_curr_qty), step=10, min_value=1, max_value=max(1, s_curr_qty), key="num_sell_qty")

                    est_pnl_vnd = (float(sell_price) - s_cost_price) * int(sell_qty)
                    est_pnl_pct = ((float(sell_price) - s_cost_price) / s_cost_price * 100.0) if s_cost_price > 0 else 0.0
                    est_color = "#10b981" if est_pnl_vnd >= 0 else "#ef4444"
                    is_full_exit = (int(sell_qty) >= s_curr_qty)

                    cs4.write("<div style='height:28px;'></div>", unsafe_allow_html=True)
                    btn_sell_label = "🔴 Bán Hết Toàn Bộ" if is_full_exit else "🔴 Xác Nhận Bán Ra"
                    if cs4.button(btn_sell_label, type="primary", use_container_width=True, key="btn_exec_sell_pos"):
                        res_sell = storage.execute_user_sell(sell_sym, int(sell_qty), float(sell_price), note="Ban chot loi/cat lo")
                        st.session_state.pop("cached_styled_exit", None)
                        st.session_state.pop("_last_user_tag", None)
                        pnl_str = f"{res_sell['realized_pnl']:+,.0f} đ ({res_sell['pnl_pct']:+.2f}%)"
                        if res_sell['remaining_qty'] <= 0:
                            st.success(f"✅ Đã chốt bán TOÀN BỘ {sell_sym}! Lãi/Lỗ thực hiện: {pnl_str}. Đã xóa vị thế khỏi danh mục!")
                        else:
                            st.success(f"✅ Đã bán {res_sell['sold_qty']:,} CP {sell_sym}! Lãi/Lỗ thực hiện: {pnl_str}. Số CP còn lại: {res_sell['remaining_qty']:,} CP.")
                        st.rerun()

                    rem_label = ' • *(Sẽ đóng toàn bộ vị thế)*' if is_full_exit else f' • *(Còn lại: {s_curr_qty - int(sell_qty):,} CP)*'
                    st.markdown(f"""
                    <div style="background:#131c2b; border:1px solid #1e3a8a; border-left:4px solid {est_color}; border-radius:6px; padding:10px 14px; margin-top:8px; font-size:0.9rem; color:#e2e8f0;">
                        💰 <strong>Giá vốn:</strong> {s_cost_price:,.0f} đ &nbsp;|&nbsp; <strong>Giá bán:</strong> {sell_price:,.0f} đ &nbsp;➡️&nbsp; <strong>Ước tính Lãi/Lỗ:</strong> <span style="color:{est_color}; font-weight:bold;">{est_pnl_vnd:+,.0f} đ ({est_pnl_pct:+.2f}%)</span>{rem_label}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("💡 Chưa có cổ phiếu nào trong danh mục để bán.")

            # 3. SUB-TAB: DIEU CHINH GIA VON TB / SO LUONG KHOP APP
            with sub_tab_adjust:
                if user_symbols_list:
                    cad1, cad2, cad3, cad4 = st.columns([1.5, 1.2, 1.2, 1.2])
                    adj_sym = cad1.selectbox("Chọn mã cần khớp dữ liệu app:", user_symbols_list, key="sel_adjust_sym")
                    pos_adj = next((p for p in saved_user_positions if p["symbol"] == adj_sym), None)
                    p_qty = int(pos_adj["quantity"]) if pos_adj else 0
                    p_price = float(pos_adj["avg_buy_price"]) if pos_adj else 0.0

                    adj_new_price = cad2.number_input("Giá Mua TB Trên App (VNĐ):", value=float(p_price), step=10.0, key="num_adj_price")
                    adj_new_qty = cad3.number_input("Số Lượng CP Trên App:", value=int(p_qty), step=1, min_value=1, key="num_adj_qty")

                    cad4.write("<div style='height:28px;'></div>", unsafe_allow_html=True)
                    if cad4.button("✏️ Đồng Bộ Khớp App", type="primary", use_container_width=True, key="btn_exec_adjust_app"):
                        storage.update_user_position_direct(adj_sym, int(adj_new_qty), float(adj_new_price), note="Dong bo khop 100% app chung khoan")
                        st.session_state.pop("cached_styled_exit", None)
                        st.session_state.pop("_last_user_tag", None)
                        st.success(f"✅ Đã đồng bộ khớp 100% mã {adj_sym}: {int(adj_new_qty):,} CP tại giá TB {adj_new_price:,.0f} đ!")
                        st.rerun()

                    st.info(f"💡 Dùng mục này để điều chỉnh giá vốn khớp chuẩn 100% theo tài khoản app chứng khoán thực tế của bạn (có tính phí giao dịch, thuế hoặc khớp lệnh nhiều mức giá khác nhau).")
                else:
                    st.info("💡 Chưa có mã nào trong danh mục để điều chỉnh.")

            # 4. SUB-TAB: THEM MA MOI
            with sub_tab_new:
                c_in1, c_in2, c_in3, c_in4 = st.columns([1.5, 1.2, 1.2, 1.0])
                input_holding_sym = c_in1.text_input("Mã CP hoặc Tên Cty:", key="user_holding_sym", placeholder="VD: TPB, HPG, FPT...").strip().upper()
                
                # Auto-match ticker
                resolved_user_sym = safe_find_symbol(st.session_state.universe, input_holding_sym) if input_holding_sym else ""
                effective_sym = resolved_user_sym if resolved_user_sym else input_holding_sym
                if resolved_user_sym:
                    c_in1.caption(f"🔵 Khớp: **{resolved_user_sym}** — {st.session_state.universe.get_symbol_display_label(resolved_user_sym).split('—')[-1].strip()}")

                existing_entry = next((p for p in saved_user_positions if p["symbol"] == effective_sym), None) if effective_sym else None

                default_p = float(existing_entry["avg_buy_price"]) if existing_entry else 20000.0
                input_holding_price = c_in2.number_input("Giá Mua TB (VNĐ):", value=default_p, step=100.0, key="user_holding_price")
                input_holding_qty = c_in3.number_input("Số Lượng CP:", value=100, step=10, min_value=1, key="user_holding_qty")

                # Canh bao truc quan neu ma da co trong danh muc
                if existing_entry:
                    e_qty = int(existing_entry["quantity"])
                    e_p = float(existing_entry["avg_buy_price"])
                    m_qty = e_qty + int(input_holding_qty)
                    m_avg = round(((e_qty * e_p) + (int(input_holding_qty) * float(input_holding_price))) / m_qty, 1)
                    st.info(f"💡 Mã **{effective_sym}** hiện đã có trong danh mục ({e_qty:,} CP @ {e_p:,.0f} đ). Khi bấm lưu, hệ thống sẽ **TỰ ĐỘNG CỘNG DỒN** thành **{m_qty:,} CP** với giá TB mới là **{m_avg:,.0f} đ** (KHÔNG BỊ MẤT DATA CŨ)!")

                c_in4.write("<div style='height:28px;'></div>", unsafe_allow_html=True)
                btn_save_txt = "💾 Cộng Dồn Vị Thế" if existing_entry else "💾 Lưu Vị Thế Mới"
                if c_in4.button(btn_save_txt, type="primary", use_container_width=True, key="btn_save_user_holding"):
                    if effective_sym:
                        res_s = storage.save_user_position(effective_sym, int(input_holding_qty), float(input_holding_price))
                        st.session_state.pop("cached_styled_exit", None)
                        st.session_state.pop("_last_user_tag", None)
                        if existing_entry:
                            st.success(f"✅ Đã CỘNG DỒN thành công mã {effective_sym}! Tổng số lượng mới: {res_s['new_qty']:,} CP (Cũ: {res_s['old_qty']:,} + Thêm: {res_s['added_qty']:,}) • Giá vốn TB mới: {res_s['new_avg_price']:,.0f} đ!")
                        else:
                            st.success(f"✅ Đã lưu mới thành công mã {effective_sym} ({int(input_holding_qty):,} CP tại {input_holding_price:,.0f} đ)!")
                        st.rerun()
                    else:
                        st.error("Vui lòng nhập mã cổ phiếu hợp lệ.")

        if saved_user_positions:
            user_rows = []
            total_invested = 0.0
            total_current_val = 0.0
            has_price_count = 0

            for up in saved_user_positions:
                s_sym = up["symbol"]
                qty = int(up["quantity"])
                buy_p = float(up["avg_buy_price"])
                
                # Tra cuu thi gia thuc te
                live_price = get_current_stock_price(s_sym, df_results, scanner)
                has_live_price = (live_price is not None and live_price > 0)
                
                if has_live_price:
                    c_price = float(live_price)
                    eval_res = ExitAdvisor.evaluate_exit(
                        symbol=s_sym,
                        buy_price=buy_p,
                        current_price=c_price
                    )
                    val_total = qty * c_price
                    invested = qty * buy_p
                    pnl_vnd = (c_price - buy_p) * qty
                    
                    total_invested += invested
                    total_current_val += val_total
                    has_price_count += 1
                    
                    pnl_pct_str = f"{eval_res['pnl_pct']:+.2f}%"
                    pnl_vnd_str = f"{pnl_vnd:+,.0f} đ"
                    market_p_str = f"{c_price:,.0f} đ"
                    val_total_str = f"{val_total:,.0f} đ"
                    action_label = eval_res["action_label"]
                    reason_detail = eval_res["reason_detail"]
                else:
                    c_price = buy_p
                    invested = qty * buy_p
                    total_invested += invested
                    total_current_val += invested
                    
                    market_p_str = "⚠️ Chưa có giá TT"
                    val_total_str = f"{invested:,.0f} đ"
                    pnl_pct_str = "Chờ cập nhật"
                    pnl_vnd_str = "Chờ cập nhật"
                    action_label = "🟡 Chờ Dữ Liệu"
                    eval_res = ExitAdvisor.evaluate_exit(
                        symbol=s_sym,
                        buy_price=buy_p,
                        current_price=buy_p
                    )
                    reason_detail = "Chưa nhận được thị giá khớp lệnh gần nhất từ sàn. Tạm tính theo giá vốn mua."

                user_rows.append({
                    "Mã CP": s_sym,
                    "Số Lượng": f"{qty:,} CP",
                    "Giá Mua TB": f"{buy_p:,.0f} đ",
                    "Giá Thị Trường": market_p_str,
                    "Giá Trị Danh Mục": val_total_str,
                    "Lãi/Lỗ (%)": pnl_pct_str,
                    "Lãi/Lỗ (VNĐ)": pnl_vnd_str,
                    "Hành Động Khuyên Dùng": action_label,
                    "Chốt Lời TP1 (+8%)": f"{eval_res['tp1_price']:,.0f} đ",
                    "Chốt Lời TP2 (+15%)": f"{eval_res['tp2_price']:,.0f} đ",
                    "Cắt Lỗ SL (-5%)": f"{eval_res['sl_price']:,.0f} đ",
                    "Điểm Chặn Lãi": f"{eval_res['trailing_stop_price']:,.0f} đ",
                    "Lý Do Cụ Thể Nên Bán Hoặc Giữ": reason_detail
                })

            total_pnl_vnd = total_current_val - total_invested
            total_pnl_pct = (total_pnl_vnd / total_invested * 100.0) if total_invested > 0 else 0.0

            # Tong hop tai san danh muc
            m1, m2, m3 = st.columns(3)
            m1.metric("💼 Tổng Vốn Đầu Tư", f"{total_invested:,.0f} đ")
            m2.metric("📈 Thị Giá Hiện Tại", f"{total_current_val:,.0f} đ")
            m3.metric("💰 Tổng Lãi / Lỗ", f"{total_pnl_vnd:+,.0f} đ", f"{total_pnl_pct:+.2f}%")

            df_user_exit = pd.DataFrame(user_rows)
            tag = str(len(df_user_exit)) + '_' + str(int(total_current_val)) + '_' + str(int(total_invested))
            if st.session_state.get('_last_user_tag') != tag or 'cached_styled_exit' not in st.session_state:
                tgt_cols = [c for c in ['Lãi/Lỗ (%)', 'Lãi/Lỗ (VNĐ)', 'Hành Động Khuyên Dùng'] if c in df_user_exit.columns]
                st.session_state.cached_styled_exit = style_table_colors(df_user_exit, target_columns=tgt_cols)
                st.session_state._last_user_tag = tag

            st.dataframe(
                st.session_state.cached_styled_exit,
                use_container_width=True,
                height=min(320, 50 + len(df_user_exit) * 40)
            )

            # BANG NHAT KY GIAO DICH
            trade_history = storage.get_user_trade_history(limit=30)
            if trade_history:
                st.markdown("##### 📜 Lịch Sử Giao Dịch Đã Chốt (Mua Thêm • Bán Ra)")
                th_rows = []
                for th in trade_history:
                    side_label = "🟢 MUA THÊM" if th["side"] == "BUY" else "🔴 BÁN RA"
                    pnl_s = f"{th['realized_pnl']:+,.0f} đ ({th['pnl_pct']:+.2f}%)" if th["side"] == "SELL" else "---"
                    th_rows.append({
                        "Thời Gian": th["trade_time"],
                        "Mã CP": th["symbol"],
                        "Loại Lệnh": side_label,
                        "Số Lượng": f"{th['quantity']:,} CP",
                        "Giá Khớp": f"{th['price']:,.0f} đ",
                        "Giá Vốn Cũ": f"{th['old_avg_price']:,.0f} đ" if th["old_avg_price"] else "---",
                        "Giá Vốn Mới": f"{th['new_avg_price']:,.0f} đ" if th["new_avg_price"] else "---",
                        "Lãi/Lỗ Thực Hiện": pnl_s,
                        "Ghi Chú": th.get("note", "")
                    })
                df_th = pd.DataFrame(th_rows)
                st.dataframe(
                    style_table_colors(df_th, target_columns=["Lãi/Lỗ Thực Hiện", "Loại Lệnh"]),
                    use_container_width=True,
                    height=min(250, 50 + len(df_th) * 35)
                )

            # THANH XOA MA TRUC DIEN
            st.markdown("##### 🗑️ Quản Lý Xóa Vị Thế:")
            col_del_s, col_del_b, col_del_all = st.columns([2.5, 1.5, 1.5])
            user_syms = [up["symbol"] for up in saved_user_positions]
            del_sym = col_del_s.selectbox("Chọn mã muốn xóa:", user_syms, key="sel_del_user_holding")
            
            if col_del_b.button(f"❌ Xóa Mã {del_sym}", type="primary", use_container_width=True, key="btn_confirm_del_user"):
                storage.delete_user_position(del_sym)
                st.session_state.pop("cached_styled_exit", None)
                st.session_state.pop("_last_user_tag", None)
                st.success(f"Đã xóa thành công mã {del_sym} khỏi danh mục cá nhân!")
                st.rerun()

            if col_del_all.button("🗑️ Xóa Toàn Bộ Danh Mục", use_container_width=True, key="btn_confirm_clear_all_user"):
                storage.clear_all_user_positions()
                st.session_state.pop("cached_styled_exit", None)
                st.session_state.pop("_last_user_tag", None)
                st.success("Đã xóa sạch toàn bộ mã trong danh mục cá nhân!")
                st.rerun()
        else:
            st.info("💡 Danh mục cá nhân hiện đang trống. Hãy nhập mã cổ phiếu bạn đang nắm giữ vào form bên trên và bấm '💾 Lưu Vị Thế Mới'.")


    # ---------------- TAB 2: VỊ THẾ BOT THEO DÕI 14 NGÀY ----------------
    with tab_tracked_pos:
        st.caption("Các mã được AI Stock Scanner khuyến nghị và đang theo dõi liên tục 14 ngày để đánh giá tỷ lệ thắng:")
        if not active_tracked.empty:
            tracked_rows = []
            for _, r in active_tracked.iterrows():
                sym = r["symbol"]
                entry_p = float(r["entry_price"])
                cur_p = float(r["current_price"])
                eval_res = ExitAdvisor.evaluate_exit(
                    symbol=sym,
                    buy_price=entry_p,
                    current_price=cur_p
                )
                pnl_pct = (cur_p - entry_p) / entry_p * 100.0 if entry_p > 0 else 0.0
                tracked_rows.append({
                    "Mã CP": sym,
                    "Ngày Đề Xuất": str(r["recommendation_date"]),
                    "Giá Mua Đề Xuất": f"{entry_p:,.0f} đ",
                    "Thị Giá": f"{cur_p:,.0f} đ",
                    "Lãi/Lỗ (%)": f"{pnl_pct:+.2f}%",
                    "Thời Gian Theo Dõi": f"{r['days_tracked']}/14 ngày",
                    "Hành Động": eval_res["action_label"],
                    "Chốt Lời TP1 (+8%)": f"{eval_res['tp1_price']:,.0f} đ",
                    "Chốt Lời TP2 (+15%)": f"{eval_res['tp2_price']:,.0f} đ",
                    "Cắt Lỗ SL (-5%)": f"{eval_res['sl_price']:,.0f} đ",
                    "Lý Do Khuyến Nghị": eval_res["reason_detail"]
                })
            df_tracked_table = pd.DataFrame(tracked_rows)
            st.dataframe(
                style_table_colors(df_tracked_table, target_columns=["Lãi/Lỗ (%)", "Hành Động"]),
                use_container_width=True,
                height=min(300, 50 + len(df_tracked_table) * 40)
            )

            # Xóa hoặc bỏ theo dõi mã
            st.markdown("##### 🗑️ Bỏ Theo Dõi Mã Khuyến Nghị:")
            c_tr1, c_tr2, c_tr3 = st.columns([2.5, 1.5, 1.5])
            tracked_syms = [r["symbol"] for _, r in active_tracked.iterrows()]
            del_tr_sym = c_tr1.selectbox("Chọn mã bỏ theo dõi:", tracked_syms, key="sel_del_tracked")
            if c_tr2.button(f"❌ Bỏ Theo Dõi {del_tr_sym}", use_container_width=True, key="btn_del_tracked_one"):
                tracker.remove_active_recommendation(del_tr_sym)
                st.success(f"Đã bỏ theo dõi mã {del_tr_sym}!")
                st.rerun()
            if c_tr3.button("🗑️ Xóa Hết Đang Theo Dõi", use_container_width=True, key="btn_del_tracked_all"):
                tracker.clear_all_active_recommendations()
                st.success("Đã xóa sạch danh sách bot theo dõi 14 ngày!")
                st.rerun()
        else:
            st.info("Hiện không có mã nào trong danh sách đang theo dõi 14 ngày.")

    # ---------------- TAB 3: DANH MỤC PAPER TRADING ----------------
    with tab_paper_pos:
        st.caption("Danh mục giao dịch giả lập tự động (Paper Trading):")
        if paper_positions:
            paper_rows = []
            for p in paper_positions:
                sym = p["symbol"]
                p_qty = int(p["quantity"])
                p_buy = float(p["avg_buy_price"])
                p_cur = float(p["current_price"])
                eval_res = ExitAdvisor.evaluate_exit(
                    symbol=sym,
                    buy_price=p_buy,
                    current_price=p_cur
                )
                val_total = p_qty * p_cur
                pnl_vnd = (p_cur - p_buy) * p_qty
                paper_rows.append({
                    "Mã CP": sym,
                    "Số Lượng": f"{p_qty:,} CP",
                    "Giá Mua": f"{p_buy:,.0f} đ",
                    "Thị Giá": f"{p_cur:,.0f} đ",
                    "Tổng Giá Trị": f"{val_total:,.0f} đ",
                    "Lãi/Lỗ (%)": f"{eval_res['pnl_pct']:+.2f}%",
                    "Lãi/Lỗ (VNĐ)": f"{pnl_vnd:+,.0f} đ",
                    "Hành Động": eval_res["action_label"],
                    "Chốt Lời TP1 (+8%)": f"{eval_res['tp1_price']:,.0f} đ",
                    "Chốt Lời TP2 (+15%)": f"{eval_res['tp2_price']:,.0f} đ",
                    "Cắt Lỗ SL (-5%)": f"{eval_res['sl_price']:,.0f} đ",
                    "Lý Do": eval_res["reason_detail"]
                })
            df_paper_table = pd.DataFrame(paper_rows)
            st.dataframe(
                style_table_colors(df_paper_table, target_columns=["Lãi/Lỗ (%)", "Lãi/Lỗ (VNĐ)", "Hành Động"]),
                use_container_width=True,
                height=min(260, 50 + len(df_paper_table) * 40)
            )
        else:
            st.info("Chưa có vị thế nào trong danh mục Paper Trading.")


    # Công cụ tra cứu tức thời cho bất kỳ mã cổ phiếu nào
    with st.expander("🔎 Tra Cứu Điểm Chốt Lời & Cắt Lỗ Cho Bất Kỳ Mã Nào (Nhập Giá Mua Của Bạn)", expanded=False):
        st.write("Nhập mã cổ phiếu hoặc tên công ty, hệ thống sẽ tự động đối chiếu mức giá và đưa ra cố vấn chốt lời hoặc cắt lỗ chuẩn xác:")

        # 1-Click Quick Select Pills cho các mã phổ biến
        st.markdown('<div class="quick-pill-label">⚡ Chọn Nhanh Mã Phổ Biến:</div>', unsafe_allow_html=True)
        pill_cols = st.columns(8)
        quick_tickers = ["TPB", "HPG", "FPT", "VPB", "VCB", "SSI", "MWG", "VND"]
        for idx, tkr in enumerate(quick_tickers):
            if pill_cols[idx].button(tkr, key=f"quick_pill_{tkr}", use_container_width=True):
                st.session_state.active_lookup_symbol = tkr
                st.session_state["lookup_input_text"] = tkr

        if "active_lookup_symbol" not in st.session_state:
            st.session_state.active_lookup_symbol = "TPB"

        if "lookup_input_text" not in st.session_state:
            st.session_state["lookup_input_text"] = st.session_state.active_lookup_symbol

        col_t1, col_t2 = st.columns([1, 1])

        typed_input = col_t1.text_input(
            "🔍 Nhập Mã Hoặc Tên Công Ty (Gõ rồi bấm Enter):",
            key="lookup_input_text",
            placeholder="Gõ TPB, HPG, Tiên Phong, Thế Giới Di Động, FPT... rồi Enter"
        )

        matched_sym = safe_find_symbol(st.session_state.universe, typed_input)
        if matched_sym:
            calc_sym = matched_sym
            st.session_state.active_lookup_symbol = matched_sym
        else:
            calc_sym = st.session_state.active_lookup_symbol

        company_full_name = st.session_state.universe.get_symbol_display_label(calc_sym).split("—")[-1].strip()
        stock_info = st.session_state.universe.get_stock_info(calc_sym) or {}
        stock_ex = stock_info.get("exchange", "HOSE")

        # Hiển thị nhãn Khớp Chuẩn Màu Xanh Dương nổi bật
        col_t1.markdown(
            f'<div class="match-exact-badge" style="background:#131c2e; color:#60a5fa; border:1px solid #2563eb; padding:7px 12px; border-radius:6px; font-weight:700; margin-top:4px; font-size:0.92rem;">🔵 ĐÃ KHỚP CHÍNH XÁC: <strong>{calc_sym}</strong> — {company_full_name} (Sàn {stock_ex})</div>',
            unsafe_allow_html=True
        )

        live_lookup_p = get_current_stock_price(calc_sym, df_results, scanner)
        curr_p_stock = float(live_lookup_p) if (live_lookup_p and live_lookup_p > 0) else 30000.0

        # Khởi tạo giá mua mặc định theo mã đang tra cứu
        if "last_calc_sym" not in st.session_state or st.session_state.last_calc_sym != calc_sym:
            st.session_state.last_calc_sym = calc_sym
            st.session_state["exit_calc_buy_price"] = f"{int(curr_p_stock):,}".replace(",", ".")

        buy_price_raw = col_t2.text_input(
            "Giá Bạn Đã Mua (VNĐ):",
            key="exit_calc_buy_price",
            placeholder=f"Ví dụ: {int(curr_p_stock):,}".replace(",", ".")
        )

        try:
            cleaned_p = float(str(buy_price_raw).replace(".", "").replace(",", "").replace(" ", "").strip())
        except Exception:
            cleaned_p = float(curr_p_stock)

        calc_buy_p = max(100.0, cleaned_p)

        eval_custom = ExitAdvisor.evaluate_exit(
            symbol=calc_sym,
            buy_price=float(calc_buy_p),
            current_price=float(curr_p_stock)
        )

        match_stock_info = {}
        if not df_results.empty:
            m_rows = df_results[df_results["symbol"] == calc_sym]
            if not m_rows.empty:
                match_stock_info = m_rows.iloc[0].to_dict()
        if not match_stock_info:
            match_stock_info = {"symbol": calc_sym, "exchange": stock_ex, "close_price": curr_p_stock, "price_change": 0.0, "volume_ratio": 1.0, "rsi": 50.0, "rule_score": 60.0}

        limit_info = LimitPricePredictor.evaluate_momentum(match_stock_info)

        # PHỐI MÀU ĐA DẠNG, TỰ NHIÊN, KHÔNG TRÙNG MÀU XANH:
        # 🟢 LÃI/CHỐT LỜI (>= 4.5%): Emerald Green
        # 🔴 LỖ/CẮT LỖ (< 0%): Coral Red
        # 🟡 CHẶN LÃI (3% - 4.5%): Amber Gold
        # 🔵 HÒA VỐN / NẮM GIỮ (0% - 3%): Cool Slate Navy (KHÔNG DÙNG XANH LÁ)
        action_type = eval_custom.get("action", "HOLD")
        pnl_val = eval_custom.get("pnl_pct", 0.0)

        if "PROFIT" in action_type or pnl_val >= 4.5:
            card_border = "#059669"
            card_bg = "#111c18"
            title_color = "#34d399"
            badge_bg = "#064e3b"
            badge_border = "#10b981"
            badge_text = "#a7f3d0"
        elif "STOP" in action_type or pnl_val < 0:
            card_border = "#dc2626"
            card_bg = "#1a1114"
            title_color = "#f87171"
            badge_bg = "#7f1d1d"
            badge_border = "#ef4444"
            badge_text = "#fecaca"
        elif "TRAILING" in action_type or pnl_val >= 3.0:
            card_border = "#d97706"
            card_bg = "#1c170f"
            title_color = "#fbbf24"
            badge_bg = "#78350f"
            badge_border = "#f59e0b"
            badge_text = "#fef3c7"
        else:
            # Neutral / Hold / Hòa vốn: Cool Slate Navy, không xanh lá
            card_border = "#3b82f6"
            card_bg = "#121824"
            title_color = "#60a5fa"
            badge_bg = "#1e3a8a"
            badge_border = "#3b82f6"
            badge_text = "#bfdbfe"

        pnl_sign_color = "#34d399" if pnl_val > 0 else ("#f87171" if pnl_val < 0 else "#94a3b8")

        card_html = f'''<div style="background:{card_bg}; border:1.5px solid {card_border}; border-radius:10px; padding:18px; margin-top:12px; box-shadow:0 6px 20px rgba(0,0,0,0.35);">
<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; padding-bottom:12px; border-bottom:1px solid #233044;">
<div>
<span style="font-size:0.8rem; font-weight:600; color:#94a3b8; text-transform:uppercase; letter-spacing:0.5px;">KẾT QUẢ ĐÁNH GIÁ VỊ THẾ CỐ VẤN</span><br>
<h3 style="margin:3px 0 0 0; color:{title_color}; font-size:1.35rem; font-weight:800;">
{calc_sym} &nbsp;·&nbsp; <span style="color:#cbd5e1; font-size:1.05rem; font-weight:600;">Giá Mua: {calc_buy_p:,.0f} đ</span> &nbsp;·&nbsp; <span style="color:#cbd5e1; font-size:1.05rem; font-weight:600;">Thị Giá: {curr_p_stock:,.0f} đ</span> &nbsp;(<span style="color:{pnl_sign_color}; font-weight:800;">{eval_custom['pnl_pct']:+.2f}%</span>)
</h3>
</div>
<div>
<span style="display:inline-block; background:{badge_bg}; border:1.5px solid {badge_border}; color:{badge_text}; padding:6px 14px; border-radius:8px; font-weight:800; font-size:0.95rem; letter-spacing:0.3px;">
{eval_custom['action_label']}
</span>
</div>
</div>
<div style="background:#161f2e; border-radius:8px; padding:12px 14px; margin:14px 0; border:1px solid #28374d;">
<p style="color:#f1f5f9; font-size:0.95rem; margin:0; line-height:1.6;">
<strong style="color:#fbbf24;">💡 Lý do tại sao:</strong> {eval_custom['reason_detail']}
</p>
</div>
<div style="background:#141a24; border:1px solid #243042; border-radius:8px; padding:10px 14px; margin-bottom:14px;">
<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
<div>
<span style="color:#94a3b8; font-size:0.82rem; font-weight:600; text-transform:uppercase;">BIÊN ĐỘ PHIÊN TỚI:</span>&nbsp;&nbsp;
<strong style="color:#facc15;">Tham chiếu: {limit_info['ref_price']:,.0f} đ 🟡</strong>&nbsp;|&nbsp;&nbsp;
<strong style="color:#c084fc;">Trần: {limit_info['ceiling_price']:,.0f} đ 🟣</strong>&nbsp;|&nbsp;&nbsp;
<strong style="color:#38bdf8;">Sàn: {limit_info['floor_price']:,.0f} đ 🔵</strong>
</div>
<div>
<span style="font-weight:700; font-size:0.9rem;">{limit_info['next_session_prediction']}</span>
</div>
</div>
<div style="color:#cbd5e1; font-size:0.84rem; margin-top:6px;">
<strong style="color:#94a3b8;">🔍 Phân tích xung lực:</strong> {limit_info['detailed_reason']} ({limit_info['floor_risk_desc']})
</div>
</div>
<div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:12px; text-align:center;">
<div style="background:#1a1114; padding:10px; border-radius:8px; border:1.5px solid #ef4444;">
<span style="color:#f87171; font-size:0.78rem; font-weight:700; text-transform:uppercase; letter-spacing:0.3px;">🔴 CẮT LỖ (SL -5%)</span><br>
<strong style="color:#ef4444; font-size:1.15rem; font-weight:800; display:inline-block; margin-top:3px;">{eval_custom['sl_price']:,.0f} đ</strong>
</div>
<div style="background:#1c170f; padding:10px; border-radius:8px; border:1.5px solid #f59e0b;">
<span style="color:#fbbf24; font-size:0.78rem; font-weight:700; text-transform:uppercase; letter-spacing:0.3px;">🟡 CHẶN LÃI (TRAILING)</span><br>
<strong style="color:#f59e0b; font-size:1.15rem; font-weight:800; display:inline-block; margin-top:3px;">{eval_custom['trailing_stop_price']:,.0f} đ</strong>
</div>
<div style="background:#0c1a14; padding:10px; border-radius:8px; border:1.5px solid #10b981;">
<span style="color:#34d399; font-size:0.78rem; font-weight:700; text-transform:uppercase; letter-spacing:0.3px;">🟢 CHỐT LỜI 1 (TP1 +8%)</span><br>
<strong style="color:#10b981; font-size:1.15rem; font-weight:800; display:inline-block; margin-top:3px;">{eval_custom['tp1_price']:,.0f} đ</strong>
</div>
<div style="background:#171024; padding:10px; border-radius:8px; border:1.5px solid #a855f7;">
<span style="color:#c084fc; font-size:0.78rem; font-weight:700; text-transform:uppercase; letter-spacing:0.3px;">🟣 CHỐT LỜI 2 (TP2 +15%)</span><br>
<strong style="color:#c084fc; font-size:1.15rem; font-weight:800; display:inline-block; margin-top:3px;">{eval_custom['tp2_price']:,.0f} đ</strong>
</div>
</div>
</div>'''
        st.markdown(card_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("⚙️ Tùy chọn Quét Lại Dữ Liệu Thị Trường Ngay"):
        st.write("Hệ thống tự động chạy quét mỗi chiều lúc 15:30. Nếu bạn muốn quét cập nhật ngay lập tức thì bấm nút dưới:")
        if st.button("🔄 Quét Lại Ngay Bây Giờ", type="secondary"):
            with st.spinner("Đang kết nối API và tính toán lại..."):
                df_res, r_info = scanner.run_market_scan()
                st.session_state.scan_results = df_res
                st.session_state.regime_info = r_info
                st.session_state.latest_summary = storage.get_latest_run_summary()
                st.session_state["cached_trade_plans"] = storage.get_latest_trade_plans()
                st.success("Đã hoàn tất quét và cập nhật lại dữ liệu mới nhất!")
                st.rerun()

elif page == "🧠 Bot Tự Học & Theo Dõi 14 Ngày":
    st.title("🧠 Hệ Thống Theo Dõi 14 Ngày & Bot Tự Học Tự Động")
    st.caption("Cơ chế tự kiểm định: Mọi mã khi được đưa vào bảng đề xuất mua sẽ được theo dõi liên tục trong 14 phiên. Bot ghi nhận kết quả Thắng/Thua, phân tích nguyên nhân và tự động tối ưu hóa trọng số AI.")

    m_info = learning_engine.compute_performance_metrics()
    active_df = tracker.get_active_recommendations()
    completed_df = tracker.get_completed_recommendations()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Tỷ Lệ Thắng (Win Rate)", f"{m_info['win_rate_pct']}%", f"{m_info['wins']} Thắng / {m_info['losses']} Thua")
    k2.metric("Lãi Trung Bình (Lệnh Thắng)", f"+{m_info['avg_win_pct']}%", "Đạt hoặc vượt TP1 (+8%)")
    k3.metric("Lỗ Trung Bình (Lệnh Thua)", f"{m_info['avg_loss_pct']}%", "Cắt lỗ kỷ luật (-5%)")
    k4.metric("Hệ Số Lợi Nhuận (Profit Factor)", f"{m_info['profit_factor']}x", f"TB {m_info['avg_holding_days']} phiên/lệnh")

    st.markdown("---")
    st.subheader("⏱️ Danh Sách Cổ Phiếu Đang Trong Chu Kỳ Theo Dõi 14 Ngày")
    st.caption("Các mã vừa được đề xuất mua đang được giám sát giá đóng cửa mỗi phiên để đối chiếu với mục tiêu chốt lời (+8%) và cắt lỗ (-5%):")

    if not active_df.empty:
        view_active = active_df.copy()
        view_active["Mã CP"] = view_active["symbol"]
        view_active["Ngày Đề Xuất"] = view_active["recommendation_date"]
        view_active["Giá Vào Lệnh"] = view_active["entry_price"].apply(lambda x: f"{x:,.0f} đ")
        view_active["Giá Hiện Tại"] = view_active["current_price"].apply(lambda x: f"{x:,.0f} đ")
        view_active["Lãi/Lỗ Hiện Tại"] = view_active["return_pct"].apply(lambda x: f"{x:+.2f}%")
        view_active["Tiến Độ"] = view_active["days_tracked"].apply(lambda x: f"{x}/14 Ngày")
        view_active["Chốt Lời TP1"] = view_active["take_profit_1"].apply(lambda x: f"{x:,.0f} đ (+8%)")
        view_active["Cắt Lỗ SL"] = view_active["stop_loss"].apply(lambda x: f"{x:,.0f} đ (-5%)")
        view_active["Điểm AI"] = view_active["rule_score"].apply(lambda x: f"{x:.1f}")
        view_active["Trạng Thái"] = view_active["return_pct"].apply(lambda r: "🟢 Vận động tích cực" if r > 0 else ("🔴 Chạm vùng rủi ro" if r < -3 else "🟡 Đang tích lũy"))

        cols_active = ["Mã CP", "Ngày Đề Xuất", "Giá Vào Lệnh", "Giá Hiện Tại", "Lãi/Lỗ Hiện Tại", "Tiến Độ", "Chốt Lời TP1", "Cắt Lỗ SL", "Điểm AI", "Trạng Thái"]
        st.dataframe(style_table_colors(view_active[cols_active], target_columns=["Lãi/Lỗ Hiện Tại", "Trạng Thái"]), use_container_width=True)
    else:
        st.info("Hiện tại chưa có mã nào trong danh sách theo dõi.")

    st.markdown("---")
    st.subheader("📚 Nhật Ký Kiểm Định & Đúc Rút Kinh Nghiệm (Tại Sao Thắng / Tại Sao Thua)")
    st.caption("Toàn bộ các lệnh đã kết thúc chu kỳ 14 ngày hoặc chạm TP1/SL được bot tự động giải trình nguyên nhân để lưu vào kho tri thức tự học:")

    if not completed_df.empty:
        view_comp = completed_df.copy()
        view_comp["Mã CP"] = view_comp["symbol"]
        view_comp["Ngày Mua"] = view_comp["recommendation_date"]
        view_comp["Ngày Đóng"] = view_comp["closed_date"].fillna("-")
        view_comp["Số Phiên"] = view_comp["days_tracked"].apply(lambda x: f"{x} phiên")
        view_comp["Kết Quả"] = view_comp.apply(lambda r: f"🟢 THẮNG ({r['return_pct']:+.2f}%)" if r['return_pct'] > 0 else f"🔴 THUA ({r['return_pct']:+.2f}%)", axis=1)
        view_comp["Lý Do Chi Tiết Tại Sao Thắng / Thua"] = view_comp["post_mortem_reason"]
        view_comp["Bài Học Kinh Nghiệm Rút Ra"] = view_comp["lesson_learned"]

        cols_comp = ["Mã CP", "Ngày Mua", "Ngày Đóng", "Số Phiên", "Kết Quả", "Lý Do Chi Tiết Tại Sao Thắng / Thua", "Bài Học Kinh Nghiệm Rút Ra"]
        st.dataframe(style_table_colors(view_comp[cols_comp], target_columns=["Kết Quả"]), use_container_width=True)
    else:
        st.info("Chưa có lệnh nào hoàn tất chu kỳ kiểm định.")

    st.markdown("---")
    st.subheader("🤖 Thống Kê Xác Suất Thắng Theo Yếu Tố & Cơ Chế Bot Tự Cải Thiện")
    col_f1, col_f2 = st.columns([3, 2])

    with col_f1:
        st.markdown("#### 📊 Hiệu Quả Thực Tế Từng Chất Xúc Tác Doanh Nghiệp")
        factor_list = learning_engine.analyze_factors_effectiveness()
        if factor_list:
            df_fac = pd.DataFrame(factor_list)
            st.dataframe(style_table_colors(df_fac, target_columns=["Tỷ Lệ Thắng (Win Rate)", "LN Trung Bình", "Điều Chỉnh Trọng Số AI"]), use_container_width=True)
        else:
            st.info("Đang tích lũy thêm dữ liệu để tính toán thống kê chi tiết.")

    with col_f2:
        st.markdown("#### 💡 Đúc Kết Chiến Thuật Mà Bot Đã Tự Học")
        insights = learning_engine.get_actionable_insights()
        for ins in insights:
            st.markdown(f"- {ins}")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#141a24; border:1px solid #283347; border-left:4px solid #3b82f6; border-radius:8px; padding:12px;">
            <strong style="color:#60a5fa;">🔄 VÒNG LẶP TỰ HỌC HOẠT ĐỘNG LIÊN TỤC:</strong><br>
            <span style="color:#cbd5e1; font-size:0.85rem;">
            Sau mỗi phiên lúc 15:30, các mã thắng sẽ tăng điểm ưu tiên cho sự kiện tương ứng; các mã thua sẽ tự động kích hoạt bộ lọc phòng vệ để bot ngày càng chuẩn xác hơn theo thời gian.
            </span>
        </div>
        """, unsafe_allow_html=True)

elif page == "🔍 Bộ Lọc Định Lượng Chuyên Sâu":
    st.title("🔍 Bộ Lọc Cổ Phiếu Định Lượng Chuyên Sâu")
    st.caption("Lọc đa chiều theo sàn giao dịch, phân loại tín hiệu, thang điểm định lượng và rủi ro. Màu sắc trực quan: Tăng Xanh | Giảm Đỏ.")

    df_results = st.session_state.scan_results
    if df_results.empty:
        st.warning("Chưa có dữ liệu quét trong Database. Hãy chạy quét dữ liệu.")
    else:
        f1, f2, f3, f4 = st.columns(4)
        exchanges = ["Tất cả"] + sorted(list(df_results["exchange"].unique()))
        categories_vn = ["Tất cả"] + sorted(list(set([translate_category(c) for c in df_results["category"].unique()])))

        sel_exchange = f1.selectbox("Sàn Giao Dịch:", exchanges)
        sel_cat = f2.selectbox("Phân Loại Tín Hiệu:", categories_vn)
        min_score = f3.slider("Ngưỡng Điểm Định Lượng Tối Thiểu:", 0, 100, 45)
        sort_by_vn = f4.selectbox("Sắp Xếp Theo:", ["Điểm Định Lượng", "Thay Đổi Giá", "Tỷ Lệ Vol 20D", "Chỉ Số RSI", "Giá Đóng Cửa"])

        sort_map = {
            "Điểm Định Lượng": "rule_score", "Thay Đổi Giá": "price_change",
            "Tỷ Lệ Vol 20D": "volume_ratio", "Chỉ Số RSI": "rsi", "Giá Đóng Cửa": "close_price"
        }

        filtered = df_results.copy()
        filtered["Phân Loại"] = filtered["category"].apply(translate_category)

        if sel_exchange != "Tất cả": filtered = filtered[filtered["exchange"] == sel_exchange]
        if sel_cat != "Tất cả": filtered = filtered[filtered["Phân Loại"] == sel_cat]
        filtered = filtered[filtered["rule_score"] >= min_score]
        filtered = filtered.sort_values(sort_map[sort_by_vn], ascending=False)

        st.markdown(f"**Kết quả: Tìm thấy {len(filtered)} / {len(df_results)} cổ phiếu thỏa mãn tiêu chí lọc.**")

        disp_filtered = filtered.copy()
        disp_filtered["Mã CP"] = disp_filtered["symbol"]
        disp_filtered["Sàn"] = disp_filtered["exchange"]
        disp_filtered["Giá Đóng Cửa"] = disp_filtered["close_price"].apply(lambda x: f"{x:,.0f} đ")
        disp_filtered["Thay Đổi"] = disp_filtered["price_change"].apply(lambda x: f"{x:+.2f}%")
        disp_filtered["Xu Hướng"] = disp_filtered["trend"].apply(translate_trend)
        disp_filtered["Điểm Định Lượng"] = disp_filtered["rule_score"].apply(lambda x: f"{x:.1f}")
        disp_filtered["Khối Lượng TB 20D"] = disp_filtered["avg_volume_20d"].apply(lambda x: f"{x:,.0f}")
        disp_filtered["Tỷ Lệ Vol"] = disp_filtered["volume_ratio"].apply(lambda x: f"{x:.2f}x")
        disp_filtered["Bứt Phá (Breakout)"] = disp_filtered["breakout_status"].apply(translate_breakout)
        disp_filtered["Mức Rủi Ro"] = disp_filtered["risk_level"].apply(translate_risk_level)
        
        cols_final = ["Mã CP", "Sàn", "Giá Đóng Cửa", "Thay Đổi", "Xu Hướng", "Điểm Định Lượng", "Phân Loại", "rsi", "Tỷ Lệ Vol", "Bứt Phá (Breakout)", "Mức Rủi Ro"]
        st.dataframe(style_table_colors(disp_filtered[cols_final], target_columns=["Thay Đổi", "Xu Hướng"]), use_container_width=True, height=450)

        exporter = ReportExporter()
        if st.button("📥 Xuất Báo Cáo Sàng Lọc Ra CSV"):
            fpath = exporter.export_scan_results_csv(filtered)
            st.success(f"Đã xuất file thành công: {fpath}")

elif page == "📈 Phân Tích Kỹ Thuật Chi Tiết":
    st.title("📈 Phân Tích Kỹ Thuật Chi Tiết & Tin Tức")

    all_symbols = st.session_state.universe.get_all_symbols()
    col_sel, col_space = st.columns([1.5, 1.5])
    selected_sym = col_sel.selectbox(
        "Chọn Mã Cổ Phiếu Cần Phân Tích:",
        all_symbols,
        index=0,
        format_func=st.session_state.universe.get_symbol_display_label
    )

    if selected_sym:
        df_stock, warnings = scanner.downloader.fetch_symbol_data(selected_sym)

        if not df_stock.empty and len(df_stock) >= 20:
            df_stock = TechnicalFeatures.add_technical_indicators(df_stock)
            df_stock = MomentumFeatures.add_momentum_indicators(df_stock)
            df_stock = VolatilityFeatures.add_volatility_indicators(df_stock)
            df_stock = LiquidityFeatures.add_liquidity_indicators(df_stock)

            idx_df = scanner.downloader.fetch_market_index()
            t_info = TrendFollowingStrategy.evaluate_trend(df_stock)
            b_info = BreakoutStrategy.evaluate_breakout(df_stock)
            rs_info = RelativeStrengthStrategy.calculate_relative_strength(df_stock, idx_df)
            scores = scanner.scoring_engine.compute_scores(df_stock, rs_info, t_info, b_info)

            last = df_stock.iloc[-1]
            prev = df_stock.iloc[-2] if len(df_stock) > 1 else last
            chg = ((last["close"] - prev["close"]) / prev["close"]) * 100.0 if prev["close"] > 0 else 0.0

            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Giá Đóng Cửa", f"{last['close']:,.0f} đ", f"{chg:+.2f}%")
            m2.metric("Điểm Định Lượng", f"{scores['total_score']:.1f}/100", scores["total_score"] >= 70 and "Tích cực" or "Trung bình")
            m3.metric("Xu Hướng Kỹ Thuật", translate_trend(t_info["trend"]))
            m4.metric("RSI (14)", f"{last.get('rsi_14', 50.0):.1f}", 50 <= last.get('rsi_14', 50) <= 68 and "Vùng tăng khỏe" or "Cần theo dõi")
            m5.metric("Volume So Với TB", f"{last.get('volume_ratio', 1.0):.2f}x", f"TB 20D: {last.get('avg_volume_20d', 0):,.0f}")

            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2])
            fig.add_trace(go.Candlestick(x=df_stock["date"], open=df_stock["open"], high=df_stock["high"], low=df_stock["low"], close=df_stock["close"], name="Giá (Nến Nhật)", increasing_line_color="#10b981", decreasing_line_color="#ef4444"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_stock["date"], y=df_stock["sma_20"], line=dict(color="#3b82f6", width=1.5), name="SMA 20"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_stock["date"], y=df_stock["sma_50"], line=dict(color="#f59e0b", width=1.5), name="SMA 50"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_stock["date"], y=df_stock["sma_200"], line=dict(color="#8b5cf6", width=1.5), name="SMA 200"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_stock["date"], y=df_stock["bb_upper"], line=dict(color="#64748b", width=1, dash="dot"), name="Dải BB Trên"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_stock["date"], y=df_stock["bb_lower"], line=dict(color="#64748b", width=1, dash="dot"), name="Dải BB Dưới"), row=1, col=1)

            vol_colors = ["#10b981" if c >= o else "#ef4444" for c, o in zip(df_stock["close"], df_stock["open"])]
            fig.add_trace(go.Bar(x=df_stock["date"], y=df_stock["volume"], marker_color=vol_colors, name="Khối Lượng"), row=2, col=1)
            fig.add_trace(go.Scatter(x=df_stock["date"], y=df_stock["rsi_14"], line=dict(color="#ec4899", width=1.5), name="RSI (14)"), row=3, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="#ef4444", line_width=1, row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="#10b981", line_width=1, row=3, col=1)
            fig.update_layout(template="plotly_dark", height=650, xaxis_rangeslider_visible=False, margin=dict(l=20, r=20, t=30, b=20), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)

            passed_liq, liq_msg = LiquidityFeatures.check_liquidity_filter(df_stock)
            pos_factors, risk_factors, risk_level = SignalExplanations.generate_explanations(df_stock, t_info, b_info, rs_info, scores, passed_liq, liq_msg)

            col_pos, col_risk = st.columns(2)
            with col_pos:
                st.markdown("#### ✅ Luận Điểm Động Lực Tích Cực")
                if pos_factors:
                    for p in pos_factors: st.markdown(f"- 🟢 **{p}**")
                else: st.write("Chưa ghi nhận động lực bứt phá mạnh tại phiên này.")

            with col_risk:
                st.markdown("#### ⚠️ Yếu Tố Cảnh Báo & Rủi Ro")
                if risk_factors:
                    for r in risk_factors: st.markdown(f"- 🔴 **{r}**")
                else: st.write("Không phát hiện tín hiệu suy yếu hoặc quá mua nghiêm trọng.")

            st.markdown("---")
            st.subheader(f"📰 Tin Tức & Dòng Sự Kiện Liên Quan: {selected_sym}")
            st.caption("Nguồn cấp tin công khai qua RSS từ Google News và CafeF. Chỉ hiển thị metadata và đường dẫn bài viết gốc.")
            
            if st.button("🔄 Cập Nhật Tin Tức Mới Nhất", key=f"btn_news_{selected_sym}"):
                storage.replace_cached_news(selected_sym, [])

            news_items = news_provider.get_symbol_news(selected_sym, limit=8)
            if news_items:
                for item in news_items:
                    st.markdown(f"""
                    <div class="news-card">
                        <a href="{item['url']}" target="_blank" style="color:#60a5fa; font-weight:600; text-decoration:none; font-size:1rem;">{item['title']}</a><br>
                        <span style="color:#64748b; font-size:0.8rem;">🏢 Nguồn: {item['source']} | 🕒 {item['published_at']}</span><br>
                        <p style="color:#cbd5e1; font-size:0.88rem; margin-top:6px; margin-bottom:0;">{item.get('summary', '')}</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info(f"Chưa có tin tức RSS công khai mới cho mã {selected_sym}. Bạn có thể bấm nút Cập Nhật Tin Tức ở trên.")
        else:
            st.error(f"Dữ liệu lịch sử của mã {selected_sym} không đủ để vẽ biểu đồ.")

elif page == "💼 Danh Mục Paper Trading":
    st.title("💼 Danh Mục Giả Lập Paper Trading")
    st.caption("Môi trường giao dịch giả lập không sử dụng tiền thật. Kiểm thử hiệu quả của bot trước khi tích hợp API.")

    bal = paper_broker.get_account_balance()
    p1, p2, p3 = st.columns(3)
    p1.metric("Tiền Mặt Khả Dụng", f"{bal['cash']:,.0f} đ")
    p2.metric("Giá Trị Cổ Phiếu Nắm Giữ", f"{bal['portfolio_value']:,.0f} đ")
    p3.metric("Tổng Tài Sản Ròng (NAV)", f"{bal['total_equity']:,.0f} đ", f"{bal['total_equity'] - 100000000:+,.0f} đ")

    st.markdown("---")
    tab_pos, tab_order = st.tabs(["📊 Vị Thế Đang Nắm Giữ (Positions)", "📝 Đặt Lệnh Paper Thủ Công"])

    with tab_pos:
        positions = paper_broker.get_positions()
        if positions:
            pos_df = pd.DataFrame(positions)
            pos_df["Mã CP"] = pos_df["symbol"]
            pos_df["Khối Lượng"] = pos_df["quantity"]
            pos_df["Giá Mua TB"] = pos_df["avg_buy_price"].apply(lambda x: f"{x:,.0f} đ")
            pos_df["Giá Hiện Tại"] = pos_df["current_price"].apply(lambda x: f"{x:,.0f} đ")
            pos_df["Giá Trị"] = pos_df["market_value"].apply(lambda x: f"{x:,.0f} đ")
            pos_df["Lãi/Lỗ (PnL)"] = pos_df["unrealized_pnl"].apply(lambda x: f"{x:+,.0f} đ")
            pos_df["Tỷ Suất (%)"] = pos_df["unrealized_pnl_pct"].apply(lambda x: f"{x:+.2f}%")
            pos_df["Thời Điểm"] = pos_df["updated_at"]
            
            show_cols = ["Mã CP", "Khối Lượng", "Giá Mua TB", "Giá Hiện Tại", "Giá Trị", "Lãi/Lỗ (PnL)", "Tỷ Suất (%)", "Thời Điểm"]
            st.dataframe(style_table_colors(pos_df[show_cols], target_columns=["Lãi/Lỗ (PnL)", "Tỷ Suất (%)"]), use_container_width=True)
        else:
            st.info("Hiện tại chưa có vị thế cổ phiếu nào trong tài khoản Paper Trading.")

    with tab_order:
        st.subheader("Gửi Lệnh Giả Lập Mua/Bán (Paper Order)")
        o_sym = st.selectbox(
            "Chọn Mã Cổ Phiếu:",
            st.session_state.universe.get_all_symbols(),
            format_func=st.session_state.universe.get_symbol_display_label,
            key="order_sym"
        )
        o_side = st.selectbox("Chiều Lệnh:", ["BUY (Mua)", "SELL (Bán)"])
        o_qty = st.number_input("Số Lượng (Lô 100):", value=100, step=100)
        o_price = st.number_input("Mức Giá Đặt (VNĐ):", value=25000.0, step=100.0)

        clean_side = "BUY" if "BUY" in o_side else "SELL"
        if st.button("📤 Xác Nhận Gửi Lệnh Giả Lập", type="primary"):
            res = paper_broker.place_order(o_sym, clean_side, int(o_qty), float(o_price))
            st.success(f"Khớp lệnh thành công: {res['side']} {res['quantity']} {res['symbol']} tại giá {res['price']:,.0f} đ (Mã lệnh: {res['order_id']})")
            st.rerun()

elif page == "🎯 Kiểm Định AI & Backtest":
    st.title("🎯 Đánh Giá Mô Hình AI & Kiểm Định Lịch Sử (Backtest)")
    t_ai, t_bt = st.tabs(["🤖 Quản Trị & Kiểm Định Mô Hình AI", "📉 Backtest Chiến Lược"])

    with t_ai:
        st.subheader("Quy Chuẩn Quản Trị Mô Hình AI (Model Governance)")
        st.info("""
        **Nguyên tắc minh bạch & an toàn dữ liệu:**
        - Xác suất AI chỉ được hiển thị khi mô hình được huấn luyện trên dữ liệu thật hợp lệ và vượt qua Walk-Forward Validation.
        - Hệ thống từ chối áp dụng xác suất giả định khi chưa đủ dữ liệu kiểm định.
        """)
        reg = ModelRegistry()
        reg_info = [reg.get_model_info(h) for h in [5, 10, 20] if reg.get_model_info(h)]
        if reg_info:
            st.write("Thông tin các phiên bản mô hình đã lưu trong Registry:")
            st.json(reg_info)
        else:
            st.write("Chưa có mô hình nào trong Registry.")

    with t_bt:
        st.subheader("Mô Phỏng Giao Dịch Sự Kiện Lịch Sử (Event-driven Backtest)")
        col_c1, col_c2, col_c3 = st.columns(3)
        cap = col_c1.number_input("Vốn Giả Định (VNĐ):", value=100000000, step=10000000)
        hold = col_c2.slider("Thời Hạn Nắm Giữ (Phiên):", 5, 20, 10)
        thresh = col_c3.slider("Ngưỡng Điểm Vào Lệnh:", 40, 80, 55)

        if st.button("▶️ Chạy Mô Phỏng Backtest", type="primary"):
            with st.spinner("Đang chạy mô phỏng backtest trừ phí giao dịch & thuế..."):
                stock_dfs = scanner.downloader.fetch_universe_data()
                idx_df = scanner.downloader.fetch_market_index()
                engine = BacktestEngine(initial_capital=cap)
                bt_res = engine.run_backtest(stock_dfs, idx_df, holding_period=hold, score_threshold=thresh)

                m = bt_res["metrics"]
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Lợi Nhuận Ròng", f"{m['total_return_pct']}%")
                k2.metric("CAGR Năm", f"{m['cagr_pct']}%")
                k3.metric("Tỷ Lệ Thắng (Win Rate)", f"{m['win_rate_pct']}%")
                k4.metric("Chỉ Số Sharpe", f"{m['sharpe_ratio']}")

                eq_df = bt_res["equity_df"]
                if not eq_df.empty:
                    fig_eq = go.Figure()
                    fig_eq.add_trace(go.Scatter(x=eq_df["date"], y=eq_df["portfolio_value"], line=dict(color="#10b981", width=2), name="Tăng Trưởng Danh Mục"))
                    fig_eq.update_layout(template="plotly_dark", title="Đường Cong Tăng Trưởng Vốn (Equity Curve)", xaxis_title="Ngày", yaxis_title="VND")
                    st.plotly_chart(fig_eq, use_container_width=True)

elif page == "⭐ Danh Mục Theo Dõi (Watchlist)":
    st.title("⭐ Quản Lý Danh Mục Theo Dõi Cá Nhân (Watchlist)")

    w_symbols = storage.get_watchlist("Default")
    col_w1, col_w2, col_w3 = st.columns([2, 3, 1])
    add_s = col_w1.selectbox(
        "Chọn Mã Cổ Phiếu Thêm Vào:",
        st.session_state.universe.get_all_symbols(),
        format_func=st.session_state.universe.get_symbol_display_label
    )
    add_n = col_w2.text_input("Ghi Chú Cá Nhân:", placeholder="Ví dụ: Chờ test lại hỗ trợ...")
    if col_w3.button("➕ Thêm Mã"):
        storage.add_to_watchlist("Default", add_s, add_n)
        st.success(f"Đã thêm {add_s} vào Danh Mục Theo Dõi!")
        st.rerun()

    st.markdown("---")
    if w_symbols:
        st.write(f"Hiện có **{len(w_symbols)}** cổ phiếu trong Danh Mục Theo Dõi:")
        st.dataframe(pd.DataFrame({"Mã Cổ Phiếu": w_symbols}), use_container_width=True)

        rem_s = st.selectbox("Chọn Mã Cần Xóa Khỏi Watchlist:", w_symbols)
        if st.button("🗑️ Xóa Khỏi Danh Mục"):
            storage.remove_from_watchlist("Default", rem_s)
            st.success(f"Đã xóa {rem_s}!")
            st.rerun()
    else:
        st.info("Danh mục theo dõi đang trống. Hãy thêm mã cổ phiếu để tiện quan sát.")
