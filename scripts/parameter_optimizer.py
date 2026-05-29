# -*- coding: utf-8 -*-
"""
参数自动调优模块
通过网格搜索找到最优的决策参数
"""

import sys
import logging
import json
import itertools
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backtester import Backtester
from config_manager import ConfigManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PARAM_GRID = {
    'buy_threshold': [0.50, 0.52, 0.55, 0.58],
    'sell_threshold': [0.42, 0.45, 0.48, 0.50],
}

WEIGHT_GRID = {
    'weight_sentiment': [0.25, 0.30, 0.35],
    'weight_technical': [0.25, 0.30, 0.35],
}


class ParameterOptimizer:
    """参数优化器"""

    def __init__(self, config_path=None):
        self.config = ConfigManager(config_path)
        self.backtester = Backtester(config_path)
        self.results = []

    def grid_search(self, fund_code=None, max_combinations=50):
        """网格搜索最优参数"""
        fund_codes = [fund_code] if fund_code else self.config.get_fund_codes()

        param_combinations = list(itertools.product(
            PARAM_GRID['buy_threshold'],
            PARAM_GRID['sell_threshold']
        ))

        if len(param_combinations) > max_combinations:
            import random
            param_combinations = random.sample(param_combinations, max_combinations)

        logger.info(f"开始网格搜索: {len(param_combinations)} 种参数组合, {len(fund_codes)} 只基金")

        results = []
        for i, (buy_threshold, sell_threshold) in enumerate(param_combinations):
            if buy_threshold <= sell_threshold:
                continue

            logger.info(f"测试参数 [{i+1}/{len(param_combinations)}]: 买入={buy_threshold}, 卖出={sell_threshold}")

            fund_results = []
            for fund in fund_codes:
                try:
                    result = self.backtester.run_backtest(
                        fund_code=fund,
                        buy_threshold=buy_threshold,
                        sell_threshold=sell_threshold
                    )
                    fund_results.append(result)
                except Exception as e:
                    logger.warning(f"基金 {fund} 回测失败: {e}")

            if fund_results:
                avg_excess = sum(r.get('excess_return', 0) for r in fund_results) / len(fund_results)
                win_count = sum(1 for r in fund_results if r.get('excess_return', 0) > 0)
                win_rate = win_count / len(fund_results)

                results.append({
                    'buy_threshold': buy_threshold,
                    'sell_threshold': sell_threshold,
                    'avg_excess_return': avg_excess,
                    'win_rate': win_rate,
                    'fund_count': len(fund_results)
                })

        results.sort(key=lambda x: x['avg_excess_return'], reverse=True)
        self.results = results

        return results

    def get_best_params(self):
        """获取最优参数"""
        if not self.results:
            return None
        return self.results[0]

    def generate_report(self):
        """生成优化报告"""
        if not self.results:
            return "无优化结果"

        lines = []
        lines.append("📊 参数优化报告")
        lines.append("=" * 40)
        lines.append(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"测试组合: {len(self.results)}")
        lines.append("")

        best = self.results[0]
        lines.append("🏆 最优参数:")
        lines.append(f"  买入阈值: {best['buy_threshold']}")
        lines.append(f"  卖出阈值: {best['sell_threshold']}")
        lines.append(f"  平均超额收益: {best['avg_excess_return']:.2f}%")
        lines.append(f"  跑赢比例: {best['win_rate']*100:.1f}%")
        lines.append("")

        lines.append("📈 Top 5 参数组合:")
        lines.append("-" * 40)
        for i, r in enumerate(self.results[:5]):
            lines.append(f"{i+1}. 买入={r['buy_threshold']}, 卖出={r['sell_threshold']}: 超额{r['avg_excess_return']:.2f}%")

        return "\n".join(lines)

    def save_results(self, filepath=None):
        """保存优化结果"""
        if filepath is None:
            filepath = Path(__file__).parent.parent / 'data' / 'optimization' / f'results_{datetime.now().strftime("%Y%m%d")}.json'

        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'timestamp': datetime.now().isoformat(),
            'results': self.results,
            'best_params': self.get_best_params()
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"优化结果已保存: {filepath}")
        return filepath


def run_optimization(config_path=None):
    """运行参数优化"""
    optimizer = ParameterOptimizer(config_path)
    results = optimizer.grid_search(max_combinations=20)

    report = optimizer.generate_report()
    print(report)

    optimizer.save_results()

    return report


if __name__ == '__main__':
    run_optimization()
