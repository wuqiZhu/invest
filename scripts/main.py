#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基金投资分析主程序
整合数据获取、分析和数据库功能

免责声明：
本工具仅供个人学习和研究使用，所展示的数据均来自第三方公开接口。
不构成任何投资建议，据此操作风险自担。
基金投资有风险，过往业绩不代表未来表现。
"""

import sys
import os
from datetime import datetime, timedelta

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fund_data_fetcher import FundDataFetcher
from fund_analyzer import FundAnalyzer
from fund_database import FundDatabase

class FundInvestmentTool:
    """基金投资分析工具"""
    
    def __init__(self):
        self.fetcher = FundDataFetcher()
        self.analyzer = FundAnalyzer()
        self.db = FundDatabase()
    
    def add_fund(self, fund_code):
        """添加基金到监控列表"""
        print(f"正在添加基金 {fund_code}...")
        
        # 获取基金信息
        fund_info = self.fetcher.get_fund_info(fund_code)
        if not fund_info:
            print(f"无法获取基金 {fund_code} 信息")
            return False
        
        # 保存基金信息
        self.db.save_fund_info(fund_info)
        print(f"基金 {fund_info.get('基金名称', '')} 已添加")
        
        return True
    
    def fetch_fund_data(self, fund_code, days=365):
        """获取基金历史数据"""
        print(f"正在获取基金 {fund_code} 最近 {days} 天数据...")
        
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        fund_data = self.fetcher.get_fund_nav(fund_code, start_date, end_date)
        
        if not fund_data.empty:
            # 保存到数据库
            self.db.save_fund_nav(fund_code, fund_data)
            print(f"成功获取 {len(fund_data)} 条数据")
            return fund_data
        else:
            print(f"获取基金 {fund_code} 数据失败")
            return None
    
    def analyze_fund(self, fund_code):
        """分析基金表现"""
        print(f"正在分析基金 {fund_code}...")
        
        # 从数据库获取数据
        fund_data = self.db.get_fund_nav(fund_code)
        
        if fund_data.empty:
            print(f"基金 {fund_code} 没有数据，请先获取数据")
            return None
        
        # 分析基金
        analysis = self.analyzer.analyze_fund(fund_data, fund_code)
        
        # 保存分析结果
        self.db.save_analysis_result(fund_code, analysis)
        
        return analysis
    
    def generate_report(self, fund_code):
        """生成基金分析报告"""
        # 获取数据
        fund_data = self.db.get_fund_nav(fund_code)
        
        if fund_data.empty:
            print(f"基金 {fund_code} 没有数据")
            return None
        
        # 生成报告
        report = self.analyzer.generate_report(fund_data, fund_code)
        
        return report
    
    def plot_fund(self, fund_code, save_path=None):
        """绘制基金图表"""
        # 获取数据
        fund_data = self.db.get_fund_nav(fund_code)
        
        if fund_data.empty:
            print(f"基金 {fund_code} 没有数据")
            return
        
        # 绘制图表
        self.analyzer.plot_fund_performance(fund_data, fund_code, save_path)
    
    def simulate_dca(self, fund_code, monthly_amount=500, months=12):
        """定投模拟"""
        print(f"正在模拟基金 {fund_code} 定投...")
        
        # 获取数据
        fund_data = self.db.get_fund_nav(fund_code)
        
        if fund_data.empty:
            print(f"基金 {fund_code} 没有数据")
            return None
        
        # 计算开始日期
        start_date = (datetime.now() - timedelta(days=months*30)).strftime('%Y-%m-%d')
        
        # 模拟定投
        result = self.analyzer.simulate_dca(fund_data, monthly_amount, start_date)
        
        return result
    
    def compare_funds(self, fund_codes):
        """对比多只基金"""
        print("正在对比基金...")
        
        funds_data = {}
        for code in fund_codes:
            fund_data = self.db.get_fund_nav(code)
            if not fund_data.empty:
                funds_data[code] = fund_data
        
        if funds_data:
            comparison = self.analyzer.compare_funds(funds_data)
            return comparison
        else:
            print("没有可对比的基金数据")
            return None
    
    def get_fund_summary(self):
        """获取基金摘要"""
        return self.db.get_fund_summary()
    
    def export_data(self, fund_code, output_path=None):
        """导出基金数据"""
        if output_path is None:
            output_path = f"fund_{fund_code}_{datetime.now().strftime('%Y%m%d')}.csv"
        
        self.db.export_to_csv(fund_code, output_path)


def main():
    """主函数"""
    tool = FundInvestmentTool()
    
    # 示例基金代码
    fund_codes = ["110011", "001632", "161725"]
    
    print("="*50)
    print("基金投资分析工具")
    print("="*50)
    
    # 1. 添加基金
    print("\n1. 添加基金到监控列表")
    for code in fund_codes:
        tool.add_fund(code)
    
    # 2. 获取历史数据
    print("\n2. 获取基金历史数据")
    for code in fund_codes:
        tool.fetch_fund_data(code, days=365)
    
    # 3. 分析基金
    print("\n3. 分析基金表现")
    for code in fund_codes:
        analysis = tool.analyze_fund(code)
        if analysis:
            print(f"\n基金 {code} 分析结果:")
            for key, value in analysis.items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.4f}")
                else:
                    print(f"  {key}: {value}")
    
    # 4. 生成报告
    print("\n4. 生成基金分析报告")
    for code in fund_codes:
        report = tool.generate_report(code)
        if report:
            print(f"\n{report}")
    
    # 5. 定投模拟
    print("\n5. 定投模拟")
    for code in fund_codes:
        result = tool.simulate_dca(code, monthly_amount=500, months=12)
        if result:
            print(f"\n基金 {code} 定投模拟结果:")
            print(f"  累计投入: {result['累计投入']} 元")
            print(f"  最终市值: {result['最终市值']} 元")
            print(f"  总收益率: {result['总收益率']:.2f}%")
    
    # 6. 基金对比
    print("\n6. 基金对比")
    comparison = tool.compare_funds(fund_codes)
    if comparison is not None:
        print("\n基金对比结果:")
        print(comparison)
    
    print("\n" + "="*50)
    print("分析完成！")
    print("="*50)


if __name__ == "__main__":
    main()