import os
import yaml
import unicodedata
from pathlib import Path
from typing import List, Dict, Any, Optional


def normalize_vietnamese_text(text: str) -> str:
    """Chuan hoa chuoi tieng Viet: bo dau tieng Viet, chuyen ve chu thuong, loai bo khoang trang thua."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(text))
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    return no_accents.replace("đ", "d").replace("Đ", "d").strip().lower()


COMMON_BRAND_ALIASES: Dict[str, str] = {
    "vietcombank": "VCB",
    "vcb": "VCB",
    "ngoai thuong": "VCB",
    "techcombank": "TCB",
    "tcb": "TCB",
    "ky thuong": "TCB",
    "vpbank": "VPB",
    "vp bank": "VPB",
    "vpb": "VPB",
    "viet nam thinh vuong": "VPB",
    "mbbank": "MBB",
    "mb bank": "MBB",
    "mbb": "MBB",
    "quan doi": "MBB",
    "tpbank": "TPB",
    "tp bank": "TPB",
    "tpb": "TPB",
    "tien phong": "TPB",
    "tien phong bank": "TPB",
    "vietinbank": "CTG",
    "vietin bank": "CTG",
    "ctg": "CTG",
    "cong thuong": "CTG",
    "bidv": "BID",
    "bid": "BID",
    "dau tu va phat trien": "BID",
    "acb": "ACB",
    "a chau": "ACB",
    "sacombank": "STB",
    "sacom bank": "STB",
    "stb": "STB",
    "sai gon thuong tin": "STB",
    "shb": "SHB",
    "shbank": "SHB",
    "vib": "VIB",
    "vibank": "VIB",
    "seabank": "SSB",
    "lpbank": "LPB",
    "lienvietpostbank": "LPB",
    "hdbank": "HDB",
    "hd bank": "HDB",
    "msb": "MSB",
    "hang hai": "MSB",
    "hoa phat": "HPG",
    "hpg": "HPG",
    "fpt": "FPT",
    "the gioi di dong": "MWG",
    "tgdd": "MWG",
    "dien may xanh": "MWG",
    "mwg": "MWG",
    "vinamilk": "VNM",
    "vnm": "VNM",
    "sua viet nam": "VNM",
    "vinhomes": "VHM",
    "vhm": "VHM",
    "vingroup": "VIC",
    "vic": "VIC",
    "vincom": "VRE",
    "vincom retail": "VRE",
    "vre": "VRE",
    "pv gas": "GAS",
    "pvgas": "GAS",
    "gas": "GAS",
    "khi viet nam": "GAS",
    "petrolimex": "PLX",
    "plx": "PLX",
    "xang dau": "PLX",
    "binh son": "BSR",
    "bsr": "BSR",
    "loc hoa dau binh son": "BSR",
    "vndirect": "VND",
    "vnd": "VND",
    "ssi": "SSI",
    "chung khoan ssi": "SSI",
    "vietcap": "VCI",
    "ban viet": "VCI",
    "vci": "VCI",
    "hsc": "HCM",
    "hcm": "HCM",
    "chung khoan tphcm": "HCM",
    "duc giang": "DGC",
    "dgc": "DGC",
    "hoa chat duc giang": "DGC",
    "pnj": "PNJ",
    "phu nhuan": "PNJ",
    "vang bac da quy phu nhuan": "PNJ",
}


class StockUniverse:
    """Manages stock universe, exchanges, sectors and indices with in-memory caching and fast smart search."""

    _CACHE: Optional[Dict[str, Any]] = None
    _CACHE_MTIME: float = 0.0

    def __init__(self, config_path: str = "config/universe.yaml"):
        self.config_path = Path(config_path)
        self.stocks: List[Dict[str, Any]] = []
        self.indices: List[Dict[str, Any]] = []
        self._stock_by_symbol: Dict[str, Dict[str, Any]] = {}
        self._symbols_cache: List[str] = []
        self._display_map: Dict[str, str] = {}
        self._search_tuples: List[tuple] = []
        self.load_universe()

    def load_universe(self):
        if self.config_path.exists():
            mtime = os.path.getmtime(self.config_path)
            if StockUniverse._CACHE is None or StockUniverse._CACHE_MTIME != mtime:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    StockUniverse._CACHE = yaml.safe_load(f) or {}
                StockUniverse._CACHE_MTIME = mtime

            data = StockUniverse._CACHE or {}
            self.stocks = data.get("stocks", [])
            self.indices = data.get("indices", [])
        else:
            self.stocks = []
            self.indices = []

        self._rebuild_indices()

    def _rebuild_indices(self):
        self._stock_by_symbol = {s["symbol"].upper(): s for s in self.stocks}
        self._symbols_cache = [s["symbol"] for s in self.stocks]
        self._display_map = {
            s["symbol"]: f"{s['symbol']} — {s.get('name', '')}" if s.get("name") else s["symbol"]
            for s in self.stocks
        }
        # Precomputed search tuples: (symbol, norm_sym, norm_name, full_norm, exchange)
        self._search_tuples = []
        for s in self.stocks:
            sym = s["symbol"].upper()
            name = s.get("name", "")
            norm_name = normalize_vietnamese_text(name)
            norm_sym = sym.lower()
            ex = s.get("exchange", "HOSE").upper()
            self._search_tuples.append((sym, norm_sym, norm_name, f"{norm_sym} {norm_name}", ex))

    def get_all_symbols(self) -> List[str]:
        return self._symbols_cache

    def get_symbols_by_exchange(self, exchange: str) -> List[str]:
        ex_upper = exchange.upper()
        return [s["symbol"] for s in self.stocks if s.get("exchange", "").upper() == ex_upper]

    def get_symbols_by_sector(self, sector: str) -> List[str]:
        sec_lower = sector.lower()
        return [s["symbol"] for s in self.stocks if s.get("sector", "").lower() == sec_lower]

    def get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        return self._stock_by_symbol.get(symbol.upper())

    def get_sectors(self) -> List[str]:
        return sorted(list(set(s.get("sector", "Other") for s in self.stocks)))

    def get_exchanges(self) -> List[str]:
        return sorted(list(set(s.get("exchange", "HOSE") for s in self.stocks)))

    def add_symbol(self, symbol: str, exchange: str = "HOSE", sector: str = "Other", name: str = ""):
        symbol = symbol.upper()
        if not self.get_stock_info(symbol):
            item = {"symbol": symbol, "exchange": exchange, "sector": sector, "name": name}
            self.stocks.append(item)
            self._rebuild_indices()

    def get_symbol_display_label(self, symbol: str) -> str:
        sym_upper = str(symbol or "").upper()
        return self._display_map.get(sym_upper, sym_upper)

    def get_display_map(self) -> Dict[str, str]:
        return self._display_map

    def find_matching_symbol(self, query: str) -> Optional[str]:
        """Smart, zero-latency stock search supporting exact ticker, prefixes, and unaccented Vietnamese company names."""
        if not query:
            return None
        clean_q = query.strip().upper()
        # 1. Exact uppercase symbol match (O(1))
        if clean_q in self._stock_by_symbol:
            return clean_q

        norm_q = normalize_vietnamese_text(query)
        if not norm_q:
            return None

        # 2. Fast alias lookup (O(1))
        if norm_q in COMMON_BRAND_ALIASES:
            alias_sym = COMMON_BRAND_ALIASES[norm_q]
            if alias_sym in self._stock_by_symbol:
                return alias_sym

        # 3. Fuzzy / substring / acronym scoring match
        candidates = []
        for sym, norm_sym, norm_name, full_norm, ex in self._search_tuples:
            score = 0
            if norm_sym == norm_q:
                score = 1000
            elif norm_sym.startswith(norm_q):
                score = 600 - len(norm_sym)
            elif norm_q in norm_sym:
                score = 400
            elif norm_q in norm_name:
                score = 250
                if norm_sym.startswith(norm_q[0]):
                    score += 80
                if f" {norm_q} " in f" {norm_name} " or norm_name.startswith(norm_q) or norm_name.endswith(norm_q):
                    score += 50
                if "tap doan" in norm_name or "tong cong ty" in norm_name:
                    score += 40
                if ex == "HOSE":
                    score += 30
                elif ex == "HNX":
                    score += 15
            elif norm_q in full_norm:
                score = 150

            if score > 0:
                candidates.append((score, sym))

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][1]

        return None
