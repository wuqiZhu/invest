# -*- coding: utf-8 -*-
"""
市场预测模块
综合情绪、技术、动量等多维度指标进行市场预测

功能：
- 市场情绪指数计算
- 多维度预测
- 趋势判断
- 预测报告生成
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class MarketPredictor:
    """市场预测器"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.ai_analyzer = None
        self.sentiment_analyzer = None

    def _init_analyzers(self):
        """初始化分析器"""
        if not self.ai_analyzer:
            try:
                from ai_sentiment_analyzer import AISentimentAnalyzer
                self.ai_analyzer = AISentimentAnalyzer()
            except ImportError:
                logger.warning("AI情绪分析器不可用")

        if not self.sentiment_analyzer:
            try:
                from sentiment_analyzer import SentimentAnalyzer
                self.sentiment_analyzer = SentimentAnalyzer()
            except ImportError:
                logger.warning("情绪分析器不可用")

    def predict_market(self, news_items: List[Dict[str, Any]],
                       fund_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        综合预测市场走势

        Args:
            news_items: 新闻列表
            fund_data: 基金数据（包含技术指标）

        Returns:
            {
                'prediction': 'bullish'/'bearish'/'neutral',
                'confidence': float (0~1),
                'market_index': float (0~100),
                'level': str,
                'factors': dict,
                'recommendation': str,
                'timestamp': str
            }
        """
        self._init_analyzers()

        sentiment_result = self._analyze_sentiment(news_items)
        technical_result = self._analyze_technical(fund_data)
        momentum_result = self._analyze_momentum(fund_data)

        market_index = self._calculate_market_index(
            sentiment_result, technical_result, momentum_result
        )

        prediction = self._make_prediction(market_index, sentiment_result, technical_result)
        recommendation = self._generate_recommendation(prediction, market_index)

        return {
            'prediction': prediction['direction'],
            'confidence': prediction['confidence'],
            'market_index': market_index['value'],
            'level': market_index['level'],
            'factors': {
                'sentiment': sentiment_result,
                'technical': technical_result,
                'momentum': momentum_result,
            },
            'recommendation': recommendation,
            'timestamp': datetime.now().isoformat(),
        }

    def _analyze_sentiment(self, news_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析情绪"""
        if not news_items:
            return {'score': 0.5, 'index': 50, 'count': 0}

        if self.ai_analyzer:
            result = self.ai_analyzer.analyze_batch(news_items)
            return {
                'score': (result['avg_score'] + 1) / 2,
                'index': result['sentiment_index'],
                'positive': result['positive_count'],
                'negative': result['negative_count'],
                'neutral': result['neutral_count'],
                'count': result['total_count'],
            }

        if self.sentiment_analyzer:
            result = self.sentiment_analyzer.analyze_batch(news_items)
            return {
                'score': result['positive_ratio'],
                'index': result['sentiment_index'],
                'positive': result['positive_count'],
                'negative': result['negative_count'],
                'neutral': result['neutral_count'],
                'count': result['total_count'],
            }

        return {'score': 0.5, 'index': 50, 'count': len(news_items)}

    def _analyze_technical(self, fund_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析技术指标"""
        if not fund_data:
            return {'score': 0.5, 'signals': []}

        signals = []
        score = 0.5

        nav_trend = fund_data.get('nav_trend', '')
        if nav_trend == 'rising':
            score += 0.1
            signals.append('净值上升趋势')
        elif nav_trend == 'falling':
            score -= 0.1
            signals.append('净值下降趋势')

        deviation = fund_data.get('deviation', 0)
        if deviation < -5:
            score += 0.15
            signals.append(f'偏离均线{deviation}%，可能超卖')
        elif deviation > 10:
            score -= 0.1
            signals.append(f'偏离均线{deviation}%，可能超买')

        macd = fund_data.get('macd', {})
        if macd.get('signal') == 'golden_cross':
            score += 0.1
            signals.append('MACD金叉')
        elif macd.get('signal') == 'death_cross':
            score -= 0.1
            signals.append('MACD死叉')

        score = max(0, min(1, score))

        return {
            'score': round(score, 4),
            'signals': signals,
        }

    def _analyze_momentum(self, fund_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析动量指标"""
        if not fund_data:
            return {'score': 0.5, 'signals': []}

        signals = []
        score = 0.5

        week_return = fund_data.get('week_return', 0)
        month_return = fund_data.get('month_return', 0)

        if week_return > 2:
            score += 0.1
            signals.append(f'周涨幅{week_return}%')
        elif week_return < -2:
            score -= 0.1
            signals.append(f'周跌幅{week_return}%')

        if month_return > 5:
            score += 0.15
            signals.append(f'月涨幅{month_return}%')
        elif month_return < -5:
            score -= 0.15
            signals.append(f'月跌幅{month_return}%')

        volatility = fund_data.get('volatility', 0)
        if volatility > 20:
            score -= 0.05
            signals.append(f'波动率较高{volatility}%')

        score = max(0, min(1, score))

        return {
            'score': round(score, 4),
            'signals': signals,
        }

    def _calculate_market_index(self, sentiment: Dict, technical: Dict,
                                 momentum: Dict) -> Dict[str, Any]:
        """计算市场情绪指数"""
        sentiment_weight = 0.4
        technical_weight = 0.35
        momentum_weight = 0.25

        index = (
            sentiment['score'] * sentiment_weight +
            technical['score'] * technical_weight +
            momentum['score'] * momentum_weight
        ) * 100

        index = max(0, min(100, index))

        if index >= 80:
            level = '极度贪婪'
        elif index >= 60:
            level = '贪婪'
        elif index >= 40:
            level = '中性'
        elif index >= 20:
            level = '恐惧'
        else:
            level = '极度恐惧'

        return {
            'value': round(index, 2),
            'level': level,
            'components': {
                'sentiment': round(sentiment['score'] * 100, 2),
                'technical': round(technical['score'] * 100, 2),
                'momentum': round(momentum['score'] * 100, 2),
            }
        }

    def _make_prediction(self, market_index: Dict, sentiment: Dict,
                          technical: Dict) -> Dict[str, Any]:
        """生成预测"""
        index = market_index['value']

        if index >= 65:
            direction = 'bullish'
            confidence = min(0.9, (index - 50) / 50)
        elif index <= 35:
            direction = 'bearish'
            confidence = min(0.9, (50 - index) / 50)
        else:
            direction = 'neutral'
            confidence = 0.5

        if sentiment['score'] > 0.6 and technical['score'] > 0.6:
            direction = 'bullish'
            confidence = max(confidence, 0.7)
        elif sentiment['score'] < 0.4 and technical['score'] < 0.4:
            direction = 'bearish'
            confidence = max(confidence, 0.7)

        return {
            'direction': direction,
            'confidence': round(confidence, 4),
        }

    def _generate_recommendation(self, prediction: Dict,
                                  market_index: Dict) -> str:
        """生成建议"""
        direction = prediction['direction']
        confidence = prediction['confidence']
        level = market_index['level']

        if direction == 'bullish':
            if confidence > 0.7:
                return f'市场情绪{level}，多项指标看涨，建议适当加仓'
            else:
                return f'市场情绪{level}，有上涨趋势，建议持有观望'
        elif direction == 'bearish':
            if confidence > 0.7:
                return f'市场情绪{level}，多项指标看跌，建议减仓或观望'
            else:
                return f'市场情绪{level}，有下跌风险，建议谨慎操作'
        else:
            return f'市场情绪{level}，方向不明确，建议保持现有仓位'

    def generate_report(self, prediction_result: Dict[str, Any]) -> str:
        """生成预测报告"""
        report = []
        report.append("=" * 50)
        report.append("市场预测报告")
        report.append("=" * 50)
        report.append(f"时间: {prediction_result['timestamp']}")
        report.append("")

        report.append(f"预测方向: {prediction_result['prediction']}")
        report.append(f"置信度: {prediction_result['confidence']*100:.1f}%")
        report.append(f"市场情绪指数: {prediction_result['market_index']}")
        report.append(f"情绪等级: {prediction_result['level']}")
        report.append("")

        report.append("建议:")
        report.append(prediction_result['recommendation'])
        report.append("")

        factors = prediction_result.get('factors', {})
        if factors:
            report.append("分析因素:")
            sentiment = factors.get('sentiment', {})
            if sentiment:
                report.append(f"  情绪得分: {sentiment.get('score', 'N/A')}")
                report.append(f"  正面新闻: {sentiment.get('positive', 0)}")
                report.append(f"  负面新闻: {sentiment.get('negative', 0)}")

        report.append("=" * 50)

        return "\n".join(report)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    predictor = MarketPredictor()

    test_news = [
        {'title': '央行宣布降准50个基点，释放流动性'},
        {'title': 'A股三大指数集体上涨，成交量放大'},
        {'title': '某科技公司发布新品，市场反应积极'},
    ]

    result = predictor.predict_market(test_news)
    print(predictor.generate_report(result))
