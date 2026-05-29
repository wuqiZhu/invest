# -*- coding: utf-8 -*-
"""
投资组合快照管理器（借鉴stock-tracker-cli的历史追踪功能）
保存每日投资组合快照，用于历史回测和绩效追踪
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


class SnapshotManager:
    """快照管理器"""

    def __init__(self, data_dir=None):
        """
        初始化快照管理器

        Args:
            data_dir: 数据目录
        """
        if data_dir is None:
            data_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = Path(data_dir)
        self.snapshots_dir = self.data_dir / 'snapshots'
        self.snapshots_dir.mkdir(exist_ok=True)

    def _get_snapshot_path(self, date=None):
        """
        获取快照文件路径

        Args:
            date: 日期字符串（YYYY-MM-DD），None表示今天

        Returns:
            Path: 文件路径
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        return self.snapshots_dir / f'snapshot_{date}.json'

    def save_snapshot(self, snapshot_data):
        """
        保存快照

        Args:
            snapshot_data: 快照数据

        Returns:
            bool: 是否成功
        """
        try:
            snapshot_path = self._get_snapshot_path()

            data = dict(snapshot_data)
            if 'timestamp' not in data:
                data['timestamp'] = datetime.now().isoformat()

            with open(snapshot_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return True
        except Exception:
            return False

    def load_snapshot(self, date=None):
        """
        加载快照

        Args:
            date: 日期字符串

        Returns:
            dict: 快照数据
        """
        try:
            snapshot_path = self._get_snapshot_path(date)
            if not snapshot_path.exists():
                return None

            with open(snapshot_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def list_snapshots(self, limit=30):
        """
        列出快照

        Args:
            limit: 限制数量

        Returns:
            list: 快照日期列表
        """
        try:
            snapshots = []
            for file in sorted(self.snapshots_dir.glob('snapshot_*.json'), reverse=True):
                date_str = file.stem.replace('snapshot_', '')
                snapshots.append(date_str)
                if len(snapshots) >= limit:
                    break
            return snapshots
        except Exception:
            return []

    def get_portfolio_history(self, days=30):
        """
        获取投资组合历史数据

        Args:
            days: 天数

        Returns:
            dict: 历史数据
        """
        history = {
            'dates': [],
            'total_invested': [],
            'total_value': [],
            'total_profit': [],
        }

        try:
            snapshot_dates = self.list_snapshots(days)
            snapshot_dates.sort()

            for date in snapshot_dates:
                snapshot = self.load_snapshot(date)
                if not snapshot:
                    continue

                portfolio = snapshot.get('portfolio', {})
                if portfolio.get('available'):
                    history['dates'].append(date)
                    history['total_invested'].append(portfolio.get('total_invested', 0))
                    history['total_value'].append(portfolio.get('total_value', 0))
                    history['total_profit'].append(portfolio.get('total_profit', 0))

            return {
                'available': True,
                'history': history,
                'count': len(history['dates'])
            }
        except Exception:
            return {'available': False}


def main():
    import argparse

    parser = argparse.ArgumentParser(description='快照管理器')
    parser.add_argument('--data-dir', help='数据目录')
    parser.add_argument('--list', action='store_true', help='列出快照')
    parser.add_argument('--load', help='加载指定日期快照')
    parser.add_argument('--history', type=int, help='获取历史数据')

    args = parser.parse_args()
    manager = SnapshotManager(args.data_dir)

    try:
        if args.list:
            print("=" * 60)
            print("快照列表")
            print("=" * 60)
            snapshots = manager.list_snapshots(30)
            for s in snapshots:
                print(s)

        elif args.load:
            print("=" * 60)
            print(f"快照: {args.load}")
            print("=" * 60)
            snapshot = manager.load_snapshot(args.load)
            print(json.dumps(snapshot, ensure_ascii=False, indent=2))

        elif args.history:
            print("=" * 60)
            print(f"历史数据 (最近 {args.history} 天)")
            print("=" * 60)
            history = manager.get_portfolio_history(args.history)
            print(json.dumps(history, ensure_ascii=False, indent=2))

        else:
            parser.print_help()

    except KeyboardInterrupt:
        print("\n操作已取消")


if __name__ == '__main__':
    main()
