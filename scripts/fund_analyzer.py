# -*- coding: utf-8 -*-
"""
基金分析模块

免责声明：
本工具仅供个人学习和研究使用，所展示的数据均来自第三方公开接口。
不构成任何投资建议，据此操作风险自担。
基金投资有风险，过往业绩不代表未来表现。
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class FundAnalyzer:
    """基金分析类"""
    
    def __init__(self):
        pass
    
    def calculate_returns(self, nav_series):
        """
        计算收益率指标
        
        Args:
            nav_series: 净值序列
        
        Returns:
            dict: 收益率指标
        """
        if len(nav_series) < 2:
            return {}
        
        # 总收益率
        total_return = (nav_series.iloc[-1] / nav_series.iloc[0] - 1) * 100
        
        # 年化收益率
        days = (nav_series.index[-1] - nav_series.index[0]).days
        if days > 0:
            annualized_return = (nav_series.iloc[-1] / nav_series.iloc[0]) ** (365 / days) - 1
            annualized_return = annualized_return * 100
        else:
            annualized_return = 0
        
        # 最大回撤
        peak = nav_series.expanding(min_periods=1).max()
        drawdown = (nav_series - peak) / peak
        max_drawdown = drawdown.min() * 100
        
        # 波动率（年化）
        daily_returns = nav_series.pct_change().dropna()
        volatility = daily_returns.std() * np.sqrt(252) * 100
        
        # 夏普比率（假设无风险利率为3%）
        risk_free_rate = 0.03
        excess_return = annualized_return / 100 - risk_free_rate
        sharpe_ratio = excess_return / (volatility / 100) if volatility > 0 else 0
        
        return {
            '总收益率': round(total_return, 4),
            '年化收益率': round(annualized_return, 4),
            '最大回撤': round(max_drawdown, 4),
            '波动率': round(volatility, 4),
            '夏普比率': round(sharpe_ratio, 4)
        }
    
    def analyze_fund(self, fund_data, fund_code=""):
        """
        分析单只基金
        
        Args:
            fund_data: 基金净值数据
            fund_code: 基金代码
        
        Returns:
            dict: 分析结果
        """
        if fund_data.empty:
            return {}
        
        nav_series = fund_data['单位净值']
        
        # 基本统计
        basic_stats = {
            '基金代码': fund_code,
            '最新净值': nav_series.iloc[-1],
            '最高净值': nav_series.max(),
            '最低净值': nav_series.min(),
            '平均净值': nav_series.mean(),
            '净值标准差': nav_series.std(),
            '数据天数': len(nav_series),
            '开始日期': nav_series.index[0].strftime('%Y-%m-%d'),
            '结束日期': nav_series.index[-1].strftime('%Y-%m-%d')
        }
        
        # 收益率指标
        return_metrics = self.calculate_returns(nav_series)
        
        # 月度收益
        monthly_returns = nav_series.resample('M').last().pct_change().dropna()
        monthly_stats = {
            '月均收益率': round(monthly_returns.mean() * 100, 4),
            '月收益标准差': round(monthly_returns.std() * 100, 4),
            '正收益月数': len(monthly_returns[monthly_returns > 0]),
            '负收益月数': len(monthly_returns[monthly_returns < 0])
        }
        
        # 合并所有指标
        analysis = {**basic_stats, **return_metrics, **monthly_stats}
        
        return analysis
    
    def compare_funds(self, funds_data):
        """
        对比多只基金
        
        Args:
            funds_data: 基金数据字典
        
        Returns:
            DataFrame: 对比结果
        """
        comparison = []
        
        for fund_code, fund_data in funds_data.items():
            if not fund_data.empty:
                analysis = self.analyze_fund(fund_data, fund_code)
                comparison.append(analysis)
        
        if comparison:
            df = pd.DataFrame(comparison)
            df = df.set_index('基金代码')
            return df
        else:
            return pd.DataFrame()
    
    def simulate_dca(self, fund_data, monthly_amount=500, start_date=None):
        """
        定投模拟
        
        Args:
            fund_data: 基金净值数据
            monthly_amount: 每月定投金额
            start_date: 开始定投日期
        
        Returns:
            dict: 定投结果
        """
        if fund_data.empty:
            return {}
        
        # 筛选定投期间数据
        if start_date:
            invest_data = fund_data[start_date:]
        else:
            invest_data = fund_data
        
        if invest_data.empty:
            return {}
        
        # 按月定投
        monthly_data = invest_data.resample('M').first()
        
        total_shares = 0
        total_invested = 0
        invest_history = []
        
        for date, row in monthly_data.iterrows():
            nav = row['单位净值']
            shares = monthly_amount / nav
            total_shares += shares
            total_invested += monthly_amount
            
            invest_history.append({
                '日期': date,
                '净值': nav,
                '份额': shares,
                '累计份额': total_shares,
                '累计投入': total_invested,
                '当前市值': total_shares * nav
            })
        
        # 计算定投收益
        final_nav = invest_data['单位净值'].iloc[-1]
        final_value = total_shares * final_nav
        total_return = (final_value - total_invested) / total_invested * 100
        
        return {
            '累计投入': round(total_invested, 2),
            '累计份额': round(total_shares, 4),
            '最终市值': round(final_value, 2),
            '总收益率': round(total_return, 4),
            '投资月数': len(monthly_data),
            '定投历史': invest_history
        }
    
    def plot_fund_performance(self, fund_data, fund_code, save_path=None):
        """
        绘制基金表现图表
        
        Args:
            fund_data: 基金净值数据
            fund_code: 基金代码
            save_path: 保存路径
        """
        if fund_data.empty:
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # 净值走势
        axes[0, 0].plot(fund_data.index, fund_data['单位净值'], label=fund_code, color='blue')
        axes[0, 0].set_title(f'基金 {fund_code} 净值走势')
        axes[0, 0].set_xlabel('日期')
        axes[0, 0].set_ylabel('单位净值')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # 收益率分布
        daily_returns = fund_data['单位净值'].pct_change().dropna()
        axes[0, 1].hist(daily_returns * 100, bins=50, alpha=0.7, color='green')
        axes[0, 1].set_title('日收益率分布')
        axes[0, 1].set_xlabel('收益率 (%)')
        axes[0, 1].set_ylabel('频次')
        axes[0, 1].grid(True, alpha=0.3)
        
        # 累计收益
        cumulative_returns = (1 + daily_returns).cumprod() - 1
        axes[1, 0].plot(cumulative_returns.index, cumulative_returns * 100, color='red')
        axes[1, 0].set_title('累计收益率')
        axes[1, 0].set_xlabel('日期')
        axes[1, 0].set_ylabel('累计收益率 (%)')
        axes[1, 0].grid(True, alpha=0.3)
        
        # 回撤分析
        nav_series = fund_data['单位净值']
        peak = nav_series.expanding(min_periods=1).max()
        drawdown = (nav_series - peak) / peak * 100
        axes[1, 1].fill_between(drawdown.index, drawdown, 0, alpha=0.3, color='red')
        axes[1, 1].set_title('回撤分析')
        axes[1, 1].set_xlabel('日期')
        axes[1, 1].set_ylabel('回撤 (%)')
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"图表已保存到: {save_path}")
        
        plt.show()
    
    def generate_report(self, fund_data, fund_code):
        """
        生成基金分析报告
        
        Args:
            fund_data: 基金净值数据
            fund_code: 基金代码
        
        Returns:
            str: 分析报告
        """
        if fund_data.empty:
            return "无法生成报告：数据为空"
        
        analysis = self.analyze_fund(fund_data, fund_code)
        
        report = f"""
