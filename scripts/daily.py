# -*- coding: utf-8 -*-
"""
日常操作脚本

使用方法：
    python daily.py --morning    # 每日晨报
    python daily.py --invest     # 定投日记录
    python daily.py --review     # 月底复盘

免责声明：
本工具仅供个人学习和研究使用，不构成任何投资建议。
"""

import sys
import os
import argparse
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main_cli import FundInvestmentCLI
from fund_notifier import FundNotifier


def morning(cli, verbose=False, quiet=False, devil=False, notify=False):
    """每日晨报：简洁格式输出，整合signal和止盈策略"""
    date_str = datetime.now().strftime('%Y-%m-%d')

    if verbose:
        print("="*50)
        print(f"每日晨报 - {date_str}")
        print("="*50)
        cli.daily_report()

    funds = cli.config.get('funds', [])
    enabled_funds = [f for f in funds if f.get('enabled', True)]

    if not enabled_funds:
        if not quiet:
            print(f"{date_str} 晨报")
            print("没有启用的基金，请先配置")
        return

    if not verbose and not quiet:
        print(f"{date_str} 晨报")

    has_signal = False
    has_important_signal = False
    signal_results = []
    important_messages = []
    
    for fund in enabled_funds:
        code = fund['code']
        name = fund.get('name', code)
        try:
            result = cli.trading_system.get_signal(
                cli.fetcher.get_fund_nav(code), code
            )
            advice = cli.trading_system.get_advice(result)
            signal = result.get('signal', 'HOLD')
            trend = result.get('modules', {}).get('trend', {}).get('status', 'unknown')
            vol = result.get('modules', {}).get('volatility', {}).get('status', 'unknown')
            profit = result.get('modules', {}).get('profit', {}).get('status', 'hold')

            trend_str = "↑" if trend == "up" else "↓" if trend == "down" else "→"
            vol_str = "适中" if vol == "moderate" else "高" if vol == "high" else "低" if vol == "low" else vol

            signal_results.append({
                'code': code,
                'name': name,
                'result': result,
                'advice': advice,
                'signal': signal,
                'trend': trend,
                'vol': vol,
                'profit': profit,
                'trend_str': trend_str,
                'vol_str': vol_str
            })

            if signal == 'SELL' or profit in ['trailing_stop', 'half_profit']:
                has_important_signal = True
                important_messages.append(f"{code} {name}：{advice}")
            
            if "提高" in advice or "赎回" in advice or "暂停" in advice:
                has_signal = True
                if quiet:
                    print(f"{code} {name}：{advice} (趋势{trend_str}，波动{vol_str})")
                else:
                    print(f"{code} {name}：{advice} (趋势{trend_str}，波动{vol_str})")
            elif not quiet:
                print(f"{code} {name}：{advice} (趋势{trend_str}，波动{vol_str})")
        except Exception as e:
            if not quiet:
                print(f"{code} {name}：获取信号失败")

    if not has_signal and not quiet:
        print("今日无操作建议。")
    elif not has_signal and quiet:
        print(f"{date_str} 今日无重要信号。")

    # 发送钉钉通知（仅在有重要信号时）
    if notify and has_important_signal:
        send_dingtalk_notification(important_messages, cli.config)

    # 魔鬼代言人模式
    if devil and signal_results:
        print(f"\n{'='*50}")
        print("[魔鬼代言人] 反面观点")
        print(f"{'='*50}")

        for sr in signal_results:
            code = sr['code']
            name = sr['name']
            result = sr['result']

            try:
                from datetime import timedelta
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
                end_date = datetime.now().strftime('%Y-%m-%d')
                fund_data = cli.fetcher.get_fund_nav(code, start_date, end_date)

                if not fund_data.empty:
                    analysis = cli.analyzer.analyze_fund(fund_data, code)
                    benchmark_code = cli.config.get('analysis.benchmark_code', '110030')
                    benchmark_data = cli.fetcher.get_fund_nav(benchmark_code, start_date, end_date)

                    warnings = cli.analyzer.devils_advocate(fund_data, code, analysis, benchmark_data)
                    mistakes = cli.analyzer.check_common_mistakes(fund_data, code, analysis)

                    if warnings or mistakes:
                        print(f"\n{name} ({code}):")
                        for w in warnings:
                            print(f"  - {w}")
                        for m in mistakes:
                            print(f"  - {m['warning']}")
                            print(f"    建议：{m['advice']}")
            except Exception as e:
                pass

        print(f"{'='*50}")


def send_dingtalk_notification(messages, config):
    """发送钉钉通知"""
    try:
        notifier = FundNotifier(config)
        
        notification_config = config.get('notification', {})
        if notification_config.get('method') == 'dingtalk':
            webhook_url = notification_config.get('dingtalk', {}).get('webhook_url')
            secret = notification_config.get('dingtalk', {}).get('secret')
            
            if webhook_url:
                content = f"📈 基金交易信号提醒\n\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                content += "\n".join(messages)
                content += "\n\n⚠️ 以上信息仅供参考，不构成投资建议"
                
                notifier.send_dingtalk(content, webhook_url, secret)
                print("\n✅ 钉钉通知已发送")
            else:
                print("\n⚠️ 未配置钉钉webhook，跳过通知")
        else:
            print("\n⚠️ 通知方式未设置为钉钉，跳过通知")
    except Exception as e:
        print(f"\n⚠️ 钉钉通知发送失败: {e}")


