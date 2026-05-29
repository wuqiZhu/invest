# -*- coding: utf-8 -*-
"""
AI情绪分析模块
使用MiMo API对新闻进行深度情绪分析

功能：
- 单条新闻情绪分析
- 批量新闻情绪分析
- 市场情绪指数计算
- 行业情绪分析
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class AISentimentAnalyzer:
    """AI情绪分析器"""

    def __init__(self, api_key: str = None, api_base: str = None, model: str = None):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.api_base = api_base or os.environ.get("DEEPSEEK_BASE_URL", "https://api.xiaomimimo.com/v1")
        self.model = model or os.environ.get("DEEPSEEK_MODEL", "mimo-v2-flash")

    def analyze_single(self, title: str, content: str = "") -> Dict[str, Any]:
        """
        分析单条新闻情绪

        Args:
            title: 新闻标题
            content: 新闻内容（可选）

        Returns:
            {
                'sentiment': 'positive'/'negative'/'neutral',
                'score': float (-1 ~ 1),
                'confidence': float (0 ~ 1),
                'impact': 'high'/'medium'/'low',
                'reason': str,
                'keywords': list
            }
        """
        if not REQUESTS_AVAILABLE or not self.api_key:
            return self._fallback_analyze(title)

        prompt = f"""分析以下财经新闻的情绪倾向，返回JSON格式：

新闻标题：{title}
{f'新闻内容：{content[:500]}' if content else ''}

请返回以下格式的JSON：
{{
    "sentiment": "positive/negative/neutral",
    "score": -1到1之间的浮点数（正数表示正面，负数表示负面）,
    "confidence": 0到1之间的置信度,
    "impact": "high/medium/low"（对市场的影响程度）,
    "reason": "分析原因",
    "keywords": ["关键情绪词1", "关键情绪词2"]
}}

