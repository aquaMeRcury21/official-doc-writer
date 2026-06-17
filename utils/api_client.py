import logging
import os
import random
import time
from dataclasses import dataclass
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# ============================================================
# 模型定价（单位：元/百万 token）
# 以 DeepSeek 官方实时定价为准，此处为兜底默认值
# ============================================================
PRICING = {
    'deepseek-chat':     {'input': 2.0, 'output': 8.0},   # V3/V4
    'deepseek-reasoner': {'input': 4.0, 'output': 16.0},  # R1
}


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    base_delay: float = 1.0        # 基础等待秒数
    max_delay: float = 30.0        # 最大等待秒数
    backoff_factor: float = 2.0    # 指数退避因子
    jitter: bool = True            # 是否加随机抖动
    retry_on_status: tuple = (429, 500, 502, 503, 504)


@dataclass
class CallResult:
    """单次 API 调用结果"""
    success: bool
    content: Optional[str] = None
    model: str = ''
    input_tokens: int = 0
    output_tokens: int = 0
    cost_yuan: float = 0.0
    duration_ms: float = 0.0
    retries_used: int = 0
    error: Optional[str] = None


class TASK_TYPE:  # noqa: N801
    """任务类型枚举 —— 用于模型自动路由"""
    DRAFT = 'draft'           # 起草公文正文 → deepseek-chat, temp=0.15
    PROOFREAD = 'proofread'   # 校对/审核 → deepseek-reasoner, temp=0.05
    OUTLINE = 'outline'       # 大纲/摘要/关键词 → deepseek-chat, temp=0.1, 节能
    REWRITE = 'rewrite'       # 润色/改写 → deepseek-chat, temp=0.2
    CLASSIFY = 'classify'     # 文种判断/分类 → deepseek-chat, temp=0.0


# 任务 → (模型, 建议温度, 建议 max_tokens)
TASK_ROUTES = {
    TASK_TYPE.DRAFT:     ('deepseek-chat', 0.15, 8192),
    TASK_TYPE.PROOFREAD: ('deepseek-reasoner', 0.05, 4096),
    TASK_TYPE.OUTLINE:   ('deepseek-chat', 0.1, 2048),
    TASK_TYPE.REWRITE:   ('deepseek-chat', 0.2, 4096),
    TASK_TYPE.CLASSIFY:  ('deepseek-chat', 0.0, 512),
}


def _build_system_prompt(task_type: str) -> str:
    """按任务类型构造系统提示词"""
    prompts = {
        TASK_TYPE.DRAFT: (
            '你是一位在体制内深耕20年以上的公文写作专家。'
            '严格遵循 GB/T 9704-2012 标准撰写公文，语言严谨、规范、无AI腔。'
            '返回纯公文正文，不加任何解释说明。'
        ),
        TASK_TYPE.PROOFREAD: (
            '你是一位公文审核专家。请严格审查以下公文，逐项指出：'
            '1) 格式错误（层级序号、标点、字体）'
            '2) 语言问题（AI腔、口语化、情绪词）'
            '3) 逻辑漏洞（前后矛盾、数据冲突）'
            '4) 敏感表述（禁用词、政治用语不规范）'
            '输出修改清单，每条注明原文 → 修改建议。'
        ),
        TASK_TYPE.OUTLINE: (
            '你是一位公文写作助手。请根据用户需求生成简洁大纲，'
            '只列出一/二级标题结构，不加正文内容。'
        ),
        TASK_TYPE.REWRITE: (
            '你是一位公文润色专家。请在保留原意和事实数据的前提下，'
            '将以下文字改写为规范的公文表述，去除口语化、AI腔和松散表达。'
        ),
        TASK_TYPE.CLASSIFY: (
            '请判断以下任务应使用何种公文文种。'
            '只返回文种名称（如：请示、通知、报告、函…），不返回其他内容。'
        ),
    }
    return prompts.get(task_type, prompts[TASK_TYPE.DRAFT])


