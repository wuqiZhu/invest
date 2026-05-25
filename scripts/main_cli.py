# -*- coding: utf-8 -*-
"""
基金投资分析主程序（命令行版本）
支持配置文件和命令行参数

免责声明：
本工具仅供个人学习和研究使用，所展示的数据均来自第三方公开接口。
不构成任何投资建议，据此操作风险自担。
基金投资有风险，过往业绩不代表未来表现。
"""

import sys
import os
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fund_data_fetcher import FundDataFetcher
from fund_data_fetcher_v2 import FundDataFetcherV2
from fund_analyzer import FundAnalyzer
from fund_analyzer_v2 import FundAnalyzerV2
from fund_database import FundDatabase
from config_manager import ConfigManager
from trading_system import TradingSystem
from knowledge_base import KnowledgeBase


class FundInvestmentCLI:
    """基金投资分析命令行工具"""
    
    def __init__(self, config_path=None):
        """
        初始化命令行工具
        
        Args:
            config_path: 配置文件路径
        """
        self.config = ConfigManager(config_path)
        self.fetcher = FundDataFetcherV2()
        self.analyzer = FundAnalyzerV2()
        self.db = FundDatabase(self.config.get('database.path', 'fund_data.db'))
        self.trading_system = TradingSystem(self.config, self.analyzer)
        self.knowledge_base = KnowledgeBase()
    
    def analyze(self, fund_codes=None, days=None):
        """
        分析基金
        
        Args:
            fund_codes: 基金代码列表，为None时使用配置文件中的基金
            days: 分析天数
        """
        if fund_codes is None:
            fund_codes = self.config.get_fund_codes()
        
        if days is None:
            days = self.config.get('analysis.default_days', 365)
        
        print(f"\n{'='*50}")
        print(f"基金分析 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}")
        
        for code in fund_codes:
            print(f"\n正在分析基金 {code}...")
            
            # 获取数据
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            fund_data = self.fetcher.get_fund_nav(code, start_date, end_date)
            
            if fund_data.empty:
                print(f"  无法获取基金 {code} 数据")
                continue
            
            # 分析基金
            analysis = self.analyzer.analyze_fund(fund_data, code)
            
            # 保存到数据库
            self.db.save_fund_nav(code, fund_data)
            self.db.save_analysis_result(code, analysis)
            
            # 打印结果
            print(f"  基金名称: {analysis.get('基金名称', 'N/A')}")
            print(f"  最新净值: {analysis.get('最新净值', 0):.4f}")
            print(f"  总收益率: {analysis.get('总收益率', 0):.2f}%")
            print(f"  年化收益率: {analysis.get('年化收益率', 0):.2f}%")
            print(f"  最大回撤: {analysis.get('最大回撤', 0):.2f}%")
            print(f"  波动率: {analysis.get('波动率', 0):.2f}%")
            print(f"  夏普比率: {analysis.get('夏普比率', 0):.4f}")
        
        print(f"\n{'='*50}")
        print("分析完成")
    
    def monitor(self, notify=False):
        """
        监控基金
        
        Args:
            notify: 是否发送通知
        """
        fund_codes = self.config.get_fund_codes()
        
        print(f"\n{'='*50}")
        print(f"基金监控 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}")
        
        alerts = []
        
        for code in fund_codes:
            print(f"\n正在检查基金 {code}...")
            
            # 获取实时信息
            fund_info = self.fetcher.get_fund_info(code)
            
            if not fund_info:
                print(f"  无法获取基金 {code} 信息")
                continue
            
            # 显示信息
            change_pct = fund_info.get('估算涨跌幅', 0)
            print(f"  基金名称: {fund_info.get('基金名称', 'N/A')}")
            print(f"  估算净值: {fund_info.get('估算净值', 0):.4f}")
            print(f"  估算涨跌幅: {change_pct:.2f}%")
            
            # 检查预警
            daily_threshold = self.config.get('alert.daily_drop_threshold', -3)
            if change_pct <= daily_threshold:
                alert_msg = f"[!] {code} {fund_info.get('基金名称', '')} 今日跌幅已达{change_pct}%，超过阈值{daily_threshold}%"
                alerts.append(alert_msg)
                print(f"  ** 预警: {alert_msg}")
        
        # 发送通知
        if notify and alerts:
            self._send_notifications(alerts)
        
        print(f"\n{'='*50}")
        print("监控完成")
        
        if alerts:
            print(f"\n共 {len(alerts)} 条预警")
    
    def backtest(self, fund_code, short_ma=None, long_ma=None):
        """
        回测策略
        
        Args:
            fund_code: 基金代码
            short_ma: 短期均线周期
            long_ma: 长期均线周期
        """
        if short_ma is None:
            short_ma = self.config.get('backtest.short_ma', 5)
        if long_ma is None:
            long_ma = self.config.get('backtest.long_ma', 20)
        
        print(f"\n{'='*50}")
        print(f"策略回测 - {fund_code}")
        print(f"{'='*50}")
        print(f"策略: 双均线 ({short_ma}日/{long_ma}日)")
        
        # 获取数据
        days = self.config.get('analysis.default_days', 365)
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        fund_data = self.fetcher.get_fund_nav(fund_code, start_date, end_date)
        
        if fund_data.empty:
            print(f"无法获取基金 {fund_code} 数据")
            return
        
        nav_series = fund_data['单位净值']
        
        # 执行回测
        signals = self._backtest_ma_strategy(nav_series, short_ma, long_ma)
        
        # 计算统计
        stats = self._calculate_backtest_stats(signals, nav_series)
        
        # 打印结果
        print(f"\n回测结果:")
        print(f"  初始资金: {stats.get('初始资金', 0):.2f} 元")
        print(f"  最终价值: {stats.get('最终价值', 0):.2f} 元")
        print(f"  总收益率: {stats.get('总收益率', 0):.2f}%")
        print(f"  总交易成本: {stats.get('总交易成本', 0):.2f} 元")
        print(f"  交易次数: {stats.get('交易次数', 0)} 次")
        
        # 打印交易记录
        trades = stats.get('交易记录', [])
        if trades:
            print(f"\n交易记录:")
            for trade in trades[-10:]:  # 只显示最近10条
                print(f"  {trade['date'].strftime('%Y-%m-%d')}: "
                      f"{trade['type']} @ {trade['price']:.4f}")
        
        print(f"\n{'='*50}")
    
    def simulate(self, fund_code=None, monthly_amount=None):
        """
        定投模拟
        
        Args:
            fund_code: 基金代码
            monthly_amount: 每月定投金额
        """
        if fund_code is None:
            fund_codes = self.config.get_fund_codes()
            if fund_codes:
                fund_code = fund_codes[0]
            else:
                print("未配置基金")
                return
        
        if monthly_amount is None:
            fund_info = self.config.get_fund_info(fund_code)
            monthly_amount = fund_info.get('monthly_invest', 500) if fund_info else 500
        
        print(f"\n{'='*50}")
        print(f"定投模拟 - {fund_code}")
        print(f"{'='*50}")
        print(f"每月定投: {monthly_amount} 元")
        
        # 获取数据
        days = self.config.get('analysis.default_days', 365)
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        fund_data = self.fetcher.get_fund_nav(fund_code, start_date, end_date)
        
        if fund_data.empty:
            print(f"无法获取基金 {fund_code} 数据")
            return
        
        # 执行定投模拟
        result = self.analyzer.simulate_dca(fund_data, monthly_amount)
        
        if not result:
            print("定投模拟失败")
            return
        
        # 打印结果
        print(f"\n定投结果:")
        print(f"  累计投入: {result['累计投入']:.2f} 元")
        print(f"  最终市值: {result['最终市值']:.2f} 元")
        print(f"  总收益率: {result['总收益率']:.2f}%")
        print(f"  投资月数: {result['投资月数']} 个月")
        
        print(f"\n{'='*50}")
    
    def list_funds(self):
        """列出配置中的基金"""
        funds = self.config.get('funds', [])
        
        print(f"\n{'='*50}")
        print(f"基金列表 ({len(funds)} 只)")
        print(f"{'='*50}")
        
        for fund in funds:
            status = "启用" if fund.get('enabled', True) else "禁用"
            print(f"\n  基金代码: {fund.get('code')}")
            print(f"  基金名称: {fund.get('name', 'N/A')}")
            print(f"  每月定投: {fund.get('monthly_invest', 0)} 元")
            print(f"  状态: {status}")
        
        print(f"\n{'='*50}")
    
    def show_config(self):
        """显示当前配置"""
        self.config.print_config()
    
    def compare(self, fund_code, benchmark_code='110030', days=365):
        """基金与基准对比"""
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"\n{'='*50}")
        print(f"基金 vs 基准对比 - {fund_code} vs {benchmark_code}")
        print(f"{'='*50}")
        
        fund_data = self.fetcher.get_fund_nav(fund_code, start_date, end_date)
        benchmark_data = self.fetcher.get_fund_nav(benchmark_code, start_date, end_date)
        
        if fund_data.empty:
            print(f"无法获取基金 {fund_code} 数据")
            return
        if benchmark_data.empty:
            print(f"无法获取基准 {benchmark_code} 数据")
            return
        
        result = self.analyzer.compare_with_benchmark(
            fund_data, benchmark_data, fund_code, benchmark_code)
        
        print(f"\n对比结果:")
        print(f"  基金收益率: {result['基金收益率']}%")
        print(f"  基准收益率: {result['基准收益率']}%")
        print(f"  超额收益: {result['超额收益']}%")
        print(f"  跟踪误差: {result['跟踪误差']}%")
        print(f"  信息比率: {result['信息比率']}")
        print(f"  {'跑赢基准!' if result['跑赢基准'] else '跑输基准'}")
        
        attribution = self.analyzer.style_attribution(fund_data, benchmark_data, fund_code, benchmark_code)
        if 'error' not in attribution:
            print(f"\n风格归因分析:")
            print(f"  信息比率: {attribution['信息比率']}")
            print(f"  跟踪误差: {attribution['跟踪误差']}%")
            print(f"  选股稳定性: {attribution['选股稳定性']}")
            print(f"  解读: {attribution['解读']}")
        
        print(f"\n{'='*50}")
    
    def run_wizard(self):
        """交互式向导模式"""
        print("\n" + "="*50)
        print("基金投资分析向导")
        print("="*50)
        
        fund_code = input("\n请输入基金代码（如110011）: ").strip()
        if not fund_code:
            print("基金代码不能为空")
            return
        
        monthly_amount = input("每月定投金额（元，默认500）: ").strip() or "500"
        threshold = input("日跌幅预警阈值（%，默认-3）: ").strip() or "-3"
        
        print("\n通知方式：1.控制台 2.微信 3.邮件")
        method = input("请选择（1-3，默认1）: ").strip() or "1"
        method_map = {'1': 'console', '2': 'wechat', '3': 'email'}
        
        self.config.add_fund(fund_code, '', int(monthly_amount))
        self.config.set('alert.daily_drop_threshold', float(threshold))
        self.config.set('notification.method', method_map.get(method, 'console'))
        self.config.save_config()
        
        print(f"\n配置完成！运行以下命令开始分析：")
        print(f"  python main_cli.py --action analyze --fund {fund_code}")
        print(f"  python main_cli.py --action simulate --fund {fund_code} --amount {monthly_amount}")
    
    def journal(self, fund_code, action, amount, nav, reason, emotion, reflection=""):
        """记录投资日志（含冷静期检查）"""
        if not self.check_cool_down(fund_code, action):
            confirm = input("是否仍然继续？(y/N): ").strip().lower()
            if confirm != 'y':
                print("操作已取消")
                return
        
        self.db.add_journal_entry(fund_code, action, amount, nav, reason, emotion, reflection)
        print(f"投资日志已记录: {fund_code} {action} {amount}元")
    
    def review(self, year=None, month=None):
        """月度复盘"""
        if year is None or month is None:
            now = datetime.now()
            year = now.year
            month = now.month
        
        print(f"\n{'='*50}")
        print(f"月度复盘 - {year}年{month}月")
        print(f"{'='*50}")
        
        results = self.db.review_month(year, month)
        
        if not results:
            print("本月暂无投资记录")
        else:
            for row in results:
                print(f"  {row['action']}: {row['count']}次, 总金额{row['total_amount']:.2f}元")
        
        entries = self.db.get_journal_entries(limit=10)
        if entries:
            print(f"\n最近投资日志:")
            for entry in entries:
                print(f"  {entry['date']} | {entry['fund_code']} | {entry['action']} | "
                      f"{entry['amount']}元 | 情绪:{entry['emotion']}")
                if entry['reason']:
                    print(f"    理由: {entry['reason']}")
        
        print(f"\n{'='*50}")
    
    def chart(self, fund_code, days=365):
        """生成交互式图表"""
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        fund_data = self.fetcher.get_fund_nav(fund_code, start_date, end_date)
        
        if fund_data.empty:
            print(f"无法获取基金 {fund_code} 数据")
            return
        
        self.analyzer.create_interactive_chart(fund_data, fund_code)
    
    def report(self, fund_code, days=365):
        """生成HTML报表"""
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        fund_data = self.fetcher.get_fund_nav(fund_code, start_date, end_date)
        
        if fund_data.empty:
            print(f"无法获取基金 {fund_code} 数据")
            return
        
        analysis = self.analyzer.analyze_fund(fund_data, fund_code)
        report_text = self.analyzer.generate_report(fund_data, fund_code)
        
        output_path = f"fund_{fund_code}_report.txt"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        print(f"分析报告已保存: {output_path}")
    
    def check_cool_down(self, fund_code, action):
        """检查冷静期和交易频率限制"""
        cool_down_days = self.config.get('behavioral.cool_down_days', 3)
        max_trades = self.config.get('behavioral.max_trades_per_month', 2)
        
        last_trade = self.db.get_last_trade(fund_code)
        if last_trade:
            last_date = datetime.strptime(last_trade['date'], '%Y-%m-%d %H:%M:%S')
            days_since = (datetime.now() - last_date).days
            if days_since < cool_down_days:
                print(f"冷静期提醒：距离上次操作仅{days_since}天，请等待{cool_down_days}天冷静期")
                return False
        
        monthly_count = self.db.get_monthly_trade_count(fund_code)
        if monthly_count >= max_trades:
            print(f"交易频率提醒：本月已交易{monthly_count}次，超过限制{max_trades}次")
            return False
        
        return True
    
    def random_review(self):
        """随机复盘：引导用户反思"""
        last_entry = self.db.get_journal_entries(limit=1)
        
        print("\n" + "="*50)
        print("随机复盘")
        print("="*50)
        
        if last_entry:
            last_date = datetime.strptime(last_entry[0]['date'], '%Y-%m-%d %H:%M:%S')
            days_ago = (datetime.now() - last_date).days
            print(f"\n距离你上次记录日志已经过去{days_ago}天。")
        else:
            print("\n你还没有任何投资日志记录。")
        
        questions = [
            "过去两周，市场最大的新闻是什么？它如何影响你的基金？",
            "你有没有想过要是当初卖出就好了？为什么？",
            "如果现在有5000元，你会怎么投？（不能回答和之前一样）",
        ]
        
        answers = []
        for i, q in enumerate(questions, 1):
            print(f"\n{i}. {q}")
            answer = input("你的回答: ").strip()
            answers.append(answer)
        
        if any(answers):
            fund_code = input("\n请输入相关基金代码（可选，直接回车跳过）: ").strip()
            if fund_code:
                self.db.add_journal_entry(
                    fund_code, 'review', 0, 0,
                    ' | '.join([f"Q{i+1}: {a}" for i, a in enumerate(answers)]),
                    'reflection', '随机复盘')
                print("复盘已保存到投资日志")
        
        print(f"\n{'='*50}")
    
    def devils_advocate_action(self, fund_code, days=365):
        """魔鬼代言人模式"""
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        fund_data = self.fetcher.get_fund_nav(fund_code, start_date, end_date)
        
        if fund_data.empty:
            print(f"无法获取基金 {fund_code} 数据")
            return
        
        analysis = self.analyzer.analyze_fund(fund_data, fund_code)
        
        benchmark_code = self.config.get('analysis.benchmark_code', '110030')
        benchmark_data = self.fetcher.get_fund_nav(benchmark_code, start_date, end_date)
        
        warnings = self.analyzer.devils_advocate(fund_data, fund_code, analysis, benchmark_data)
        mistakes = self.analyzer.check_common_mistakes(fund_data, fund_code, analysis)
        
        print(f"\n{'='*50}")
        print(f"魔鬼代言人说 - 基金 {fund_code}")
        print(f"{'='*50}")
        
        if warnings:
            print("\n反面观点：")
            for w in warnings:
                print(f"  - {w}")
        else:
            print("\n该基金目前没有明显的风险信号。")
        
        if mistakes:
            print("\n常见错误提醒：")
            for m in mistakes:
                print(f"  - {m['warning']}")
                print(f"    建议：{m['advice']}")
        
        print(f"\n{'='*50}")
    
    def buffet_bet_action(self, fund_code, benchmark_code='110030', days=1825):
        """巴菲特赌局模拟"""
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        fund_data = self.fetcher.get_fund_nav(fund_code, start_date, end_date)
        benchmark_data = self.fetcher.get_fund_nav(benchmark_code, start_date, end_date)
        
        if fund_data.empty or benchmark_data.empty:
            print("无法获取数据")
            return
        
        result = self.analyzer.buffet_bet(fund_data, benchmark_data, fund_code, benchmark_code)
        
        print(f"\n{'='*50}")
        print(f"巴菲特赌局模拟 - {fund_code} vs {benchmark_code}")
        print(f"{'='*50}")
        print(f"\n  基金 {fund_code} 收益率: {result['基金收益率']}%")
        print(f"  基准 {benchmark_code} 收益率: {result['基准收益率']}%")
        print(f"  持有年限: {result['持有年限']}年")
        print(f"  赢家: {result['赢家']}（领先{result['差距']}%）")
        print(f"\n  提示: {result['提示']}")
        print(f"\n{'='*50}")
    
    def daily_report(self):
        """生成每日简报"""
        funds = self.config.get('funds', [])
        
        print(f"\n{'='*50}")
        print(f"基金每日简报 - {datetime.now().strftime('%Y-%m-%d')}")
        print(f"{'='*50}")
        
        for fund in funds:
            if not fund.get('enabled', True):
                continue
            
            code = fund['code']
            name = fund.get('name', code)
            
            try:
                fund_info = self.fetcher.get_fund_info(code)
                if fund_info:
                    nav = fund_info.get('单位净值', 'N/A')
                    change = fund_info.get('估算涨跌幅', 0)
                    
                    print(f"\n{name}: 净值{nav} 涨跌幅{change}%")
                    
                    if change > 2:
                        print(f"   今日大涨，注意不要追高")
                    elif change < -2:
                        print(f"   今日大跌，冷静思考是否加仓")
                else:
                    print(f"\n{name}: 数据获取失败")
            except Exception as e:
                print(f"\n{name}: 数据获取失败 - {e}")
        
        method = self.config.get('notification.method', 'console')
        if method in ['wechat', 'email']:
            print(f"\n通知方式: {method}（功能已配置但需要webhook/邮箱信息）")
        
        print(f"\n{'='*50}")
    
    def signal(self, fund_code, days=365, devil=False):
        """获取模块化交易信号"""
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        fund_data = self.fetcher.get_fund_nav(fund_code, start_date, end_date)
        
        if fund_data.empty:
            print(f"无法获取基金 {fund_code} 数据")
            return
        
        result = self.trading_system.get_signal(fund_data, fund_code)
        
        print(f"\n{'='*50}")
        print(f"基金 {fund_code} 交易信号分析")
        print(f"{'='*50}")
        
        # 趋势模块
        trend = result['modules']['trend']
        status_icon = '[OK]' if trend['pass'] else '[X]'
        print(f"\n【趋势模块】{status_icon} {trend['status'].upper()}")
        print(f"  {trend['detail']}")
        
        # 波动模块
        vol = result['modules']['volatility']
        status_icon = '[OK]' if vol['pass'] else '[!]'
        print(f"\n【波动模块】{status_icon} {vol['status'].upper()}")
        print(f"  {vol['detail']}")
        
        # 买点模块
        entry = result['modules']['entry']
        status_icon = '[OK]' if entry['pass'] else '[X]'
        print(f"\n【买点模块】{status_icon} {entry['status'].upper()}")
        print(f"  {entry['detail']}")
        
        # 风控模块
        risk = result['modules']['risk']
        status_icon = '[OK]' if risk['pass'] else '[X]'
        print(f"\n【风控模块】{status_icon} {risk['status'].upper()}")
        print(f"  {risk['detail']}")
        
        # 止盈模块
        profit = result['modules']['profit']
        status_icon = '[OK]' if profit['pass'] else '[-]'
        print(f"\n【止盈模块】{status_icon} {profit['status'].upper()}")
        print(f"  {profit['detail']}")

        # 情绪模块
        sentiment = result['modules'].get('sentiment', {})
        if sentiment:
            status_icon = '[OK]' if sentiment.get('pass', True) else '[!]'
            print(f"\n【情绪模块】{status_icon} {sentiment.get('status', 'N/A').upper()}")
            print(f"  {sentiment.get('detail', '')}")

        # 综合决策
        signal_type = result['signal']
        advice = self.trading_system.get_advice(result)
        
        print(f"\n{'='*50}")
        print(f"【投资建议】")
        print(f"{'='*50}")
        print(f"当前趋势：{trend['status'].upper()}")
        print(f"波动率：{vol['status'].upper()}")
        print(f"建议：{advice}")
        print(f"{'='*50}")
        
        # 魔鬼代言人模式
        if devil:
            print(f"\n{'='*50}")
            print(f"[魔鬼代言人] 反面观点")
            print(f"{'='*50}")
            
            analysis = self.analyzer.analyze_fund(fund_data, fund_code)
            benchmark_code = self.config.get('analysis.benchmark_code', '110030')
            benchmark_data = self.fetcher.get_fund_nav(benchmark_code, start_date, end_date)
            
            warnings = self.analyzer.devils_advocate(fund_data, fund_code, analysis, benchmark_data)
            mistakes = self.analyzer.check_common_mistakes(fund_data, fund_code, analysis)
            
            if warnings:
                print("\n反面观点：")
                for w in warnings:
                    print(f"  - {w}")
            else:
                print("\n该基金目前没有明显的风险信号。")
            
            if mistakes:
                print("\n常见错误提醒：")
                for m in mistakes:
                    print(f"  - {m['warning']}")
                    print(f"    建议：{m['advice']}")
            
            print(f"{'='*50}")
    
    def timeline(self, fund_code=None, days=30):
        """显示时间线视图"""
        events = self.db.get_timeline(fund_code, days)
        
        print(f"\n{'='*50}")
        print(f"投资时间线（最近{days}天）")
        print(f"{'='*50}")
        
        if not events:
            print("\n暂无记录")
            return
        
        for event in events:
            date = event['date']
            event_type = event['type']
            detail = event['detail']
            reason = event.get('reason', '')
            emotion = event.get('emotion', '')
            
            print(f"\n{date} | {event_type} | {detail}")
            if reason:
                print(f"  理由：{reason}")
            if emotion:
                print(f"  情绪：{emotion}")
        
        print(f"\n{'='*50}")
        print(f"共 {len(events)} 条记录")
    
    def what_if(self, fund_code, amount=500, years=3):
        """假设定投分析"""
        start_date = (datetime.now() - timedelta(days=years*365)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        fund_data = self.fetcher.get_fund_nav(fund_code, start_date, end_date)
        
        if fund_data.empty:
            print(f"无法获取基金 {fund_code} 数据")
            return
        
        result = self.analyzer.what_if_dca(fund_data, amount, years)
        
        if 'error' in result:
            print(f"假设分析失败: {result['error']}")
            return
        
        print(f"\n{'='*50}")
        print(f"假设分析：{fund_code} 定投{years}年")
        print(f"{'='*50}")
        print(f"每月定投：{result['每月定投']}元")
        print(f"定投次数：{result['定投次数']}次")
        print(f"累计投入：{result['累计投入']}元")
        print(f"最终市值：{result['最终市值']}元")
        print(f"收益金额：{result['收益金额']}元")
        print(f"总收益率：{result['总收益率']}%")
        print(f"年化收益率：{result['年化收益率']}%")
        print(f"{'='*50}")
    
    def _backtest_ma_strategy(self, nav_series, short_ma, long_ma):
        """双均线策略回测"""
        signals = []
        position = False
        
        ma_short = nav_series.rolling(short_ma).mean()
        ma_long = nav_series.rolling(long_ma).mean()
        
        for i in range(long_ma, len(nav_series)):
            if ma_short.iloc[i] > ma_long.iloc[i] and not position:
                signals.append(('买入', nav_series.index[i], nav_series.iloc[i]))
                position = True
            elif ma_short.iloc[i] < ma_long.iloc[i] and position:
                signals.append(('卖出', nav_series.index[i], nav_series.iloc[i]))
                position = False
        
        return signals
    
    def _calculate_backtest_stats(self, signals, nav_series):
        """计算回测统计（含交易成本和滑点）"""
        if not signals:
            return {}
        
        initial_capital = self.config.get('backtest.initial_capital', 10000)
        commission = self.config.get('backtest.commission', 0.0015)
        slippage = self.config.get('backtest.slippage', 0.001)
        shares = 0
        capital = initial_capital
        trades = []
        total_cost = 0
        
        for signal_type, date, price in signals:
            if signal_type == '买入':
                actual_price = price * (1 + slippage)
                cost = capital * commission
                shares = (capital - cost) / actual_price
                total_cost += cost
                capital = 0
            elif signal_type == '卖出':
                actual_price = price * (1 - slippage)
                capital = shares * actual_price
                cost = capital * commission
                capital -= cost
                total_cost += cost
                shares = 0
            
            trades.append({
                'type': signal_type,
                'date': date,
                'price': price,
                'capital': capital,
                'shares': shares
            })
        
        final_value = capital + shares * nav_series.iloc[-1]
        total_return = (final_value - initial_capital) / initial_capital * 100
        
        return {
            '初始资金': initial_capital,
            '最终价值': round(final_value, 2),
            '总收益率': round(total_return, 2),
            '总交易成本': round(total_cost, 2),
            '交易次数': len(signals) // 2,
            '交易记录': trades
        }
    
    def _send_notifications(self, alerts):
        """发送通知"""
        method = self.config.get('notification.method', 'console')
        
        if method == 'console':
            print("\n" + "="*50)
            print("预警通知")
            print("="*50)
            for alert in alerts:
                print(alert)
        
        elif method == 'wechat':
            webhook_url = self.config.get('notification.wechat.webhook_url')
            if webhook_url:
                import requests
                content = "\n".join(alerts)
                data = {"msgtype": "text", "text": {"content": content}}
                try:
                    requests.post(webhook_url, json=data, timeout=10)
                    print("微信通知已发送")
                except Exception as e:
                    print(f"微信通知失败: {e}")
            else:
                print("未配置微信webhook")
        
        elif method == 'dingtalk':
            webhook_url = self.config.get('notification.dingtalk.webhook_url')
            secret = self.config.get('notification.dingtalk.secret')
            if webhook_url:
                from fund_notifier import FundNotifier
                notifier = FundNotifier(self.config.get('notification', {}))
                content = "\n".join(alerts)
                notifier.send_dingtalk(content, webhook_url, secret)
            else:
                print("未配置钉钉webhook")
        
        elif method == 'email':
            # 邮件通知实现
            print("邮件通知功能待实现")
    
    def show_books(self, level=None, focus=None, recommended=False):
        """显示推荐书籍"""
        books = self.knowledge_base.get_books(level=level, focus=focus, recommended_only=recommended)
        
        print("\n" + "="*50)
        print("投资书籍推荐")
        print("="*50)
        
        if not books:
            print("\n暂无符合条件的书籍")
            return
        
        for book in books:
            star = "★" if book['recommended'] else "☆"
            print(f"\n{star} {book['title']}")
            print(f"  作者: {book['author']} ({book['year']})")
            print(f"  级别: {book['level']} | 主题: {book['focus']}")
            print(f"  核心要点: {', '.join(book['key_points'])}")
        
        print(f"\n共 {len(books)} 本书")
    
    def show_quotes(self, author=None, context=None):
        """显示投资金句"""
        quotes = self.knowledge_base.get_quotes(author=author, context=context)
        
        print("\n" + "="*50)
        print("投资智慧金句")
        print("="*50)
        
        if not quotes:
            print("\n暂无符合条件的金句")
            return
        
        for quote in quotes:
            print(f"\n  {quote['quote']}")
            print(f"  ——{quote['author']} ({quote['source']})")
        
        print(f"\n共 {len(quotes)} 条金句")
    
    def check_risk(self, text):
        """检查文本中的风险关键词"""
        risks = self.knowledge_base.check_risk(text)
        
        print("\n" + "="*50)
        print("风险检测结果")
        print("="*50)
        
        if not risks:
            print(f"\n[OK] 未发现风险关键词")
            print(f"检测文本: {text[:50]}...")
        else:
            print(f"\n[!] 发现 {len(risks)} 个风险关键词:")
            for risk in risks:
                print(f"\n  类型: {risk['type']}")
                print(f"  关键词: {risk['keyword']}")
                print(f"  风险等级: {risk['risk_level']}")
                print(f"  警告: {risk['warning']}")
        
        print(f"\n{'='*50}")
    
    def add_note(self, book, quote, reflection=""):
        """添加笔记"""
        note = self.knowledge_base.add_note(book, quote, reflection)
        print(f"\n笔记已添加:")
        print(f"  书籍: {note['book']}")
        print(f"  摘录: {note['quote']}")
        if note['reflection']:
            print(f"  反思: {note['reflection']}")
        print(f"  时间: {note['date']}")
    
    def list_notes(self, book=None, keyword=None):
        """列出笔记"""
        notes = self.knowledge_base.get_notes(book=book, keyword=keyword)
        
        print(f"\n{'='*50}")
        print("投资笔记")
        print(f"{'='*50}")
        
        if not notes:
            print("\n暂无笔记")
            return
        
        for note in notes:
            print(f"\n{note['date']}")
            print(f"  书籍: {note['book']}")
            print(f"  摘录: {note['quote']}")
            if note.get('reflection'):
                print(f"  反思: {note['reflection']}")
        
        print(f"\n{'='*50}")
        print(f"共 {len(notes)} 条笔记")


DANGER_MESSAGE = """
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
WARNING: 你正在试图预测市场！
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

历史数据显示，超过80%的散户频繁择时会导致收益低于买入持有。

建议你先运行：
  python main_cli.py --action simulate --fund CODE

对比一下定投与一次性投入的收益差异。

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
"""


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='基金投资分析工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
核心命令:
  python main_cli.py --action signal --fund 110011          # 交易信号
  python main_cli.py --action signal --fund 110011 --devil  # 信号+反面观点
  python main_cli.py --action what-if --fund 110011         # 假设分析
  python main_cli.py --action note --book "聪明的投资者" --text "安全边际"  # 笔记
  python main_cli.py --wizard                               # 向导模式
  python main_cli.py --action list                          # 列出基金
  python main_cli.py --action config                        # 显示配置

独立脚本:
  python daily.py --morning                                 # 晨报（含信号）
  python daily.py --invest                                  # 定投
  python daily.py --review                                  # 复盘
  python knowledge.py --books                               # 书籍推荐
  python knowledge.py --quotes                              # 投资金句
  python knowledge.py --check-risk --text "保本保息"         # 风险检测
  python analysis_tools.py --help                           # 高级分析工具
        """
    )
    
    parser.add_argument('--config', '-c', help='配置文件路径')
    parser.add_argument('--action', '-a',
                       choices=['signal', 'what-if', 'note', 'config', 'list', 'sentiment'],
                       help='执行的操作（核心命令）')
    parser.add_argument('--fund', '-f', nargs='+', help='基金代码')
    parser.add_argument('--days', '-d', type=int, help='分析天数')
    parser.add_argument('--amount', type=int, help='定投金额')
    parser.add_argument('--wizard', action='store_true', help='交互式向导模式')
    parser.add_argument('--book', help='书籍名称（用于note）')
    parser.add_argument('--text', help='笔记内容（用于note）')
    parser.add_argument('--years', type=int, default=3, help='定投年数（用于what-if）')
    parser.add_argument('--devil', action='store_true', help='显示反面观点（魔鬼代言人模式，用于signal）')
    parser.add_argument('--news-api', action='store_true', help='启动新闻情绪API服务')

    args = parser.parse_args()

    # 启动新闻 API 服务
    if args.news_api:
        from news_api_server import run_server
        host = cli.config.get('news_api.host', '0.0.0.0')
        port = cli.config.get('news_api.port', 5000)
        run_server(host, port, args.config)
        return

    # 向导模式
    if args.wizard:
        cli = FundInvestmentCLI(args.config)
        cli.run_wizard()
        return
    
    # 初始化CLI
    cli = FundInvestmentCLI(args.config)

    # 核心命令
    if not args.action:
        parser.print_help()
        return
    
    # 执行核心命令
    if args.action == 'signal':
        if not args.fund:
            print("信号分析需要指定基金代码: --fund CODE")
            return
        cli.signal(args.fund[0], args.days or 365, devil=args.devil)
    
    elif args.action == 'what-if':
        if not args.fund:
            print("假设分析需要指定基金代码: --fund CODE")
            return
        cli.what_if(args.fund[0], args.amount or 500, args.years or 3)
    
    elif args.action == 'note':
        if args.book and args.text:
            cli.add_note(args.book, args.text, args.reflection or '')
        else:
            cli.list_notes(book=args.book, keyword=args.text)
    
    elif args.action == 'config':
        cli.show_config()

    elif args.action == 'list':
        cli.list_funds()

    elif args.action == 'sentiment':
        show_sentiment(cli, args.fund[0] if args.fund else None, args.days or 7)


def show_sentiment(cli, fund_code=None, days=7):
    """显示新闻情绪数据"""
    print(f"\n{'='*50}")
    print(f"新闻情绪分析")
    print(f"{'='*50}")

    summary = cli.db.get_sentiment_summary(days)
    print(f"\n最近{days}天情绪摘要:")
    print(f"  平均情绪分: {summary['avg_sentiment']:.4f}")
    print(f"  平均财经分: {summary['avg_finance']:.4f}")
    print(f"  正面新闻: {summary['total_positive']}条")
    print(f"  负面新闻: {summary['total_negative']}条")
    print(f"  中性新闻: {summary['total_neutral']}条")
    print(f"  总新闻数: {summary['total_news']}条")

    recent = cli.db.get_recent_sentiment(fund_code, days)
    if recent:
        print(f"\n每日情绪详情:")
        for item in recent:
            score = item['sentiment_score']
            icon = '[+]' if score > 0.2 else '[-]' if score < -0.2 else '[~]'
            print(f"  {icon} {item['date']}: 情绪{score:.4f} "
                  f"(财经{item['finance_score']:.4f}, {item['total_count']}条)")
            if item.get('top_keywords'):
                print(f"      关键词: {item['top_keywords']}")
    else:
        print("\n暂无情绪数据")

    print(f"\n{'='*50}")


if __name__ == "__main__":
    main()