只返回JSON，不要其他内容。"""

        try:
            result = self._call_api(prompt)
            if result:
                return result
        except Exception as e:
            logger.error(f"AI情绪分析失败: {e}")

        return self._fallback_analyze(title)

    def analyze_batch(self, news_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量分析新闻情绪

        Args:
            news_items: 新闻列表，每个包含 title 和可选的 content

        Returns:
            {
                'total_count': int,
                'positive_count': int,
                'negative_count': int,
                'neutral_count': int,
                'avg_score': float,
                'sentiment_index': float (0~100),
                'items': list (带情绪标注的新闻)
            }
        """
        if not news_items:
            return self._empty_result()

        analyzed_items = []
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        total_score = 0

        for item in news_items:
            title = item.get('title', '')
            content = item.get('content', '')

            if not title:
                continue

            sentiment = self.analyze_single(title, content)
            analyzed_item = {
                **item,
                'ai_sentiment': sentiment['sentiment'],
                'ai_score': sentiment['score'],
                'ai_confidence': sentiment['confidence'],
                'ai_impact': sentiment['impact'],
                'ai_reason': sentiment['reason'],
            }
            analyzed_items.append(analyzed_item)

            if sentiment['sentiment'] == 'positive':
                positive_count += 1
            elif sentiment['sentiment'] == 'negative':
                negative_count += 1
            else:
                neutral_count += 1

            total_score += sentiment['score']

        total = len(analyzed_items)
        avg_score = total_score / total if total > 0 else 0

        sentiment_index = self._calculate_sentiment_index(
            positive_count, negative_count, neutral_count, total
        )

        return {
            'total_count': total,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'avg_score': round(avg_score, 4),
            'sentiment_index': round(sentiment_index, 2),
            'items': analyzed_items,
            'timestamp': datetime.now().isoformat(),
        }

    def calculate_market_index(self, news_items: List[Dict[str, Any]],
                                technical_score: float = 0.5,
                                momentum_score: float = 0.5) -> Dict[str, Any]:
        """
        计算市场情绪指数

        Args:
            news_items: 新闻列表
            technical_score: 技术指标得分 (0~1)
            momentum_score: 动量指标得分 (0~1)

        Returns:
            {
                'market_index': float (0~100),
                'level': '极度恐惧/恐惧/中性/贪婪/极度贪婪',
                'news_score': float,
                'technical_score': float,
                'momentum_score': float,
                'components': dict
            }
        """
        news_result = self.analyze_batch(news_items)
        news_score = (news_result['avg_score'] + 1) / 2

        market_index = (
            news_score * 0.4 +
            technical_score * 0.35 +
            momentum_score * 0.25
        ) * 100

        if market_index >= 80:
            level = '极度贪婪'
        elif market_index >= 60:
            level = '贪婪'
        elif market_index >= 40:
            level = '中性'
        elif market_index >= 20:
            level = '恐惧'
        else:
            level = '极度恐惧'

        return {
            'market_index': round(market_index, 2),
            'level': level,
            'news_score': round(news_score, 4),
            'technical_score': round(technical_score, 4),
            'momentum_score': round(momentum_score, 4),
            'components': {
                'positive_count': news_result['positive_count'],
                'negative_count': news_result['negative_count'],
                'neutral_count': news_result['neutral_count'],
            },
            'timestamp': datetime.now().isoformat(),
        }

    def _call_api(self, prompt: str) -> Optional[Dict]:
        """调用MiMo API"""
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": 0.3
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            return json.loads(content)
        except Exception as e:
            logger.error(f"API调用失败: {e}")
            return None

    def _fallback_analyze(self, title: str) -> Dict[str, Any]:
        """回退分析（关键词匹配）"""
        positive_keywords = ['利好', '上涨', '增长', '突破', '新高', '反弹', '牛市', '盈利']
        negative_keywords = ['利空', '下跌', '暴跌', '崩盘', '亏损', '风险', '熊市', '危机']

        pos_count = sum(1 for kw in positive_keywords if kw in title)
        neg_count = sum(1 for kw in negative_keywords if kw in title)

        if pos_count > neg_count:
            return {
                'sentiment': 'positive',
                'score': min(1.0, (pos_count - neg_count) * 0.3),
                'confidence': 0.5,
                'impact': 'medium',
                'reason': '关键词匹配',
                'keywords': [kw for kw in positive_keywords if kw in title]
            }
        elif neg_count > pos_count:
            return {
                'sentiment': 'negative',
                'score': max(-1.0, -(neg_count - pos_count) * 0.3),
                'confidence': 0.5,
                'impact': 'medium',
                'reason': '关键词匹配',
                'keywords': [kw for kw in negative_keywords if kw in title]
            }
        else:
            return {
                'sentiment': 'neutral',
                'score': 0.0,
                'confidence': 0.3,
                'impact': 'low',
                'reason': '无明显情绪倾向',
                'keywords': []
            }

    def _calculate_sentiment_index(self, positive: int, negative: int,
                                    neutral: int, total: int) -> float:
        """计算情绪指数 (0~100)"""
        if total == 0:
            return 50.0

        ratio = (positive - negative) / total
        index = (ratio + 1) * 50
        return max(0, min(100, index))

    def _empty_result(self) -> Dict[str, Any]:
        return {
            'total_count': 0,
            'positive_count': 0,
            'negative_count': 0,
            'neutral_count': 0,
            'avg_score': 0.0,
            'sentiment_index': 50.0,
            'items': [],
            'timestamp': datetime.now().isoformat(),
        }


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    analyzer = AISentimentAnalyzer()

    test_news = [
        {'title': '央行宣布降准50个基点，释放流动性'},
        {'title': '某科技公司股价暴跌30%，市值蒸发千亿'},
        {'title': 'A股三大指数小幅高开'},
    ]

    result = analyzer.analyze_batch(test_news)
    print(json.dumps(result, ensure_ascii=False, indent=2))