基金分析报告 - {fund_code}
{'='*50}

一、基本信息
- 基金代码: {analysis.get('基金代码', '')}
- 数据范围: {analysis.get('开始日期', '')} 至 {analysis.get('结束日期', '')}
- 数据天数: {analysis.get('数据天数', 0)} 天

二、净值统计
- 最新净值: {analysis.get('最新净值', 0):.4f}
- 最高净值: {analysis.get('最高净值', 0):.4f}
- 最低净值: {analysis.get('最低净值', 0):.4f}
- 平均净值: {analysis.get('平均净值', 0):.4f}

三、收益指标
- 总收益率: {analysis.get('总收益率', 0):.2f}%
- 年化收益率: {analysis.get('年化收益率', 0):.2f}%
- 最大回撤: {analysis.get('最大回撤', 0):.2f}%
- 波动率: {analysis.get('波动率', 0):.2f}%
- 夏普比率: {analysis.get('夏普比率', 0):.4f}

四、月度表现
- 月均收益率: {analysis.get('月均收益率', 0):.2f}%
- 月收益标准差: {analysis.get('月收益标准差', 0):.2f}%
- 正收益月数: {analysis.get('正收益月数', 0)} 个月
- 负收益月数: {analysis.get('负收益月数', 0)} 个月

五、风险评估
"""
        
        # 风险评估
        max_drawdown = abs(analysis.get('最大回撤', 0))
        volatility = analysis.get('波动率', 0)
        
        if max_drawdown < 10:
            risk_level = "低风险"
        elif max_drawdown < 20:
            risk_level = "中风险"
        else:
            risk_level = "高风险"
        
        report += f"- 风险等级: {risk_level}\n"
        report += f"- 最大回撤: {max_drawdown:.2f}%\n"
        report += f"- 波动率: {volatility:.2f}%\n"
        
        return report


# 使用示例
if __name__ == "__main__":
    from fund_data_fetcher import FundDataFetcher
    
    fetcher = FundDataFetcher()
    analyzer = FundAnalyzer()
    
    # 获取基金数据
    fund_code = "110011"
    fund_data = fetcher.get_fund_nav(fund_code)
    
    if not fund_data.empty:
        # 生成分析报告
        report = analyzer.generate_report(fund_data, fund_code)
        print(report)
        
        # 绘制图表
        analyzer.plot_fund_performance(fund_data, fund_code, f"fund_{fund_code}_analysis.png")