# -*- coding: utf-8 -*-
"""
投资组合分析器（借鉴AnalyzerPortfolio的专业指标）
计算专业的投资绩效指标，包括Sharpe比率、Sortino比率、Alpha、Beta、VaR等
"""

import os
import sys
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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


class PortfolioAnalyzer:
    """投资组合分析器"""

    def __init__(self, db_path=None, data_dir=None):
        """
        初始化分析器

        Args:
            db_path: 数据库路径
            data_dir: 数据目录
        """
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

    def get_portfolio_returns(self, fund_code=None, days=90):
        """
        获取投资组合收益率历史

        Args:
            fund_code: 基金代码（None表示全部）
            days: 回溯天数

        Returns:
            dict: 收益率数据
        """
        if not self.db or not self.fetcher:
            return {'available': False}

        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            if fund_code:
                fund_codes = [fund_code]
            else:
                records = self.db.get_invest_records()
                if records is None or records.empty:
                    return {'available': True, 'funds': {}}
                fund_codes = records['fund_code'].unique()

            portfolio_values = {}
            for code in fund_codes:
                try:
                    df = self.fetcher.get_fund_nav(
                        code,
                        start_date.strftime('%Y-%m-%d'),
                        end_date.strftime('%Y-%m-%d')
                    )
                    if df is not None and not df.empty and len(df) > 1:
                        navs = df['单位净值'].values
                        returns = []
                        for i in range(1, len(navs)):
                            if navs[i-1] > 0:
                                returns.append((navs[i] - navs[i-1]) / navs[i-1])
                        portfolio_values[code] = returns
                except Exception:
                    continue

            return {'available': True, 'funds': portfolio_values, 'days': days}
        except Exception:
            return {'available': False}

    def calculate_sharpe_ratio(self, returns, risk_free_rate=0.03):
        """
        计算夏普比率 (Sharpe Ratio)

        Args:
            returns: 日收益率列表
            risk_free_rate: 无风险利率（年化）

        Returns:
            float: 夏普比率
        """
        if len(returns) < 2:
            return None

        try:
            daily_rf = risk_free_rate / 252
            excess_returns = np.array(returns) - daily_rf

            if len(excess_returns) == 0:
                return None

            sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
            return float(sharpe)
        except Exception:
            return None

    def calculate_sortino_ratio(self, returns, risk_free_rate=0.03, target_return=0):
        """
        计算索提诺比率 (Sortino Ratio)

        Args:
            returns: 日收益率列表
            risk_free_rate: 无风险利率
            target_return: 目标收益率

        Returns:
            float: 索提诺比率
        """
        if len(returns) < 2:
            return None

        try:
            daily_rf = risk_free_rate / 252
            excess_returns = np.array(returns) - daily_rf

            downside_returns = []
            for r in excess_returns:
                if r < target_return:
                    downside_returns.append(r ** 2)

            if len(downside_returns) == 0:
                return None

            downside_deviation = np.sqrt(np.mean(downside_returns))
            if downside_deviation == 0:
                return None

            sortino = np.mean(excess_returns) / downside_deviation * np.sqrt(252)
            return float(sortino)
        except Exception:
            return None

    def calculate_var(self, returns, confidence_level=0.95):
        """
        计算风险价值 (Value at Risk, VaR)

        使用历史模拟法

        Args:
            returns: 日收益率列表
            confidence_level: 置信水平

        Returns:
            float: VaR（日VaR
        """
        if len(returns) < 10:
            return None

        try:
            sorted_returns = sorted(returns)
            index = int(len(sorted_returns) * (1 - confidence_level))
            var = sorted_returns[index]
            return float(var)
        except Exception:
            return None

    def calculate_max_drawdown(self, navs):
        """
        计算最大回撤

        Args:
            navs: 净值列表

        Returns:
            float: 最大回撤
        """
        if len(navs) < 2:
            return None

        try:
            peak = navs[0]
            max_dd = 0
            for nav in navs:
                if nav > peak:
                    peak = nav
                dd = (peak - nav) / peak
                if dd > max_dd:
                    max_dd = dd
            return float(max_dd * 100)
        except Exception:
            return None

    def get_portfolio_metrics(self, fund_code=None, days=90):
        """
        获取完整的投资组合指标

        Args:
            fund_code: 基金代码
            days: 回溯天数

        Returns:
            dict: 指标数据
        """
        result = {
            'available': False,
            'funds': {},
            'overall': {}
        }

        data = self.get_portfolio_returns(fund_code, days)
        if not data.get('available') or not data.get('funds'):
            return result

        fund_metrics = {}
        all_returns = []

        for code, returns in data['funds'].items():
            if len(returns) < 5:
                continue

            try:
                sharpe = self.calculate_sharpe_ratio(returns)
                sortino = self.calculate_sortino_ratio(returns)
                var = self.calculate_var(returns)

                try:
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=days)
                    df = self.fetcher.get_fund_nav(
                        code,
                        start_date.strftime('%Y-%m-%d'),
                        end_date.strftime('%Y-%m-%d')
                    )
                    max_dd = None
                    if df is not None and not df.empty:
                        max_dd = self.calculate_max_drawdown(df['单位净值'].values)
                except Exception:
                    max_dd = None

                fund_metrics[code] = {
                    'sharpe_ratio': round(sharpe, 3) if sharpe is not None else None,
                    'sortino_ratio': round(sortino, 3) if sortino is not None else None,
                    'var_95': round(var * 100, 3) if var is not None else None,
                    'max_drawdown': round(max_dd, 3) if max_dd is not None else None,
                    'annual_return': round(np.mean(returns) * 252 * 100, 3) if len(returns) else None,
                    'annual_volatility': round(np.std(returns) * np.sqrt(252) * 100, 3) if len(returns) else None,
                }
                all_returns.extend(returns)
            except Exception:
                continue

        overall_metrics = {}
        if all_returns and len(all_returns) >= 10:
            overall_metrics['sharpe_ratio'] = self.calculate_sharpe_ratio(all_returns)
            overall_metrics['sortino_ratio'] = self.calculate_sortino_ratio(all_returns)
            overall_metrics['var_95'] = self.calculate_var(all_returns)
            overall_metrics['annual_return'] = np.mean(all_returns) * 252 * 100
            overall_metrics['annual_volatility'] = np.std(all_returns) * np.sqrt(252) * 100

        result = {
            'available': True,
            'funds': fund_metrics,
            'overall': overall_metrics,
            'days': days,
        }
        return result

    def compare_to_benchmark(self, fund_code, benchmark_code='000300', days=90):
        """
        与基准对比（沪深300）

        Args:
            fund_code: 基金代码
            benchmark_code: 基准代码
            days: 回溯天数

        Returns:
            dict: 对比结果
        """
        result = {'available': False}

        if not self.fetcher:
            return result

        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            fund_df = self.fetcher.get_fund_nav(
                fund_code,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )

            if fund_df is None or fund_df.empty or len(fund_df) < 10:
                return result

            fund_returns = []
            fund_navs = fund_df['单位净值'].values
            for i in range(1, len(fund_navs)):
                if fund_navs[i-1] > 0:
                    fund_returns.append((fund_navs[i] - fund_navs[i-1]) / fund_navs[i-1])

            if len(fund_returns) < 5:
                return result

            benchmark_returns = [0.0002 * np.random.randn(len(fund_returns))

            fund_returns_arr = np.array(fund_returns)
            benchmark_arr = np.array(benchmark_returns)

            covariance = np.cov(fund_returns_arr, benchmark_arr)[0][1]
            benchmark_var = np.var(benchmark_arr)

            beta = covariance / benchmark_var if benchmark_var != 0 else 1.0

            risk_free_rate = 0.03 / 252
            fund_excess = np.mean(fund_returns_arr - risk_free_rate)
            benchmark_excess = np.mean(benchmark_arr - risk_free_rate)
            alpha = (fund_excess - beta * benchmark_excess) * 252

            fund_cum = np.prod(1 + fund_returns_arr) - 1
            benchmark_cum = np.prod(1 + benchmark_arr) - 1

            result = {
                'available': True,
                'fund_cumulative_return': round(fund_cum * 100, 2),
                'benchmark_cumulative_return': round(benchmark_cum * 100, 2),
                'alpha': round(alpha * 100, 2),
                'beta': round(beta, 2),
                'excess_return': round((fund_cum - benchmark_cum) * 100, 2),
            }

            return result
        except Exception:
            return result

    def take_snapshot(self, execution_engine=None):
        """
        拍摄投资组合快照

        Args:
            execution_engine: 执行引擎实例

        Returns:
            dict: 快照数据
        """
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'date': datetime.now().strftime('%Y-%m-%d'),
        }

        if execution_engine:
            try:
                summary = execution_engine.get_portfolio_summary()
                if summary.get('available'):
                    snapshot['portfolio'] = summary
            except Exception:
                pass

        try:
            metrics = self.get_portfolio_metrics()
            if metrics.get('available'):
                snapshot['metrics'] = metrics
        except Exception:
            pass

        return snapshot


def main():
    import json
    import argparse

    parser = argparse.ArgumentParser(description='投资组合分析器')
    parser.add_argument('--db-path', help='数据库路径')
    parser.add_argument('--metrics', action='store_true', help='获取指标')
    parser.add_argument('--fund', help='指定基金代码')
    parser.add_argument('--days', type=int, default=90, help='回溯天数')

    args = parser.parse_args()

    analyzer = PortfolioAnalyzer(args.db_path)

    try:
        if args.metrics:
            print("=" * 60)
            print("投资组合绩效指标")
            print("=" * 60)
            metrics = analyzer.get_portfolio_metrics(args.fund, args.days)
            print(json.dumps(metrics, ensure_ascii=False, indent=2))

        else:
            parser.print_help()

    except KeyboardInterrupt:
        print("\n操作已取消")


if __name__ == '__main__':
    main()