class DeepSeekClient:
    """DeepSeek API 客户端 —— 封装重试、退避、记账、模型路由"""

    def __init__(
        self,
        api_key: str,
        base_url: str = 'https://api.deepseek.com',
        retry_config: Optional[RetryConfig] = None,
        default_task: str = TASK_TYPE.DRAFT,
        enable_tracking: bool = True,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.retry_cfg = retry_config or RetryConfig()
        self.default_task = default_task
        self.enable_tracking = enable_tracking
        self._tracker = None

    @classmethod
    def from_env(cls, **kwargs):
        """从环境变量 / .env 文件创建客户端。

        按优先级：显式参数 > 环境变量 > 默认值
        """
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        return cls(
            api_key=kwargs.get('api_key') or os.getenv('DEEPSEEK_API_KEY', ''),
            base_url=kwargs.get('base_url') or os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com'),
            **{k: v for k, v in kwargs.items() if k not in ('api_key', 'base_url')},
        )

    # ---- 公开接口 ----

    def chat(
        self,
        user_message: str,
        task_type: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        extra_messages: Optional[list] = None,
    ) -> CallResult:
        """发送对话请求，自动路由模型、重试、记账。

        Args:
            user_message: 用户输入的文本
            task_type: 任务类型（draft/proofread/outline/rewrite/classify）
            temperature: 覆盖默认温度（None 则按任务自动选择）
            max_tokens: 最大输出 token（None 则自动估算）
            extra_messages: 额外的消息列表（放在 system prompt 之后）

        Returns:
            CallResult（含内容、token 用量、费用、耗时等）
        """
        tt = task_type or self.default_task
        model, default_temp, default_max = TASK_ROUTES.get(
            tt, TASK_ROUTES[TASK_TYPE.DRAFT]
        )
        temp = temperature if temperature is not None else default_temp
        mt = max_tokens if max_tokens is not None else default_max

        messages = [{'role': 'system', 'content': _build_system_prompt(tt)}]
        if extra_messages:
            messages.extend(extra_messages)
        messages.append({'role': 'user', 'content': user_message})

        payload = {
            'model': model,
            'messages': messages,
            'temperature': temp,
            'max_tokens': mt,
        }

        return self._call_with_retry(payload, model, task_type=tt)

    def draft(
        self,
        user_message: str,
        temperature: float = 0.15,
        max_tokens: int = 8192,
    ) -> CallResult:
        """起草公文快捷方法"""
        return self.chat(
            user_message,
            task_type=TASK_TYPE.DRAFT,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def proofread(self, document: str) -> CallResult:
        """校对公文快捷方法"""
        return self.chat(
            document,
            task_type=TASK_TYPE.PROOFREAD,
        )

    def outline(self, requirement: str) -> CallResult:
        """生成大纲快捷方法"""
        return self.chat(
            requirement,
            task_type=TASK_TYPE.OUTLINE,
        )

    def classify(self, query: str) -> CallResult:
        """文种分类快捷方法"""
        return self.chat(
            query,
            task_type=TASK_TYPE.CLASSIFY,
        )

    def _get_tracker(self):
        if self._tracker is None and self.enable_tracking:
            from .cost_tracker import get_tracker
            self._tracker = get_tracker()
        return self._tracker

    # ---- 核心调用逻辑 ----

    def _call_with_retry(self, payload: dict, model: str, task_type: str = '') -> CallResult:
        """带指数退避重试的 API 调用"""
        url = f'{self.base_url}/v1/chat/completions'
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

        last_error = None

        for attempt in range(self.retry_cfg.max_retries + 1):
            t_start = time.perf_counter()
            try:
                resp = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=(30, 300),  # (connect, read)
                )

                # ---- 成功 ----
                if resp.status_code == 200:
                    body = resp.json()
                    usage = body.get('usage', {})
                    input_tokens = usage.get('prompt_tokens', 0)
                    output_tokens = usage.get('completion_tokens', 0)
                    content = body['choices'][0]['message']['content']
                    cost = self._calc_cost(model, input_tokens, output_tokens)
                    result = CallResult(
                        success=True,
                        content=content,
                        model=model,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cost_yuan=cost,
                        duration_ms=(time.perf_counter() - t_start) * 1000,
                        retries_used=attempt,
                    )
                    tracker = self._get_tracker()
                    if tracker is not None:
                        tracker.log(result, task_type)
                    return result

                # ---- 429 限流 / 5xx 服务端错误 → 重试 ----
                if resp.status_code in self.retry_cfg.retry_on_status:
                    if attempt < self.retry_cfg.max_retries:
                        delay = self._calc_delay(attempt, resp)
                        logger.warning(
                            'API 返回 %d，第 %d/%d 次重试，等待 %.1f 秒...',
                            resp.status_code, attempt + 1,
                            self.retry_cfg.max_retries, delay
                        )
                        time.sleep(delay)
                        continue
                    last_error = f'HTTP {resp.status_code}: {resp.text[:200]}'

                # ---- 其他客户端错误 → 不重试 ----
                else:
                    last_error = f'HTTP {resp.status_code}: {resp.text[:200]}'
                    break

            except requests.exceptions.Timeout:
                if attempt < self.retry_cfg.max_retries:
                    delay = self._calc_delay(attempt)
                    logger.warning(
                        'API 请求超时，第 %d/%d 次重试，等待 %.1f 秒...',
                        attempt + 1, self.retry_cfg.max_retries, delay
                    )
                    time.sleep(delay)
                    continue
                last_error = '请求超时（已达最大重试次数）'

            except requests.exceptions.ConnectionError as e:
                if attempt < self.retry_cfg.max_retries:
                    delay = self._calc_delay(attempt)
                    logger.warning(
                        '网络连接错误: %s，第 %d/%d 次重试，等待 %.1f 秒...',
                        str(e)[:100], attempt + 1,
                        self.retry_cfg.max_retries, delay
                    )
                    time.sleep(delay)
                    continue
                last_error = f'网络连接失败: {str(e)[:200]}'

            except Exception as e:
                last_error = f'未知异常: {type(e).__name__}: {str(e)[:200]}'
                break

        # 走到这里 = 彻底失败
        result = CallResult(
            success=False,
            model=model,
            retries_used=attempt,
            duration_ms=(time.perf_counter() - t_start) * 1000,
            error=last_error,
        )
        tracker = self._get_tracker()
        if tracker is not None:
            tracker.log(result, task_type)
        return result

    def _calc_delay(self, attempt: int, resp=None) -> float:
        """计算等待秒数：Retry-After > 指数退避 > 兜底"""
        # 优先尊重服务端 Retry-After
        if resp is not None:
            ra = resp.headers.get('Retry-After')
            if ra is not None:
                try:
                    return float(ra)
                except ValueError:
                    pass

        delay = self.retry_cfg.base_delay * (
            self.retry_cfg.backoff_factor ** attempt
        )
        delay = min(delay, self.retry_cfg.max_delay)
        if self.retry_cfg.jitter:
            delay *= random.uniform(0.5, 1.5)
        return delay

    @staticmethod
    def _calc_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        """计算单次调用费用（元）"""
        pricing = PRICING.get(model, PRICING['deepseek-chat'])
        input_cost = (input_tokens / 1_000_000) * pricing['input']
        output_cost = (output_tokens / 1_000_000) * pricing['output']
        return round(input_cost + output_cost, 6)

    def estimate_tokens_for_words(self, word_count: int) -> int:
        """根据目标字数估算所需 max_tokens（中文约 1 字 ≈ 1.5 token）"""
        return int(word_count * 1.5) + 512  # 加 buffer
