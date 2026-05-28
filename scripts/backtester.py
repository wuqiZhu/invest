# -*- coding: utf-8 -*-
import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config_manager import ConfigManager
from fund_data_fetcher import FundDataFetcher
from fund_database import FundDatabase


class Backtester:
    def __init__(self, config_path=None):
        self.config = ConfigManager(config_path)
        self.fetcher = FundDataFetcher()
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fund_data.db')
        self.db = FundDatabase(db_path)

    def run_backtest(self, fund_code, start_date=None, end_date=None, initial_capital=10000):
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        nav_data = self.fetcher.get_fund_nav(fund_code, start_date, end_date)
        if nav_data is None or nav_data.empty:
            print(f"  {fund_code}: 无数据")
            return None

        print(f"  {fund_code}: 获取到 {len(nav_data)} 条数据")

        navs = nav_data['单位净值'].values
        dates = nav_data.index.tolist()

        if len(navs) < 21:
            return None

        capital = initial_capital
        shares = 0
        avg_cost = 0
        trades = []
        equity_curve = []

        for i in range(20, len(navs)):
            current_nav = navs[i]
            ma5 = navs[i-5:i].mean()
            ma10 = navs[i-10:i].mean()
            ma20 = navs[i-20:i].mean()

            momentum_score = 0.5
            if current_nav > ma5 > ma10 > ma20:
                momentum_score = 0.8
            elif current_nav > ma5 > ma10:
                momentum_score = 0.7
            elif current_nav > ma5:
                momentum_score = 0.6
            elif current_nav < ma5 < ma10 < ma20:
                momentum_score = 0.2
            elif current_nav < ma5 < ma10:
                momentum_score = 0.3
            elif current_nav < ma5:
                momentum_score = 0.4

            returns = [(navs[j] - navs[j-1]) / navs[j-1] for j in range(max(1, i-20), i)]
            volatility = (sum(r**2 for r in returns) / len(returns)) ** 0.5 if returns else 0.01

            volatility_score = 0.5
            if volatility < 0.005:
                volatility_score = 0.7
            elif volatility < 0.01:
                volatility_score = 0.6
            elif volatility > 0.03:
                volatility_score = 0.3
            elif volatility > 0.02:
                volatility_score = 0.4

            composite = momentum_score * 0.6 + volatility_score * 0.4

            total_value = capital + shares * current_nav
            equity_curve.append({
                'date': dates[i].strftime('%Y-%m-%d'),
                'nav': current_nav,
                'capital': capital,
                'shares': shares,
                'total_value': total_value
            })

            profit_rate = (current_nav - avg_cost) / avg_cost if avg_cost > 0 and shares > 0 else 0

            if shares > 0 and profit_rate > 0.05:
                sell_shares = shares * 0.5
                sell_amount = sell_shares * current_nav
                shares -= sell_shares
                capital += sell_amount
                if shares == 0:
                    avg_cost = 0
                trades.append({
                    'date': dates[i].strftime('%Y-%m-%d'),
                    'action': 'take_profit',
                    'nav': current_nav,
                    'shares': sell_shares,
                    'amount': sell_amount,
                    'profit_rate': round(profit_rate * 100, 2)
                })
            elif composite > 0.58 and capital > 100:
                buy_amount = min(capital * 0.5, 1000)
                buy_shares = buy_amount / current_nav
                if shares > 0:
                    avg_cost = (avg_cost * shares + current_nav * buy_shares) / (shares + buy_shares)
                else:
                    avg_cost = current_nav
                shares += buy_shares
                capital -= buy_amount
                trades.append({
                    'date': dates[i].strftime('%Y-%m-%d'),
                    'action': 'buy',
                    'nav': current_nav,
                    'shares': buy_shares,
                    'amount': buy_amount,
                    'composite': composite
                })
            elif composite < 0.40 and shares > 0:
                sell_shares = shares * 0.5
                sell_amount = sell_shares * current_nav
                shares -= sell_shares
                capital += sell_amount
                if shares == 0:
                    avg_cost = 0
                trades.append({
                    'date': dates[i].strftime('%Y-%m-%d'),
                    'action': 'sell',
                    'nav': current_nav,
                    'shares': sell_shares,
                    'amount': sell_amount,
                    'composite': composite
                })

        final_value = capital + shares * navs[-1]
        total_return = (final_value - initial_capital) / initial_capital * 100

        buy_and_hold_shares = initial_capital / navs[20]
        buy_and_hold_value = buy_and_hold_shares * navs[-1]
        buy_and_hold_return = (buy_and_hold_value - initial_capital) / initial_capital * 100

        return {
            'fund_code': fund_code,
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': initial_capital,
            'final_value': round(final_value, 2),
            'total_return': round(total_return, 2),
            'buy_and_hold_return': round(buy_and_hold_return, 2),
            'excess_return': round(total_return - buy_and_hold_return, 2),
            'total_trades': len(trades),
            'trades': trades,
            'equity_curve': equity_curve
        }

    def run_multi_fund_backtest(self, fund_codes=None, start_date=None, end_date=None):
        if fund_codes is None:
            fund_codes = self.config.get_fund_codes()

        results = {}
        for code in fund_codes:
            result = self.run_backtest(code, start_date, end_date)
            if result:
                results[code] = result

        return results

    def print_summary(self, results):
        print("\n" + "=" * 60)
        print("回测结果汇总")
        print("=" * 60)

        for code, result in results.items():
            print(f"\n基金: {code}")
            print(f"  期间: {result['start_date']} ~ {result['end_date']}")
            print(f"  初始资金: {result['initial_capital']}元")
            print(f"  最终价值: {result['final_value']}元")
            print(f"  策略收益: {result['total_return']}%")
            print(f"  买入持有: {result['buy_and_hold_return']}%")
            print(f"  超额收益: {result['excess_return']}%")
            print(f"  交易次数: {result['total_trades']}")

        print("\n" + "=" * 60)


if __name__ == '__main__':
    backtester = Backtester()

    fund_codes = backtester.config.get_fund_codes()
    if not fund_codes:
        fund_codes = ['110011']

    results = backtester.run_multi_fund_backtest(fund_codes)
    backtester.print_summary(results)
