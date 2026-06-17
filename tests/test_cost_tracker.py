"""Tests for cost_tracker.py — CostEntry, budget checks, monthly report."""

import json
import os

import pytest

from utils.api_client import CallResult
from utils.cost_tracker import CostEntry, CostTracker


class TestCostEntry:
    def test_from_result_creates_entry(self):
        result = CallResult(
            success=True, content='ok', model='deepseek-chat',
            input_tokens=100, output_tokens=50, cost_yuan=0.001,
            duration_ms=500.0, retries_used=0,
        )
        entry = CostEntry.from_result(result, 'draft')
        assert entry.model == 'deepseek-chat'
        assert entry.task_type == 'draft'
        assert entry.input_tokens == 100
        assert entry.output_tokens == 50
        assert entry.success is True


class TestCostTracker:
    @pytest.fixture
    def tracker(self, temp_dir):
        log_path = os.path.join(temp_dir, 'cost_log.jsonl')
        return CostTracker(log_path=log_path, daily_budget_yuan=10.0)

    def test_log_and_today_cost(self, tracker):
        result = CallResult(success=True, content='ok', model='deepseek-chat',
                            input_tokens=100, output_tokens=50, cost_yuan=0.005,
                            duration_ms=200.0)
        tracker.log(result, 'draft')
        cost = tracker.today_cost()
        assert cost > 0

    def test_check_budget_within_limit(self, tracker):
        assert tracker.check_budget() is True

    def test_check_budget_exceeded(self, tracker):
        # Log enough to exceed budget
        result = CallResult(success=True, content='', model='deepseek-chat',
                            input_tokens=0, output_tokens=0, cost_yuan=15.0,
                            duration_ms=0.0)
        tracker.log(result, 'draft')
        assert tracker.check_budget() is False

    def test_budget_remaining(self, tracker):
        result = CallResult(success=True, content='', model='deepseek-chat',
                            input_tokens=0, output_tokens=0, cost_yuan=3.0,
                            duration_ms=0.0)
        tracker.log(result, 'draft')
        remaining = tracker.budget_remaining()
        assert abs(remaining - 7.0) < 0.001

    def test_monthly_report(self, tracker):
        result = CallResult(success=True, content='', model='deepseek-chat',
                            input_tokens=100, output_tokens=50, cost_yuan=0.5,
                            duration_ms=100.0)
        tracker.log(result, 'draft')
        report = tracker.monthly_report()
        assert report['total_cost_yuan'] > 0
        assert report['call_count'] == 1
        assert report['success_count'] == 1

    def test_log_persists_to_disk(self, temp_dir):
        log_path = os.path.join(temp_dir, 'cost_log.jsonl')
        tracker = CostTracker(log_path=log_path, daily_budget_yuan=10.0)
        result = CallResult(success=True, content='', model='test-model',
                            input_tokens=10, output_tokens=5, cost_yuan=0.001,
                            duration_ms=50.0)
        tracker.log(result, 'test')
        assert os.path.exists(log_path)
        with open(log_path, 'r', encoding='utf-8') as f:
            line = json.loads(f.readline())
            assert line['model'] == 'test-model'
