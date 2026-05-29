# -*- coding: utf-8 -*-
"""
知识库管理模块
记录每次决策和结果，建立决策历史，为后续学习优化提供数据
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path(__file__).parent.parent / 'data' / 'knowledge'


class KnowledgeManager:
    """知识库管理器"""

    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir) if data_dir else KNOWLEDGE_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.decisions_file = self.data_dir / 'decisions.json'
        self.stats_file = self.data_dir / 'statistics.json'
        self._load_data()

    def _load_data(self):
        if self.decisions_file.exists():
            try:
                with open(self.decisions_file, 'r', encoding='utf-8') as f:
                    self.decisions = json.load(f)
            except Exception as e:
                logger.error(f"加载决策历史失败: {e}")
                self.decisions = []
        else:
            self.decisions = []

        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    self.stats = json.load(f)
            except Exception as e:
                logger.error(f"加载统计数据失败: {e}")
                self.stats = self._init_stats()
        else:
            self.stats = self._init_stats()

    def _init_stats(self):
        return {
            'total_decisions': 0,
            'buy_count': 0,
            'sell_count': 0,
            'hold_count': 0,
            'win_count': 0,
            'loss_count': 0,
            'win_rate': 0.0,
            'avg_profit': 0.0,
            'total_profit': 0.0,
            'last_updated': datetime.now().isoformat()
        }

    def _save_decisions(self):
        try:
            with open(self.decisions_file, 'w', encoding='utf-8') as f:
                json.dump(self.decisions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存决策历史失败: {e}")

    def _save_stats(self):
        try:
            self.stats['last_updated'] = datetime.now().isoformat()
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存统计数据失败: {e}")

    def save_decision(self, decision: Dict[str, Any]) -> str:
        """保存决策记录"""
        decision_record = {
            'decision_id': decision.get('decision_id', f"dec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
            'fund_code': decision.get('fund_code', ''),
            'fund_name': decision.get('fund_name', ''),
            'action': decision.get('action', 'hold'),
            'confidence': decision.get('confidence', 0.5),
            'amount': decision.get('amount', 0),
            'reason': decision.get('reason', ''),
            'factors': decision.get('factors', {}),
            'timestamp': decision.get('timestamp', datetime.now().isoformat()),
            'result': {
                'profit_rate': None,
                'hold_days': None,
                'status': 'pending'
            }
        }

        self.decisions.append(decision_record)
        self._save_decisions()

        action = decision_record['action']
        self.stats['total_decisions'] += 1
        if action == 'buy':
            self.stats['buy_count'] += 1
        elif action == 'sell':
            self.stats['sell_count'] += 1
        else:
            self.stats['hold_count'] += 1
        self._save_stats()

        logger.info(f"决策已保存: {decision_record['decision_id']}")
        return decision_record['decision_id']

    def update_result(self, decision_id: str, profit_rate: float, hold_days: int = 0):
        """更新决策结果"""
        for decision in self.decisions:
            if decision['decision_id'] == decision_id:
                decision['result'] = {
                    'profit_rate': profit_rate,
                    'hold_days': hold_days,
                    'status': 'completed',
                    'updated_at': datetime.now().isoformat()
                }
                self._save_decisions()

                if profit_rate > 0:
                    self.stats['win_count'] += 1
                else:
                    self.stats['loss_count'] += 1

                total_completed = self.stats['win_count'] + self.stats['loss_count']
                if total_completed > 0:
                    self.stats['win_rate'] = self.stats['win_count'] / total_completed

                self.stats['total_profit'] += profit_rate
                if total_completed > 0:
                    self.stats['avg_profit'] = self.stats['total_profit'] / total_completed

                self._save_stats()
                logger.info(f"决策结果已更新: {decision_id}, 收益: {profit_rate:.2f}%")
                return True

        logger.warning(f"未找到决策: {decision_id}")
        return False

    def get_similar_cases(self, fund_code: str = None, action: str = None, limit: int = 10) -> List[Dict]:
        """查询相似案例"""
        filtered = self.decisions

        if fund_code:
            filtered = [d for d in filtered if d['fund_code'] == fund_code]

        if action:
            filtered = [d for d in filtered if d['action'] == action]

        completed = [d for d in filtered if d['result']['status'] == 'completed']

        completed.sort(key=lambda x: x['timestamp'], reverse=True)
        return completed[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计数据"""
        return self.stats

    def get_fund_history(self, fund_code: str) -> List[Dict]:
        """获取某只基金的决策历史"""
        return [d for d in self.decisions if d['fund_code'] == fund_code]

    def get_recent_decisions(self, days: int = 7) -> List[Dict]:
        """获取最近N天的决策"""
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        return [d for d in self.decisions if d['timestamp'] >= cutoff]


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    km = KnowledgeManager()
    print(f"知识库统计: {km.get_statistics()}")
    print(f"历史决策数: {len(km.decisions)}")
