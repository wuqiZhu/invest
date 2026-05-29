# -*- coding: utf-8 -*-
"""
决策历史存储模块

设计目标：
1. 记录每次决策的完整上下文（市场环境、因子得分、技术指标）
2. 支持按时间、基金、决策类型等多维度查询
3. 提供决策效果分析和模式识别
4. 为参数优化和策略调整提供数据支持

存储结构：
- decisions/YYYY-MM.json: 按月分库，避免单文件过大
- analysis/monthly_report.json: 月度分析报告
- patterns/learned_patterns.json: 识别出的决策模式
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / 'data' / 'decision_history'


@dataclass
class MarketContext:
    """市场环境上下文"""
    date: str                          # 日期
    market_trend: str = "neutral"      # 市场趋势: bull/bear/neutral/volatile
    volatility_index: float = 0.0      # 波动率指数
    sentiment_score: float = 0.5       # 市场情绪得分 (0-1)
    news_keywords: List[str] = None    # 相关新闻关键词
    sector_performance: Dict[str, float] = None  # 板块表现

    def __post_init__(self):
        if self.news_keywords is None:
            self.news_keywords = []
        if self.sector_performance is None:
            self.sector_performance = {}


@dataclass
class FactorScores:
    """决策因子得分"""
    sentiment: float = 0.5             # 情绪因子 (0-1)
    technical: float = 0.5             # 技术因子 (0-1)
    multi_timeframe: float = 0.5       # 多时间框架因子 (0-1)
    momentum: float = 0.5              # 动量因子 (0-1)
    volatility: float = 0.5            # 波动率因子 (0-1)
    history: float = 0.5               # 历史匹配因子 (0-1)
    keyword: float = 0.5               # 关键词因子 (0-1)
    composite: float = 0.5             # 综合得分 (0-1)

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class TechnicalIndicators:
    """技术指标"""
    ma5: float = 0.0                   # 5日均线
    ma10: float = 0.0                  # 10日均线
    ma20: float = 0.0                  # 20日均线
    rsi: float = 50.0                  # RSI指标
    macd: float = 0.0                  # MACD
    bollinger_upper: float = 0.0       # 布林带上轨
    bollinger_lower: float = 0.0       # 布林带上轨
    current_nav: float = 0.0           # 当前净值

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class DecisionRecord:
    """决策记录"""
    decision_id: str                   # 决策ID
    timestamp: str                     # 决策时间
    fund_code: str                     # 基金代码
    fund_name: str                     # 基金名称
    action: str                        # 决策动作: buy/sell/hold
    confidence: float                  # 置信度 (0-1)
    amount: float                      # 决策金额
    reason: str                        # 决策原因

    # 决策上下文
    market_context: MarketContext       # 市场环境
    factor_scores: FactorScores        # 因子得分
    technical_indicators: TechnicalIndicators  # 技术指标

    # 决策参数
    buy_threshold: float = 0.58        # 买入阈值
    sell_threshold: float = 0.42       # 卖出阈值

    # 执行结果（待填充）
    result: Dict[str, Any] = None

    def __post_init__(self):
        if self.result is None:
            self.result = {
                'status': 'pending',
                'profit_rate': None,
                'hold_days': None,
                'executed_at': None,
                'completed_at': None
            }


class DecisionHistory:
    """决策历史管理器"""

    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 创建子目录
        (self.data_dir / 'decisions').mkdir(exist_ok=True)
        (self.data_dir / 'analysis').mkdir(exist_ok=True)
        (self.data_dir / 'patterns').mkdir(exist_ok=True)

    def _get_month_file(self, date_str: str = None) -> Path:
        """获取按月分库的文件路径"""
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        month_key = date_str[:7]  # YYYY-MM
        return self.data_dir / 'decisions' / f'{month_key}.json'

    def _load_month_data(self, date_str: str = None) -> List[Dict]:
        """加载某月的决策数据"""
        file_path = self._get_month_file(date_str)
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载决策数据失败: {e}")
        return []

    def _save_month_data(self, decisions: List[Dict], date_str: str = None):
        """保存某月的决策数据"""
        file_path = self._get_month_file(date_str)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(decisions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存决策数据失败: {e}")

    def save_decision(self, record: DecisionRecord) -> str:
        """保存决策记录"""
        decisions = self._load_month_data(record.timestamp)
        decisions.append(asdict(record))
        self._save_month_data(decisions, record.timestamp)
        logger.info(f"决策已保存: {record.decision_id}")
        return record.decision_id

    def update_result(self, decision_id: str, profit_rate: float, hold_days: int):
        """更新决策结果"""
        # 遍历所有月份文件查找决策
        for month_file in (self.data_dir / 'decisions').glob('*.json'):
            decisions = self._load_month_data(month_file.stem + '-01')
            for decision in decisions:
                if decision.get('decision_id') == decision_id:
                    decision['result'] = {
                        'status': 'completed',
                        'profit_rate': profit_rate,
                        'hold_days': hold_days,
                        'completed_at': datetime.now().isoformat()
                    }
                    self._save_month_data(decisions, month_file.stem + '-01')
                    logger.info(f"决策结果已更新: {decision_id}")
                    return True
        logger.warning(f"未找到决策: {decision_id}")
        return False

    def get_decisions(self, start_date: str = None, end_date: str = None,
                      fund_code: str = None, action: str = None) -> List[Dict]:
        """查询决策记录"""
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        # 确定需要查询的月份
        start_month = start_date[:7]
        end_month = end_date[:7]

        all_decisions = []
        current_month = start_month
        while current_month <= end_month:
            decisions = self._load_month_data(current_month + '-01')
            all_decisions.extend(decisions)
            # 移动到下一个月
            year, month = map(int, current_month.split('-'))
            if month == 12:
                current_month = f"{year + 1}-01"
            else:
                current_month = f"{year}-{month + 1:02d}"

        # 过滤
        filtered = []
        for d in all_decisions:
            if d.get('timestamp', '') < start_date:
                continue
            if d.get('timestamp', '') > end_date + 'T23:59:59':
                continue
            if fund_code and d.get('fund_code') != fund_code:
                continue
            if action and d.get('action') != action:
                continue
            filtered.append(d)

        return filtered

    def get_fund_performance(self, fund_code: str, days: int = 90) -> Dict[str, Any]:
        """获取某只基金的决策表现"""
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        decisions = self.get_decisions(start_date=start_date, fund_code=fund_code)

        completed = [d for d in decisions if d.get('result', {}).get('status') == 'completed']
        if not completed:
            return {
                'fund_code': fund_code,
                'total_decisions': len(decisions),
                'completed_decisions': 0,
                'win_rate': 0.0,
                'avg_profit': 0.0,
                'best_trade': None,
                'worst_trade': None
            }

        profits = [d['result']['profit_rate'] for d in completed if d['result'].get('profit_rate') is not None]
        wins = [p for p in profits if p > 0]

        return {
            'fund_code': fund_code,
            'total_decisions': len(decisions),
            'completed_decisions': len(completed),
            'win_rate': len(wins) / len(profits) if profits else 0.0,
            'avg_profit': sum(profits) / len(profits) if profits else 0.0,
            'best_trade': max(profits) if profits else None,
            'worst_trade': min(profits) if profits else None,
            'recent_decisions': decisions[-5:]  # 最近5条决策
        }

    def get_decision_patterns(self, min_occurrences: int = 3) -> List[Dict]:
        """识别决策模式"""
        decisions = self.get_decisions(start_date='2020-01-01')  # 获取所有历史

        # 按因子得分区间分组
        patterns = {}
        for d in decisions:
            if d.get('result', {}).get('status') != 'completed':
                continue

            factors = d.get('factor_scores', {})
            composite = factors.get('composite', 0.5)
            action = d.get('action', 'hold')
            profit = d.get('result', {}).get('profit_rate', 0)

            # 简化分组：按综合得分区间
            if composite >= 0.7:
                score_range = 'high'
            elif composite >= 0.5:
                score_range = 'medium'
            else:
                score_range = 'low'

            pattern_key = f"{action}_{score_range}"
            if pattern_key not in patterns:
                patterns[pattern_key] = {
                    'pattern': pattern_key,
                    'action': action,
                    'score_range': score_range,
                    'occurrences': 0,
                    'wins': 0,
                    'total_profit': 0.0,
                    'avg_profit': 0.0,
                    'win_rate': 0.0
                }

            patterns[pattern_key]['occurrences'] += 1
            patterns[pattern_key]['total_profit'] += profit
            if profit > 0:
                patterns[pattern_key]['wins'] += 1

        # 计算统计值
        for p in patterns.values():
            if p['occurrences'] > 0:
                p['avg_profit'] = p['total_profit'] / p['occurrences']
                p['win_rate'] = p['wins'] / p['occurrences']

        # 过滤低频模式
        return [p for p in patterns.values() if p['occurrences'] >= min_occurrences]

    def generate_monthly_report(self, year: int = None, month: int = None) -> Dict[str, Any]:
        """生成月度报告"""
        if year is None:
            year = datetime.now().year
        if month is None:
            month = datetime.now().month

        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"

        decisions = self.get_decisions(start_date=start_date, end_date=end_date)

        completed = [d for d in decisions if d.get('result', {}).get('status') == 'completed']
        profits = [d['result']['profit_rate'] for d in completed if d.get('result', {}).get('profit_rate') is not None]

        # 按基金统计
        fund_stats = {}
        for d in decisions:
            fund_code = d.get('fund_code', 'unknown')
            if fund_code not in fund_stats:
                fund_stats[fund_code] = {'decisions': 0, 'profits': []}
            fund_stats[fund_code]['decisions'] += 1
            if d.get('result', {}).get('profit_rate') is not None:
                fund_stats[fund_code]['profits'].append(d['result']['profit_rate'])

        for fund in fund_stats.values():
            fund['avg_profit'] = sum(fund['profits']) / len(fund['profits']) if fund['profits'] else 0

        report = {
            'period': f"{year}-{month:02d}",
            'total_decisions': len(decisions),
            'completed_decisions': len(completed),
            'buy_count': len([d for d in decisions if d.get('action') == 'buy']),
            'sell_count': len([d for d in decisions if d.get('action') == 'sell']),
            'hold_count': len([d for d in decisions if d.get('action') == 'hold']),
            'win_rate': len([p for p in profits if p > 0]) / len(profits) if profits else 0,
            'avg_profit': sum(profits) / len(profits) if profits else 0,
            'total_profit': sum(profits),
            'best_trade': max(profits) if profits else None,
            'worst_trade': min(profits) if profits else None,
            'fund_performance': fund_stats,
            'generated_at': datetime.now().isoformat()
        }

        # 保存报告
        report_file = self.data_dir / 'analysis' / f'{year}-{month:02d}_report.json'
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            logger.info(f"月度报告已生成: {report_file}")
        except Exception as e:
            logger.error(f"保存月度报告失败: {e}")

        return report

    def export_for_optimization(self, days: int = 180) -> List[Dict]:
        """导出数据用于参数优化"""
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        decisions = self.get_decisions(start_date=start_date)

        # 转换为优化器可用的格式
        export_data = []
        for d in decisions:
            if d.get('result', {}).get('status') != 'completed':
                continue

            export_data.append({
                'date': d.get('timestamp', ''),
                'fund_code': d.get('fund_code', ''),
                'action': d.get('action', ''),
                'composite_score': d.get('factor_scores', {}).get('composite', 0.5),
                'profit_rate': d.get('result', {}).get('profit_rate', 0),
                'buy_threshold': d.get('buy_threshold', 0.58),
                'sell_threshold': d.get('sell_threshold', 0.42)
            })

        return export_data


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # 测试
    history = DecisionHistory()
    print(f"决策历史目录: {history.data_dir}")
    print(f"历史决策数: {len(history.get_decisions())}")

    # 生成月度报告
    report = history.generate_monthly_report()
    print(f"本月决策数: {report['total_decisions']}")
    print(f"胜率: {report['win_rate']:.1%}")
