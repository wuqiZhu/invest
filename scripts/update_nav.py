# -*- coding: utf-8 -*-
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config_manager import ConfigManager
from fund_data_fetcher import FundDataFetcher
from fund_database import FundDatabase


def update_fund_nav():
    config = ConfigManager()
    fetcher = FundDataFetcher()
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fund_data.db')
    db = FundDatabase(db_path)

    funds = config.get('funds', [])
    enabled_funds = [f for f in funds if f.get('enabled', True)]

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始更新净值...")

    success_count = 0
    for fund in enabled_funds:
        code = fund['code']
        name = fund.get('name', code)
        try:
            nav_df = fetcher.get_fund_nav(code)
            if nav_df is not None and not nav_df.empty:
                db.save_fund_nav(code, nav_df)
                latest_nav = nav_df['单位净值'].iloc[-1]
                latest_date = nav_df.index[-1].strftime('%Y-%m-%d')
                print(f"  OK {code} {name}: {latest_nav} ({latest_date})")
                success_count += 1
            else:
                print(f"  FAIL {code} {name}: 获取失败")
        except Exception as e:
            print(f"  FAIL {code} {name}: {e}")

    db.close()
    print(f"更新完成: {success_count}/{len(enabled_funds)} 成功")
    return success_count


if __name__ == '__main__':
    update_fund_nav()
