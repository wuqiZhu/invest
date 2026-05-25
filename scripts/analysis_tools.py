# -*- coding: utf-8 -*-
"""
高级分析工具脚本

使用方法：
    python analysis_tools.py analyze --fund 110011    # 深度分析
    python analysis_tools.py compare --fund 110011    # 基金对比
    python analysis_tools.py backtest --fund 110011   # 回测
    python analysis_tools.py simulate --fund 110011   # 定投模拟
    python analysis_tools.py chart --fund 110011      # 图表
    python analysis_tools.py report --fund 110011     # 报告
    python analysis_tools.py timeline                 # 时间线

免责声明：
本工具仅供个人学习和研究使用，不构成任何投资建议。
基金投资有风险，过往业绩不代表未来表现。
"""

import sys
import os
import argparse
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main_cli import FundInvestmentCLI


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='高级分析工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python analysis_tools.py analyze --fund 110011           # 深度分析
  python analysis_tools.py compare --fund 110011           # 基金对比
  python analysis_tools.py backtest --fund 110011          # 回测
  python analysis_tools.py simulate --fund 110011 --amount 500  # 定投模拟
  python analysis_tools.py chart --fund 110011             # 交互式图表
  python analysis_tools.py report --fund 110011            # 分析报告
  python analysis_tools.py timeline                        # 投资时间线
        """
    )

    parser.add_argument('action',
                       choices=['analyze', 'compare', 'backtest', 'simulate', 'chart', 'report', 'timeline'],
                       help='执行的操作')
    parser.add_argument('--config', '-c', help='配置文件路径')
    parser.add_argument('--fund', '-f', nargs='+', help='基金代码')
    parser.add_argument('--days', '-d', type=int, help='分析天数')
    parser.add_argument('--benchmark', '-b', default='110030', help='基准基金代码（默认沪深300）')
    parser.add_argument('--amount', type=int, help='定投金额')
    parser.add_argument('--short-ma', type=int, help='短期均线周期')
    parser.add_argument('--long-ma', type=int, help='长期均线周期')

    args = parser.parse_args()

    cli = FundInvestmentCLI(args.config)

    if args.action == 'analyze':
        if not args.fund:
            print("深度分析需要指定基金代码: --fund CODE")
            return
        cli.analyze(fund_codes=args.fund, days=args.days)

    elif args.action == 'compare':
        if not args.fund:
            print("基金对比需要指定基金代码: --fund CODE")
            return
        cli.compare(args.fund[0], args.benchmark, args.days or 365)

    elif args.action == 'backtest':
        if not args.fund:
            print("回测需要指定基金代码: --fund CODE")
            return
        cli.backtest(args.fund[0], args.short_ma, args.long_ma)

    elif args.action == 'simulate':
        if not args.fund:
            print("定投模拟需要指定基金代码: --fund CODE")
            return
        cli.simulate(fund_code=args.fund[0], monthly_amount=args.amount)

    elif args.action == 'chart':
        if not args.fund:
            print("图表需要指定基金代码: --fund CODE")
            return
        cli.chart(args.fund[0], args.days or 365)

    elif args.action == 'report':
        if not args.fund:
            print("报告需要指定基金代码: --fund CODE")
            return
        cli.report(args.fund[0], args.days or 365)

    elif args.action == 'timeline':
        cli.timeline(fund_code=args.fund[0] if args.fund else None, days=args.days or 30)


if __name__ == "__main__":
    main()
