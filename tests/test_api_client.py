"""Tests for api_client.py — cost calculation, pricing, retry delay."""

from utils.api_client import TASK_ROUTES, TASK_TYPE, DeepSeekClient, RetryConfig


class TestPricing:
    def test_calc_cost_chat(self):
        cost = DeepSeekClient._calc_cost('deepseek-chat', 1000, 500)
        assert abs(cost - 0.006) < 1e-6

    def test_calc_cost_reasoner(self):
        cost = DeepSeekClient._calc_cost('deepseek-reasoner', 1000, 500)
        assert abs(cost - 0.012) < 1e-6

    def test_calc_cost_unknown_model_fallsback(self):
        cost = DeepSeekClient._calc_cost('unknown-model', 1000, 500)
        assert abs(cost - 0.006) < 1e-6

    def test_zero_tokens(self):
        cost = DeepSeekClient._calc_cost('deepseek-chat', 0, 0)
        assert cost == 0.0


class TestRetryDelay:
    def setup_method(self):
        self.cfg = RetryConfig(base_delay=1.0, max_delay=30.0, backoff_factor=2.0, jitter=False)

    def test_base_delay(self):
        client = DeepSeekClient(api_key='test', retry_config=self.cfg)
        delay = client._calc_delay(0)
        assert delay == 1.0

    def test_exponential_backoff(self):
        client = DeepSeekClient(api_key='test', retry_config=self.cfg)
        delay = client._calc_delay(2)
        assert delay == 4.0

    def test_max_delay_capped(self):
        cfg = RetryConfig(base_delay=10.0, max_delay=30.0, backoff_factor=3.0, jitter=False)
        client = DeepSeekClient(api_key='test', retry_config=cfg)
        delay = client._calc_delay(5)
        assert delay == 30.0

    def test_jitter(self):
        cfg = RetryConfig(base_delay=1.0, max_delay=10.0, backoff_factor=2.0, jitter=True)
        client = DeepSeekClient(api_key='test', retry_config=cfg)
        delays = [client._calc_delay(1) for _ in range(50)]
        assert all(1.0 <= d <= 3.0 for d in delays)


class TestTaskRoutes:
    def test_draft_uses_deepseek_chat(self):
        model, temp, max_tok = TASK_ROUTES[TASK_TYPE.DRAFT]
        assert model == 'deepseek-chat'
        assert temp == 0.15
        assert max_tok == 8192

    def test_proofread_uses_reasoner(self):
        model, temp, max_tok = TASK_ROUTES[TASK_TYPE.PROOFREAD]
        assert model == 'deepseek-reasoner'
        assert temp == 0.05

    def test_classify_low_temp(self):
        model, temp, max_tok = TASK_ROUTES[TASK_TYPE.CLASSIFY]
        assert temp == 0.0
        assert max_tok == 512


class TestClientInit:
    def test_from_env_no_key_returns_empty(self):
        client = DeepSeekClient(api_key='', base_url='https://api.deepseek.com')
        assert client.api_key == ''

    def test_default_task_is_draft(self):
        client = DeepSeekClient(api_key='test-key')
        assert client.default_task == TASK_TYPE.DRAFT

    def test_estimate_tokens(self):
        client = DeepSeekClient(api_key='test-key')
        estimated = client.estimate_tokens_for_words(1000)
        assert estimated == 1000 * 1.5 + 512
