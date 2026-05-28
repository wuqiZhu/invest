# -*- coding: utf-8 -*-
"""
交易执行引擎（模拟模式）
接收决策引擎的投资决策，执行模拟交易，记录结果到数据库和结果队列

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
    from fund_database import FundDatabase
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

try:
    from fund_data_fetcher import FundDataFetcher
    FETCHER_AVAILABLE = True
except ImportError:
    FETCHER_AVAILABLE = False


class ExecutionEngine:
    """交易执行引擎（模拟模式）"""

    def __init__(self, config_path=None, data_dir=None, db_path=None):
        """
        初始化执行引擎

        Args:
            config_path: 配置文件路径
            data_dir: 数据目录路径
            db_path: 数据库文件路径
        """
        self.config = ConfigManager(config_path)
        self.executor = ParallelExecutor(data_dir)

        self.db = None
        if DB_AVAILABLE:
            try:
                if db_path is None:
                    db_path = os.path.join(
                        os.path.dirname(os.path.abspath(__file__)), 'fund_data.db'
                    )
                self.db = FundDatabase(db_path)
            except Exception:
                pass

        self.fetcher = None
        if FETCHER_AVAILABLE:
            try:
                self.fetcher = FundDataFetcher()
            except Exception:
                pass

    def execute(self, decision, update_batch=True):
        """
        主执行流程

        Args:
            decision: 决策数据（来自 decision_engine）
            update_batch: 是否更新批次状态

        Returns:
            dict: 执行结果
        """
        if not self.validate_decision(decision):
            return {
                'batch_id': decision.get('batch_id', ''),
                'execution_id': f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'decision_id': decision.get('decision_id', ''),
                'action': decision.get('action', 'unknown'),
                'status': 'rejected',
                'reason': '决策校验失败：缺少必要字段或数据不合法',
                'timestamp': datetime.now().isoformat()
            }

        action = decision.get('action', 'hold')
        fund_code = decision.get('fund_code', '')

        if action == 'buy':
            result = self.simulate_buy(decision)
        elif action == 'sell':
            result = self.simulate_sell(decision)
        else:
            result = {
                'batch_id': decision.get('batch_id', ''),
                'execution_id': f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'decision_id': decision.get('decision_id', ''),
                'action': 'hold',
                'fund_code': fund_code,
                'fund_name': decision.get('fund_name', ''),
                'amount': 0,
                'price': 0,
                'shares': 0,
                'status': 'hold',
                'reason': '继续持有',
                'timestamp': datetime.now().isoformat()
            }

        self._record_to_results(result)

        if update_batch:
            batch_id = decision.get('batch_id', '')
            if batch_id:
                self.executor.update_batch_status(batch_id, 'executed', {'execution': result})

        return result

    def validate_decision(self, decision):
        """
        校验决策有效性

        Args:
            decision: 决策数据

        Returns:
            bool
        """
        if not isinstance(decision, dict):
            return False

        required_fields = ['batch_id', 'action', 'fund_code']
        for field in required_fields:
            if not decision.get(field):
                return False

        action = decision.get('action', '')
        if action not in ('buy', 'sell', 'hold'):
            return False

        if action in ('buy', 'sell'):
            amount = decision.get('amount', 0)
            if not isinstance(amount, (int, float)) or amount < 0:
                return False
            if amount > 100000:
                return False

        return True

    def _get_current_nav(self, fund_code):
        """
        获取当前基金净值

        优先级：
        1. 从东方财富API获取实时估值
        2. 从数据库获取历史净值

        Args:
            fund_code: 基金代码

        Returns:
            float: 最新净值，失败返回 None
        """
        if self.fetcher:
            try:
                info = self.fetcher.get_fund_info(fund_code)
                if info:
                    estimated_nav = info.get('估算净值', 0)
                    if estimated_nav and estimated_nav > 0:
                        return float(estimated_nav)
                    unit_nav = info.get('单位净值', 0)
                    if unit_nav and unit_nav > 0:
                        return float(unit_nav)
            except Exception:
                pass

        if self.db:
            try:
                df = self.db.get_fund_nav(fund_code)
                if df is not None and not df.empty:
                    return float(df['单位净值'].iloc[-1])
            except Exception:
                pass

        return None

    def _get_shares_held(self, fund_code):
        """
        获取当前持有份额

        Args:
            fund_code: 基金代码

        Returns:
            float: 持有份额
        """
        if not self.db:
            return 0

        try:
            records = self.db.get_invest_records(fund_code)
            if records is None or records.empty:
                return 0
            total_bought = records[records['amount'] > 0]['shares'].sum()
            total_sold_records = records[records['amount'] < 0]
            total_sold = abs(total_sold_records['shares'].sum()) if not total_sold_records.empty else 0
            return total_bought - total_sold
        except Exception:
            return 0

    def simulate_buy(self, decision):
        """
        模拟买入

        Args:
            decision: 决策数据

        Returns:
            dict: 执行结果
        """
        fund_code = decision.get('fund_code', '')
        fund_name = decision.get('fund_name', fund_code)
        amount = float(decision.get('amount', 0))

        nav = self._get_current_nav(fund_code)
        if nav is None:
            nav = 1.0

        shares = amount / nav if nav > 0 else 0

        result = {
            'batch_id': decision.get('batch_id', ''),
            'execution_id': f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'decision_id': decision.get('decision_id', ''),
            'action': 'buy',
            'fund_code': fund_code,
            'fund_name': fund_name,
            'amount': amount,
            'price': round(nav, 4),
            'shares': round(shares, 2),
            'status': 'executed',
            'reason': decision.get('reason', ''),
            'confidence': decision.get('confidence', 0),
            'timestamp': datetime.now().isoformat()
        }

        self._record_trade(fund_code, amount, nav, shares)

        return result

    def simulate_sell(self, decision):
        """
        模拟卖出

        Args:
            decision: 决策数据

        Returns:
            dict: 执行结果
        """
        fund_code = decision.get('fund_code', '')
        fund_name = decision.get('fund_name', fund_code)

        nav = self._get_current_nav(fund_code)
        if nav is None:
            nav = 1.0

        shares_held = self._get_shares_held(fund_code)
        sell_amount = float(decision.get('amount', 0))

        if shares_held <= 0:
            return {
                'batch_id': decision.get('batch_id', ''),
                'execution_id': f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'decision_id': decision.get('decision_id', ''),
                'action': 'sell',
                'fund_code': fund_code,
                'fund_name': fund_name,
                'amount': 0,
                'price': round(nav, 4),
                'shares': 0,
                'status': 'rejected',
                'reason': '无持仓可卖出',
                'timestamp': datetime.now().isoformat()
            }

        sell_shares = min(sell_amount / nav if nav > 0 else 0, shares_held)
        actual_amount = sell_shares * nav

        result = {
            'batch_id': decision.get('batch_id', ''),
            'execution_id': f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'decision_id': decision.get('decision_id', ''),
            'action': 'sell',
            'fund_code': fund_code,
            'fund_name': fund_name,
            'amount': round(actual_amount, 2),
            'price': round(nav, 4),
            'shares': round(sell_shares, 2),
            'status': 'executed',
            'reason': decision.get('reason', ''),
            'confidence': decision.get('confidence', 0),
            'timestamp': datetime.now().isoformat()
        }

        self._record_trade(fund_code, -actual_amount, nav, -sell_shares)

        return result

    def _record_trade(self, fund_code, amount, nav, shares):
        """
        记录交易到数据库

        Args:
            fund_code: 基金代码
            amount: 交易金额
            nav: 交易净值
            shares: 交易份额
        """
        if not self.db:
            return

        try:
            records = self.db.get_invest_records(fund_code)
            if records is not None and not records.empty:
                last = records.iloc[-1]
                total_shares = last.get('total_shares', 0) + shares
                total_invested = last.get('total_invested', 0) + amount
            else:
                total_shares = shares
                total_invested = amount

            current_value = total_shares * nav
            profit = current_value - total_invested
            profit_rate = (profit / total_invested * 100) if total_invested > 0 else 0

            invest_record = {
                'fund_code': fund_code,
                'invest_date': datetime.now().strftime('%Y-%m-%d'),
                'amount': round(amount, 2),
                'nav': round(nav, 4),
                'shares': round(shares, 2),
                'total_shares': round(total_shares, 2),
                'total_invested': round(total_invested, 2),
                'current_value': round(current_value, 2),
                'profit': round(profit, 2),
                'profit_rate': round(profit_rate, 2)
            }
            self.db.save_invest_record(invest_record)
        except Exception:
            pass

    def _record_to_results(self, result):
        """
        写入执行结果到结果队列

        Args:
            result: 执行结果
        """
        self.executor.write_execution(result)

    def get_portfolio_summary(self):
        """
        获取当前持仓汇总（使用实时净值计算）

        Returns:
            dict: 持仓信息
        """
        if not self.db:
            return {'available': False, 'reason': '数据库不可用'}

        try:
            records = self.db.get_invest_records()
            if records is None or records.empty:
                return {'available': True, 'holdings': [], 'total_invested': 0, 'total_value': 0}

            holdings = []
            for fund_code in records['fund_code'].unique():
                fund_records = records[records['fund_code'] == fund_code]
                last = fund_records.iloc[-1]
                total_shares = last.get('total_shares', 0)
                total_invested = last.get('total_invested', 0)

                current_nav = self._get_current_nav(fund_code)
                if current_nav and current_nav > 0:
                    current_value = total_shares * current_nav
                else:
                    current_value = last.get('current_value', 0)

                profit = current_value - total_invested
                profit_rate = (profit / total_invested * 100) if total_invested > 0 else 0

                holdings.append({
                    'fund_code': fund_code,
                    'total_shares': round(total_shares, 2),
                    'total_invested': round(total_invested, 2),
                    'current_nav': round(current_nav, 4) if current_nav else None,
                    'current_value': round(current_value, 2),
                    'profit': round(profit, 2),
                    'profit_rate': round(profit_rate, 2),
                })

            total_invested = sum(h['total_invested'] for h in holdings)
            total_value = sum(h['current_value'] for h in holdings)

            return {
                'available': True,
                'holdings': holdings,
                'total_invested': round(total_invested, 2),
                'total_value': round(total_value, 2),
                'total_profit': round(total_value - total_invested, 2),
            }
        except Exception:
            return {'available': False, 'reason': '查询失败'}

    def process_next_batch(self):
        """
        处理队列中下一个待执行的批次

        Returns:
            list 或 dict 或 None: 执行结果列表（多基金）或单个结果
        """
        batch = self.executor.get_next_batch(status='decided')
        if batch is None:
            return None

        decision_data = batch.get('decision', {})
        if not decision_data:
            return None

        batch_id = batch.get('batch_id')

        if 'decisions' in decision_data:
            results = []
            for dec in decision_data['decisions']:
                dec['batch_id'] = batch_id
                result = self.execute(dec, update_batch=False)
                results.append(result)
            self.executor.update_batch_status(batch_id, 'executed', {'executions': results})
            return results
        else:
            decision_data['batch_id'] = batch_id
            return self.execute(decision_data)

    def close(self):
        """关闭数据库连接"""
        if self.db:
            self.db.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(description='交易执行引擎')
    parser.add_argument('--config', help='配置文件路径')
    parser.add_argument('--data-dir', help='数据目录路径')
    parser.add_argument('--db-path', help='数据库文件路径')
    parser.add_argument('--process', action='store_true', help='处理下一个待执行批次')
    parser.add_argument('--portfolio', action='store_true', help='查看持仓汇总')
    parser.add_argument('--test', action='store_true', help='使用测试数据运行')

    args = parser.parse_args()
    engine = ExecutionEngine(args.config, args.data_dir, args.db_path)

    try:
        if args.process:
            result = engine.process_next_batch()
            if result:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print("没有待执行的批次")

        elif args.portfolio:
            summary = engine.get_portfolio_summary()
            print(json.dumps(summary, ensure_ascii=False, indent=2))

        elif args.test:
            test_decision = {
                'batch_id': 'test_001',
                'decision_id': 'dec_test_001',
                'action': 'buy',
                'confidence': 0.75,
                'fund_code': '110011',
                'fund_name': '易方达中小盘混合',
                'amount': 200,
                'reason': '情绪指数=0.72, 技术信号=看多',
                'factors': {},
                'timestamp': datetime.now().isoformat()
            }
            result = engine.execute(test_decision)
            print(json.dumps(result, ensure_ascii=False, indent=2))

        else:
            parser.print_help()

    finally:
        engine.close()


if __name__ == '__main__':
    main()
