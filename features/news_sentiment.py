"""
Event-Driven News Sentiment & Catalysts Analyzer for Vietnam Stock Market.
Detects major corporate catalysts:
1. TRÚNG THẦU & DỰ ÁN (Bidding, EPC, Construction, Infrastructure)
2. CỔ TỨC (Cash dividend, Bonus shares)
3. MỞ RỘNG KINH DOANH (New branches, CapEx, M&A, Export expansion)
4. KẾT QUẢ KINH DOANH (Surge in profit, Revenue growth)
5. GIAO DỊCH LÃNH ĐẠO (Insiders / Institutional buying)
6. TIÊU CỰC / BÁO ĐỘNG ĐỎ (Legal risk, Losses, Debt default, Margin cut, Investigation)
"""

from __future__ import annotations
import re
from typing import Dict, Any, List


class NewsAnalyzer:
    """Analyzes financial news articles, extracts catalysts, and computes news impact score."""

    # Catalyst taxonomy with weights (-10 to +10)
    POSITIVE_CATALYSTS = {
        "TRUNG_THAU": {
            "name": "Trúng Thầu / Dự Án Mới",
            "score": 10.0,
            "patterns": [
                r"trúng\s+thầu",
                r"thắng\s+thầu",
                r"ký\s+hợp\s+đồng",
                r"khởi\s+công\s+dự\s+án",
                r"triển\s+khai\s+dự\s+án",
                r"gói\s+thầu",
                r"tổng\s+thầu",
                r"dự\s+án\s+cầu\s+đường",
                r"đầu\s+tư\s+công",
                r"giải\s+ngân\s+đầu\s+tư\s+công",
            ]
        },
        "CO_TUC": {
            "name": "Chia Cổ Tức Khủng / Thưởng",
            "score": 8.0,
            "patterns": [
                r"trả\s+cổ\s+tức",
                r"chi\s+trả\s+cổ\s+tức",
                r"cổ\s+tức\s+tiền\s+mặt",
                r"cổ\s+tức\s+bằng\s+tiền",
                r"tạm\s+ứng\s+cổ\s+tức",
                r"thưởng\s+cổ\s+phiếu",
                r"phát\s+hành\s+tăng\s+vốn",
                r"ngày\s+giao\s+dịch\s+không\s+hưởng\s+quyền",
                r"chốt\s+danh\s+sách\s+cổ\s+đông",
            ]
        },
        "MO_RONG": {
            "name": "Mở Rộng Quy Mô / Chi Nhánh",
            "score": 7.0,
            "patterns": [
                r"mở\s+thêm\s+chi\s+nhánh",
                r"khai\s+trương\s+chi\s+nhánh",
                r"mở\s+rộng\s+mạng\s+lưới",
                r"nâng\s+công\s+suất",
                r"xây\s+dựng\s+nhà\s+máy",
                r"thâu\s+tóm",
                r"sáp\s+nhập",
                r"hợp\s+tác\s+chiến\s+lược",
                r"xuất\s+khẩu\s+sang",
                r"mở\s+rộng\s+thị\s+trường",
            ]
        },
        "KQKD_DOT_PHA": {
            "name": "KQKD Đột Phá / Lợi Nhuận Tăng Trưởng",
            "score": 9.0,
            "patterns": [
                r"lợi\s+nhuận\s+tăng\s+trưởng",
                r"lợi\s+nhuận\s+kỷ\s+lục",
                r"lãi\s+đột\s+biến",
                r"lãi\s+ròng\s+tăng",
                r"vượt\s+kế\s+hoạch\s+lợi\s+nhuận",
                r"doanh\s+thu\s+tăng\s+trưởng",
                r"doanh\s+thu\s+kỷ\s+lục",
                r"báo\s+lãi",
            ]
        },
        "MUA_VAO_NOI_BO": {
            "name": "Lãnh Đạo / Cổ Đông Lớn Gom Mua",
            "score": 6.0,
            "patterns": [
                r"chủ\s+tịch\s+đăng\s+ký\s+mua",
                r"lãnh\s+đạo\s+gom\s+mua",
                r"cổ\s+đông\s+lớn\s+mua\s+vào",
                r"khối\s+ngoại\s+gom\s+ròng",
                r"tự\s+doanh\s+mua\s+ròng",
            ]
        }
    }

    NEGATIVE_CATALYSTS = {
        "PHAP_LY_XU_PHAT": {
            "name": "Rủi Ro Pháp Lý / Bị Xử Phạt / Điều Tra",
            "score": -15.0,
            "patterns": [
                r"bị\s+xử\s+phạt",
                r"vi\s+phạm",
                r"bị\s+phạt\s+tiền",
                r"thanh\s+tra",
                r"điều\s+tra",
                r"khởi\s+tố",
                r"tạm\s+hoãn\s+xuất\s+cảnh",
                r"bắt\s+tạm\s+giam",
                r"hủy\s+niêm\s+yết",
                r"đình\s+chỉ\s+giao\s+dịch",
                r"cắt\s+margin",
                r"vào\s+diện\s+kiểm\s+soát",
                r"vào\s+diện\s+cảnh\s+báo",
            ]
        },
        "THUA_LO_NO_XAU": {
            "name": "Kinh Doanh Thua Lỗ / Vỡ Nợ",
            "score": -12.0,
            "patterns": [
                r"thua\s+lỗ",
                r"lỗ\s+ròng",
                r"lỗ\s+nặng",
                r"báo\s+lỗ",
                r"sụt\s+giảm\s+lợi\s+nhuận",
                r"chậm\s+trả\s+gốc\s+lãi",
                r"vỡ\s+nợ\s+trái\s+phiếu",
                r"nợ\s+xấu\s+tăng",
                r"chậm\s+nộp\s+báo\s+cáo",
            ]
        },
        "BAN_THAO_NOI_BO": {
            "name": "Lãnh Đạo / Cổ Đông Thoái Vốn Bán Tháo",
            "score": -7.0,
            "patterns": [
                r"chủ\s+tịch\s+bán\s+hết",
                r"lãnh\s+đạo\s+bán\s+tháo",
                r"cổ\s+đông\s+lớn\s+thoái\s+vốn",
                r"bị\s+bán\s+giải\s+chấp",
                r"call\s+margin",
            ]
        }
    }

    @classmethod
    def analyze_article(cls, title: str, summary: str = "") -> Dict[str, Any]:
        """Analyzes a single article text and identifies detected catalysts and sentiment score."""
        text = f"{title} {summary}".lower()

        detected_positives = []
        detected_negatives = []
        score = 0.0

        # Check Positive Catalysts
        for key, cat in cls.POSITIVE_CATALYSTS.items():
            for pat in cat["patterns"]:
                if re.search(pat, text, re.IGNORECASE):
                    detected_positives.append(cat["name"])
                    score += cat["score"]
                    break  # count category once per article

        # Check Negative Catalysts
        for key, cat in cls.NEGATIVE_CATALYSTS.items():
            for pat in cat["patterns"]:
                if re.search(pat, text, re.IGNORECASE):
                    detected_negatives.append(cat["name"])
                    score += cat["score"]
                    break

        sentiment = "NEUTRAL"
        if score >= 6.0:
            sentiment = "BULLISH"
        elif score <= -6.0:
            sentiment = "BEARISH"

        return {
            "score": score,
            "sentiment": sentiment,
            "positive_catalysts": list(set(detected_positives)),
            "negative_catalysts": list(set(detected_negatives)),
            "is_severe_negative": score <= -12.0
        }

    @classmethod
    def analyze_symbol_news(cls, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregates all recent news articles for a symbol and returns a consolidated catalyst report."""
        if not articles:
            return {
                "news_sentiment": "NEUTRAL",
                "news_score_adjustment": 0.0,
                "detected_catalysts": [],
                "negative_warnings": [],
                "has_fatal_news": False,
                "total_articles_analyzed": 0,
                "summary_reason": "Không ghi nhận tin tức sự kiện đột biến trong các bài báo gần đây."
            }

        total_score = 0.0
        all_positives = []
        all_negatives = []
        has_fatal_news = False
        analyzed_count = len(articles)

        for art in articles:
            analysis = cls.analyze_article(art.get("title", ""), art.get("summary", ""))
            total_score += analysis["score"]
            all_positives.extend(analysis["positive_catalysts"])
            all_negatives.extend(analysis["negative_catalysts"])
            if analysis["is_severe_negative"]:
                has_fatal_news = True

        # Cap adjustment between -20 and +15 to avoid news overpowering fundamentals
        clamped_score = max(-20.0, min(15.0, total_score))

        all_positives = list(set(all_positives))
        all_negatives = list(set(all_negatives))

        sentiment = "NEUTRAL"
        if clamped_score >= 8.0 and not has_fatal_news:
            sentiment = "BULLISH"
        elif clamped_score <= -8.0 or has_fatal_news:
            sentiment = "BEARISH"

        # Generate human-readable summary
        summary_parts = []
        if all_positives:
            summary_parts.append(f"Xuất hiện tin tức hỗ trợ mạnh: {', '.join(all_positives)}")
        if all_negatives:
            summary_parts.append(f"CẢNH BÁO TIN XẤU: {', '.join(all_negatives)}")
        if not summary_parts:
            summary_parts.append("Tin tức bình thường, không có sự kiện doanh nghiệp đột biến")

        return {
            "news_sentiment": sentiment,
            "news_score_adjustment": round(clamped_score, 1),
            "detected_catalysts": all_positives,
            "negative_warnings": all_negatives,
            "has_fatal_news": has_fatal_news,
            "total_articles_analyzed": analyzed_count,
            "summary_reason": "; ".join(summary_parts)
        }
