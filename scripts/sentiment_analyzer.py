# -*- coding: utf-8 -*-
"""
新闻情绪分析模块
接收 TrendRadar 推送的新闻数据，分析与基金投资相关的情绪

免责声明：
本工具仅供个人学习和研究使用，所展示的数据均来自第三方公开接口。
不构成任何投资建议，据此操作风险自担。
基金投资有风险，过往业绩不代表未来表现。
"""

import re
from datetime import datetime, timedelta
from collections import Counter


FINANCE_KEYWORDS = {
    'positive': [
        '利好', '上涨', '增长', '突破', '新高', '反弹', '回暖', '提振',
        '降准', '降息', '宽松', '刺激', '扶持', '减税', '红利', '牛市',
        '盈利', '分红', '回购', '增持', '流入', '加仓', '看涨', '超预期',
        '创新高', '放量', '企稳', '向好', '乐观', '复苏', '景气', '强势',
    ],
    'negative': [
        '利空', '下跌', '下滑', '暴跌', '崩盘', '亏损', '违约', '风险',
        '加息', '收紧', '制裁', '关税', '贸易战', '熊市', '赎回', '减持',
        '流出', '减仓', '看跌', '不及预期', '破位', '缩量', '疲软', '悲观',
        '衰退', '萧条', '爆雷', '清盘', '熔断', '踩踏', '恐慌', '危机',
    ],
}

MARKET_KEYWORDS = [
    'A股', '沪指', '深成指', '创业板', '科创板', '港股', '美股',
    '基金', 'ETF', '债券', '期货', '外汇', '黄金', '原油',
    '央行', '美联储', 'GDP', 'CPI', 'PMI', '利率', '汇率',
    '半导体', '新能源', '医药', '消费', '科技', '金融', '地产',
    '银行', '券商', '保险', '白酒', '军工', '光伏', '锂电',
]


class SentimentAnalyzer:
    """新闻情绪分析器"""

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        self._pos_patterns = [re.compile(re.escape(kw)) for kw in FINANCE_KEYWORDS['positive']]
        self._neg_patterns = [re.compile(re.escape(kw)) for kw in FINANCE_KEYWORDS['negative']]
        self._market_patterns = [re.compile(re.escape(kw)) for kw in MARKET_KEYWORDS]

    def analyze_news(self, news_items):
        """
        分析新闻列表的情绪

        Args:
            news_items: 新闻条目列表，每个包含 title 字段

        Returns:
            dict: {
                'total_count': int,
                'finance_count': int,
                'positive_count': int,
                'negative_count': int,
                'neutral_count': int,
                'sentiment_score': float (-1 ~ 1),
                'finance_score': float (-1 ~ 1),
                'top_keywords': list,
                'items': list (带情绪标注的条目),
            }
        """
        if not news_items:
            return self._empty_result()

        analyzed_items = []
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        finance_count = 0
        all_keywords = []

        for item in news_items:
            title = item.get('title', '')
            if not title:
                continue

            sentiment = self._analyze_single(title)
            is_finance = self._is_finance_related(title)

            analyzed_item = {
                **item,
                'sentiment': sentiment['label'],
                'sentiment_score': sentiment['score'],
                'is_finance': is_finance,
                'matched_keywords': sentiment['keywords'],
            }
            analyzed_items.append(analyzed_item)

            if sentiment['label'] == 'positive':
                positive_count += 1
            elif sentiment['label'] == 'negative':
                negative_count += 1
            else:
                neutral_count += 1

            if is_finance:
                finance_count += 1
                all_keywords.extend(sentiment['keywords'])

        total = len(analyzed_items)
        sentiment_score = (positive_count - negative_count) / total if total > 0 else 0
        finance_score = self._calculate_finance_score(analyzed_items)
        keyword_counts = Counter(all_keywords).most_common(10)

        return {
            'total_count': total,
            'finance_count': finance_count,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'sentiment_score': round(sentiment_score, 4),
            'finance_score': round(finance_score, 4),
            'top_keywords': [kw for kw, _ in keyword_counts],
            'items': analyzed_items,
        }

    def _analyze_single(self, text):
        pos_matches = [p.pattern for p in self._pos_patterns if p.search(text)]
        neg_matches = [p.pattern for p in self._neg_patterns if p.search(text)]

        pos_count = len(pos_matches)
        neg_count = len(neg_matches)

        if pos_count > neg_count:
            score = min(1.0, (pos_count - neg_count) * 0.3)
            return {'label': 'positive', 'score': round(score, 4), 'keywords': pos_matches}
        elif neg_count > pos_count:
            score = max(-1.0, -(neg_count - pos_count) * 0.3)
            return {'label': 'negative', 'score': round(score, 4), 'keywords': neg_matches}
        else:
            return {'label': 'neutral', 'score': 0.0, 'keywords': []}

    def _is_finance_related(self, text):
        return any(p.search(text) for p in self._market_patterns)

    def _calculate_finance_score(self, items):
        finance_items = [i for i in items if i['is_finance']]
        if not finance_items:
            return 0.0

        total_score = sum(i['sentiment_score'] for i in finance_items)
        return total_score / len(finance_items)

    def get_sentiment_trend(self, db_conn, fund_code=None, days=7):
        """
        获取情绪趋势

        Args:
            db_conn: 数据库连接
            fund_code: 基金代码（可选）
            days: 查询天数

        Returns:
            list: 每日情绪数据
        """
        cursor = db_conn.cursor()
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        if fund_code:
            cursor.execute('''
                SELECT date, sentiment_score, finance_score, positive_count,
                       negative_count, neutral_count, total_count
                FROM news_sentiment
                WHERE fund_code = ? AND date >= ?
                ORDER BY date
            ''', (fund_code, start_date))
        else:
            cursor.execute('''
                SELECT date, sentiment_score, finance_score, positive_count,
                       negative_count, neutral_count, total_count
                FROM news_sentiment
                WHERE date >= ?
                ORDER BY date
            ''', (start_date,))

        columns = ['date', 'sentiment_score', 'finance_score', 'positive_count',
                    'negative_count', 'neutral_count', 'total_count']
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def _empty_result(self):
        return {
            'total_count': 0,
            'finance_count': 0,
            'positive_count': 0,
            'negative_count': 0,
            'neutral_count': 0,
            'sentiment_score': 0.0,
            'finance_score': 0.0,
            'top_keywords': [],
            'items': [],
        }
