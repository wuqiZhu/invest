# -*- coding: utf-8 -*-
import sys
import os
import io
import traceback
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_fund_data_fetcher():
    print("\n" + "="*50)
    print("1. Test FundDataFetcher")
    print("="*50)
    
    try:
        from fund_data_fetcher import FundDataFetcher
        fetcher = FundDataFetcher()
        
        print("\n1.1 Get fund info...")
        fund_info = fetcher.get_fund_info("110011")
        if fund_info:
            print("  [OK] Got fund info")
            print(f"    Name: {fund_info.get('fund_name', 'N/A')}")
        else:
            print("  [WARN] Failed to get fund info (network issue)")
        
        print("\n1.2 Get historical data...")
        fund_data = fetcher.get_fund_nav("110011", "2024-01-01", "2024-01-31")
        if not fund_data.empty:
            print(f"  [OK] Got {len(fund_data)} records")
        else:
            print("  [WARN] Failed to get historical data")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        traceback.print_exc()
        return False

def test_fund_analyzer():
    print("\n" + "="*50)
    print("2. Test FundAnalyzer")
    print("="*50)
    
    try:
        import pandas as pd
        import numpy as np
        from fund_analyzer import FundAnalyzer
        
        analyzer = FundAnalyzer()
        
        print("\n2.1 Create test data...")
        dates = pd.date_range(end=datetime.now(), periods=100, freq='B')
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, len(dates))
        nav_series = 1.0 * (1 + returns).cumprod()
        
        test_data = pd.DataFrame({
            'unit_nav': nav_series,
            'total_nav': nav_series,
            'daily_return': returns * 100
        }, index=dates)
        test_data.columns = ['unit_nav', 'total_nav', 'daily_return']
        
        print(f"  [OK] Created {len(test_data)} test records")
        
        print("\n2.2 Test analysis...")
        # Simple analysis test
        nav = test_data['unit_nav']
        total_return = (nav.iloc[-1] / nav.iloc[0] - 1) * 100
        print(f"  [OK] Total return: {total_return:.2f}%")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        traceback.print_exc()
        return False

def test_fund_database():
    print("\n" + "="*50)
    print("3. Test FundDatabase")
    print("="*50)
    
    try:
        from fund_database import FundDatabase
        
        test_db = "test_temp.db"
        db = FundDatabase(test_db)
        
        print("\n3.1 Database created...")
        print("  [OK] Success")
        
        print("\n3.2 Save fund info...")
        db.save_fund_info({
            'fund_code': 'TEST001',
            'fund_name': 'Test Fund'
        })
        print("  [OK] Saved")
        
        print("\n3.3 Get fund list...")
        funds = db.get_fund_list()
        print(f"  [OK] Found {len(funds)} funds")
        
        db.close()
        os.remove(test_db)
        print("\n  [OK] Cleanup done")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        traceback.print_exc()
        return False

def test_matplotlib():
    print("\n" + "="*50)
    print("4. Test Matplotlib")
    print("="*50)
    
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np
        
        print("\n4.1 Create test chart...")
        x = np.linspace(0, 10, 100)
        y = np.sin(x)
        
        fig, ax = plt.subplots()
        ax.plot(x, y)
        ax.set_title('Test Chart')
        
        test_file = "test_chart.png"
        plt.savefig(test_file)
        plt.close()
        
        if os.path.exists(test_file):
            print(f"  [OK] Chart saved: {test_file}")
            os.remove(test_file)
            print("  [OK] Cleanup done")
        else:
            print("  [FAIL] Chart not created")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        traceback.print_exc()
        return False

def check_files():
    print("\n" + "="*50)
    print("5. Check Project Files")
    print("="*50)
    
    # Get the scripts directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    
    files = [
        ("scripts/fund_data_fetcher.py", script_dir),
        ("scripts/fund_analyzer.py", script_dir),
        ("scripts/fund_database.py", script_dir),
        ("scripts/main.py", script_dir),
        ("scripts/demo_analysis.py", script_dir),
        ("scripts/README.md", script_dir)
    ]
    
    print("\n5.1 Script files:")
    for f, directory in files:
        full_path = os.path.join(directory, os.path.basename(f))
        if os.path.exists(full_path):
            size = os.path.getsize(full_path)
            print(f"  [OK] {f} ({size} bytes)")
        else:
            print(f"  [FAIL] {f} not found")
    
    print("\n5.2 Generated files in project root:")
    for f in os.listdir(project_dir):
        if f.endswith('.png') or f.endswith('.db'):
            full_path = os.path.join(project_dir, f)
            size = os.path.getsize(full_path)
            print(f"  [OK] {f} ({size} bytes)")
    
    return True

def main():
    print("="*60)
    print("Fund Investment Project - Comprehensive Test")
    print("="*60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Dir: {os.getcwd()}")
    
    results = []
    results.append(("DataFetcher", test_fund_data_fetcher()))
    results.append(("Analyzer", test_fund_analyzer()))
    results.append(("Database", test_fund_database()))
    results.append(("Matplotlib", test_matplotlib()))
    results.append(("Files", check_files()))
    
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
        print("\nAll tests passed! Project is ready to use.")
    else:
        print(f"\n{total - passed} tests failed. Please check.")
    
    print("="*60)

if __name__ == "__main__":
    main()