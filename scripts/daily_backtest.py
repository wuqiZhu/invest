# -*- coding: utf-8 -*-
import os
import sys
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backtester import Backtester


def run_daily_backtest():
    backtester = Backtester()
    fund_codes = backtester.config.get_fund_codes()
    if not fund_codes:
        fund_codes = ['110011']

    results = backtester.run_multi_fund_backtest(fund_codes)

    summary_lines = [
        f"策略回测报告 {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "=========================",
    ]

    for code, result in results.items():
        emoji = "OK" if result['excess_return'] >= 0 else "!!"
        summary_lines.append(
            f"{emoji} {code}: "
            f"策略{result['total_return']}% | "
            f"持有{result['buy_and_hold_return']}% | "
            f"超额{result['excess_return']:+.2f}%"
        )

    summary_lines.append("=========================")

    avg_excess = sum(r['excess_return'] for r in results.values()) / len(results) if results else 0
    summary_lines.append(f"平均超额收益: {avg_excess:+.2f}%")

    report = "\n".join(summary_lines)
    print(report)

    return report


if __name__ == '__main__':
    run_daily_backtest()
