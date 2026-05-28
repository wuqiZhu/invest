# -*- coding: utf-8 -*-
"""
投资决策引擎
读取终端1的分析报告，结合历史知识和技术分析，生成投资决策

免责声明：
本工具仅供个人学习和研究使用，不构成任何投资建议。
据此操作风险自担。基金投资有风险，过往业绩不代表未来表现。
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config_manager import ConfigManager
from parallel_executor import ParallelExecutor

try:
    from knowledge_vector_db import KnowledgeVectorDB
    KB_AVAILABLE = True
except ImportError:
    KB_AVAILABLE = False

try:
    from fund_data_fetcher import FundDataFetcher
    from fund_analyzer import FundAnalyzer
    from trading_system import TradingSystem
    TECH_AVAILABLE = True
except ImportError:
    TECH_AVAILABLE = False


WEIGHT_SENTIMENT = 0.35
WEIGHT_TECHNICAL = 0.30
WEIGHT_HISTORY = 0.15
WEIGHT_KEYWORD = 0.20

BUY_THRESHOLD = 0.55
SELL_THRESHOLD = 0.45


class DecisionEngine:
    """投资决策引擎"""

    def __init__(self, config_path=None, data_dir=None):
        """
        初始化决策引擎

        Args:
            config_path: 配置文件路径
            data_dir: 数据目录路径
        """
        self.config = ConfigManager(config_path)
        self.executor = ParallelExecutor(data_dir)

        self.knowledge_db = None
        if KB_AVAILABLE:
            try:
                self.knowledge_db = KnowledgeVectorDB()
            except Exception:
                pass

        self.trading_system = None
        self.fetcher = None
        if TECH_AVAILABLE:
            try:
                self.fetcher = FundDataFetcher()
                analyzer = FundAnalyzer()
                self.trading_system = TradingSystem(self.config, analyzer)
            except Exception:
                pass

    def make_decision(self, analysis_report):
        """
        主决策流程

        Args:
            analysis_report: 分析报告数据（来自队列批次的 data 字段）

        Returns:
            dict: 决策结果
        """
        batch_id = analysis_report.get('batch_id', '')
        indicators = self._extract_indicators(analysis_report)

        fund_codes = self.config.get_fund_codes()
        if not fund_codes:
            fund_codes = ['110011']

        decisions = []
        for fund_code in fund_codes:
            fund_info = self.config.get_fund_info(fund_code) or {}
            fund_name = fund_info.get('name', fund_code)

            similar_cases = self._query_similar_cases(indicators)
            tech_signals = self._get_technical_signals(fund_code)

            fund_indicators = dict(indicators)
            momentum_data = self._calculate_momentum(fund_code)
            fund_indicators.update(momentum_data)

            decision_result = self._apply_decision_rules(
                fund_indicators, tech_signals, similar_cases
            )

            decision = {
                'batch_id': batch_id,
                'decision_id': f"dec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{fund_code}",
                'fund_code': fund_code,
                'fund_name': fund_name,
                'action': decision_result['action'],
                'confidence': decision_result['confidence'],
                'amount': self._calculate_amount(
                    decision_result['action'], decision_result['confidence'],
                    fund_info.get('monthly_invest', 200)
                ),
                'reason': decision_result['reason'],
                'factors': decision_result['factors'],
                'timestamp': datetime.now().isoformat()
            }
            decisions.append(decision)

        if len(decisions) == 1:
            return decisions[0]
        return {'batch_id': batch_id, 'decisions': decisions, 'timestamp': datetime.now().isoformat()}

    def _extract_indicators(self, report):
        sentiment_score = report.get('sentiment_score', 0.5)
        if isinstance(sentiment_score, str):
            try:
                sentiment_score = float(sentiment_score)
            except (ValueError, TypeError):
                sentiment_score = 0.5

        key_themes = report.get('key_themes', [])
        if isinstance(key_themes, str):
            key_themes = [t.strip() for t in key_themes.split(',') if t.strip()]

        alerts = report.get('alerts', [])
        news_count = report.get('news_count', 0)
        ai_summary = report.get('ai_summary', '')

        keyword_score = 0.5
        positive_keywords = ['利好', '上涨', '增长', '突破', '降准', '降息', '牛市', '反弹']
        negative_keywords = ['利空', '下跌', '暴跌', '崩盘', '风险', '危机', '恐慌']

        all_text = ' '.join(key_themes) + ' ' + ai_summary
        pos_count = sum(1 for kw in positive_keywords if kw in all_text)
        neg_count = sum(1 for kw in negative_keywords if kw in all_text)
        total = pos_count + neg_count
        if total > 0:
            keyword_score = pos_count / total

        return {
            'sentiment_score': sentiment_score,
            'key_themes': key_themes,
            'alerts': alerts,
            'news_count': news_count,
            'ai_summary': ai_summary,
            'keyword_score': keyword_score,
        }

    def _query_similar_cases(self, indicators):
        if not self.knowledge_db:
            return []

        try:
            query = ' '.join(indicators.get('key_themes', []))
            if not query:
                query = indicators.get('ai_summary', '')[:100]
            if not query:
                return []

            results = self.knowledge_db.search(query, n_results=3)
            return results
        except Exception:
            return []

    def _get_technical_signals(self, fund_code):
        if not self.trading_system or not self.fetcher:
            return {'signal': 'HOLD', 'available': False}

        try:
            fund_data = self.fetcher.get_fund_nav(fund_code, days=180)
            if fund_data is None or fund_data.empty:
                return {'signal': 'HOLD', 'available': False}

            result = self.trading_system.get_signal(fund_data, fund_code)
            return {
                'signal': result.get('signal', 'HOLD'),
                'modules': result.get('modules', {}),
                'available': True
            }
        except Exception:
            return {'signal': 'HOLD', 'available': False}

    def _calculate_momentum(self, fund_code):
        if not self.fetcher:
            return {'momentum_score': 0.5, 'volatility_score': 0.5}

        try:
            fund_data = self.fetcher.get_fund_nav(fund_code, days=60)
            if fund_data is None or fund_data.empty:
                return {'momentum_score': 0.5, 'volatility_score': 0.5}

            navs = fund_data['单位净值'].values
            if len(navs) < 10:
                return {'momentum_score': 0.5, 'volatility_score': 0.5}

            current = navs[-1]
            ma5 = navs[-5:].mean()
            ma10 = navs[-10:].mean()
            ma20 = navs[-20:].mean() if len(navs) >= 20 else navs.mean()

            momentum_score = 0.5
            if current > ma5 > ma10 > ma20:
                momentum_score = 0.8
            elif current > ma5 > ma10:
                momentum_score = 0.7
            elif current > ma5:
                momentum_score = 0.6
            elif current < ma5 < ma10 < ma20:
                momentum_score = 0.2
            elif current < ma5 < ma10:
                momentum_score = 0.3
            elif current < ma5:
                momentum_score = 0.4

            returns = [(navs[i] - navs[i-1]) / navs[i-1] for i in range(1, len(navs))]
            volatility = (sum(r**2 for r in returns) / len(returns)) ** 0.5

            volatility_score = 0.5
            if volatility < 0.005:
                volatility_score = 0.7
            elif volatility < 0.01:
                volatility_score = 0.6
            elif volatility > 0.03:
                volatility_score = 0.3
            elif volatility > 0.02:
                volatility_score = 0.4

            return {
                'momentum_score': momentum_score,
                'volatility_score': volatility_score
            }
        except Exception:
            return {'momentum_score': 0.5, 'volatility_score': 0.5}

    def _apply_decision_rules(self, indicators, tech_signals, similar_cases):
        sentiment = indicators.get('sentiment_score', 0.5)
        keyword = indicators.get('keyword_score', 0.5)

        tech_score = 0.5
        tech_signal = tech_signals.get('signal', 'HOLD')
        if tech_signal == 'BUY':
            tech_score = 0.8
        elif tech_signal == 'SELL':
            tech_score = 0.2

        momentum_score = indicators.get('momentum_score', 0.5)
        volatility_score = indicators.get('volatility_score', 0.5)

        history_score = 0.5
        historical_match = False
        if similar_cases:
            historical_match = True
            profits = []
            for case in similar_cases:
                meta = case.get('metadata', {})
                if 'profit' in meta:
                    try:
                        profits.append(float(meta['profit']))
                    except (ValueError, TypeError):
                        pass
            if profits:
                avg_profit = sum(profits) / len(profits)
                history_score = min(max(0.5 + avg_profit * 5, 0), 1)

        composite = (
            sentiment * 0.25 +
            tech_score * 0.25 +
            momentum_score * 0.20 +
            volatility_score * 0.10 +
            history_score * 0.10 +
            keyword * 0.10
        )

        if composite > BUY_THRESHOLD:
            action = 'buy'
            confidence = composite
        elif composite < SELL_THRESHOLD:
            action = 'sell'
            confidence = 1 - composite
        else:
            action = 'hold'
            confidence = 0.5

        reason_parts = [f'情绪指数={sentiment:.2f}']
        if tech_signals.get('available'):
            reason_parts.append(f'技术信号={tech_signal}')
        if indicators.get('key_themes'):
            reason_parts.append(f'关键主题={indicators["key_themes"]}')

        return {
            'action': action,
            'confidence': round(confidence, 4),
            'reason': ', '.join(reason_parts),
            'factors': {
                'sentiment_score': round(sentiment, 4),
                'technical_score': round(tech_score, 4),
                'technical_signal': tech_signal,
                'history_score': round(history_score, 4),
                'historical_match': historical_match,
                'keyword_score': round(keyword, 4),
                'composite_score': round(composite, 4),
            }
        }

    def _calculate_amount(self, action, confidence, base_amount):
        if action == 'hold':
            return 0

        if confidence > 0.85:
            return base_amount * 1.5
        elif confidence > 0.75:
            return base_amount * 1.2
        else:
            return base_amount

    def process_next_batch(self):
        batch = self.executor.get_next_batch(status='analyzed')
        if batch is None:
            return None

        batch_id = batch.get('batch_id')
        analysis_data = batch.get('data', {})
        analysis_data['batch_id'] = batch_id

        decision = self.make_decision(analysis_data)
        self.executor.update_batch_status(batch_id, 'decided', {'decision': decision})

        return decision


def main():
    import argparse

    parser = argparse.ArgumentParser(description='投资决策引擎')
    parser.add_argument('--config', help='配置文件路径')
    parser.add_argument('--data-dir', help='数据目录路径')
    parser.add_argument('--process', action='store_true', help='处理下一个待决策批次')
    parser.add_argument('--test', action='store_true', help='使用测试数据运行')

    args = parser.parse_args()
    engine = DecisionEngine(args.config, args.data_dir)

    if args.process:
        result = engine.process_next_batch()
        if result:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("没有待处理的批次")

    elif args.test:
        test_report = {
            'batch_id': 'test_001',
            'news_count': 150,
            'sentiment_score': 0.72,
            'key_themes': ['央行降准', '半导体上涨', '消费回暖'],
            'ai_summary': '央行宣布降准0.5个百分点，释放长期资金约1万亿元，半导体板块领涨',
            'alerts': []
        }
        decision = engine.make_decision(test_report)
        print(json.dumps(decision, ensure_ascii=False, indent=2))

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
