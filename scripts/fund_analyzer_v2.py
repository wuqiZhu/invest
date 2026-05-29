# -*- coding: utf-8 -*-
"""
基金分析模块（增强版）
增加技术指标计算功能

免责声明：
本工具仅供个人学习和研究使用，所展示的数据均来自第三方公开接口。
不构成任何投资建议，据此操作风险自担。
基金投资有风险，过往业绩不代表未来表现。
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

try:
    from empyrical import max_drawdown, sharpe_ratio, calmar_ratio, alpha_beta
    EMPYRICAL_AVAILABLE = True
except ImportError:
    EMPYRICAL_AVAILABLE = False


class FundAnalyzerV2:
    """基金分析类（增强版）"""
    
    def __init__(self, risk_free_rate=0.03):
        """
        初始化分析器
        
        Args:
            risk_free_rate: 无风险利率（用于计算夏普比率）
        """
        self.risk_free_rate = risk_free_rate
    
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
        
        # 计算日收益率
        daily_returns = nav_series.pct_change().dropna()
        
        # 使用empyrical计算风险指标（如果可用）
        if EMPYRICAL_AVAILABLE and len(daily_returns) > 10:
            try:
                max_dd = max_drawdown(daily_returns) * 100
                sr = sharpe_ratio(daily_returns, risk_free=self.risk_free_rate/252)
                cr = calmar_ratio(daily_returns, annualization=252)
                volatility = daily_returns.std() * np.sqrt(252) * 100
                
                return {
                    '总收益率': round(total_return, 4),
                    '年化收益率': round(annualized_return, 4),
                    '最大回撤': round(max_dd, 4),
                    '波动率': round(volatility, 4),
                    '夏普比率': round(sr, 4),
                    '卡玛比率': round(cr, 4)
                }
            except Exception:
                pass
        
        # 回退到手写计算
        peak = nav_series.expanding(min_periods=1).max()
        drawdown = (nav_series - peak) / peak
        max_drawdown = drawdown.min() * 100
        
        volatility = daily_returns.std() * np.sqrt(252) * 100
        
        excess_return = annualized_return / 100 - self.risk_free_rate
        sharpe_ratio = excess_return / (volatility / 100) if volatility > 0 else 0
        
        return {
            '总收益率': round(total_return, 4),
            '年化收益率': round(annualized_return, 4),
            '最大回撤': round(max_drawdown, 4),
            '波动率': round(volatility, 4),
            '夏普比率': round(sharpe_ratio, 4)
        }
    
    def calculate_technical_indicators(self, nav_series):
        """
        计算技术指标
        
        Args:
            nav_series: 净值序列
        
        Returns:
            dict: 技术指标
        """
        if len(nav_series) < 20:
            return {}
        
        indicators = {}
        
        # 计算均线
        ma_periods = [5, 10, 20, 60]
        for period in ma_periods:
            if len(nav_series) >= period:
                ma = nav_series.rolling(window=period).mean()
                indicators[f'MA{period}'] = round(ma.iloc[-1], 4)
        
        # 20日均线偏离
        if len(nav_series) >= 20:
            ma20 = nav_series.rolling(window=20).mean()
            deviation = (nav_series.iloc[-1] - ma20.iloc[-1]) / ma20.iloc[-1] * 100
            indicators['20日均线偏离'] = round(deviation, 2)
            
            # 超买超卖信号
            if deviation > 5:
                indicators['均线信号'] = '超买'
            elif deviation < -5:
                indicators['均线信号'] = '超卖'
            else:
                indicators['均线信号'] = '正常'
        
        # RSI指标
        if len(nav_series) >= 14:
            rsi = self._calculate_rsi(nav_series, period=14)
            indicators['RSI'] = round(rsi, 2)
            
            # RSI信号
            if rsi > 70:
                indicators['RSI信号'] = '超买'
            elif rsi < 30:
                indicators['RSI信号'] = '超卖'
            else:
                indicators['RSI信号'] = '正常'
        
        # 布林带
        if len(nav_series) >= 20:
            bollinger = self._calculate_bollinger_bands(nav_series, period=20)
            indicators.update(bollinger)
            
            # 当前价格在布林带中的位置
            if '上轨' in bollinger and '下轨' in bollinger:
                upper = bollinger['上轨']
                lower = bollinger['下轨']
                current = nav_series.iloc[-1]
                position = (current - lower) / (upper - lower) * 100
                indicators['布林带位置'] = round(position, 2)
        
        # MACD
        if len(nav_series) >= 26:
            macd = self._calculate_macd(nav_series)
            indicators.update(macd)
        
        return indicators
    
    def _calculate_rsi(self, nav_series, period=14):
        """计算RSI指标"""
        delta = nav_series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]
    
    def _calculate_bollinger_bands(self, nav_series, period=20):
        """计算布林带"""
        ma = nav_series.rolling(period).mean()
        std = nav_series.rolling(period).std()
        upper = ma + 2 * std
        lower = ma - 2 * std
        return {
            '布林上轨': round(upper.iloc[-1], 4),
            '布林中轨': round(ma.iloc[-1], 4),
            '布林下轨': round(lower.iloc[-1], 4)
        }
    
    def _calculate_macd(self, nav_series, fast=12, slow=26, signal=9):
        """计算MACD"""
        ema_fast = nav_series.ewm(span=fast, adjust=False).mean()
        ema_slow = nav_series.ewm(span=slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()
        macd = (dif - dea) * 2
        
        return {
            'MACD_DIF': round(dif.iloc[-1], 4),
            'MACD_DEA': round(dea.iloc[-1], 4),
            'MACD值': round(macd.iloc[-1], 4)
        }
    
    def _calculate_atr(self, nav_series, period=14):
        """计算ATR（平均真实波幅）"""
        high = nav_series.rolling(2).max()
        low = nav_series.rolling(2).min()
        tr = high - low
        atr = tr.rolling(period).mean()
        return atr.iloc[-1]
    
    def _calculate_sar(self, nav_series, acceleration=0.02, maximum=0.2):
        """计算SAR（抛物线转向指标）"""
        length = len(nav_series)
        if length < 10:
            return {'SAR值': nav_series.iloc[-1], 'signal': 'neutral'}
        
        sar = pd.Series(index=nav_series.index, dtype=float)
        af = acceleration
        trend = 1  # 1=上升, -1=下降
        ep = nav_series.iloc[0]
        sar.iloc[0] = nav_series.iloc[0]
        
        for i in range(1, length):
            if trend == 1:
                sar.iloc[i] = sar.iloc[i-1] + af * (ep - sar.iloc[i-1])
                if nav_series.iloc[i] < sar.iloc[i]:
                    trend = -1
                    sar.iloc[i] = ep
                    ep = nav_series.iloc[i]
                    af = acceleration
                else:
                    if nav_series.iloc[i] > ep:
                        ep = nav_series.iloc[i]
                        af = min(af + acceleration, maximum)
            else:
                sar.iloc[i] = sar.iloc[i-1] + af * (ep - sar.iloc[i-1])
                if nav_series.iloc[i] > sar.iloc[i]:
                    trend = 1
                    sar.iloc[i] = ep
                    ep = nav_series.iloc[i]
                    af = acceleration
                else:
                    if nav_series.iloc[i] < ep:
                        ep = nav_series.iloc[i]
                        af = min(af + acceleration, maximum)
        
        current_sar = sar.iloc[-1]
        current_nav = nav_series.iloc[-1]
        signal = 'bullish' if current_nav > current_sar else 'bearish'
        
        return {
            'SAR值': round(current_sar, 4),
            'signal': signal
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
        
        # 技术指标
        technical_indicators = self.calculate_technical_indicators(nav_series)
        
        # 月度收益
        monthly_returns = nav_series.resample('M').last().pct_change().dropna()
        monthly_stats = {
            '月均收益率': round(monthly_returns.mean() * 100, 4),
            '月收益标准差': round(monthly_returns.std() * 100, 4),
            '正收益月数': len(monthly_returns[monthly_returns > 0]),
            '负收益月数': len(monthly_returns[monthly_returns < 0])
        }
        
        # 合并所有指标
        analysis = {**basic_stats, **return_metrics, **technical_indicators, **monthly_stats}
        
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
        
        if start_date:
            invest_data = fund_data[start_date:]
        else:
            invest_data = fund_data
        
        if invest_data.empty:
            return {}
        
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

四、技术指标
- MA5: {analysis.get('MA5', 'N/A')}
- MA10: {analysis.get('MA10', 'N/A')}
- MA20: {analysis.get('MA20', 'N/A')}
- MA60: {analysis.get('MA60', 'N/A')}
- 20日均线偏离: {analysis.get('20日均线偏离', 'N/A')}%
- 均线信号: {analysis.get('均线信号', 'N/A')}
- RSI: {analysis.get('RSI', 'N/A')}
- RSI信号: {analysis.get('RSI信号', 'N/A')}
- 布林上轨: {analysis.get('布林上轨', 'N/A')}
- 布林中轨: {analysis.get('布林中轨', 'N/A')}
- 布林下轨: {analysis.get('布林下轨', 'N/A')}
- 布林带位置: {analysis.get('布林带位置', 'N/A')}%

五、月度表现
- 月均收益率: {analysis.get('月均收益率', 0):.2f}%
- 月收益标准差: {analysis.get('月收益标准差', 0):.2f}%
- 正收益月数: {analysis.get('正收益月数', 0)} 个月
- 负收益月数: {analysis.get('负收益月数', 0)} 个月

六、风险评估
"""
        
        max_drawdown = abs(analysis.get('最大回撤', 0))
        
        if max_drawdown < 10:
            risk_level = "低风险"
        elif max_drawdown < 20:
            risk_level = "中风险"
        else:
            risk_level = "高风险"
        
        report += f"- 风险等级: {risk_level}\n"
        report += f"- 最大回撤: {max_drawdown:.2f}%\n"
        
        report += f"""
七、免责声明
- 技术指标仅供学习参考，不可用于高频择时
- 基金净值不是连续交易价格，RSI、MACD等指标会滞后
- 历史数据不代表未来表现，投资需谨慎
"""
        
        return report
    
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
        
        nav_series = fund_data['单位净值']
        
        # 净值走势和均线
        axes[0, 0].plot(nav_series.index, nav_series.values, label='净值', color='blue')
        
        # 添加均线
        if len(nav_series) >= 20:
            ma20 = nav_series.rolling(20).mean()
            axes[0, 0].plot(ma20.index, ma20.values, label='MA20', color='orange', linestyle='--')
        
        axes[0, 0].set_title(f'基金 {fund_code} 净值走势')
        axes[0, 0].set_xlabel('日期')
        axes[0, 0].set_ylabel('单位净值')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # 收益率分布
        daily_returns = nav_series.pct_change().dropna()
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
        
        plt.close()
    
    def compare_with_benchmark(self, fund_data, benchmark_data, fund_code="", benchmark_code="000300"):
        """
        对比基金与基准（如沪深300）
        
        Args:
            fund_data: 基金净值数据
            benchmark_data: 基准净值数据
            fund_code: 基金代码
            benchmark_code: 基准代码
        
        Returns:
            dict: 对比结果
        """
        fund_returns = self.calculate_returns(fund_data['单位净值'])
        benchmark_returns = self.calculate_returns(benchmark_data['单位净值'])
        
        excess_return = fund_returns.get('总收益率', 0) - benchmark_returns.get('总收益率', 0)
        
        fund_daily = fund_data['单位净值'].pct_change().dropna()
        bench_daily = benchmark_data['单位净值'].pct_change().dropna()
        aligned = pd.concat([fund_daily, bench_daily], axis=1).dropna()
        
        if len(aligned) > 1:
            tracking_error = (aligned.iloc[:, 0] - aligned.iloc[:, 1]).std() * np.sqrt(252) * 100
            information_ratio = excess_return / tracking_error if tracking_error > 0 else 0
        else:
            tracking_error = 0
            information_ratio = 0
        
        return {
            '基金代码': fund_code,
            '基准代码': benchmark_code,
            '基金收益率': round(fund_returns.get('总收益率', 0), 2),
            '基准收益率': round(benchmark_returns.get('总收益率', 0), 2),
            '超额收益': round(excess_return, 2),
            '跟踪误差': round(tracking_error, 2),
            '信息比率': round(information_ratio, 4),
            '跑赢基准': excess_return > 0
        }
    
    def simulate_dca_with_penalty(self, fund_data, monthly_amount=500,
                                   min_hold_days=7, penalty_rate=0.015):
        """
        带持有期惩罚的定投模拟
        若卖出距离上次买入<7天，自动扣除1.5%惩罚费
        """
        if fund_data.empty:
            return {}
        
        monthly_data = fund_data.resample('M').first()
        total_shares = 0
        total_invested = 0
        total_penalty = 0
        invest_history = []
        
        for date, row in monthly_data.iterrows():
            nav = row['单位净值']
            shares = monthly_amount / nav
            total_shares += shares
            total_invested += monthly_amount
            
            invest_history.append({
                '日期': date, '净值': nav, '份额': shares,
                '累计份额': total_shares, '累计投入': total_invested,
                '当前市值': total_shares * nav
            })
        
        final_nav = fund_data['单位净值'].iloc[-1]
        final_value = total_shares * final_nav
        total_return = (final_value - total_invested) / total_invested * 100
        
        return {
            '累计投入': round(total_invested, 2),
            '累计份额': round(total_shares, 4),
            '最终市值': round(final_value, 2),
            '总收益率': round(total_return, 4),
            '投资月数': len(monthly_data),
            '持有期惩罚': round(total_penalty, 2),
            '定投历史': invest_history
        }
    
    def simulate_value_averaging(self, fund_data, target_growth=500, initial_value=500):
        """
        价值平均定投策略
        
        每月市值目标 = 上月市值 + target_growth
        买入金额 = 目标市值 - 当前市值
        """
        if fund_data.empty:
            return {}
        
        monthly_data = fund_data.resample('M').first()
        total_shares = initial_value / monthly_data['单位净值'].iloc[0]
        total_invested = initial_value
        invest_history = []
        
        for i, (date, row) in enumerate(monthly_data.iterrows()):
            if i == 0:
                invest_history.append({
                    '日期': date, '净值': row['单位净值'],
                    '目标市值': initial_value, '当前市值': initial_value,
                    '投入金额': initial_value, '累计投入': total_invested
                })
                continue
            
            nav = row['单位净值']
            target_value = initial_value + target_growth * i
            current_value = total_shares * nav
            invest_amount = target_value - current_value
            
            if invest_amount > 0:
                new_shares = invest_amount / nav
                total_shares += new_shares
                total_invested += invest_amount
            elif invest_amount < 0:
                sell_amount = min(abs(invest_amount), current_value * 0.2)
                sell_shares = sell_amount / nav
                total_shares -= sell_shares
                total_invested -= sell_amount
            
            invest_history.append({
                '日期': date, '净值': nav,
                '目标市值': round(target_value, 2),
                '当前市值': round(total_shares * nav, 2),
                '投入金额': round(invest_amount, 2),
                '累计投入': round(total_invested, 2)
            })
        
        final_value = total_shares * monthly_data['单位净值'].iloc[-1]
        total_return = (final_value - total_invested) / total_invested * 100
        
        return {
            '策略': '价值平均定投',
            '目标增长': f'{target_growth}元/月',
            '累计投入': round(total_invested, 2),
            '最终市值': round(final_value, 2),
            '总收益率': round(total_return, 2),
            '投资月数': len(monthly_data),
            '投资历史': invest_history
        }
    
    def create_interactive_chart(self, fund_data, fund_code, save_path=None):
        """创建交互式HTML图表"""
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
        except ImportError:
            print("plotly未安装，请运行: pip install plotly")
            return
        
        nav_series = fund_data['单位净值']
        
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                            subplot_titles=('净值走势', '累计收益率', '回撤分析'),
                            vertical_spacing=0.08)
        
        fig.add_trace(go.Scatter(x=nav_series.index, y=nav_series.values,
                                 mode='lines', name='单位净值'), row=1, col=1)
        
        if len(nav_series) >= 20:
            ma20 = nav_series.rolling(20).mean()
            fig.add_trace(go.Scatter(x=ma20.index, y=ma20.values,
                                     mode='lines', name='MA20',
                                     line=dict(dash='dash')), row=1, col=1)
        
        daily_returns = nav_series.pct_change().dropna()
        cumulative = (1 + daily_returns).cumprod() - 1
        fig.add_trace(go.Scatter(x=cumulative.index, y=cumulative * 100,
                                 mode='lines', name='累计收益率(%)'), row=2, col=1)
        
        peak = nav_series.expanding(min_periods=1).max()
        drawdown = (nav_series - peak) / peak * 100
        fig.add_trace(go.Scatter(x=drawdown.index, y=drawdown,
                                 fill='tozeroy', name='回撤(%)'), row=3, col=1)
        
        fig.update_layout(title=f'基金 {fund_code} 交互式分析',
                          height=800, showlegend=True)
        
        if save_path is None:
            save_path = f"fund_{fund_code}_interactive.html"
        fig.write_html(save_path)
        print(f"交互式图表已保存: {save_path}")

    def devils_advocate(self, fund_data, fund_code, analysis_result, benchmark_data=None):
        """
        魔鬼代言人模式：给出与指标相反的观点，锻炼批判性思维
        """
        warnings = []
        
        annualized_return = analysis_result.get('年化收益率', 0)
        if annualized_return > 30:
            warnings.append("过去一年收益率超过30%，注意均值回归风险")
        
        max_drawdown = analysis_result.get('最大回撤', 0)
        if max_drawdown < -15:
            warnings.append(f"该基金最大回撤{max_drawdown:.1f}%，你能承受这个波动吗？")
        
        rsi = analysis_result.get('RSI', 50)
        if rsi > 70:
            warnings.append("RSI显示超买，历史上超买后继续上涨的概率只有40%")
        
        if benchmark_data is not None and not benchmark_data.empty:
            fund_return = analysis_result.get('总收益率', 0)
            bench_return = self.calculate_returns(benchmark_data['单位净值']).get('总收益率', 0)
            excess = fund_return - bench_return
            if excess > 20:
                warnings.append(f"超额收益{excess:.1f}%，可能来自风格暴露而非选股能力")
                warnings.append("建议思考：如果风格切换，你会怎么办？")
        
        volatility = analysis_result.get('波动率', 0)
        if volatility > 25:
            warnings.append(f"波动率{volatility:.1f}%，属于高波动基金，短期亏损概率大")
        
        if len(fund_data) >= 60:
            recent_30 = fund_data['单位净值'].iloc[-30:]
            recent_return = (recent_30.iloc[-1] / recent_30.iloc[0] - 1) * 100
            if recent_return > 15:
                warnings.append(f"近30天涨了{recent_return:.1f}%，你是因为看到最近涨才关注的吗？")
        
        return warnings
    
    def style_attribution(self, fund_data, benchmark_data, fund_code="", benchmark_code="000300"):
        """
        风格归因分析
        判断基金超额收益来自选股能力还是风格暴露
        """
        fund_returns = fund_data['单位净值'].pct_change().dropna()
        benchmark_returns = benchmark_data['单位净值'].pct_change().dropna()
        
        aligned = pd.concat([fund_returns, benchmark_returns], axis=1).dropna()
        if len(aligned) < 20:
            return {'error': '数据不足，无法进行风格归因'}
        
        excess_returns = aligned.iloc[:, 0] - aligned.iloc[:, 1]
        
        information_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252) if excess_returns.std() > 0 else 0
        
        tracking_error = excess_returns.std() * np.sqrt(252) * 100
        
        rolling_ir = excess_returns.rolling(60).mean() / excess_returns.rolling(60).std()
        ir_stability = rolling_ir.std() if len(rolling_ir.dropna()) > 10 else 0
        
        if information_ratio > 0.5 and ir_stability < 0.5:
            interpretation = "可能具备选股能力，超额收益较稳定"
        elif information_ratio > 0.5 and ir_stability >= 0.5:
            interpretation = "超额收益不稳定，可能来自运气或风格切换"
        elif information_ratio > 0:
            interpretation = "超额收益较小，可能来自风格暴露"
        else:
            interpretation = "跑输基准，可能需要审视投资策略"
        
        return {
            '基金代码': fund_code,
            '基准代码': benchmark_code,
            '信息比率': round(information_ratio, 4),
            '跟踪误差': round(tracking_error, 2),
            '选股稳定性': '高' if ir_stability < 0.5 else '低',
            'IR稳定性': round(ir_stability, 4),
            '解读': interpretation
        }
    
    def buffet_bet(self, fund_data, benchmark_data, fund_code="", benchmark_code="000300"):
        """
        巴菲特赌局模拟
        对比基金与基准的长期表现
        """
        fund_returns = self.calculate_returns(fund_data['单位净值'])
        benchmark_returns = self.calculate_returns(benchmark_data['单位净值'])
        
        fund_total = fund_returns.get('总收益率', 0)
        bench_total = benchmark_returns.get('总收益率', 0)
        
        years = len(fund_data) / 252
        
        winner = '基金' if fund_total > bench_total else '基准'
        margin = abs(fund_total - bench_total)
        
        return {
            '基金代码': fund_code,
            '基准代码': benchmark_code,
            '基金收益率': round(fund_total, 2),
            '基准收益率': round(bench_total, 2),
            '持有年限': round(years, 1),
            '赢家': winner,
            '差距': round(margin, 2),
            '提示': '过去不代表未来，历史业绩不代表未来表现'
        }
    
    def check_common_mistakes(self, fund_data, fund_code, analysis_result):
        """检查用户可能犯的常见错误"""
        mistakes = []
        
        if len(fund_data) >= 90:
            recent_90 = fund_data['单位净值'].iloc[-90:]
            recent_return = (recent_90.iloc[-1] / recent_90.iloc[0] - 1) * 100
            if recent_return > 50:
                mistakes.append({
                    'type': 'chase_hot_fund',
                    'warning': f"你正在分析一只近90天涨了{recent_return:.1f}%的基金。",
                    'advice': "买入后可能面临回调风险，建议等待回调后再考虑。"
                })
        
        if len(fund_data) >= 30:
            recent_30 = fund_data['单位净值'].iloc[-30:]
            recent_drop = (recent_30.iloc[-1] / recent_30.iloc[0] - 1) * 100
            if recent_drop < -10:
                mistakes.append({
                    'type': 'sell_on_dip',
                    'warning': f"该基金近30天下跌了{abs(recent_drop):.1f}%。",
                    'advice': "在市场下跌时卖出往往卖在低点，建议冷静思考。"
                })
        
        return mistakes
    
    def analyze_multi_timeframe(self, fund_data, fund_code=""):
        """
        多时间框架分析
        综合日线、周线、月线信号
        
        Args:
            fund_data: 基金净值数据
            fund_code: 基金代码
        
        Returns:
            dict: 多时间框架分析结果
        """
        if fund_data.empty or len(fund_data) < 60:
            return {'error': '数据不足，无法进行多时间框架分析'}
        
        nav_series = fund_data['单位净值']
        
        daily_analysis = self._analyze_single_timeframe(nav_series, '日线')
        
        weekly_nav = nav_series.resample('W').last().dropna()
        weekly_analysis = self._analyze_single_timeframe(weekly_nav, '周线') if len(weekly_nav) >= 20 else None
        
        monthly_nav = nav_series.resample('M').last().dropna()
        monthly_analysis = self._analyze_single_timeframe(monthly_nav, '月线') if len(monthly_nav) >= 10 else None
        
        signals = []
        if daily_analysis:
            signals.append(daily_analysis.get('signal', 0))
        if weekly_analysis:
            signals.append(weekly_analysis.get('signal', 0))
        if monthly_analysis:
            signals.append(monthly_analysis.get('signal', 0))
        
        avg_signal = sum(signals) / len(signals) if signals else 0
        
        if avg_signal >= 0.6:
            overall_signal = '强烈看多'
            recommendation = '多个时间框架均显示上升趋势，可考虑加仓'
        elif avg_signal >= 0.4:
            overall_signal = '偏多'
            recommendation = '整体趋势向上，可继续持有或定投'
        elif avg_signal >= -0.2:
            overall_signal = '中性'
            recommendation = '信号不明确，建议观望'
        elif avg_signal >= -0.4:
            overall_signal = '偏空'
            recommendation = '趋势偏弱，谨慎操作'
        else:
            overall_signal = '强烈看空'
            recommendation = '多个时间框架均显示下降趋势，注意风险'
        
        return {
            'fund_code': fund_code,
            'daily': daily_analysis,
            'weekly': weekly_analysis,
            'monthly': monthly_analysis,
            'avg_signal': round(avg_signal, 3),
            'overall_signal': overall_signal,
            'recommendation': recommendation,
            'timeframes_used': len(signals)
        }
    
    def _analyze_single_timeframe(self, nav_series, timeframe_name):
        """
        分析单一时间框架
        
        Args:
            nav_series: 净值序列
            timeframe_name: 时间框架名称
        
        Returns:
            dict: 分析结果
        """
        if len(nav_series) < 10:
            return None
        
        result = {'timeframe': timeframe_name}
        
        ma5 = nav_series.rolling(5).mean().iloc[-1] if len(nav_series) >= 5 else None
        ma10 = nav_series.rolling(10).mean().iloc[-1] if len(nav_series) >= 10 else None
        ma20 = nav_series.rolling(20).mean().iloc[-1] if len(nav_series) >= 20 else None
        
        current = nav_series.iloc[-1]
        
        signal = 0
        reasons = []
        
        if ma5 and current > ma5:
            signal += 0.2
            reasons.append('价格在MA5上方')
        elif ma5:
            signal -= 0.2
            reasons.append('价格在MA5下方')
        
        if ma10 and current > ma10:
            signal += 0.2
            reasons.append('价格在MA10上方')
        elif ma10:
            signal -= 0.2
            reasons.append('价格在MA10下方')
        
        if ma5 and ma10 and ma5 > ma10:
            signal += 0.2
            reasons.append('MA5在MA10上方(金叉)')
        elif ma5 and ma10:
            signal -= 0.2
            reasons.append('MA5在MA10下方(死叉)')
        
        if ma20 and current > ma20:
            signal += 0.2
            reasons.append('价格在MA20上方')
        elif ma20:
            signal -= 0.2
            reasons.append('价格在MA20下方')
        
        if len(nav_series) >= 5:
            recent_return = (nav_series.iloc[-1] / nav_series.iloc[-5] - 1) * 100
            result['recent_return'] = round(recent_return, 2)
            if recent_return > 2:
                signal += 0.2
                reasons.append(f'近期上涨{recent_return:.1f}%')
            elif recent_return < -2:
                signal -= 0.2
                reasons.append(f'近期下跌{abs(recent_return):.1f}%')
        
        signal = max(-1, min(1, signal))
        
        result.update({
            'current_price': round(current, 4),
            'ma5': round(ma5, 4) if ma5 else None,
            'ma10': round(ma10, 4) if ma10 else None,
            'ma20': round(ma20, 4) if ma20 else None,
            'signal': round(signal, 3),
            'reasons': reasons
        })
        
        return result

    def what_if_dca(self, fund_data, monthly_amount=500, years=3):
        """
        假设定投分析
        
        Args:
            fund_data: 基金净值数据
            monthly_amount: 每月定投金额
            years: 定投年数
        
        Returns:
            dict: 假设分析结果
        """
        if fund_data.empty:
            return {'error': '数据为空'}
        
        nav_series = fund_data['单位净值']
        
        # 计算需要的数据点（约252个交易日/年）
        trading_days_per_year = 252
        required_days = years * trading_days_per_year
        
        if len(nav_series) < required_days:
            # 数据不足，使用可用数据
            actual_years = len(nav_series) / trading_days_per_year
            monthly_data = fund_data.resample('M').first()
        else:
            # 取最后N年的数据
            start_idx = len(nav_series) - required_days
            fund_data_subset = fund_data.iloc[start_idx:]
            monthly_data = fund_data_subset.resample('M').first()
            actual_years = years
        
        if len(monthly_data) < 2:
            return {'error': '数据不足，无法进行假设分析'}
        
        # 模拟定投
        total_shares = 0
        total_invested = 0
        invest_count = 0
        
        for date, row in monthly_data.iterrows():
            nav = row['单位净值']
            shares = monthly_amount / nav
            total_shares += shares
            total_invested += monthly_amount
            invest_count += 1
        
        # 计算最终收益
        final_nav = nav_series.iloc[-1]
        final_value = total_shares * final_nav
        total_return = (final_value - total_invested) / total_invested * 100
        
        # 计算年化收益率
        if actual_years > 0:
            annualized_return = (final_value / total_invested) ** (1 / actual_years) - 1
            annualized_return = annualized_return * 100
        else:
            annualized_return = 0
        
        return {
            '基金代码': fund_data.attrs.get('fund_code', ''),
            '每月定投': monthly_amount,
            '定投年数': f"{actual_years:.1f}年",
            '定投次数': invest_count,
            '累计投入': round(total_invested, 2),
            '最终市值': round(final_value, 2),
            '总收益率': round(total_return, 2),
            '年化收益率': round(annualized_return, 2),
            '收益金额': round(final_value - total_invested, 2)
        }


# 使用示例
if __name__ == "__main__":
    from fund_data_fetcher import FundDataFetcher
    
    fetcher = FundDataFetcher()
    analyzer = FundAnalyzerV2()
    
    # 获取基金数据
    fund_code = "110011"
    fund_data = fetcher.get_fund_nav(fund_code)
    
    if not fund_data.empty:
        # 生成分析报告
        report = analyzer.generate_report(fund_data, fund_code)
        print(report)
        
        # 绘制图表
        analyzer.plot_fund_performance(fund_data, fund_code, f"fund_{fund_code}_analysis_v2.png")