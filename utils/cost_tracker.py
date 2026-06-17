import json
import os
import threading
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Optional

from .api_client import CallResult

LOG_PATH = os.path.join(os.path.dirname(__file__), 'cost_log.jsonl')


@dataclass
class CostEntry:
    """单次调用记账条目"""
    timestamp: str         # ISO 格式时间
    date: str              # 日期 YYYY-MM-DD
    model: str
    task_type: str
    input_tokens: int
    output_tokens: int
    cost_yuan: float
    duration_ms: float
    success: bool
    error: Optional[str] = None
    retries_used: int = 0

    @classmethod
    def from_result(cls, result: CallResult, task_type: str) -> 'CostEntry':
        now = datetime.now()
        return cls(
            timestamp=now.isoformat(),
            date=now.strftime('%Y-%m-%d'),
            model=result.model,
            task_type=task_type,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cost_yuan=result.cost_yuan,
            duration_ms=round(result.duration_ms, 0),
            success=result.success,
            error=result.error,
            retries_used=result.retries_used,
        )


class CostTracker:
    """Token 用量 & 费用跟踪器（线程安全、JSONL 持久化）"""

    def __init__(self, log_path: str = LOG_PATH, daily_budget_yuan: float = 50.0):
        self._log_path = log_path
        self._lock = threading.Lock()
        self.daily_budget = daily_budget_yuan
        # 内存缓存今日累计
        self._today_cache: tuple[str, float] = ('', 0.0)

    # ---- 公开接口 ----

    def log(self, result: CallResult, task_type: str) -> CostEntry:
        """记录一次调用并写入磁盘"""
        entry = CostEntry.from_result(result, task_type)
        with self._lock:
            with open(self._log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(asdict(entry), ensure_ascii=False) + '\n')
        return entry

    def today_cost(self) -> float:
        """查询今日累计费用"""
        today_str = date.today().isoformat()
        if self._today_cache[0] == today_str:
            return self._today_cache[1]
        total = 0.0
        for entry in self._iter_today():
            total += entry.get('cost_yuan', 0)
        self._today_cache = (today_str, total)
        return total

    def check_budget(self) -> bool:
        """检查是否超出日预算，返回 True 表示可继续调用"""
        return self.today_cost() < self.daily_budget

    def budget_remaining(self) -> float:
        """剩余预算"""
        return max(0.0, self.daily_budget - self.today_cost())

    def monthly_report(self, year: int = None, month: int = None) -> dict:
        """生成月度费用统计"""
        if year is None or month is None:
            now = datetime.now()
            year, month = now.year, now.month
        prefix = f'{year:04d}-{month:02d}'
        total_cost = 0.0
        total_input = 0
        total_output = 0
        success_count = 0
        fail_count = 0
        by_task = {}
        for entry in self._iter_all():
            if not entry.get('date', '').startswith(prefix):
                continue
            total_cost += entry.get('cost_yuan', 0)
            total_input += entry.get('input_tokens', 0)
            total_output += entry.get('output_tokens', 0)
            if entry.get('success'):
                success_count += 1
            else:
                fail_count += 1
            tt = entry.get('task_type', 'unknown')
            if tt not in by_task:
                by_task[tt] = {'count': 0, 'cost': 0.0}
            by_task[tt]['count'] += 1
            by_task[tt]['cost'] += entry.get('cost_yuan', 0)

        return {
            'period': f'{prefix}',
            'total_cost_yuan': round(total_cost, 4),
            'total_input_tokens': total_input,
            'total_output_tokens': total_output,
            'call_count': success_count + fail_count,
            'success_count': success_count,
            'fail_count': fail_count,
            'by_task': by_task,
        }

    def summary(self) -> str:
        """生成可读的今日摘要"""
        today = self.today_cost()
        budget = self.daily_budget
        pct = (today / budget * 100) if budget > 0 else 0
        status = '⚠️ 预算紧张' if pct > 80 else ('🚫 已超预算' if pct >= 100 else '正常')
        return (
            f'今日费用：¥{today:.4f} / ¥{budget:.2f} ({pct:.1f}%)  [{status}]'
        )

    # ---- 内部方法 ----

    def _iter_all(self):
        """遍历所有日志条目（生成器）"""
        if not os.path.exists(self._log_path):
            return
        with open(self._log_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue

    def _iter_today(self):
        """遍历今日日志"""
        today_str = date.today().isoformat()
        for entry in self._iter_all():
            if entry.get('date') == today_str:
                yield entry


# ============================================================
# 全局单例
# ============================================================
_tracker: Optional[CostTracker] = None
_tracker_lock = threading.Lock()


def get_tracker(daily_budget_yuan: float = 50.0) -> CostTracker:
    """获取全局 CostTracker 单例"""
    global _tracker
    if _tracker is None:
        with _tracker_lock:
            if _tracker is None:
                _tracker = CostTracker(daily_budget_yuan=daily_budget_yuan)
    return _tracker
