# -*- coding: utf-8 -*-
"""
持仓日报模块
生成详细的持仓日报，包括盈亏详情、技术信号、止盈止损预警
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config_manager import ConfigManager
from execution_engine import ExecutionEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_daily_report(config_path=None):
    """生成持仓日报"""
    config = ConfigManager(config_path)
    executor = ExecutionEngine(config_path)

    today = datetime.now().strftime('%Y-%m-%d')
    lines = []

    lines.append(f"📊 持仓日报 {today}")
    lines.append("=" * 30)

    portfolio = executor.get_portfolio_summary()

    lines.append("")
    lines.append("💰 投资组合总览")
    lines.append(f"总资产: ¥{portfolio.get('total_value', 0):,.2f}")
    lines.append(f"总投入: ¥{portfolio.get('total_invested', 0):,.2f}")
    profit = portfolio.get('total_value', 0) - portfolio.get('total_invested', 0)
    profit_rate = (profit / portfolio.get('total_invested', 1)) * 100
    lines.append(f"总收益: ¥{profit:,.2f} ({profit_rate:+.2f}%)")

    lines.append("")
    lines.append("📈 基金详情")
    lines.append("-" * 30)

    holdings = portfolio.get('holdings', [])
    for holding in holdings:
        fund_code = holding.get('fund_code', '')
        fund_name = holding.get('fund_name', fund_code)
        nav = holding.get('current_nav', 0)
        cost = holding.get('avg_cost', 0)
        shares = holding.get('shares', 0)
        value = holding.get('current_value', 0)
        invested = holding.get('total_invested', 0)
        pnl = value - invested
        pnl_rate = (pnl / invested * 100) if invested > 0 else 0

        lines.append(f"┌─────────────────────────────────────┐")
        lines.append(f"│ {fund_code} {fund_name}")
        lines.append(f"│ 净值: {nav:.4f} | 成本: {cost:.4f} | 份额: {shares:.2f}")
        lines.append(f"│ 市值: ¥{value:,.2f} | 投入: ¥{invested:,.2f}")
        lines.append(f"│ 盈亏: ¥{pnl:,.2f} ({pnl_rate:+.2f}%)")

        if pnl_rate >= 15:
            lines.append(f"│ 🔴 接近止盈线(+20%)")
        elif pnl_rate <= -8:
            lines.append(f"│ ⚠️ 接近止损线(-10%)")

        lines.append(f"└─────────────────────────────────────┘")

    alerts = executor.check_take_profit_stop_loss(take_profit=20, stop_loss=-10)
    if alerts:
        lines.append("")
        lines.append("🚨 止盈止损预警")
        lines.append("-" * 30)
        for alert in alerts:
            action = "止盈" if alert['action'] == 'take_profit' else "止损"
            lines.append(f"⚠️ {alert['fund_code']}: {action}信号 (盈亏: {alert['profit_rate']:.2f}%)")

    lines.append("")
    lines.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return "\n".join(lines)


def send_report_to_dingtalk(report_text):
    """发送日报到钉钉"""
    import requests

    webhook_url = os.environ.get('DINGTALK_WEBHOOK_URL')
    if not webhook_url:
        logger.warning("钉钉 Webhook 未配置")
        return False

    payload = {
        "msgtype": "text",
        "text": {"content": report_text}
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('errcode') == 0:
                logger.info("日报发送成功")
                return True
            else:
                logger.error(f"发送失败: {result}")
        else:
            logger.error(f"HTTP错误: {response.status_code}")
    except Exception as e:
        logger.error(f"发送异常: {e}")

    return False


if __name__ == '__main__':
    report = generate_daily_report()
    print(report)

    if '--send' in sys.argv:
        send_report_to_dingtalk(report)
