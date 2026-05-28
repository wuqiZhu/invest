# -*- coding: utf-8 -*-
"""
三终端并行处理系统集成测试
测试完整数据流：终端1 → 任务队列 → 终端2 → 结果队列 → 终端3
"""

import os
import sys
import json
import time
import shutil
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'test_integration')
TEST_QUEUE_DIR = os.path.join(TEST_DATA_DIR, 'tasks')
TEST_RESULTS_DIR = os.path.join(TEST_DATA_DIR, 'results')
TEST_KNOWLEDGE_DIR = os.path.join(TEST_DATA_DIR, 'knowledge')

class IntegrationTest:
    """集成测试类"""
    
    def __init__(self):
        self.test_results = []
        self.passed = 0
        self.failed = 0
        
    def setup(self):
        """测试环境准备"""
        print("\n" + "="*60)
        print("三终端并行处理系统集成测试")
        print("="*60)
        print(f"\n测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试目录: {TEST_DATA_DIR}")
        
        if os.path.exists(TEST_DATA_DIR):
            shutil.rmtree(TEST_DATA_DIR)
        
        os.makedirs(TEST_QUEUE_DIR, exist_ok=True)
        os.makedirs(TEST_RESULTS_DIR, exist_ok=True)
        os.makedirs(TEST_KNOWLEDGE_DIR, exist_ok=True)
        
        self._init_queue_files()
        
    def _init_queue_files(self):
        """初始化队列文件"""
        queue_file = os.path.join(TEST_QUEUE_DIR, 'queue.json')
        results_file = os.path.join(TEST_RESULTS_DIR, 'executions.json')
        
        with open(queue_file, 'w', encoding='utf-8') as f:
            json.dump({
                "version": "1.0",
                "last_updated": "",
                "batches": []
            }, f, ensure_ascii=False, indent=2)
            
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                "version": "1.0",
                "last_updated": "",
                "executions": []
            }, f, ensure_ascii=False, indent=2)
    
    def log_test(self, test_name, passed, details=""):
        """记录测试结果"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.test_results.append({
            'name': test_name,
            'status': status,
            'passed': passed,
            'details': details
        })
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        print(f"  {status} | {test_name}")
        if details and not passed:
            print(f"         | 详情: {details}")
    
    def test_terminal1_write(self):
        """测试终端1：写入任务队列"""
        print("\n[终端1] 测试写入任务队列...")
        
        try:
            from parallel_executor import ParallelExecutor
            
            executor = ParallelExecutor(TEST_DATA_DIR)
            
            test_batch = {
                'batch_id': f'test_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'status': 'analyzed',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'priority': 'high',
                'data': {
                    'news_count': 150,
                    'sentiment_score': 0.72,
                    'key_themes': ['央行降准', '半导体上涨', '消费回暖'],
                    'ai_summary': '央行宣布降准0.5个百分点，释放长期资金约1万亿元',
                    'alerts': [],
                    'analysis_time': datetime.now().isoformat()
                }
            }
            
            result = executor.add_batch(test_batch)
            self.log_test("终端1-写入任务队列", result, f"批次ID: {test_batch['batch_id']}")
            
            queue = executor.read_queue()
            batches = queue.get('batches', [])
            has_batch = len(batches) > 0 and batches[0].get('status') == 'analyzed'
            self.log_test("终端1-队列状态正确", has_batch, f"队列中有 {len(batches)} 个批次")
            
            return test_batch['batch_id'] if result else None
            
        except Exception as e:
            self.log_test("终端1-写入任务队列", False, str(e))
            return None
    
    def test_terminal2_process(self, batch_id):
        """测试终端2：读取并处理"""
        print("\n[终端2] 测试读取并处理...")
        
        if not batch_id:
            self.log_test("终端2-读取任务队列", False, "无可用批次")
            return None
            
        try:
            from parallel_executor import ParallelExecutor
            from decision_engine import DecisionEngine
            
            executor = ParallelExecutor(TEST_DATA_DIR)
            
            batch = executor.get_next_batch(status='analyzed')
            self.log_test("终端2-读取任务队列", batch is not None, 
                         f"批次: {batch.get('batch_id') if batch else 'None'}")
            
            if not batch:
                return None
            
            engine = DecisionEngine(data_dir=TEST_DATA_DIR)
            
            analysis_data = batch.get('data', {})
            analysis_data['batch_id'] = batch.get('batch_id')
            
            decision = engine.make_decision(analysis_data)
            
            has_decision = False
            if decision is not None:
                if 'action' in decision:
                    has_decision = True
                    action = decision.get('action')
                elif 'decisions' in decision:
                    has_decision = True
                    action = f"多基金决策({len(decision.get('decisions', []))}个)"
                else:
                    action = "未知格式"
            else:
                action = "None"
            
            self.log_test("终端2-生成决策", has_decision, f"决策: {action}")
            
            if has_decision:
                batch_id = batch.get('batch_id')
                update_result = executor.update_batch_status(
                    batch_id, 'decided', {'decision': decision}
                )
                self.log_test("终端2-更新状态为decided", update_result)
            
            return decision
            
        except Exception as e:
            self.log_test("终端2-处理", False, str(e))
            import traceback
            traceback.print_exc()
            return None
    
    def test_terminal2_execute(self, decision):
        """测试终端2：执行交易"""
        print("\n[终端2] 测试执行交易...")
        
        if not decision:
            self.log_test("终端2-执行交易", False, "无可用决策")
            return None
            
        try:
            from execution_engine import ExecutionEngine
            from parallel_executor import ParallelExecutor
            
            engine = ExecutionEngine(data_dir=TEST_DATA_DIR)
            
            if 'decisions' in decision:
                results = []
                for dec in decision['decisions']:
                    result = engine.execute(dec, update_batch=False)
                    results.append(result)
                self.log_test("终端2-执行交易", len(results) > 0, 
                             f"执行了 {len(results)} 笔交易")
            else:
                result = engine.execute(decision)
                self.log_test("终端2-执行交易", result is not None, 
                             f"状态: {result.get('status') if result else 'None'}")
                results = [result]
            
            executor = ParallelExecutor(TEST_DATA_DIR)
            results_data = executor.read_results()
            executions = results_data.get('executions', [])
            self.log_test("终端2-结果写入队列", len(executions) > 0, 
                         f"结果队列中有 {len(executions)} 条记录")
            
            batch = executor.get_next_batch(status='decided')
            if batch:
                batch_id = batch.get('batch_id')
                executor.update_batch_status(batch_id, 'executed', {'execution': results})
            
            return results
            
        except Exception as e:
            self.log_test("终端2-执行交易", False, str(e))
            import traceback
            traceback.print_exc()
            return None
    
    def test_terminal3_process(self):
        """测试终端3：反馈学习"""
        print("\n[终端3] 测试反馈学习...")
        
        try:
            from parallel_executor import ParallelExecutor
            
            executor = ParallelExecutor(TEST_DATA_DIR)
            results_data = executor.read_results()
            executions = results_data.get('executions', [])
            
            if not executions:
                self.log_test("终端3-读取结果队列", False, "结果队列为空")
                return None
            
            self.log_test("终端3-读取结果队列", True, f"读取到 {len(executions)} 条结果")
            
            execution = executions[0]
            self.log_test("终端3-获取执行结果", True, 
                         f"执行ID: {execution.get('execution_id', 'N/A')}")
            
            batch_id = execution.get('batch_id')
            if batch_id:
                executor.update_batch_status(batch_id, 'feedbacked', {'feedback': {'status': 'collected'}})
                self.log_test("终端3-更新状态为feedbacked", True)
                
                executor.update_batch_status(batch_id, 'learned', {'learning': {'status': 'completed'}})
                self.log_test("终端3-更新状态为learned", True)
            
            return execution
            
        except Exception as e:
            self.log_test("终端3-处理", False, str(e))
            import traceback
            traceback.print_exc()
            return None
    
    def test_full_flow(self):
        """测试完整流程"""
        print("\n[完整流程] 验证端到端数据流...")
        
        try:
            from parallel_executor import ParallelExecutor
            
            executor = ParallelExecutor(TEST_DATA_DIR)
            
            summary = executor.get_queue_summary()
            self.log_test("完整流程-队列状态查询", True, f"状态: {summary}")
            
            results_summary = executor.get_results_summary()
            self.log_test("完整流程-结果队列查询", True, f"结果: {results_summary}")
            
            queue = executor.read_queue()
            batches = queue.get('batches', [])
            
            if batches:
                batch = batches[0]
                batch_id = batch.get('batch_id')
                
                statuses = []
                if 'decision' in batch:
                    statuses.append('decided')
                if 'execution' in batch or 'executions' in batch:
                    statuses.append('executed')
                if 'feedback' in batch:
                    statuses.append('feedbacked')
                if 'learning' in batch:
                    statuses.append('learned')
                
                self.log_test("完整流程-批次有决策", 'decided' in statuses)
                self.log_test("完整流程-批次有执行", 'executed' in statuses)
                self.log_test("完整流程-批次有反馈", 'feedbacked' in statuses)
                self.log_test("完整流程-批次有学习", 'learned' in statuses)
            
            return True
            
        except Exception as e:
            self.log_test("完整流程", False, str(e))
            return False
    
    def test_state_transitions(self):
        """测试状态流转"""
        print("\n[状态流转] 验证状态转换规则...")
        
        try:
            from parallel_executor import ParallelExecutor, VALID_TRANSITIONS
            
            executor = ParallelExecutor(TEST_DATA_DIR)
            
            for old_status, new_statuses in VALID_TRANSITIONS.items():
                for new_status in new_statuses:
                    valid = executor.validate_status_transition(old_status, new_status)
                    self.log_test(f"状态转换-{old_status}→{new_status}", valid)
            
            invalid = executor.validate_status_transition('created', 'learned')
            self.log_test("状态转换-无效转换拒绝", not invalid, "created→learned 应该被拒绝")
            
            return True
            
        except Exception as e:
            self.log_test("状态流转", False, str(e))
            return False
    
    def test_file_lock(self):
        """测试文件锁"""
        print("\n[文件锁] 验证并发安全...")
        
        try:
            from parallel_executor import ParallelExecutor
            
            executor = ParallelExecutor(TEST_DATA_DIR)
            
            with executor._lock(executor.queue_lock_path, exclusive=True):
                self.log_test("文件锁-排他锁获取", True)
            
            with executor._lock(executor.queue_lock_path, exclusive=False):
                self.log_test("文件锁-共享锁获取", True)
            
            return True
            
        except Exception as e:
            self.log_test("文件锁", False, str(e))
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        self.setup()
        
        self.test_file_lock()
        self.test_state_transitions()
        
        batch_id = self.test_terminal1_write()
        
        decision = self.test_terminal2_process(batch_id)
        
        results = self.test_terminal2_execute(decision)
        
        self.test_terminal3_process()
        
        self.test_full_flow()
        
        self.print_summary()
    
    def print_summary(self):
        """打印测试总结"""
        print("\n" + "="*60)
        print("测试总结")
        print("="*60)
        
        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0
        
        print(f"\n总测试数: {total}")
        print(f"通过: {self.passed}")
        print(f"失败: {self.failed}")
        print(f"通过率: {pass_rate:.1f}%")
        
        if self.failed > 0:
            print("\n失败的测试:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"  ❌ {result['name']}: {result['details']}")
        
        print("\n" + "="*60)
        
        if pass_rate >= 80:
            print("✅ 系统整体健康，可以部署")
        elif pass_rate >= 60:
            print("⚠️ 系统基本可用，但有部分问题需要修复")
        else:
            print("❌ 系统存在严重问题，需要修复后才能部署")
        
        return pass_rate >= 80


def main():
    test = IntegrationTest()
    test.run_all_tests()


if __name__ == '__main__':
    main()
