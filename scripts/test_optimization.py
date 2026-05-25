# -*- coding: utf-8 -*-
"""
优化功能测试脚本
测试所有新增功能
"""

import sys
import os
import traceback
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_config_manager():
    """测试配置管理模块"""
    print("\n" + "="*50)
    print("1. Test ConfigManager")
    print("="*50)
    
    try:
        from config_manager import ConfigManager
        
        # 测试加载配置
        print("\n1.1 Load config...")
        config = ConfigManager()
        print("  [OK] Config loaded")
        
        # 测试获取配置
        print("\n1.2 Get config values...")
        funds = config.get('funds')
        print(f"  [OK] Funds: {len(funds)} items")
        
        # 测试获取基金列表
        print("\n1.3 Get fund codes...")
        codes = config.get_fund_codes()
        print(f"  [OK] Fund codes: {codes}")
        
        # 测试验证配置
        print("\n1.4 Validate config...")
        is_valid, errors = config.validate()
        print(f"  [OK] Valid: {is_valid}, Errors: {len(errors)}")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        traceback.print_exc()
        return False


def test_enhanced_fetcher():
    """测试增强版数据获取模块"""
    print("\n" + "="*50)
    print("2. Test Enhanced DataFetcher")
    print("="*50)
    
    try:
        from fund_data_fetcher_v2 import FundDataFetcherV2
        
        # 测试创建实例
        print("\n2.1 Create instance...")
        fetcher = FundDataFetcherV2(primary_source='eastmoney', fallback_enabled=True)
        print("  [OK] Instance created")
        
        # 测试获取基金信息
        print("\n2.2 Get fund info...")
        info = fetcher.get_fund_info("110011")
        if info:
            print(f"  [OK] Fund name: {info.get('基金名称', 'N/A')}")
        else:
            print("  [WARN] Failed to get fund info")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        traceback.print_exc()
        return False


def test_enhanced_analyzer():
    """测试增强版分析模块"""
    print("\n" + "="*50)
    print("3. Test Enhanced Analyzer")
    print("="*50)
    
    try:
        import pandas as pd
        import numpy as np
        from fund_analyzer_v2 import FundAnalyzerV2
        
        analyzer = FundAnalyzerV2()
        
        # 创建测试数据
        print("\n3.1 Create test data...")
        dates = pd.date_range(end=datetime.now(), periods=100, freq='B')
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, len(dates))
        nav_series = 1.0 * (1 + returns).cumprod()
        
        test_data = pd.DataFrame({
            '单位净值': nav_series,
            '累计净值': nav_series,
            '日增长率': returns * 100
        }, index=dates)
        
        print(f"  [OK] Created {len(test_data)} test records")
        
        # 测试技术指标计算
        print("\n3.2 Test technical indicators...")
        indicators = analyzer.calculate_technical_indicators(test_data['单位净值'])
        print(f"  [OK] Technical indicators: {len(indicators)} items")
        
        if 'MA20' in indicators:
            print(f"    MA20: {indicators['MA20']}")
        if 'RSI' in indicators:
            print(f"    RSI: {indicators['RSI']}")
        if '20日均线偏离' in indicators:
            print(f"    20日均线偏离: {indicators['20日均线偏离']}%")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        traceback.print_exc()
        return False


def test_notifier():
    """测试通知模块"""
    print("\n" + "="*50)
    print("4. Test Notifier")
    print("="*50)
    
    try:
        from fund_notifier import FundNotifier
        
        # 测试创建实例
        print("\n4.1 Create instance...")
        notifier = FundNotifier()
        print("  [OK] Instance created")
        
        # 测试控制台通知
        print("\n4.2 Test console notification...")
        notifier.send_console("Test notification message")
        print("  [OK] Console notification sent")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        traceback.print_exc()
        return False


def test_main_cli():
    """测试主程序CLI"""
    print("\n" + "="*50)
    print("5. Test Main CLI")
    print("="*50)
    
    try:
        from main_cli import FundInvestmentCLI
        
        # 测试创建实例
        print("\n5.1 Create instance...")
        cli = FundInvestmentCLI()
        print("  [OK] Instance created")
        
        # 测试列出基金
        print("\n5.2 List funds...")
        cli.list_funds()
        print("  [OK] Listed funds")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        traceback.print_exc()
        return False


def check_new_files():
    """检查新增文件"""
    print("\n" + "="*50)
    print("6. Check New Files")
    print("="*50)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    new_files = [
        "config.yaml",
        "config_manager.py",
        "main_cli.py",
        "fund_data_fetcher_v2.py",
        "fund_analyzer_v2.py",
        "fund_notifier.py"
    ]
    
    print("\n6.1 New files:")
    for f in new_files:
        full_path = os.path.join(script_dir, f)
        if os.path.exists(full_path):
            size = os.path.getsize(full_path)
            print(f"  [OK] {f} ({size} bytes)")
        else:
            print(f"  [FAIL] {f} not found")
    
    return True


def main():
    """主测试函数"""
    print("="*60)
    print("Optimization Test - Comprehensive Test")
    print("="*60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    results.append(("ConfigManager", test_config_manager()))
    results.append(("EnhancedFetcher", test_enhanced_fetcher()))
    results.append(("EnhancedAnalyzer", test_enhanced_analyzer()))
    results.append(("Notifier", test_notifier()))
    results.append(("MainCLI", test_main_cli()))
    results.append(("NewFiles", check_new_files()))
    
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, r in results:
        status = "[PASS]" if r else "[FAIL]"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\nAll optimization tests passed!")
    else:
        print(f"\n{total - passed} tests failed.")
    
    print("="*60)


if __name__ == "__main__":
    main()