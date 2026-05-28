# -*- coding: utf-8 -*-
"""
并行处理框架
管理共享任务队列、结果队列，提供跨平台文件锁和批次状态流转

免责声明：
本工具仅供个人学习和研究使用，不构成任何投资建议。
"""

import os
import sys
import json
import time
import platform
import tempfile
from datetime import datetime
from contextlib import contextmanager

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

IS_WINDOWS = platform.system() == 'Windows'

if IS_WINDOWS:
    import msvcrt
else:
    import fcntl

VALID_TRANSITIONS = {
    'created': ['analyzed', 'error'],
    'analyzed': ['decided', 'error'],
    'decided': ['executed', 'error'],
    'executed': ['feedbacked', 'error'],
    'feedbacked': ['learned', 'error'],
    'error': ['created'],
}

ALL_STATUSES = ['created', 'analyzed', 'decided', 'executed', 'feedbacked', 'learned', 'error']


class ParallelExecutor:
    """并行处理框架"""

    def __init__(self, data_dir=None):
        """
        初始化并行处理框架

        Args:
            data_dir: 数据目录路径，默认为 invest/data
        """
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

        self.data_dir = os.path.abspath(data_dir)
        self.tasks_dir = os.path.join(self.data_dir, 'tasks')
        self.results_dir = os.path.join(self.data_dir, 'results')
        self.knowledge_dir = os.path.join(self.data_dir, 'knowledge')
        self.archive_dir = os.path.join(self.tasks_dir, 'archive')

        self.queue_path = os.path.join(self.tasks_dir, 'queue.json')
        self.queue_lock_path = os.path.join(self.tasks_dir, '.queue.lock')
        self.results_path = os.path.join(self.results_dir, 'executions.json')
        self.results_lock_path = os.path.join(self.results_dir, '.results.lock')

        self._ensure_dirs()

    def _ensure_dirs(self):
        for d in [self.tasks_dir, self.results_dir, self.knowledge_dir, self.archive_dir]:
            os.makedirs(d, exist_ok=True)

    def _acquire_lock(self, lock_path, timeout=30, exclusive=True):
        start = time.time()
        while time.time() - start < timeout:
            try:
                if IS_WINDOWS:
                    lock_handle = open(lock_path, 'w')
                    msvcrt.locking(lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
                    return lock_handle
                else:
                    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
                    lock_type = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
                    fcntl.flock(fd, lock_type | fcntl.LOCK_NB)
                    return fd
            except (IOError, OSError):
                try:
                    if IS_WINDOWS and 'lock_handle' in dir():
                        lock_handle.close()
                    elif not IS_WINDOWS and 'fd' in dir():
                        os.close(fd)
                except:
                    pass
                time.sleep(0.1)
        return None

    def _release_lock(self, handle):
        if handle is None:
            return
        try:
            if IS_WINDOWS:
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                except:
                    pass
                handle.close()
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)
                os.close(handle)
        except:
            try:
                if IS_WINDOWS:
                    handle.close()
                else:
                    os.close(handle)
            except:
                pass

    @contextmanager
    def _lock(self, lock_path, exclusive=True, timeout=30):
        fd = self._acquire_lock(lock_path, timeout=timeout, exclusive=exclusive)
        if fd is None:
            raise TimeoutError(f'无法获取锁: {lock_path}，超时 {timeout} 秒')
        try:
            yield fd
        finally:
            self._release_lock(fd)

    def _atomic_write_json(self, filepath, data):
        dir_name = os.path.dirname(filepath)
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, filepath)
        except:
            try:
                os.unlink(tmp_path)
            except:
                pass
            raise

    def _read_json_safe(self, filepath):
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def validate_status_transition(self, old_status, new_status):
        allowed = VALID_TRANSITIONS.get(old_status, [])
        return new_status in allowed

    def read_queue(self):
        with self._lock(self.queue_lock_path, exclusive=False):
            data = self._read_json_safe(self.queue_path)
        if data is None:
            data = {'version': '1.0', 'last_updated': '', 'batches': []}
        return data

    def write_queue(self, data):
        data['last_updated'] = datetime.now().isoformat()
        with self._lock(self.queue_lock_path, exclusive=True):
            self._atomic_write_json(self.queue_path, data)

    def get_batches_by_status(self, status):
        queue = self.read_queue()
        return [b for b in queue.get('batches', []) if b.get('status') == status]

    def get_next_batch(self, status='analyzed'):
        batches = self.get_batches_by_status(status)
        if not batches:
            return None
        return batches[0]

    def get_batch(self, batch_id):
        queue = self.read_queue()
        for batch in queue.get('batches', []):
            if batch.get('batch_id') == batch_id:
                return batch
        return None

    def update_batch_status(self, batch_id, new_status, data=None):
        with self._lock(self.queue_lock_path, exclusive=True):
            queue = self._read_json_safe(self.queue_path)
            if queue is None:
                queue = {'version': '1.0', 'last_updated': '', 'batches': []}

            target = None
            for batch in queue.get('batches', []):
                if batch.get('batch_id') == batch_id:
                    target = batch
                    break

            if target is None:
                return False

            old_status = target.get('status', '')
            if not self.validate_status_transition(old_status, new_status):
                return False

            target['status'] = new_status
            target['updated_at'] = datetime.now().isoformat()
            if data:
                target.update(data)

            queue['last_updated'] = datetime.now().isoformat()
            self._atomic_write_json(self.queue_path, queue)
            return True

    def add_batch(self, batch):
        with self._lock(self.queue_lock_path, exclusive=True):
            queue = self._read_json_safe(self.queue_path)
            if queue is None:
                queue = {'version': '1.0', 'last_updated': '', 'batches': []}

            for existing in queue.get('batches', []):
                if existing.get('batch_id') == batch.get('batch_id'):
                    return False

            queue['batches'].append(batch)
            queue['last_updated'] = datetime.now().isoformat()
            self._atomic_write_json(self.queue_path, queue)
            return True

    def archive_batch(self, batch_id):
        with self._lock(self.queue_lock_path, exclusive=True):
            queue = self._read_json_safe(self.queue_path)
            if queue is None:
                return False

            target_idx = None
            for i, batch in enumerate(queue.get('batches', [])):
                if batch.get('batch_id') == batch_id:
                    target_idx = i
                    break

            if target_idx is None:
                return False

            batch = queue['batches'][target_idx]
            archive_file = os.path.join(self.archive_dir, f'{batch_id}.json')
            self._atomic_write_json(archive_file, batch)

            queue['batches'].pop(target_idx)
            queue['last_updated'] = datetime.now().isoformat()
            self._atomic_write_json(self.queue_path, queue)
            return True

    def read_results(self):
        with self._lock(self.results_lock_path, exclusive=False):
            data = self._read_json_safe(self.results_path)
        if data is None:
            data = {'version': '1.0', 'last_updated': '', 'executions': []}
        return data

    def write_execution(self, execution):
        with self._lock(self.results_lock_path, exclusive=True):
            data = self._read_json_safe(self.results_path)
            if data is None:
                data = {'version': '1.0', 'last_updated': '', 'executions': []}

            data['executions'].append(execution)
            data['last_updated'] = datetime.now().isoformat()
            self._atomic_write_json(self.results_path, data)
            return True

    def get_queue_summary(self):
        queue = self.read_queue()
        summary = {s: 0 for s in ALL_STATUSES}
        for batch in queue.get('batches', []):
            status = batch.get('status', 'unknown')
            if status in summary:
                summary[status] += 1
        return summary

    def get_results_summary(self):
        results = self.read_results()
        executions = results.get('executions', [])
        return {
            'total': len(executions),
            'buy': len([e for e in executions if e.get('action') == 'buy']),
            'sell': len([e for e in executions if e.get('action') == 'sell']),
            'hold': len([e for e in executions if e.get('action') == 'hold']),
        }


