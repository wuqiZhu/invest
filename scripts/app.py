# -*- coding: utf-8 -*-
"""
基金投资分析仪表盘（Streamlit版）

使用方法：
    pip install streamlit
    streamlit run app.py

免责声明：
本工具仅供个人学习和研究使用，不构成任何投资建议。
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fund_data_fetcher_v2 import FundDataFetcherV2
from fund_analyzer_v2 import FundAnalyzerV2
from trading_system import TradingSystem
from config_manager import ConfigManager


st.set_page_config(
    page_title="基金投资分析仪表盘",
    page_icon="chart_with_upwards_trend",
    layout="wide"
)

@st.cache_resource
def init_modules():
    config = ConfigManager()
    fetcher = FundDataFetcherV2()
    analyzer = FundAnalyzerV2()
    trading_system = TradingSystem(config, analyzer)
    return config, fetcher, analyzer, trading_system

config, fetcher, analyzer, trading_system = init_modules()

st.title("基金投资分析仪表盘")
st.markdown("---")

with st.sidebar:
    st.header("设置")
    
    funds = config.get('funds', [])
    fund_options = {f['code']: f['name'] for f in funds if f.get('enabled', True)}
    
    selected_fund = st.selectbox(
        "选择基金",
        options=list(fund_options.keys()),
        format_func=lambda x: f"{x} - {fund_options.get(x, '')}"
    )
    
    days = st.slider("分析天数", 30, 365, 180)
    
    st.markdown("---")
    st.markdown("### 基金代码输入")
    custom_fund = st.text_input("或输入基金代码", "")
    if custom_fund:
        selected_fund = custom_fund

if selected_fund:
    with st.spinner(f"正在获取 {selected_fund} 数据..."):
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        fund_data = fetcher.get_fund_nav(selected_fund, start_date, end_date)
    
    if fund_data.empty:
        st.error(f"无法获取基金 {selected_fund} 数据")
    else:
        tab1, tab2, tab3, tab4 = st.tabs(["基本信息", "交易信号", "技术指标", "投资日志"])
        
        with tab1:
            col1, col2, col3, col4 = st.columns(4)
            
            nav_series = fund_data['单位净值']
            latest_nav = nav_series.iloc[-1]
            total_return = (nav_series.iloc[-1] / nav_series.iloc[0] - 1) * 100
            
            with col1:
                st.metric("最新净值", f"{latest_nav:.4f}")
            with col2:
                st.metric("总收益率", f"{total_return:.2f}%")
            with col3:
                peak = nav_series.expanding(min_periods=1).max()
                drawdown = (nav_series - peak) / peak
                max_dd = drawdown.min() * 100
                st.metric("最大回撤", f"{max_dd:.2f}%")
            with col4:
                daily_returns = nav_series.pct_change().dropna()
                volatility = daily_returns.std() * (252 ** 0.5) * 100
                st.metric("年化波动率", f"{volatility:.2f}%")
            
            st.markdown("---")
            st.subheader("净值走势图")
            st.line_chart(nav_series)
            
            st.markdown("---")
            st.subheader("回撤分析")
            drawdown_series = (nav_series - peak) / peak * 100
            st.area_chart(drawdown_series)
        
        with tab2:
            st.subheader("模块化交易信号")
            
            result = trading_system.get_signal(fund_data, selected_fund)
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                signal = result['signal']
                if signal == 'BUY':
                    st.success("**买入信号**")
                    st.markdown("建议仓位：总资金的20%")
                elif signal == 'SELL':
                    st.error("**卖出信号**")
                    st.markdown("建议操作：根据止盈模块提示执行")
                else:
                    st.info("**持有观望**")
                    st.markdown("建议操作：继续定投，等待信号")
            
            with col2:
                modules = result.get('modules', {})
                
                for name, module in modules.items():
                    status = module.get('status', 'unknown')
                    detail = module.get('detail', '')
                    passed = module.get('pass', False)
                    
                    icon = "✅" if passed else "❌"
                    label = {
                        'trend': '趋势模块',
                        'volatility': '波动模块',
                        'entry': '买点模块',
                        'risk': '风控模块',
                        'profit': '止盈模块'
                    }.get(name, name)
                    
                    st.markdown(f"{icon} **{label}**: {status.upper()}")
                    st.caption(detail)
        
        with tab3:
            st.subheader("技术指标")
            
            analysis = analyzer.analyze_fund(fund_data, selected_fund)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("### 均线")
                st.write(f"MA5: {analysis.get('MA5', 'N/A')}")
                st.write(f"MA10: {analysis.get('MA10', 'N/A')}")
                st.write(f"MA20: {analysis.get('MA20', 'N/A')}")
                st.write(f"MA60: {analysis.get('MA60', 'N/A')}")
            
            with col2:
                st.markdown("### 动量指标")
                st.write(f"RSI: {analysis.get('RSI', 'N/A')}")
                st.write(f"RSI信号: {analysis.get('RSI信号', 'N/A')}")
                st.write(f"20日均线偏离: {analysis.get('20日均线偏离', 'N/A')}%")
                st.write(f"均线信号: {analysis.get('均线信号', 'N/A')}")
            
            with col3:
                st.markdown("### MACD")
                st.write(f"DIF: {analysis.get('MACD_DIF', 'N/A')}")
                st.write(f"DEA: {analysis.get('MACD_DEA', 'N/A')}")
                st.write(f"MACD值: {analysis.get('MACD值', 'N/A')}")
        
        with tab4:
            st.subheader("投资日志")
            
            st.markdown("### 记录新操作")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                action = st.selectbox("操作", ['buy', 'sell', 'hold'])
            with col2:
                amount = st.number_input("金额", min_value=0, value=100)
            with col3:
                nav_input = st.number_input("净值", min_value=0.0, value=float(latest_nav), step=0.01)
            
            reason = st.text_input("操作理由", "")
            emotion = st.selectbox("当前情绪", ['calm', 'fear', 'greed'])
            
            if st.button("保存日志"):
                st.success("日志已保存（功能开发中）")

st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>基金投资分析仪表盘 | 仅供学习研究，不构成投资建议</p>
</div>
""", unsafe_allow_html=True)