def invest(cli, verbose=False):
    """定投日记录：简洁格式输出"""
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    funds = cli.config.get('funds', [])
    enabled_funds = [f for f in funds if f.get('enabled', True)]
    
    if not enabled_funds:
        print(f"{date_str} 定投")
        print("没有启用的基金，请先配置")
        return
    
    if verbose:
        print("="*50)
        print(f"定投记录 - {date_str}")
        print("="*50)
        
        print("\n今日定投计划：")
        total_amount = 0
        for fund in enabled_funds:
            code = fund['code']
            name = fund.get('name', code)
            amount = fund.get('monthly_invest', 0)
            print(f"  {code} {name}: {amount}元")
            total_amount += amount
        
        print(f"\n总计：{total_amount}元")
        
        confirm = input("\n确认执行定投？(y/n): ").strip().lower()
        if confirm != 'y':
            print("已取消")
            return
    else:
        print(f"{date_str} 定投记录")
    
    total_invested = 0
    for fund in enabled_funds:
        code = fund['code']
        name = fund.get('name', code)
        amount = fund.get('monthly_invest', 0)
        
        if amount <= 0:
            continue
        
        try:
            nav = 0
            fund_data = cli.fetcher.get_fund_nav(code)
            if not fund_data.empty:
                nav = fund_data['单位净值'].iloc[-1]
            
            if not verbose:
                confirm = input(f"{code} {name} 买入{amount}元？(y/n): ").strip().lower()
                if confirm != 'y':
                    continue
            
            cli.journal(
                fund_code=code,
                action='buy',
                amount=amount,
                nav=nav,
                reason='定投',
                emotion='calm',
                reflection=''
            )
            print(f"{code} {name}：买入{amount}元 净值{nav:.4f}")
            total_invested += amount
        except Exception as e:
            print(f"{code} {name}：记录失败")
    
    if total_invested > 0:
        print(f"定投完成，共投入{total_invested}元。")
    else:
        print("今日无定投。")


def review(cli, verbose=False):
    """月底复盘：简洁格式输出，随机提问"""
    import random
    date_str = datetime.now().strftime('%Y-%m-%d')
    now = datetime.now()

    if verbose:
        print("="*50)
        print(f"月底复盘 - {date_str}")
        print("="*50)
        cli.review(year=now.year, month=now.month)
    else:
        print(f"{date_str} 月底复盘")
        cli.review(year=now.year, month=now.month)

    print("\n反思提示：")
    questions = [
        "本月最大的市场新闻是什么？",
        "你的信号系统给出了什么建议？你实际做了什么？",
        "本月有冲动交易吗？",
        "下个月你想调整什么？"
    ]

    for i, q in enumerate(questions, 1):
        print(f"{i}. {q}")

    # 随机从笔记或金句库中抽取
    try:
        notes = cli.knowledge_base.get_notes()
        quotes = cli.knowledge_base.get_quotes()

        random_items = []
        if notes:
            random_items.append(('note', random.choice(notes)))
        if quotes:
            random_items.append(('quote', random.choice(quotes)))

        if random_items:
            item_type, item = random.choice(random_items)
            print(f"\n随机回顾：")
            if item_type == 'note':
                print(f"  来自《{item.get('book', '未知')}》：{item.get('text', '')}")
                print(f"  问题：这个月你有做到吗？")
            else:
                print(f"  {item.get('text', '')} —— {item.get('author', '未知')}")
                print(f"  问题：这个月你有践行吗？")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description='日常操作脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 每日晨报（含信号）
  python daily.py --morning

  # 每日晨报（含反面观点）
  python daily.py --morning --devil

  # 每日晨报（安静模式）
  python daily.py --morning --quiet

  # 每日晨报（详细）
  python daily.py --morning --verbose

  # 每日晨报（含钉钉通知）
  python daily.py --morning --notify

  # 定投日记录
  python daily.py --invest

  # 月底复盘
  python daily.py --review
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--morning', action='store_true', help='每日晨报（含信号）')
    group.add_argument('--invest', action='store_true', help='定投日记录')
    group.add_argument('--review', action='store_true', help='月底复盘')

    parser.add_argument('--config', '-c', help='配置文件路径')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细信息')
    parser.add_argument('--quiet', '-q', action='store_true', help='安静模式（只显示重要信号）')
    parser.add_argument('--devil', action='store_true', help='显示反面观点（魔鬼代言人模式）')
    parser.add_argument('--notify', '-n', action='store_true', help='发送钉钉通知（仅在有重要信号时）')

    args = parser.parse_args()

    cli = FundInvestmentCLI(args.config)

    if args.morning:
        morning(cli, verbose=args.verbose, quiet=args.quiet, devil=args.devil, notify=args.notify)
    elif args.invest:
        invest(cli, verbose=args.verbose)
    elif args.review:
        review(cli, verbose=args.verbose)


if __name__ == "__main__":
    main()