def main():
    import argparse

    parser = argparse.ArgumentParser(description='并行处理框架')
    parser.add_argument('--data-dir', help='数据目录路径')
    parser.add_argument('--check-queue', action='store_true', help='查看队列状态')
    parser.add_argument('--check-results', action='store_true', help='查看结果队列')
    parser.add_argument('--status', metavar='BATCH_ID', help='查看指定批次状态')
    parser.add_argument('--add-test-batch', action='store_true', help='添加测试批次')
    parser.add_argument('--archive', metavar='BATCH_ID', help='归档指定批次')

    args = parser.parse_args()
    executor = ParallelExecutor(args.data_dir)

    if args.check_queue:
        summary = executor.get_queue_summary()
        queue = executor.read_queue()
        print(f"队列版本: {queue.get('version')}")
        print(f"最后更新: {queue.get('last_updated', '无')}")
        print(f"批次总数: {len(queue.get('batches', []))}")
        print("各状态数量:")
        for status, count in summary.items():
            if count > 0:
                print(f"  {status}: {count}")

    elif args.check_results:
        summary = executor.get_results_summary()
        print(f"执行结果总数: {summary['total']}")
        print(f"  买入: {summary['buy']}")
        print(f"  卖出: {summary['sell']}")
        print(f"  持有: {summary['hold']}")

    elif args.status:
        batch = executor.get_batch(args.status)
        if batch:
            print(json.dumps(batch, ensure_ascii=False, indent=2))
        else:
            print(f"未找到批次: {args.status}")

    elif args.add_test_batch:
        now = datetime.now()
        batch_id = now.strftime('%Y%m%d_%H%M%S')
        test_batch = {
            'batch_id': batch_id,
            'status': 'analyzed',
            'created_at': now.isoformat(),
            'updated_at': now.isoformat(),
            'priority': 'high',
            'data': {
                'news_count': 150,
                'sentiment_score': 0.65,
                'key_themes': ['央行降准', '半导体上涨'],
                'ai_summary': '市场整体情绪偏积极，央行降准释放流动性利好'
            }
        }
        if executor.add_batch(test_batch):
            print(f"测试批次已添加: {batch_id}")
        else:
            print("添加失败，批次ID可能已存在")

    elif args.archive:
        if executor.archive_batch(args.status):
            print(f"批次 {args.status} 已归档")
        else:
            print(f"归档失败: 批次不存在或无法归档")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
